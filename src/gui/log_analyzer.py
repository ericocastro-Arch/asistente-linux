"""Consulta local y resumen de registros del journal de systemd."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
from typing import Any


MAX_EVENTS = 250
MAX_MESSAGE_CHARS = 1800
MAX_CAPTURE_CHARS = 4_000_000

PRIORITIES = {"err", "warning", "notice", "info", "debug", "all"}
PERIODS = {"1h": "1 hour ago", "24h": "24 hours ago", "7d": "7 days ago", "boot": "boot"}
SOURCES: dict[str, tuple[str, str | None]] = {
    "system": ("system", None),
    "user": ("user", None),
    "kernel": ("system", "__kernel__"),
    "network": ("system", "NetworkManager.service"),
    "bluetooth": ("system", "bluetooth.service"),
    "printing": ("system", "cups.service"),
    "audio": ("user", "pipewire.service"),
    "packagekit": ("system", "packagekit.service"),
}

PRIORITY_NAMES = {
    "0": "Emergencia", "1": "Alerta", "2": "Crítico", "3": "Error",
    "4": "Advertencia", "5": "Aviso", "6": "Información", "7": "Depuración",
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization)\b(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;]+)"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)(https?://)[^/@\s:]+:[^/@\s]+@"),
)
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_HOME_PATTERN = re.compile(r"(?<![A-Za-z0-9_.-])/home/[^/\s]+")

_INSIGHT_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("Red", re.compile(r"(?i)\b(network|wifi|wi-fi|dns|dhcp|carrier|connectivity|no route to host)\b"), "Revisa la conexión, el router y si una VPN está interfiriendo."),
    ("Almacenamiento", re.compile(r"(?i)(no space left|disk full|read-only file system|enospc)"), "Comprueba el espacio libre y conserva una copia antes de borrar archivos."),
    ("Paquetes", re.compile(r"(?i)\b(apt|dpkg|dnf|rpm|pacman|zypper|packagekit|flatpak|snap)\b.*(error|fail|broken|lock)|unable to locate|dependency problems"), "Revisa el gestor de paquetes y cancela si propone quitar componentes que necesitas."),
    ("Audio", re.compile(r"(?i)\b(pipewire|pulseaudio|alsa|audio|sound)\b.*(error|fail|timeout|unavailable)|failed.*(pipewire|pulseaudio)"), "Comprueba el dispositivo de salida y el volumen en los ajustes de Sonido."),
    ("Bluetooth", re.compile(r"(?i)\b(bluetooth|bluez)\b.*(error|fail|timeout|rfkill|blocked)"), "Revisa si Bluetooth está activo y si el dispositivo está en modo de emparejamiento."),
    ("Dispositivos gráficos", re.compile(r"(?i)\b(nvidia|nouveau|amdgpu|i915|drm|gpu|xorg|wayland)\b.*(error|fail|timeout|firmware)"), "Comprueba el modelo gráfico y los controladores recomendados por tu distribución."),
    ("Servicios", re.compile(r"(?i)(failed to start|unit .* failed|service .* failed|dependency failed)"), "Busca el nombre del servicio afectado y revisa su estado antes de reiniciarlo."),
    ("Permisos", re.compile(r"(?i)(permission denied|operation not permitted|access denied)"), "Confirma la ruta y la cuenta propietaria; evita aplicar permisos amplios a carpetas enteras."),
)


def _redact(value: str) -> str:
    text = str(value or "")
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 3:
            text = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}[oculto]", text)
        else:
            text = pattern.sub("[dato sensible oculto]", text)
    text = _EMAIL_PATTERN.sub("[correo oculto]", text)
    text = _HOME_PATTERN.sub("~", text)
    text = "".join(char for char in text if char.isprintable() or char == "\t")
    return text[:MAX_MESSAGE_CHARS]


def _event_time(raw: Any) -> str:
    try:
        stamp = int(raw) / 1_000_000
        return dt.datetime.fromtimestamp(stamp).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError, OverflowError):
        return "Hora desconocida"


def _parse_event(raw: str) -> dict[str, str] | None:
    try:
        item = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(item, dict):
        return None
    priority = str(item.get("PRIORITY", "7"))
    message = item.get("MESSAGE", "")
    if isinstance(message, list):
        message = "".join(str(part) for part in message)
    source = item.get("SYSLOG_IDENTIFIER") or item.get("_SYSTEMD_UNIT") or item.get("_SYSTEMD_USER_UNIT") or item.get("_COMM") or "Sistema"
    unit = item.get("_SYSTEMD_UNIT") or item.get("_SYSTEMD_USER_UNIT") or ""
    return {
        "time": _event_time(item.get("__REALTIME_TIMESTAMP")),
        "priority": priority if priority in PRIORITY_NAMES else "7",
        "severity": PRIORITY_NAMES.get(priority, "Depuración"),
        "source": _redact(str(source))[:100],
        "unit": _redact(str(unit))[:120],
        "message": _redact(str(message)),
    }


def _summarize(events: list[dict[str, str]]) -> list[dict[str, str]]:
    insights: list[dict[str, str]] = []
    messages = [event["message"] for event in events]
    for title, pattern, recommendation in _INSIGHT_PATTERNS:
        matches = sum(bool(pattern.search(message)) for message in messages)
        if matches:
            insights.append({"title": title, "count": str(matches), "recommendation": recommendation})
    if not insights and events:
        insights.append({
            "title": "Sin patrón frecuente detectado", "count": "0",
            "recommendation": "Abre un registro y revisa el mensaje y la hora. LinuxMate no cambia la configuración ni concluye una causa automáticamente.",
        })
    return insights[:5]


def get_system_logs(
    priority: str = "err",
    period: str = "24h",
    source: str = "system",
    query: str = "",
) -> dict[str, Any]:
    """Lee hasta 250 eventos del journal con filtros fijos y devuelve datos redactados."""
    if not isinstance(priority, str) or priority not in PRIORITIES:
        return {"success": False, "message": "Prioridad no válida."}
    if not isinstance(period, str) or period not in PERIODS:
        return {"success": False, "message": "Periodo no válido."}
    if not isinstance(source, str) or source not in SOURCES:
        return {"success": False, "message": "Origen de registros no válido."}
    query = query[:100].strip().lower() if isinstance(query, str) else ""
    if not shutil.which("journalctl"):
        return {"success": False, "message": "Este sistema no tiene journalctl. El analizador requiere el journal de systemd."}

    scope, unit = SOURCES[source]
    args = ["journalctl", "--no-pager", "--quiet", "--output=json", f"--lines={MAX_EVENTS}"]
    args.append("--user" if scope == "user" else "--system")
    period_value = PERIODS[period]
    if period_value == "boot":
        args.append("--boot")
    else:
        args.extend(["--since", period_value])
    if priority != "all":
        args.extend(["--priority", priority])
    if unit == "__kernel__":
        args.append("--dmesg")
    elif unit:
        args.extend(["--unit", unit])

    try:
        result = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=15,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "La lectura del journal tardó demasiado y se canceló."}
    except OSError:
        return {"success": False, "message": "No se pudo consultar el journal de este equipo."}

    if result.returncode != 0:
        error = _redact((result.stderr or "").strip())
        if "permission denied" in error.lower() or "not seeing messages" in error.lower():
            message = "Tu cuenta no tiene permiso para leer estos registros del sistema. Puedes consultar los registros de usuario o pedir al administrador que habilite el acceso de lectura."
        else:
            message = "journalctl no pudo leer este origen. Puede que el servicio o ese tipo de registros no estén disponibles."
        return {"success": False, "message": message, "detail": error[:500]}

    output = result.stdout[:MAX_CAPTURE_CHARS]
    events = [event for line in output.splitlines() if (event := _parse_event(line)) is not None]
    if query:
        events = [event for event in events if query in " ".join((event["source"], event["unit"], event["message"])).lower()]
    return {
        "success": True,
        "events": events,
        "insights": _summarize(events),
        "count": len(events),
        "scanned": min(MAX_EVENTS, sum(1 for line in output.splitlines() if line.strip().startswith("{"))),
        "limit": MAX_EVENTS,
        "message": "Los registros se analizaron en este equipo; no se enviaron al agente.",
    }

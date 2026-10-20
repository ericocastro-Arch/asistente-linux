"""Catálogo de diagnósticos de solo lectura con comandos fijos.

El modelo elige un nombre del catálogo; nunca escribe el comando. Cada entrada es una
lista de argumentos que se ejecuta SIN shell, así que no hay interpolación, tuberías
ni redirecciones que puedan abusarse.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

MAX_OUTPUT_CHARS = 6000
TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class Diagnostic:
    description: str
    argv: tuple[str, ...]
    max_lines: Optional[int] = None


DIAGNOSTICS: dict[str, Diagnostic] = {
    "disk_usage": Diagnostic("Espacio en disco por partición", ("df", "-h", "-x", "tmpfs", "-x", "devtmpfs")),
    "block_devices": Diagnostic("Discos y particiones", ("lsblk",)),
    "memory": Diagnostic("Memoria RAM y swap", ("free", "-h")),
    "uptime_load": Diagnostic("Tiempo encendido y carga del sistema", ("uptime",)),
    "top_cpu_processes": Diagnostic(
        "Procesos que más CPU usan", ("ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%cpu"), max_lines=11),
    "top_memory_processes": Diagnostic(
        "Procesos que más memoria usan", ("ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%mem"), max_lines=11),
    "cpu_info": Diagnostic("Información del procesador", ("lscpu",)),
    "kernel_info": Diagnostic("Versión del kernel y arquitectura", ("uname", "-a")),
    "os_release": Diagnostic("Distribución instalada", ("cat", "/etc/os-release")),
    "network_addresses": Diagnostic("Interfaces y direcciones IP", ("ip", "-br", "addr")),
    "network_routes": Diagnostic("Rutas de red", ("ip", "route")),
    "network_devices": Diagnostic("Estado de los dispositivos de red", ("nmcli", "device", "status")),
    "network_connectivity": Diagnostic("Conectividad según NetworkManager", ("nmcli", "networking", "connectivity")),
    "ping_internet": Diagnostic("Prueba de conexión a Internet (2 paquetes)", ("ping", "-c", "2", "-W", "2", "1.1.1.1")),
    "failed_services": Diagnostic("Servicios systemd que fallaron", ("systemctl", "--failed", "--no-pager")),
    "recent_errors": Diagnostic(
        "Errores recientes del sistema", ("journalctl", "-p", "err", "-b", "--no-pager", "-n", "30")),
    "pending_updates": Diagnostic("Actualizaciones disponibles", ("apt", "list", "--upgradable"), max_lines=40),
    "temperatures": Diagnostic("Temperaturas y sensores", ("sensors",)),
    "usb_devices": Diagnostic("Dispositivos USB conectados", ("lsusb",)),
    "pci_devices": Diagnostic("Dispositivos PCI (tarjeta gráfica, red, etc.)", ("lspci",)),
}


def catalog_description() -> str:
    return "; ".join(f"{name} = {item.description}" for name, item in DIAGNOSTICS.items())


def run_diagnostic(name: object) -> tuple[str, str, str, Optional[int]]:
    """Ejecuta un diagnóstico del catálogo. Devuelve (mensaje, stdout, stderr, código)."""
    if not isinstance(name, str) or name not in DIAGNOSTICS:
        message = "Diagnóstico no reconocido. Disponibles: " + ", ".join(DIAGNOSTICS)
        return message, "", message, None

    item = DIAGNOSTICS[name]
    if shutil.which(item.argv[0]) is None:
        message = f"⚠️ No encontré `{item.argv[0]}` en este equipo; no puedo ejecutar «{item.description}»."
        return message, "", message, None

    try:
        result = subprocess.run(
            list(item.argv),
            shell=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env={**os.environ, "LANG": "es_ES.UTF-8"},
        )
    except subprocess.TimeoutExpired:
        message = f"⏱️ «{item.description}» tardó más de {TIMEOUT_SECONDS} s y fue cancelado."
        return message, "", message, None
    except OSError as exc:
        message = f"❌ No pude ejecutar «{item.description}»: {exc}"
        return message, "", str(exc), None

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    shown = stdout
    if item.max_lines:
        shown = "\n".join(stdout.splitlines()[: item.max_lines])
    if len(shown) > MAX_OUTPUT_CHARS:
        shown = shown[:MAX_OUTPUT_CHARS] + "\n… (salida recortada)"

    if shown:
        message = f"**{item.description}**\n```\n{shown}\n```"
    elif stderr:
        message = f"⚠️ Salida de error de «{item.description}»:\n```\n{stderr}\n```"
    else:
        message = f"✅ «{item.description}» se ejecutó sin salida."
    return message, stdout, stderr, result.returncode

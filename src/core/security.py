"""Reglas de seguridad para acciones del asistente Linux."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9@._:+-]+$")


class SafetyLevel(str, Enum):
    SAFE = "safe"
    CONFIRM = "confirm"
    BLOCKED = "blocked"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class SafetyDecision:
    level: SafetyLevel
    message: str
    risk: RiskLevel = RiskLevel.LOW
    category: str = "read_only"

    @property
    def is_blocked(self) -> bool:
        return self.level == SafetyLevel.BLOCKED

    @property
    def needs_confirmation(self) -> bool:
        return self.level == SafetyLevel.CONFIRM


BLOCKED_PATTERNS = [
    r"\brm\s+-[^\n]*r[^\n]*f\b",
    r"\bmkfs(?:\.[A-Za-z0-9]+)?\b",
    r"\bdd\s+.*\bof=/dev/",
    r":\(\)\s*\{",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bhalt\b",
    r"\bpoweroff\b",
    r"(?<![12])>\s*/dev/(?!null\b)",
    r"\bchmod\s+-R\s+777\b",
    r"\bfind\b[^\n]*(?:-delete|-exec\s+rm)\b",
    r"\b(?:bash|sh)\s+-c\b",
    r"\$\(|`",
]

HIGH_RISK_PATTERNS = [
    r"\bapt(?:-get)?\s+(remove|purge|autoremove|dist-upgrade|full-upgrade)\b",
    r"\bsnap\s+remove\b",
    r"\bflatpak\s+(?:uninstall|remove)\b",
    r"\bsystemctl\s+(stop|disable|mask)\b",
    r"\b(?:rm|unlink|rmdir)\b",
    r"\bchown\b",
    r"\bchmod\b",
    r"\bmv\b.*\s/(etc|usr|bin|sbin|boot)\b",
]

MEDIUM_RISK_PATTERNS = [
    r"\bsudo\b",
    r"\bpkexec\b",
    r"\bapt(?:-get)?\s+(install|upgrade|update)\b",
    r"\bsystemctl\s+(start|restart|enable)\b",
    r"(?:^|[^<])>(?:>|\s*)[^&]",
    r"\bsed\b[^\n]*\s-i(?:\s|$)",
]

READ_ONLY_COMMANDS = {
    "apt-cache", "awk", "cat", "cut", "date", "df", "dpkg", "dpkg-query", "du", "echo", "env",
    "file", "find", "flatpak", "free", "grep", "head", "hostname", "id", "ip", "journalctl",
    "ls", "lsblk", "lscpu", "lspci", "lsusb", "nmcli", "pgrep", "ping", "ps",
    "printf", "pwd", "readlink", "sensors", "snap", "sort", "stat", "systemctl", "tail",
    "top", "uname", "uptime", "wc", "which", "who", "whoami",
}

SYSTEM_WRITE_PREFIXES = (
    "/etc/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/boot/",
    "/sys/",
    "/proc/",
    "/dev/",
    "/run/",
)


def is_safe_name(value: str) -> bool:
    """Valida nombres simples como paquetes apt y servicios systemd."""
    return bool(value and SAFE_NAME_RE.fullmatch(value.strip()))


def assess_command(command: str, allow_confirmation: bool = False) -> SafetyDecision:
    """Clasifica un comando antes de ejecutarlo."""
    clean = command.strip()
    lowered = clean.lower()
    safety_text = re.sub(r"\s*[12]?>\s*/dev/null\b", "", lowered)
    if not clean:
        return SafetyDecision(
            SafetyLevel.BLOCKED,
            "No recibí ningún comando para ejecutar.",
            RiskLevel.CRITICAL,
            "invalid",
        )

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, safety_text):
            return SafetyDecision(
                SafetyLevel.BLOCKED,
                "Bloqueado por seguridad: este comando puede borrar, apagar o dañar el sistema.",
                RiskLevel.CRITICAL,
                "destructive",
            )

    risk_patterns = (
        (HIGH_RISK_PATTERNS, RiskLevel.HIGH),
        (MEDIUM_RISK_PATTERNS, RiskLevel.MEDIUM),
    )
    for patterns, risk in risk_patterns:
        if any(re.search(pattern, safety_text) for pattern in patterns):
            if allow_confirmation:
                return SafetyDecision(
                    SafetyLevel.CONFIRM,
                    f"Accion de riesgo {risk.value}: puede cambiar el sistema y requiere confirmacion explicita.",
                    risk,
                    "system_change",
                )
            return SafetyDecision(
                SafetyLevel.BLOCKED,
                "Este comando requiere permisos o cambia el sistema. Usa una accion grafica con confirmacion.",
                risk,
                "system_change",
            )

    segments = re.split(r"(?:\|\||&&|[|;])", safety_text)
    for segment in segments:
        words = re.findall(r"[a-z0-9_.+-]+", segment.strip())
        if not words:
            continue
        command_name = words[0]
        if command_name in {"command", "timeout"} and len(words) > 1:
            command_name = words[1]
        if command_name not in READ_ONLY_COMMANDS:
            return SafetyDecision(
                SafetyLevel.BLOCKED,
                f"'{command_name}' no esta en la lista de consultas permitidas para ejecucion silenciosa.",
                RiskLevel.MEDIUM,
                "unknown_command",
            )

    return SafetyDecision(
        SafetyLevel.SAFE,
        "Consulta de solo lectura permitida.",
        RiskLevel.LOW,
        "read_only",
    )


def assess_file_write(path: str) -> SafetyDecision:
    """Valida si una ruta puede ser escrita por herramientas del asistente."""
    if not path.strip():
        return SafetyDecision(SafetyLevel.BLOCKED, "Indica la ruta donde quieres guardar el archivo.")

    if path.startswith(SYSTEM_WRITE_PREFIXES):
        return SafetyDecision(
            SafetyLevel.BLOCKED,
            "Escritura bloqueada en una ruta del sistema. Para principiantes, esta acción debe hacerse con confirmación explícita.",
            RiskLevel.HIGH,
            "system_file",
        )

    return SafetyDecision(SafetyLevel.SAFE, "Ruta permitida para escritura.")

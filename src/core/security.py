"""Reglas de seguridad para acciones del asistente Linux."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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
    r"\bdnf\s+(remove|erase|autoremove)\b",
    r"\bpacman\s+-[R]\w*\b",
    r"\bzypper\s+(remove|rm)\b",
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
    r"\bdnf\s+(install|upgrade|update)\b",
    r"\bpacman\s+-[S]\w*\b",
    r"\bzypper\s+(install|in|update|up)\b",
    r"\bsystemctl\s+(start|restart|enable)\b",
    r"(?:^|[^<])>(?:>|\s*)[^&]",
    r"\bsed\b[^\n]*\s-i(?:\s|$)",
]

# "env" y "awk" se quitaron a propósito: `env <programa>` ejecuta cualquier cosa,
# `env` sin argumentos vuelca las API keys y `awk` puede llamar a system().
READ_ONLY_COMMANDS = {
    "apt-cache", "cat", "cut", "date", "df", "dnf", "dpkg", "dpkg-query", "du", "echo",
    "file", "find", "flatpak", "free", "grep", "head", "hostname", "id", "ip", "journalctl",
    "ls", "lsblk", "lscpu", "lspci", "lsusb", "nmcli", "pacman", "pgrep", "ping", "ps",
    "printf", "pwd", "readlink", "rpm", "sensors", "snap", "sort", "stat", "systemctl", "tail",
    "top", "uname", "uptime", "wc", "which", "who", "whoami", "zypper",
}

# Programas que cambian el sistema según su subcomando: solo se permiten estos.
READ_ONLY_SUBCOMMANDS = {
    "systemctl": {
        "status", "is-active", "is-enabled", "is-failed", "list-units", "list-unit-files",
        "list-timers", "list-sockets", "show", "cat",
    },
    "snap": {"list", "info", "find", "services", "version", "connections", "changes"},
    "flatpak": {"list", "info", "search", "remote-ls", "remotes", "history", "--version"},
    "dpkg": {"-l", "--list", "-s", "--status", "-L", "--listfiles", "-S", "--search",
             "--get-selections", "--version"},
    "dnf": {"search", "info", "list", "repoquery", "check-update", "--version"},
    "rpm": {"-q", "-qa", "-qi", "-ql", "-qf", "--version"},
    "pacman": {"-Ss", "-Si", "-Q", "-Qi", "-Ql", "-Qe", "--version", "-V"},
    "zypper": {"search", "se", "info", "if", "packages", "pa", "list-updates", "lu", "--version"},
}

# nmcli, ip, find y sort son de lectura salvo con estas palabras u opciones.
MUTATING_WORDS = {
    "nmcli": {"up", "down", "delete", "modify", "add", "connect", "disconnect", "on", "off",
              "reload", "edit", "import", "clone", "hotspot", "monitor", "save"},
    "ip": {"add", "del", "delete", "set", "flush", "change", "replace", "append", "netns"},
    "find": {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0",
             "-fprintf", "-fls"},
    "sort": {"-o", "--output"},
}

# Rutas con credenciales: nunca se leen en silencio ni se envían al LLM.
SENSITIVE_PATH_PATTERNS = [
    r"(?:^|[\s/=\"'])\.env(?:\.[\w-]+)?(?:$|[\s\"';|&])",
    r"\.ssh\b",
    r"\.gnupg\b",
    r"\.aws\b",
    r"\.netrc\b",
    r"\.pgpass\b",
    r"\.git-credentials\b",
    r"\bid_(?:rsa|dsa|ecdsa|ed25519)\b",
    r"/etc/(?:shadow|gshadow|sudoers)",
    r"/proc/[^\s/]+/environ",
    r"asistente-linux/assistant\.db",
    r"\.local/share/keyrings",
    r"\bprintenv\b",
]

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


def _mutating_usage(command_name: str, args: list[str]) -> str | None:
    """Devuelve un motivo de bloqueo si el comando de lectura se usa para modificar algo."""
    allowed = READ_ONLY_SUBCOMMANDS.get(command_name)
    if allowed is not None:
        if command_name == "dpkg":
            sub = args[0] if args else ""
        else:
            sub = next((word for word in args if not word.startswith("-")), "")
        if sub not in allowed:
            return (
                f"'{command_name} {sub}'".strip()
                + " no es una consulta de solo lectura. Usa una accion grafica con confirmacion."
            )
    mutating = MUTATING_WORDS.get(command_name)
    if mutating:
        for word in args:
            if word in mutating or word.split("=", 1)[0] in mutating:
                return f"'{command_name} {word}' puede modificar el sistema; no se ejecuta en silencio."
        if command_name == "sort" and any(re.fullmatch(r"-[a-z]*o[a-z0-9]*", word) for word in args):
            return "'sort -o' escribe archivos; no se ejecuta en silencio."
    return None


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

    for pattern in SENSITIVE_PATH_PATTERNS:
        if re.search(pattern, safety_text):
            return SafetyDecision(
                SafetyLevel.BLOCKED,
                "Bloqueado por seguridad: ese comando intenta leer credenciales, claves o variables de entorno.",
                RiskLevel.CRITICAL,
                "sensitive_data",
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

    # Las redirecciones tipo 2>&1 no son operadores de segmento.
    segment_text = re.sub(r"[0-9]?>&[0-9-]", " ", safety_text)
    segments = re.split(r"(?:\|\||&&|[|;&\n])", segment_text)
    for segment in segments:
        words = re.findall(r"[a-z0-9_.+-]+", segment.strip())
        if not words:
            continue
        command_name = words[0]
        args = words[1:]
        if command_name in {"command", "timeout"} and args:
            if command_name == "timeout":
                # timeout [opciones] DURACION comando ...
                args = [w for w in args if not w.startswith("-")]
                if args and re.fullmatch(r"\d+(?:\.\d+)?[smhd]?", args[0]):
                    args = args[1:]
                if not args:
                    continue
            command_name, args = args[0], args[1:]
        if command_name not in READ_ONLY_COMMANDS:
            return SafetyDecision(
                SafetyLevel.BLOCKED,
                f"'{command_name}' no esta en la lista de consultas permitidas para ejecucion silenciosa.",
                RiskLevel.MEDIUM,
                "unknown_command",
            )
        blocked_reason = _mutating_usage(command_name, args)
        if blocked_reason:
            return SafetyDecision(
                SafetyLevel.BLOCKED,
                blocked_reason,
                RiskLevel.MEDIUM,
                "unknown_command",
            )

    return SafetyDecision(
        SafetyLevel.SAFE,
        "Consulta de solo lectura permitida.",
        RiskLevel.LOW,
        "read_only",
    )


APP_ROOT = Path(__file__).resolve().parents[2]

# Rutas dentro de $HOME donde el asistente nunca escribe: credenciales, ejecución
# automática (persistencia) y el estado propio de la aplicación.
HOME_DENIED_SUBPATHS = (
    ".ssh", ".gnupg", ".aws", ".kube", ".netrc", ".pgpass", ".git-credentials",
    ".docker/config.json",
    ".local/share/keyrings",
    ".config/autostart",
    ".config/systemd",
    ".config/asistente-linux",
    ".local/share/asistente-linux",
)


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def assess_file_write(path: str) -> SafetyDecision:
    """Valida si una ruta puede ser escrita por herramientas del asistente.

    Política de lista blanca: solo se escribe dentro de $HOME, resolviendo enlaces
    simbólicos y `..`. Dentro de $HOME se excluyen credenciales, autoarranque y el
    código/estado del propio asistente.
    """
    if not isinstance(path, str) or not path.strip():
        return SafetyDecision(SafetyLevel.BLOCKED, "Indica la ruta donde quieres guardar el archivo.")

    try:
        target = Path(path).expanduser().resolve()
        home = Path.home().resolve()
    except (OSError, RuntimeError):
        return SafetyDecision(SafetyLevel.BLOCKED, "No pude interpretar esa ruta de forma segura.", RiskLevel.HIGH, "invalid")

    if str(target).startswith(SYSTEM_WRITE_PREFIXES) or not _is_within(target, home):
        return SafetyDecision(
            SafetyLevel.BLOCKED,
            "Escritura bloqueada: solo puedo guardar archivos dentro de tu carpeta personal. "
            "Los cambios en el sistema deben hacerse con una acción con confirmación y permisos.",
            RiskLevel.HIGH,
            "system_file",
        )

    denied = [home / sub for sub in HOME_DENIED_SUBPATHS]
    denied.append(APP_ROOT)
    if any(_is_within(target, root) for root in denied) or any(
        re.search(pattern, str(target).lower()) for pattern in SENSITIVE_PATH_PATTERNS
    ):
        return SafetyDecision(
            SafetyLevel.BLOCKED,
            "Escritura bloqueada: esa ruta contiene credenciales, configuración de arranque o archivos del propio asistente.",
            RiskLevel.CRITICAL,
            "protected_path",
        )

    return SafetyDecision(SafetyLevel.SAFE, "Ruta permitida para escritura.")


def assess_file_read(path: str) -> SafetyDecision:
    """Valida si una ruta puede leerse y enviarse al chat (y por tanto al LLM)."""
    if not path.strip():
        return SafetyDecision(SafetyLevel.BLOCKED, "Indica la ruta del archivo que quieres leer.")

    lowered = path.lower()
    if any(re.search(pattern, lowered) for pattern in SENSITIVE_PATH_PATTERNS):
        return SafetyDecision(
            SafetyLevel.BLOCKED,
            "Lectura bloqueada: ese archivo puede contener credenciales o claves y su contenido se enviaría a la IA.",
            RiskLevel.CRITICAL,
            "sensitive_data",
        )

    return SafetyDecision(SafetyLevel.SAFE, "Ruta permitida para lectura.")

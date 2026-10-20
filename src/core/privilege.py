"""Capa de ejecución privilegiada con PolicyKit (pkexec) y fallback a terminal interactiva.

Garantiza el principio de mínimo privilegio:
- El agente nunca recibe acceso root general ni ejecuta shells arbitrarias con privilegios.
- Solo ejecuta acciones administrativas estrictamente autorizadas (lista blanca estructurada).
- Solicita autorización centralizada al usuario a través del diálogo de seguridad nativo de PolicyKit.
- Degrada limpiamente a terminal interactiva con sudo si no hay entorno gráfico o agente Polkit disponible.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


# Servicios que NUNCA deben ser detenidos, deshabilitados ni reiniciados arbitrariamente
CRITICAL_SERVICES = {
    "accounts-daemon", "dbus", "display-manager", "gdm", "gdm3", "lightdm",
    "network-manager", "networkmanager", "polkit", "sddm", "ssh", "sshd",
    "systemd-journald", "systemd-logind", "systemd-networkd",
    "systemd-networkd-wait-online", "systemd-resolved", "systemd-udevd", "udev",
    "wpa_supplicant",
}

CRITICAL_PACKAGE_PREFIXES = (
    "firmware-", "grub-", "initramfs-", "linux-base", "linux-firmware",
    "linux-generic", "linux-headers", "linux-image", "linux-modules",
    "systemd", "ubuntu-drivers",
)

CRITICAL_PACKAGES = {
    "bash", "coreutils", "dpkg", "apt", "libc6", "systemd", "systemd-sysv",
    "polkitd", "policykit-1", "sudo", "libpam-runtime", "login",
}


@dataclass
class PrivilegedResult:
    """Resultado de una ejecución que requirió privilegios administrativos."""
    success: bool
    mechanism: str  # "pkexec", "terminal", "blocked", "cancelled", "failed"
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    message: str = ""
    command: List[str] = field(default_factory=list)


def is_pkexec_available() -> bool:
    """Comprueba si la utilidad pkexec de PolicyKit está instalada en el sistema."""
    return bool(shutil.which("pkexec"))


def is_graphical_session() -> bool:
    """Indica si el proceso actual se ejecuta dentro de una sesión de escritorio (X11 o Wayland)."""
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def can_use_pkexec() -> bool:
    """Indica si pkexec puede solicitar autenticación gráfica en esta sesión."""
    return is_pkexec_available() and is_graphical_session()


def get_privilege_status() -> Dict[str, Any]:
    """Reporta el estado de las herramientas de elevación de privilegios."""
    has_pk = is_pkexec_available()
    has_gui = is_graphical_session()
    can_pk = has_pk and has_gui
    return {
        "pkexec_available": has_pk,
        "graphical_session": has_gui,
        "policykit_enabled": can_pk,
        "preferred_mechanism": "pkexec" if can_pk else "terminal",
    }


def is_critical_service(service_name: str) -> bool:
    """Comprueba si el servicio es vital para el inicio, red o sesión gráfica."""
    name = service_name.strip().lower()
    if name.endswith(".service"):
        name = name[:-8]
    return name in CRITICAL_SERVICES or name.startswith("user@")


def is_critical_package(package_name: str) -> bool:
    """Comprueba si el paquete es parte central del sistema operativo."""
    pkg = package_name.strip().lower()
    if pkg in CRITICAL_PACKAGES:
        return True
    return any(pkg.startswith(pfx) for pfx in CRITICAL_PACKAGE_PREFIXES)


def validate_privileged_request(argv: Sequence[str]) -> Tuple[bool, str]:
    """Valida los argumentos contra la lista blanca estricta de acciones del sistema.

    Retorna (True, "") si la acción está permitida, o (False, "motivo") si se bloquea.
    """
    if not argv or not isinstance(argv, (list, tuple)):
        return False, "La solicitud de comando privilegiado está vacía."

    clean_args = [str(a).strip() for a in argv]
    if any(not a for a in clean_args):
        return False, "Los argumentos contienen parámetros vacíos."

    binary = clean_args[0].lower()

    # 1. GESTIÓN DE SERVICIOS SYSTEMD
    if binary == "systemctl":
        if len(clean_args) not in (3, 4):
            return False, "Sintaxis de systemctl privilegiado no autorizada."
        action = clean_args[1].lower()
        valid_actions = {"start", "stop", "restart", "reload", "enable", "disable"}
        if action not in valid_actions:
            return False, f"Acción de servicio no autorizada: '{action}'."
        service = clean_args[2]
        if not re.fullmatch(r"[A-Za-z0-9@._:-]+", service):
            return False, "Nombre de servicio inválido o con caracteres no permitidos."
        service_clean = service.lower()
        if service_clean.endswith(".service"):
            service_clean = service_clean[:-8]
        if service_clean in {"network-manager", "networkmanager"}:
            if action in {"stop", "disable"}:
                return False, f"No está permitido detener ni deshabilitar el servicio de red '{service}'."
            return True, ""
        if action in {"stop", "disable", "restart"} and is_critical_service(service):
            return False, f"No está permitido modificar el servicio crítico del sistema '{service}'."
        return True, ""

    # 2. GESTIÓN DE PAQUETES APT / APT-GET
    if binary in {"apt", "apt-get"}:
        subcmd = clean_args[1].lower()
        if subcmd == "update":
            return True, ""
        if subcmd == "upgrade":
            allowed = {"upgrade", "-y"}
            if set(clean_args[1:]).issubset(allowed):
                return True, ""
            return False, "Sintaxis de apt upgrade no permitida."
        if subcmd == "clean":
            return True, ""
        if subcmd == "autoremove":
            allowed = {"autoremove", "-y", "--purge"}
            if set(clean_args[1:]).issubset(allowed):
                return True, ""
            return False, "Sintaxis de apt autoremove no permitida."
        if subcmd == "install":
            pkgs = [p for p in clean_args[2:] if p != "-y"]
            if not pkgs:
                return False, "No se especificó ningún paquete para instalar."
            for p in pkgs:
                if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", p):
                    return False, f"Identificador de paquete sospechoso: '{p}'."
            return True, ""
        if subcmd == "remove":
            pkgs = [p for p in clean_args[2:] if p != "-y"]
            if not pkgs:
                return False, "No se especificó ningún paquete para desinstalar."
            for p in pkgs:
                if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", p):
                    return False, f"Identificador de paquete sospechoso: '{p}'."
                if is_critical_package(p):
                    return False, f"No se puede desinstalar el paquete crítico '{p}'."
            return True, ""
        if subcmd == "--fix-broken":
            if len(clean_args) >= 3 and clean_args[2].lower() == "install":
                return True, ""
            return False, "Sintaxis de --fix-broken no autorizada."
        return False, f"Subcomando apt no autorizado: '{subcmd}'."

    # 3. DPKG (REPARACIÓN O INSTALACIÓN LOCAL .DEB)
    if binary == "dpkg":
        if clean_args[1:] == ["--configure", "-a"]:
            return True, ""
        if len(clean_args) == 3 and clean_args[1] == "-i":
            deb_path = Path(clean_args[2]).expanduser()
            if deb_path.suffix.lower() != ".deb":
                return False, "El archivo seleccionado no tiene extensión .deb."
            if not deb_path.is_file():
                return False, "El archivo .deb indicado no existe en el sistema."
            return True, ""
        return False, "Operación dpkg no autorizada."

    # 4. SNAP
    if binary == "snap":
        subcmd = clean_args[1].lower()
        if subcmd == "install":
            pkgs = [p for p in clean_args[2:] if p not in {"--classic", "--edge", "--beta"}]
            if not pkgs:
                return False, "No se especificó ningún snap para instalar."
            for p in pkgs:
                if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", p):
                    return False, f"Nombre de paquete snap sospechoso: '{p}'."
            return True, ""
        if subcmd == "remove":
            if len(clean_args) == 3 and re.fullmatch(r"[A-Za-z0-9@._:+-]+", clean_args[2]):
                return True, ""
            return False, "Sintaxis de snap remove no autorizada."
        if subcmd == "refresh":
            return True, ""
        return False, f"Subcomando snap privilegiado no autorizado: '{subcmd}'."

    # 5. DNF (FEDORA / RHEL)
    if binary == "dnf":
        subcmd = clean_args[1].lower()
        if subcmd in {"upgrade", "update"}:
            return True, ""
        if subcmd == "clean":
            return True, ""
        if subcmd == "install":
            pkgs = [p for p in clean_args[2:] if p != "-y"]
            if not pkgs:
                return False, "No se especificó ningún paquete para instalar con dnf."
            for p in pkgs:
                if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", p):
                    return False, f"Nombre de paquete dnf sospechoso: '{p}'."
            return True, ""
        if subcmd in {"remove", "erase"}:
            pkgs = [p for p in clean_args[2:] if p != "-y"]
            if not pkgs:
                return False, "No se especificó ningún paquete para desinstalar con dnf."
            for p in pkgs:
                if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", p):
                    return False, f"Nombre de paquete dnf sospechoso: '{p}'."
                if is_critical_package(p):
                    return False, f"No se puede desinstalar el paquete crítico '{p}'."
            return True, ""
        return False, f"Subcomando dnf privilegiado no autorizado: '{subcmd}'."

    # 6. PACMAN (ARCH / MANJARO)
    if binary == "pacman":
        flag = clean_args[1]
        if flag in {"-Syu", "-Sy", "-Su", "-Syyu"}:
            return True, ""
        if flag.startswith("-S") and not flag.startswith("-Sc"):
            pkgs = [p for p in clean_args[2:] if p not in {"--noconfirm", "--needed"}]
            if not pkgs and flag in {"-Syu", "-Sy"}:
                return True, ""
            if not pkgs:
                return False, "No se especificó ningún paquete para instalar con pacman."
            for p in pkgs:
                if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", p):
                    return False, f"Nombre de paquete pacman sospechoso: '{p}'."
            return True, ""
        if flag.startswith("-R"):
            pkgs = [p for p in clean_args[2:] if p not in {"--noconfirm", "--nosave"}]
            if not pkgs:
                return False, "No se especificó ningún paquete para desinstalar con pacman."
            for p in pkgs:
                if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", p):
                    return False, f"Nombre de paquete pacman sospechoso: '{p}'."
                if is_critical_package(p):
                    return False, f"No se puede desinstalar el paquete crítico '{p}'."
            return True, ""
        if flag in {"-Sc", "-Scc"}:
            return True, ""
        return False, f"Operación pacman privilegiada no autorizada: '{flag}'."

    # 7. ZYPPER (OPENSUSE)
    if binary == "zypper":
        subcmd = clean_args[1].lower()
        if subcmd in {"update", "up"}:
            return True, ""
        if subcmd == "clean":
            return True, ""
        if subcmd in {"install", "in"}:
            pkgs = [p for p in clean_args[2:] if p not in {"-y", "--no-confirm"}]
            if not pkgs:
                return False, "No se especificó ningún paquete para instalar con zypper."
            for p in pkgs:
                if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", p):
                    return False, f"Nombre de paquete zypper sospechoso: '{p}'."
            return True, ""
        if subcmd in {"remove", "rm"}:
            pkgs = [p for p in clean_args[2:] if p not in {"-y", "--no-confirm"}]
            if not pkgs:
                return False, "No se especificó ningún paquete para desinstalar con zypper."
            for p in pkgs:
                if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", p):
                    return False, f"Nombre de paquete zypper sospechoso: '{p}'."
                if is_critical_package(p):
                    return False, f"No se puede desinstalar el paquete crítico '{p}'."
            return True, ""
        return False, f"Subcomando zypper privilegiado no autorizado: '{subcmd}'."

    # 8. ACTUALIZADOR DE FIRMWARE FWUPD
    if binary == "fwupdmgr":
        if clean_args[1:] in (["refresh", "--force"], ["update"]):
            return True, ""
        return False, "Acción de fwupdmgr no autorizada."

    return False, f"El binario '{binary}' no pertenece a la lista blanca de acciones del sistema."


def execute_privileged_action(
    argv: Sequence[str],
    timeout: int = 60,
    title: str = "",
    allow_terminal_fallback: bool = True,
) -> PrivilegedResult:
    """Ejecuta una acción privilegiada del sistema usando PolicyKit (pkexec) con fallback a terminal.

    1. Valida estrictamente los argumentos contra la lista blanca.
    2. Si PolicyKit gráfico está disponible, invoca pkexec para autenticar vía diálogo del escritorio.
    3. Si el usuario cancela la autenticación, se registra y se devuelve el estado cancelado amablemente.
    4. Si pkexec no está disponible o falla por ausencia de display, usa terminal interactiva con sudo.
    """
    clean_argv = [str(a).strip() for a in argv]
    valid, reason = validate_privileged_request(clean_argv)
    if not valid:
        return PrivilegedResult(
            success=False,
            mechanism="blocked",
            message=f"⛔ Acción del sistema bloqueada por política de seguridad: {reason}",
            command=clean_argv,
        )

    # Importación diferida para evitar dependencias circulares
    from src.core.tools import launch_in_terminal

    action_title = title or f"Acción del sistema: {clean_argv[0]}"

    # Intentar ejecutar con PolicyKit si hay entorno gráfico y pkexec
    if can_use_pkexec():
        try:
            cmd = ["pkexec", *clean_argv]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            if proc.returncode == 0:
                return PrivilegedResult(
                    success=True,
                    mechanism="pkexec",
                    returncode=0,
                    stdout=stdout,
                    stderr=stderr,
                    message="✅ Acción ejecutada y autorizada con éxito mediante PolicyKit.",
                    command=cmd,
                )

            # Código 126 en pkexec indica comúnmente que el usuario cerró o canceló el cuadro de diálogo
            if proc.returncode == 126 or "dismissed" in stderr.lower() or "not authorized" in stderr.lower():
                return PrivilegedResult(
                    success=False,
                    mechanism="cancelled",
                    returncode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    message="⛔ Autenticación de administrador cancelada o denegada por el usuario.",
                    command=cmd,
                )

            # Si pkexec falló con otro código (ej. no hay agente Polkit activo en esta sesión gráfica):
            if "no session for cookie" in stderr.lower() or "cannot open display" in stderr.lower():
                # Reintentar mediante terminal interactiva si está permitido
                if allow_terminal_fallback:
                    cmd_str = "sudo " + " ".join(shlex.quote(a) for a in clean_argv)
                    ok, msg = launch_in_terminal(cmd_str, title=action_title)
                    return PrivilegedResult(
                        success=ok,
                        mechanism="terminal",
                        message=(
                            f"Se abrió una terminal con 'sudo {clean_argv[0]}...' porque PolicyKit no tiene agente activo en esta sesión."
                            if ok else f"No se pudo abrir la terminal: {msg}"
                        ),
                        command=clean_argv,
                    )

            return PrivilegedResult(
                success=False,
                mechanism="failed",
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                message=f"La acción no pudo completarse ({proc.returncode}): {stderr or stdout}",
                command=cmd,
            )

        except subprocess.TimeoutExpired:
            return PrivilegedResult(
                success=False,
                mechanism="failed",
                message=f"La operación excedió el tiempo límite de espera ({timeout}s).",
                command=["pkexec", *clean_argv],
            )
        except Exception as exc:
            if not allow_terminal_fallback:
                return PrivilegedResult(
                    success=False,
                    mechanism="failed",
                    message=f"Error al ejecutar PolicyKit: {exc}",
                    command=["pkexec", *clean_argv],
                )

    # Fallback si no hay PolicyKit o se ejecuta en terminal / sin entorno gráfico
    if allow_terminal_fallback:
        cmd_str = "sudo " + " ".join(shlex.quote(a) for a in clean_argv)
        ok, msg = launch_in_terminal(cmd_str, title=action_title)
        return PrivilegedResult(
            success=ok,
            mechanism="terminal",
            message=(
                f"Se abrió una terminal interactiva para ejecutar `{clean_argv[0]} ...` con confirmación de sudo."
                if ok else f"No se pudo iniciar la terminal interactiva: {msg}"
            ),
            command=clean_argv,
        )

    cmd_quoted = "sudo " + " ".join(shlex.quote(a) for a in clean_argv)
    return PrivilegedResult(
        success=False,
        mechanism="failed",
        message=(
            "PolicyKit no está disponible en este entorno sin interfaz gráfica. "
            f"Ejecuta manualmente en tu terminal:\n```bash\n{cmd_quoted}\n```"
        ),
        command=clean_argv,
    )

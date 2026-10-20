"""Configurador guiado paso a paso adaptado a la distribución detectada."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any

from src.core.distro import detect_distro
from src.core.tools import launch_in_terminal


_CODEC_COMMANDS = {
    "apt": "sudo apt update && sudo apt install -y ffmpeg gstreamer1.0-libav gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly",
    "dnf": "sudo dnf install -y ffmpeg-free gstreamer1-plugins-good gstreamer1-plugins-bad-free",
    "pacman": "sudo pacman -S --needed ffmpeg gst-libav gst-plugins-good gst-plugins-bad gst-plugins-ugly",
    "zypper": "sudo zypper install -y ffmpeg gstreamer-plugins-good gstreamer-plugins-bad gstreamer-plugins-ugly",
}

_UPDATE_COMMANDS = {
    "apt": "sudo apt update && sudo apt upgrade",
    "dnf": "sudo dnf upgrade --refresh",
    "pacman": "sudo pacman -Syu",
    "zypper": "sudo zypper refresh && sudo zypper update",
}

_LOCALE_COMMANDS = {
    "apt": "localectl status; echo ''; locale; echo ''; sudo dpkg-reconfigure locales",
    "dnf": "localectl status; echo ''; locale",
    "pacman": "localectl status; echo ''; locale",
    "zypper": "localectl status; echo ''; locale",
}

_PROFILE_TOOLS: dict[str, dict[str, tuple[str, str]]] = {
    "daily": {
        "apt": ("vlc libreoffice keepassxc", "sudo apt install -y vlc libreoffice keepassxc"),
        "dnf": ("vlc libreoffice keepassxc", "sudo dnf install -y vlc libreoffice keepassxc"),
        "pacman": ("vlc libreoffice-fresh keepassxc", "sudo pacman -S --needed vlc libreoffice-fresh keepassxc"),
        "zypper": ("vlc libreoffice keepassxc", "sudo zypper install -y vlc libreoffice keepassxc"),
    },
    "study": {
        "apt": ("libreoffice thunderbird okular", "sudo apt install -y libreoffice thunderbird okular"),
        "dnf": ("libreoffice thunderbird okular", "sudo dnf install -y libreoffice thunderbird okular"),
        "pacman": ("libreoffice-fresh thunderbird okular", "sudo pacman -S --needed libreoffice-fresh thunderbird okular"),
        "zypper": ("libreoffice thunderbird okular", "sudo zypper install -y libreoffice thunderbird okular"),
    },
    "development": {
        "apt": ("git python3-pip python3-venv build-essential curl", "sudo apt install -y git python3-pip python3-venv build-essential curl"),
        "dnf": ("git python3-pip gcc make curl", "sudo dnf install -y git python3-pip gcc make curl"),
        "pacman": ("git python-pip base-devel curl", "sudo pacman -S --needed git python-pip base-devel curl"),
        "zypper": ("git python3-pip gcc make curl", "sudo zypper install -y git python3-pip gcc make curl"),
    },
    "gaming": {
        "apt": ("steam lutris gamemode", "sudo apt install -y steam lutris gamemode"),
        "dnf": ("steam lutris gamemode", "sudo dnf install -y steam lutris gamemode"),
        "pacman": ("steam lutris gamemode", "sudo pacman -S --needed steam lutris gamemode"),
        "zypper": ("steam lutris gamemode", "sudo zypper install -y steam lutris gamemode"),
    },
}

_PROFILE_META: dict[str, dict[str, str]] = {
    "daily": {
        "title": "uso diario",
        "category": "internet",
        "tools_title": "Instala aplicaciones esenciales de uso diario",
    },
    "study": {
        "title": "estudio",
        "category": "office",
        "tools_title": "Instala ofimática y herramientas de estudio",
    },
    "development": {
        "title": "desarrollo",
        "category": "development",
        "tools_title": "Prepara Git, compiladores y entorno de programación",
    },
    "gaming": {
        "title": "juegos",
        "category": "games",
        "tools_title": "Instala plataformas de juegos y optimización (GameMode)",
    },
}


def _run(args: list[str], timeout: int = 6) -> tuple[int | None, str]:
    if not args or shutil.which(args[0]) is None:
        return None, ""
    try:
        result = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
        return result.returncode, (result.stdout or result.stderr).strip()
    except (OSError, subprocess.SubprocessError):
        return None, ""


def _detect_codecs_status(manager: str) -> dict[str, str]:
    has_ffmpeg = shutil.which("ffmpeg") is not None
    has_gst = shutil.which("gst-inspect-1.0") is not None or shutil.which("gst-launch-1.0") is not None
    cmd = _CODEC_COMMANDS.get(manager, _CODEC_COMMANDS["apt"])
    if has_ffmpeg and has_gst:
        return {
            "status": "ready",
            "badge": "Instalados",
            "detail": f"Se detectaron FFmpeg y herramientas GStreamer. Comando para {manager.upper()}: {cmd}",
            "command": cmd,
        }
    if has_ffmpeg or has_gst:
        found = "FFmpeg" if has_ffmpeg else "GStreamer"
        return {
            "status": "partial",
            "badge": "Parcial",
            "detail": f"Se detectó {found}, pero puedes completar los codecs de audio/video con {manager.upper()}.",
            "command": cmd,
        }
    return {
        "status": "pending",
        "badge": "Pendiente",
        "detail": f"Aún no se detecta FFmpeg en este equipo. Instala los codecs multimedia recomendados para {manager.upper()}.",
        "command": cmd,
    }


def _detect_locale_status(manager: str) -> dict[str, str]:
    lang = (os.environ.get("LANG") or os.environ.get("LC_ALL") or "").strip()
    keymap = ""
    code, output = _run(["localectl", "status"])
    if code == 0 and output:
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith(("x11 layout:", "vc keymap:")):
                keymap = stripped.split(":", 1)[1].strip()
                if keymap and keymap != "(unset)":
                    break
    cmd = _LOCALE_COMMANDS.get(manager, _LOCALE_COMMANDS["apt"])
    if lang and lang.upper() not in {"C", "POSIX"}:
        extra = f" · Teclado: {keymap}" if keymap else ""
        return {
            "status": "ready",
            "badge": f"Activo ({lang.split('.')[0]})",
            "detail": f"Idioma del sistema detectado: {lang}{extra}. Puedes verificar o ajustar variantes regionales.",
            "command": cmd,
        }
    return {
        "status": "pending",
        "badge": "Por configurar",
        "detail": "El idioma regional aparece en modo básico (C/POSIX). Configura tu idioma y distribución de teclado.",
        "command": cmd,
    }


def _collect_driver_items(distro_id: str, manager: str) -> list[dict[str, str]]:
    """Recopila dispositivos gráficos y de red junto con el controlador de kernel en uso."""
    items: list[dict[str, str]] = []
    code, output = _run(["lspci", "-nnk"], timeout=5)
    if code == 0 and output:
        current_kind = ""
        current_device = ""
        current_driver = ""
        current_modules = ""

        def _flush() -> None:
            if not current_device:
                return
            drv = current_driver or "Sin módulo activo detectado"
            mods = f" (módulos: {current_modules})" if current_modules and current_modules != current_driver else ""
            status = "ok" if current_driver else "warning"
            items.append({
                "kind": current_kind,
                "device": current_device,
                "driver": f"{drv}{mods}",
                "status": status,
            })

        for raw_line in output.splitlines():
            if not raw_line.startswith(("\t", " ")):
                _flush()
                current_kind = ""
                current_device = ""
                current_driver = ""
                current_modules = ""
                if re.search(r"VGA compatible controller|3D controller|Display controller", raw_line, re.IGNORECASE):
                    current_kind = "Gráficos (GPU)"
                    current_device = re.sub(r"^[^:]+:\s*", "", raw_line.strip())[:110]
                elif re.search(r"Network controller|Ethernet controller", raw_line, re.IGNORECASE):
                    current_kind = "Red / Wi-Fi"
                    current_device = re.sub(r"^[^:]+:\s*", "", raw_line.strip())[:110]
            elif current_device:
                stripped = raw_line.strip()
                if stripped.lower().startswith("kernel driver in use:"):
                    current_driver = stripped.split(":", 1)[1].strip()
                elif stripped.lower().startswith("kernel modules:"):
                    current_modules = stripped.split(":", 1)[1].strip()
        _flush()

    if not items:
        items.append({
            "kind": "Hardware del sistema",
            "device": "Dispositivos gráficos y de red gestionados por el kernel Linux",
            "driver": f"Gestor recomendado: {manager.upper()}",
            "status": "ok",
        })
    return items


def _detect_drivers_status(distro_id: str, manager: str) -> dict[str, Any]:
    gpu_model = ""
    code, output = _run(["lspci"])
    if code == 0 and output:
        for line in output.splitlines():
            if re.search(r"VGA compatible controller|3D controller|Display controller", line, re.IGNORECASE):
                gpu_model = re.sub(r"^[^:]+:\s*", "", line.strip())[:100]
                break

    if shutil.which("ubuntu-drivers") and distro_id in {"ubuntu", "linuxmint", "pop"}:
        cmd = "ubuntu-drivers devices; echo ''; lspci -nnk | grep -EA3 'VGA|3D|Display|Network'"
    elif shutil.which("mhwd"):
        cmd = "mhwd -l; echo ''; lspci -nnk | grep -EA3 'VGA|3D|Display|Network'"
    elif manager == "dnf":
        cmd = "lspci -nnk | grep -EA3 'VGA|3D|Display|Network'; echo ''; dnf list installed '*nvidia*' '*mesa*' '*firmware*'"
    elif manager == "pacman":
        cmd = "lspci -nnk | grep -EA3 'VGA|3D|Display|Network'; echo ''; pacman -Qs 'mesa|nvidia|vulkan|firmware'"
    elif manager == "zypper":
        cmd = "lspci -nnk | grep -EA3 'VGA|3D|Display|Network'; echo ''; zypper se -i mesa kernel-firmware"
    else:
        cmd = "lspci -nnk | grep -EA3 'VGA|3D|Display|Network'"

    if gpu_model:
        return {
            "status": "ready",
            "badge": "GPU detectada",
            "detail": f"Gráficos detectados: {gpu_model}. Revisa el módulo activo y las recomendaciones de tu distribución.",
            "command": cmd,
        }
    return {
        "status": "partial",
        "badge": "Revisar hardware",
        "detail": "Comprueba los controladores de gráficos y red recomendados para tu distribución.",
        "command": cmd,
    }


def _detect_firewall_status(manager: str) -> dict[str, str]:
    if shutil.which("ufw"):
        code, state = _run(["systemctl", "is-active", "ufw"])
        active = code == 0 and state.strip() == "active"
        cmd = "sudo ufw status verbose; sudo ufw enable"
        return {
            "status": "ready" if active else "pending",
            "badge": "UFW activo" if active else "UFW inactivo",
            "detail": "El servicio UFW está activo." if active else "UFW está disponible en este equipo. Puedes activarlo para proteger conexiones entrantes.",
            "command": cmd,
        }
    if shutil.which("firewall-cmd"):
        code, state = _run(["systemctl", "is-active", "firewalld"])
        active = code == 0 and state.strip() == "active"
        cmd = "sudo systemctl enable --now firewalld && sudo firewall-cmd --state"
        return {
            "status": "ready" if active else "pending",
            "badge": "firewalld activo" if active else "firewalld inactivo",
            "detail": "El servicio firewalld está activo." if active else "firewalld está disponible. Puedes habilitarlo e iniciarlo con confirmación.",
            "command": cmd,
        }
    install_fw = {
        "apt": "sudo apt install -y ufw && sudo ufw enable",
        "dnf": "sudo dnf install -y firewalld && sudo systemctl enable --now firewalld",
        "pacman": "sudo pacman -S --needed ufw && sudo systemctl enable --now ufw && sudo ufw enable",
        "zypper": "sudo zypper install -y firewalld && sudo systemctl enable --now firewalld",
    }.get(manager, "sudo ufw status")
    return {
        "status": "pending",
        "badge": "No detectado",
        "detail": f"No se detectó UFW ni firewalld activo. Puedes instalar y activar el cortafuegos con {manager.upper()}.",
        "command": install_fw,
    }


def get_setup_plan(profile: str = "daily") -> dict[str, Any]:
    """Construye el plan del configurador guiado adaptado a la distribución y perfil."""
    selected_profile = profile if profile in _PROFILE_META else "daily"
    meta = _PROFILE_META[selected_profile]
    distro = detect_distro()
    distro_id = getattr(distro, "id", "") or getattr(distro, "distro_id", "") or "linux"
    distro_version = getattr(distro, "version_id", "") or getattr(distro, "version", "") or ""
    family_raw = getattr(distro, "family", "generic")
    distro_family = getattr(family_raw, "value", str(family_raw))
    manager = distro.native_package_manager if distro.native_package_manager in _UPDATE_COMMANDS else "apt"

    update_cmd = _UPDATE_COMMANDS[manager]
    codecs = _detect_codecs_status(manager)
    locale_info = _detect_locale_status(manager)
    drivers = _detect_drivers_status(distro_id, manager)
    firewall = _detect_firewall_status(manager)
    pkg_list, tools_cmd = _PROFILE_TOOLS[selected_profile].get(manager, _PROFILE_TOOLS[selected_profile]["apt"])

    steps = [
        {
            "id": "updates",
            "icon": "sync",
            "title": f"Actualiza {distro.pretty_name} ({manager.upper()})",
            "detail": f"Sincroniza repositorios e instala parches de seguridad con el gestor nativo ({update_cmd}).",
            "status": "ready",
            "badge": manager.upper(),
            "command": update_cmd,
            "action": "run:update_distro",
            "actionLabel": f"Actualizar con {manager.upper()}",
            "secondaryAction": "update_system",
            "secondaryLabel": "Guía de actualización",
        },
        {
            "id": "codecs",
            "icon": "game",
            "title": "Codecs multimedia (audio y video)",
            "detail": codecs["detail"],
            "status": codecs["status"],
            "badge": codecs["badge"],
            "command": codecs["command"],
            "action": "run:install_codecs",
            "actionLabel": "Instalar codecs multimedia",
            "secondaryAction": "apps",
            "secondaryCategory": "multimedia",
            "secondaryLabel": "Catálogo multimedia",
        },
        {
            "id": "locale",
            "icon": "language",
            "title": "Idioma, formato regional y teclado",
            "detail": locale_info["detail"],
            "status": locale_info["status"],
            "badge": locale_info["badge"],
            "command": locale_info["command"],
            "action": "run:configure_locale",
            "actionLabel": "Revisar idioma en terminal",
        },
        {
            "id": "drivers",
            "icon": "settings",
            "title": "Controladores gráficos y de red",
            "detail": drivers["detail"],
            "status": drivers["status"],
            "badge": drivers["badge"],
            "command": drivers["command"],
            "action": "run:check_drivers",
            "actionLabel": "Comprobar controladores",
            "secondaryAction": "drivers_manager",
            "secondaryLabel": "Consultar al asistente",
        },
        {
            "id": "tools",
            "icon": "package",
            "title": meta["tools_title"],
            "detail": f"Paquetes recomendados en {distro.pretty_name} para {meta['title']}: {pkg_list}.",
            "status": "ready",
            "badge": f"Perfil {meta['title']}",
            "command": tools_cmd,
            "action": "run:install_profile_tools",
            "actionLabel": f"Instalar base ({pkg_list.split()[0]}…)",
            "secondaryAction": "apps",
            "secondaryCategory": meta["category"],
            "secondaryLabel": "Explorar catálogo visual",
        },
        {
            "id": "firewall",
            "icon": "shield",
            "title": "Cortafuegos y seguridad básica",
            "detail": firewall["detail"],
            "status": firewall["status"],
            "badge": firewall["badge"],
            "command": firewall["command"],
            "action": "run:configure_firewall",
            "actionLabel": "Configurar cortafuegos",
        },
        {
            "id": "backup",
            "icon": "backup",
            "title": "Configura tu primera copia de seguridad",
            "detail": "Elige qué carpetas personales respaldar o configura instantáneas del sistema con Timeshift.",
            "status": "ready",
            "badge": "Protección",
            "command": "",
            "action": "backup_manager",
            "actionLabel": "Abrir gestor de respaldos",
        },
    ]

    return {
        "success": True,
        "profile": selected_profile,
        "profile_title": meta["title"],
        "distro": {
            "id": distro_id,
            "name": distro.pretty_name,
            "version": distro_version,
            "family": distro_family,
            "package_manager": manager,
            "available_package_managers": list(distro.available_package_managers),
        },
        "steps": steps,
    }


def run_setup_action(action_id: str, profile: str = "daily") -> dict[str, Any]:
    """Ejecuta o abre en terminal el paso de configuración solicitado para la distribución actual."""
    clean_action = (action_id or "").strip()
    plan = get_setup_plan(profile)
    manager = plan["distro"]["package_manager"]
    distro_id = plan["distro"]["id"]
    selected_profile = plan["profile"]

    actions_map: dict[str, tuple[str, str]] = {
        "update_distro": (
            _UPDATE_COMMANDS[manager],
            f"Actualizar {plan['distro']['name']} — LinuxMate AI",
        ),
        "install_codecs": (
            _CODEC_COMMANDS[manager],
            "Instalar codecs multimedia — LinuxMate AI",
        ),
        "configure_locale": (
            _LOCALE_COMMANDS[manager],
            "Idioma y configuración regional — LinuxMate AI",
        ),
        "check_drivers": (
            _detect_drivers_status(distro_id, manager)["command"],
            "Comprobar controladores — LinuxMate AI",
        ),
        "install_profile_tools": (
            _PROFILE_TOOLS[selected_profile].get(manager, _PROFILE_TOOLS[selected_profile]["apt"])[1],
            f"Herramientas para {plan['profile_title']} — LinuxMate AI",
        ),
        "configure_firewall": (
            _detect_firewall_status(manager)["command"],
            "Configurar cortafuegos — LinuxMate AI",
        ),
    }

    if clean_action not in actions_map:
        return {"success": False, "message": "Acción del configurador no reconocida."}

    command, title = actions_map[clean_action]
    driver_items = _collect_driver_items(distro_id, manager) if clean_action == "check_drivers" else []
    ok, message = launch_in_terminal(command, title)
    if ok:
        return {
            "success": True,
            "command": command,
            "driver_report": driver_items,
            "message": (
                "Controladores comprobados y terminal abierta con el detalle completo."
                if clean_action == "check_drivers"
                else "Se abrió una terminal con el paso seleccionado. Revisa el comando y confirma cuando estés listo."
            ),
        }
    if clean_action == "check_drivers" and driver_items:
        return {
            "success": True,
            "command": command,
            "driver_report": driver_items,
            "message": "Se comprobaron los controladores locales de gráficos y red.",
        }
    return {"success": False, "message": f"No se pudo abrir la terminal: {message}"}

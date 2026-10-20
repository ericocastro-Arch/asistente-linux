"""Detección de distribución Linux y perfiles de gestores de paquetes.

Permite que LinuxMate adapte automáticamente sus comandos, diagnósticos y sugerencias
según la distribución del usuario:
- Familia Debian (Ubuntu, Debian, Linux Mint, Pop!_OS) → apt / dpkg
- Familia Fedora / RedHat (Fedora, RHEL, CentOS, Rocky Linux) → dnf / rpm
- Familia Arch (Arch Linux, Manjaro, EndeavourOS) → pacman
- Familia openSUSE (Leap, Tumbleweed) → zypper / rpm
- Gestores universales → Flatpak y Snap
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class DistroFamily(str, Enum):
    DEBIAN = "debian"
    FEDORA = "fedora"
    ARCH = "arch"
    SUSE = "suse"
    GENERIC = "generic"


@dataclass
class DistroInfo:
    """Información identificada de la distribución del sistema operativo."""
    id: str
    name: str
    pretty_name: str
    version_id: str
    id_like: str
    family: DistroFamily
    native_package_manager: str
    available_package_managers: List[str] = field(default_factory=list)


def parse_os_release(content: str) -> Dict[str, str]:
    """Parsea el contenido en formato clave=valor estándar de /etc/os-release."""
    data: Dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        data[key] = val
    return data


def _identify_family(distro_id: str, id_like: str) -> DistroFamily:
    """Clasifica la distribución en su familia principal."""
    tokens = {distro_id.lower(), *id_like.lower().split()}
    if any(t in tokens for t in ("debian", "ubuntu", "mint", "pop", "elementary", "kali", "raspbian")):
        return DistroFamily.DEBIAN
    if any(t in tokens for t in ("fedora", "rhel", "centos", "rocky", "almalinux")):
        return DistroFamily.FEDORA
    if any(t in tokens for t in ("arch", "manjaro", "endeavouros", "garuda", "artix")):
        return DistroFamily.ARCH
    if any(t in tokens for t in ("suse", "opensuse", "opensuse-leap", "opensuse-tumbleweed", "sle")):
        return DistroFamily.SUSE
    return DistroFamily.GENERIC


def _native_manager_for_family(family: DistroFamily) -> str:
    """Devuelve el gestor de paquetes nativo recomendado para la familia."""
    mapping = {
        DistroFamily.DEBIAN: "apt",
        DistroFamily.FEDORA: "dnf",
        DistroFamily.ARCH: "pacman",
        DistroFamily.SUSE: "zypper",
        DistroFamily.GENERIC: "apt",
    }
    return mapping.get(family, "apt")


def get_available_package_managers() -> List[str]:
    """Detecta todos los gestores de paquetes instalados en el sistema."""
    candidates = ["apt", "dnf", "pacman", "zypper", "flatpak", "snap"]
    return [c for c in candidates if shutil.which(c)]


def detect_distro(os_release_path: Optional[Path] = None) -> DistroInfo:
    """Detecta la distribución de Linux actual leyendo /etc/os-release o /usr/lib/os-release."""
    path = os_release_path
    if path is None:
        if Path("/etc/os-release").is_file():
            path = Path("/etc/os-release")
        elif Path("/usr/lib/os-release").is_file():
            path = Path("/usr/lib/os-release")

    raw_data: Dict[str, str] = {}
    if path and path.is_file():
        try:
            raw_data = parse_os_release(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            pass

    distro_id = raw_data.get("ID", "linux").lower()
    distro_name = raw_data.get("NAME", "Linux")
    pretty_name = raw_data.get("PRETTY_NAME", f"{distro_name} Linux")
    version_id = raw_data.get("VERSION_ID", "")
    id_like = raw_data.get("ID_LIKE", "").lower()

    family = _identify_family(distro_id, id_like)
    native_pm = _native_manager_for_family(family)

    # Si el gestor primario de la familia no está en PATH, usar el primer nativo que exista
    available = get_available_package_managers()
    if native_pm not in available:
        for fallback in ("apt", "dnf", "pacman", "zypper", "flatpak", "snap"):
            if fallback in available:
                native_pm = fallback
                break

    return DistroInfo(
        id=distro_id,
        name=distro_name,
        pretty_name=pretty_name,
        version_id=version_id,
        id_like=id_like,
        family=family,
        native_package_manager=native_pm,
        available_package_managers=available,
    )


def get_active_package_manager(preference: Optional[str] = None) -> str:
    """Devuelve el gestor de paquetes a usar según la preferencia configurada o la distro."""
    pref = (preference or os.environ.get("PACKAGE_PREFERENCE", "")).strip().lower()
    available = get_available_package_managers()

    if pref and pref in available:
        return pref

    info = detect_distro()
    return info.native_package_manager


@dataclass
class PackageCommandProfile:
    """Comandos estructurados para un gestor de paquetes específico."""
    manager: str
    search: Callable[[str], str]
    install: Callable[[str, bool], str]
    remove: Callable[[str], str]
    update: str
    clean: str
    is_installed_probe: Callable[[str], List[str]]


def get_package_profile(manager: Optional[str] = None) -> PackageCommandProfile:
    """Construye el perfil de comandos para el gestor de paquetes especificado o activo."""
    mgr = (manager or get_active_package_manager()).lower().strip()

    if mgr == "dnf":
        return PackageCommandProfile(
            manager="dnf",
            search=lambda q: f"dnf search {shlex.quote(q)} | head -25",
            install=lambda pkg, y=True: f"sudo dnf install {'-y ' if y else ''}{shlex.quote(pkg)}",
            remove=lambda pkg: f"sudo dnf remove -y {shlex.quote(pkg)}",
            update="sudo dnf upgrade -y",
            clean="sudo dnf clean all",
            is_installed_probe=lambda pkg: ["rpm", "-q", pkg],
        )

    if mgr == "pacman":
        return PackageCommandProfile(
            manager="pacman",
            search=lambda q: f"pacman -Ss {shlex.quote(q)} | head -25",
            install=lambda pkg, y=True: f"sudo pacman -S {'--noconfirm ' if y else ''}{shlex.quote(pkg)}",
            remove=lambda pkg: f"sudo pacman -R --noconfirm {shlex.quote(pkg)}",
            update="sudo pacman -Syu --noconfirm",
            clean="sudo pacman -Sc --noconfirm",
            is_installed_probe=lambda pkg: ["pacman", "-Q", pkg],
        )

    if mgr == "zypper":
        return PackageCommandProfile(
            manager="zypper",
            search=lambda q: f"zypper search {shlex.quote(q)} | head -25",
            install=lambda pkg, y=True: f"sudo zypper install {'-y ' if y else ''}{shlex.quote(pkg)}",
            remove=lambda pkg: f"sudo zypper remove -y {shlex.quote(pkg)}",
            update="sudo zypper update -y",
            clean="sudo zypper clean",
            is_installed_probe=lambda pkg: ["rpm", "-q", pkg],
        )

    if mgr == "flatpak":
        return PackageCommandProfile(
            manager="flatpak",
            search=lambda q: f"flatpak search {shlex.quote(q)} | head -25",
            install=lambda pkg, y=True: f"flatpak install -y flathub {shlex.quote(pkg)}",
            remove=lambda pkg: f"flatpak uninstall -y {shlex.quote(pkg)}",
            update="flatpak update -y",
            clean="flatpak uninstall --unused -y",
            is_installed_probe=lambda pkg: ["flatpak", "info", pkg],
        )

    if mgr == "snap":
        return PackageCommandProfile(
            manager="snap",
            search=lambda q: f"snap find {shlex.quote(q)} | head -25",
            install=lambda pkg, y=True: f"sudo snap install {shlex.quote(pkg)}",
            remove=lambda pkg: f"sudo snap remove {shlex.quote(pkg)}",
            update="sudo snap refresh",
            clean="sudo snap refresh",
            is_installed_probe=lambda pkg: ["snap", "list", pkg],
        )

    # Por defecto: apt (Debian/Ubuntu/Mint)
    return PackageCommandProfile(
        manager="apt",
        search=lambda q: f"apt-cache search {shlex.quote(q)} | head -25",
        install=lambda pkg, y=True: f"sudo apt install {'-y ' if y else ''}{shlex.quote(pkg)}",
        remove=lambda pkg: f"sudo apt remove {shlex.quote(pkg)}",
        update="sudo apt update && sudo apt upgrade -y",
        clean="sudo apt autoremove --purge -y && sudo apt clean",
        is_installed_probe=lambda pkg: ["dpkg-query", "-W", "-f=${Status}", pkg],
    )

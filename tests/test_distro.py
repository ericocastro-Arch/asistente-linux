"""Pruebas unitarias para perfiles de distribución y compatibilidad multi-distro."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from src.core import distro, tools, settings_manager
from src.core.agent import _build_system_context


OS_RELEASE_UBUNTU = """\
NAME="Ubuntu"
VERSION="24.04 LTS (Noble Numbat)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 24.04 LTS"
VERSION_ID="24.04"
"""

OS_RELEASE_FEDORA = """\
NAME="Fedora Linux"
VERSION="40 (Workstation Edition)"
ID=fedora
ID_LIKE=""
PRETTY_NAME="Fedora Linux 40 (Workstation Edition)"
VERSION_ID="40"
"""

OS_RELEASE_ARCH = """\
NAME="Arch Linux"
PRETTY_NAME="Arch Linux"
ID=arch
BUILD_ID=rolling
"""

OS_RELEASE_MANJARO = """\
NAME="Manjaro Linux"
ID=manjaro
ID_LIKE=arch
PRETTY_NAME="Manjaro Linux"
"""

OS_RELEASE_OPENSUSE = """\
NAME="openSUSE Tumbleweed"
ID="opensuse-tumbleweed"
ID_LIKE="opensuse suse"
PRETTY_NAME="openSUSE Tumbleweed"
"""


def test_parse_os_release():
    """Valida el parseo correcto de variables en /etc/os-release."""
    data = distro.parse_os_release(OS_RELEASE_UBUNTU)
    assert data["ID"] == "ubuntu"
    assert data["PRETTY_NAME"] == "Ubuntu 24.04 LTS"
    assert data["ID_LIKE"] == "debian"


@pytest.mark.parametrize("content,expected_family,expected_pm", [
    (OS_RELEASE_UBUNTU, distro.DistroFamily.DEBIAN, "apt"),
    (OS_RELEASE_FEDORA, distro.DistroFamily.FEDORA, "dnf"),
    (OS_RELEASE_ARCH, distro.DistroFamily.ARCH, "pacman"),
    (OS_RELEASE_MANJARO, distro.DistroFamily.ARCH, "pacman"),
    (OS_RELEASE_OPENSUSE, distro.DistroFamily.SUSE, "zypper"),
])
def test_detect_distro_families(tmp_path, content, expected_family, expected_pm, monkeypatch):
    """Detecta correctamente la familia de la distro y su gestor nativo."""
    release_file = tmp_path / "os-release"
    release_file.write_text(content, encoding="utf-8")

    # Simular que el binario esperado existe en PATH
    monkeypatch.setattr(distro, "get_available_package_managers", lambda: [expected_pm, "flatpak"])

    info = distro.detect_distro(release_file)
    assert info.family == expected_family
    assert info.native_package_manager == expected_pm
    assert "flatpak" in info.available_package_managers


@pytest.mark.parametrize("manager,expected_search,expected_update", [
    ("apt", "apt-cache search", "sudo apt update && sudo apt upgrade -y"),
    ("dnf", "dnf search", "sudo dnf upgrade -y"),
    ("pacman", "pacman -Ss", "sudo pacman -Syu --noconfirm"),
    ("zypper", "zypper search", "sudo zypper update -y"),
    ("flatpak", "flatpak search", "flatpak update -y"),
    ("snap", "snap find", "sudo snap refresh"),
])
def test_package_command_profiles(manager, expected_search, expected_update):
    """Comprueba que cada perfil genera los comandos sintácticamente correctos."""
    profile = distro.get_package_profile(manager)
    assert profile.manager == manager
    assert expected_search in profile.search("vlc")
    assert "vlc" in profile.search("vlc")
    assert profile.update == expected_update


def test_tool_search_package_adapts_to_distro(monkeypatch):
    """tool_search_package utiliza el perfil de la distribución activa."""
    called_cmds = []

    def mock_silent(cmd):
        called_cmds.append(cmd)
        return "```\npaquete-prueba - descripcion\n```"

    monkeypatch.setattr(tools, "tool_run_command_silent", mock_silent)
    monkeypatch.setattr(distro, "get_active_package_manager", lambda: "dnf")

    out = tools.tool_search_package("htop")
    assert "Resultados para 'htop' (dnf)" in out
    assert any("dnf search" in c and "htop" in c for c in called_cmds)


def test_tool_update_system_adapts_to_distro(monkeypatch):
    """tool_update_system invoca el comando de actualización apropiado."""
    launched = []
    monkeypatch.setattr(tools, "launch_in_terminal", lambda cmd, title: launched.append((cmd, title)) or (True, "ok"))
    monkeypatch.setattr(distro, "get_active_package_manager", lambda: "pacman")

    out = tools.tool_update_system(mode="terminal")
    assert "pacman -Syu" in out
    assert launched[0][0] == "sudo pacman -Syu --noconfirm"


def test_system_context_contains_distro_info(monkeypatch, tmp_path):
    """_build_system_context incluye nombre y familia de la distro en el prompt."""
    fake_release = tmp_path / "os-release"
    fake_release.write_text(OS_RELEASE_FEDORA, encoding="utf-8")

    fedora_info = distro.detect_distro(fake_release)
    monkeypatch.setattr(distro, "detect_distro", lambda *args, **kwargs: fedora_info)
    monkeypatch.setattr(distro, "get_active_package_manager", lambda: "dnf")

    context = _build_system_context()
    assert "Fedora Linux 40" in context
    assert "familia fedora" in context
    assert "dnf" in context


def test_settings_distro_metadata():
    """settings_manager.get_settings incluye el bloque 'distro' y lista gestores."""
    settings = settings_manager.get_settings()
    assert "distro" in settings
    assert "name" in settings["distro"]
    assert "family" in settings["distro"]
    assert "native_package_manager" in settings["distro"]

    diag = settings_manager.get_system_diagnostics()
    assert "distro_name" in diag
    assert "distro_family" in diag
    assert "native_package_manager" in diag
    assert "apt" in diag
    assert "dnf" in diag
    assert "pacman" in diag
    assert "zypper" in diag

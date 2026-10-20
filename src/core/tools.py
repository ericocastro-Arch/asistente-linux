# Definicion y ejecutor de herramientas del sistema Linux (Ubuntu) para el Agente.

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.core import backups
from src.core.diagnostic_catalog import DIAGNOSTICS, catalog_description, run_diagnostic
from src.core.policy import authorize_tool
from src.core.security import assess_command, assess_file_read, assess_file_write, is_safe_name
from src.core.storage import log_tool_run


PACKAGE_ALIASES = {
    "obs": ("apt", "obs-studio", "OBS Studio"),
    "obs studio": ("apt", "obs-studio", "OBS Studio"),
    "vs code": ("apt", "code", "Visual Studio Code"),
    "visual code": ("apt", "code", "Visual Studio Code"),
    "visual studio code": ("apt", "code", "Visual Studio Code"),
    "vscode": ("apt", "code", "Visual Studio Code"),
    "chrome": ("apt", "google-chrome-stable", "Google Chrome"),
    "google chrome": ("apt", "google-chrome-stable", "Google Chrome"),
    "spotify": ("apt", "spotify-client", "Spotify"),
    "trilium": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium notes": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium-notes": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
    "proton": ("snap", "proton-vpn", "Proton VPN"),
    "proton vpn": ("snap", "proton-vpn", "Proton VPN"),
    "protonvpn": ("snap", "proton-vpn", "Proton VPN"),
}

SOURCE_PACKAGE_ALIASES = {
    "flatpak": {
        "trilium": ("org.triliumnotes.Trilium", "Trilium Notes"),
        "trilium notes": ("org.triliumnotes.Trilium", "Trilium Notes"),
        "trilium-notes": ("org.triliumnotes.Trilium", "Trilium Notes"),
        "com.github.zadam.trilium": ("com.github.zadam.trilium", "Trilium Notes"),
        "proton": ("com.protonvpn.www", "Proton VPN"),
        "proton vpn": ("com.protonvpn.www", "Proton VPN"),
        "protonvpn": ("com.protonvpn.www", "Proton VPN"),
    },
    "snap": {
        "trilium": ("trilium-notes", "Trilium Notes"),
        "trilium notes": ("trilium-notes", "Trilium Notes"),
        "trilium-notes": ("trilium-notes", "Trilium Notes"),
        "proton": ("proton-vpn", "Proton VPN"),
        "proton vpn": ("proton-vpn", "Proton VPN"),
        "protonvpn": ("proton-vpn", "Proton VPN"),
        "proton-vpn": ("proton-vpn", "Proton VPN"),
    },
}

INSTALL_SOURCE_ORDER = ("apt", "flatpak", "snap", "dnf", "pacman", "zypper")
LAST_INSTALLED_APP: dict[str, str] = {}

APP_ALIASES = {
    "trilium": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium notes": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium-notes": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
}

CRITICAL_SYSTEM_PACKAGES = {
    "apt",
    "base-files",
    "bash",
    "coreutils",
    "dbus",
    "dpkg",
    "gnome-shell",
    "grub",
    "grub2",
    "libc6",
    "linux",
    "network-manager",
    "openssh-client",
    "python3",
    "sudo",
    "systemd",
    "ubuntu-desktop",
    "ubuntu-minimal",
    "ubuntu-standard",
    "xorg",
}

CRITICAL_SYSTEM_PREFIXES = (
    "firmware-",
    "grub-",
    "initramfs-",
    "linux-base",
    "linux-firmware",
    "linux-generic",
    "linux-headers",
    "linux-image",
    "linux-modules",
    "systemd",
    "ubuntu-drivers",
)

CRITICAL_SYSTEM_SERVICES = {
    "accounts-daemon", "dbus", "display-manager", "gdm", "gdm3", "lightdm",
    "network-manager", "networkmanager", "polkit", "sddm", "ssh", "sshd",
    "systemd-journald", "systemd-logind", "systemd-networkd",
    "systemd-networkd-wait-online", "systemd-resolved", "systemd-udevd", "udev",
    "wpa_supplicant",
}


def is_critical_system_service(service_name: str) -> bool:
    """Evita detener servicios necesarios para iniciar, administrar o conectar el equipo."""
    name = service_name.strip().lower()
    if name.endswith(".service"):
        name = name[:-8]
    return name in CRITICAL_SYSTEM_SERVICES or name.startswith("user@")


def _quote(value: str) -> str:
    return shlex.quote(value.strip())


def is_critical_system_package(package_name: str) -> bool:
    """Detecta paquetes que no deben desinstalarse desde una accion guiada simple."""
    package = package_name.strip().lower()
    if package in CRITICAL_SYSTEM_PACKAGES:
        return True
    return any(package.startswith(prefix) for prefix in CRITICAL_SYSTEM_PREFIXES)


def parse_package_source_request(package_name: str, default_source: str = "auto") -> tuple[str, str]:
    """Extrae una fuente opcional como apt/snap/flatpak y deja un nombre seguro."""
    source = default_source
    name = package_name.strip()
    match = re.match(
        r"^(?:por|con|desde|usando|en)?\s*(apt|apt-get|dnf|pacman|zypper|snap|flatpak|desktop|local|lanzador)\s+(.+)$",
        name,
        flags=re.IGNORECASE,
    )
    if match:
        requested_source = match.group(1).lower()
        if requested_source == "apt-get":
            source = "apt"
        elif requested_source in {"local", "lanzador"}:
            source = "desktop"
        else:
            source = requested_source
        name = match.group(2).strip()
    return source, name


def build_uninstall_args(package_name: str, source: str = "apt", privilege_tool: str = "pkexec") -> list[str]:
    """Genera argumentos seguros para desinstalar una aplicacion instalada."""
    source, package = parse_package_source_request(package_name, source)
    package = package.replace(" ", "-") if source in {"apt", "dnf", "pacman", "zypper", "snap"} else package
    valid_sources = {"apt", "dnf", "pacman", "zypper", "snap", "flatpak"}
    if source not in valid_sources:
        raise ValueError("Metodo de desinstalacion no reconocido. Usa apt, dnf, pacman, zypper, snap o flatpak.")
    if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", package):
        raise ValueError("Nombre de paquete invalido. Usa el nombre exacto, sin simbolos de shell.")
    if is_critical_system_package(package):
        raise ValueError(
            f"'{package}' parece ser parte critica del sistema operativo. "
            "No lo desinstalo desde el asistente."
        )
    if source == "apt":
        return [privilege_tool, "apt", "remove", "-y", package]
    if source == "dnf":
        return [privilege_tool, "dnf", "remove", "-y", package]
    if source == "pacman":
        return [privilege_tool, "pacman", "-R", "--noconfirm", package]
    if source == "zypper":
        return [privilege_tool, "zypper", "remove", "-y", package]
    if source == "snap":
        return [privilege_tool, "snap", "remove", package]
    return ["flatpak", "uninstall", "-y", package]


def _is_apt_installed(package: str) -> bool:
    output = _run_probe(["dpkg-query", "-W", "-f=${Status}", package])
    return "install ok installed" in output.lower()


def _is_snap_installed(package: str) -> bool:
    if not shutil.which("snap"):
        return False
    output = _run_probe(["snap", "list", package])
    lowered = output.lower()
    negative_markers = (
        "is not installed",
        "not installed",
        "no matching snaps installed",
        "no snaps are installed",
    )
    if output.strip() and not any(marker in lowered for marker in negative_markers):
        for line in output.splitlines():
            parts = line.split()
            if parts and parts[0].lower() == package.lower():
                return True
    norm_pkg = _normalize_lookup(package)
    snap_apps_dir = Path("/var/lib/snapd/desktop/applications")
    if snap_apps_dir.is_dir() and norm_pkg:
        for desktop_file in snap_apps_dir.glob("*.desktop"):
            stem_norm = _normalize_lookup(desktop_file.stem)
            if stem_norm == norm_pkg or stem_norm.startswith(f"{norm_pkg}_"):
                return True
    return False


def _is_flatpak_installed(package: str) -> bool:
    if not shutil.which("flatpak"):
        return False
    output = _run_probe(["flatpak", "list", "--app", "--columns=application"])
    return any(line.strip().lower() == package.lower() for line in output.splitlines())


def _normalize_lookup(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _read_text_file(path: Path, max_chars: int = 20000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def _find_user_desktop_launchers(query: str) -> list[Path]:
    desktop_dir = Path.home() / ".local" / "share" / "applications"
    if not desktop_dir.is_dir():
        return []

    needle = _normalize_lookup(query.replace(".desktop", ""))
    if not needle:
        return []

    matches: list[tuple[int, Path]] = []
    for path in desktop_dir.glob("*.desktop"):
        content = _read_text_file(path)
        haystack = f"{path.stem}\n{content}"
        normalized_haystack = _normalize_lookup(haystack)
        if needle not in normalized_haystack:
            continue
        score = 0 if _normalize_lookup(path.stem) == needle else 1
        matches.append((score, path))

    return [path for _score, path in sorted(matches, key=lambda item: (item[0], item[1].name.lower()))]


def _desktop_exec_paths(launcher: Path) -> list[Path]:
    paths: list[Path] = []
    for line in _read_text_file(launcher).splitlines():
        if not line.startswith(("Exec=", "TryExec=")):
            continue
        value = line.split("=", 1)[1]
        try:
            parts = shlex.split(value)
        except ValueError:
            continue
        if not parts:
            continue
        binary = parts[0]
        if binary.startswith("/") or binary.startswith("~"):
            paths.append(Path(binary).expanduser())
    return paths


def _path_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _local_app_root(path: Path) -> Path | None:
    home = Path.home()
    local_root = home / ".local"
    applications_root = home / "Applications"
    resolved = path.resolve()
    if not _path_inside(resolved, home):
        return None

    for parent in (resolved, *resolved.parents):
        if parent.parent == local_root and parent.name.endswith(".app"):
            return parent
    if _path_inside(resolved, applications_root):
        try:
            first_part = resolved.relative_to(applications_root.resolve()).parts[0]
        except (IndexError, ValueError):
            return None
        return applications_root / first_part
    return None


def _local_desktop_removal_paths(package: str) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        normalized = path.expanduser()
        if normalized in seen or not normalized.exists():
            return
        if not _path_inside(normalized, Path.home()):
            return
        seen.add(normalized)
        paths.append(normalized)

    for launcher in _find_user_desktop_launchers(package):
        add(launcher)
        for exec_path in _desktop_exec_paths(launcher):
            if exec_path.is_symlink():
                add(exec_path)
                try:
                    resolved_exec = exec_path.resolve()
                except Exception:
                    resolved_exec = exec_path
            else:
                resolved_exec = exec_path
            root = _local_app_root(resolved_exec)
            if root:
                add(root)
            else:
                add(exec_path)

    binary = shutil.which(package)
    if binary:
        binary_path = Path(binary)
        if _path_inside(binary_path, Path.home()):
            if binary_path.is_symlink():
                add(binary_path)
                try:
                    resolved_binary = binary_path.resolve()
                except Exception:
                    resolved_binary = binary_path
            else:
                resolved_binary = binary_path
            root = _local_app_root(resolved_binary)
            if root:
                add(root)
            elif not binary_path.is_symlink():
                add(binary_path)

    return paths


def _is_rpm_installed(package: str) -> bool:
    if not shutil.which("rpm"):
        return False
    output = _run_probe(["rpm", "-q", "--qf", "%{NAME}\n", package])
    return any(line.strip().lower() == package.lower() for line in output.splitlines())


def _is_pacman_installed(package: str) -> bool:
    if not shutil.which("pacman"):
        return False
    output = _run_probe(["pacman", "-Qq", package])
    return any(line.strip().lower() == package.lower() for line in output.splitlines())


def _is_installed_in_source(source: str, package: str) -> bool:
    if source == "apt":
        return _is_apt_installed(package)
    if source in {"dnf", "zypper"}:
        return _is_rpm_installed(package)
    if source == "pacman":
        return _is_pacman_installed(package)
    if source == "snap":
        return _is_snap_installed(package)
    if source == "flatpak":
        return _is_flatpak_installed(package)
    if source == "desktop":
        return bool(_local_desktop_removal_paths(package))
    return False


def _resolve_uninstall_source(source: str, package: str) -> str:
    sources = ["apt", "dnf", "pacman", "zypper", "snap", "flatpak", "desktop"]
    candidates = []
    if source != "auto":
        candidates.append(source)
    candidates.extend(item for item in sources if item not in candidates)

    for candidate in candidates:
        if _is_installed_in_source(candidate, package):
            return candidate
    return ""


def _scan_desktop_entries() -> list[dict]:
    """Escanea lanzadores .desktop para encontrar nombres visibles y fuentes asociadas."""
    search_dirs = [
        Path.home() / ".local" / "share" / "applications",
        Path("/var/lib/snapd/desktop/applications"),
        Path("/usr/share/applications"),
    ]
    entries = []
    seen = set()
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        try:
            files = list(directory.glob("*.desktop"))
        except Exception:
            continue
        for path in files:
            if path.name in seen:
                continue
            seen.add(path.name)
            content = _read_text_file(path, max_chars=8000)
            disp_name = ""
            snap_instance = ""
            exec_line = ""
            for line in content.splitlines():
                if line.startswith("Name=") and not disp_name:
                    disp_name = line.split("=", 1)[1].strip()
                elif line.startswith("X-SnapInstanceName="):
                    snap_instance = line.split("=", 1)[1].strip()
                elif line.startswith("Exec=") and not exec_line:
                    exec_line = line.split("=", 1)[1].strip()

            source = "desktop"
            pkg = path.stem
            if snap_instance:
                source = "snap"
                pkg = snap_instance
            elif exec_line.startswith("/snap/bin/"):
                source = "snap"
                parts = exec_line.replace("/snap/bin/", "").split()
                if parts:
                    pkg = parts[0]
            elif "/flatpak/" in exec_line or path.name.count(".") >= 2:
                if shutil.which("flatpak") and _is_flatpak_installed(path.stem):
                    source = "flatpak"
                    pkg = path.stem
            elif _path_inside(path, Path.home()):
                source = "desktop"
                pkg = path.stem
            else:
                try:
                    from src.core.distro import detect_distro
                    native_mgr = detect_distro().native_package_manager
                except Exception:
                    native_mgr = "apt"
                source = native_mgr if native_mgr in {"apt", "dnf", "pacman", "zypper"} else "apt"
                pkg = path.stem

            entries.append({
                "path": path,
                "display_name": disp_name or path.stem,
                "package": pkg,
                "source": source,
            })
    return entries


def find_uninstall_candidates(query: str, source: str = "auto") -> list[dict]:
    """Busca candidatos de desinstalacion en Snap, Flatpak, Desktop y gestores nativos usando coincidencia flexible."""
    norm_query = _normalize_lookup(query)
    if not norm_query:
        return []

    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add_candidate(cand_source: str, cand_pkg: str, cand_disp: str, score: float):
        key = (cand_source, cand_pkg.lower())
        if key in seen:
            for item in candidates:
                if (item["source"], item["package"].lower()) == key:
                    if score > item["score"]:
                        item["score"] = score
                        item["display_name"] = cand_disp
            return
        seen.add(key)
        candidates.append({
            "source": cand_source,
            "package": cand_pkg,
            "display_name": cand_disp,
            "score": score,
        })

    # 1. Escanear Snap
    if source in {"auto", "snap"} and shutil.which("snap"):
        snap_list_output = _run_probe(["snap", "list"])
        for line in snap_list_output.splitlines()[1:]:
            parts = line.split()
            if not parts:
                continue
            snap_name = parts[0]
            norm_snap = _normalize_lookup(snap_name)
            if norm_query == norm_snap:
                add_candidate("snap", snap_name, snap_name, 1.0)
            elif norm_query in norm_snap:
                add_candidate("snap", snap_name, snap_name, 0.9)
            elif norm_snap in norm_query and len(norm_snap) >= 4:
                add_candidate("snap", snap_name, snap_name, 0.8)

    # 2. Escanear lanzadores .desktop (Snap, sistema, usuario)
    for entry in _scan_desktop_entries():
        ent_src = entry["source"]
        if source != "auto" and source != ent_src:
            continue
        pkg = entry["package"]
        disp = entry["display_name"]
        norm_pkg = _normalize_lookup(pkg)
        norm_disp = _normalize_lookup(disp)

        if norm_query == norm_pkg or norm_query == norm_disp:
            add_candidate(ent_src, pkg, disp, 1.0)
        elif norm_query in norm_pkg or norm_query in norm_disp:
            add_candidate(ent_src, pkg, disp, 0.85)
        elif (norm_pkg in norm_query and len(norm_pkg) >= 4) or (norm_disp in norm_query and len(norm_disp) >= 4):
            add_candidate(ent_src, pkg, disp, 0.8)

    # 3. Escanear Flatpak
    if source in {"auto", "flatpak"} and shutil.which("flatpak"):
        fp_output = _run_probe(["flatpak", "list", "--app", "--columns=application,name"])
        for line in fp_output.splitlines():
            parts = line.split("\t")
            app_id = parts[0].strip() if parts else ""
            app_name = parts[1].strip() if len(parts) > 1 else app_id
            if not app_id:
                continue
            norm_id = _normalize_lookup(app_id)
            norm_name = _normalize_lookup(app_name)
            if norm_query == norm_id or norm_query == norm_name:
                add_candidate("flatpak", app_id, app_name, 1.0)
            elif norm_query in norm_id or norm_name and norm_query in norm_name:
                add_candidate("flatpak", app_id, app_name, 0.85)

    # 4. Escanear APT si se solicita o si auto no encontró nada con score 1.0
    if source in {"auto", "apt"} and shutil.which("dpkg-query"):
        has_exact = any(c["score"] == 1.0 for c in candidates)
        if not has_exact:
            apt_out = _run_probe(["dpkg-query", "-W", "-f=${Package}\t${Status}\n", f"*{norm_query}*"])
            for line in apt_out.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2 and "install ok installed" in parts[1].lower():
                    pkg = parts[0].strip()
                    norm_p = _normalize_lookup(pkg)
                    score = 1.0 if norm_query == norm_p else 0.75
                    add_candidate("apt", pkg, pkg, score)

    # 5. Escanear RPM (DNF / Zypper) o Pacman cuando corresponda
    if source in {"auto", "dnf", "zypper"} and shutil.which("rpm"):
        has_exact = any(c["score"] == 1.0 for c in candidates)
        if not has_exact:
            target_mgr = "zypper" if source == "zypper" or (source == "auto" and shutil.which("zypper") and not shutil.which("dnf")) else "dnf"
            rpm_out = _run_probe(["rpm", "-qa", "--qf", "%{NAME}\n"])
            for line in rpm_out.splitlines():
                pkg = line.strip()
                norm_p = _normalize_lookup(pkg)
                if norm_query in norm_p:
                    score = 1.0 if norm_query == norm_p else 0.75
                    add_candidate(target_mgr, pkg, pkg, score)

    if source in {"auto", "pacman"} and shutil.which("pacman"):
        has_exact = any(c["score"] == 1.0 for c in candidates)
        if not has_exact:
            pac_out = _run_probe(["pacman", "-Qq"])
            for line in pac_out.splitlines():
                pkg = line.strip()
                norm_p = _normalize_lookup(pkg)
                if norm_query in norm_p:
                    score = 1.0 if norm_query == norm_p else 0.75
                    add_candidate("pacman", pkg, pkg, score)

    # Filtrar candidatos que realmente sigan instalados según el detector de su fuente
    verified: list[dict] = []
    for c in candidates:
        if _is_installed_in_source(c["source"], c["package"]):
            verified.append(c)

    verified.sort(key=lambda item: (item["score"], len(item["package"])), reverse=True)
    return verified


def build_interactive_uninstall_command(package_name: str, source: str = "auto") -> tuple[str, str, str]:
    """Construye un comando interactivo para terminal real, no para panel de solo salida."""
    source, package = parse_package_source_request(package_name, source)
    resolved_package = package
    resolved_source = _resolve_uninstall_source(source, package)

    if not resolved_source and source in {"auto", "apt", "snap"}:
        hyphen_pkg = package.replace(" ", "-")
        if hyphen_pkg != package:
            resolved_source = _resolve_uninstall_source(source, hyphen_pkg)
            if resolved_source:
                resolved_package = hyphen_pkg

    if not resolved_source:
        candidates = find_uninstall_candidates(package, source)
        if len(candidates) == 1:
            resolved_source = candidates[0]["source"]
            resolved_package = candidates[0]["package"]
        elif len(candidates) > 1:
            exact_cands = [c for c in candidates if c["score"] == 1.0]
            if len(exact_cands) == 1:
                resolved_source = exact_cands[0]["source"]
                resolved_package = exact_cands[0]["package"]
            else:
                names = [f"'{c['package']}' ({c['source']})" for c in candidates[:5]]
                raise ValueError(
                    f"Encontré varias aplicaciones que coinciden con '{package}': {', '.join(names)}. "
                    "Especifica el nombre exacto de la que deseas desinstalar."
                )

    if not resolved_source:
        raise ValueError(
            f"No encontre '{package}' instalado por apt, Snap, Flatpak ni como lanzador local. "
            "No abro una desinstalacion hasta saber exactamente que se va a quitar."
        )
    valid_sources = {"apt", "dnf", "pacman", "zypper", "snap", "flatpak", "desktop"}
    if resolved_source not in valid_sources:
        raise ValueError("Metodo de desinstalacion no reconocido.")
    if resolved_source != "desktop" and not re.fullmatch(r"[A-Za-z0-9@._:+-]+", resolved_package):
        raise ValueError("Nombre de paquete invalido. Usa el nombre exacto, sin simbolos de shell.")
    if is_critical_system_package(resolved_package):
        raise ValueError(
            f"'{resolved_package}' parece ser parte critica del sistema operativo. "
            "No lo desinstalo desde el asistente."
        )
    if resolved_source in {"apt", "dnf", "pacman", "zypper"}:
        from src.core.distro import get_package_profile
        profile = get_package_profile(resolved_source)
        return profile.remove(resolved_package), resolved_source, resolved_package
    if resolved_source == "snap":
        return f"sudo snap remove {shlex.quote(resolved_package)}", resolved_source, resolved_package
    if resolved_source == "flatpak":
        return f"flatpak uninstall {shlex.quote(resolved_package)}", resolved_source, resolved_package

    paths = _local_desktop_removal_paths(resolved_package)
    if not paths:
        raise ValueError(f"No encontre un lanzador local para '{resolved_package}'.")
    if not shutil.which("gio"):
        raise ValueError("No encontre `gio` para mover la app local a la papelera de forma recuperable.")
    quoted_paths = " ".join(shlex.quote(str(path)) for path in paths)
    return f"gio trash {quoted_paths}", resolved_source, resolved_package


TERMINAL_START_TIMEOUT = 5.0


def _terminal_args(executable: str, kind: str, title: str, script: str) -> list[str]:
    shell = ["bash", "-c", script]
    if kind == "ptyxis":
        return [executable, "--new-window", "--title", title, "--", *shell]
    if kind == "gnome-terminal":
        return [executable, "--window", "--title", title, "--", *shell]
    if kind == "konsole":
        return [executable, "--new-window", "-p", f"tabtitle={title}", "-e", *shell]
    if kind == "xfce4-terminal":
        return [executable, "--title", title, "--execute", *shell]
    if kind == "tilix":
        return [executable, "--action=app-new-window", "--title", title, "-e", *shell]
    if kind == "kgx":
        return [executable, "--title", title, "--", *shell]
    return [executable, "-T", title, "-e", *shell]


def launch_in_terminal(command: str, title: str = "Asistente Linux") -> Tuple[bool, str]:
    """Confirma que el comando arranca con una TTY antes de anunciar la apertura."""
    terminal_candidates = [
        "ptyxis",
        "gnome-terminal",
        "x-terminal-emulator",
        "kgx",
        "tilix",
        "konsole",
        "xfce4-terminal",
        "xterm",
    ]
    errors = []
    tried = set()
    for term in terminal_candidates:
        executable = shutil.which(term)
        if not executable:
            continue
        resolved = Path(executable).resolve()
        if resolved in tried:
            continue
        tried.add(resolved)
        kind = resolved.name if term == "x-terminal-emulator" else term
        with tempfile.TemporaryDirectory(prefix="asistente-terminal-") as directory:
            claim = Path(directory) / "started"
            # mkdir es una disputa atomica: al cancelar, un arranque tardio no ejecuta nada.
            script = (
                "test -t 0 && test -t 1 || exit 1\n"
                f"mkdir -- {shlex.quote(str(claim))} 2>/dev/null || exit 1\n"
                f"bash -c {shlex.quote(command)}\n"
                "result=$?\n"
                "printf '\\nProceso finalizado (codigo %s).\\n' \"$result\"\n"
                "printf 'Presiona Enter para cerrar esta ventana...'\n"
                "IFS= read -r answer\n"
                "exit \"$result\"\n"
            )
            with tempfile.TemporaryFile(mode="w+") as stderr:
                try:
                    process = subprocess.Popen(
                        _terminal_args(executable, kind, title, script),
                        stdout=subprocess.DEVNULL,
                        stderr=stderr,
                        start_new_session=True,
                    )
                except OSError as exc:
                    errors.append(f"{term}: {exc}")
                    continue

                deadline = time.monotonic() + TERMINAL_START_TIMEOUT
                while not claim.exists() and time.monotonic() < deadline:
                    if process.poll() not in (None, 0):
                        break
                    time.sleep(0.05)
                try:
                    claim.mkdir()
                except FileExistsError:
                    threading.Thread(target=process.wait, daemon=True).start()
                    return True, f"Se abrió una terminal ({term}) ejecutando: {command}"

                stderr.seek(0)
                detail = stderr.read(1500).strip()
                errors.append(f"{term}: {detail or 'no confirmo el arranque de la terminal'}")
                threading.Thread(target=process.wait, daemon=True).start()

    if errors:
        return False, "No se pudo iniciar una terminal interactiva.\n" + "\n".join(errors)
    return False, "No se encontró ningún emulador de terminal compatible instalado."


def tool_update_system(mode: str = "gui") -> str:
    if mode == "gui":
        if shutil.which("update-manager"):
            try:
                subprocess.Popen(["update-manager"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "Exito: Se ha abierto la interfaz grafica del Actualizador de Software de Ubuntu (update-manager)."
            except Exception as e:
                pass
        if shutil.which("gnome-software"):
            try:
                subprocess.Popen(["gnome-software", "--mode=updates"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "Exito: Se ha abierto la seccion de actualizaciones de la Tienda de Software de Ubuntu."
            except Exception:
                pass

    from src.core.distro import get_package_profile
    profile = get_package_profile()
    success, msg = launch_in_terminal(profile.update, title=f"Actualización del sistema ({profile.manager})")
    if success:
        return f"Exito: Se ha abierto una ventana de terminal con '{profile.update}'. Ingresa tu contrasena en la terminal para continuar."
    return f"Fallo al ejecutar actualizacion: {msg}"


def tool_manage_firmware(action: str = "check") -> str:
    """Revisa o instala actualizaciones de firmware usando fwupd."""
    action = action.strip().lower()
    if action not in {"check", "update"}:
        return "Accion de firmware no reconocida. Usa check o update."
    if not shutil.which("fwupdmgr"):
        return (
            "No encontre fwupdmgr, que es la herramienta de Ubuntu para firmware.\n\n"
            "Puedes instalarla con:\n```bash\nsudo apt install fwupd\n```"
        )

    if action == "check":
        command = "fwupdmgr refresh --force; echo; fwupdmgr get-updates"
        success, msg = launch_in_terminal(command, title="Revisando firmware")
        if success:
            return (
                "Abrí una terminal para revisar actualizaciones de firmware.\n\n"
                "Comando ejecutado:\n```bash\n"
                f"{command}\n"
                "```\n"
                "Si no aparecen dispositivos o actualizaciones, tu firmware ya está al día o tu hardware no publica updates por fwupd."
            )
        return f"No pude revisar firmware: {msg}"

    command = "fwupdmgr refresh --force; echo; fwupdmgr get-updates; echo; fwupdmgr update"
    success, msg = launch_in_terminal(command, title="Actualizando firmware")
    if success:
        return (
            "Abrí una terminal para buscar e instalar actualizaciones de firmware con fwupd.\n\n"
            "Comando ejecutado:\n```bash\n"
            f"{command}\n"
            "```\n"
            "Lee la terminal antes de aceptar: algunas actualizaciones pueden pedir reiniciar el equipo."
        )
    return f"No pude iniciar la actualización de firmware: {msg}"


def _find_software_center_binary() -> str | None:
    candidates = ["snap-store", "ubuntu-app-center", "gnome-software", "ubuntu-software"]
    for name in candidates:
        which_path = shutil.which(name)
        if which_path:
            return which_path
    snap_paths = [
        Path("/snap/bin/snap-store"),
        Path("/snap/bin/ubuntu-app-center"),
        Path("/var/lib/snapd/snap/bin/snap-store"),
    ]
    for path in snap_paths:
        if path.exists():
            return str(path)
    if Path("/var/lib/snapd/desktop/applications/snap-store_snap-store.desktop").exists() and shutil.which("gtk-launch"):
        return "snap-store"
    return None


def tool_open_software_center(app_name: str = "", mode: str = "") -> str:
    bin_path = _find_software_center_binary()
    if not bin_path:
        return "No se encontro un Centro de Software grafico instalado."

    bin_name = Path(bin_path).name
    is_manage = mode in {"installed", "manage", "gestionar"}
    args = [bin_path]

    if is_manage:
        if bin_name == "gnome-software":
            args.append("--mode=installed")
        elif "snap-store" in bin_name or "app-center" in bin_name:
            desktop_updates = Path("/var/lib/snapd/desktop/applications/snap-store_show-updates.desktop")
            if desktop_updates.exists() and shutil.which("gtk-launch"):
                args = ["gtk-launch", "snap-store_show-updates"]
            elif shutil.which("snap-store.show-updates"):
                args = ["snap-store.show-updates", "--updates"]
            elif Path("/snap/bin/snap-store.show-updates").exists():
                args = ["/snap/bin/snap-store.show-updates", "--updates"]
            else:
                args.append("--updates")
    elif app_name:
        args.append(f"--search={app_name}")

    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if is_manage:
            display_name = "Centro de aplicaciones de Ubuntu" if ("snap-store" in bin_name or "app-center" in bin_name) else f"Centro de Software ({bin_name})"
            return f"Se abrió el {display_name} en el apartado 'Gestionar' para administrar las aplicaciones instaladas."
        return f"Exito: Se abrio el Centro de Software ({bin_name})."
    except Exception as e:
        return f"Error al abrir la tienda de software: {e}"


def _installed_java_major_version() -> int | None:
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None

    output = f"{result.stdout}\n{result.stderr}"
    match = re.search(r'version\s+"(\d+)', output)
    if not match:
        return None
    return int(match.group(1))


def _netbeans_java_diagnostic() -> str | None:
    java_version = _installed_java_major_version()
    if java_version is None:
        return (
            "NetBeans necesita Java 21 o más nuevo, pero no pude detectar Java instalado.\n\n"
            "Solución recomendada:\n"
            "```bash\nsudo apt update\nsudo apt install openjdk-21-jdk\n```"
        )
    if java_version < 21:
        return (
            f"NetBeans está instalado, pero tu sistema usa Java {java_version}. "
            "Esta versión de NetBeans requiere Java 21 o más nuevo.\n\n"
            "Solución recomendada:\n"
            "```bash\nsudo apt update\nsudo apt install openjdk-21-jdk\n```\n"
            "Después verifica con `java -version` y vuelve a abrir NetBeans."
        )
    return None


def _proton_vpn_diagnostic() -> str:
    return (
        "Proton VPN no parece estar instalado en tu sistema.\n\n"
        "Puedes instalarlo con cualquiera de las siguientes opciones:\n\n"
        "1. **Snap (Recomendado en Ubuntu)**:\n"
        "```bash\n"
        "sudo snap install proton-vpn\n"
        "```\n\n"
        "2. **Flatpak**:\n"
        "```bash\n"
        "flatpak install flathub com.protonvpn.www\n"
        "```\n\n"
        "3. **Paquete oficial DEB**:\n"
        "Descárgalo desde [protonvpn.com](https://protonvpn.com/es/download-linux/) o ejecuta:\n"
        "```bash\n"
        "sudo apt update && sudo apt install -y protonvpn-app\n"
        "```"
    )


def _find_desktop_application(query: str) -> tuple[str, str, str, str] | None:
    """Busca dinámicamente un archivo .desktop en las rutas estándar de Ubuntu/Linux.
    Retorna (friendly_name, desktop_id, file_path, exec_cmd) o None si no encuentra coincidencia.
    """
    dirs = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        os.path.expanduser("~/.local/share/applications"),
        "/var/lib/snapd/desktop/applications",
        "/var/lib/flatpak/exports/share/applications",
        os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
    ]
    clean_query = query.lower().strip()
    norm_query = re.sub(r"[^a-z0-9]", "", clean_query)
    if not norm_query:
        return None

    candidates = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        try:
            entries = os.scandir(d)
        except OSError:
            continue
        for entry in entries:
            if not entry.name.endswith(".desktop"):
                continue
            desktop_id = entry.name[:-8]
            file_path = entry.path

            name = ""
            exec_cmd = ""
            no_display = False
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str.startswith("Name=") and not name:
                            name = line_str[5:].strip()
                        elif line_str.startswith("Exec=") and not exec_cmd:
                            exec_cmd = line_str[5:].strip()
                        elif line_str == "NoDisplay=true":
                            no_display = True
                        elif line_str.startswith("[") and line_str != "[Desktop Entry]" and name:
                            break
            except Exception:
                continue

            if no_display:
                continue

            norm_name = re.sub(r"[^a-z0-9]", "", name.lower())
            norm_id = re.sub(r"[^a-z0-9]", "", desktop_id.lower())

            score = 0
            if norm_name == norm_query or norm_id == norm_query:
                score = 100
            elif norm_name.startswith(norm_query) or norm_id.startswith(norm_query):
                score = 85
            elif norm_query in norm_name or norm_query in norm_id:
                score = 70
            elif any(w == norm_name for w in clean_query.split() if len(w) > 2):
                score = 60
            elif any(w in norm_name for w in clean_query.split() if len(w) > 2):
                score = 50

            if score > 0:
                candidates.append((score, name or desktop_id, desktop_id, file_path, exec_cmd))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best = candidates[0]
        return best[1], best[2], best[3], best[4]
    return None


def _launch_desktop_entry(desktop_id: str, exec_cmd: str, friendly_name: str) -> tuple[bool, str]:
    """Ejecuta una entrada .desktop usando gtk-launch o el comando Exec del archivo."""
    # 1. gtk-launch si está disponible (método estándar oficial en GNOME/Ubuntu)
    if shutil.which("gtk-launch"):
        try:
            subprocess.Popen(["gtk-launch", desktop_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"Exito: Se ha abierto la aplicacion {friendly_name}."
        except Exception:
            pass

    # 2. Comando Exec limpio del archivo .desktop
    if exec_cmd:
        clean_cmd = re.sub(r"%[a-zA-Z]", "", exec_cmd).strip()
        try:
            parts = shlex.split(clean_cmd)
        except Exception:
            parts = clean_cmd.split()
        if parts:
            binary = parts[0]
            if shutil.which(binary) or Path(binary).exists():
                try:
                    subprocess.Popen(parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True, f"Exito: Se ha abierto la aplicacion {friendly_name}."
                except Exception as e:
                    return False, f"Error al abrir {friendly_name}: {e}"

    # 3. Fallback para paquetes Snap si corresponde
    if "snap" in desktop_id.lower() or "/snap/" in exec_cmd:
        snap_name = desktop_id.split("_")[0] if "_" in desktop_id else desktop_id
        if shutil.which("snap"):
            try:
                subprocess.Popen(["snap", "run", snap_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, f"Exito: Se ha abierto la aplicacion {friendly_name}."
            except Exception:
                pass

    return False, f"No se pudo ejecutar el lanzador para {friendly_name}."


def tool_open_application(app_name: str) -> str:
    app_map = {
        "terminal": ["gnome-terminal", "x-terminal-emulator", "xterm"],
        "explorador": ["nautilus", "nemo", "thunar", "dolphin"],
        "archivos": ["nautilus", "nemo", "thunar", "dolphin"],
        "navegador": ["firefox", "google-chrome", "chromium-browser", "xdg-open https://google.com"],
        "calculadora": ["gnome-calculator", "kcalc", "galculator", "xcalc"],
        "monitor": ["gnome-system-monitor", "ksysguard", "htop"],
        "configuracion": ["gnome-control-center", "systemsettings"],
        "editor": ["gedit", "kate", "mousepad", "gnome-text-editor"],
        "wine": ["winecfg"],
        "winecfg": ["winecfg"],
        "netbeans": ["netbeans", "apache-netbeans"],
        "apache-netbeans": ["apache-netbeans", "netbeans"],
        "proton": ["protonvpn-app", "protonvpn", "proton-vpn"],
        "proton vpn": ["protonvpn-app", "protonvpn", "proton-vpn"],
        "protonvpn": ["protonvpn-app", "protonvpn", "proton-vpn"],
        "proton-vpn": ["protonvpn-app", "protonvpn", "proton-vpn"],
        "brave": ["brave-browser", "brave"],
        "discord": ["discord"],
        "telegram": ["telegram-desktop", "telegram"],
        "spotify": ["spotify"],
    }

    target = app_name.lower().strip()
    if any(phrase in target for phrase in ["la aplicacion que instalaste", "la aplicación que instalaste", "lo que instalaste", "ultima aplicacion", "última aplicación"]):
        if LAST_INSTALLED_APP.get("source") and LAST_INSTALLED_APP.get("package"):
            source = LAST_INSTALLED_APP["source"]
            package = LAST_INSTALLED_APP["package"]
            friendly_name = LAST_INSTALLED_APP.get("friendly_name", package)
            return _open_resolved_application(source, package, friendly_name)
        return "Todavía no tengo registrada una aplicación instalada en esta sesión."

    alias = APP_ALIASES.get(target)
    if alias:
        source, package, friendly_name = alias
        return _open_resolved_application(source, package, friendly_name)

    executables = app_map.get(target, [target])

    if target in {"netbeans", "apache-netbeans"}:
        diagnostic = _netbeans_java_diagnostic()
        if diagnostic:
            return diagnostic

    for cmd in executables:
        parts = cmd.split()
        binary = parts[0]
        if shutil.which(binary) or Path(binary).exists():
            try:
                subprocess.Popen(parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Exito: Se ha abierto la aplicacion {app_name}."
            except Exception as e:
                return f"Error al abrir {app_name}: {e}"

    # Búsqueda dinámica en archivos .desktop del sistema (soporta Snaps, Flatpaks y aplicaciones instaladas)
    desktop_app = _find_desktop_application(target)
    if desktop_app:
        friendly_name, desktop_id, file_path, exec_cmd = desktop_app
        ok, msg = _launch_desktop_entry(desktop_id, exec_cmd, friendly_name)
        if ok:
            return msg

    # Diagnósticos y sugerencias de instalación específicas
    if target in {"proton", "proton vpn", "protonvpn", "proton-vpn"}:
        return _proton_vpn_diagnostic()

    return f"No se encontro el ejecutable para la aplicacion '{app_name}'."


def _open_resolved_application(source: str, package: str, friendly_name: str) -> str:
    if source == "flatpak":
        if not shutil.which("flatpak"):
            return "Flatpak no esta disponible en este sistema."
        installed = _run_probe(["flatpak", "list", "--app", "--columns=application,name"], timeout=8)
        if package not in installed:
            return (
                f"{friendly_name} parece ser una app Flatpak, pero no la veo instalada.\n"
                f"Instalala con:\n```bash\nflatpak install flathub {package}\n```"
            )
        try:
            subprocess.Popen(["flatpak", "run", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abriendo {friendly_name} con Flatpak (`flatpak run {package}`)."
        except Exception as exc:
            return f"No pude abrir {friendly_name} con Flatpak: {exc}"

    if source == "snap":
        if not shutil.which("snap"):
            return "Snap no esta disponible en este sistema."
        try:
            subprocess.Popen(["snap", "run", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abriendo {friendly_name} con Snap (`snap run {package}`)."
        except Exception as exc:
            return f"No pude abrir {friendly_name} con Snap: {exc}"

    if shutil.which(package):
        try:
            subprocess.Popen([package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abriendo {friendly_name} (`{package}`)."
        except Exception as exc:
            return f"No pude abrir {friendly_name}: {exc}"
    return f"No encontre el ejecutable para {friendly_name}."


def tool_open_terminal_command(command: str, explanation: str = "") -> str:
    decision = assess_command(command, allow_confirmation=False)
    if decision.is_blocked:
        return f"Accion bloqueada por seguridad ({decision.risk.value}): {decision.message}"
    success, msg = launch_in_terminal(command, title=f"Comando: {command[:20]}")
    if success:
        return f"Exito: Se ha abierto una terminal ejecutando `{command}`."
    return f"Fallo al abrir terminal: {msg}"


def tool_install_deb_package(package_name: str = "") -> str:
    """Busca e instala un archivo .deb en Descargas o Downloads de forma interactiva."""
    folders = [
        os.path.expanduser("~/Descargas"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~"),
    ]
    candidates = []
    for f in folders:
        if os.path.isdir(f):
            try:
                for item in os.listdir(f):
                    if item.endswith(".deb"):
                        candidates.append(os.path.join(f, item))
            except Exception:
                pass

    if not candidates:
        return "No se encontró ningún archivo .deb en tu carpeta de Descargas."

    target_file = None
    if package_name:
        query = package_name.lower().replace(".deb", "").strip()
        matched = [c for c in candidates if query in os.path.basename(c).lower()]
        if matched:
            target_file = matched[0]

    if not target_file:
        if len(candidates) == 1:
            target_file = candidates[0]
        else:
            names = [os.path.basename(c) for c in candidates]
            return f"Encontré varios paquetes .deb: {', '.join(names)}. ¿Cuál de ellos deseas instalar?"

    cmd = f"sudo dpkg -i {shlex.quote(target_file)} && sudo apt-get install -f -y"
    success, msg = launch_in_terminal(cmd, title=f"Instalando {os.path.basename(target_file)}")
    if success:
        return f"Éxito: Se abrió la terminal para instalar '{os.path.basename(target_file)}'. Ingresa tu contraseña en la terminal para completar la instalación."
    return f"Error al abrir la terminal: {msg}"


def build_deb_install_args(file_path: str, privilege_tool: str = "pkexec") -> list[str]:
    """Valida una ruta .deb y genera argumentos seguros, sin usar un shell."""
    path = Path(file_path).expanduser().resolve()
    if path.suffix.lower() != ".deb":
        raise ValueError("El archivo seleccionado no tiene extension .deb.")
    if not path.is_file():
        raise ValueError("El archivo .deb seleccionado no existe.")
    return [privilege_tool, "apt", "install", "-y", str(path)]


def _parse_program_request(program_name: str, preferred_source: str = "auto") -> tuple[str, str, str]:
    source = preferred_source.strip().lower() or "auto"
    name = program_name.strip().lower()
    name = re.sub(r"\b(por favor|porfa|please)\b", "", name).strip()
    name = re.sub(r"\b(en|para)\s+(mi\s+)?(ubuntu|linux|sistema|computadora|pc)\b", "", name).strip()

    source_match = re.match(r"^(?:por|con|desde|usando|en)?\s*(apt|apt-get|dnf|pacman|zypper|snap|flatpak)\s+(.+)$", name)
    if source_match:
        source = "apt" if source_match.group(1) == "apt-get" else source_match.group(1)
        name = source_match.group(2).strip()

    alias = PACKAGE_ALIASES.get(name)
    if alias and source == "auto":
        return alias

    source_alias = SOURCE_PACKAGE_ALIASES.get(source, {}).get(name)
    if source_alias:
        package, friendly_name = source_alias
        return source, package, friendly_name

    package = name.replace(" ", "-")
    return source, package, program_name.strip()


def _run_probe(args: list[str], timeout: int = 8) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return ""
    return f"{result.stdout}\n{result.stderr}".strip()


def _apt_has_candidate(package: str) -> bool:
    output = _run_probe(["apt-cache", "policy", package])
    for line in output.splitlines():
        text = line.strip().lower()
        if text.startswith("candidato:") or text.startswith("candidate:"):
            value = text.split(":", 1)[1].strip()
            return value not in {"(ninguno)", "(none)", "none", ""}
    return False


def _native_has_candidate(source: str, package: str) -> bool:
    probes = {
        "dnf": ["dnf", "list", "--available", package],
        "pacman": ["pacman", "-Si", package],
        "zypper": ["zypper", "search", "--details", "--match-exact", package],
    }
    if source not in probes or not shutil.which(source):
        return False
    return bool(_run_probe(probes[source], timeout=12).strip())


def _flatpak_has_match(package: str) -> bool:
    if not shutil.which("flatpak"):
        return False
    output = _run_probe(["flatpak", "search", package], timeout=12)
    needle = package.lower()
    return any(needle in line.lower().split() for line in output.splitlines())


def _snap_has_match(package: str) -> bool:
    if not shutil.which("snap"):
        return False
    output = _run_probe(["snap", "find", package], timeout=12)
    needle = package.lower()
    for line in output.splitlines():
        parts = line.split()
        if parts and parts[0].lower() == needle:
            return True
    return False


def _source_has_package(source: str, package: str) -> bool:
    if source == "apt":
        return _apt_has_candidate(package)
    if source == "flatpak":
        return _flatpak_has_match(package)
    if source == "snap":
        return _snap_has_match(package)
    if source in {"dnf", "pacman", "zypper"}:
        return _native_has_candidate(source, package)
    return False


def _resolve_install_source(source: str, package: str, friendly_name: str) -> tuple[str | None, str, str, str]:
    if source != "auto":
        if _source_has_package(source, package):
            return source, package, friendly_name, ""
        return (
            None,
            package,
            friendly_name,
            f"No encontre '{friendly_name}' como paquete disponible en {source}. "
            "No voy a ejecutar un comando que probablemente fallara.",
        )

    alias = PACKAGE_ALIASES.get(package.lower())
    candidates = [alias] if alias else []
    from src.core.distro import get_active_package_manager
    native = get_active_package_manager()
    source_order = [native, "flatpak", "snap", *INSTALL_SOURCE_ORDER]
    for candidate_source in dict.fromkeys(source_order):
        source_alias = SOURCE_PACKAGE_ALIASES.get(candidate_source, {}).get(package.lower())
        if source_alias:
            candidate_package, candidate_name = source_alias
            candidates.append((candidate_source, candidate_package, candidate_name))
        candidates.append((candidate_source, package, friendly_name))

    seen = set()
    for candidate_source, candidate_package, candidate_name in candidates:
        key = (candidate_source, candidate_package)
        if key in seen:
            continue
        seen.add(key)
        if _source_has_package(candidate_source, candidate_package):
            return candidate_source, candidate_package, candidate_name, ""

    return (
        None,
        package,
        friendly_name,
        f"No encontre '{friendly_name}' en apt, Flatpak ni Snap. "
        "Puede que necesite descargarse desde su pagina oficial o que falte configurar un repositorio.",
    )


def prepare_install_program(program_name: str, preferred_source: str = "auto") -> dict | str:
    """Resuelve una solicitud de instalación y devuelve un plan sin ejecutarlo."""
    if not program_name.strip():
        return "Indica que programa quieres instalar."

    source, package, friendly_name = _parse_program_request(program_name, preferred_source)

    if source not in {"auto", "apt", "dnf", "pacman", "zypper", "snap", "flatpak"}:
        return "Metodo de instalacion no reconocido."
    if not re.fullmatch(r"[A-Za-z0-9.+_-]+", package) and source != "flatpak":
        return f"No pude convertir '{program_name}' a un nombre seguro de paquete."

    resolved_source, package, friendly_name, problem = _resolve_install_source(source, package, friendly_name)
    if not resolved_source:
        return (
            f"{problem}\n\n"
            "Sugerencia: prueba pedirlo por una fuente concreta, por ejemplo "
            "`instala trilium notes por flatpak`, o abre la tienda de aplicaciones."
        )
    source = resolved_source

    if source in {"apt", "dnf", "pacman", "zypper"}:
        from src.core.distro import get_package_profile
        profile = get_package_profile(source)
        command = profile.install(package, False)
    elif source == "snap":
        command = f"sudo snap install {shlex.quote(package)}"
    else:
        command = f"flatpak install flathub {shlex.quote(package)}"

    return {
        "source": source,
        "package": package,
        "friendly_name": friendly_name,
        "command": command,
    }


def _execute_install_plan(plan: dict) -> str:
    source = plan.get("source")
    package = plan.get("package")
    friendly_name = plan.get("friendly_name") or package
    if source not in {"apt", "dnf", "pacman", "zypper", "snap", "flatpak"}:
        return "El plan de instalación ya no es válido."
    if not isinstance(package, str) or not re.fullmatch(r"[A-Za-z0-9@._:+-]+", package):
        return "El identificador del paquete no es seguro."
    if source in {"apt", "dnf", "pacman", "zypper"}:
        from src.core.distro import get_package_profile
        command = get_package_profile(source).install(package, False)
    elif source == "snap":
        command = f"sudo snap install {shlex.quote(package)}"
    else:
        command = f"flatpak install flathub {shlex.quote(package)}"

    success, msg = launch_in_terminal(command, title=f"Instalando {str(friendly_name)[:24]}")
    if success:
        LAST_INSTALLED_APP.clear()
        LAST_INSTALLED_APP.update({
            "source": source,
            "package": package,
            "friendly_name": friendly_name,
        })
        return (
            f"Abrí una terminal para instalar {friendly_name} usando {source}.\n"
            f"Comando:\n```bash\n{command}\n```\n"
            "Si Ubuntu pide contraseña o confirmación, acéptala en la ventana que se abrió."
        )
    return f"No pude abrir la terminal para instalar {friendly_name}: {msg}\n\nComando recomendado:\n```bash\n{command}\n```"


def tool_install_program(
    program_name: str,
    preferred_source: str = "auto",
    prepared_plan: dict | None = None,
) -> str:
    """Prepara o ejecuta un plan de instalación previamente presentado al usuario."""
    plan = prepared_plan or prepare_install_program(program_name, preferred_source)
    if isinstance(plan, str):
        return plan
    return _execute_install_plan(plan)


def tool_get_system_status() -> str:
    from src.nlp.system_tools import get_system_status
    return get_system_status()


# ─── NUEVAS HERRAMIENTAS ────────────────────────────────────────────────────


def _run_command_silent(command: str) -> tuple[str, str, str, int | None]:
    command = command.strip()
    decision = assess_command(command, allow_confirmation=False)
    if decision.is_blocked:
        message = f"⛔ {decision.message}\n\nComando: `{command}`"
        return message, "", decision.message, None
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "LANG": "es_ES.UTF-8"},
        )
        output = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if output:
            message = f"```\n{output}\n```"
        elif stderr:
            message = f"⚠️ Salida de error:\n```\n{stderr}\n```"
        else:
            message = "✅ Comando ejecutado sin salida."
        return message, output, stderr, result.returncode
    except subprocess.TimeoutExpired:
        message = "⏱️ El comando tardó demasiado (más de 15 s) y fue cancelado."
        return message, "", message, None
    except Exception as e:
        message = f"❌ Error al ejecutar el comando: {e}"
        return message, "", str(e), None


def tool_run_command_silent(command: str) -> str:
    """Ejecuta un comando no interactivo y devuelve su salida directamente en el chat."""
    return _run_command_silent(command)[0]


def tool_manage_service(service_name: str, action: str) -> str:
    """Gestiona un servicio systemd (start/stop/restart/status)."""
    valid_actions = {"start", "stop", "restart", "status", "enable", "disable"}
    if not isinstance(service_name, str) or not isinstance(action, str):
        return "❌ Indica un servicio y una acción válidos."
    service_name = service_name.strip()
    action = action.lower().strip()
    if action not in valid_actions:
        return f"Acción inválida: '{action}'. Usa: {', '.join(valid_actions)}."
    if not is_safe_name(service_name):
        return "❌ Nombre de servicio inválido. Usa sólo letras, números, puntos, guiones, @, dos puntos o guiones bajos."

    if action in {"stop", "disable", "restart"} and is_critical_system_service(service_name):
        return (
            f"⛔ No detendré, deshabilitaré ni reiniciaré el servicio crítico '{service_name}'. "
            "Podrías perder la red, la sesión gráfica o la administración del sistema."
        )

    if action == "status":
        # Status se puede mostrar directamente en el chat
        return tool_run_command_silent(f"systemctl {action} {_quote(service_name)} --no-pager")
    else:
        # Acciones que modifican el servicio utilizan PolicyKit (pkexec) con fallback a terminal
        from src.core.privilege import execute_privileged_action
        priv_res = execute_privileged_action(
            ["systemctl", action, service_name],
            title=f"Servicio: {service_name}",
        )
        if priv_res.success:
            if priv_res.mechanism == "pkexec":
                status_preview = tool_run_command_silent(f"systemctl status {_quote(service_name)} --no-pager")
                return (
                    f"✅ Servicio '{service_name}' ({action}) ejecutado con éxito mediante PolicyKit.\n\n"
                    f"{status_preview}"
                )
            return f"✅ Se abrió una terminal para ejecutar `systemctl {action} {service_name}`."
        if priv_res.mechanism == "cancelled":
            return f"⛔ Autenticación cancelada por el usuario. El servicio '{service_name}' no fue modificado."
        if priv_res.mechanism == "blocked":
            return priv_res.message
        return f"❌ No se pudo ejecutar la acción sobre '{service_name}': {priv_res.message}"


def tool_search_package(query: str) -> str:
    """Busca paquetes disponibles en el gestor de la distribución y devuelve los resultados."""
    query = query.strip()
    if not query:
        return "❌ Indica qué paquete quieres buscar."
    from src.core.distro import get_package_profile
    profile = get_package_profile()
    search_cmd = profile.search(query)
    result = tool_run_command_silent(search_cmd)
    if "```" in result and len(result) > 10:
        return f"📦 Resultados para '{query}' ({profile.manager}):\n{result}"
    return f"No se encontraron paquetes para '{query}' en {profile.manager}."


def tool_remove_package(package_name: str, source: str = "auto") -> str:
    """Desinstala una aplicacion con el mecanismo apropiado para su fuente."""
    package_name = package_name.strip()
    try:
        cmd, resolved_source, resolved_package = build_interactive_uninstall_command(package_name, source)
    except ValueError as exc:
        err_msg = str(exc)
        if "no encontre" in err_msg.lower():
            sc_result = tool_open_software_center(mode="installed")
            return (
                f"⛔ {err_msg}\n\n"
                f"🛒 {sc_result}\n"
                "Puedes revisar y desinstalar la aplicación visualmente desde la sección 'Gestionar'."
            )
        return f"⛔ {err_msg}"

    if resolved_source == "desktop":
        paths = _local_desktop_removal_paths(resolved_package)
        if not paths:
            return f"⛔ No encontre un lanzador local para '{resolved_package}'."
        try:
            result = subprocess.run(
                ["gio", "trash", *(str(path) for path in paths)],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except Exception as exc:
            return f"❌ No pude mover '{resolved_package}' a la Papelera: {exc}"

        if result.returncode == 0:
            moved = "\n".join(f"- {path}" for path in paths)
            return (
                f"✅ Movi '{resolved_package}' a la Papelera como aplicacion local de usuario.\n"
                "No abri terminal porque no requiere permisos de administrador.\n\n"
                f"Elementos movidos:\n{moved}"
            )
        detail = (result.stderr or result.stdout or "").strip()
        return f"❌ No pude mover '{resolved_package}' a la Papelera.\n{detail}"

    success, msg = launch_in_terminal(cmd, title=f"Desinstalando {resolved_package}")
    if success:
        return (
            f"✅ Se abrió una terminal para desinstalar '{resolved_package}' usando {resolved_source}.\n"
            "Revisa el resumen y confirma en esa terminal si el gestor lo solicita."
        )
    return f"❌ No se pudo abrir terminal: {msg}"


def tool_read_file(file_path: str) -> str:
    """Lee y devuelve el contenido de un archivo del sistema en el chat."""
    if not file_path.strip():
        return "❌ Indica la ruta del archivo que quieres leer."
    path = os.path.abspath(os.path.expanduser(file_path))
    for candidate in (path, os.path.realpath(path)):
        decision = assess_file_read(candidate)
        if decision.is_blocked:
            return f"⛔ {decision.message}\n\nRuta: `{candidate}`"
    if not os.path.exists(path):
        return f"❌ El archivo no existe: `{path}`"
    if not os.path.isfile(path):
        return f"❌ La ruta no es un archivo: `{path}`"
    try:
        size = os.path.getsize(path)
        if size > 50_000:
            return f"⚠️ El archivo es demasiado grande ({size // 1024} KB). Usa `head` o `tail` para verlo parcialmente."
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        lines = content.splitlines()
        preview = "\n".join(lines[:100])
        suffix = f"\n... ({len(lines) - 100} líneas más)" if len(lines) > 100 else ""
        return f"📄 `{path}`:\n```\n{preview}{suffix}\n```"
    except Exception as e:
        return f"❌ Error al leer el archivo: {e}"


def tool_write_file(file_path: str, content: str) -> str:
    """Crea o sobreescribe un archivo de texto en la ruta dada."""
    if not isinstance(file_path, str) or not file_path.strip():
        return "❌ Indica la ruta donde quieres guardar el archivo."
    if not isinstance(content, str):
        return "❌ El contenido del archivo debe ser texto."
    path = str(Path(file_path).expanduser().resolve())
    decision = assess_file_write(path)
    if decision.is_blocked:
        return f"⛔ {decision.message}\n\nRuta: `{path}`"
    try:
        target = Path(path)
        if target.exists() and not target.is_file():
            return f"⛔ La ruta existe y no es un archivo normal: `{path}`"
        sha_before = backups.sha256_file(target)
        backup_path = backups.create_backup(target)
        backups.write_atomic(target, content)
        change_id = backups.record_change(target, backup_path, sha_before, backups.sha256_text(content))
        backup_note = (
            f" Copia anterior: `{backup_path}`."
            if backup_path else " Era un archivo nuevo; no hacía falta respaldo."
        )
        return (
            f"✅ Archivo guardado: `{path}` ({len(content)} caracteres).{backup_note} "
            f"Puedes revertirlo con «deshacer el último cambio» (id {change_id})."
        )
    except backups.BackupError as e:
        return f"⛔ {e}"
    except Exception as e:
        return f"❌ Error al escribir el archivo: {e}"


def tool_undo_last_change() -> str:
    """Revierte el último archivo que el asistente escribió, si no se modificó después."""
    try:
        return backups.undo_last_change()
    except Exception as e:
        return f"❌ No pude deshacer el cambio: {e}"


# ─── DEFINICIÓN DE HERRAMIENTAS PARA EL AGENTE ─────────────────────────────

LINUX_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "install_program",
            "description": "Instala un programa solicitado en lenguaje natural. Resuelve nombres comunes a paquetes apt/snap/flatpak y abre una terminal interactiva con el comando correcto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "program_name": {
                        "type": "string",
                        "description": "Nombre del programa que el usuario quiere instalar, por ejemplo 'trilium notes', 'vlc', 'netbeans', 'spotify'."
                    },
                    "preferred_source": {
                        "type": "string",
                        "enum": ["auto", "apt", "dnf", "pacman", "zypper", "snap", "flatpak"],
                        "description": "Metodo preferido si el usuario lo menciono. Usa auto cuando no lo diga."
                    }
                },
                "required": ["program_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_firmware",
            "description": "Revisa o instala actualizaciones de firmware del equipo con fwupd/fwupdmgr. Usar cuando el usuario diga firmware, BIOS, UEFI, drivers de dispositivo o actualizar componentes internos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["check", "update"],
                        "description": "check solo busca actualizaciones; update busca e intenta instalarlas con confirmaciones en terminal."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_system",
            "description": "Actualiza el sistema operativo Ubuntu y sus paquetes. Por defecto abre la interfaz grafica del Actualizador de Software (update-manager) o una terminal interactiva si el usuario lo pide o si no hay GUI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["gui", "terminal"],
                        "description": "gui para abrir el Gestor de Actualizaciones visual de Ubuntu (update-manager); terminal para abrir una consola interactiva ejecutando apt upgrade."
                    }
                },
                "required": ["mode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_deb_package",
            "description": "Busca e instala automáticamente un paquete de software descargado (.deb) en la carpeta Descargas o Downloads mediante dpkg y apt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Nombre o palabra clave del paquete a instalar (ej: wps-office, chrome, cursor, discord)."
                    }
                },
                "required": ["package_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_software_center",
            "description": "Abre la Tienda de Software / Centro de Aplicaciones de Ubuntu para buscar o instalar programas graficamente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Nombre de la aplicacion a buscar en la tienda (opcional)."
                    },
                    "mode": {
                        "type": "string",
                        "description": "Modo opcional, por ejemplo 'installed' o 'manage' para ver y desinstalar aplicaciones instaladas."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Abre una aplicacion de escritorio instalada en Ubuntu. Soporta ejecutables normales, apps Flatpak/Snap conocidas y referencias como 'la aplicacion que instalaste ahora'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Nombre de la aplicacion a abrir (ej: terminal, explorador, navegador, calculadora, monitor, configuracion, editor)."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_terminal_command",
            "description": "Abre una ventana de terminal real en Ubuntu para ejecutar interactivamente un comando que requiere interacción del usuario, sudo, o es de larga duración (ej: sudo apt install htop, htop, ping google.com). NO usar para comandos de solo lectura/diagnóstico rápido como ls, df, free, cat, ip a — para esos usar run_command_silent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "El comando exacto a ejecutar en la terminal."
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Breve explicacion de que hace el comando."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Consulta el uso en tiempo real de memoria RAM, espacio en disco, tiempo encendido y estado del sistema Linux.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_diagnostic",
            "description": (
                "Ejecuta un diagnóstico de SOLO LECTURA predefinido y muestra su salida en el chat. "
                "Es la opción preferida para consultar el estado del equipo: elige un nombre del catálogo, "
                "no escribas comandos. Catálogo: " + catalog_description() + "."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": list(DIAGNOSTICS),
                        "description": "Nombre del diagnóstico del catálogo.",
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command_silent",
            "description": "ÚLTIMO RECURSO: solo si ningún diagnóstico de run_diagnostic sirve. Ejecuta una consulta de solo lectura no interactiva (sin sudo) y muestra la salida en el chat. Solo se permiten comandos de consulta conocidos (ls, df, free, ip, cat de archivos normales, uname, ps, lsblk, lscpu, find sin -exec, grep, etc.) y subcomandos de lectura como `systemctl status` o `snap list`. Se bloquean variables de entorno, credenciales, intérpretes y cualquier cambio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "El comando exacto a ejecutar (sin sudo). Ejemplo: 'ls -la ~/Documentos', 'cat /etc/os-release'."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_service",
            "description": "Gestiona servicios del sistema Linux con systemd: iniciar, detener, reiniciar, ver estado, habilitar o deshabilitar un servicio (ej: nginx, ssh, bluetooth, NetworkManager, cups).",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Nombre del servicio systemd (ej: ssh, nginx, bluetooth, cups, NetworkManager)."
                    },
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop", "restart", "status", "enable", "disable"],
                        "description": "Acción a realizar sobre el servicio."
                    }
                },
                "required": ["service_name", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_package",
            "description": "Busca paquetes disponibles en los repositorios apt de Ubuntu sin instalar nada. Útil para descubrir el nombre exacto de un paquete antes de instalarlo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Término de búsqueda del paquete (ej: vlc, python3, nodejs, ffmpeg)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_package",
            "description": "Prepara la desinstalacion de una aplicacion normal y solicita confirmacion al usuario. Usa auto si el usuario no indico el gestor. La aplicacion solo ejecutara la desinstalacion tras confirmar en un turno posterior. Bloquea paquetes criticos del sistema operativo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Nombre exacto de la app o paquete a desinstalar (ej: vlc, zed, waydroid, office365WebDesktop, org.app.Id)."
                    },
                    "source": {
                        "type": "string",
                        "enum": ["auto", "apt", "snap", "flatpak", "desktop"],
                        "description": "Gestor donde esta instalada la app. Usa auto si el usuario no lo especifica. Usa desktop para lanzadores locales en ~/.local/share/applications."
                    }
                },
                "required": ["package_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lee y muestra el contenido de un archivo de texto en el chat. Útil para ver archivos de configuración, logs, scripts, etc. (ej: ~/.bashrc, /etc/hosts, ~/script.sh).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Ruta absoluta o relativa al archivo a leer (soporta ~ para home). Ejemplo: '~/.bashrc', '/etc/hosts'."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Crea o sobreescribe un archivo de texto dentro de la carpeta personal del usuario (notas, scripts, configuración personal). No permite escribir fuera de ~ (/etc, /usr, /opt...) ni en credenciales (~/.ssh), autoarranque o archivos del propio asistente. Antes de sobrescribir se guarda una copia y el cambio se puede deshacer con undo_last_change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Ruta del archivo a crear o sobreescribir (soporta ~). Ejemplo: '~/scripts/mi_script.sh', '~/notas.txt'."
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenido de texto a escribir en el archivo."
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "undo_last_change",
            "description": "Deshace el último archivo escrito por el asistente (write_file), restaurando su copia anterior o eliminándolo si lo creó el asistente. No sobrescribe si el archivo cambió después. Úsala cuando el usuario pida deshacer, revertir o recuperar el último cambio.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]


def _audit_arguments(name: str, arguments: Dict[str, Any]) -> str:
    """Evita persistir el contenido de archivos en la auditoría de herramientas."""
    if name == "write_file":
        return (
            f"file_path={arguments.get('file_path', '')}; "
            f"content_length={len(str(arguments.get('content', '')))}"
        )
    return str(arguments)


def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    if not isinstance(arguments, dict):
        arguments = {}
    audit_arguments = _audit_arguments(name, arguments)
    decision = authorize_tool(name, arguments)
    if decision.is_blocked:
        result = f"⛔ {decision.message}"
        log_tool_run(name, audit_arguments[:500], result, status="blocked")
        return result

    if name == "install_program":
        program_name = arguments.get("program_name", "")
        preferred_source = arguments.get("preferred_source", "auto")
        result = tool_install_program(
            program_name,
            preferred_source,
            prepared_plan=arguments.get("_prepared_install_plan"),
        )
    elif name == "manage_firmware":
        action = arguments.get("action", "check")
        result = tool_manage_firmware(action)
    elif name == "update_system":
        mode = arguments.get("mode", "gui")
        result = tool_update_system(mode)
    elif name == "install_deb_package":
        package_name = arguments.get("package_name", "")
        result = tool_install_deb_package(package_name)
    elif name == "open_software_center":
        app_name = arguments.get("app_name", "")
        mode = arguments.get("mode", "")
        result = tool_open_software_center(app_name, mode=mode)
    elif name == "open_application":
        app_name = arguments.get("app_name", "")
        result = tool_open_application(app_name)
    elif name == "open_terminal_command":
        command = arguments.get("command", "")
        explanation = arguments.get("explanation", "")
        result = tool_open_terminal_command(command, explanation)
    elif name == "get_system_status":
        result = tool_get_system_status()
    elif name == "run_command_silent":
        command = arguments.get("command", "")
        result, stdout, stderr, exit_code = _run_command_silent(command)
    elif name == "manage_service":
        service_name = arguments.get("service_name", "")
        action = arguments.get("action", "status")
        result = tool_manage_service(service_name, action)
    elif name == "search_package":
        query = arguments.get("query", "")
        result = tool_search_package(query)
    elif name == "remove_package":
        package_name = arguments.get("package_name", "")
        source = arguments.get("source", "auto")
        result = tool_remove_package(package_name, source)
    elif name == "read_file":
        file_path = arguments.get("file_path", "")
        result = tool_read_file(file_path)
    elif name == "write_file":
        file_path = arguments.get("file_path", "")
        content = arguments.get("content", "")
        result = tool_write_file(file_path, content)
    elif name == "undo_last_change":
        result = tool_undo_last_change()
    elif name == "run_diagnostic":
        result, stdout, stderr, exit_code = run_diagnostic(arguments.get("name"))
    else:
        result = f"Herramienta '{name}' no reconocida."

    if name in {"run_command_silent", "run_diagnostic"}:
        log_tool_run(
            name,
            audit_arguments,
            result,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )
    else:
        log_tool_run(name, audit_arguments, result)
    return result

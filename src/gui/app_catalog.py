"""Catálogo de aplicaciones APT, DNF, Pacman, Zypper, Snap y Flatpak."""

from __future__ import annotations

import base64
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse


CATEGORIES = {
    "all": "Todas",
    "internet": "Internet",
    "office": "Oficina",
    "multimedia": "Multimedia",
    "development": "Desarrollo",
    "design": "Diseño",
    "communication": "Comunicación",
    "games": "Juegos",
    "utilities": "Utilidades",
    "system": "Sistema",
    "other": "Otros paquetes",
}


def _app(source: str, package: str, name: str, description: str, category: str) -> dict[str, str]:
    return {
        "source": source,
        "package": package,
        "name": name,
        "description": description,
        "category": category,
    }


CURATED_APPS = [
    _app("apt", "firefox", "Firefox", "Navegador web privado y extensible.", "internet"),
    _app("apt", "chromium-browser", "Chromium", "Navegador web de código abierto.", "internet"),
    _app("apt", "thunderbird", "Thunderbird", "Correo, calendario y contactos.", "communication"),
    _app("apt", "filezilla", "FileZilla", "Cliente gráfico para FTP y SFTP.", "internet"),
    _app("apt", "libreoffice", "LibreOffice", "Suite completa de documentos y hojas de cálculo.", "office"),
    _app("apt", "vlc", "VLC", "Reproductor multimedia compatible con muchos formatos.", "multimedia"),
    _app("apt", "audacity", "Audacity", "Grabación y edición de audio.", "multimedia"),
    _app("apt", "kdenlive", "Kdenlive", "Editor de video no lineal.", "multimedia"),
    _app("apt", "obs-studio", "OBS Studio", "Grabación de pantalla y transmisiones.", "multimedia"),
    _app("apt", "gimp", "GIMP", "Edición avanzada de imágenes.", "design"),
    _app("apt", "inkscape", "Inkscape", "Diseño e ilustración vectorial.", "design"),
    _app("apt", "blender", "Blender", "Modelado, animación y renderizado 3D.", "design"),
    _app("apt", "git", "Git", "Control de versiones distribuido.", "development"),
    _app("apt", "nodejs", "Node.js", "Entorno de JavaScript para desarrollo.", "development"),
    _app("apt", "docker.io", "Docker", "Contenedores para desarrollo y servidores.", "development"),
    _app("apt", "steam", "Steam", "Biblioteca y tienda de videojuegos.", "games"),
    _app("apt", "lutris", "Lutris", "Gestor de juegos para Linux.", "games"),
    _app("apt", "keepassxc", "KeePassXC", "Gestor local de contraseñas.", "utilities"),
    _app("apt", "timeshift", "Timeshift", "Instantáneas y restauración del sistema.", "system"),
    _app("apt", "htop", "Htop", "Monitor interactivo de procesos.", "system"),
    _app("apt", "gparted", "GParted", "Gestión gráfica de particiones.", "system"),
    _app("snap", "code", "Visual Studio Code", "Editor para programación y extensiones.", "development"),
    _app("snap", "postman", "Postman", "Pruebas y documentación de APIs.", "development"),
    _app("snap", "pycharm-community", "PyCharm Community", "IDE gratuito para Python.", "development"),
    _app("snap", "spotify", "Spotify", "Música, podcasts y listas de reproducción.", "multimedia"),
    _app("snap", "vlc", "VLC", "Reproductor multimedia universal.", "multimedia"),
    _app("snap", "obs-studio", "OBS Studio", "Grabación y transmisiones en directo.", "multimedia"),
    _app("snap", "discord", "Discord", "Comunidades, chat y llamadas.", "communication"),
    _app("snap", "slack", "Slack", "Mensajería para equipos de trabajo.", "communication"),
    _app("snap", "telegram-desktop", "Telegram", "Mensajería rápida y sincronizada.", "communication"),
    _app("snap", "chromium", "Chromium", "Navegador web de código abierto.", "internet"),
    _app("snap", "onlyoffice-desktopeditors", "ONLYOFFICE", "Documentos compatibles con Microsoft Office.", "office"),
    _app("snap", "bitwarden", "Bitwarden", "Gestor de contraseñas sincronizado.", "utilities"),
    _app("snap", "steam", "Steam", "Plataforma de videojuegos.", "games"),
    _app("flatpak", "org.mozilla.firefox", "Firefox", "Navegador web desde Flathub.", "internet"),
    _app("flatpak", "com.google.Chrome", "Google Chrome", "Navegador web de Google.", "internet"),
    _app("flatpak", "org.libreoffice.LibreOffice", "LibreOffice", "Suite de oficina completa.", "office"),
    _app("flatpak", "org.onlyoffice.desktopeditors", "ONLYOFFICE", "Edición moderna de documentos.", "office"),
    _app("flatpak", "org.videolan.VLC", "VLC", "Reproductor multimedia universal.", "multimedia"),
    _app("flatpak", "org.audacityteam.Audacity", "Audacity", "Grabación y edición de audio.", "multimedia"),
    _app("flatpak", "org.kde.kdenlive", "Kdenlive", "Edición profesional de video.", "multimedia"),
    _app("flatpak", "com.obsproject.Studio", "OBS Studio", "Grabación y transmisiones.", "multimedia"),
    _app("flatpak", "org.gimp.GIMP", "GIMP", "Edición avanzada de imágenes.", "design"),
    _app("flatpak", "org.inkscape.Inkscape", "Inkscape", "Ilustración vectorial.", "design"),
    _app("flatpak", "org.blender.Blender", "Blender", "Creación y animación 3D.", "design"),
    _app("flatpak", "com.visualstudio.code", "Visual Studio Code", "Editor para programación.", "development"),
    _app("flatpak", "io.podman_desktop.PodmanDesktop", "Podman Desktop", "Contenedores y Kubernetes.", "development"),
    _app("flatpak", "com.discordapp.Discord", "Discord", "Comunidades, chat y llamadas.", "communication"),
    _app("flatpak", "org.telegram.desktop", "Telegram", "Mensajería multiplataforma.", "communication"),
    _app("flatpak", "com.spotify.Client", "Spotify", "Música y podcasts.", "multimedia"),
    _app("flatpak", "com.valvesoftware.Steam", "Steam", "Plataforma de videojuegos.", "games"),
    _app("flatpak", "net.lutris.Lutris", "Lutris", "Biblioteca de juegos para Linux.", "games"),
    _app("flatpak", "com.bitwarden.desktop", "Bitwarden", "Gestor de contraseñas.", "utilities"),
    _app("flatpak", "org.keepassxc.KeePassXC", "KeePassXC", "Contraseñas locales y cifradas.", "utilities"),
    _app("flatpak", "md.obsidian.Obsidian", "Obsidian", "Notas enlazadas en Markdown.", "office"),
]


CATEGORY_KEYWORDS = {
    "internet": ("browser", "navegador", "internet", "web", "torrent", "ftp", "network"),
    "office": ("office", "document", "spreadsheet", "notes", "notas", "calendar", "pdf"),
    "multimedia": ("audio", "video", "media", "music", "música", "player", "stream", "podcast"),
    "development": ("developer", "development", "editor", "ide", "code", "programming", "git", "database"),
    "design": ("design", "graphics", "image", "photo", "drawing", "3d", "cad", "animation"),
    "communication": ("chat", "messaging", "mail", "correo", "call", "social", "conference"),
    "games": ("game", "gaming", "steam", "emulator"),
    "system": ("system", "driver", "backup", "partition", "monitor", "security", "kernel"),
}


# Los identificadores permiten reutilizar los iconos a color de AppStream/Flathub
# para la misma aplicacion aunque se instale desde APT o Snap.
ICON_ALIASES = {
    "audacity": "org.audacityteam.Audacity",
    "bitwarden": "com.bitwarden.desktop",
    "blender": "org.blender.Blender",
    "chromium": "org.chromium.Chromium",
    "chromium-browser": "org.chromium.Chromium",
    "chrome": "com.google.Chrome",
    "code": "com.visualstudio.code",
    "discord": "com.discordapp.Discord",
    "filezilla": "org.filezillaproject.Filezilla",
    "firefox": "org.mozilla.firefox",
    "gimp": "org.gimp.GIMP",
    "inkscape": "org.inkscape.Inkscape",
    "keepassxc": "org.keepassxc.KeePassXC",
    "krita": "org.kde.krita",
    "dolphin": "org.kde.dolphin",
    "gnome-disk-utility": "org.gnome.DiskUtility",
    "gnome-logs": "org.gnome.Logs",
    "gnome-system-monitor": "org.gnome.SystemMonitor",
    "gnome-text-editor": "org.gnome.TextEditor",
    "kate": "org.kde.kate",
    "flameshot": "org.flameshot.Flameshot",
    "kdenlive": "org.kde.kdenlive",
    "libreoffice": "org.libreoffice.LibreOffice",
    "lutris": "net.lutris.Lutris",
    "obs-studio": "com.obsproject.Studio",
    "onlyoffice-desktopeditors": "org.onlyoffice.desktopeditors",
    "postman": "com.getpostman.Postman",
    "pycharm-community": "com.jetbrains.PyCharm-Community",
    "slack": "com.slack.Slack",
    "spotify": "com.spotify.Client",
    "steam": "com.valvesoftware.Steam",
    "telegram-desktop": "org.telegram.desktop",
    "thunderbird": "org.mozilla.Thunderbird",
    "vlc": "org.videolan.VLC",
}

BRAND_ICON_URLS = {
    "docker.io": "https://cdn.simpleicons.org/docker/2496ED",
    "git": "https://cdn.simpleicons.org/git/F05032",
    "nodejs": "https://cdn.simpleicons.org/nodedotjs/5FA04E",
    "pycharm-community": "https://cdn.simpleicons.org/pycharm/21D789",
}

_icon_index: dict[str, Path] | None = None
_icon_lock = threading.Lock()

_installed_cache: dict[str, set[str]] | None = None
_installed_cache_time = 0.0
_installed_lock = threading.Lock()
_catalog_cache: dict[tuple[str, str, str], tuple[float, list[dict[str, str]], str]] = {}
_catalog_lock = threading.Lock()
_catalog_ttl = 600


def _index_icon(path: Path, index: dict[str, Path]) -> None:
    if path.suffix.lower() not in {".png", ".svg"}:
        return
    stem = path.stem.lower()
    index.setdefault(stem, path)
    if "_" in stem:
        package, icon_name = stem.split("_", 1)
        index.setdefault(package, path)
        index.setdefault(icon_name, path)


def _system_icon_index() -> dict[str, Path]:
    global _icon_index
    with _icon_lock:
        if _icon_index is not None:
            return _icon_index

        index: dict[str, Path] = {}
        locations = (
            (Path("/var/lib/flatpak/appstream"), "*/*/*/icons/128x128/*"),
            (Path.home() / ".local/share/flatpak/appstream", "*/*/*/icons/128x128/*"),
            (Path("/var/lib/flatpak/appstream"), "*/*/*/icons/64x64/*"),
            (Path.home() / ".local/share/flatpak/appstream", "*/*/*/icons/64x64/*"),
            (Path("/usr/share/icons/hicolor"), "256x256/apps/*"),
            (Path("/usr/share/icons/hicolor"), "128x128/apps/*"),
            (Path("/usr/share/icons/hicolor"), "64x64/apps/*"),
            (Path("/usr/share/icons/hicolor"), "scalable/apps/*"),
            (Path("/var/lib/app-info/icons"), "*/64x64/*"),
            (Path("/var/lib/app-info/icons"), "*/48x48/*"),
            (Path("/usr/share/pixmaps"), "*"),
        )
        for root, pattern in locations:
            if not root.exists():
                continue
            for path in root.glob(pattern):
                if path.is_file():
                    _index_icon(path, index)

        _icon_index = index
        return index


@lru_cache(maxsize=256)
def _file_as_data_uri(path_text: str) -> str:
    path = Path(path_text)
    try:
        if path.stat().st_size > 512_000:
            return ""
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""
    mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    return f"data:{mime};base64,{payload}"


def _icon_data(app: dict[str, str]) -> str:
    if app.get("icon"):
        return app["icon"]
    package = app["package"]
    if app["source"] == "snap":
        for suffix in ("icon.svg", "icon.png"):
            snap_icon = Path("/snap") / package / "current/meta/gui" / suffix
            if snap_icon.is_file():
                return _file_as_data_uri(str(snap_icon))

    index = _system_icon_index()
    package_key = package.lower()
    aliases = [ICON_ALIASES.get(package_key, ""), package]
    if app["source"] == "flatpak":
        aliases.insert(0, package)
    aliases.extend(
        (
            app["name"],
            re.sub(r"[^a-z0-9]+", "-", app["name"].lower()).strip("-"),
        )
    )
    for alias in aliases:
        path = index.get(alias.lower()) if alias else None
        if path:
            return _file_as_data_uri(str(path))

    if package_key in BRAND_ICON_URLS:
        return BRAND_ICON_URLS[package_key]
    app_id = package if app["source"] == "flatpak" and app.get("origin") == "flathub" else ICON_ALIASES.get(package_key, "")
    if app_id and re.fullmatch(r"[A-Za-z0-9._-]+", app_id):
        return f"https://dl.flathub.org/repo/appstream/x86_64/icons/128x128/{app_id}.png"
    return ""


_WINDOWS_GUIDE_ICON_PACKAGES = {
    "libreoffice-writer": "libreoffice",
    "libreoffice-calc": "libreoffice",
    "libreoffice-impress": "libreoffice",
    "onlyoffice": "onlyoffice-desktopeditors",
    "chrome": "chrome",
    "visual-studio-code": "code",
}


def get_app_icon(package: str) -> str:
    """Return the same AppStream/store icon used by the application catalog."""
    package_key = (package or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9._+-]{1,100}", package_key):
        return ""
    canonical = _WINDOWS_GUIDE_ICON_PACKAGES.get(package_key, package_key)
    app = next((entry for entry in CURATED_APPS if entry["package"].lower() == canonical), None)
    if app is None:
        app = _app("apt", canonical, canonical, "", "other")
    return _icon_data(app)


def _run(args: list[str], timeout: int = 8) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return ""
    return result.stdout or ""


def _run_checked(args: list[str], timeout: int = 12) -> tuple[str, str]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "", str(exc)
    return (result.stdout, "") if result.returncode == 0 else ("", result.stderr.strip() or "No se pudo consultar el repositorio.")


def _installed_packages(force: bool = False) -> dict[str, set[str]]:
    global _installed_cache, _installed_cache_time
    with _installed_lock:
        if not force and _installed_cache and time.monotonic() - _installed_cache_time < 20:
            return _installed_cache

        apt = set()
        for line in _run(["dpkg-query", "-W", "-f=${Status}\t${binary:Package}\n"], timeout=10).splitlines():
            status, _, package = line.partition("\t")
            if status == "install ok installed" and package:
                apt.add(package.split(":", 1)[0])
        snap_lines = _run(["snap", "list"], timeout=5).splitlines() if shutil.which("snap") else []
        snap = {line.split()[0] for line in snap_lines[1:] if line.split()}
        flatpak = {
            line.strip()
            for line in _run(["flatpak", "list", "--app", "--columns=application"], timeout=6).splitlines()
            if line.strip()
        } if shutil.which("flatpak") else set()

        rpm_packages = set(_run(["rpm", "-qa", "--qf", "%{NAME}\n"], timeout=12).splitlines()) if shutil.which("rpm") else set()
        pacman_packages = set(_run(["pacman", "-Qq"], timeout=12).splitlines()) if shutil.which("pacman") else set()

        _installed_cache = {
            "apt": apt,
            "dnf": rpm_packages,
            "pacman": pacman_packages,
            "zypper": rpm_packages,
            "snap": snap,
            "flatpak": flatpak,
        }
        _installed_cache_time = time.monotonic()
        return _installed_cache


def _guess_category(name: str, description: str) -> str:
    text = f"{name} {description}".lower()
    for category, words in CATEGORY_KEYWORDS.items():
        if any(word in text for word in words):
            return category
    return "other"


_package_pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+_-]*\Z")
_flatpak_pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_curated = {(item["source"], item["package"].lower()): item for item in CURATED_APPS}
_curated_order = {(item["source"], item["package"].lower()): index for index, item in enumerate(CURATED_APPS)}


def _load_apt(query: str = "") -> tuple[list[dict[str, str]], str]:
    output, error = _run_checked(["apt-cache", "search", query or "."], timeout=20)
    if error:
        return [], f"APT: {error}"
    apps = []
    for line in output.splitlines():
        package, separator, description = line.partition(" - ")
        if separator and _package_pattern.fullmatch(package):
            known = _curated.get(("apt", package.lower()))
            name = known["name"] if known else package
            category = known["category"] if known else _guess_category(package, description)
            apps.append(_app("apt", package, name, description, category))
    return apps, ""


_rpm_arches = {"x86_64", "i686", "i586", "aarch64", "armv7hl", "noarch", "ppc64le", "s390x"}


def _native_app(source: str, package: str, description: str) -> dict[str, str]:
    known = _curated.get((source, package.lower())) or _curated.get(("apt", package.lower()))
    name = known["name"] if known else package
    category = known["category"] if known else _guess_category(name, description)
    return _app(source, package, name, description or (known["description"] if known else ""), category)


def _clean_rpm_name(package: str) -> str:
    name, dot, architecture = package.rpartition(".")
    return name if dot and architecture in _rpm_arches else package


def _load_dnf(query: str) -> tuple[list[dict[str, str]], str]:
    if query:
        output, error = _run_checked(["dnf", "search", "--quiet", query], timeout=25)
        if error:
            return [], f"DNF: {error}"
        apps = []
        for line in output.splitlines():
            match = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9+._-]*)\s*:\s*(.*)$", line)
            if not match:
                continue
            package = _clean_rpm_name(match.group(1))
            apps.append(_native_app("dnf", package, match.group(2).strip()))
        return apps, ""

    output, error = _run_checked(
        ["dnf", "repoquery", "--available", "--qf", "%{name}\t%{summary}"], timeout=30
    )
    if error:
        output, error = _run_checked(["dnf", "list", "--available", "--quiet"], timeout=30)
        if error:
            return [], f"DNF: No se pudo consultar el catálogo. {error}"
        apps = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            package = _clean_rpm_name(parts[0])
            if _package_pattern.fullmatch(package):
                apps.append(_native_app("dnf", package, ""))
        return apps, "DNF no pudo mostrar descripciones; se muestran nombres de paquetes."
    apps = []
    for line in output.splitlines():
        package, separator, summary = line.partition("\t")
        if separator and _package_pattern.fullmatch(package):
            apps.append(_native_app("dnf", package, summary.strip()))
    return apps, ""


def _load_pacman(query: str) -> tuple[list[dict[str, str]], str]:
    output, error = _run_checked(["pacman", "-Ss", query or "."], timeout=25)
    if error:
        return [], f"Pacman: {error}"
    apps = []
    lines = output.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^([^/\s]+)/([^\s]+)\s+([^\s]+)$", line)
        if not match:
            continue
        package = match.group(2)
        if not _package_pattern.fullmatch(package):
            continue
        description = lines[index + 1].strip() if index + 1 < len(lines) and lines[index + 1][:1].isspace() else ""
        apps.append(_native_app("pacman", package, description))
    return apps, ""


def _load_zypper(query: str) -> tuple[list[dict[str, str]], str]:
    args = ["zypper", "--no-refresh", "search", "--details", "--type", "package"]
    if query:
        args.append(query)
    output, error = _run_checked(args, timeout=25)
    if error:
        return [], f"Zypper: {error}"

    apps = []
    columns = None
    for line in output.splitlines():
        if "|" not in line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if "Name" in parts and "Summary" in parts:
            columns = (parts.index("Name"), parts.index("Summary"))
            continue
        if columns is None or len(parts) <= max(columns):
            continue
        package, summary = parts[columns[0]], parts[columns[1]]
        if _package_pattern.fullmatch(package):
            apps.append(_native_app("zypper", package, summary))
    return apps, ""


def _load_flatpak() -> tuple[list[dict[str, str]], str]:
    args = ["flatpak", "remote-ls", "--app", "--columns=application,name,description,origin"]
    output, error = _run_checked(args, timeout=18)
    notice = ""
    if error:
        output, cached_error = _run_checked(args[:2] + ["--cached"] + args[2:], timeout=12)
        if cached_error:
            return [], f"Flatpak: {error}"
        notice = "Flatpak: se muestran datos guardados; no se pudo actualizar la tienda."
    apps = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        package = parts[0].strip()
        if not _flatpak_pattern.fullmatch(package):
            continue
        known = _curated.get(("flatpak", package.lower()))
        name = parts[1].strip() or (known["name"] if known else package)
        description = parts[2].strip() if len(parts) > 2 else ""
        origin = parts[3].strip() if len(parts) > 3 else ""
        category = known["category"] if known else _guess_category(name, description)
        app = _app("flatpak", package, name, description, category)
        app["origin"] = origin
        apps.append(app)
    if not apps and not notice:
        notice = "Flatpak: no hay aplicaciones en los repositorios configurados."
    return apps, notice


class _SnapdConnection(http.client.HTTPConnection):
    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect("/run/snapd.socket")


_snap_sections = {
    "office": "productivity",
    "multimedia": "music-and-audio",
    "development": "development",
    "design": "art-and-design",
    "communication": "social",
    "games": "games",
    "utilities": "utilities",
    "system": "security",
}

_snap_categories = {
    "productivity": "office",
    "music-and-audio": "multimedia",
    "photo-and-video": "multimedia",
    "art-and-design": "design",
    "development": "development",
    "social": "communication",
    "games": "games",
    "utilities": "utilities",
    "security": "system",
}


def _snapd_find(query: str, category: str) -> list[dict[str, str]]:
    params = {"q": query} if query else ({"q": "browser"} if category == "internet" else {"section": _snap_sections.get(category, "featured")})
    connection = _SnapdConnection("localhost", timeout=9)
    try:
        connection.request("GET", f"/v2/find?{urlencode(params)}")
        response = connection.getresponse()
        payload = json.loads(response.read())
        if response.status != 200 or not isinstance(payload.get("result"), list):
            raise ValueError("La tienda Snap no respondió correctamente.")
    finally:
        connection.close()

    apps = []
    for item in payload["result"]:
        if not isinstance(item, dict):
            continue
        package = item.get("name", "")
        if not isinstance(package, str) or not _package_pattern.fullmatch(package):
            continue
        known = _curated.get(("snap", package.lower()))
        name = item.get("title") or (known["name"] if known else package)
        description = item.get("summary") or (known["description"] if known else "")
        categories = {value.get("name", "") for value in (item.get("categories") or []) if isinstance(value, dict)}
        detected = next((_snap_categories[value] for value in sorted(categories) if value in _snap_categories), None)
        guessed = _guess_category(name, description)
        app_category = known["category"] if known else (guessed if guessed != "other" else (detected or "other"))
        app = _app("snap", package, name, description, app_category)
        icon = item.get("icon") or ""
        parsed = urlparse(icon)
        if parsed.scheme == "https" and (parsed.hostname == "snapcraft.io" or (parsed.hostname or "").endswith(".snapcraft.io")):
            app["icon"] = icon
        publisher = item.get("publisher") or {}
        app["verified"] = publisher.get("validation") == "verified"
        apps.append(app)
    return apps


def _load_snap(query: str, category: str) -> tuple[list[dict[str, str]], str]:
    try:
        if not query and category == "all":
            browse_categories = (
                "all", "internet", "office", "multimedia", "development",
                "design", "communication", "games", "utilities", "system",
            )
            unique: dict[str, dict[str, str]] = {}
            failures = 0
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(_snapd_find, "", section) for section in browse_categories]
                for future in as_completed(futures):
                    try:
                        for app in future.result():
                            unique.setdefault(app["package"], app)
                    except (OSError, ValueError, http.client.HTTPException) as exc:
                        failures += 1
                        last_error = exc
            if unique:
                notice = "Snap: algunas secciones no respondieron." if failures else ""
                return list(unique.values()), notice
            raise last_error if failures else ValueError("La tienda Snap no devolvió aplicaciones.")
        return _snapd_find(query, category), ""
    except (OSError, ValueError, http.client.HTTPException, socket.timeout) as exc:
        args = ["snap", "find"] + ([query] if query else [])
        output, fallback_error = _run_checked(args, timeout=12)
        if fallback_error:
            return [], f"Snap: {exc}"
        apps = []
        for line in output.splitlines()[1:]:
            parts = line.split(None, 4)
            if parts and _package_pattern.fullmatch(parts[0]):
                known = _curated.get(("snap", parts[0].lower()))
                description = parts[4] if len(parts) == 5 else ""
                name = known["name"] if known else parts[0]
                app_category = known["category"] if known else _guess_category(name, description)
                apps.append(_app("snap", parts[0], name, description, app_category))
        return apps, "Snap: se muestran resultados de la búsqueda básica."


def _source_catalog(source: str, query: str, category: str, refresh: bool) -> tuple[list[dict[str, str]], str]:
    filtered_source = source in {"apt", "dnf", "pacman", "zypper", "snap"}
    key = (source, query.strip().lower() if filtered_source else "", category if source == "snap" else "")
    with _catalog_lock:
        cached = _catalog_cache.get(key)
        if cached and not refresh and time.monotonic() - cached[0] < _catalog_ttl:
            return cached[1], cached[2]
    if source == "apt":
        apps, notice = _load_apt(query)
    elif source == "dnf":
        apps, notice = _load_dnf(query)
    elif source == "pacman":
        apps, notice = _load_pacman(query)
    elif source == "zypper":
        apps, notice = _load_zypper(query)
    elif source == "flatpak":
        apps, notice = _load_flatpak()
    else:
        apps, notice = _load_snap(query, category)
    if apps:
        with _catalog_lock:
            _catalog_cache[key] = (time.monotonic(), apps, notice)
    return apps, notice


def get_catalog(
    source: str = "all",
    category: str = "all",
    query: str = "",
    offset: int = 0,
    limit: int = 36,
    refresh_installed: bool = False,
) -> dict[str, Any]:
    managers = ("apt", "dnf", "pacman", "zypper", "snap", "flatpak")
    source = source if source in {"all", *managers} else "all"
    category = category if category in CATEGORIES else "all"
    query = query.strip()[:100]
    offset = max(0, int(offset))
    limit = min(40, max(4, int(limit)))

    available = {
        "apt": shutil.which("apt-cache") is not None,
        "dnf": shutil.which("dnf") is not None,
        "pacman": shutil.which("pacman") is not None,
        "zypper": shutil.which("zypper") is not None,
        "snap": shutil.which("snap") is not None,
        "flatpak": shutil.which("flatpak") is not None,
    }
    try:
        from src.core.distro import detect_distro
        distro = detect_distro()
        distro_name = distro.pretty_name
        recommended_source = distro.native_package_manager
    except Exception:
        distro_name = "Linux"
        recommended_source = "apt"
    if not available.get(recommended_source):
        recommended_source = next((manager for manager in managers if available[manager]), "")
    selected = [key for key in managers if available[key] and source in {"all", key}]
    batches = []
    if selected:
        with ThreadPoolExecutor(max_workers=len(selected)) as executor:
            batches = list(executor.map(lambda key: _source_catalog(key, query, category, refresh_installed), selected))
    apps = [app for batch, _ in batches for app in batch]
    notices = [notice for _, notice in batches if notice]
    if source != "all" and not available[source]:
        notices.append(f"{source.upper()} no está instalado en este equipo.")
    if source in {"all", "snap"} and available["snap"]:
        notices.append("Snap muestra resultados por secciones y búsqueda; no es un inventario completo de su tienda.")

    normalized_query = query.lower()
    unique: dict[tuple[str, str], dict[str, str]] = {}
    for original in apps:
        app = dict(original)
        if source != "all" and app["source"] != source:
            continue
        if category != "all" and app["category"] != category:
            continue
        haystack = f"{app['name']} {app['package']} {app['description']}".lower()
        if normalized_query and normalized_query not in haystack:
            continue
        unique.setdefault((app["source"], app["package"].lower()), app)

    installed = _installed_packages(force=refresh_installed)
    ordered = list(unique.values())
    if normalized_query:
        def search_rank(item: dict[str, str]) -> tuple[int, int, str]:
            package = item["package"].lower()
            name = item["name"].lower()
            if normalized_query in {package, name}:
                exactness = 0
            elif package.startswith(normalized_query) or name.startswith(normalized_query):
                exactness = 1
            else:
                exactness = 2
            technical_penalty = 1 if package.startswith("lib") or package.endswith(("-dev", "-dbg", "-doc")) else 0
            return exactness, technical_penalty, name

        ordered.sort(key=search_rank)
    elif source == "all":
        order = [recommended_source, "apt", "dnf", "pacman", "zypper", "snap", "flatpak"]
        order = list(dict.fromkeys(key for key in order if key in managers))
        recommendations = {key: [] for key in order}
        remaining = []
        for item in ordered:
            rank = _curated_order.get((item["source"], item["package"].lower()))
            if rank is None and item["source"] in {"dnf", "pacman", "zypper"}:
                rank = _curated_order.get(("apt", item["package"].lower()))
            if rank is not None:
                recommendations[item["source"]].append((rank, item))
            else:
                remaining.append(item)
        for group in recommendations.values():
            group.sort(key=lambda entry: entry[0])
        ordered = []
        while any(recommendations.values()):
            for group in recommendations.values():
                if group:
                    ordered.append(group.pop(0)[1])
        ordered.extend(sorted(remaining, key=lambda item: (item["name"].lower(), item["source"])))
    else:
        ordered.sort(
            key=lambda item: (
                _curated_order.get(
                    (item["source"], item["package"].lower()),
                    _curated_order.get(("apt", item["package"].lower()), len(_curated_order))
                    if item["source"] in {"dnf", "pacman", "zypper"}
                    else len(_curated_order),
                ),
                item["name"].lower(),
            )
        )
    for app in ordered:
        app["installed"] = app["package"] in installed.get(app["source"], set())

    page = ordered[offset:offset + limit]
    for app in page:
        app["icon"] = _icon_data(app)
        app["recommended"] = app["source"] == recommended_source
    return {
        "apps": page,
        "total": len(ordered),
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(page) < len(ordered),
        "categories": CATEGORIES,
        "sources_available": available,
        "recommended_source": recommended_source,
        "distribution": distro_name,
        "notices": notices,
    }


def clear_installed_cache() -> None:
    global _installed_cache, _installed_cache_time
    with _installed_lock:
        _installed_cache = None
        _installed_cache_time = 0.0

"""Instalación local y reversible de AppImage para el usuario actual."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path


class AppImageError(ValueError):
    """Error de validación o instalación que se puede mostrar en la interfaz."""


def validate_appimage(path_text: str) -> Path:
    original = Path(path_text).expanduser()
    if original.is_symlink():
        raise AppImageError("No instalaré un AppImage que sea un enlace simbólico.")
    try:
        path = original.resolve(strict=True)
    except OSError as exc:
        raise AppImageError("No se encontró el archivo AppImage seleccionado.") from exc
    if not path.is_file() or path.suffix.lower() != ".appimage":
        raise AppImageError("Selecciona un archivo con extensión .AppImage.")
    try:
        with path.open("rb") as handle:
            magic = handle.read(4)
    except OSError as exc:
        raise AppImageError("No se pudo leer el archivo seleccionado.") from exc
    if magic != b"\x7fELF":
        raise AppImageError("El archivo no parece ser un AppImage ejecutable.")
    if path.stat().st_size < 1024:
        raise AppImageError("El archivo AppImage está incompleto o vacío.")
    return path


def _escape_desktop_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", " ").replace("\r", " ")


def _desktop_exec(path: Path) -> str:
    value = str(path).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
    return f'"{value}" %U'


def install_appimage(path_text: str) -> Path:
    """Copy an already selected AppImage into ~/Applications and add a launcher."""
    source = validate_appimage(path_text)
    home = Path.home().resolve()
    applications = home / "Applications"
    desktop_dir = home / ".local" / "share" / "applications"

    if applications.is_symlink() or desktop_dir.is_symlink():
        raise AppImageError("La carpeta destino es un enlace simbólico; no instalaré el archivo ahí.")
    if applications.resolve().parent != home or home not in desktop_dir.resolve().parents:
        raise AppImageError("La carpeta de instalación quedó fuera de tu carpeta personal.")
    try:
        applications.mkdir(mode=0o755, parents=True, exist_ok=True)
        desktop_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError as exc:
        raise AppImageError("No se pudieron preparar las carpetas de instalación en tu usuario.") from exc
    if applications.is_symlink() or desktop_dir.is_symlink():
        raise AppImageError("La carpeta destino cambió a un enlace simbólico; no instalaré el archivo ahí.")
    if applications.resolve().parent != home or home not in desktop_dir.resolve().parents:
        raise AppImageError("La carpeta de instalación quedó fuera de tu carpeta personal.")

    stem = source.stem
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-_").lower()[:64] or "appimage"
    display_name = _escape_desktop_value(re.sub(r"[._-]+", " ", stem).strip()[:80] or "Aplicación AppImage")
    destination = applications / f"{slug}.AppImage"
    desktop_file = desktop_dir / f"linuxmate-{slug}.desktop"
    if destination.exists() or desktop_file.exists():
        raise AppImageError("Ya existe una aplicación con ese nombre. Renombra el archivo y vuelve a elegirlo.")

    try:
        fd, temporary_name = tempfile.mkstemp(prefix=".linuxmate-", suffix=".AppImage", dir=applications)
        os.close(fd)
    except OSError as exc:
        raise AppImageError("No se pudo preparar el archivo de instalación.") from exc
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        temporary.chmod(0o755)
        os.replace(temporary, destination)
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={display_name}\n"
            f"Exec={_desktop_exec(destination)}\n"
            f"TryExec={_desktop_exec(destination).removesuffix(' %U')}\n"
            "Terminal=false\n"
            "Categories=Utility;\n"
            "StartupNotify=true\n"
        )
        desktop_file.write_text(content, encoding="utf-8")
        desktop_file.chmod(0o644)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        desktop_file.unlink(missing_ok=True)
        raise AppImageError("No se pudo copiar la aplicación al menú de aplicaciones.") from exc
    return destination

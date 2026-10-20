"""Copias personales en ZIP y restauración aislada para la interfaz web."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import tempfile
import threading
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


MAX_RESTORE_FILES = 100_000
MAX_RESTORE_BYTES = 500 * 1024**3
BLOCK_SIZE = 1024 * 1024

_CATEGORY_INFO: dict[str, dict[str, Any]] = {
    "documents": {"name": "Documentos", "xdg": "DOCUMENTS", "names": ("Documents", "Documentos")},
    "desktop": {"name": "Escritorio", "xdg": "DESKTOP", "names": ("Desktop", "Escritorio")},
    "downloads": {"name": "Descargas", "xdg": "DOWNLOAD", "names": ("Downloads", "Descargas")},
    "pictures": {"name": "Imágenes", "xdg": "PICTURES", "names": ("Pictures", "Imágenes", "Imagenes")},
    "music": {"name": "Música", "xdg": "MUSIC", "names": ("Music", "Música")},
    "videos": {"name": "Videos", "xdg": "VIDEOS", "names": ("Videos", "Vídeos", "Videos")},
}

_job_lock = threading.RLock()
_jobs: dict[str, dict[str, Any]] = {}
_active_job: str | None = None
_custom_sources: dict[str, dict[str, str]] = {}


class BackupError(RuntimeError):
    """Error seguro y legible para mostrar en la interfaz."""


def _home() -> Path:
    return Path.home().resolve()


def _restoration_parent() -> Path:
    home = _home()
    parent = home / "Restauraciones-LinuxMate"
    if parent.is_symlink():
        raise BackupError("La carpeta de restauración es un enlace simbólico; no escribiré ahí.")
    if parent.exists() and not parent.is_dir():
        raise BackupError("La ubicación de restauración ya existe como archivo; no la modificaré.")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    resolved = parent.resolve(strict=True)
    if resolved.parent != home:
        raise BackupError("La carpeta de restauración debe permanecer dentro de tu carpeta personal.")
    return resolved


def _data_dir() -> Path:
    directory = Path.home() / ".local" / "share" / "linuxmate" / "backup-manager"
    if directory.is_symlink():
        raise BackupError("La carpeta privada de respaldos es un enlace simbólico; no escribiré ahí.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    return directory


def _registry_path() -> Path:
    return _data_dir() / "backups.json"


def _timeshift_gui() -> str | None:
    return shutil.which("timeshift-gtk") or shutil.which("timeshift-launcher")


def _read_registry() -> list[dict[str, Any]]:
    path = _registry_path()
    if path.is_symlink() or not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [entry for entry in data if isinstance(entry, dict) and isinstance(entry.get("id"), str)] if isinstance(data, list) else []


def _save_registry(entries: list[dict[str, Any]]) -> None:
    path = _registry_path()
    if path.is_symlink():
        raise BackupError("El registro de respaldos es un enlace simbólico; no lo modificaré.")
    fd, temporary = tempfile.mkstemp(prefix=".backups-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(entries[-50:], handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _xdg_directory(key: str) -> Path | None:
    config = Path.home() / ".config" / "user-dirs.dirs"
    try:
        lines = config.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    pattern = re.compile(rf"^{re.escape(key)}=\"([^\"]*)\"$")
    for line in lines:
        match = pattern.match(line.strip())
        if not match:
            continue
        value = match.group(1).replace(r"\$", "$").replace(r"\`", "`").replace(r"\\", "\\")
        home = _home()
        if value == "$HOME":
            return home
        if value.startswith("$HOME/"):
            return home / value[6:]
        if value.startswith("~/"):
            return home / value[2:]
        candidate = Path(value).expanduser()
        return candidate if candidate.is_absolute() else None
    return None


def available_backup_sources() -> list[dict[str, str]]:
    """Devuelve carpetas personales conocidas, limitadas a ubicaciones dentro de HOME."""
    home = _home()
    found: list[dict[str, str]] = []
    seen: set[Path] = set()
    for category_id, info in _CATEGORY_INFO.items():
        candidates = [_xdg_directory(info["xdg"])]
        candidates.extend(home / name for name in info["names"])
        selected: Path | None = None
        for candidate in candidates:
            if candidate is None or candidate.is_symlink() or not candidate.is_dir():
                continue
            try:
                resolved = candidate.resolve(strict=True)
                if resolved == home or home not in resolved.parents or resolved in seen:
                    continue
            except OSError:
                continue
            selected = resolved
            seen.add(resolved)
            break
        if selected:
            found.append({"id": category_id, "name": info["name"], "path": str(selected)})
    return found


def register_custom_backup_source(path_text: str) -> dict[str, Any]:
    """Registra una carpeta escogida con el selector nativo, solo dentro del home."""
    if not isinstance(path_text, str) or not path_text.strip():
        return {"success": False, "message": "No se seleccionó una carpeta."}
    candidate = Path(path_text).expanduser()
    if candidate.is_symlink() or not candidate.is_dir():
        return {"success": False, "message": "Elige una carpeta normal dentro de tu carpeta personal."}
    try:
        source = candidate.resolve(strict=True)
        home = _home()
        if source == home or home not in source.parents:
            return {"success": False, "message": "Por seguridad, solo se pueden respaldar carpetas dentro de tu carpeta personal."}
    except OSError:
        return {"success": False, "message": "No se pudo abrir la carpeta seleccionada."}
    with _job_lock:
        if len(_custom_sources) >= 10:
            return {"success": False, "message": "Ya añadiste diez carpetas adicionales. Quita alguna y vuelve a intentarlo."}
        if any(Path(item["path"]) == source for item in _custom_sources.values()):
            return {"success": False, "message": "Esa carpeta ya está añadida."}
        if any(Path(item["path"]).resolve() == source for item in available_backup_sources()):
            return {"success": False, "message": "Esa carpeta ya aparece en las carpetas personales disponibles."}
        token = secrets.token_hex(10)
        name = source.name or "Carpeta personal"
        source_id = f"custom-{token}"
        item = {"id": source_id, "name": f"Carpeta: {name}", "path": str(source)}
        _custom_sources[token] = item
    return {"success": True, "source": {"id": f"custom:{token}", "name": item["name"], "path": item["path"]}}


def remove_custom_backup_source(source_id: str) -> dict[str, Any]:
    if not isinstance(source_id, str) or not source_id.startswith("custom:"):
        return {"success": False, "message": "Carpeta añadida no válida."}
    token = source_id.removeprefix("custom:")
    if not re.fullmatch(r"[0-9a-f]{20}", token):
        return {"success": False, "message": "Carpeta añadida no válida."}
    with _job_lock:
        removed = _custom_sources.pop(token, None)
    if not removed:
        return {"success": False, "message": "Esa carpeta ya no está en la lista."}
    return {"success": True}


def _registered_backup(backup_id: str) -> dict[str, Any]:
    if not isinstance(backup_id, str) or len(backup_id) > 64:
        raise BackupError("Identificador de respaldo no válido.")
    entry = next((item for item in _read_registry() if item.get("id") == backup_id), None)
    if not entry:
        raise BackupError("No encontré ese respaldo en el registro de LinuxMate.")
    path = Path(str(entry.get("path", ""))).expanduser()
    if path.is_symlink() or not path.is_file():
        raise BackupError("El archivo de respaldo ya no está disponible o es un enlace simbólico.")
    entry["path"] = str(path.resolve(strict=True))
    return entry


def get_backup_overview() -> dict[str, Any]:
    """Información para la vista: carpetas disponibles, respaldos y Timeshift."""
    try:
        sources = available_backup_sources()
        backups: list[dict[str, Any]] = []
        for entry in reversed(_read_registry()):
            try:
                backup = _registered_backup(str(entry.get("id", "")))
                archive = Path(backup["path"])
                backups.append({
                    "id": backup["id"], "created_at": backup.get("created_at", ""),
                    "folders": backup.get("folders", []), "file_count": int(backup.get("file_count", 0)),
                    "size": archive.stat().st_size, "source_bytes": int(backup.get("source_bytes", 0)),
                    "path": str(archive),
                })
            except (BackupError, OSError, TypeError, ValueError):
                continue
        return {
            "success": True,
            "sources": sources,
            "backups": backups,
            "timeshift_available": bool(_timeshift_gui()),
            "timeshift_installed": bool(shutil.which("timeshift")),
        }
    except BackupError as exc:
        return {"success": False, "message": str(exc)}
    except OSError:
        return {"success": False, "message": "No se pudo leer el registro privado de respaldos."}


def open_timeshift() -> dict[str, Any]:
    """Abre Timeshift si existe; la creación/restauración se confirma en su propia interfaz."""
    executable = _timeshift_gui()
    if not executable:
        if shutil.which("timeshift"):
            return {"success": False, "message": "Timeshift está instalado, pero no encontré su interfaz gráfica. Ábrela desde el menú de aplicaciones."}
        return {"success": False, "message": "Timeshift no está instalado. Puedes instalarlo desde el gestor de aplicaciones de tu distribución."}
    try:
        subprocess.Popen([executable], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return {"success": False, "message": "No se pudo abrir Timeshift en este equipo."}
    return {"success": True, "message": "Timeshift se abrió. Revisa el destino y el contenido del snapshot antes de confirmarlo."}


def _set_job(task_id: str, **updates: Any) -> None:
    with _job_lock:
        if task_id in _jobs:
            _jobs[task_id].update(updates)


def _start_job(kind: str, worker: Any, *args: Any) -> dict[str, Any]:
    global _active_job
    with _job_lock:
        if _active_job and _jobs.get(_active_job, {}).get("status") == "running":
            return {"success": False, "message": "Espera a que termine la operación de respaldo actual."}
        completed = [key for key, value in _jobs.items() if value.get("status") != "running"]
        for old_id in completed[:-40]:
            _jobs.pop(old_id, None)
        task_id = secrets.token_hex(12)
        _jobs[task_id] = {
            "id": task_id, "kind": kind, "status": "running", "progress": 0,
            "message": "Preparando…", "result": None, "error": None,
        }
        _active_job = task_id
    threading.Thread(target=worker, args=(task_id, *args), daemon=True, name=f"linuxmate-{kind}-{task_id[:6]}").start()
    return {"success": True, "task_id": task_id}


def get_backup_task(task_id: str) -> dict[str, Any]:
    with _job_lock:
        task = _jobs.get(task_id)
        if not task:
            return {"success": False, "message": "La operación ya no está disponible."}
        return {"success": True, "task": dict(task)}


def _scan_files(sources: list[dict[str, str]]) -> list[tuple[str, Path, str, int]]:
    entries: list[tuple[str, Path, str, int]] = []
    for source in sources:
        root = Path(source["path"])
        def on_walk_error(_error: OSError) -> None:
            raise BackupError(f"No pude revisar todos los archivos de {source['name']}. Comprueba sus permisos y vuelve a intentarlo.")

        for current, directories, filenames in os.walk(root, topdown=True, onerror=on_walk_error, followlinks=False):
            current_path = Path(current)
            directories[:] = [name for name in directories if not (current_path / name).is_symlink()]
            for name in filenames:
                path = current_path / name
                try:
                    if path.is_symlink():
                        continue
                    details = path.stat(follow_symlinks=False)
                    if not stat.S_ISREG(details.st_mode):
                        continue
                    relative = path.relative_to(root).as_posix()
                    entries.append((source["id"], path, relative, details.st_size))
                except OSError as exc:
                    raise BackupError(f"No pude revisar {path.name}. Comprueba sus permisos y vuelve a intentarlo.") from exc
    return entries


def start_personal_backup(categories: list[str], destination: str) -> dict[str, Any]:
    """Inicia una copia ZIP de las carpetas permitidas en una ubicación elegida por el usuario."""
    if not isinstance(categories, list) or not categories or any(not isinstance(item, str) for item in categories):
        return {"success": False, "message": "Selecciona al menos una carpeta para respaldar."}
    if len(set(categories)) != len(categories):
        return {"success": False, "message": "La selección de carpetas no es válida."}
    if not isinstance(destination, str) or not destination.strip():
        return {"success": False, "message": "Selecciona dónde guardar el respaldo."}
    sources_by_id = {source["id"]: source for source in available_backup_sources()}
    sources: list[dict[str, str]] = []
    custom_tokens: list[str] = []
    for item in categories:
        if item in sources_by_id:
            sources.append(sources_by_id[item])
            continue
        token = item.removeprefix("custom:") if item.startswith("custom:") else ""
        if not token or not re.fullmatch(r"[0-9a-f]{20}", token):
            return {"success": False, "message": "La selección de carpetas no es válida."}
        with _job_lock:
            source = _custom_sources.get(token)
        if not source:
            return {"success": False, "message": "Una carpeta añadida ya no está disponible. Vuelve a seleccionarla."}
        sources.append(dict(source))
        custom_tokens.append(token)
    if len(sources) != len(categories):
        return {"success": False, "message": "Una de las carpetas seleccionadas ya no está disponible."}
    home = _home()
    for source in sources:
        source_path = Path(source["path"])
        if source_path.is_symlink() or not source_path.is_dir():
            return {"success": False, "message": "Una de las carpetas seleccionadas ya no está disponible."}
        try:
            resolved_source = source_path.resolve(strict=True)
            if resolved_source == home or home not in resolved_source.parents:
                return {"success": False, "message": "Solo se pueden respaldar carpetas dentro de tu carpeta personal."}
            source["path"] = str(resolved_source)
        except OSError:
            return {"success": False, "message": "No se pudo abrir una de las carpetas seleccionadas."}
    dest_path = Path(destination).expanduser()
    if dest_path.is_symlink() or not dest_path.is_dir():
        return {"success": False, "message": "El destino debe ser una carpeta existente y no un enlace simbólico."}
    try:
        dest_path = dest_path.resolve(strict=True)
        for source in sources:
            source_path = Path(source["path"]).resolve(strict=True)
            if dest_path == source_path or source_path in dest_path.parents:
                return {"success": False, "message": "El destino está dentro de una carpeta que vas a respaldar. Elige otra ubicación para evitar copiar el respaldo dentro de sí mismo."}
        probe_fd, probe_name = tempfile.mkstemp(prefix=".linuxmate-write-check-", dir=dest_path)
        os.close(probe_fd)
        os.unlink(probe_name)
    except OSError:
        return {"success": False, "message": "No tienes permiso de escritura en la carpeta elegida."}
    response = _start_job("backup", _backup_worker, sources, str(dest_path))
    if response.get("success"):
        with _job_lock:
            for token in custom_tokens:
                _custom_sources.pop(token, None)
    return response


def _backup_worker(task_id: str, sources: list[dict[str, str]], destination: str) -> None:
    archive_path: Path | None = None
    partial_path: Path | None = None
    try:
        _set_job(task_id, progress=3, message="Revisando las carpetas elegidas…")
        entries = _scan_files(sources)
        if not entries:
            raise BackupError("Las carpetas elegidas no contienen archivos. No creé un ZIP vacío.")
        total_bytes = sum(item[3] for item in entries)
        now = datetime.now()
        backup_id = secrets.token_hex(8)
        archive_name = f"LinuxMate-respaldo-{now:%Y%m%d-%H%M%S}-{backup_id}.zip"
        archive_path = Path(destination) / archive_name
        partial_path = Path(destination) / f".{archive_name}.partial"
        written_bytes = 0
        _set_job(task_id, progress=5, message=f"Comprimiendo {len(entries)} archivos…")
        with zipfile.ZipFile(partial_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            for index, (category_id, path, relative, file_size) in enumerate(entries, start=1):
                archive_name_in_zip = f"{category_id}/{relative}"
                source_fd = -1
                try:
                    source_fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
                    file_stat = os.fstat(source_fd)
                    if not stat.S_ISREG(file_stat.st_mode):
                        raise BackupError("Una carpeta cambió durante el respaldo; no seguí el enlace.")
                    try:
                        zip_time = datetime.fromtimestamp(file_stat.st_mtime)
                    except (OSError, OverflowError, ValueError):
                        zip_time = datetime.now()
                    if zip_time.year < 1980:
                        zip_time = zip_time.replace(year=1980, month=1, day=1, hour=0, minute=0, second=0)
                    elif zip_time.year > 2107:
                        zip_time = zip_time.replace(year=2107, month=12, day=31, hour=23, minute=59, second=58)
                    info = zipfile.ZipInfo(archive_name_in_zip, date_time=zip_time.timetuple()[:6])
                    info.compress_type = zipfile.ZIP_STORED if file_size >= 64 * 1024 * 1024 else zipfile.ZIP_DEFLATED
                    info.external_attr = (stat.S_IMODE(file_stat.st_mode) & 0o777) << 16
                    source_handle = os.fdopen(source_fd, "rb")
                    source_fd = -1
                    with source_handle as source_file, archive.open(info, "w") as backup_file:
                        while True:
                            block = source_file.read(BLOCK_SIZE)
                            if not block:
                                break
                            backup_file.write(block)
                            written_bytes += len(block)
                    progress = 5 + int(min(1.0, written_bytes / max(1, total_bytes)) * 88)
                    if index == len(entries) or index % 25 == 0:
                        _set_job(task_id, progress=progress, message=f"Copiando archivos: {index} de {len(entries)}…")
                except OSError as exc:
                    raise BackupError(f"No pude leer {path.name}. Revisa que siga disponible y vuelve a intentarlo.") from exc
                finally:
                    if source_fd >= 0:
                        os.close(source_fd)

            manifest = {
                "format": 1, "created_at": now.isoformat(timespec="seconds"),
                "folders": [{"id": source["id"], "name": source["name"]} for source in sources],
                "file_count": len(entries), "source_bytes": written_bytes,
            }
            archive.writestr(".linuxmate-backup.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        partial_path.chmod(0o600)
        os.replace(partial_path, archive_path)
        metadata = {
            "id": backup_id, "created_at": now.isoformat(timespec="seconds"), "path": str(archive_path),
            "folders": [source["name"] for source in sources], "file_count": len(entries),
            "source_bytes": written_bytes,
        }
        _save_registry([*_read_registry(), metadata])
        _set_job(task_id, status="complete", progress=100, message="Respaldo creado y registrado.", result=metadata)
    except Exception as exc:
        if partial_path:
            try:
                partial_path.unlink(missing_ok=True)
            except OSError:
                pass
        if archive_path:
            try:
                archive_path.unlink(missing_ok=True)
            except OSError:
                pass
        _set_job(task_id, status="failed", progress=0, message="No se pudo crear el respaldo.", error=str(exc) if isinstance(exc, BackupError) else "Ocurrió un error al crear el archivo. Revisa el espacio disponible y vuelve a intentarlo.")


def preview_backup_restore(backup_id: str) -> dict[str, Any]:
    """Muestra qué contiene una copia y dónde se extraería, sin cambiar archivos personales."""
    try:
        entry = _registered_backup(backup_id)
        archive_path = Path(entry["path"])
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            files = [info for info in infos if not info.is_dir() and info.filename != ".linuxmate-backup.json"]
            if len(files) > MAX_RESTORE_FILES or sum(info.file_size for info in files) > MAX_RESTORE_BYTES:
                return {"success": False, "message": "Este archivo supera los límites de restauración segura de LinuxMate."}
            sample = [PurePosixPath(info.filename).as_posix() for info in files[:8]]
        restore_root = _restoration_parent() / f"{datetime.now():%Y%m%d-%H%M%S}-{backup_id[:8]}"
        return {
            "success": True, "id": entry["id"], "created_at": entry.get("created_at", ""),
            "folders": entry.get("folders", []), "file_count": len(files), "size": archive_path.stat().st_size,
            "source_bytes": int(entry.get("source_bytes", 0)), "restore_path": str(restore_root), "sample": sample,
        }
    except (BackupError, OSError, zipfile.BadZipFile):
        return {"success": False, "message": "No pude leer este respaldo. El archivo puede estar dañado o ya no existir."}


def start_backup_restore(backup_id: str) -> dict[str, Any]:
    try:
        entry = _registered_backup(backup_id)
    except BackupError as exc:
        return {"success": False, "message": str(exc)}
    return _start_job("restore", _restore_worker, entry)


def _safe_archive_parts(filename: str) -> tuple[str, ...]:
    path = PurePosixPath(filename)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise BackupError("El archivo contiene una ruta no segura y no se extraerá.")
    return path.parts


def _restore_worker(task_id: str, entry: dict[str, Any]) -> None:
    restore_root: Path | None = None
    try:
        archive_path = Path(entry["path"])
        details = archive_path.stat()
        if archive_path.is_symlink() or not stat.S_ISREG(details.st_mode):
            raise BackupError("El archivo de respaldo no es un archivo normal.")
        restore_root = _restoration_parent() / f"{datetime.now():%Y%m%d-%H%M%S}-{entry['id'][:8]}-{secrets.token_hex(2)}"
        restore_root.mkdir(mode=0o700)
        _set_job(task_id, progress=4, message="Validando el archivo de respaldo…")
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            files = [info for info in infos if not info.is_dir() and info.filename != ".linuxmate-backup.json"]
            if len(files) > MAX_RESTORE_FILES or sum(info.file_size for info in files) > MAX_RESTORE_BYTES:
                raise BackupError("Este archivo supera los límites de restauración segura de LinuxMate.")
            for index, info in enumerate(files, start=1):
                parts = _safe_archive_parts(info.filename)
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise BackupError("La copia contiene un enlace simbólico y no se extraerá.")
                if parts[0] not in _CATEGORY_INFO and not re.fullmatch(r"custom-[0-9a-f]{20}", parts[0]):
                    raise BackupError("La copia contiene una carpeta que LinuxMate no reconoce.")
                target = restore_root.joinpath(*parts)
                if not target.resolve().is_relative_to(restore_root.resolve()):
                    raise BackupError("La copia contiene una ruta que sale de la carpeta de restauración.")
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                if target.exists():
                    raise BackupError("La copia contiene rutas repetidas; la restauración se detuvo sin sobrescribir archivos.")
                with archive.open(info, "r") as source_file, target.open("xb") as target_file:
                    shutil.copyfileobj(source_file, target_file, BLOCK_SIZE)
                target.chmod((mode & 0o700) | 0o600)
                if index == len(files) or index % 25 == 0:
                    _set_job(task_id, progress=5 + int(index / max(1, len(files)) * 94), message=f"Restaurando archivos: {index} de {len(files)}…")
        _set_job(task_id, status="complete", progress=100, message="Restauración preparada en una carpeta aparte.", result={"path": str(restore_root), "file_count": len(files)})
    except Exception as exc:
        if restore_root:
            try:
                shutil.rmtree(restore_root)
            except OSError:
                pass
        _set_job(task_id, status="failed", progress=0, message="No se pudo restaurar el respaldo.", error=str(exc) if isinstance(exc, BackupError) else "El archivo no se pudo validar o extraer de forma segura.")

"""Respaldos, registro de cambios y deshacer para las escrituras del asistente.

Cada archivo que el asistente sobrescribe se copia antes a una carpeta privada y se
anota en un manifiesto JSONL (solo se agregan líneas, nunca se editan) con la ruta
original, el hash antes/después y la fecha. Con esos datos se puede deshacer el último
cambio de forma segura: si el archivo se modificó después, no se pisa.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.core.security import assess_file_write


MANIFEST_NAME = "manifest.jsonl"


class BackupError(RuntimeError):
    """Error controlado: el mensaje se puede mostrar al usuario."""


def backup_root() -> Path:
    return Path.home() / ".local" / "share" / "asistente-linux" / "backups"


def _private_dir() -> Path:
    root = backup_root()
    if root.is_symlink():
        raise BackupError(
            "La carpeta de respaldos es un enlace simbólico; no escribiré fuera de la ubicación privada esperada."
        )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    return root


def sha256_file(path: Path) -> Optional[str]:
    """Hash SHA-256 del archivo, o None si no existe."""
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except FileNotFoundError:
        return None


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_backup(target: Path) -> Optional[Path]:
    """Copia `target` a la carpeta privada. Devuelve None si el archivo no existe."""
    if not target.exists():
        return None
    root = _private_dir()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = root / f"{stamp}-{target.name}.bak"
    shutil.copy2(target, backup_path)
    backup_path.chmod(0o600)
    return backup_path


def write_atomic(target: Path, content: str | bytes) -> None:
    """Escribe `content` en `target` sin dejar el archivo a medias; conserva sus permisos."""
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = target.stat().st_mode & 0o777 if target.exists() else 0o644
    data = content.encode("utf-8") if isinstance(content, str) else content
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _manifest_path() -> Path:
    return _private_dir() / MANIFEST_NAME


def _append_manifest(entry: dict[str, Any]) -> None:
    path = _manifest_path()
    new_file = not path.exists()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if new_file:
        path.chmod(0o600)


def record_change(
    original_path: Path,
    backup_path: Optional[Path],
    sha_before: Optional[str],
    sha_after: Optional[str],
    action: str = "write_file",
) -> str:
    """Anota un cambio aplicado y devuelve su identificador."""
    change_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    _append_manifest({
        "id": change_id,
        "at": datetime.now().isoformat(timespec="seconds"),
        "action": action,
        "path": str(original_path),
        "backup": str(backup_path) if backup_path else None,
        "sha_before": sha_before,
        "sha_after": sha_after,
        "status": "applied",
    })
    return change_id


def list_changes(limit: int = 10) -> list[dict[str, Any]]:
    """Cambios registrados (más recientes primero) con su estado actual."""
    path = backup_root() / MANIFEST_NAME
    if not path.is_file():
        return []
    entries: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue  # una línea dañada no debe invalidar el historial
        if not isinstance(item, dict) or "id" not in item:
            continue
        if "path" in item:
            entries[item["id"]] = item
            order.append(item["id"])
        elif item["id"] in entries:
            entries[item["id"]]["status"] = item.get("status", entries[item["id"]]["status"])
            entries[item["id"]]["undone_at"] = item.get("at")
    return [entries[change_id] for change_id in reversed(order)][: max(1, limit)]


def undo_last_change() -> str:
    """Revierte el último cambio aplicado. Devuelve un mensaje para el usuario."""
    pending = next((item for item in list_changes(limit=10_000) if item.get("status") == "applied"), None)
    if pending is None:
        return "No hay cambios del asistente que se puedan deshacer."

    target = Path(pending["path"])
    decision = assess_file_write(str(target))
    if decision.is_blocked:
        return f"⛔ No puedo deshacer: {decision.message}\n\nRuta: `{target}`"

    current_hash = sha256_file(target)
    expected_hash = pending.get("sha_after")
    if current_hash is not None and current_hash != expected_hash:
        return (
            f"⚠️ `{target}` cambió después de la acción del asistente. "
            "No lo sobrescribo para no perder tus modificaciones.\n"
            f"Copia anterior disponible en: `{pending.get('backup') or 'no hay (archivo nuevo)'}`."
        )

    backup = Path(pending["backup"]) if pending.get("backup") else None
    try:
        if backup is not None:
            if sha256_file(backup) != pending.get("sha_before"):
                return f"⛔ La copia `{backup}` no coincide con su hash registrado; no la restauro."
            safety_copy = create_backup(target)  # lo que hay ahora, por si se arrepiente
            write_atomic(target, backup.read_bytes())
            result = f"✅ Restauré `{target}` a su versión anterior."
        else:
            if current_hash is None:
                result = f"`{target}` ya no existe; no hay nada que quitar."
                safety_copy = None
            else:
                safety_copy = create_backup(target)
                target.unlink()
                result = f"✅ Eliminé `{target}` (lo había creado el asistente)."
        _append_manifest({
            "id": pending["id"],
            "at": datetime.now().isoformat(timespec="seconds"),
            "status": "undone",
        })
    except BackupError as exc:
        return f"⛔ {exc}"
    except (OSError, UnicodeDecodeError) as exc:
        return f"❌ No pude deshacer el cambio: {exc}"
    if safety_copy:
        result += f" Guardé la versión que había antes de deshacer en `{safety_copy}`."
    return result

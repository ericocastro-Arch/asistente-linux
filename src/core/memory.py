"""Memoria conversacional persistente almacenada en SQLite."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.storage import (
    clear_messages,
    get_active_session_id,
    init_db,
    load_recent_messages,
    replace_session_messages,
    start_session,
)


MAX_EXCHANGES = 50


def _legacy_memory_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "asistente-linux" / "memory.json"


def _migrate_legacy_memory() -> None:
    legacy_path = _legacy_memory_path()
    if not legacy_path.is_file():
        return
    try:
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
        messages = [
            item for item in data
            if isinstance(item, dict)
            and item.get("role") in {"user", "assistant"}
            and isinstance(item.get("content"), str)
        ][-(MAX_EXCHANGES * 2):]
        if messages:
            replace_session_messages(start_session("json-migration", activate=False), messages)
        legacy_path.rename(legacy_path.with_suffix(".json.migrated"))
    except (OSError, ValueError, TypeError):
        return


def load_memory() -> List[Dict[str, Any]]:
    """Carga los mensajes recientes de todas las sesiones."""
    messages = load_recent_messages(MAX_EXCHANGES * 2)
    if not messages:
        _migrate_legacy_memory()
        messages = load_recent_messages(MAX_EXCHANGES * 2)
    return messages


def save_memory(history: List[Dict[str, Any]], session_id: Optional[int] = None) -> None:
    """Sincroniza el historial visible de una sesion en SQLite."""
    filtered = [
        message for message in history
        if isinstance(message, dict) and message.get("role") in ("user", "assistant")
    ][-(MAX_EXCHANGES * 2):]
    replace_session_messages(session_id or get_active_session_id(), filtered)


def clear_memory() -> None:
    """Borra el historial conversacional; conserva la auditoria de comandos."""
    clear_messages()


def memory_summary() -> str:
    msgs = load_memory()
    if not msgs:
        return "Sin historial previo guardado."
    path = init_db()
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
    except OSError:
        modified = "-"
    return f"{len(msgs) // 2} intercambios guardados (ultima actividad: {modified})"


def get_memory_count() -> int:
    return len(load_memory())

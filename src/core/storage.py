"""Persistencia SQLite para sesiones, conversacion y auditoria del sistema."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


_ACTIVE_SESSIONS: dict[Path, int] = {}


def _db_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "asistente-linux" / "assistant.db"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_tool_run_columns(con: sqlite3.Connection) -> None:
    columns = {row[1] for row in con.execute("PRAGMA table_info(tool_runs)")}
    migrations = {
        "session_id": "INTEGER",
        "stdout": "TEXT NOT NULL DEFAULT ''",
        "stderr": "TEXT NOT NULL DEFAULT ''",
        "exit_code": "INTEGER",
    }
    for name, definition in migrations.items():
        if name not in columns:
            con.execute(f"ALTER TABLE tool_runs ADD COLUMN {name} {definition}")


def init_db() -> Path:
    """Crea o actualiza el esquema sin eliminar datos existentes."""
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                client TEXT NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                arguments TEXT NOT NULL,
                result_preview TEXT NOT NULL,
                status TEXT NOT NULL,
                session_id INTEGER,
                stdout TEXT NOT NULL DEFAULT '',
                stderr TEXT NOT NULL DEFAULT '',
                exit_code INTEGER,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
            )
            """
        )
        _ensure_tool_run_columns(con)
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS system_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                created_at TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                details TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_tool_runs_created ON tool_runs(created_at)")
    return path


def start_session(client: str = "desktop", activate: bool = True) -> int:
    """Inicia una sesion auditable y devuelve su identificador."""
    path = init_db()
    with sqlite3.connect(path) as con:
        cursor = con.execute(
            "INSERT INTO sessions (started_at, client) VALUES (?, ?)",
            (_now(), client[:80] or "desktop"),
        )
        session_id = int(cursor.lastrowid)
    if activate:
        _ACTIVE_SESSIONS[path] = session_id
    return session_id


def get_active_session_id() -> int:
    path = init_db()
    session_id = _ACTIVE_SESSIONS.get(path)
    if session_id is None:
        session_id = start_session()
    return session_id


def close_session(session_id: int) -> None:
    path = init_db()
    with sqlite3.connect(path) as con:
        con.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (_now(), session_id))
    if _ACTIVE_SESSIONS.get(path) == session_id:
        _ACTIVE_SESSIONS.pop(path, None)


def replace_session_messages(session_id: int, messages: list[dict[str, Any]]) -> None:
    """Sincroniza los mensajes de una sesion, omitiendo roles internos del agente."""
    filtered = [
        message for message in messages
        if isinstance(message, dict)
        and message.get("role") in {"user", "assistant"}
        and isinstance(message.get("content"), str)
    ]
    path = init_db()
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        con.executemany(
            "INSERT INTO messages (session_id, created_at, role, content) VALUES (?, ?, ?, ?)",
            [(session_id, _now(), item["role"], item["content"]) for item in filtered],
        )


def log_message(role: str, content: str, session_id: Optional[int] = None) -> None:
    """Agrega un mensaje de usuario o asistente a la sesion activa."""
    if role not in {"user", "assistant"} or not isinstance(content, str):
        return
    path = init_db()
    resolved_session = session_id or get_active_session_id()
    with sqlite3.connect(path) as con:
        con.execute(
            "INSERT INTO messages (session_id, created_at, role, content) VALUES (?, ?, ?, ?)",
            (resolved_session, _now(), role, content),
        )


def load_recent_messages(limit: int = 100) -> list[dict[str, str]]:
    path = init_db()
    with sqlite3.connect(path) as con:
        rows = con.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def clear_messages() -> None:
    path = init_db()
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM messages")


def log_tool_run(
    tool_name: str,
    arguments: str,
    result: str,
    status: Optional[str] = None,
    *,
    stdout: Optional[str] = None,
    stderr: str = "",
    exit_code: Optional[int] = None,
    session_id: Optional[int] = None,
) -> None:
    """Guarda resultado, salidas y codigo sin interrumpir al usuario si falla."""
    try:
        path = init_db()
        output = result if stdout is None else stdout
        preview = result.replace("\n", " ")[:500]
        run_status = status or (
            "blocked" if "bloqueado" in result.lower()
            else "ok" if exit_code in (None, 0)
            else "error"
        )
        resolved_session = session_id or get_active_session_id()
        with sqlite3.connect(path) as con:
            con.execute(
                """
                INSERT INTO tool_runs (
                    created_at, tool_name, arguments, result_preview, status,
                    session_id, stdout, stderr, exit_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now(), tool_name, arguments[:4000], preview, run_status,
                    resolved_session, output, stderr, exit_code,
                ),
            )
    except Exception:
        pass


def log_system_snapshot(
    cpu_percent: Optional[float],
    memory_percent: Optional[float],
    disk_percent: Optional[float],
    details: Optional[dict[str, Any]] = None,
    session_id: Optional[int] = None,
) -> None:
    try:
        path = init_db()
        resolved_session = session_id or get_active_session_id()
        with sqlite3.connect(path) as con:
            con.execute(
                """
                INSERT INTO system_snapshots (
                    session_id, created_at, cpu_percent, memory_percent, disk_percent, details
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    resolved_session, _now(), cpu_percent, memory_percent, disk_percent,
                    json.dumps(details or {}, ensure_ascii=False),
                ),
            )
    except Exception:
        pass

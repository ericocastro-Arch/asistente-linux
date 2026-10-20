"""Política de escritura en $HOME, respaldos con hash y deshacer."""

import json
import os
from pathlib import Path

import pytest

from src.core import backups
from src.core.security import APP_ROOT, SafetyLevel, assess_file_write
from src.core.tools import execute_tool


@pytest.fixture
def home(tmp_path, monkeypatch):
    """HOME aislado; devuelve (home, carpeta_fuera_de_home)."""
    fake_home = tmp_path / "home"
    outside = tmp_path / "outside"
    fake_home.mkdir()
    outside.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return fake_home, outside


def write(path, content):
    return execute_tool("write_file", {"file_path": str(path), "content": content})


# ── Política de rutas ───────────────────────────────────────────────────────

def test_write_inside_home_is_allowed(home):
    fake_home, _ = home
    assert assess_file_write(str(fake_home / "notas.txt")).level == SafetyLevel.SAFE
    assert assess_file_write("~/Documentos/nuevo/notas.txt").level == SafetyLevel.SAFE


@pytest.mark.parametrize("path", ["/tmp/x.txt", "/opt/app/x", "/var/tmp/x", "/etc/hosts", "/usr/bin/x", "/root/x"])
def test_write_outside_home_is_blocked(home, path):
    assert assess_file_write(path).is_blocked


def test_relative_traversal_out_of_home_is_blocked(home):
    fake_home, outside = home
    assert assess_file_write(str(fake_home / ".." / "outside" / "x.txt")).is_blocked


def test_symlink_escape_is_blocked(home):
    fake_home, outside = home
    (fake_home / "atajo").symlink_to(outside)
    assert assess_file_write(str(fake_home / "atajo" / "x.txt")).is_blocked
    assert not (outside / "x.txt").exists()


@pytest.mark.parametrize("relative", [
    ".ssh/authorized_keys",
    ".gnupg/pubring.kbx",
    ".aws/credentials",
    ".config/autostart/malo.desktop",
    ".config/systemd/user/malo.service",
    ".config/asistente-linux/assistant.db",
    ".local/share/asistente-linux/backups/manifest.jsonl",
    ".local/share/keyrings/login.keyring",
    ".env",
    "proyecto/.env",
    ".netrc",
])
def test_protected_paths_inside_home_are_blocked(home, relative):
    fake_home, _ = home
    assert assess_file_write(str(fake_home / relative)).is_blocked, relative


def test_assistant_cannot_rewrite_its_own_code():
    assert assess_file_write(str(APP_ROOT / "src" / "core" / "security.py")).is_blocked
    assert assess_file_write(str(APP_ROOT / "main.py")).is_blocked


def test_blocked_write_does_not_touch_disk(home):
    fake_home, outside = home
    result = write(outside / "x.txt", "no")
    assert "bloqueada" in result.lower()
    assert not (outside / "x.txt").exists()


def test_blocked_write_audit_does_not_store_file_content(home, monkeypatch):
    from src.core import tools

    _, outside = home
    records = []
    monkeypatch.setattr(tools, "log_tool_run", lambda *args, **kwargs: records.append(args))
    secret = "contenido confidencial de prueba"

    result = write(outside / "x.txt", secret)

    assert "bloqueada" in result.lower()
    assert len(records) == 1
    assert secret not in records[0][1]
    assert f"content_length={len(secret)}" in records[0][1]


# ── Respaldo y registro ─────────────────────────────────────────────────────

def test_overwrite_creates_backup_with_hashes_in_manifest(home):
    fake_home, _ = home
    target = fake_home / "config.txt"
    target.write_text("original", encoding="utf-8")

    result = write(target, "nuevo")

    assert "Archivo guardado" in result
    assert target.read_text(encoding="utf-8") == "nuevo"
    [entry] = backups.list_changes()
    assert entry["path"] == str(target)
    assert entry["sha_before"] == backups.sha256_text("original")
    assert entry["sha_after"] == backups.sha256_text("nuevo")
    assert Path(entry["backup"]).read_text(encoding="utf-8") == "original"
    assert entry["status"] == "applied"


def test_backup_storage_is_private(home):
    fake_home, _ = home
    target = fake_home / "a.txt"
    target.write_text("x", encoding="utf-8")
    write(target, "y")

    root = backups.backup_root()
    assert root.stat().st_mode & 0o777 == 0o700
    assert (root / backups.MANIFEST_NAME).stat().st_mode & 0o777 == 0o600
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in root.glob("*.bak"))


def test_overwrite_preserves_file_permissions(home):
    fake_home, _ = home
    target = fake_home / "secreto.txt"
    target.write_text("a", encoding="utf-8")
    target.chmod(0o600)
    write(target, "b")
    assert target.stat().st_mode & 0o777 == 0o600


def test_atomic_write_leaves_no_temp_files(home):
    fake_home, _ = home
    write(fake_home / "a.txt", "x")
    assert sorted(p.name for p in fake_home.iterdir() if p.is_file()) == ["a.txt"]


def test_backup_dir_symlink_is_refused(home):
    fake_home, outside = home
    target = fake_home / "a.txt"
    target.write_text("x", encoding="utf-8")
    link = backups.backup_root()
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)

    result = write(target, "y")

    assert "enlace simbólico" in result
    assert target.read_text(encoding="utf-8") == "x"
    assert list(outside.iterdir()) == []


# ── Deshacer ────────────────────────────────────────────────────────────────

def test_undo_restores_previous_content(home):
    fake_home, _ = home
    target = fake_home / "a.txt"
    target.write_text("v0", encoding="utf-8")
    write(target, "v1")

    result = execute_tool("undo_last_change", {})

    assert "Restauré" in result
    assert target.read_text(encoding="utf-8") == "v0"
    assert backups.list_changes()[0]["status"] == "undone"


def test_undo_removes_file_created_by_assistant(home):
    fake_home, _ = home
    target = fake_home / "nuevo.txt"
    write(target, "hola")
    assert target.exists()

    result = execute_tool("undo_last_change", {})

    assert "Eliminé" in result
    assert not target.exists()


def test_undo_walks_back_through_several_changes(home):
    fake_home, _ = home
    target = fake_home / "a.txt"
    target.write_text("v0", encoding="utf-8")
    write(target, "v1")
    write(target, "v2")

    execute_tool("undo_last_change", {})
    assert target.read_text(encoding="utf-8") == "v1"
    execute_tool("undo_last_change", {})
    assert target.read_text(encoding="utf-8") == "v0"
    assert "No hay cambios" in execute_tool("undo_last_change", {})


def test_undo_refuses_to_overwrite_later_user_edits(home):
    fake_home, _ = home
    target = fake_home / "a.txt"
    target.write_text("v0", encoding="utf-8")
    write(target, "v1")
    target.write_text("edición del usuario", encoding="utf-8")

    result = execute_tool("undo_last_change", {})

    assert "cambió después" in result
    assert target.read_text(encoding="utf-8") == "edición del usuario"
    assert backups.list_changes()[0]["status"] == "applied"


def test_undo_detects_tampered_backup(home):
    fake_home, _ = home
    target = fake_home / "a.txt"
    target.write_text("v0", encoding="utf-8")
    write(target, "v1")
    Path(backups.list_changes()[0]["backup"]).write_text("manipulado", encoding="utf-8")

    result = execute_tool("undo_last_change", {})

    assert "no coincide" in result
    assert target.read_text(encoding="utf-8") == "v1"


def test_undo_keeps_a_copy_of_what_it_replaces(home):
    fake_home, _ = home
    target = fake_home / "a.txt"
    target.write_text("v0", encoding="utf-8")
    write(target, "v1")

    execute_tool("undo_last_change", {})

    copies = [p.read_text(encoding="utf-8") for p in backups.backup_root().glob("*.bak")]
    assert "v1" in copies


def test_undo_restores_non_utf8_original(home):
    fake_home, _ = home
    target = fake_home / "datos.bin"
    target.write_bytes(b"\xff\xfe\x00binario")
    write(target, "texto")

    execute_tool("undo_last_change", {})

    assert target.read_bytes() == b"\xff\xfe\x00binario"


def test_undo_with_nothing_to_undo(home):
    assert "No hay cambios" in execute_tool("undo_last_change", {})


def test_corrupt_manifest_line_does_not_break_history(home):
    fake_home, _ = home
    target = fake_home / "a.txt"
    write(target, "x")
    manifest = backups.backup_root() / backups.MANIFEST_NAME
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write("{esto no es json\n")
        handle.write(json.dumps(["no", "es", "dict"]) + "\n")

    assert len(backups.list_changes()) == 1
    assert "Eliminé" in execute_tool("undo_last_change", {})

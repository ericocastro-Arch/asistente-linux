"""Pruebas de la capa de políticas, niveles de herramientas y catálogo de diagnósticos."""

import pytest
from src.core.policy import (
    MODE_READONLY,
    MODE_SAFE,
    ToolLevel,
    TOOL_LEVELS,
    authorize_tool,
    current_mode,
    normalize_mode,
    tool_level,
)
from src.core.diagnostic_catalog import (
    DIAGNOSTICS,
    catalog_description,
    run_diagnostic,
)
from src.core.tools import execute_tool


# ── Modos y normalización ───────────────────────────────────────────────────

def test_normalize_mode():
    assert normalize_mode("safe") == MODE_SAFE
    assert normalize_mode("readonly") == MODE_READONLY
    assert normalize_mode("READONLY") == MODE_READONLY
    # Modos heredados o desconocidos deben operar siempre como safe
    assert normalize_mode("autonomous") == MODE_SAFE
    assert normalize_mode("") == MODE_SAFE
    assert normalize_mode(None) == MODE_SAFE
    assert normalize_mode("inseguro") == MODE_SAFE


def test_current_mode_reads_env(monkeypatch):
    monkeypatch.setenv("SECURITY_MODE", "readonly")
    assert current_mode() == MODE_READONLY

    monkeypatch.setenv("SECURITY_MODE", "safe")
    assert current_mode() == MODE_SAFE

    monkeypatch.setenv("SECURITY_MODE", "autonomous")
    assert current_mode() == MODE_SAFE


# ── Niveles de herramientas ──────────────────────────────────────────────────

def test_tool_levels_assignment():
    assert tool_level("run_diagnostic") == ToolLevel.READ
    assert tool_level("get_system_status") == ToolLevel.READ
    assert tool_level("read_file") == ToolLevel.READ
    assert tool_level("search_package") == ToolLevel.READ

    assert tool_level("open_application") == ToolLevel.USER
    assert tool_level("write_file") == ToolLevel.USER
    assert tool_level("undo_last_change") == ToolLevel.USER

    assert tool_level("install_program") == ToolLevel.SYSTEM
    assert tool_level("update_system") == ToolLevel.SYSTEM
    assert tool_level("remove_package") == ToolLevel.SYSTEM

    # Argumentos dinámicos
    assert tool_level("manage_service", {"action": "status"}) == ToolLevel.READ
    assert tool_level("manage_service", {"action": "restart"}) == ToolLevel.SYSTEM
    assert tool_level("manage_service", {"action": "stop"}) == ToolLevel.SYSTEM

    assert tool_level("herramienta_fantasma") is None


# ── Autorización en modo SAFE y READONLY ────────────────────────────────────

def test_authorize_tool_unknown_rejected():
    decision = authorize_tool("eval_arbitrary_code", {})
    assert decision.is_blocked
    assert decision.category == "unknown_tool"


def test_authorize_tool_in_safe_mode(monkeypatch):
    monkeypatch.setenv("SECURITY_MODE", "safe")

    # Todo lo registrado está permitido a nivel de política (luego cada tool pide confirmación)
    assert not authorize_tool("run_diagnostic", {"name": "memory"}).is_blocked
    assert not authorize_tool("write_file", {"file_path": "~/doc.txt"}).is_blocked
    assert not authorize_tool("install_program", {"program_name": "htop"}).is_blocked
    assert not authorize_tool("manage_service", {"action": "restart"}).is_blocked


def test_authorize_tool_in_readonly_mode(monkeypatch):
    monkeypatch.setenv("SECURITY_MODE", "readonly")

    # Lectura permitida
    assert not authorize_tool("run_diagnostic", {"name": "disk_usage"}).is_blocked
    assert not authorize_tool("get_system_status", {}).is_blocked
    assert not authorize_tool("read_file", {"file_path": "~/doc.txt"}).is_blocked
    assert not authorize_tool("manage_service", {"action": "status"}).is_blocked

    # Acciones de usuario bloqueadas
    write_dec = authorize_tool("write_file", {"file_path": "~/doc.txt"})
    assert write_dec.is_blocked
    assert write_dec.category == "mode_restricted"
    assert "solo lectura" in write_dec.message.lower()

    app_dec = authorize_tool("open_application", {"app_name": "vlc"})
    assert app_dec.is_blocked

    # Acciones de sistema bloqueadas
    inst_dec = authorize_tool("install_program", {"program_name": "vlc"})
    assert inst_dec.is_blocked

    svc_dec = authorize_tool("manage_service", {"action": "restart"})
    assert svc_dec.is_blocked


# ── Ejecución mediante execute_tool ──────────────────────────────────────────

def test_execute_tool_enforces_policy_in_readonly(monkeypatch):
    monkeypatch.setenv("SECURITY_MODE", "readonly")

    res = execute_tool("install_program", {"program_name": "htop"})
    assert "Modo solo lectura activo" in res
    assert "⛔" in res

    res_write = execute_tool("write_file", {"file_path": "~/test.txt", "content": "hola"})
    assert "Modo solo lectura activo" in res_write


def test_execute_tool_blocks_unknown_tool():
    res = execute_tool("hacker_tool", {})
    assert "⛔" in res
    assert "no reconocida" in res


# ── Catálogo de diagnósticos estructurados ───────────────────────────────────

def test_diagnostic_catalog_entries():
    assert len(DIAGNOSTICS) >= 15
    for key, diag in DIAGNOSTICS.items():
        assert diag.description
        assert len(diag.argv) > 0

    desc = catalog_description()
    assert "memory" in desc
    assert "disk_usage" in desc


def test_run_diagnostic_unknown():
    msg, stdout, stderr, code = run_diagnostic("no_existe")
    assert "no reconocido" in msg.lower()
    assert code is None


def test_run_diagnostic_valid():
    # 'uptime_load' o 'kernel_info' son comandos estándar en Linux
    msg, stdout, stderr, code = run_diagnostic("kernel_info")
    assert "uname" in msg.lower() or "linux" in msg.lower()
    assert code == 0

    # A través de execute_tool
    tool_out = execute_tool("run_diagnostic", {"name": "uptime_load"})
    assert "uptime" in tool_out.lower() or "tiempo" in tool_out.lower()

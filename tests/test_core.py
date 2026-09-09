"""Pruebas unitarias de las funcionalidades del núcleo (tools, memory, agent prompt)."""

import os
import sqlite3
import json
from pathlib import Path
from src.core.tools import LINUX_TOOLS, build_deb_install_args, execute_tool
from src.core.memory import save_memory, load_memory, clear_memory, get_memory_count
from src.core.security import RiskLevel, SafetyLevel, assess_command, assess_file_write
from src.core.storage import init_db, log_tool_run
from src.nlp.processor import NLPProcessor
from src.nlp.router import route_request


def test_tools_registered():
    names = {tool["function"]["name"] for tool in LINUX_TOOLS}
    expected = {
        "update_system",
        "install_deb_package",
        "open_software_center",
        "open_application",
        "open_terminal_command",
        "get_system_status",
        "run_command_silent",
        "manage_service",
        "search_package",
        "remove_package",
        "read_file",
        "write_file",
    }
    assert expected.issubset(names), f"Faltan herramientas: {expected - names}"


def test_run_command_silent():
    out = execute_tool("run_command_silent", {"command": "echo 'prueba_asistente'"})
    assert "prueba_asistente" in out


def test_command_blocked():
    out = execute_tool("run_command_silent", {"command": "rm -rf /tmp/fake"})
    assert "bloqueado por seguridad" in out.lower()


def test_sudo_command_uses_visual_confirmation_path():
    decision = assess_command("sudo apt install vlc")
    assert decision.level == SafetyLevel.BLOCKED
    assert "confirmación" in decision.message or "confirmacion" in decision.message
    assert decision.risk == RiskLevel.MEDIUM


def test_adaptive_risk_levels():
    safe = assess_command("free -m")
    install = assess_command("sudo apt install vlc", allow_confirmation=True)
    removal = assess_command("sudo apt remove vlc", allow_confirmation=True)
    destructive = assess_command("rm -rf /")

    assert (safe.level, safe.risk) == (SafetyLevel.SAFE, RiskLevel.LOW)
    assert (install.level, install.risk) == (SafetyLevel.CONFIRM, RiskLevel.MEDIUM)
    assert (removal.level, removal.risk) == (SafetyLevel.CONFIRM, RiskLevel.HIGH)
    assert (destructive.level, destructive.risk) == (SafetyLevel.BLOCKED, RiskLevel.CRITICAL)


def test_unknown_or_shell_wrapped_command_is_not_silent():
    assert assess_command("python3 -c 'print(1)'").is_blocked
    assert assess_command("bash -c 'echo ok'").is_blocked


def test_terminal_tool_blocks_destructive_command():
    out = execute_tool("open_terminal_command", {"command": "rm -rf /tmp/fake"})
    assert "bloqueada por seguridad" in out.lower()


def test_system_file_write_blocked():
    decision = assess_file_write("/etc/hosts")
    assert decision.level == SafetyLevel.BLOCKED


def test_cpu_temperature_intent_is_specific():
    processor = NLPProcessor()
    intent, param = processor.analyze_intent("quiero ver la temperatura de mi cpu")
    assert intent == "CPU_TEMPERATURE"
    assert param is None


def test_wallpaper_intent_is_local():
    processor = NLPProcessor()
    intent, param = processor.analyze_intent("quiero cambiar el fondo de pantalla de mi ubuntu")
    assert intent == "WALLPAPER_SETTINGS"
    assert param is None


def test_local_route_matrix():
    cases = {
        "temperatura de la CPU": ("CPU_TEMPERATURE", None),
        "quiero cambiar el fondo de pantalla de mi Ubuntu": ("WALLPAPER_SETTINGS", None),
        "muéstrame el estado del sistema": ("SYSTEM_STATUS", None),
        "cuánta RAM tengo disponible": ("SYSTEM_STATUS", None),
        "abre la terminal": ("OPEN_APP", "terminal"),
        "habre la terminal": ("OPEN_APP", "terminal"),
        "quiero abrir internet": ("OPEN_APP", "navegador"),
        "abre Firefox": ("OPEN_APP", "firefox"),
        "quiero ver los procesos activos": ("SHOW_PROCESSES", None),
        "abre el monitor del sistema": ("SHOW_PROCESSES", None),
        "muéstrame mi dirección IP": ("SHOW_NETWORK", None),
        "abre el wifi": ("SHOW_NETWORK", None),
        "actualiza Ubuntu": ("UPDATE_SYSTEM", None),
        "instala VLC": ("INSTALL_PACKAGE", "vlc"),
        "intala VLC": ("INSTALL_PACKAGE", "vlc"),
        "instálame Google Chrome en mi Ubuntu": ("INSTALL_PACKAGE", "google chrome"),
        "abre la tienda de aplicaciones": ("OPEN_STORE", None),
        "instala paquete.deb": ("INSTALL_DEB", "paquete.deb"),
        "mi máquina está lenta": ("DIAGNOSE_PERFORMANCE", None),
        "no tengo internet": ("DIAGNOSE_NETWORK", None),
    }

    for text, expected in cases.items():
        route = route_request(text)
        assert route.is_local, f"Debía ser local: {text} ({route.reason})"
        assert (route.intent, route.param) == expected


def test_ambiguous_or_explanatory_requests_go_to_ai():
    cases = [
        "cómo cambiar el fondo de pantalla",
        "no abras Firefox",
        "actualiza Firefox",
        "es normal que mi CPU esté a 80 grados",
        "cómo liberar memoria RAM",
        "cómo instalar VLC",
        "abre https://example.com",
        "conéctame al wifi de la oficina",
        "qué es un proceso en Linux",
        "quiero poner música",
    ]

    for text in cases:
        route = route_request(text)
        assert not route.is_local, f"Debía ir a IA: {text} -> {route}"


def test_process_reports_the_real_source():
    class FakeAgent:
        def chat(self, _message: str) -> str:
            return "respuesta remota"

    processor = NLPProcessor()
    local = processor.process_with_source("qué hora es", FakeAgent())
    remote = processor.process_with_source("explícame qué es systemd", FakeAgent())

    assert local.source == "LOCAL"
    assert remote.source == "IA"
    assert remote.text == "respuesta remota"


def test_symptom_diagnostics_work_without_ai():
    processor = NLPProcessor()

    performance = processor.process_with_source("mi computadora está lenta")
    network = processor.process_with_source("no tengo internet")

    assert performance.source == "LOCAL"
    assert "Diagnostico local de rendimiento" in performance.text
    assert "No se modifico el sistema" in performance.text
    assert network.source == "LOCAL"
    assert "Diagnostico local de red" in network.text
    assert "No se modifico la configuracion" in network.text


def test_deb_install_command_keeps_path_as_one_argument(tmp_path: Path):
    package = tmp_path / "paquete con espacios.deb"
    package.write_bytes(b"prueba")

    args = build_deb_install_args(str(package))

    assert args[:4] == ["pkexec", "apt", "install", "-y"]
    assert args[4] == str(package.resolve())

    invalid = tmp_path / "paquete.txt"
    invalid.write_text("no es deb", encoding="utf-8")
    try:
        build_deb_install_args(str(invalid))
        raise AssertionError("Un archivo sin extension .deb no debe aceptarse")
    except ValueError:
        pass


def test_read_write_file(tmp_path: Path):
    test_file = tmp_path / "test_nota.txt"
    w_res = execute_tool("write_file", {"file_path": str(test_file), "content": "Hola mundo Linux"})
    assert "guardado exitosamente" in w_res.lower()

    r_res = execute_tool("read_file", {"file_path": str(test_file)})
    assert "Hola mundo Linux" in r_res


def test_memory_lifecycle(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    clear_memory()
    assert get_memory_count() == 0


def test_sqlite_tool_log(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    log_tool_run("run_command_silent", "{'command': 'echo ok'}", "ok")
    db_path = init_db()
    assert db_path.exists()

    dummy_history = [
        {"role": "user", "content": "¿Cómo instalo htop?"},
        {"role": "assistant", "content": "Puedes usar sudo apt install htop"},
    ]
    save_memory(dummy_history)
    assert get_memory_count() == 2

    loaded = load_memory()
    assert len(loaded) == 2
    assert loaded[0]["content"] == "¿Cómo instalo htop?"

    clear_memory()
    assert get_memory_count() == 0


def test_sqlite_audit_schema_and_command_outputs(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    result = execute_tool("run_command_silent", {"command": "printf audit-ok"})
    assert "audit-ok" in result

    db_path = init_db()
    with sqlite3.connect(db_path) as con:
        tables = {
            row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        audit = con.execute(
            "SELECT stdout, stderr, exit_code, status FROM tool_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert tables == {"sessions", "messages", "tool_runs", "system_snapshots"}
    assert audit == ("audit-ok", "", 0, "ok")


def test_legacy_json_memory_is_migrated(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config = tmp_path / "asistente-linux"
    config.mkdir()
    legacy = config / "memory.json"
    legacy.write_text(
        json.dumps([
            {"role": "user", "content": "mensaje anterior"},
            {"role": "assistant", "content": "respuesta anterior"},
        ]),
        encoding="utf-8",
    )

    loaded = load_memory()

    assert [item["content"] for item in loaded] == ["mensaje anterior", "respuesta anterior"]
    assert not legacy.exists()
    assert legacy.with_suffix(".json.migrated").exists()


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))

"""Pruebas unitarias de las funcionalidades del núcleo (tools, memory, agent prompt)."""

import os
import sqlite3
import json
from pathlib import Path
from src.core.tools import (
    LINUX_TOOLS,
    build_deb_install_args,
    build_interactive_uninstall_command,
    build_uninstall_args,
    execute_tool,
    find_uninstall_candidates,
    is_critical_system_package,
    tool_open_software_center,
    tool_remove_package,
)
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
        "puedes desinstalar office365WebDesktop",
        "desinstala vlc",
        "puedes desintalar zed",
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


def test_uninstall_command_requires_safe_app_target():
    apt_args = build_uninstall_args("vlc", "apt")
    snap_args = build_uninstall_args("office365WebDesktop", "snap")
    flatpak_args = build_uninstall_args("org.example.App", "flatpak")

    assert apt_args == ["pkexec", "apt", "remove", "-y", "vlc"]
    assert snap_args == ["pkexec", "snap", "remove", "office365WebDesktop"]
    assert flatpak_args == ["flatpak", "uninstall", "-y", "org.example.App"]

    assert is_critical_system_package("systemd")
    assert is_critical_system_package("linux-image-generic")
    try:
        build_uninstall_args("systemd", "apt")
        raise AssertionError("Un paquete critico no debe poder desinstalarse")
    except ValueError as exc:
        assert "critica" in str(exc).lower()


def test_ai_can_inspect_installed_apps_but_not_remove_silently():
    assert assess_command("which zed 2>/dev/null").level == SafetyLevel.SAFE
    assert assess_command("dpkg -l | grep -i zed").level == SafetyLevel.SAFE
    assert assess_command("snap list 2>/dev/null | grep -i zed").level == SafetyLevel.SAFE
    assert assess_command("flatpak list 2>/dev/null | grep -i zed").level == SafetyLevel.SAFE

    assert assess_command("snap remove zed").is_blocked
    assert assess_command("flatpak uninstall org.example.App").is_blocked


def test_interactive_uninstall_command_supports_sources(monkeypatch):
    monkeypatch.setattr("src.core.tools._resolve_uninstall_source", lambda source, package: source if source != "auto" else "apt")

    apt_cmd, apt_source, apt_package = build_interactive_uninstall_command("vlc", "apt")
    snap_cmd, snap_source, snap_package = build_interactive_uninstall_command("office365WebDesktop", "snap")
    flatpak_cmd, flatpak_source, flatpak_package = build_interactive_uninstall_command("org.example.App", "flatpak")

    assert (apt_cmd, apt_source, apt_package) == ("sudo apt remove vlc", "apt", "vlc")
    assert (snap_cmd, snap_source, snap_package) == ("sudo snap remove office365WebDesktop", "snap", "office365WebDesktop")
    assert (flatpak_cmd, flatpak_source, flatpak_package) == ("flatpak uninstall org.example.App", "flatpak", "org.example.App")


def test_uninstall_does_not_open_wrong_source(monkeypatch):
    monkeypatch.setattr("src.core.tools._is_apt_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_snap_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_flatpak_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._local_desktop_removal_paths", lambda package: [])

    try:
        build_interactive_uninstall_command("office365WebDesktop", "snap")
        raise AssertionError("No debe abrir snap remove si Snap dice que no esta instalado")
    except ValueError as exc:
        assert "no encontre" in str(exc).lower()


def test_uninstall_local_desktop_launcher_from_auto_source(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("src.core.tools._is_apt_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_snap_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_flatpak_installed", lambda package: False)

    desktop_dir = tmp_path / ".local" / "share" / "applications"
    app_dir = tmp_path / ".local" / "zed.app"
    bin_dir = tmp_path / ".local" / "bin"
    desktop_dir.mkdir(parents=True)
    (app_dir / "bin").mkdir(parents=True)
    bin_dir.mkdir(parents=True)
    zed_binary = app_dir / "bin" / "zed"
    zed_binary.write_text("#!/bin/sh\n", encoding="utf-8")
    zed_link = bin_dir / "zed"
    zed_link.symlink_to(zed_binary)
    launcher = desktop_dir / "dev.zed.Zed.desktop"
    launcher.write_text(
        "[Desktop Entry]\nName=Zed\nExec=" + str(zed_link) + " %U\nKeywords=zed;\n",
        encoding="utf-8",
    )

    command, source, package = build_interactive_uninstall_command("zed", "snap")

    assert source == "desktop"
    assert package == "zed"
    assert command.startswith("gio trash ")
    assert str(launcher) in command
    assert str(zed_link) in command
    assert str(app_dir) in command
    assert str(zed_binary) not in command


def test_remove_package_does_not_launch_when_not_installed(monkeypatch):
    monkeypatch.setattr("src.core.tools._is_apt_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_snap_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_flatpak_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._local_desktop_removal_paths", lambda package: [])
    monkeypatch.setattr(
        "src.core.tools.launch_in_terminal",
        lambda command, title="Asistente Linux": (_ for _ in ()).throw(AssertionError("No debe abrir terminal")),
    )

    result = tool_remove_package("office365WebDesktop", "snap")

    assert "no encontre" in result.lower()


def test_remove_local_desktop_uses_trash_without_terminal(tmp_path: Path, monkeypatch):
    launcher = tmp_path / "dev.zed.Zed.desktop"
    app_dir = tmp_path / "zed.app"
    link = tmp_path / "zed"
    for path in (launcher, app_dir, link):
        if path.suffix:
            path.write_text("desktop", encoding="utf-8")
        else:
            path.mkdir()

    monkeypatch.setattr("src.core.tools._is_apt_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_snap_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_flatpak_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._local_desktop_removal_paths", lambda package: [launcher, app_dir, link])
    monkeypatch.setattr("src.core.tools.shutil.which", lambda name: "/usr/bin/gio" if name == "gio" else None)
    monkeypatch.setattr(
        "src.core.tools.launch_in_terminal",
        lambda command, title="Asistente Linux": (_ for _ in ()).throw(AssertionError("No debe abrir terminal para desktop")),
    )

    calls = []

    def fake_run(args, **_kwargs):
        calls.append(args)
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("src.core.tools.subprocess.run", fake_run)

    result = tool_remove_package("zed", "auto")

    assert calls == [["gio", "trash", str(launcher), str(app_dir), str(link)]]
    assert "papelera" in result.lower()
    assert "no abri terminal" in result.lower()


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


def test_fuzzy_candidate_resolution_matches_office365(monkeypatch):
    monkeypatch.setattr("src.core.tools.shutil.which", lambda name: "/usr/bin/snap" if name == "snap" else None)
    monkeypatch.setattr("src.core.tools._run_probe", lambda args, timeout=8: (
        "Name                Version    Rev    Tracking       Publisher   Notes\n"
        "office365webdesktop 1.0.0      12     latest/stable  -           -\n"
    ))
    monkeypatch.setattr("src.core.tools._is_snap_installed", lambda pkg: pkg.lower() == "office365webdesktop")

    candidates = find_uninstall_candidates("office 365", "auto")
    assert len(candidates) >= 1
    assert candidates[0]["package"] == "office365webdesktop"
    assert candidates[0]["source"] == "snap"

    cmd, source, package = build_interactive_uninstall_command("office 365", "auto")
    assert source == "snap"
    assert package == "office365webdesktop"
    assert cmd == "sudo snap remove office365webdesktop"


def test_ambiguous_package_removal_raises_clarification_error(monkeypatch):
    monkeypatch.setattr("src.core.tools.find_uninstall_candidates", lambda query, source: [
        {"package": "libreoffice", "source": "apt", "display_name": "LibreOffice", "score": 0.8},
        {"package": "office365webdesktop", "source": "snap", "display_name": "Office 365", "score": 0.8},
    ])
    monkeypatch.setattr("src.core.tools._is_apt_installed", lambda pkg: False)
    monkeypatch.setattr("src.core.tools._is_snap_installed", lambda pkg: False)
    monkeypatch.setattr("src.core.tools._is_flatpak_installed", lambda pkg: False)
    monkeypatch.setattr("src.core.tools._local_desktop_removal_paths", lambda pkg: [])

    try:
        build_interactive_uninstall_command("office", "auto")
        raise AssertionError("Debe fallar ante múltiples candidatos")
    except ValueError as exc:
        assert "varias aplicaciones" in str(exc).lower()
        assert "libreoffice" in str(exc)
        assert "office365webdesktop" in str(exc)


def test_uninstall_fallback_opens_software_center_and_guides_user(monkeypatch):
    monkeypatch.setattr("src.core.tools._is_apt_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_snap_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._is_flatpak_installed", lambda package: False)
    monkeypatch.setattr("src.core.tools._local_desktop_removal_paths", lambda package: [])
    monkeypatch.setattr("src.core.tools.find_uninstall_candidates", lambda query, source: [])

    opened_mode = []
    monkeypatch.setattr(
        "src.core.tools.tool_open_software_center",
        lambda app_name="", mode="": opened_mode.append(mode) or "Se abrio la tienda de aplicaciones (snap-store).",
    )

    result = tool_remove_package("aplicacion_inexistente_xyz", "auto")

    assert "no encontre" in result.lower()
    assert "gestionar" in result.lower()
    assert "snap-store" in result.lower()
    assert opened_mode == ["installed"]


def test_open_software_center_modes_and_binary_resolution(monkeypatch):
    monkeypatch.setattr("src.core.tools._find_software_center_binary", lambda: "/usr/bin/gnome-software")
    launched = []
    monkeypatch.setattr("src.core.tools.subprocess.Popen", lambda args, **kwargs: launched.append(args))

    res = tool_open_software_center(mode="installed")
    assert "gestionar" in res.lower() or "instaladas" in res.lower()
    assert launched == [["/usr/bin/gnome-software", "--mode=installed"]]


def test_open_software_center_ubuntu_snap_store_gestionar(monkeypatch):
    monkeypatch.setattr("src.core.tools._find_software_center_binary", lambda: "/snap/bin/snap-store")
    monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
    monkeypatch.setattr("shutil.which", lambda name: "/snap/bin/snap-store" if name == "snap-store" else None)
    launched = []
    monkeypatch.setattr("src.core.tools.subprocess.Popen", lambda args, **kwargs: launched.append(args))

    res = tool_open_software_center(mode="gestionar")
    assert "gestionar" in res.lower()
    assert "centro de aplicaciones de ubuntu" in res.lower()
    assert launched == [["/snap/bin/snap-store", "--updates"]]


def test_ai_package_recommendation_fallback_docker():
    from src.gui.visual_views import _get_ai_package_recommendation

    class FakeApp:
        agent = None

    rec = _get_ai_package_recommendation(FakeApp(), "docker desktop")
    assert "docker" in rec.lower()
    assert "kvm" in rec.lower() or "deb" in rec.lower() or "docker.io" in rec.lower()


def test_ai_package_recommendation_uses_agent():
    from src.gui.visual_views import _get_ai_package_recommendation

    class FakeChoice:
        message = type("Msg", (), {"content": "Usa el comando: sudo apt install fake-pkg"})()

    class FakeCompletions:
        def create(self, **kwargs):
            return type("Resp", (), {"choices": [FakeChoice()]})()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    class FakeAgent:
        model = "fake-model"
        _client = FakeClient()

    class FakeApp:
        agent = FakeAgent()

    rec = _get_ai_package_recommendation(FakeApp(), "cualquier programa")
    assert "fake-pkg" in rec


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))

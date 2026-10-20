"""Pruebas unitarias para la capa de ejecución privilegiada con PolicyKit (pkexec)."""

import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from src.core import privilege, tools
from src.gui import system_diagnostics


def test_privilege_status_detection(monkeypatch):
    """Comprueba el reporte de estado de PolicyKit según presencia de pkexec y display."""
    monkeypatch.setattr(privilege, "is_pkexec_available", lambda: True)
    monkeypatch.setenv("DISPLAY", ":0")
    status = privilege.get_privilege_status()
    assert status["pkexec_available"] is True
    assert status["graphical_session"] is True
    assert status["policykit_enabled"] is True
    assert status["preferred_mechanism"] == "pkexec"

    # En sesión headless sin display
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    status_headless = privilege.get_privilege_status()
    assert status_headless["graphical_session"] is False
    assert status_headless["policykit_enabled"] is False
    assert status_headless["preferred_mechanism"] == "terminal"


@pytest.mark.parametrize("argv", [
    ["systemctl", "restart", "bluetooth"],
    ["systemctl", "start", "cups"],
    ["systemctl", "stop", "nginx"],
    ["apt", "update"],
    ["apt", "upgrade", "-y"],
    ["apt", "install", "-y", "htop"],
    ["apt", "remove", "-y", "vlc"],
    ["dpkg", "--configure", "-a"],
    ["snap", "refresh"],
    ["fwupdmgr", "refresh", "--force"],
])
def test_validate_allowed_privileged_commands(argv):
    """Acciones legítimas y estructuradas del sistema son permitidas."""
    valid, reason = privilege.validate_privileged_request(argv)
    assert valid is True
    assert reason == ""


@pytest.mark.parametrize("argv,expected_msg", [
    ([], "vacía"),
    (["bash", "-c", "rm -rf /"], "no pertenece a la lista blanca"),
    (["rm", "-rf", "/etc"], "no pertenece a la lista blanca"),
    (["cat", "/etc/shadow"], "no pertenece a la lista blanca"),
    (["systemctl", "stop", "dbus"], "servicio crítico"),
    (["systemctl", "disable", "display-manager"], "servicio crítico"),
    (["systemctl", "restart", "polkit"], "servicio crítico"),
    (["systemctl", "status", "bluetooth"], "no autorizada"),  # status no requiere privilegios
    (["apt", "remove", "-y", "systemd"], "paquete crítico"),
    (["apt", "remove", "-y", "bash"], "paquete crítico"),
    (["apt", "install", "vlc; reboot"], "Identificador de paquete sospechoso"),
    (["snap", "run", "curl"], "no autorizado"),
])
def test_validate_blocked_privileged_commands(argv, expected_msg):
    """Comandos peligrosos, no autorizados o sobre componentes críticos son bloqueados."""
    valid, reason = privilege.validate_privileged_request(argv)
    assert valid is False
    assert expected_msg in reason


def test_execute_privileged_action_blocked():
    """Un comando bloqueado no se intenta ejecutar y retorna mechanism='blocked'."""
    res = privilege.execute_privileged_action(["rm", "-rf", "/"])
    assert res.success is False
    assert res.mechanism == "blocked"
    assert "bloqueada por política" in res.message


def test_execute_privileged_action_pkexec_success(monkeypatch):
    """Cuando pkexec tiene éxito (retorno 0), retorna success=True y mechanism='pkexec'."""
    monkeypatch.setattr(privilege, "can_use_pkexec", lambda: True)

    def mock_run(cmd, **kwargs):
        assert cmd[0] == "pkexec"
        return SimpleNamespace(returncode=0, stdout="Restarted successfully.", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    res = privilege.execute_privileged_action(["systemctl", "restart", "bluetooth"])
    assert res.success is True
    assert res.mechanism == "pkexec"
    assert res.returncode == 0
    assert "éxito" in res.message


def test_execute_privileged_action_pkexec_user_cancelled(monkeypatch):
    """Si el usuario cancela el diálogo de PolicyKit (código 126), reporta cancelación amigable."""
    monkeypatch.setattr(privilege, "can_use_pkexec", lambda: True)

    def mock_run(cmd, **kwargs):
        return SimpleNamespace(returncode=126, stdout="", stderr="Error executing command as another user: Request dismissed")

    monkeypatch.setattr(subprocess, "run", mock_run)

    res = privilege.execute_privileged_action(["systemctl", "restart", "bluetooth"])
    assert res.success is False
    assert res.mechanism == "cancelled"
    assert "cancelada" in res.message


def test_execute_privileged_action_terminal_fallback(monkeypatch):
    """En ausencia de PolicyKit gráfico, se abre una terminal interactiva con sudo."""
    monkeypatch.setattr(privilege, "can_use_pkexec", lambda: False)

    launched = []
    def mock_launch(command, title):
        launched.append((command, title))
        return True, "Terminal abierta."

    monkeypatch.setattr("src.core.tools.launch_in_terminal", mock_launch)

    res = privilege.execute_privileged_action(["systemctl", "restart", "bluetooth"], title="Servicio bluetooth")
    assert res.success is True
    assert res.mechanism == "terminal"
    assert len(launched) == 1
    assert "sudo systemctl restart bluetooth" in launched[0][0]


def test_tool_manage_service_uses_policykit_and_reports_result(monkeypatch):
    """tool_manage_service ejecuta servicios no críticos mediante PolicyKit."""
    monkeypatch.setattr(privilege, "can_use_pkexec", lambda: True)

    def mock_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(tools, "tool_run_command_silent", lambda cmd: "Active: active (running)")

    output = tools.tool_manage_service("bluetooth", "restart")
    assert "PolicyKit" in output
    assert "Active: active" in output


def test_tool_manage_service_handles_user_cancellation(monkeypatch):
    """tool_manage_service informa cuando el usuario cancela la autenticación en PolicyKit."""
    monkeypatch.setattr(privilege, "can_use_pkexec", lambda: True)

    def mock_run(cmd, **kwargs):
        return SimpleNamespace(returncode=126, stdout="", stderr="Dismissed")

    monkeypatch.setattr(subprocess, "run", mock_run)

    output = tools.tool_manage_service("bluetooth", "restart")
    assert "Autenticación cancelada" in output
    assert "no fue modificado" in output


def test_tool_manage_service_blocks_critical_service():
    """Servicios críticos no llegan a ejecutarse con PolicyKit ni con terminal."""
    output = tools.tool_manage_service("dbus", "stop")
    assert "crítico" in output


def test_restart_network_privileged_action(monkeypatch):
    """El reinicio de NetworkManager está autorizado para recuperación en PolicyKit."""
    monkeypatch.setattr(privilege, "can_use_pkexec", lambda: True)

    def mock_run(cmd, **kwargs):
        assert cmd == ["pkexec", "systemctl", "restart", "NetworkManager"]
        return SimpleNamespace(returncode=0, stdout="Network restarted.", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = privilege.execute_privileged_action(["systemctl", "restart", "NetworkManager"])
    assert result.success is True
    assert result.mechanism == "pkexec"
    assert "PolicyKit" in result.message


def test_jsapi_polkit_status(monkeypatch):
    """JsApi en webview_app expone get_polkit_status."""
    from src.gui.webview_app import JsApi
    monkeypatch.setattr(privilege, "is_pkexec_available", lambda: True)
    monkeypatch.setenv("DISPLAY", ":0")

    api = JsApi()
    status = api.get_polkit_status()
    assert status["pkexec_available"] is True
    assert status["policykit_enabled"] is True


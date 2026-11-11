"""Routing must not claim app compatibility or mutate the machine during discovery."""
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.gui import compatibility as service
from src.gui.compatibility_catalog import compatibility_catalog
from src.gui.webview_app import JsApi


@pytest.mark.parametrize("use,expected", [
    ("application", "bottles"), ("steam", "proton"), ("stores", "heroic"),
    ("other-game", "lutris"), ("full-windows", "winboat"),
])
def test_routes_are_advisory_even_with_special_requirements(use, expected):
    result = service.recommend_compatibility({"use_case": use, "application": "Mi app 2024",
                                             "special_requirements": True})
    assert result["tool"] == expected
    assert result["needs_review"] is True
    assert "No se ha verificado" in result["notice"]
    assert "fabricante" in result["checks"][0]


@pytest.mark.parametrize("payload", [None, [], {"use_case": []}, {"use_case": "arbitrary-command"},
                                      {"application": "x" * 161}, {"application": {}},
                                      {"special_requirements": "false"}])
def test_invalid_requests_are_rejected_at_bridge(payload):
    result = JsApi.__new__(JsApi).recommend_windows_compatibility(payload)
    assert result["success"] is False
    assert result["message"]


def test_application_name_is_only_data(monkeypatch):
    execute = Mock(side_effect=AssertionError("Must not execute a user string"))
    monkeypatch.setattr(service.subprocess, "run", execute)
    text = '<img src=x onerror=alert(1)>; $(touch /tmp/unwanted)'
    result = service.recommend_compatibility({"application": text})
    assert result["application"] == text
    execute.assert_not_called()


def mock_machine(monkeypatch, binaries):
    monkeypatch.setattr(service.shutil, "which", lambda name: "/usr/bin/" + name if name in binaries else None)
    monkeypatch.setattr(service.psutil, "virtual_memory", lambda: SimpleNamespace(total=8 * 1024**3))
    monkeypatch.setattr(service.shutil, "disk_usage", lambda _: SimpleNamespace(free=64 * 1024**3))
    monkeypatch.setattr(service.os.path, "exists", lambda _: True)
    monkeypatch.setattr(service.os, "access", lambda *_: False)


def test_detection_is_read_only_and_proton_is_not_claimed_installed(monkeypatch):
    mock_machine(monkeypatch, {"flatpak", "wine", "docker", "xfreerdp"})
    execute = Mock(return_value=SimpleNamespace(returncode=0, stdout="com.usebottles.bottles\ncom.valvesoftware.Steam\n"))
    monkeypatch.setattr(service.subprocess, "run", execute)
    result = service.compatibility_overview()
    execute.assert_called_once_with(["flatpak", "list", "--app", "--columns=application"],
                                    capture_output=True, text=True, timeout=5, check=False)
    assert result["tools"]["bottles"]["formats"] == ["Flatpak"]
    assert result["tools"]["wine"]["detected"]
    assert "Proton" in result["tools"]["proton"]["note"]
    assert "dentro de Steam" in result["tools"]["proton"]["note"]
    assert result["tools"]["winboat"]["status"] == "No detectado"
    assert result["machine"]["kvm_present"] and not result["machine"]["kvm_access"]
    assert result["machine"]["ram_gib"] == 8


@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired("flatpak", 5), OSError("unavailable"), None])
def test_failed_flatpak_discovery_is_unknown_not_absent(monkeypatch, failure):
    mock_machine(monkeypatch, {"flatpak", "lutris"})
    execute = Mock(side_effect=failure, return_value=SimpleNamespace(returncode=1))
    monkeypatch.setattr(service.subprocess, "run", execute)
    result = service.compatibility_overview()
    assert result["tools"]["bottles"]["status"] == "Sin comprobar"
    assert result["tools"]["lutris"]["status"] == "Detectado"
    assert len(result["notices"]) == 3


def test_absent_managers_never_start_a_process_and_missing_metrics_survive(monkeypatch):
    mock_machine(monkeypatch, set())
    execute = Mock(side_effect=AssertionError("No process needed"))
    monkeypatch.setattr(service.subprocess, "run", execute)
    monkeypatch.setattr(service.shutil, "disk_usage", Mock(side_effect=OSError))
    monkeypatch.setattr(service.psutil, "virtual_memory", Mock(side_effect=OSError))
    result = service.compatibility_overview()
    assert result["machine"]["home_free_gib"] is None
    assert result["machine"]["ram_gib"] is None
    execute.assert_not_called()


def test_catalog_routes_and_installation_contract():
    catalog = compatibility_catalog()
    tools = {tool["id"]: tool for tool in catalog["tools"]}
    assert len(tools) == len(catalog["tools"]) == 7
    assert set(tools) == set(service.DETECTORS)
    for primary, _, alternatives in service.ROUTES.values():
        assert {primary, *alternatives} <= tools.keys()
    for tool in tools.values():
        assert tool["steps"] and tool["requirements"] and tool["limits"]
        assert all(source["url"].startswith("https://") for source in tool["sources"])
        for method in tool["methods"]:
            assert sum(key in method for key in ("package", "query", "url", "local")) == 1
            if "package" in method:
                assert method["source"] == "flatpak"
    assert not tools["wineboot"]["methods"]
    tools["wine"]["steps"].clear()
    assert compatibility_catalog()["tools"][1]["steps"]


def test_bridge_returns_catalog_and_read_only_overview(monkeypatch):
    from src.gui import webview_app
    monkeypatch.setattr(webview_app, "compatibility_overview", lambda: {"tools": {}})
    api = JsApi.__new__(JsApi)
    assert api.get_compatibility_overview() == {"tools": {}}
    assert len(api.get_compatibility_catalog()["tools"]) == 7


def test_file_picker_uses_independent_window_without_opening_installer():
    api = JsApi.__new__(JsApi)
    api.window = Mock()
    api._migration_window = Mock()
    api._migration_window.create_file_dialog.return_value = ("/tmp/WinBoat.deb",)
    api.prepare_local_package = Mock(return_value={"success": True, "preview": {}})
    assert api.choose_local_package("migration")["success"]
    api._migration_window.create_file_dialog.assert_called_once()
    api.window.create_file_dialog.assert_not_called()
    api.prepare_local_package.assert_called_once_with("/tmp/WinBoat.deb")
    api._migration_window = None
    assert not api.choose_local_package("migration")["success"]

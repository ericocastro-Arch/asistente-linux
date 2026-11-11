"""La planificación no debe convertir inventarios en órdenes ejecutables."""
from types import SimpleNamespace
from unittest.mock import Mock
import threading

import pytest
from src.gui.migration import build_migration_plan
from src.gui.webview_app import JsApi
from src.gui import webview_app
from src.gui import migration


def test_winget_inventory_preserves_unknowns_and_deduplicates():
    result = build_migration_plan(
        "Nombre                 Id                  Versión\n"
        "---------------------------------------------------\n"
        "Google Chrome          Google.Chrome       130\n"
        "Microsoft Word\nGoogle Chrome\nMi herramienta privada\nsudo rm -rf /"
    )
    assert result["total"] == 4
    assert [e["route"] for e in result["entries"]] == ["native", "alternative", "review", "review"]
    assert result["entries"][-1]["match"] is None


def test_typo_requires_user_selection():
    entry = build_migration_plan("Photoshp")["entries"][0]
    assert entry["match"] is None
    assert entry["suggestion"]["id"] == "photoshop"
    assert entry["route"] == "review"


@pytest.mark.parametrize("inventory", [None, "a"*20001, "\n".join(f"App {i}" for i in range(101))])
def test_inventory_limits(inventory):
    with pytest.raises(ValueError):
        build_migration_plan(inventory)


def test_window_is_reused_and_can_reopen_after_close(monkeypatch):
    closed = []
    class Event:
        def __iadd__(self, callback):
            closed.append(callback)
            return self
    window = SimpleNamespace(restore=Mock(), show=Mock(), events=SimpleNamespace(closed=Event()))
    create = Mock(return_value=window)
    monkeypatch.setattr(webview_app.webview, "create_window", create)
    api = JsApi.__new__(JsApi)
    api._migration_lock = threading.Lock()
    api._migration_window = None
    assert api.open_migration_window()["success"]
    assert api.open_migration_window()["success"]
    assert create.call_count == 1
    window.restore.assert_called_once()
    closed[0]()
    assert api.open_migration_window()["success"]
    assert create.call_count == 2


def test_saved_plan_round_trip_rebuilds_catalog_and_preserves_progress(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    migration.save_plan({'inventory': 'Chrome', 'entries': [
        {'input': 'Chrome', 'match': {'id': 'chrome', 'searches': [{'query': 'malicious'}]}, 'tested': True}
    ], 'checks': {'files': True, 'backup': False}})
    result = migration.load_plan()
    assert result['entries'][0]['tested'] is True
    assert result['entries'][0]['match']['searches'][0]['query'] == 'chrome'
    assert result['checks']['files'] is True
    assert result['checks']['backup'] is False


def test_bad_save_does_not_replace_existing_plan(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    migration.save_plan({'inventory': 'Word'})
    with pytest.raises(ValueError):
        migration.save_plan({'inventory': 'x' * 20001})
    assert migration.load_plan()['inventory'] == 'Word'

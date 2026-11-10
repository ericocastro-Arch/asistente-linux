"""Garantiza que el módulo de bienvenida sea una ventana independiente y no esté en el dashboard."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.gui import webview_app

WEB = Path(__file__).resolve().parents[1] / "src" / "gui" / "web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_index_dashboard_has_no_welcome_in_home_view():
    html = read("index.html")
    assert 'id="welcomeCommandBanner"' not in html
    assert 'id="firstRunDialog"' not in html
    assert 'id="welcomeBannerMount"' not in html
    assert 'id="welcomeDialogMount"' not in html
    assert "welcome-templates.js" not in html
    assert "welcome.js" not in html
    assert "welcome.css" not in html
    assert '<section class="cyber-dashboard-panel">' in html


def test_app_js_opens_welcome_window_without_welcome_internals():
    app = read("app.js")
    for symbol in (
        "initWelcomeStudio",
        "syncWelcome",
        "populateWelcomeTelemetry",
        "completeFirstRun",
        "firstRunDialog",
        "cachedDistroInfo",
    ):
        assert symbol not in app, symbol
    assert "openWelcomeWindow" in app
    assert "open_welcome_window" in app


def test_welcome_window_is_standalone_html_module():
    welcome_html = read("welcome.html")
    assert "<!DOCTYPE html>" in welcome_html
    assert 'src="welcome.js"' in welcome_html
    assert 'href="welcome.css"' in welcome_html
    assert 'id="firstRunTitle"' in welcome_html
    assert 'id="welcomeStepLaunchpadTitle"' in welcome_html
    assert 'data-welcome-profile="daily"' in welcome_html

    welcome_css = read("welcome.css")
    assert ".welcome-window-body" in welcome_css
    assert ".welcome-studio-shell" in welcome_css

    welcome_js = read("welcome.js")
    assert "open_welcome_window" not in welcome_js or "welcome_navigate" in welcome_js


def test_jsapi_open_close_and_navigate_welcome_window(monkeypatch):
    api = webview_app.JsApi.__new__(webview_app.JsApi)
    api.window = MagicMock()
    api._welcome_window = None
    api._welcome_lock = webview_app.threading.Lock()

    # Test open_welcome_window when webview.create_window succeeds
    mock_window = MagicMock()
    mock_window.events = SimpleNamespace(closed=MagicMock())
    monkeypatch.setattr(webview_app.webview, "create_window", lambda *args, **kwargs: mock_window)

    res_open = api.open_welcome_window()
    assert res_open["success"] is True
    assert api._welcome_window is mock_window

    # Test restore/show when already open
    res_restore = api.open_welcome_window()
    assert res_restore["success"] is True
    mock_window.restore.assert_called()

    # Test welcome_navigate syncs profile, theme, and tool
    res_nav = api.welcome_navigate(target="troubleshooter", profile="development", theme="violet")
    assert res_nav["success"] is True
    assert any("openTool" in str(call) for call in api.window.evaluate_js.call_args_list)

    # Test close_welcome_window
    res_close = api.close_welcome_window()
    assert res_close["success"] is True
    assert api._welcome_window is None
    mock_window.destroy.assert_called()

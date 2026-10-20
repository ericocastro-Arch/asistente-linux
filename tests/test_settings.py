"""Pruebas unitarias para el gestor de configuración y modelos de LinuxMate AI."""

import os
from unittest.mock import patch
from src.core.settings_manager import (
    get_settings,
    save_settings,
    check_llm_connection,
    clear_assistant_memory,
    run_system_cleanup,
    get_system_diagnostics,
)
from src.core.storage import init_db
from src.gui.webview_app import JsApi


def test_get_settings_structure():
    settings = get_settings()
    assert "llm" in settings
    assert "security" in settings
    assert "appearance" in settings
    assert "memory" in settings
    assert "system_diagnostics" in settings

    llm = settings["llm"]
    assert "provider" in llm
    assert "groq_api_key" in llm
    assert "groq_model" in llm
    assert "temperature" in llm


def test_save_settings_updates_env_and_memory(tmp_path):
    fake_env = tmp_path / ".env"
    fake_env.write_text("LLM_PROVIDER=groq\nGROQ_MODEL=llama-3.3-70b-versatile\n", encoding="utf-8")

    with patch("src.core.settings_manager.ENV_PATH", fake_env):
        payload = {
            "llm": {
                "provider": "ollama",
                "groq_model": "llama-3.1-8b-instant",
                "temperature": 0.5,
            },
            "security": {
                "security_mode": "autonomous",
            },
            "appearance": {
                "enable_blur_effects": False,
            }
        }
        res = save_settings(payload)
        assert res["success"] is True

        content = fake_env.read_text(encoding="utf-8")
        assert "LLM_PROVIDER=ollama" in content
        assert "GROQ_MODEL=llama-3.1-8b-instant" in content
        assert "SECURITY_MODE=autonomous" in content
        assert "ENABLE_BLUR_EFFECTS=false" in content

        assert os.environ.get("LLM_PROVIDER") == "ollama"
        assert os.environ.get("GROQ_MODEL") == "llama-3.1-8b-instant"


def test_save_settings_keeps_env_private(tmp_path):
    fake_env = tmp_path / ".env"
    fake_env.write_text("GROQ_API_KEY=gsk_secreta\n", encoding="utf-8")
    fake_env.chmod(0o664)

    with patch("src.core.settings_manager.ENV_PATH", fake_env):
        res = save_settings({"llm": {"provider": "groq"}})

    assert res["success"] is True
    assert fake_env.stat().st_mode & 0o777 == 0o600
    assert "GROQ_API_KEY=gsk_secreta" in fake_env.read_text(encoding="utf-8")
    assert not (tmp_path / ".env.tmp").exists()


def test_check_llm_connection_requires_api_key_when_applicable():
    res = check_llm_connection("groq", "", "llama-3.3-70b-versatile")
    assert res["success"] is False
    assert "clave de API" in res["error"]


def test_system_diagnostics():
    diag = get_system_diagnostics()
    assert "python_version" in diag
    assert "apt" in diag
    assert "snap" in diag


def test_system_cleanup():
    res = run_system_cleanup()
    assert res["success"] is True
    assert "freed_mb" in res


def test_clear_assistant_memory(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    init_db()
    res = clear_assistant_memory()
    assert res["success"] is True


def test_webview_jsapi_settings():
    api = JsApi()
    settings = api.get_settings()
    assert "llm" in settings

    diag = api.get_system_environment_diagnostics()
    assert "python_version" in diag

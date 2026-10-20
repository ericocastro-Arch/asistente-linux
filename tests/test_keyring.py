"""Pruebas unitarias para el almacenamiento seguro de claves en Keyring y fallback a .env."""

from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from src.core import keyring_manager, providers, settings_manager
from src.gui.webview_app import JsApi


class InMemoryKeyringBackend:
    """Backend en memoria para pruebas de keyring sin depender de D-Bus ni SecretService."""
    priority = 10
    name = "MockDesktopKeyring"

    def __init__(self):
        self.storage = {}

    def get_password(self, service, username):
        return self.storage.get((service, username))

    def set_password(self, service, username, password):
        self.storage[(service, username)] = password

    def delete_password(self, service, username):
        self.storage.pop((service, username), None)


def test_keyring_unavailable_behavior_with_fail_backend(monkeypatch):
    """Cuando no hay backend utilizable, keyring_manager degrada silenciosamente a .env / environ."""
    # Simular backend fallido de prioridad 0
    fail_backend = SimpleNamespace(priority=0, name="fail")
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.return_value = fail_backend
    monkeypatch.setattr(keyring_manager, "keyring", mock_keyring)

    assert keyring_manager.is_keyring_available() is False
    assert "No disponible" in keyring_manager.get_backend_name()

    # Fallback a os.environ
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fallback_env")
    assert keyring_manager.get_api_key("groq") == "gsk_fallback_env"

    # set_api_key no falla y retorna False al no haber keyring
    assert keyring_manager.set_api_key("groq", "gsk_nueva") is False
    assert keyring_manager.delete_api_key("groq") is False
    assert keyring_manager.migrate_env_keys_to_keyring() == {}

    status = keyring_manager.get_keyring_status()
    assert status["available"] is False
    assert status["stored_providers"] == []


def test_keyring_functional_storage_and_retrieval(monkeypatch):
    """Con backend activo, guarda, recupera y elimina credenciales en el keyring."""
    mock_backend = InMemoryKeyringBackend()
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.return_value = mock_backend
    mock_keyring.get_password.side_effect = mock_backend.get_password
    mock_keyring.set_password.side_effect = mock_backend.set_password
    mock_keyring.delete_password.side_effect = mock_backend.delete_password
    monkeypatch.setattr(keyring_manager, "keyring", mock_keyring)

    assert keyring_manager.is_keyring_available() is True
    assert keyring_manager.get_backend_name() == "MockDesktopKeyring"

    # Guardar clave
    assert keyring_manager.set_api_key("openai", "sk-proj-test123") is True
    # Recuperar clave
    assert keyring_manager.get_api_key("openai") == "sk-proj-test123"

    # El keyring tiene prioridad sobre os.environ si ambos existen
    monkeypatch.setenv("OPENAI_API_KEY", "sk-old-in-env")
    assert keyring_manager.get_api_key("openai") == "sk-proj-test123"

    # Verificar estado
    status = keyring_manager.get_keyring_status()
    assert status["available"] is True
    assert "openai" in status["stored_providers"]

    # Eliminar clave
    assert keyring_manager.delete_api_key("openai") is True
    # Ahora cae a os.environ
    assert keyring_manager.get_api_key("openai") == "sk-old-in-env"


def test_keyring_migration_from_env(monkeypatch):
    """migrate_env_keys_to_keyring copia variables de entorno válidas al keyring."""
    mock_backend = InMemoryKeyringBackend()
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.return_value = mock_backend
    mock_keyring.get_password.side_effect = mock_backend.get_password
    mock_keyring.set_password.side_effect = mock_backend.set_password
    mock_keyring.delete_password.side_effect = mock_backend.delete_password
    monkeypatch.setattr(keyring_manager, "keyring", mock_keyring)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("GROQ_API_KEY", "tu_clave_aqui_placeholder")  # Debe ser ignorado
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    results = keyring_manager.migrate_env_keys_to_keyring(["anthropic", "groq", "openai"])
    assert results == {"anthropic": True}
    assert keyring_manager.get_api_key("anthropic") == "sk-ant-test-key"
    assert "groq" not in results


def test_provider_config_uses_keyring_key(monkeypatch):
    """providers.provider_config debe leer la clave desde keyring si está configurada."""
    mock_backend = InMemoryKeyringBackend()
    mock_backend.set_password("asistente-linux", "DEEPSEEK_API_KEY", "ds-key-from-keyring")
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.return_value = mock_backend
    mock_keyring.get_password.side_effect = mock_backend.get_password
    monkeypatch.setattr(keyring_manager, "keyring", mock_keyring)

    key, model, url = providers.provider_config("deepseek")
    assert key == "ds-key-from-keyring"


def test_save_settings_keeps_api_key_only_in_keyring(tmp_path, monkeypatch):
    """Con keyring disponible, save_settings no duplica la clave en .env."""
    fake_env = tmp_path / ".env"
    monkeypatch.setattr(settings_manager, "ENV_PATH", fake_env)

    mock_backend = InMemoryKeyringBackend()
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.return_value = mock_backend
    mock_keyring.get_password.side_effect = mock_backend.get_password
    mock_keyring.set_password.side_effect = mock_backend.set_password
    mock_keyring.delete_password.side_effect = mock_backend.delete_password
    monkeypatch.setattr(keyring_manager, "keyring", mock_keyring)

    payload = {
        "llm": {
            "provider": "gemini",
            "gemini_api_key": "ai-studio-gemini-key",
            "gemini_model": "gemini-3.8-flash",
        },
        "security": {"security_mode": "safe"},
        "appearance": {},
    }

    res = settings_manager.save_settings(payload)
    assert res["success"] is True

    # Comprobar que se guardó en el keyring
    assert mock_backend.get_password("asistente-linux", "GEMINI_API_KEY") == "ai-studio-gemini-key"

    assert "GEMINI_API_KEY" not in fake_env.read_text(encoding="utf-8")
    assert fake_env.stat().st_mode & 0o777 == 0o600
    assert "GEMINI_API_KEY" not in __import__("os").environ

    # Comprobar get_settings
    settings = settings_manager.get_settings()
    assert settings["llm"]["gemini_api_key"] == "ai-studio-gemini-key"
    assert settings["keyring"]["available"] is True
    assert "gemini" in settings["keyring"]["stored_providers"]


def test_save_settings_falls_back_to_private_env_without_keyring(tmp_path, monkeypatch):
    fake_env = tmp_path / ".env"
    monkeypatch.setattr(settings_manager, "ENV_PATH", fake_env)
    monkeypatch.setattr(keyring_manager, "keyring", MagicMock())
    monkeypatch.setattr(keyring_manager, "is_keyring_available", lambda: False)

    result = settings_manager.save_settings({
        "llm": {"groq_api_key": "gsk-fallback"},
        "security": {},
        "appearance": {},
    })

    assert result["success"] is True
    assert "GROQ_API_KEY=gsk-fallback" in fake_env.read_text(encoding="utf-8")
    assert fake_env.stat().st_mode & 0o777 == 0o600


def test_migrate_keys_to_keyring_removes_only_migrated_env_keys(tmp_path, monkeypatch):
    fake_env = tmp_path / ".env"
    fake_env.write_text(
        "ANTHROPIC_API_KEY=sk-ant-migrate\nGROQ_API_KEY=tu_clave_aqui_placeholder\nLLM_PROVIDER=groq\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_manager, "ENV_PATH", fake_env)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-migrate")
    monkeypatch.setenv("GROQ_API_KEY", "tu_clave_aqui_placeholder")

    backend = InMemoryKeyringBackend()
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.return_value = backend
    mock_keyring.get_password.side_effect = backend.get_password
    mock_keyring.set_password.side_effect = backend.set_password
    monkeypatch.setattr(keyring_manager, "keyring", mock_keyring)

    result = settings_manager.migrate_keys_to_keyring()

    assert result["success"] is True
    env_text = fake_env.read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" not in env_text
    assert "GROQ_API_KEY=tu_clave_aqui_placeholder" in env_text
    assert "LLM_PROVIDER=groq" in env_text
    assert "ANTHROPIC_API_KEY" not in __import__("os").environ


def test_jsapi_keyring_integration(monkeypatch):
    """JsApi en webview_app expone get_keyring_status y migrate_api_keys_to_keyring."""
    mock_backend = InMemoryKeyringBackend()
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.return_value = mock_backend
    mock_keyring.get_password.side_effect = mock_backend.get_password
    mock_keyring.set_password.side_effect = mock_backend.set_password
    monkeypatch.setattr(keyring_manager, "keyring", mock_keyring)

    monkeypatch.setenv("GROQ_API_KEY", "gsk_migrated_from_env")

    api = JsApi()
    status = api.get_keyring_status()
    assert status["available"] is True

    migration = api.migrate_api_keys_to_keyring()
    assert migration["success"] is True
    assert migration["migrated"].get("groq") is True

"""Provider routing and persistence without external requests or real keys."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from dotenv import dotenv_values

from src.core import providers, settings_manager, agent, llm, keyring_manager


@pytest.mark.parametrize("provider", providers.PROVIDERS)
def test_provider_routes_client_and_model(provider, monkeypatch):
    factory = MagicMock()
    monkeypatch.setattr(providers, "OpenAI", factory)
    monkeypatch.setattr(providers, "Groq", factory)
    client, model, key = providers.create_provider_client(
        provider, "test-only-key", "model-from-account", "https://example.test/api", timeout=25)
    assert client is factory.return_value
    assert model == "model-from-account"
    assert key == "test-only-key"
    assert factory.call_args.kwargs == dict(api_key=key, base_url="https://example.test/api/v1" if provider == "ollama" else "https://example.test/api", timeout=25, max_retries=0)


@pytest.mark.parametrize("provider", providers.PROVIDERS)
def test_provider_settings_roundtrip(provider, tmp_path, monkeypatch):
    path = tmp_path / ".env"
    monkeypatch.setattr(settings_manager, "ENV_PATH", path)
    monkeypatch.setattr(settings_manager, "is_keyring_available", lambda: False)
    monkeypatch.setattr(keyring_manager, "is_keyring_available", lambda: False)
    prefix = provider.upper()
    for suffix in ("API_KEY", "MODEL", "BASE_URL"):
        monkeypatch.delenv(f"{prefix}_{suffix}", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    fields = {f"{provider}_api_key": "test-only-#'key", f"{provider}_model": "custom-model", f"{provider}_base_url": "https://example.test/v1"}
    assert settings_manager.save_settings({"llm": {"provider": provider, **fields}})["success"]
    stored = dotenv_values(path)
    for key, value in fields.items():
        assert stored[key.upper()] == value
    reloaded = settings_manager.get_settings()["llm"]
    assert all(reloaded[key] == value for key, value in fields.items())


def test_validation_does_not_write_or_update_environment(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("LLM_PROVIDER=groq\n")
    monkeypatch.setattr(settings_manager, "ENV_PATH", path)
    monkeypatch.setattr(settings_manager, "is_keyring_available", lambda: True)
    monkeypatch.setattr(settings_manager, "set_api_key", lambda *_args: True)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    for payload in ({"provider": "unknown"}, {"request_timeout": "nan"}, {"max_tokens": 0}, {"deepseek_api_key": "key\nLLM_PROVIDER=other"}):
        assert not settings_manager.save_settings({"llm": payload})["success"]
        assert path.read_text() == "LLM_PROVIDER=groq\n"
    assert providers.os.environ["LLM_PROVIDER"] == "groq"


def test_disk_error_preserves_active_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_manager, "ENV_PATH", tmp_path)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert not settings_manager.save_settings({"llm": {"provider": "deepseek"}})["success"]
    assert providers.os.environ["LLM_PROVIDER"] == "groq"


@pytest.mark.parametrize("provider", ["deepseek", "qwen", "moonshot", "zai", "anthropic", "gemini", "xai", "together", "custom"])
def test_agent_and_chat_use_selected_provider(provider, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv(f"{provider.upper()}_API_KEY", "test-only-key")
    monkeypatch.setenv(f"{provider.upper()}_MODEL", "account-model")
    monkeypatch.setenv(f"{provider.upper()}_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT", "125")
    monkeypatch.setenv("LLM_MAX_TOKENS", "4096")
    factory = MagicMock()
    monkeypatch.setattr(providers, "OpenAI", factory)
    monkeypatch.setattr(agent, "_build_system_context", lambda: "test")
    monkeypatch.setattr(agent, "start_session", lambda _: 1)
    monkeypatch.setattr(agent, "load_memory", lambda **kwargs: [])
    active = agent.LinuxAgent()
    fallback = llm.GroqClient()
    assert active.provider == fallback.provider == provider
    assert active.model == fallback.model == "account-model"
    assert active.request_timeout == 125
    assert active.max_tokens == 4096
    assert factory.call_args.kwargs["base_url"] == "https://example.test/v1"


def test_probe_and_model_list_use_unsaved_credentials(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    client.chat.completions.create.return_value = SimpleNamespace(choices=[object()])
    client.models.list.return_value = SimpleNamespace(data=[SimpleNamespace(id="second"), SimpleNamespace(id="first")])
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(providers, "OpenAI", factory)
    assert settings_manager.check_llm_connection("deepseek", "draft-key", "draft-model", "https://draft.test/v1")["success"]
    assert factory.call_args.kwargs["api_key"] == "draft-key"
    assert client.chat.completions.create.call_args.kwargs["model"] == "draft-model"
    assert settings_manager.list_llm_models("deepseek", "draft-key", "https://draft.test/v1")["models"] == ["first", "second"]


def test_sampling_and_reasoning_parameters():
    assert "temperature" not in providers.completion_options("anthropic", "claude-opus-5-5", .2, 1500)
    assert providers.completion_options("openai", "o3-mini", .2, 1500) == {"max_completion_tokens": 1500}
    assert providers.completion_options("moonshot", "kimi-k2.6", .2, 1500)["extra_body"]["thinking"]["type"] == "disabled"

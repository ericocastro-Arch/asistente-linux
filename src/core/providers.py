"""Shared provider configuration for settings, chat and the tool agent."""

import math
import os
from urllib.parse import urlsplit

from groq import Groq
from openai import OpenAI

from src.core.keyring_manager import get_api_key


def _provider(name, region, base_url, model, docs, note=""):
    return dict(name=name, region=region, base_url=base_url, model=model, docs=docs, note=note)


PROVIDERS = {
    "groq": _provider("Groq", "Estados Unidos", "https://api.groq.com", "llama-3.3-70b-versatile", "https://console.groq.com/docs/models"),
    "nvidia": _provider("NVIDIA NIM", "Estados Unidos", "https://integrate.api.nvidia.com/v1", "meta/llama-3.2-11b-vision-instruct", "https://build.nvidia.com/models"),
    "openai": _provider("OpenAI", "Estados Unidos", "https://api.openai.com/v1", "gpt-4o-mini", "https://platform.openai.com/docs/models"),
    "anthropic": _provider("Anthropic / Claude", "Estados Unidos", "https://api.anthropic.com/v1", "claude-opus-5-5", "https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk"),
    "gemini": _provider("Google Gemini", "Estados Unidos", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.8-flash", "https://ai.google.dev/gemini-api/docs/openai"),
    "xai": _provider("xAI / Grok", "Estados Unidos", "https://api.x.ai/v1", "grok-4.7", "https://docs.x.ai/developers/model-capabilities/text/generate-text"),
    "together": _provider("Together AI", "Estados Unidos", "https://api.together.ai/v1", "MiniMaxAI/MiniMax-M3", "https://docs.together.ai/docs/inference/openai-compatibility"),
    "deepseek": _provider("DeepSeek", "China", "https://api.deepseek.com", "deepseek-flash", "https://api-docs.deepseek.com/"),
    "qwen": _provider("Alibaba Cloud / Qwen", "China", "https://dashscope-us.aliyuncs.com/compatible-mode/v1", "qwen-plus", "https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope", "La clave y la URL deben pertenecer a la misma región. URL inicial: Virginia; usa la URL de tu espacio para otra región."),
    "moonshot": _provider("Moonshot / Kimi", "China", "https://api.moonshot.ai/v1", "kimi-k2.6", "https://platform.moonshot.ai/docs/api/chat"),
    "zai": _provider("Z.ai / GLM", "China", "https://api.z.ai/api/paas/v4", "glm-5.3", "https://docs.z.ai/guides/overview/quick-start", "API estándar. Los planes de programación utilizan una URL diferente."),
    "ollama": _provider("Ollama", "Local", "http://localhost:11434", "llama3.2", "https://docs.ollama.com/openai"),
    "custom": _provider("API compatible personalizada", "Personalizado", "", "", "", "Introduce la URL base y un modelo con soporte de herramientas."),
}


def number_setting(name, default, minimum, maximum):
    try:
        value = float(os.getenv(name, str(default)))
        return min(maximum, max(minimum, value)) if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def provider_config(provider, api_key=None, model=None, base_url=None):
    if provider not in PROVIDERS:
        raise ValueError("Proveedor de IA no reconocido.")
    defaults = PROVIDERS[provider]
    prefix = provider.upper()
    key = (get_api_key(provider) if api_key is None else api_key).strip()
    selected_model = (os.getenv(f"{prefix}_MODEL", "") if model is None else model).strip() or defaults["model"]
    url = (os.getenv(f"{prefix}_BASE_URL", "") if base_url is None else base_url).strip() or defaults["base_url"]
    if provider == "ollama":
        key = key or "ollama"
        url = url.rstrip("/")
        if not url.endswith("/v1"):
            url += "/v1"
    if not key or "tu_clave_aqui" in key:
        raise ValueError(f"Ingresa una clave de API para {defaults['name']}.")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or "{" in url:
        raise ValueError("La URL de la API debe ser HTTP/HTTPS, sin credenciales, consultas ni marcadores pendientes.")
    return key, selected_model, url.rstrip("/")


def create_provider_client(provider, api_key=None, model=None, base_url=None, timeout=None):
    key, selected_model, url = provider_config(provider, api_key, model, base_url)
    client_class = Groq if provider == "groq" else OpenAI
    client = client_class(api_key=key, base_url=url,
                          timeout=timeout or number_setting("LLM_REQUEST_TIMEOUT", 60, 5, 600), max_retries=0)
    return client, selected_model, key


def completion_options(provider, model, temperature, max_tokens):
    """Use conservative parameters for APIs with fixed sampling or reasoning."""
    options = {"max_tokens": max_tokens}
    if provider == "openai" and model.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4")):
        return {"max_completion_tokens": max_tokens}
    if provider in {"groq", "nvidia", "openai", "ollama", "custom"}:
        options["temperature"] = temperature
    if provider == "deepseek":
        options["extra_body"] = {"thinking": {"type": "disabled"}}
    if provider == "moonshot" and model == "kimi-k2.6":
        options["extra_body"] = {"thinking": {"type": "disabled"}}
    return options

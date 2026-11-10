"""Cliente LLM con GroqCloud y soporte para Ollama/OpenAI para Linux."""

import os
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI
from src.core.providers import create_provider_client, completion_options, number_setting

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SYSTEM_PROMPT = (
    "Eres un asistente conversacional inteligente experto en Linux (especialmente Ubuntu). "
    "SIEMPRE responde en español, de forma concisa, directa y amigable. "
    "Tu objetivo es ayudar al usuario a dominar su sistema Linux: "
    "resolver dudas técnicas con claridad, sugerir comandos de terminal seguros con ejemplos prácticos, "
    "administrar paquetes (apt, snap, flatpak), gestionar procesos y servicios (systemd), "
    "configurar redes, monitorear recursos del sistema y guiar paso a paso. "
    "Cuando sugieras comandos, explica brevemente qué hace cada uno. "
    "Si el usuario comete un error en un comando, corrígelo amablemente. "
    "Advierte siempre antes de ejecutar acciones que puedan ser destructivas o irreversibles."
)

DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEFAULT_NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-pro-0813")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")


def _request_timeout() -> float:
    try:
        return max(5.0, float(os.getenv("LLM_REQUEST_TIMEOUT", "60")))
    except (TypeError, ValueError):
        return 60.0


LLM_REQUEST_TIMEOUT = _request_timeout()


class GroqClient:
    """Cliente LLM compatible con GroqCloud y NVIDIA NIM manteniendo historial conversacional."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
        self._client, self.model, self.api_key = create_provider_client(self.provider, api_key, model)
        if not self.model:
            raise ValueError("Configura el modelo en Configuración.")
        self._history: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def chat(self, user_message: str) -> str:
        """Envía un mensaje al LLM y devuelve la respuesta del asistente."""
        self._history.append({"role": "user", "content": user_message})

        completion = self._client.chat.completions.create(
            model=self.model,
            messages=self._history,
            **completion_options(self.provider, self.model, number_setting("LLM_TEMPERATURE", 0.2, 0, 1),
                                 int(number_setting("LLM_MAX_TOKENS", 1500, 256, 32768))),
        )

        reply = (completion.choices[0].message.content or "").strip()
        if not reply:
            raise RuntimeError("El modelo no devolvió ninguna respuesta.")

        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset_chat(self) -> None:
        """Reinicia el historial de conversación."""
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]


def format_llm_error(exc: Exception) -> str:
    """Formatea excepciones comunes para mostrarlas amigablemente en la interfaz."""
    message = str(exc)
    lower = message.lower()

    if "503" in message or "high demand" in lower or "overloaded" in lower or "unavailable" in lower:
        return (
            "⚠️ El modelo de IA en la nube está experimentando alta demanda temporal (Error 503).\n"
            "Intenta de nuevo en unos segundos o cambia a otro modelo/proveedor (como Gemini 2.5 Flash o Groq) en Configuración."
        )
    if "429" in message or "rate_limit_exceeded" in lower or "resource_exhausted" in lower or "quota" in lower:
        return (
            "⚠️ Límite de solicitudes alcanzado con el proveedor de IA.\n"
            "Espera unos momentos e intenta de nuevo, o selecciona otro modelo en Configuración."
        )
    if "401" in message or "invalid_api_key" in lower or "invalid api key" in lower or "api_key_invalid" in lower:
        return (
            "⚠️ Clave de API inválida.\n"
            "Revisa la clave del proveedor seleccionado en Configuración."
        )
    if "404" in message or "model_not_found" in lower or "not_found" in lower:
        return (
            "⚠️ El modelo configurado no está disponible.\n"
            "Revisa el modelo seleccionado en Configuración."
        )
    if "timeout" in lower or "timed out" in lower or "tiempo máximo" in lower:
        return (
            "⚠️ La IA tardó demasiado en responder y cancelé la espera.\n"
            "Las acciones locales siguen disponibles; intenta de nuevo si necesitas una respuesta de IA."
        )
    if "connection error" in lower or "connecterror" in lower:
        return (
            "⚠️ No pude conectar con el proveedor de IA.\n"
            "Revisa la red, la URL del proveedor y sus ajustes de conexión; si usas Ollama, verifica que esté iniciado."
        )

    return f"⚠️ Error del asistente:\n{message[:300]}"


def create_client() -> GroqClient | None:
    """Crea una instancia de GroqClient o None si la configuración es inválida."""
    try:
        return GroqClient()
    except (ValueError, Exception):
        return None

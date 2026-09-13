"""Cliente LLM con GroqCloud y soporte para Ollama/OpenAI para Linux."""

import os
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

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
        self.provider = DEFAULT_PROVIDER
        if self.provider not in {"groq", "nvidia"}:
            raise ValueError("LLM_PROVIDER debe ser 'groq' o 'nvidia'.")

        if self.provider == "nvidia":
            self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "").strip()
            placeholder = "nvapi_tu_clave_aqui"
            missing_message = "Falta NVIDIA_API_KEY. Configura tu clave en el archivo .env."
            self.model = model or DEFAULT_NVIDIA_MODEL
            self._client = OpenAI(
                base_url=NVIDIA_BASE_URL,
                api_key=self.api_key,
                timeout=LLM_REQUEST_TIMEOUT,
                max_retries=0,
            )
        else:
            self.api_key = api_key or os.getenv("GROQ_API_KEY", "").strip()
            placeholder = "gsk_tu_clave_aqui"
            missing_message = "Falta GROQ_API_KEY. Configura tu clave en el archivo .env."
            self.model = model or DEFAULT_GROQ_MODEL
            self._client = Groq(
                api_key=self.api_key,
                timeout=LLM_REQUEST_TIMEOUT,
                max_retries=0,
            )

        if not self.api_key or self.api_key == placeholder:
            raise ValueError(
                missing_message
            )
        self._history: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def chat(self, user_message: str) -> str:
        """Envía un mensaje al LLM y devuelve la respuesta del asistente."""
        self._history.append({"role": "user", "content": user_message})

        completion = self._client.chat.completions.create(
            model=self.model,
            messages=self._history,
            temperature=0.7,
            max_tokens=1024,
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

    if "429" in message or "rate_limit_exceeded" in message:
        return (
            "⚠️ Límite de solicitudes alcanzado en Groq.\n"
            "Espera unos momentos e intenta de nuevo."
        )
    if "401" in message or "invalid_api_key" in message or "Invalid API Key" in message:
        return (
            "⚠️ Clave de API inválida.\n"
            "Revisa tu GROQ_API_KEY o NVIDIA_API_KEY en el archivo .env."
        )
    if "404" in message or "model_not_found" in message:
        return (
            f"⚠️ El modelo configurado no está disponible.\n"
            f"Revisa el modelo configurado en GROQ_MODEL o NVIDIA_MODEL en tu .env."
        )
    if "Timeout" in message or "timed out" in message or "tiempo máximo" in message:
        return (
            "⚠️ La IA tardó demasiado en responder y cancelé la espera.\n"
            "Las acciones locales siguen disponibles; intenta de nuevo si necesitas una respuesta de IA."
        )
    if "Connection error" in message or "ConnectError" in message:
        return (
            "⚠️ Error de conexión a internet.\n"
            "Verifica tu conexión de red para consultar el asistente en la nube."
        )

    return f"⚠️ Error del asistente:\n{message[:300]}"


def create_client() -> GroqClient | None:
    """Crea una instancia de GroqClient o None si la configuración es inválida."""
    try:
        return GroqClient()
    except (ValueError, Exception):
        return None

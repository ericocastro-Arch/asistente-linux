"""Agente Autónomo para Linux con soporte de ejecución de herramientas (Tool Calling) y memoria persistente."""

import json
import os
import platform
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

from src.core.tools import LINUX_TOOLS, execute_tool
from src.core.memory import load_memory, clear_memory
from src.core.storage import log_message, start_session

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _clean_model_reply(reply: str) -> str:
    """Evita mostrar pseudollamadas internas que algunos modelos imprimen como texto."""
    markers = ("DSML", "tool_calls", "<|", "</|", "<function=", "<tool")
    if any(marker in reply for marker in markers):
        return (
            "Intenté preparar una acción del sistema, pero el modelo devolvió instrucciones "
            "internas en vez de ejecutarla. Prueba con una orden directa como: "
            "`abre wine` o `abre la terminal`."
        )
    return reply


def _build_system_context() -> str:
    """Genera un bloque de contexto del sistema para el agente al inicio de la sesión."""
    try:
        uname = platform.uname()
        kernel = uname.release
        arch = uname.machine
    except Exception:
        kernel, arch = "desconocido", "x86_64"

    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem_total = next((int(l.split()[1]) // 1024 for l in lines if l.startswith("MemTotal:")), 0)
        mem_avail = next((int(l.split()[1]) // 1024 for l in lines if l.startswith("MemAvailable:")), 0)
        mem_used = mem_total - mem_avail
        ram_info = f"{mem_used} MB usados / {mem_total} MB totales"
    except Exception:
        ram_info = "no disponible"

    try:
        disk = shutil.disk_usage("/")
        disk_info = f"{disk.used / 1e9:.1f} GB usados / {disk.total / 1e9:.1f} GB totales"
    except Exception:
        disk_info = "no disponible"

    try:
        distro = ""
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    distro = line.strip().split("=", 1)[1].strip('"')
                    break
    except Exception:
        distro = "Ubuntu Linux"

    home = os.path.expanduser("~")
    user = os.environ.get("USER", os.environ.get("LOGNAME", "usuario"))

    return (
        f"[CONTEXTO DEL SISTEMA — inicio de sesión]\n"
        f"• Distro: {distro}\n"
        f"• Kernel: {kernel} ({arch})\n"
        f"• RAM: {ram_info}\n"
        f"• Disco (/): {disk_info}\n"
        f"• Usuario: {user} (home: {home})\n"
    )


SYSTEM_PROMPT_TEMPLATE = """\
Eres un Agente Autónomo conversacional experto en Linux (especialmente Ubuntu), \
que asiste al usuario SIEMPRE EN ESPAÑOL.

REGLAS DE USO DE HERRAMIENTAS:
1. Cuando el usuario pida una ACCIÓN en el sistema, USA tus herramientas — no te limites a dar instrucciones de texto.
2. Para comandos rápidos de solo lectura (ls, df, free, cat, ip a, uname, etc.) → usa `run_command_silent` y muestra la salida en el chat.
3. Para comandos que requieren sudo o interacción del usuario → usa `open_terminal_command`.
4. Para actualizar el sistema → usa `update_system` (preferiblemente modo gui).
5. Para instalar programas desde lenguaje natural → usa `install_program`.
6. Para instalar paquetes .deb descargados → usa `install_deb_package`.
7. Para revisar o actualizar firmware → usa `manage_firmware`.
8. Para abrir aplicaciones gráficas → usa `open_application`.
9. Para gestionar servicios systemd → usa `manage_service`.
10. Para buscar paquetes sin instalar → usa `search_package`.
11. Para leer o crear archivos → usa `read_file` o `write_file`.
12. Para preguntas técnicas o conceptuales → responde directamente con texto claro, conciso y ejemplos prácticos.

REGLAS DE SEGURIDAD:
- Antes de ejecutar acciones destructivas (borrar archivos, formatear, desinstalar paquetes importantes), \
ADVIERTE al usuario y pide confirmación explícita.
- Nunca ejecutes comandos como rm -rf /, mkfs, dd en dispositivos críticos, o similares sin advertencia clara.
- Cuando uses `run_command_silent`, evita comandos con sudo.

ESTILO DE RESPUESTA:
- Siempre en español.
- Sé conciso, directo y amigable.
- Usa emojis moderadamente para mejorar la lectura.
- Cuando ejecutes una herramienta, explica brevemente en tu respuesta qué hiciste.
- Si el usuario comete un error en un comando, corrígelo de forma amable.

{system_context}
"""


DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEFAULT_NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-pro-0813")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")


def _timeout_setting(name: str, default: float) -> float:
    try:
        return max(5.0, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


LLM_REQUEST_TIMEOUT = _timeout_setting("LLM_REQUEST_TIMEOUT", 25.0)
LLM_TOTAL_TIMEOUT = max(
    LLM_REQUEST_TIMEOUT,
    _timeout_setting("LLM_TOTAL_TIMEOUT", 45.0),
)


class LinuxAgent:
    """Agente inteligente capaz de razonar y ejecutar acciones en Ubuntu Linux con memoria persistente."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
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

        # Construir system prompt con contexto del sistema actual
        system_context = _build_system_context()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(system_context=system_context)

        # Inicializar historial con el system prompt
        self._history: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        self.session_id = start_session("ai-agent")

        # Cargar memoria persistente (últimas sesiones)
        self._load_persistent_memory()
        self._session_history_start = len(self._history)

    def _load_persistent_memory(self) -> None:
        """Carga el historial de sesiones anteriores en el contexto del agente."""
        past = load_memory()
        if past:
            # Insertar separador para distinguir conversación anterior de la actual
            self._history.append({
                "role": "assistant",
                "content": "[Memoria de sesiones anteriores cargada — contexto previo disponible]"
            })
            self._history.extend(past[-40:])  # máximo 40 mensajes anteriores

    def chat(self, user_message: str) -> str:
        """Procesa el mensaje del usuario, ejecutando herramientas si el LLM lo decide."""
        history_start = len(self._history)
        self._history.append({"role": "user", "content": user_message})
        log_message("user", user_message, self.session_id)

        deadline = time.monotonic() + LLM_TOTAL_TIMEOUT

        def remaining_timeout() -> float:
            remaining = deadline - time.monotonic()
            if remaining <= 1:
                raise TimeoutError(
                    f"La IA superó el tiempo máximo de espera ({LLM_TOTAL_TIMEOUT:.0f} segundos)."
                )
            return min(LLM_REQUEST_TIMEOUT, remaining)

        max_tool_steps = 5
        current_step = 0
        executed_actions = []

        try:
            while current_step < max_tool_steps:
                current_step += 1

                request_args = {
                    "model": self.model,
                    "messages": self._history,
                    "temperature": 0.5,
                    "max_tokens": 1500,
                    "timeout": remaining_timeout(),
                }
                request_args.update({
                    "tools": LINUX_TOOLS,
                    "tool_choice": "auto",
                })
                response = self._client.chat.completions.create(**request_args)

                response_message = response.choices[0].message
                tool_calls = getattr(response_message, "tool_calls", None)

                # Si el modelo no pide más herramientas, tenemos la respuesta final
                if not tool_calls:
                    reply = _clean_model_reply((response_message.content or "").strip())
                    if not reply and executed_actions:
                        reply = "\n".join(executed_actions)
                    self._history.append({"role": "assistant", "content": reply})
                    # Guardar en memoria persistente tras cada respuesta
                    log_message("assistant", reply, self.session_id)
                    return reply

                # Guardar la llamada a la herramienta del asistente en el historial
                self._history.append({
                    "role": "assistant",
                    "content": response_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                })

                # Ejecutar cada herramienta solicitada
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except Exception:
                        args = {}

                    tool_result = execute_tool(function_name, args)
                    executed_actions.append(tool_result)

                    self._history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": str(tool_result),
                    })

            # Si agotó los pasos, devolver resumen de acciones
            final_reply = "\n".join(executed_actions) if executed_actions else "Acción completada."
            self._history.append({"role": "assistant", "content": final_reply})
            log_message("assistant", final_reply, self.session_id)
            return final_reply

        except Exception as exc:
            # Fallback seguro: si el LLM falló al formatear JSON de herramientas, intentar respuesta en texto plano
            try:
                fallback_timeout = remaining_timeout()
                fallback_history = [m for m in self._history if m.get("role") in ("system", "user")]
                fallback_response = self._client.chat.completions.create(
                    model=self.model,
                    messages=fallback_history,
                    temperature=0.6,
                    max_tokens=1500,
                    timeout=fallback_timeout,
                )
                fallback_reply = _clean_model_reply(
                    (fallback_response.choices[0].message.content or "").strip()
                )
                if executed_actions:
                    fallback_reply = "\n".join(executed_actions) + "\n\n" + fallback_reply
                if not fallback_reply:
                    raise RuntimeError("La IA no devolvió una respuesta válida.")
                self._history.append({"role": "assistant", "content": fallback_reply})
                log_message("assistant", fallback_reply, self.session_id)
                return fallback_reply
            except Exception as fallback_exc:
                if executed_actions:
                    final_reply = "\n".join(executed_actions)
                    self._history.append({"role": "assistant", "content": final_reply})
                    log_message("assistant", final_reply, self.session_id)
                    return final_reply
                del self._history[history_start:]
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"La IA superó el tiempo máximo de espera ({LLM_TOTAL_TIMEOUT:.0f} segundos)."
                    ) from fallback_exc
                raise exc

    def reset_chat(self, clear_persistent: bool = False) -> None:
        """Reinicia el historial de conversación. Opcionalmente borra la memoria persistente."""
        system_context = _build_system_context()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(system_context=system_context)
        self._history = [{"role": "system", "content": system_prompt}]
        if clear_persistent:
            clear_memory()

    @property
    def model_name(self) -> str:
        """Devuelve el nombre del modelo activo."""
        return f"{self.provider}: {self.model}"


def create_agent() -> Optional[LinuxAgent]:
    """Crea una instancia de LinuxAgent o None si no hay configuración válida."""
    try:
        return LinuxAgent()
    except (ValueError, Exception):
        return None

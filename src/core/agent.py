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
from src.core.backups import list_changes
from src.core.memory import load_memory, clear_memory
from src.core.storage import log_message, log_tool_run, start_session
from src.core.providers import create_provider_client, completion_options, number_setting

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


import re
import unicodedata

_INTERNAL_MARKERS = ("DSML", "tool_calls", "<|", "</|", "<function=", "<tool")


def _has_internal_tool_markers(reply: str) -> bool:
    return any(marker in reply for marker in _INTERNAL_MARKERS)


def _clean_model_reply(reply: str) -> str:
    """Evita mostrar pseudollamadas internas que algunos modelos imprimen como texto."""
    if _has_internal_tool_markers(reply):
        return (
            "Intenté preparar una acción del sistema, pero el modelo devolvió instrucciones "
            "internas en vez de ejecutarla. Prueba con una orden directa como: "
            "`abre wine` o `abre la terminal`."
        )
    return reply


def _fold_ascii(text: str) -> str:
    folded = unicodedata.normalize("NFKD", (text or "").casefold())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _claims_fictional_execution(reply: str) -> bool:
    """Detecta si una respuesta en texto plano afirma falsamente haber abierto terminal o ejecutado un cambio."""
    folded = _fold_ascii(reply)
    patterns = (
        r"\b(?:se abrio|abri|he abierto)\b.*\b(?:terminal|consola|instalador|actualizador)\b",
        r"\b(?:listo|exito)\b[,:\s]+(?:se abrio|abri|instale|desinstale|elimine|actualice|guarde|cree)\b",
        r"\b(?:instalacion|desinstalacion)\s+(?:iniciada|completada|realizada)\b",
        r"\b(?:he instalado|ya instale|he desinstalado|ya desinstale|archivo guardado|cambios aplicados)\b",
    )
    return any(re.search(pat, folded) for pat in patterns)


def _requires_mutating_or_action_tool(
    user_message: str,
    pending_at_start: Any = None,
    pending_action_at_start: Any = None,
) -> bool:
    """Indica si el mensaje del usuario exige invocar una herramienta de acción o confirmación."""
    if pending_at_start is not None or pending_action_at_start is not None:
        return True
    folded = re.sub(r"[^a-z0-9]+", " ", _fold_ascii(user_message)).strip()
    if not folded:
        return False
    # Si es una pregunta explicativa, reporte de problema/error o acción negada, puede responderse conversacionalmente
    if re.search(
        r"\b(?:como|que es|que pasa|por que|para que|cual es|cuando|explica|explicame|ensename|diferencia|significa|sirve|problema|problemas|error|errores|falla|fallo|no puedo|no me deja|no funciona|ayuda|duda)\b",
        folded,
    ):
        return False
    if re.search(r"\b(?:no|nunca)\s+(?:abras|instales|desinstales|borres|actualices|ejecutes)\b", folded):
        return False
    action_patterns = (
        r"\b(?:instala|instalar|instalame|instalarme|intala|intalar|instaalr)\b",
        r"\b(?:desinstala|desinstalar|desinstalame|desintala|desintalar)\b",
        r"\b(?:actualiza|actualizar|actualisa|actualisar)\b",
        r"\b(?:abre|abrir|abreme|habre)\b",
        r"\b(?:crea|escribe|guarda)\b.*\b(?:archivo|nota|fichero|\.txt|\.sh|\.py|\.md)\b",
        r"\b(?:deshaz|revertir|deshacer)\b",
        r"\b(?:reinicia|deten|inicia)\s+(?:el\s+)?servicio\b",
    )
    return any(re.search(pat, folded) for pat in action_patterns)


def _is_unsolicited_system_action(function_name: str, user_message: str) -> bool:
    """Detecta si el modelo intenta ejecutar una herramienta de actualización/tienda/firmware no pedida por el mensaje actual."""
    folded = re.sub(r"[^a-z0-9]+", " ", _fold_ascii(user_message)).strip()
    if function_name == "update_system":
        return not bool(re.search(r"\b(?:actualiz\w*|actualis\w*|update|upgrade|parche\w*)\b", folded))
    if function_name == "open_software_center":
        return not bool(re.search(r"\b(?:tienda|software|centro|catalogo|aplicaciones|programas|instala\w*|desinstala\w*)\b", folded))
    if function_name == "manage_firmware":
        return not bool(re.search(r"\b(?:firmware|bios|uefi|fwupd)\b", folded))
    return False


GLOBAL_SYSTEM_PROMPT = """\
Eres LinuxMate AI en modo **Chat Global** (conversación general libre), SIEMPRE EN ESPAÑOL.
Tu objetivo es responder cualquier pregunta de cultura general, historia, ciencia, deportes, programación, matemáticas, redacción, idiomas o tecnología con precisión, claridad y amabilidad.
En este modo conversacional:
- No ejecutas herramientas del sistema ni modificas paquetes, archivos o configuraciones del equipo.
- Responde de forma directa, natural y bien estructurada.
"""


def _is_retriable_provider_error(exc: Exception) -> bool:
    """Identifica errores de sobrecarga (503), cuota (429), modelo no encontrado (404) o red."""
    msg = str(exc).lower()
    tokens = (
        "503", "429", "404", "500", "502", "504",
        "unavailable", "high demand", "overloaded", "resource_exhausted",
        "rate_limit", "quota", "model_not_found", "not_found", "does not exist",
        "decommissioned", "connection error", "connecterror", "timed out",
    )
    return any(tok in msg for tok in tokens)


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
        from src.core.distro import detect_distro, get_active_package_manager
        distro_info = detect_distro()
        distro = distro_info.pretty_name
        family_str = f" (familia {distro_info.family.value})"
        active_pm = get_active_package_manager()
        pkg_summary = f"• Gestor de paquetes primario: {distro_info.native_package_manager} (activo: {active_pm})\n"
        if distro_info.available_package_managers:
            pkg_summary += f"• Gestores disponibles en el sistema: {', '.join(distro_info.available_package_managers)}\n"
    except Exception:
        distro = "Ubuntu Linux"
        family_str = ""
        pkg_summary = "• Gestor de paquetes primario: apt\n"

    home = os.path.expanduser("~")
    user = os.environ.get("USER", os.environ.get("LOGNAME", "usuario"))

    return (
        f"[CONTEXTO DEL SISTEMA — inicio de sesión]\n"
        f"• Distro: {distro}{family_str}\n"
        f"{pkg_summary}"
        f"• Kernel: {kernel} ({arch})\n"
        f"• RAM: {ram_info}\n"
        f"• Disco (/): {disk_info}\n"
        f"• Usuario: {user} (home: {home})\n"
    )


SYSTEM_PROMPT_TEMPLATE = """\
Eres LinuxMate AI, un asistente que combina dos roles esenciales SIEMPRE EN ESPAÑOL:
1. **Chatbot conversacional experto y amigable**: Respondes cualquier pregunta, duda o conversación del usuario (sobre Ubuntu/Linux, hardware, software, comandos, errores, recomendaciones de programas o uso general del equipo) con explicaciones claras, pacientes y fáciles de entender para principiantes.
2. **Agente del sistema Ubuntu con acceso controlado y seguro**: Tienes acceso directo de lectura y diagnóstico a este equipo Linux, y acceso con confirmación a tareas administrativas para ayudar al usuario a detectar su hardware, diagnosticar fallos y resolver problemas reales.

Interpreta las solicitudes en lenguaje natural y atiende todos sus objetivos, aunque no usen nombres de comandos. Si falta información esencial, pregunta. Diagnostica antes de proponer una reparación; si una acción no está disponible o se bloquea, explica la razón y ofrece pasos concretos que el usuario pueda revisar. No afirmes haber hecho cambios sin el resultado de una herramienta. Nunca solicites ni aceptes contraseñas en el chat: la autenticación corresponde al diálogo del sistema o a sudo interactivo.

REGLAS DE USO DE HERRAMIENTAS:
1. Cuando el usuario pida una ACCIÓN en el sistema o pregunte por el estado/hardware/software de su propio equipo, USA tus herramientas — no adivines datos que puedes consultar en vivo.
2. Para inspeccionar el hardware, software o salud del equipo (CPU, RAM, discos, particiones, tarjeta gráfica/drivers PCI, dispositivos USB, sonido/audio, batería, Bluetooth, pantallas, red, procesos, servicios fallidos, errores recientes del sistema, temperaturas o actualizaciones) → USA `run_diagnostic` eligiendo el diagnóstico adecuado del catálogo (puedes llamar varios en un mismo turno). Si ninguna opción del catálogo cubre una consulta de solo lectura → usa `run_command_silent`.
3. Tras ejecutar herramientas de diagnóstico o lectura (`run_diagnostic`, `get_system_status`, `run_command_silent`, `read_file`, `search_package`), analiza los datos reales obtenidos y explícalos al usuario en lenguaje claro y útil (usando `respond_to_user` o tu respuesta directa).
4. Para comandos que requieren sudo o interacción del usuario → usa `open_terminal_command`.
5. Para actualizar el sistema → usa `update_system` (preferiblemente modo gui).
6. Para instalar programas desde lenguaje natural → usa `install_program`.
7. Para instalar paquetes .deb descargados → usa `install_deb_package`.
8. Para revisar o actualizar firmware → usa `manage_firmware`.
9. Para abrir aplicaciones gráficas → usa `open_application`.
10. Para gestionar servicios systemd → usa `manage_service`.
11. Para buscar paquetes sin instalar → usa `search_package`.
12. Para leer o crear archivos → usa `read_file` o `write_file` (solo se escribe dentro de la carpeta personal; cada cambio se respalda). Si el usuario pide deshacer o revertir el último cambio de un archivo → usa `undo_last_change`.
13. Para desinstalar aplicaciones o paquetes → usa `remove_package` para PREPARAR la solicitud. La aplicación pedirá confirmación automáticamente. Usa `source="auto"` si el usuario no dijo apt/snap/flatpak/desktop. Si no se encuentra el paquete, el sistema abrirá el Centro de Software (sección Gestionar) como alternativa. Nunca inventes cadenas con `which`, `dpkg`, `snap list`, `flatpak list` y tuberías si la intención final es quitar una app.
14. Para responder conversación general, preguntas conceptuales, saludos, explicar un resultado o pedir una aclaración → usa `respond_to_user` con un mensaje claro y amable.
15. Para instalar llama a `install_program`. Si hay una desinstalación pendiente y el usuario la confirma, llama a `confirm_package_removal` con `confirmed=true`; si la cancela, usa `confirmed=false`. Para escribir un archivo, instalar o cambiar un servicio, LinuxMate mostrará primero un plan y pedirá confirmación; nunca llames a `confirm_pending_action` en el mismo turno que propone la acción. Escribir que se abrió una terminal no la abre.

REGLAS DE SEGURIDAD:
- Antes de ejecutar acciones destructivas (borrar archivos, formatear, desinstalar paquetes importantes), \
ADVIERTE al usuario y pide confirmación explícita.
- Desinstalar una aplicación normal (por ejemplo vlc, zed, waydroid u office365WebDesktop) NO es daño al sistema operativo. Trátalo como una acción administrativa permitida con confirmación. Algunas apps como Zed o accesos web pueden ser lanzadores locales de usuario, no paquetes Snap.
- La herramienta remove_package solo prepara y pide confirmación: úsala en vez de redactar tu propia pregunta. No llames a confirm_package_removal hasta recibir una respuesta posterior del usuario que confirme la solicitud pendiente.
- Antes de escribir un archivo o modificar un servicio, prepara la herramienta correspondiente para que LinuxMate muestre el plan. Solo confirma después de un mensaje posterior que acepte claramente ese plan.
- Interpreta la confirmación en su contexto. Nunca confirmes si el usuario rechaza, pregunta, cambia de aplicación o pide otra tarea. Bloquea componentes críticos del sistema como systemd, kernel/linux-image, apt, dpkg, sudo, ubuntu-desktop o network-manager.
- Nunca ejecutes comandos como rm -rf /, mkfs, dd en dispositivos críticos, o similares sin advertencia clara.
- Cuando uses `run_command_silent`, evita comandos con sudo.

ESTILO DE RESPUESTA:
- Siempre en español.
- Sé conversacional, claro, empático y útil, tanto si el usuario saluda o hace una pregunta sencilla como si reporta un problema técnico complejo de hardware o software.
- Usa emojis moderadamente para mejorar la lectura.
- Cuando ejecutes una herramienta, explica brevemente en tu respuesta qué hiciste y qué significan los resultados para el usuario.
- Después de usar una herramienta, respeta su salida real. No digas que se abrió una terminal si la herramienta no lo informó.
- La memoria de sesiones anteriores solo aporta contexto; sus afirmaciones de éxito no prueban ejecuciones actuales. No copies esos mensajes para responder a una nueva acción.
- Si el usuario comete un error en un comando o tiene dudas de principiante, oriéntalo de forma amable paso a paso.

{system_context}
"""


DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEFAULT_NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")


def _timeout_setting(name: str, default: float) -> float:
    try:
        return max(5.0, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


LLM_REQUEST_TIMEOUT = _timeout_setting("LLM_REQUEST_TIMEOUT", 60.0)
LLM_TOTAL_TIMEOUT = max(
    LLM_REQUEST_TIMEOUT,
    _timeout_setting("LLM_TOTAL_TIMEOUT", 90.0),
)


REPLY_TOOL = {
    "type": "function",
    "function": {
        "name": "respond_to_user",
        "description": (
            "Responde preguntas o solicita una aclaracion/confirmacion. No ejecuta nada. "
            "No usar para anunciar instalaciones, desinstalaciones o terminales abiertas: "
            "para esas solicitudes usa la herramienta real correspondiente."
        ),
        "parameters": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
}

CONFIRM_REMOVAL_TOOL = {
    "type": "function",
    "function": {
        "name": "confirm_package_removal",
        "description": (
            "Resuelve la desinstalacion pendiente tras una respuesta posterior del usuario. "
            "confirmed=true solo si su mensaje actual acepta claramente quitar esa aplicacion; "
            "false si cancela. No usar si pregunta, cambia de aplicacion o pide otra accion."
        ),
        "parameters": {
            "type": "object",
            "properties": {"confirmed": {"type": "boolean"}},
            "required": ["confirmed"],
        },
    },
}

CONFIRM_ACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "confirm_pending_action",
        "description": (
            "Confirma o cancela una escritura de archivo o cambio de servicio que LinuxMate ya mostró. "
            "Solo confirma si el mensaje actual del usuario acepta claramente ese plan."
        ),
        "parameters": {
            "type": "object",
            "properties": {"confirmed": {"type": "boolean"}},
            "required": ["confirmed"],
        },
    },
}

ACTION_RESULT_TOOLS = {
    "install_program", "remove_package", "confirm_package_removal", "confirm_pending_action", "install_deb_package", "open_terminal_command",
    "update_system", "manage_firmware", "manage_service", "open_application",
    "open_software_center", "write_file", "undo_last_change",
}

PROVIDER_FALLBACK_MODELS: Dict[str, List[str]] = {
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
    "openai": ["gpt-4.1-mini", "gpt-4o-mini"],
    "nvidia": ["meta/llama-3.2-11b-vision-instruct"],
    "anthropic": ["claude-sonnet-4-5"],
}


class LinuxAgent:
    """Agente inteligente capaz de razonar y ejecutar acciones en Ubuntu Linux con memoria persistente."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.provider = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
        self.temperature = number_setting("LLM_TEMPERATURE", 0.2, 0, 1)
        self.request_timeout = number_setting("LLM_REQUEST_TIMEOUT", 60, 5, 600)
        self.max_tokens = int(number_setting("LLM_MAX_TOKENS", 1500, 256, 32768))
        self._client, self.model, self.api_key = create_provider_client(self.provider, api_key, model)
        if not self.model:
            raise ValueError("Configura el identificador del modelo en Configuración.")

        # Construir system prompt con contexto del sistema actual
        system_context = _build_system_context()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(system_context=system_context)
        style = os.getenv("SYSTEM_MODE", "didactic")
        system_prompt += {"didactic": "\nExplica los pasos con ejemplos sencillos para principiantes.",
                          "sysadmin": "\nResponde de forma técnica y directa, con comandos precisos y su efecto.",
                          "devops": "\nPrioriza automatización reproducible, scripts y diagnóstico de servicios."}.get(style, "")

        # Inicializar historial con el system prompt
        self._history: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]
        self._pending_removal: Optional[Dict[str, str]] = None
        self._pending_action: Optional[Dict[str, Any]] = None

        self.session_id = start_session("ai-agent")

        # Cargar memoria persistente (últimas sesiones)
        self._load_persistent_memory()
        self._session_history_start = len(self._history)

    def _load_persistent_memory(self) -> None:
        """Carga el historial de sesiones anteriores en el contexto del agente, ignorando mensajes huérfanos."""
        past = load_memory()
        if not past:
            return
        paired: List[Dict[str, Any]] = []
        i = 0
        while i < len(past):
            msg = past[i]
            if msg.get("role") == "user":
                if i + 1 < len(past) and past[i + 1].get("role") == "assistant":
                    paired.append(msg)
                    paired.append(past[i + 1])
                    i += 2
                    continue
                i += 1
            else:
                i += 1
        if paired:
            # Insertar separador para distinguir conversación anterior de la actual
            self._history.append({
                "role": "assistant",
                "content": "[Memoria de sesiones anteriores cargada — contexto previo disponible]"
            })
            self._history.extend(paired[-10:])  # máximo 10 mensajes anteriores para respetar límites de cuota/tokens

    def _call_llm_with_fallback(
        self,
        messages: List[Dict[str, Any]],
        available_tools: Optional[List[Dict[str, Any]]],
        remaining_timeout_fn,
    ):
        """Invoca al proveedor actual y, ante errores 503/429/404, intenta modelos/proveedores de respaldo."""
        provider = getattr(self, "provider", "groq")
        model = getattr(self, "model", DEFAULT_GROQ_MODEL)
        temperature = getattr(self, "temperature", 0.2)
        max_tokens = getattr(self, "max_tokens", 1500)
        tool_choice = "required" if provider in {"groq", "nvidia", "openai", "ollama"} else "auto"

        """Invoca al proveedor actual y, ante errores 503/429/404, intenta modelos/proveedores de respaldo."""
        provider = getattr(self, "provider", "groq")
        model = getattr(self, "model", DEFAULT_GROQ_MODEL)
        temperature = getattr(self, "temperature", 0.2)
        max_tokens = getattr(self, "max_tokens", 1500)
        tool_choice = "required" if provider in {"groq", "nvidia", "openai", "ollama"} else "auto"

        request_args: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            **completion_options(provider, model, temperature, max_tokens),
            "timeout": remaining_timeout_fn(),
        }
        if available_tools:
            request_args["tools"] = available_tools
            request_args["tool_choice"] = tool_choice
        try:
            return self._client.chat.completions.create(**request_args)
        except Exception as first_exc:
            if not _is_retriable_provider_error(first_exc):
                raise

            last_exc: Exception = first_exc
            # 1) Probar modelos alternativos del mismo proveedor
            for alt_model in PROVIDER_FALLBACK_MODELS.get(provider, []):
                if alt_model == model:
                    continue
                alt_args: Dict[str, Any] = {
                    "model": alt_model,
                    "messages": messages,
                    **completion_options(provider, alt_model, temperature, max_tokens),
                    "timeout": remaining_timeout_fn(),
                }
                if available_tools:
                    alt_args["tools"] = available_tools
                    alt_args["tool_choice"] = tool_choice
                try:
                    response = self._client.chat.completions.create(**alt_args)
                    self.model = alt_model
                    return response
                except Exception as alt_exc:
                    last_exc = alt_exc
                    if not _is_retriable_provider_error(alt_exc):
                        break

            # 2) Probar otros proveedores configurados (solo con clientes reales o fábrica inyectada)
            client_factory = getattr(self, "_fallback_client_factory", None)
            if client_factory is None and isinstance(getattr(self, "_client", None), (OpenAI, Groq)):
                client_factory = create_provider_client

            if callable(client_factory):
                for alt_provider in ("groq", "gemini", "openai", "nvidia", "anthropic", "ollama"):
                    if alt_provider == provider:
                        continue
                    try:
                        alt_client, alt_model, _ = client_factory(alt_provider, None, None)
                    except Exception:
                        continue
                    if not alt_model:
                        continue
                    alt_tool_choice = "required" if alt_provider in {"groq", "nvidia", "openai", "ollama"} else "auto"
                    alt_args = {
                        "model": alt_model,
                        "messages": messages,
                        **completion_options(alt_provider, alt_model, temperature, max_tokens),
                        "timeout": remaining_timeout_fn(),
                    }
                    if available_tools:
                        alt_args["tools"] = available_tools
                        alt_args["tool_choice"] = alt_tool_choice
                    try:
                        response = alt_client.chat.completions.create(**alt_args)
                        self._client = alt_client
                        self.provider = alt_provider
                        self.model = alt_model
                        return response
                    except Exception as alt_exc:
                        last_exc = alt_exc
                        continue

            # El error de un respaldo (por ejemplo Ollama detenido) no describe
            # necesariamente el fallo del proveedor seleccionado por el usuario.
            raise first_exc

    def _try_local_pending_resolution(
        self,
        user_message: str,
        pending_at_start: Optional[Dict[str, str]],
        pending_action_at_start: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Resuelve confirmaciones pendientes ('sí'/'no') localmente si el proveedor de IA está caído."""
        if not pending_at_start and not pending_action_at_start:
            return None
        folded = re.sub(r"[^a-z0-9]+", " ", _fold_ascii(user_message)).strip()
        yes_words = {"si", "s", "confirmo", "confirmar", "adelante", "ok", "dale", "hazlo", "acepto", "continuar", "continua"}
        no_words = {"no", "n", "mejor no", "cancelar", "cancela", "abortar", "detener", "negativo"}
        if folded in yes_words:
            confirmed = True
        elif folded in no_words:
            confirmed = False
        else:
            return None

        if pending_action_at_start and getattr(self, "_pending_action", None) is pending_action_at_start:
            self._pending_action = None
            if confirmed:
                pending_arguments = dict(pending_action_at_start["arguments"])
                if pending_action_at_start.get("prepared_install_plan"):
                    pending_arguments["_prepared_install_plan"] = pending_action_at_start["prepared_install_plan"]
                return str(execute_tool(pending_action_at_start["tool_name"], pending_arguments))
            tool_result = "Acción cancelada; no se modificó el sistema."
            log_tool_run(
                "confirmation",
                pending_action_at_start["tool_name"],
                tool_result,
                status="cancelled",
                session_id=self.session_id,
            )
            return tool_result

        if pending_at_start and getattr(self, "_pending_removal", None) is pending_at_start:
            self._pending_removal = None
            if confirmed:
                return str(execute_tool("remove_package", pending_at_start))
            return "Desinstalacion cancelada."

        return None

    def chat(self, user_message: str) -> str:
        """Procesa el mensaje del usuario, ejecutando herramientas si el LLM lo decide."""
        history_start = len(self._history)
        self._history.append({"role": "user", "content": user_message})

        deadline = time.monotonic() + max(LLM_TOTAL_TIMEOUT, getattr(self, "request_timeout", LLM_REQUEST_TIMEOUT))

        def remaining_timeout() -> float:
            remaining = deadline - time.monotonic()
            if remaining <= 1:
                raise TimeoutError(
                    f"La IA superó el tiempo máximo de espera ({LLM_TOTAL_TIMEOUT:.0f} segundos)."
                )
            return min(getattr(self, "request_timeout", LLM_REQUEST_TIMEOUT), remaining)

        max_tool_steps = 5
        current_step = 0
        executed_actions = []
        retry_needed = False
        pending_at_start = getattr(self, "_pending_removal", None)
        pending_action_at_start = getattr(self, "_pending_action", None)

        def finish(reply: str) -> str:
            self._history.append({"role": "assistant", "content": reply})
            log_message("user", user_message, self.session_id)
            log_message("assistant", reply, self.session_id)
            return reply

        try:
            while current_step < max_tool_steps:
                current_step += 1
                messages = list(self._history)
                available_tools = [*LINUX_TOOLS, REPLY_TOOL]
                if pending_at_start:
                    available_tools.append(CONFIRM_REMOVAL_TOOL)
                    messages.append({
                        "role": "system",
                        "content": (
                            "Desinstalacion pendiente de confirmacion: "
                            + json.dumps(pending_at_start, ensure_ascii=False)
                            + ". Interpreta el mensaje actual del usuario para confirmar, cancelar "
                            "o atender otra solicitud. Usa confirm_package_removal si confirma o cancela."
                        ),
                    })
                if pending_action_at_start:
                    available_tools.append(CONFIRM_ACTION_TOOL)
                    messages.append({
                        "role": "system",
                        "content": (
                            "Hay una acción pendiente que LinuxMate ya mostró al usuario: "
                            + json.dumps(pending_action_at_start, ensure_ascii=False)
                            + ". Usa confirm_pending_action solo si el mensaje actual confirma claramente "
                            "ese plan; cancélalo si el usuario dice que no. Si pregunta o cambia de tema, "
                            "no ejecutes la acción pendiente."
                        ),
                    })
                if retry_needed:
                    messages.append({
                        "role": "system",
                        "content": (
                            "La respuesta anterior no produjo una llamada valida. Usa las herramientas: "
                            "install_program para instalar, remove_package para desinstalar tras "
                            "confirmacion, respond_to_user para preguntas o pedir confirmacion. "
                            "No afirmes que ejecutaste acciones escribiendo solo texto."
                        ),
                    })
                try:
                    response = self._call_llm_with_fallback(messages, available_tools, remaining_timeout)
                except Exception as call_exc:
                    if retry_needed or _is_retriable_provider_error(call_exc):
                        raise
                    retry_needed = True
                    continue

                response_message = response.choices[0].message
                tool_calls = getattr(response_message, "tool_calls", None)

                # Aceptar respuesta conversacional en texto plano solo si NO finge ejecución
                # y no se trata de una orden de acción/confirmación sin ejecutar.
                if not tool_calls:
                    raw_content = getattr(response_message, "content", None) or ""
                    cleaned_content = _clean_model_reply(raw_content.strip()) if isinstance(raw_content, str) else ""
                    if (
                        cleaned_content
                        and not _has_internal_tool_markers(raw_content)
                        and not _claims_fictional_execution(raw_content)
                        and (
                            executed_actions
                            or not _requires_mutating_or_action_tool(
                                user_message,
                                pending_at_start=pending_at_start,
                                pending_action_at_start=pending_action_at_start,
                            )
                        )):
                        return finish(cleaned_content)
                    if retry_needed:
                        raise RuntimeError(
                            "La IA no genero una llamada de herramienta valida. No se ejecuto una nueva accion."
                        )
                    retry_needed = True
                    continue
                retry_needed = False

                # Guardar la llamada a la herramienta del asistente en el historial
                assistant_message = {
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
                }
                # Preserve reasoning and tool signatures required by compatible APIs.
                if hasattr(response_message, "model_dump"):
                    assistant_message = response_message.model_dump(exclude_none=True)
                self._history.append(assistant_message)

                direct_result = False
                conversational_reply = ""
                # Responder a todas las llamadas antes de cerrar el turno conserva un historial valido.
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                        if not isinstance(args, dict):
                            raise ValueError("Se esperaba un objeto de argumentos.")
                    except (ValueError, TypeError):
                        tool_result = "Argumentos invalidos. La herramienta no se ejecuto; corrige la llamada."
                    else:
                        if function_name == "respond_to_user":
                            message = args.get("message")
                            conversational_reply = _clean_model_reply(message.strip()) if isinstance(message, str) else ""
                            tool_result = "Respuesta preparada." if conversational_reply else "Falta el mensaje de respuesta."
                        else:
                            if (
                                pending_action_at_start
                                and function_name != "confirm_pending_action"
                                and getattr(self, "_pending_action", None) is pending_action_at_start
                            ):
                                self._pending_action = None
                                log_tool_run(
                                    "confirmation", pending_action_at_start["tool_name"],
                                    "Plan cancelado porque el usuario inició otra acción.",
                                    status="superseded", session_id=self.session_id,
                                        )
                            if function_name == "confirm_pending_action":
                                pending = getattr(self, "_pending_action", None)
                                if pending_action_at_start is None or pending is not pending_action_at_start:
                                    tool_result = "No hay una acción anterior pendiente de confirmación."
                                elif not isinstance(args.get("confirmed"), bool):
                                    tool_result = "Falta indicar si confirmas o cancelas la acción pendiente."
                                else:
                                    self._pending_action = None
                                    if args["confirmed"]:
                                        pending_arguments = dict(pending["arguments"])
                                        if pending.get("prepared_install_plan"):
                                            pending_arguments["_prepared_install_plan"] = pending["prepared_install_plan"]
                                        tool_result = execute_tool(pending["tool_name"], pending_arguments)
                                    else:
                                        tool_result = "Acción cancelada; no se modificó el sistema."
                                        log_tool_run(
                                            "confirmation", pending["tool_name"], tool_result,
                                            status="cancelled", session_id=self.session_id,
                                        )
                            elif function_name == "install_program":
                                if getattr(self, "_pending_removal", None):
                                    self._pending_removal = None
                                decision = None
                                try:
                                    from src.core.policy import authorize_tool
                                    decision = authorize_tool(function_name, args)
                                except Exception:
                                    decision = None
                                if decision is not None and decision.is_blocked:
                                    tool_result = f"⛔ {decision.message}"
                                else:
                                    from src.core.tools import prepare_install_program
                                    plan = prepare_install_program(
                                        args.get("program_name", ""),
                                        args.get("preferred_source", "auto"),
                                    )
                                    if isinstance(plan, str):
                                        tool_result = plan
                                    else:
                                        self._pending_action = {
                                            "tool_name": function_name,
                                            "arguments": args,
                                            "prepared_install_plan": plan,
                                        }
                                        tool_result = (
                                            "Vista previa de instalación:\n"
                                            f"Aplicación: {plan['friendly_name']}\n"
                                            f"Paquete: {plan['package']}\n"
                                            f"Origen: {plan['source']}\n"
                                            f"Comando exacto: `{plan['command']}`\n"
                                            "Tamaño y dependencias: los mostrará el gestor de paquetes al confirmar.\n"
                                            "¿Confirmas que continúe?"
                                        )
                                        log_tool_run(
                                            "pending_confirmation", function_name,
                                            json.dumps({"package": plan["package"], "source": plan["source"]}, ensure_ascii=False),
                                            status="pending_confirmation", session_id=self.session_id,
                                        )
                            elif function_name == "remove_package":
                                package = args.get("package_name")
                                if not isinstance(package, str) or not package.strip():
                                    tool_result = "Indica que aplicacion quieres desinstalar."
                                else:
                                    self._pending_removal = {
                                        "package_name": package.strip(),
                                        "source": args.get("source", "auto"),
                                    }
                                    tool_result = f"¿Confirmas que quieres desinstalar '{package.strip()}'?"
                            elif function_name == "write_file" and (
                                not isinstance(args.get("file_path"), str)
                                or not isinstance(args.get("content"), str)
                            ):
                                tool_result = execute_tool(function_name, args)
                            elif function_name in {"write_file", "manage_service", "undo_last_change"} and (
                                function_name != "manage_service" or args.get("action") != "status"
                            ):
                                self._pending_action = {
                                    "tool_name": function_name,
                                    "arguments": args,
                                }
                                if function_name == "write_file":
                                    path = str(Path(args.get("file_path", "")).expanduser().resolve())
                                    exists = Path(path).is_file()
                                    description = (
                                        f"{ 'Sobrescribir' if exists else 'Crear' } el archivo {path}. "
                                        f"Contenido nuevo: {len(str(args.get('content', '')))} caracteres."
                                    )
                                    if exists:
                                        description += " Se guardará una copia privada antes de reemplazarlo."
                                elif function_name == "undo_last_change":
                                    last = next(
                                        (c for c in list_changes(limit=10_000) if c.get("status") == "applied"),
                                        None,
                                    )
                                    if last is None:
                                        self._pending_action = None
                                        tool_result = "No hay cambios del asistente que se puedan deshacer."
                                        description = ""
                                    else:
                                        what = "restaurar su versión anterior" if last.get("backup") else "eliminarlo (lo creó el asistente)"
                                        description = f"Deshacer el cambio del {last.get('at', '?')} en {last['path']}: {what}."
                                else:
                                    description = (
                                        f"Ejecutar `systemctl {args.get('action', '')} "
                                        f"{args.get('service_name', '')}` con autenticación del sistema."
                                    )
                                if self._pending_action is not None:
                                    tool_result = f"Plan de acción: {description}\n¿Confirmas que continúe?"
                                audit_arguments = args
                                if function_name == "write_file":
                                    audit_arguments = {
                                        "file_path": args.get("file_path", ""),
                                        "content_length": len(str(args.get("content", ""))),
                                    }
                                if self._pending_action is not None:
                                    log_tool_run(
                                        "pending_confirmation", function_name,
                                        json.dumps(audit_arguments, ensure_ascii=False),
                                        status="pending_confirmation", session_id=self.session_id,
                                    )
                            elif function_name == "confirm_package_removal":
                                pending = getattr(self, "_pending_removal", None)
                                if not pending_at_start or pending is not pending_at_start:
                                    tool_result = "No hay una desinstalacion anterior pendiente de confirmacion."
                                elif not isinstance(args.get("confirmed"), bool):
                                    tool_result = "Falta indicar si se confirma o cancela la desinstalacion."
                                else:
                                    self._pending_removal = None
                                    if args["confirmed"]:
                                        tool_result = execute_tool("remove_package", pending)
                                    else:
                                        tool_result = "Desinstalacion cancelada."
                                executed_actions.append(str(tool_result))
                                direct_result |= function_name in ACTION_RESULT_TOOLS
                            elif _is_unsolicited_system_action(function_name, user_message):
                                tool_result = (
                                    f"Acción bloqueada: el mensaje actual del usuario ('{user_message}') "
                                    f"es una pregunta o conversación y no solicitó ejecutar `{function_name}`. "
                                    "Responde directamente a la pregunta del usuario usando `respond_to_user`."
                                )
                            else:
                                tool_result = execute_tool(function_name, args)
                                executed_actions.append(str(tool_result))
                                direct_result |= function_name in ACTION_RESULT_TOOLS
                            if function_name not in {"confirm_package_removal"} and not _is_unsolicited_system_action(function_name, user_message) and function_name in {
                                "confirm_pending_action", "install_program", "remove_package", "write_file", "manage_service", "undo_last_change"
                            }:
                                executed_actions.append(str(tool_result))
                                direct_result |= function_name in ACTION_RESULT_TOOLS

                    self._history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": str(tool_result),
                    })
                if direct_result:
                    return finish("\n\n".join(executed_actions))
                if conversational_reply:
                    return finish(conversational_reply)

            return finish("\n".join(executed_actions) or "No se pudo completar la solicitud. No se ejecuto ninguna accion.")

        except Exception as exc:
            if executed_actions:
                return finish("\n".join(executed_actions))
            if _is_retriable_provider_error(exc):
                local_pending_reply = self._try_local_pending_resolution(
                    user_message,
                    pending_at_start=pending_at_start,
                    pending_action_at_start=pending_action_at_start,
                )
                if local_pending_reply is not None:
                    return finish(local_pending_reply)
            del self._history[history_start:]
            raise

    def chat_global(self, user_message: str) -> str:
        """Modo Chat Global: conversación general pura sin herramientas ni efectos sobre el sistema."""
        global_history = getattr(self, "_global_history", None)
        if not isinstance(global_history, list) or not global_history:
            global_history = [{"role": "system", "content": GLOBAL_SYSTEM_PROMPT}]
            self._global_history = global_history

        history_start = len(global_history)
        global_history.append({"role": "user", "content": user_message})

        deadline = time.monotonic() + max(LLM_TOTAL_TIMEOUT, getattr(self, "request_timeout", LLM_REQUEST_TIMEOUT))

        def remaining_timeout() -> float:
            remaining = deadline - time.monotonic()
            if remaining <= 1:
                raise TimeoutError(
                    f"La IA superó el tiempo máximo de espera ({LLM_TOTAL_TIMEOUT:.0f} segundos)."
                )
            return min(getattr(self, "request_timeout", LLM_REQUEST_TIMEOUT), remaining)

        try:
            response = self._call_llm_with_fallback(list(global_history), None, remaining_timeout)
            response_message = response.choices[0].message
            raw_content = getattr(response_message, "content", None) or ""
            cleaned = _clean_model_reply(raw_content.strip()) if isinstance(raw_content, str) else ""
            if not cleaned:
                cleaned = "No pude generar una respuesta en este momento."
            global_history.append({"role": "assistant", "content": cleaned})
            log_message("user", user_message, self.session_id)
            log_message("assistant", cleaned, self.session_id)
            return cleaned
        except Exception:
            del global_history[history_start:]
            raise

    def reset_chat(self, clear_persistent: bool = False) -> None:
        """Reinicia el historial de conversación. Opcionalmente borra la memoria persistente."""
        system_context = _build_system_context()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(system_context=system_context)
        self._history = [{"role": "system", "content": system_prompt}]
        self._global_history = [{"role": "system", "content": GLOBAL_SYSTEM_PROMPT}]
        self._pending_removal = None
        self._pending_action = None
        if clear_persistent:
            clear_memory()

    clear_session_history = reset_chat

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


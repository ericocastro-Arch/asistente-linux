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
Eres un Agente Autónomo conversacional experto en Linux (adaptable a Ubuntu/Debian, Fedora, Arch Linux, openSUSE y más), \
que asiste al usuario SIEMPRE EN ESPAÑOL.

REGLAS DE USO DE HERRAMIENTAS:
1. Cuando el usuario pida una ACCIÓN en el sistema, USA tus herramientas — no te limites a dar instrucciones de texto.
2. Para consultar el estado del equipo, recursos, red, disco, memoria, procesos o diagnósticos → PREFIERE `run_diagnostic` eligiendo el nombre del catálogo. Si ninguna opción del catálogo cubre la consulta de solo lectura → usa `run_command_silent` como último recurso.
3. Para comandos que requieren sudo o interacción del usuario → usa `open_terminal_command`.
4. Para actualizar el sistema → usa `update_system` (preferiblemente modo gui).
5. Para instalar programas desde lenguaje natural → usa `install_program`.
6. Para instalar paquetes .deb descargados → usa `install_deb_package`.
7. Para revisar o actualizar firmware → usa `manage_firmware`.
8. Para abrir aplicaciones gráficas → usa `open_application`.
9. Para gestionar servicios systemd → usa `manage_service`.
10. Para buscar paquetes sin instalar → usa `search_package`.
11. Para leer o crear archivos → usa `read_file` o `write_file` (solo se escribe dentro de la carpeta personal; cada cambio se respalda). Si el usuario pide deshacer o revertir el último cambio de un archivo → usa `undo_last_change`.
12. Para desinstalar aplicaciones o paquetes → usa `remove_package` para PREPARAR la solicitud. La aplicación pedirá confirmación automáticamente. Usa `source="auto"` si el usuario no dijo apt/snap/flatpak/desktop. Si no se encuentra el paquete, el sistema abrirá el Centro de Software (sección Gestionar) como alternativa. Nunca inventes cadenas con `which`, `dpkg`, `snap list`, `flatpak list` y tuberías si la intención final es quitar una app.
13. Para preguntas, aclaraciones o solicitar confirmación → usa `respond_to_user` con texto claro y conciso. Esta herramienta solo conversa, no realiza acciones.
14. Cada turno debe producir una llamada real a una herramienta. Para instalar llama a install_program. Si hay una desinstalación pendiente y el usuario la confirma, llama a confirm_package_removal con confirmed=true; si la cancela, usa confirmed=false. Para escribir o cambiar un servicio, LinuxMate mostrará primero un plan y pedirá confirmación; nunca llames a confirm_pending_action en el mismo turno que propone la acción. Escribir que se abrió una terminal no la abre.

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
- Sé conciso, directo y amigable.
- Usa emojis moderadamente para mejorar la lectura.
- Cuando ejecutes una herramienta, explica brevemente en tu respuesta qué hiciste.
- Después de usar una herramienta, respeta su salida real. No digas que se abrió una terminal si la herramienta no lo informó.
- La memoria de sesiones anteriores solo aporta contexto; sus afirmaciones de éxito no prueban ejecuciones actuales. No copies esos mensajes para responder a una nueva acción.
- Si el usuario comete un error en un comando, corrígelo de forma amable.

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
        """Carga el historial de sesiones anteriores en el contexto del agente."""
        past = load_memory()
        if past:
            # Insertar separador para distinguir conversación anterior de la actual
            self._history.append({
                "role": "assistant",
                "content": "[Memoria de sesiones anteriores cargada — contexto previo disponible]"
            })
            self._history.extend(past[-10:])  # máximo 10 mensajes anteriores para respetar límites de cuota/tokens

    def chat(self, user_message: str) -> str:
        """Procesa el mensaje del usuario, ejecutando herramientas si el LLM lo decide."""
        history_start = len(self._history)
        self._history.append({"role": "user", "content": user_message})
        log_message("user", user_message, self.session_id)

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
                request_args = {
                    "model": self.model,
                    "messages": messages,
                    **completion_options(getattr(self, "provider", "groq"), self.model,
                                         getattr(self, "temperature", 0.2), getattr(self, "max_tokens", 1500)),
                    "timeout": remaining_timeout(),
                    "tools": available_tools,
                    "tool_choice": "required" if getattr(self, "provider", "groq") in {"groq", "nvidia", "openai", "ollama"} else "auto",
                }
                try:
                    response = self._client.chat.completions.create(**request_args)
                except Exception:
                    if retry_needed:
                        raise
                    retry_needed = True
                    continue

                response_message = response.choices[0].message
                tool_calls = getattr(response_message, "tool_calls", None)

                # No se acepta texto libre como evidencia de que una accion ocurrio.
                if not tool_calls:
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
                            else:
                                tool_result = execute_tool(function_name, args)
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

        except Exception:
            if executed_actions:
                return finish("\n".join(executed_actions))
            del self._history[history_start:]
            raise

    def reset_chat(self, clear_persistent: bool = False) -> None:
        """Reinicia el historial de conversación. Opcionalmente borra la memoria persistente."""
        system_context = _build_system_context()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(system_context=system_context)
        self._history = [{"role": "system", "content": system_prompt}]
        self._pending_removal = None
        self._pending_action = None
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

"""Procesador de solicitudes locales y delegacion controlada al agente de IA."""

from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Optional, Tuple

from src.core.diagnostic_catalog import run_diagnostic
from src.core.tools import (
    execute_tool,
    prepare_install_program,
    tool_open_application,
    tool_open_software_center,
)
from src.nlp.router import RequestRoute, route_request
from src.nlp.system_tools import (
    get_cpu_temperature_status,
    get_current_time_date,
    get_network_diagnostic,
    get_performance_diagnostic,
    get_system_status,
    open_wallpaper_settings,
)


@dataclass(frozen=True)
class ProcessedResponse:
    """Texto de respuesta y origen real usado para producirlo."""

    text: str
    source: str


def _fold_ascii(text: str) -> str:
    folded = unicodedata.normalize("NFKD", (text or "").casefold())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _run_diag_text(check_name: str) -> str:
    """Ejecuta un diagnóstico del catálogo y devuelve el texto formateado sin importar la aridad de la tupla."""
    res = run_diagnostic(check_name)
    if isinstance(res, tuple):
        return str(res[0]) if res else ""
    return str(res)


def _extract_driver_summary(diag_markdown: str, vendor_filter: str = "") -> str:
    """Extrae un resumen legible de dispositivos PCI y su 'Kernel driver in use' desde lspci -nnk."""
    lines = diag_markdown.splitlines()
    entries: list[tuple[str, str, str]] = []
    current_device = ""
    current_driver = ""
    current_modules = ""

    def flush() -> None:
        nonlocal current_device, current_driver, current_modules
        if current_device:
            if not vendor_filter or vendor_filter.lower() in current_device.lower():
                if current_driver or current_modules:
                    entries.append((current_device, current_driver, current_modules))
        current_device = ""
        current_driver = ""
        current_modules = ""

    for raw in lines:
        line = raw.rstrip()
        if not line or line.startswith("```") or line.startswith("**"):
            continue
        if re.match(r"^[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9]", line):
            flush()
            current_device = line
        elif "Kernel driver in use:" in line:
            current_driver = line.split("Kernel driver in use:", 1)[1].strip()
        elif "Kernel modules:" in line:
            current_modules = line.split("Kernel modules:", 1)[1].strip()
    flush()

    if not entries:
        return ""

    vendor_title = f" ({vendor_filter.capitalize()})" if vendor_filter else ""
    bullet_lines = [f"🧩 **Resumen de controladores activos en el kernel{vendor_title}:**"]
    for dev, drv, mods in entries[:14]:
        drv_label = f"`{drv}`" if drv else "*(sin driver activo)*"
        mod_label = f" · módulo: `{mods}`" if mods and mods != drv else ""
        bullet_lines.append(f"• **{dev}** → Controlador en uso: {drv_label}{mod_label}")
    return "\n".join(bullet_lines)


SYSTEM_CONCEPTS_KB: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("sudo", "superusuario", "pkexec", "polkit"),
        "🔐 **`sudo` y permisos de superusuario en Ubuntu**\n\n"
        "• **`sudo`** (*superuser do*) permite ejecutar un comando puntual con privilegios de administrador (`root`).\n"
        "• En Linux, las tareas críticas (instalar paquetes con `apt`, modificar servicios con `systemctl` o editar `/etc`) están protegidas para que ningún programa altere el sistema sin tu autorización.\n"
        "• **Ejemplo práctico:** `sudo apt update` actualiza la lista de paquetes pidiendo tu contraseña.\n"
        "• En entornos gráficos, Ubuntu utiliza **Polkit (`pkexec`)** para mostrar el diálogo oficial de autenticación.",
    ),
    (
        ("apt", "dpkg", "paquete deb", "gestor de paquetes"),
        "📦 **Gestores de paquetes en Ubuntu (`apt` y `dpkg`)**\n\n"
        "• **`apt`** descarga, instala y actualiza software desde los repositorios oficiales de Ubuntu resolviendo todas las dependencias automáticamente.\n"
        "• **`dpkg`** instala archivos locales `.deb` directamente en el sistema.\n"
        "• **Comandos esenciales:**\n"
        "  - `sudo apt update && sudo apt upgrade` → actualiza tus programas.\n"
        "  - `apt search <nombre>` → busca un paquete sin instalarlo.\n"
        "  - `sudo apt install <paquete>` → instala una aplicación.",
    ),
    (
        ("systemd", "systemctl", "servicio", "servicios", "daemon"),
        "⚙️ **Servicios del sistema (`systemd` y `systemctl`)**\n\n"
        "• **`systemd`** es el gestor de arranque y servicios de Ubuntu. Controla los procesos que corren en segundo plano (red, audio, Bluetooth, Docker, SSH).\n"
        "• **Comandos útiles:**\n"
        "  - `systemctl status <servicio>` → consulta si un servicio está activo.\n"
        "  - `systemctl --failed` → muestra si algún servicio falló al iniciar.\n"
        "  - `sudo systemctl restart <servicio>` → reinicia un servicio.",
    ),
    (
        ("chmod", "chown", "permisos de archivo", "permisos en linux"),
        "🛡️ **Permisos de archivos en Linux (`chmod` y `chown`)**\n\n"
        "• Cada archivo tiene permisos para **propietario (u)**, **grupo (g)** y **otros (o)**: lectura (`r=4`), escritura (`w=2`) y ejecución (`x=1`).\n"
        "• `chmod +x script.sh` → hace ejecutable un script.\n"
        "• `chmod 600 archivo` → solo tú puedes leerlo y escribirlo (ideal para claves privadas).\n"
        "• `chown usuario:grupo archivo` → cambia el propietario del archivo.",
    ),
)


def _prepare_local_install_preview(program_name: str, agent: Optional[Any] = None) -> str:
    """Prepara una vista previa de instalación local y registra la confirmación pendiente si hay agente."""
    try:
        from src.core.policy import authorize_tool
        decision = authorize_tool("install_program", {"program_name": program_name})
        if decision is not None and decision.is_blocked:
            return f"⛔ {decision.message}"
    except Exception:
        pass

    plan = prepare_install_program(program_name, "auto")
    if isinstance(plan, str):
        return plan

    if agent is not None:
        agent._pending_action = {
            "tool_name": "install_program",
            "arguments": {"program_name": program_name, "preferred_source": "auto"},
            "prepared_install_plan": plan,
        }
    return (
        "Vista previa de instalación:\n"
        f"Aplicación: {plan['friendly_name']}\n"
        f"Paquete: {plan['package']}\n"
        f"Origen: {plan['source']}\n"
        f"Comando exacto: `{plan['command']}`\n"
        "Tamaño y dependencias: los mostrará el gestor de paquetes al confirmar.\n"
        "¿Confirmas que continúe?"
    )


def try_local_hardware_software_fallback(user_text: str) -> Optional[str]:
    """Proporciona diagnóstico real de hardware/software o respuesta guía local si la IA en la nube falla."""
    folded = re.sub(r"[^a-z0-9]+", " ", _fold_ascii(user_text)).strip()
    if not folded:
        return None

    # Saludos y ayuda general
    if re.fullmatch(
        r"(?:hola|buenas|buenos dias|buenas tardes|buenas noches|hey|saludos|que tal|como estas|quien eres|que puedes hacer|ayuda)(?:\s+.*)?",
        folded,
    ) and len(folded.split()) <= 8:
        return (
            "¡Hola! Soy **LinuxMate AI**, tu asistente y agente para Ubuntu Linux.\n\n"
            "Puedo ayudarte en dos modos:\n"
            "• **🐧 Chat del Sistema**: inspeccionar hardware en vivo (controladores Intel/AMD/NVIDIA, GPU, audio, discos, USB, batería, red, temperaturas), explicar conceptos de Linux y gestionar paquetes con confirmación.\n"
            "• **🌐 Chat Global**: responder cualquier pregunta general (cultura, programación, ciencia, historia, etc.) sin tocar el sistema.\n\n"
            "¿Qué te gustaría consultar o revisar hoy?"
        )

    # Conceptos del sistema Linux (explicación local cuando el usuario pregunta qué es / cómo funciona un concepto)
    if re.search(r"\b(?:que es|explica|explicame|para que sirve|como funciona|significa)\b", folded):
        for keywords, explanation in SYSTEM_CONCEPTS_KB:
            if any(re.search(rf"\b{re.escape(kw)}\b", folded) for kw in keywords):
                return explanation

    checks_to_run: list[str] = []
    if re.search(r"\b(?:grafica|gpu|nvidia|amd|radeon|geforce|intel|video|driver|drivers|controlador|controladores|opengl|vulkan|pci)\b", folded):
        checks_to_run.append("graphics_devices")
    if re.search(r"\b(?:audio|sonido|altavoz|altavoces|bocina|auriculares|microfono|alsa|pipewire|pulseaudio|suena|sonar)\b", folded):
        checks_to_run.append("audio_devices")
    if re.search(r"\b(?:bateria|energia|cargador|corriente|autonomia)\b", folded):
        checks_to_run.append("battery_power")
    if re.search(r"\b(?:bluetooth|emparejar)\b", folded):
        checks_to_run.append("bluetooth_status")
    if re.search(r"\b(?:pantalla|pantallas|monitor|monitores|resolucion|wayland|x11|xorg|display)\b", folded):
        checks_to_run.append("session_display")
    if re.search(r"\b(?:disco|discos|almacenamiento|espacio|particion|particiones|ssd|nvme|hdd)\b", folded):
        checks_to_run.extend(["disk_usage", "block_devices"])
    if re.search(r"\b(?:usb|pendrive|periferico|perifericos)\b", folded):
        checks_to_run.append("usb_devices")
    if re.search(r"\b(?:errores|logs|journal|journalctl|servicios fallidos|fallo del sistema)\b", folded):
        checks_to_run.extend(["failed_services", "recent_errors"])

    if checks_to_run:
        outputs = []
        seen = set()
        vendor_filter = ""
        for vendor in ("intel", "nvidia", "amd", "realtek"):
            if re.search(rf"\b{vendor}\b", folded):
                vendor_filter = vendor
                break

        for check_name in checks_to_run:
            if check_name in seen:
                continue
            seen.add(check_name)
            text_out = _run_diag_text(check_name)
            if check_name == "graphics_devices":
                summary = _extract_driver_summary(text_out, vendor_filter=vendor_filter)
                if summary:
                    outputs.append(summary)
            outputs.append(text_out)
        return (
            "🔍 **Diagnóstico local de tu equipo Ubuntu** *(modo directo sin modificar el sistema)*:\n\n"
            + "\n\n".join(outputs)
        )

    if re.search(r"\b(?:hardware|componentes|especificaciones|caracteristicas|mi pc|mi equipo|procesador|cpu|ram|memoria)\b", folded):
        status = get_system_status()
        gpu_out = _run_diag_text("graphics_devices")
        return f"{status}\n\n{gpu_out}"

    return None


class NLPProcessor:
    """Analiza el texto del usuario para resolver intenciones locales o delegar al Agente."""

    def __init__(self) -> None:
        # El enrutador es determinista y no necesita cargar un modelo pesado al iniciar.
        self.nlp = None

    def route(self, text: str) -> RequestRoute:
        """Devuelve la ruta completa para que GUI y backend usen la misma decision."""
        return route_request(text)

    def analyze_intent(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Mantiene la interfaz anterior devolviendo solo intencion y parametro."""
        route = self.route(text)
        return route.intent, route.param

    def process(self, user_text: str, agent: Optional[Any] = None, mode: str = "system") -> str:
        """Procesa el mensaje y devuelve solo texto por compatibilidad."""
        return self.process_with_source(user_text, agent, mode=mode).text

    def process_with_source(
        self,
        user_text: str,
        agent: Optional[Any] = None,
        route: Optional[RequestRoute] = None,
        mode: str = "system",
    ) -> ProcessedResponse:
        """Procesa una ruta ya calculada e informa si respondio LOCAL o IA."""
        normalized_mode = (mode or "system").strip().lower()

        # En modo "global" (Chat Global), va directo a conversación libre sin herramientas del sistema
        if normalized_mode == "global":
            if agent is not None:
                if hasattr(agent, "chat_global"):
                    return ProcessedResponse(agent.chat_global(user_text), "IA")
                if hasattr(agent, "chat"):
                    return ProcessedResponse(agent.chat(user_text), "IA")
            return ProcessedResponse(
                "🌐 **Modo Chat Global**: Configura una clave de API válida en **Configuración → Modelos y API** "
                "para conversar sobre cualquier tema general.",
                "SISTEMA",
            )

        # Si el agente tiene una confirmación pendiente, darle prioridad para no perder el flujo
        if agent is not None and (
            getattr(agent, "_pending_removal", None) is not None
            or getattr(agent, "_pending_action", None) is not None
        ):
            if hasattr(agent, "chat"):
                return ProcessedResponse(agent.chat(user_text), "IA")

        resolved_route = route or self.route(user_text)
        intent, param = resolved_route.intent, resolved_route.param

        if intent == "TIME_DATE":
            return ProcessedResponse(get_current_time_date(), "LOCAL")

        if intent == "CPU_TEMPERATURE":
            return ProcessedResponse(get_cpu_temperature_status(), "LOCAL")

        if intent == "WALLPAPER_SETTINGS":
            return ProcessedResponse(open_wallpaper_settings(), "LOCAL")

        if intent == "SYSTEM_STATUS":
            return ProcessedResponse(get_system_status(), "LOCAL")

        if intent == "DIAGNOSE_PERFORMANCE":
            return ProcessedResponse(get_performance_diagnostic(), "LOCAL")

        if intent == "DIAGNOSE_NETWORK" or intent == "SHOW_NETWORK":
            return ProcessedResponse(get_network_diagnostic(), "LOCAL")

        if intent == "OPEN_STORE":
            return ProcessedResponse(tool_open_software_center(), "LOCAL")

        if intent == "SHOW_PROCESSES":
            cpu_out = _run_diag_text("top_cpu_processes")
            mem_out = _run_diag_text("top_memory_processes")
            return ProcessedResponse(f"{cpu_out}\n\n{mem_out}", "LOCAL")

        if intent == "UPDATE_SYSTEM":
            return ProcessedResponse(execute_tool("update_system", {"mode": "gui"}), "LOCAL")

        if intent == "INSTALL_PACKAGE" and param:
            return ProcessedResponse(_prepare_local_install_preview(param, agent=agent), "LOCAL")

        if intent == "INSTALL_DEB" and param:
            return ProcessedResponse(execute_tool("install_deb_package", {"file_path": param}), "LOCAL")

        if intent == "OPEN_APP" and param:
            return ProcessedResponse(tool_open_application(param), "LOCAL")

        if agent and hasattr(agent, "chat"):
            try:
                return ProcessedResponse(agent.chat(user_text), "IA")
            except Exception:
                fallback = try_local_hardware_software_fallback(user_text)
                if fallback:
                    return ProcessedResponse(fallback, "LOCAL")
                raise

        fallback = try_local_hardware_software_fallback(user_text)
        if fallback:
            return ProcessedResponse(fallback, "LOCAL")

        return ProcessedResponse(
            "Recibí tu mensaje: " + user_text + "\n"
            "Configura tu proveedor de IA en Configuración para activar respuestas avanzadas, "
            "o hazme una consulta directa sobre tu hardware, red, discos, procesos o controladores.",
            "SISTEMA",
        )

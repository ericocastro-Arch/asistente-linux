"""Procesador de solicitudes locales y delegacion controlada al agente de IA."""

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from src.core.tools import tool_open_application, tool_open_software_center
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

    def process(self, user_text: str, agent: Optional[Any] = None) -> str:
        """Procesa el mensaje y devuelve solo texto por compatibilidad."""
        return self.process_with_source(user_text, agent).text

    def process_with_source(
        self,
        user_text: str,
        agent: Optional[Any] = None,
        route: Optional[RequestRoute] = None,
    ) -> ProcessedResponse:
        """Procesa una ruta ya calculada e informa si respondio LOCAL o IA."""
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

        if intent == "DIAGNOSE_NETWORK":
            return ProcessedResponse(get_network_diagnostic(), "LOCAL")

        if intent == "OPEN_STORE":
            return ProcessedResponse(tool_open_software_center(), "LOCAL")

        if resolved_route.is_visual:
            return ProcessedResponse(
                "Esta accion se completa desde su panel visual local.",
                "LOCAL",
            )

        if intent == "OPEN_APP" and param:
            return ProcessedResponse(tool_open_application(param), "LOCAL")

        if agent and hasattr(agent, "chat"):
            return ProcessedResponse(agent.chat(user_text), "IA")

        return ProcessedResponse(
            "Recibí tu mensaje: " + user_text + "\n"
            "Configura tu GROQ_API_KEY en .env para activar las acciones y respuestas del agente.",
            "SISTEMA",
        )

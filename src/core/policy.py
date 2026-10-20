"""Capa de políticas: decide qué herramientas del agente pueden ejecutarse y en qué modo.

Todas las herramientas pasan por `authorize_tool` antes de ejecutarse (ver
`execute_tool` y el agente). Es una lista blanca: una herramienta que no figura en
`TOOL_LEVELS` se rechaza, aunque el modelo la invente.

Niveles (de menor a mayor impacto):
  READ    consultas y diagnóstico que no modifican nada.
  USER    acciones dentro de la sesión del usuario (abrir apps, escribir en ~).
  SYSTEM  paquetes, servicios, firmware, actualizaciones (requieren privilegios).

Modos (`SECURITY_MODE`):
  readonly  el agente solo puede usar herramientas READ.
  safe      (por defecto) todas, con las confirmaciones que exige cada una.
Ningún modo omite confirmaciones: no existe un modo «autónomo».
"""

from __future__ import annotations

import os
from enum import IntEnum
from typing import Any, Mapping

from src.core.security import RiskLevel, SafetyDecision, SafetyLevel


class ToolLevel(IntEnum):
    READ = 0
    USER = 1
    SYSTEM = 2


MODE_READONLY = "readonly"
MODE_SAFE = "safe"
VALID_MODES = (MODE_SAFE, MODE_READONLY)

MODE_MAX_LEVEL = {
    MODE_READONLY: ToolLevel.READ,
    MODE_SAFE: ToolLevel.SYSTEM,
}

TOOL_LEVELS: dict[str, ToolLevel] = {
    # lectura
    "get_system_status": ToolLevel.READ,
    "run_diagnostic": ToolLevel.READ,
    "run_command_silent": ToolLevel.READ,
    "read_file": ToolLevel.READ,
    "search_package": ToolLevel.READ,
    # usuario
    "open_application": ToolLevel.USER,
    "open_software_center": ToolLevel.USER,
    "open_terminal_command": ToolLevel.USER,
    "write_file": ToolLevel.USER,
    "undo_last_change": ToolLevel.USER,
    # sistema
    "install_program": ToolLevel.SYSTEM,
    "install_deb_package": ToolLevel.SYSTEM,
    "remove_package": ToolLevel.SYSTEM,
    "update_system": ToolLevel.SYSTEM,
    "manage_firmware": ToolLevel.SYSTEM,
    "manage_service": ToolLevel.SYSTEM,
}

LEVEL_LABELS = {
    ToolLevel.READ: "de consulta",
    ToolLevel.USER: "de usuario",
    ToolLevel.SYSTEM: "del sistema",
}


def normalize_mode(value: Any) -> str:
    """Convierte cualquier valor guardado en un modo válido.

    Valores desconocidos o heredados (por ejemplo el antiguo «autonomous») se tratan
    como `safe`: nunca se relaja la seguridad por un valor mal escrito.
    """
    mode = str(value or "").strip().lower()
    return mode if mode in VALID_MODES else MODE_SAFE


def current_mode() -> str:
    return normalize_mode(os.environ.get("SECURITY_MODE"))


def tool_level(name: str, arguments: Mapping[str, Any] | None = None) -> ToolLevel | None:
    """Nivel efectivo de una llamada; depende de los argumentos en algunos casos."""
    level = TOOL_LEVELS.get(name)
    args = arguments if isinstance(arguments, Mapping) else {}
    if level is None:
        return None
    if name == "manage_service" and str(args.get("action", "status")).strip().lower() == "status":
        return ToolLevel.READ
    if name == "manage_firmware" and str(args.get("action", "check")).strip().lower() == "check":
        return ToolLevel.USER  # abre una terminal para consultar; no instala nada
    return level


def authorize_tool(name: str, arguments: Mapping[str, Any] | None = None) -> SafetyDecision:
    """Decide si la herramienta puede ejecutarse en el modo actual."""
    level = tool_level(name, arguments)
    if level is None:
        return SafetyDecision(
            SafetyLevel.BLOCKED,
            f"Herramienta '{name}' no reconocida o no permitida.",
            RiskLevel.HIGH,
            "unknown_tool",
        )
    mode = current_mode()
    if level > MODE_MAX_LEVEL[mode]:
        return SafetyDecision(
            SafetyLevel.BLOCKED,
            f"Modo solo lectura activo: no puedo ejecutar acciones {LEVEL_LABELS[level]} "
            f"('{name}'). Cambia el modo en Configuración > Ejecución si quieres permitirlo.",
            RiskLevel.MEDIUM,
            "mode_restricted",
        )
    return SafetyDecision(SafetyLevel.SAFE, "Herramienta permitida.", RiskLevel.LOW, "allowed")

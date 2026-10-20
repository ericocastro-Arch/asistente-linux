"""Consultas y acciones limitadas para servicios systemd del sistema."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any

from src.core.privilege import execute_privileged_action
from src.core.tools import is_critical_system_service


_UNIT_NAME = re.compile(r"[A-Za-z0-9_](?:[A-Za-z0-9_@.:-]|\\x[0-9A-Fa-f]{2})*\.service\Z")
_ALLOWED_ACTIONS = {"start", "stop", "restart", "enable", "disable"}
_MAX_SERVICES = 500


def _run_systemctl(arguments: list[str], timeout: int = 15) -> tuple[int, str, str]:
    """Ejecuta systemctl con argumentos fijos, sin shell y en locale estable."""
    binary = shutil.which("systemctl")
    if not binary:
        return 127, "", "systemctl no está disponible en este equipo."
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    try:
        process = subprocess.run(
            [binary, *arguments],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return 124, "", "La consulta de servicios tardó demasiado."
    except OSError:
        return 127, "", "No se pudo consultar systemd en este equipo."
    return process.returncode, process.stdout, process.stderr


def _read_installed_units() -> tuple[dict[str, str], str | None]:
    code, output, error = _run_systemctl([
        "list-unit-files", "--type=service", "--no-legend", "--no-pager", "--full"
    ])
    if code != 0:
        detail = error.strip()
        if "Operation not permitted" in detail or "Failed to connect" in detail:
            detail = "No se pudo acceder al bus del sistema. Comprueba que systemd esté disponible en esta sesión."
        return {}, detail or "No se pudo obtener la lista de servicios del sistema."

    units: dict[str, str] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 2:
            continue
        unit, startup = fields[0], fields[1]
        if _UNIT_NAME.fullmatch(unit):
            units[unit] = startup
    return units, None


def _read_active_units() -> tuple[dict[str, dict[str, str]], str | None]:
    code, output, error = _run_systemctl([
        "list-units", "--type=service", "--all", "--no-legend", "--no-pager", "--plain", "--full"
    ])
    if code != 0:
        detail = error.strip()
        if "Operation not permitted" in detail or "Failed to connect" in detail:
            detail = "No se pudo acceder al bus del sistema. Comprueba que systemd esté disponible en esta sesión."
        return {}, detail or "No se pudo consultar el estado de los servicios."

    units: dict[str, dict[str, str]] = {}
    for line in output.splitlines():
        fields = line.split(None, 4)
        if len(fields) < 4:
            continue
        unit, _load, active, sub = fields[:4]
        description = fields[4] if len(fields) > 4 else "Servicio del sistema"
        if _UNIT_NAME.fullmatch(unit):
            units[unit] = {"active": active, "sub": sub, "description": description}
    return units, None


def get_service_overview() -> dict[str, Any]:
    """Devuelve servicios instalados con estado actual y estado de inicio."""
    installed, installed_error = _read_installed_units()
    if installed_error:
        return {"success": False, "message": installed_error, "services": []}

    active, active_error = _read_active_units()
    if active_error:
        return {"success": False, "message": active_error, "services": []}

    services: list[dict[str, Any]] = []
    for unit, startup in installed.items():
        live = active.get(unit, {})
        current = live.get("active", "inactive")
        services.append({
            "unit": unit,
            "description": live.get("description") or unit.removesuffix(".service"),
            "active": current,
            "sub": live.get("sub", "dead" if current == "inactive" else "unknown"),
            "startup": startup,
            "critical": is_critical_system_service(unit),
        })

    order = {"failed": 0, "active": 1, "activating": 2, "reloading": 3, "inactive": 4}
    services.sort(key=lambda item: (order.get(item["active"], 5), item["unit"].casefold()))
    total = len(services)
    return {
        "success": True,
        "services": services[:_MAX_SERVICES],
        "total": total,
        "limited": total > _MAX_SERVICES,
        "message": "Servicios del sistema actualizados.",
    }


def manage_system_service(unit: str, action: str, confirmed: bool) -> dict[str, Any]:
    """Aplica una acción permitida a un servicio instalado tras confirmación explícita."""
    if not isinstance(unit, str) or not isinstance(action, str):
        return {"success": False, "message": "Indica un servicio y una acción válidos."}
    service = unit.strip()
    operation = action.strip().lower()
    if not _UNIT_NAME.fullmatch(service):
        return {"success": False, "message": "El identificador del servicio no es válido."}
    if re.search(r"\\x[0-9A-Fa-f]{2}", service):
        return {"success": False, "message": "Este servicio usa un nombre escapado. Puedes consultar su estado, pero LinuxMate no lo controla desde este panel."}
    if operation not in _ALLOWED_ACTIONS:
        return {"success": False, "message": "La acción solicitada no está permitida."}
    if confirmed is not True:
        return {"success": False, "cancelled": True, "message": "No se hizo ningún cambio."}
    if operation in {"stop", "disable", "restart"} and is_critical_system_service(service):
        return {
            "success": False,
            "message": "LinuxMate bloquea detener, deshabilitar o reiniciar este servicio porque puede afectar el inicio, la red o tu sesión.",
        }

    installed, installed_error = _read_installed_units()
    if installed_error:
        return {"success": False, "message": installed_error}
    if service not in installed:
        return {"success": False, "message": "El servicio ya no aparece instalado. Actualiza la lista y vuelve a intentarlo."}

    if operation in {"stop", "disable", "restart"}:
        code, output, error = _run_systemctl(["show", service, "--property=Id", "--value"])
        canonical = output.strip()
        if code != 0 or not _UNIT_NAME.fullmatch(canonical):
            detail = error.strip() or "No se pudo confirmar el servicio de destino."
            return {"success": False, "message": detail}
        if is_critical_system_service(canonical):
            return {
                "success": False,
                "message": "LinuxMate bloquea esta acción porque el servicio apunta a un componente esencial del sistema.",
            }

    result = execute_privileged_action(
        ["systemctl", operation, service],
        title=f"Servicio del sistema: {service}",
    )
    if not result.success:
        return {
            "success": False,
            "cancelled": result.mechanism == "cancelled",
            "message": result.message or "No se pudo aplicar el cambio.",
        }

    if result.mechanism == "terminal":
        message = "Se abrió una terminal para confirmar la operación con tu contraseña. Cuando termine, actualiza la lista."
    else:
        message = f"La acción «{operation}» se completó para {service}."
    return {
        "success": True,
        "mechanism": result.mechanism,
        "refresh": result.mechanism != "terminal",
        "message": message,
    }

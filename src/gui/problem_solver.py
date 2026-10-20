"""Flujos guiados para problemas comunes, con comprobaciones locales de solo lectura."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import psutil

from src.core.tools import launch_in_terminal
from src.gui.system_diagnostics import (
    _check_network,
    _check_packages,
    _check_repositories,
    _check_updates,
    _package_repair_command,
)


GUIDES: list[dict[str, Any]] = [
    {
        "id": "wifi", "title": "Wi-Fi o Internet", "icon": "network",
        "summary": "Averigua si falta la conexión, la ruta al router o la resolución DNS.",
        "steps": [
            "Comprueba que el modo avión esté desactivado y que estés conectado a la red correcta.",
            "Acércate al router y prueba la misma red desde otro dispositivo.",
            "Ejecuta las comprobaciones. Si hay red local pero falla DNS, revisa VPN o DNS privado antes de cambiar ajustes.",
        ],
        "checks": ["connection", "gateway", "dns"],
        "actions": [
            {
                "id": "restart_network",
                "kind": "repair",
                "label": "Reiniciar NetworkManager",
                "description": "Se abrirá una terminal para reiniciar NetworkManager. Tu red puede reconectarse durante unos segundos.",
            },
            {"id": "config_network", "kind": "tool", "label": "Ver más herramientas de red"},
            {"id": "service_manager", "kind": "tool", "label": "Revisar servicios del sistema"},
        ],
    },
    {
        "id": "sound", "title": "No hay sonido", "icon": "volume",
        "summary": "Comprueba el servidor de audio y el dispositivo de salida seleccionado.",
        "steps": [
            "Sube el volumen del equipo y comprueba que la aplicación y el sistema no estén silenciados.",
            "En los ajustes de Sonido, selecciona los altavoces o auriculares correctos y prueba la salida.",
            "Desconecta y vuelve a conectar el dispositivo. En Bluetooth, confirma también que esté conectado como salida de audio.",
        ],
        "checks": ["audio_server", "audio_output"],
        "actions": [
            {
                "id": "unmute_audio",
                "kind": "repair",
                "label": "Activar salida y subir volumen al 75%",
                "description": "Quita el silencio de la salida de audio predeterminada y ajusta su volumen al 75% para tu sesión.",
            },
            {
                "id": "restart_audio",
                "kind": "repair",
                "label": "Reiniciar servidor de audio",
                "description": "Reinicia los servicios de audio de tu sesión (PipeWire / PulseAudio) sin cerrar tus programas.",
            },
            {"id": "logs_analyzer", "kind": "tool", "label": "Revisar registros de audio"},
        ],
    },
    {
        "id": "bluetooth", "title": "Bluetooth no conecta", "icon": "bluetooth",
        "summary": "Revisa el servicio Bluetooth y si el adaptador está encendido.",
        "steps": [
            "Carga el accesorio, acércalo al equipo y activa su modo de emparejamiento.",
            "Comprueba Bluetooth en el menú del sistema y asegúrate de que el modo avión esté apagado.",
            "Si el accesorio ya estaba emparejado, quítalo desde los ajustes gráficos y vuelve a emparejarlo.",
        ],
        "checks": ["bluetooth_service", "bluetooth_adapter"],
        "actions": [
            {
                "id": "repair_bluetooth",
                "kind": "repair",
                "label": "Activar y reiniciar servicio Bluetooth",
                "description": "Se abrirá una terminal para desbloquear el adaptador (rfkill), encenderlo e iniciar bluetooth.service.",
            },
            {"id": "service_manager", "kind": "tool", "label": "Abrir gestor de servicios"},
            {"id": "logs_analyzer", "kind": "tool", "label": "Ver registros de Bluetooth"},
        ],
    },
    {
        "id": "printer", "title": "La impresora no aparece", "icon": "printer",
        "summary": "Comprueba el servicio de impresión y si Linux detecta impresoras configuradas.",
        "steps": [
            "Confirma que la impresora esté encendida y sin avisos de papel, tinta o tóner.",
            "Conecta el equipo y la impresora a la misma red, o prueba otro cable USB.",
            "Abre Impresoras en la configuración del sistema y verifica que no esté pausada la cola.",
        ],
        "checks": ["print_service", "configured_printers"],
        "actions": [
            {
                "id": "repair_cups",
                "kind": "repair",
                "label": "Iniciar y habilitar servicio de impresión (CUPS)",
                "description": "Se abrirá una terminal para habilitar e iniciar cups.service mediante systemd.",
            },
            {"id": "service_manager", "kind": "tool", "label": "Ver servicios de impresión"},
            {"id": "logs_analyzer", "kind": "tool", "label": "Ver registros de impresión"},
        ],
    },
    {
        "id": "disk", "title": "El disco está lleno", "icon": "backup",
        "summary": "Mide el espacio de la carpeta personal y del sistema sin recorrer ni borrar archivos.",
        "steps": [
            "Revisa Descargas, vídeos y la papelera; identifica archivos que reconozcas antes de eliminarlos.",
            "Guarda una copia de los archivos importantes en otro soporte antes de liberar espacio.",
            "No borres carpetas de /usr, /var o /boot. Si no reconoces un archivo, consúltalo primero.",
        ],
        "checks": ["disk_space"],
        "actions": [
            {
                "id": "clean_package_cache",
                "kind": "repair",
                "label": "Limpiar caché de paquetes en terminal",
                "description": "Se abrirá una terminal para limpiar la caché del gestor de paquetes de tu distribución sin tocar tus documentos.",
            },
            {"id": "backup_manager", "kind": "tool", "label": "Respaldar archivos personales"},
            {"id": "troubleshooter", "kind": "tool", "label": "Abrir diagnóstico del sistema"},
        ],
    },
    {
        "id": "updates", "title": "Fallan las actualizaciones", "icon": "sync",
        "summary": "Busca problemas de red, poco espacio, dependencias y repositorios usando datos locales.",
        "steps": [
            "Comprueba la conexión a Internet, la fecha y hora del equipo y el espacio disponible.",
            "Ejecuta el análisis. LinuxMate consulta los índices guardados y no los actualiza durante la comprobación.",
            "Si el gestor propone quitar paquetes que necesitas, cancela y pide ayuda antes de continuar.",
        ],
        "checks": ["network", "disk_space", "packages", "updates", "repositories"],
        "actions": [
            {
                "id": "repair_packages",
                "kind": "repair",
                "label": "Reparar gestor de paquetes",
                "description": "Se abrirá una terminal con el comando oficial de reparación de dependencias de tu distribución.",
            },
            {"id": "update_system", "kind": "tool", "label": "Abrir guía de actualizaciones"},
            {"id": "troubleshooter", "kind": "tool", "label": "Ver diagnóstico completo"},
        ],
    },
    {
        "id": "permissions", "title": "Permiso denegado", "icon": "shield",
        "summary": "Revisa permisos básicos de una ruta de tu carpeta personal, sin cambiarla.",
        "steps": [
            "Comprueba que la ruta exista y que estés usando la cuenta correcta.",
            "Indica una ruta dentro de tu carpeta personal para revisar lectura, escritura y acceso.",
            "Evita usar chmod 777 o sudo a ciegas: pueden exponer archivos o cambiar el propietario incorrecto.",
        ],
        "checks": ["home_permissions"],
        "input": {"id": "problemPath", "label": "Ruta dentro de tu carpeta personal", "placeholder": "Ejemplo: ~/Documentos/tarea.txt"},
        "actions": [
            {
                "id": "repair_home_permissions",
                "kind": "repair",
                "label": "Restaurar propietario de tu carpeta personal",
                "description": "Se abrirá una terminal para devolver la propiedad de los archivos de tu carpeta personal a tu usuario actual.",
            },
            {"id": "backup_manager", "kind": "tool", "label": "Crear copia de seguridad antes de cambiar"},
        ],
    },
    {
        "id": "app", "title": "Una aplicación no abre", "icon": "package",
        "summary": "Comprueba si el programa o su lanzador están disponibles sin abrirlos.",
        "steps": [
            "Escribe el nombre del programa o su comando. Prueba abrirlo desde el menú de aplicaciones.",
            "Comprueba que la aplicación terminó de instalarse y que el disco tiene espacio suficiente.",
            "Si no aparece como instalada, búscala en el catálogo de LinuxMate y revisa origen y distribución.",
        ],
        "checks": ["application_entry", "packages", "disk_space"],
        "input": {"id": "problemApplication", "label": "Nombre del programa o comando", "placeholder": "Ejemplo: firefox"},
        "actions": [
            {
                "id": "repair_packages",
                "kind": "repair",
                "label": "Verificar y reparar dependencias",
                "description": "Se abrirá una terminal para reparar paquetes o instalaciones incompletas en tu distribución.",
            },
            {"id": "install_programs", "kind": "tool", "label": "Buscar en el catálogo de apps"},
            {"id": "logs_analyzer", "kind": "tool", "label": "Ver errores recientes en registros"},
        ],
    },
    {
        "id": "boot", "title": "Problemas de inicio o lentitud al arrancar", "icon": "cpu",
        "summary": "Analiza el tiempo de arranque, los servicios que más tardan y las aplicaciones de autoinicio.",
        "steps": [
            "Desconecta discos externos o periféricos USB que no sean necesarios durante el encendido.",
            "Ejecuta las comprobaciones para identificar qué servicios de systemd tardaron más en el último arranque.",
            "Desactiva desde el Monitor de recursos las aplicaciones de inicio de usuario que no necesites al encender.",
        ],
        "checks": ["boot_time", "slow_boot_services", "failed_services", "startup_apps_count"],
        "actions": [
            {
                "id": "inspect_boot_blame",
                "kind": "repair",
                "label": "Inspeccionar tiempos de arranque en terminal",
                "description": "Se abrirá una terminal mostrando systemd-analyze time, los servicios más lentos y errores críticos del arranque.",
            },
            {"id": "resource_monitor", "kind": "tool", "label": "Gestionar aplicaciones de inicio"},
            {"id": "service_manager", "kind": "tool", "label": "Abrir gestor de servicios"},
        ],
    },
    {
        "id": "screen", "title": "Pantalla negra o gráficos", "icon": "tools",
        "summary": "Comprueba si Linux detecta un adaptador gráfico y si hay servicios fallidos.",
        "steps": [
            "Espera un minuto, revisa el brillo y vuelve a conectar el monitor o cargador.",
            "Prueba una pantalla externa. En algunos equipos, Ctrl+Alt+F3 permite ver si responde una consola de texto.",
            "No elimines drivers ni cambies GRUB sin una vía de recuperación. Consulta el modelo detectado y la recomendación de tu distribución.",
        ],
        "checks": ["graphics_adapter", "failed_services"],
        "actions": [
            {
                "id": "inspect_graphics_logs",
                "kind": "repair",
                "label": "Ver controlador en uso y errores gráficos",
                "description": "Se abrirá una terminal con el módulo de kernel activo para tu tarjeta gráfica y los avisos del arranque.",
            },
            {"id": "drivers_manager", "kind": "tool", "label": "Consultar controladores"},
            {"id": "troubleshooter", "kind": "tool", "label": "Ver diagnóstico del sistema"},
        ],
    },
]

_GUIDE_BY_ID = {guide["id"]: guide for guide in GUIDES}


def get_problem_guides() -> dict[str, Any]:
    """Devuelve instrucciones presentables; nunca incluye comandos para ejecución libre."""
    return {"success": True, "guides": GUIDES}


def _run(args: list[str], timeout: int = 8) -> tuple[int | None, str]:
    if not args or shutil.which(args[0]) is None:
        return None, ""
    try:
        result = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
        return result.returncode, (result.stdout or result.stderr).strip()
    except (OSError, subprocess.SubprocessError):
        return None, ""


def _result(title: str, status: str, detail: str) -> dict[str, str]:
    return {"title": title, "status": status, "detail": detail[:420]}


def _check_connection() -> dict[str, str]:
    code, output = _run(["nmcli", "-t", "-f", "STATE", "general"])
    if code is None:
        return _result("Estado de NetworkManager", "unknown", "NetworkManager o nmcli no está disponible; revisa la conexión desde los ajustes del escritorio.")
    state = output.lower()
    if "connected" in state and "disconnected" not in state:
        return _result("Estado de NetworkManager", "ok", "NetworkManager informa que hay una conexión activa.")
    if "connecting" in state:
        return _result("Estado de NetworkManager", "warning", "NetworkManager todavía intenta conectarse.")
    return _result("Estado de NetworkManager", "warning", "NetworkManager no informa una conexión activa.")


def _check_gateway() -> dict[str, str]:
    code, output = _run(["ip", "route", "show", "default"])
    if code is None:
        return _result("Ruta al router", "unknown", "No se pudo consultar la ruta de red.")
    return _result("Ruta al router", "ok" if output else "warning", "Hay una ruta de salida configurada." if output else "No aparece una ruta de salida; comprueba Wi-Fi o el cable de red.")


def _check_dns() -> dict[str, str]:
    code, _ = _run(["getent", "ahostsv4", "example.com"], timeout=6)
    if code is None:
        return _result("Resolución DNS", "unknown", "No se pudo comprobar DNS; getent no está disponible.")
    if code == 0:
        return _result("Resolución DNS", "ok", "La consulta DNS a example.com respondió.")
    return _result("Resolución DNS", "warning", "No respondió DNS. Esta prueba consulta example.com; puede fallar si la red bloquea consultas externas.")


def _check_audio_server() -> dict[str, str]:
    if shutil.which("wpctl"):
        code, output = _run(["wpctl", "status"])
        if code == 0:
            return _result("Servidor de audio", "ok", "PipeWire respondió a la consulta de estado.")
    if shutil.which("pactl"):
        code, output = _run(["pactl", "info"])
        if code == 0:
            has_sink = any(line.lower().startswith("default sink:") for line in output.splitlines())
            return _result("Servidor de audio", "ok" if has_sink else "warning", "PulseAudio/PipeWire respondió." + (" Hay una salida predeterminada." if has_sink else " No hay una salida predeterminada."))
    return _result("Servidor de audio", "unknown", "No se detectó wpctl ni pactl. Comprueba Sonido en la configuración del escritorio.")


def _check_audio_output() -> dict[str, str]:
    if shutil.which("wpctl"):
        code, output = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
        if code == 0:
            muted = "MUTED" in output.upper()
            match = re.search(r"Volume:\s*([0-9.]+)", output)
            volume = round(float(match.group(1)) * 100) if match else None
            if muted:
                return _result("Volumen de salida", "warning", "La salida predeterminada aparece silenciada; puedes cambiarlo desde Sonido.")
            if volume is not None:
                return _result("Volumen de salida", "ok" if volume > 0 else "warning", f"Volumen de salida detectado: {volume}%." if volume > 0 else "El volumen de salida aparece en 0%.")
    if shutil.which("pactl"):
        code, output = _run(["pactl", "info"])
        if code == 0 and any(line.lower().startswith("default sink:") and ":" in line and line.split(":", 1)[1].strip() for line in output.splitlines()):
            return _result("Volumen de salida", "ok", "Hay una salida de audio predeterminada. Verifica el volumen y el silencio en los ajustes gráficos.")
    return _result("Volumen de salida", "unknown", "No se pudo leer la salida predeterminada. Selecciona un dispositivo en Sonido.")


def _check_bluetooth_service() -> dict[str, str]:
    code, output = _run(["systemctl", "is-active", "bluetooth"])
    if code is None:
        return _result("Servicio Bluetooth", "unknown", "No se pudo consultar systemd; comprueba Bluetooth desde los ajustes gráficos.")
    if output == "active":
        return _result("Servicio Bluetooth", "ok", "El servicio Bluetooth está activo.")
    if output == "inactive":
        return _result("Servicio Bluetooth", "warning", "El servicio Bluetooth está detenido.")
    return _result("Servicio Bluetooth", "unknown", f"Estado informado: {output or 'no disponible'}. Puede que este equipo no tenga el servicio instalado.")


def _check_bluetooth_adapter() -> dict[str, str]:
    code, output = _run(["bluetoothctl", "show"])
    if code is None:
        return _result("Adaptador Bluetooth", "unknown", "bluetoothctl no está disponible o no se detectó un adaptador.")
    powered = re.search(r"^\s*Powered:\s*(yes|no)\s*$", output, re.IGNORECASE | re.MULTILINE)
    if not powered:
        return _result("Adaptador Bluetooth", "warning", "No se encontró un adaptador Bluetooth visible para el sistema.")
    is_on = powered.group(1).lower() == "yes"
    return _result("Adaptador Bluetooth", "ok" if is_on else "warning", "El adaptador está encendido." if is_on else "El adaptador está apagado; puedes encenderlo desde los ajustes gráficos.")


def _check_print_service() -> dict[str, str]:
    code, output = _run(["lpstat", "-r"])
    if code is None:
        return _result("Servicio de impresión", "unknown", "CUPS o lpstat no está disponible en este equipo.")
    running = "scheduler is running" in output.lower()
    return _result("Servicio de impresión", "ok" if running else "warning", "El planificador de impresión está activo." if running else "El planificador de impresión no está activo.")


def _check_printers() -> dict[str, str]:
    code, output = _run(["lpstat", "-p"])
    if code is None:
        return _result("Impresoras configuradas", "unknown", "No se pudo consultar la lista local de impresoras.")
    count = sum(line.startswith("printer ") for line in output.splitlines())
    return _result("Impresoras configuradas", "ok" if count else "warning", f"Hay {count} impresora(s) configurada(s)." if count else "No aparecen impresoras configuradas; añádela desde la configuración del sistema.")


def _check_disk_space() -> dict[str, str]:
    try:
        root = psutil.disk_usage("/")
        home = psutil.disk_usage(str(Path.home()))
    except OSError:
        return _result("Espacio disponible", "unknown", "No se pudo medir el espacio de almacenamiento.")
    free_gb = home.free / 1024**3
    used_pct = home.percent
    status = "warning" if free_gb < 2 or used_pct >= 90 else "ok"
    try:
        root_same = os.stat("/").st_dev == os.stat(Path.home()).st_dev
    except OSError:
        root_same = True
    detail = f"Tu carpeta personal tiene {free_gb:.1f} GB libres ({used_pct:.0f}% en uso)."
    if not root_same:
        detail += f" La raíz del sistema tiene {root.free / 1024**3:.1f} GB libres."
    if status == "warning":
        detail += " Haz una copia de los archivos importantes antes de liberar espacio."
    return _result("Espacio disponible", status, detail)


def _check_home_permissions(target_path: str = "") -> dict[str, str]:
    home = Path.home().resolve()
    raw = (target_path or "").strip()
    if not raw:
        path = home
    else:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = home / candidate
        try:
            path = candidate.resolve(strict=True)
            path.relative_to(home)
        except (OSError, ValueError, RuntimeError):
            return _result("Permisos de la ruta", "warning", "La ruta no existe o queda fuera de tu carpeta personal. Por seguridad, esta comprobación solo revisa archivos de tu usuario.")
    try:
        details = path.stat()
    except OSError:
        return _result("Permisos de la ruta", "warning", "No se pudo acceder a esa ruta. Comprueba que exista y vuelve a escribirla.")
    can_read = os.access(path, os.R_OK)
    can_write = os.access(path, os.W_OK)
    can_enter = os.access(path, os.X_OK) if path.is_dir() else True
    status = "ok" if can_read and can_write and can_enter else "warning"
    kind = "carpeta" if path.is_dir() else "archivo"
    detail = f"La {kind} existe; lectura: {'sí' if can_read else 'no'}, escritura: {'sí' if can_write else 'no'}"
    if path.is_dir():
        detail += f", acceso: {'sí' if can_enter else 'no'}"
    detail += f". Propietario actual: {'tu usuario' if details.st_uid == os.getuid() else 'otro usuario'}; modo: {details.st_mode & 0o777:04o}."
    return _result("Permisos de la ruta", status, detail)


def _check_application(application: str = "") -> dict[str, str]:
    name = (application or "").strip()
    if not name:
        return _result("Aplicación", "unknown", "Escribe el nombre del programa para buscarlo en este equipo.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,79}", name):
        return _result("Aplicación", "warning", "Usa solo el nombre del programa, sin rutas ni comandos.")
    binary = shutil.which(name)
    desktop_name = name[:-8] if name.lower().endswith(".desktop") else name
    desktop_dirs = (
        Path.home() / ".local/share/applications",
        Path("/usr/local/share/applications"),
        Path("/usr/share/applications"),
        Path("/var/lib/flatpak/exports/share/applications"),
    )
    desktop_found = any((directory / f"{desktop_name}.desktop").is_file() for directory in desktop_dirs)
    if binary or desktop_found:
        detail = "Se encontró un comando ejecutable." if binary else "Se encontró un lanzador de escritorio."
        detail += " La comprobación no abrió la aplicación."
        return _result("Aplicación", "ok", detail)
    return _result("Aplicación", "warning", "No se encontró un comando ni un lanzador con ese nombre. Puede tener otro nombre de paquete o no estar instalada.")


def _check_graphics_adapter() -> dict[str, str]:
    code, output = _run(["lspci"])
    if code is None:
        return _result("Adaptador gráfico", "unknown", "lspci no está disponible para consultar los dispositivos PCI.")
    rows = [line.strip() for line in output.splitlines() if re.search(r"VGA compatible controller|3D controller|Display controller", line, re.IGNORECASE)]
    if not rows:
        return _result("Adaptador gráfico", "warning", "lspci no mostró un controlador gráfico. Puede que este equipo no exponga el dispositivo por PCI.")
    models = [re.sub(r"^[^:]+:\s*", "", row)[:120] for row in rows[:2]]
    return _result("Adaptador gráfico", "ok", "Detectado: " + "; ".join(models))


def _check_failed_services() -> dict[str, str]:
    code, output = _run(["systemctl", "--failed", "--no-legend", "--plain", "--no-pager"])
    if code is None:
        return _result("Servicios del sistema", "unknown", "No se pudo consultar el estado de systemd.")
    if code != 0:
        return _result("Servicios del sistema", "unknown", "systemd no devolvió un estado verificable.")
    failed = [line for line in output.splitlines() if line.strip()]
    return _result("Servicios del sistema", "warning" if failed else "ok", f"Hay {len(failed)} servicio(s) fallido(s)." if failed else "No aparecen servicios fallidos.")


def _check_boot_time() -> dict[str, str]:
    code, output = _run(["systemd-analyze", "time"], timeout=8)
    if code is None:
        return _result("Tiempo de arranque", "unknown", "systemd-analyze no está disponible en este equipo.")
    if code != 0 or not output:
        return _result("Tiempo de arranque", "unknown", f"No se pudo medir el arranque actual ({output[:140] or 'sin datos'}).")
    first_line = output.splitlines()[0].strip()
    total_match = re.search(r"=\s*(?:(\d+)min\s*)?([0-9.]+)s\s*$", first_line)
    status = "ok"
    if total_match:
        minutes = int(total_match.group(1) or 0)
        seconds = float(total_match.group(2) or 0)
        if minutes * 60 + seconds > 45:
            status = "warning"
    return _result("Tiempo de arranque", status, first_line)


def _check_slow_boot_services() -> dict[str, str]:
    code, output = _run(["systemd-analyze", "blame", "--no-pager"], timeout=8)
    if code is None or code != 0:
        return _result("Servicios más lentos al iniciar", "unknown", "No se pudo consultar la lista de servicios del arranque.")
    entries = [line.strip() for line in output.splitlines() if line.strip()][:3]
    if not entries:
        return _result("Servicios más lentos al iniciar", "ok", "No se reportaron servicios lentos en el arranque.")
    has_slow = any("min" in item or (re.match(r"^([0-9.]+)s\b", item) and float(re.match(r"^([0-9.]+)s\b", item).group(1)) >= 12.0) for item in entries)
    return _result(
        "Servicios más lentos al iniciar",
        "warning" if has_slow else "ok",
        "Principales tiempos: " + " · ".join(entries),
    )


def _check_startup_apps_count() -> dict[str, str]:
    from src.gui.resource_monitor import _startup_apps
    apps = _startup_apps()
    enabled = [app["name"] for app in apps if app.get("enabled")]
    if not apps:
        return _result("Aplicaciones de autoinicio", "ok", "No hay accesos directos .desktop configurados en el inicio de sesión.")
    status = "warning" if len(enabled) >= 8 else "ok"
    sample = ", ".join(enabled[:4]) + ("…" if len(enabled) > 4 else "")
    detail = f"{len(enabled)} activa(s) de {len(apps)} detectada(s)" + (f": {sample}." if sample else ".")
    return _result("Aplicaciones de autoinicio", status, detail)


def run_problem_checks(issue_id: str, application: str = "", target_path: str = "") -> dict[str, Any]:
    """Ejecuta comprobaciones predefinidas para un problema seleccionado."""
    guide = _GUIDE_BY_ID.get(issue_id) if isinstance(issue_id, str) else None
    if guide is None:
        return {"success": False, "message": "Selecciona un problema de la lista."}
    application = application[:80] if isinstance(application, str) else ""
    target_path = target_path[:240] if isinstance(target_path, str) else ""

    checks: dict[str, Any] = {
        "connection": _check_connection,
        "gateway": _check_gateway,
        "dns": _check_dns,
        "audio_server": _check_audio_server,
        "audio_output": _check_audio_output,
        "bluetooth_service": _check_bluetooth_service,
        "bluetooth_adapter": _check_bluetooth_adapter,
        "print_service": _check_print_service,
        "configured_printers": _check_printers,
        "disk_space": _check_disk_space,
        "network": _check_network,
        "packages": _check_packages,
        "updates": _check_updates,
        "repositories": _check_repositories,
        "home_permissions": lambda: _check_home_permissions(target_path),
        "application_entry": lambda: _check_application(application),
        "graphics_adapter": _check_graphics_adapter,
        "failed_services": _check_failed_services,
        "boot_time": _check_boot_time,
        "slow_boot_services": _check_slow_boot_services,
        "startup_apps_count": _check_startup_apps_count,
    }
    selected = [checks[name] for name in guide["checks"]]
    with ThreadPoolExecutor(max_workers=min(5, len(selected))) as executor:
        results = list(executor.map(lambda check: check(), selected))
    return {"success": True, "results": results, "message": "Comprobaciones locales terminadas. No se cambió el sistema."}


def _clean_cache_command() -> str:
    try:
        from src.core.distro import detect_distro
        manager = detect_distro().native_package_manager
    except Exception:
        manager = "apt"
    commands = {
        "apt": "sudo apt autoremove -y && sudo apt clean",
        "dnf": "sudo dnf autoremove -y && sudo dnf clean all",
        "pacman": "sudo pacman -Sc",
        "zypper": "sudo zypper clean --all",
    }
    return commands.get(manager, commands["apt"])


def run_problem_action(action_id: str) -> dict[str, Any]:
    """Ejecuta una acción de reparación guiada tras la confirmación del usuario."""
    clean_id = (action_id or "").strip()
    if clean_id == "unmute_audio":
        if shutil.which("wpctl"):
            code1, _ = _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"])
            code2, _ = _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.75"])
            if code1 == 0 and code2 == 0:
                return {"success": True, "message": "Se activó la salida de audio predeterminada y se ajustó el volumen al 75%."}
        if shutil.which("pactl"):
            code1, _ = _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
            code2, _ = _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "75%"])
            if code1 == 0 and code2 == 0:
                return {"success": True, "message": "Se activó la salida de audio predeterminada y se ajustó el volumen al 75%."}
        return {"success": False, "message": "No se pudo cambiar el volumen automáticamente. Revisa los ajustes de Sonido del escritorio."}

    if clean_id == "restart_audio":
        if shutil.which("systemctl"):
            code, _ = _run(["systemctl", "--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"], timeout=10)
            if code == 0:
                return {"success": True, "message": "Se reiniciaron los servicios de audio (PipeWire / WirePlumber) de tu sesión."}
            code_pa, _ = _run(["systemctl", "--user", "restart", "pulseaudio"], timeout=10)
            if code_pa == 0:
                return {"success": True, "message": "Se reinició el servicio PulseAudio de tu sesión."}
        if shutil.which("pulseaudio"):
            code, _ = _run(["pulseaudio", "-k"], timeout=8)
            if code == 0:
                return {"success": True, "message": "Se reinició PulseAudio para tu sesión."}
        return {"success": False, "message": "No se pudo reiniciar el servidor de audio automáticamente."}

    terminal_actions: dict[str, tuple[str, str]] = {
        "restart_network": (
            "sudo systemctl restart NetworkManager",
            "Reiniciar NetworkManager — LinuxMate AI",
        ),
        "repair_bluetooth": (
            "sudo rfkill unblock bluetooth; sudo systemctl enable --now bluetooth && bluetoothctl power on",
            "Reparar Bluetooth — LinuxMate AI",
        ),
        "repair_cups": (
            "sudo systemctl enable --now cups && lpstat -r",
            "Activar servicio de impresión CUPS — LinuxMate AI",
        ),
        "clean_package_cache": (
            _clean_cache_command(),
            "Limpiar caché de paquetes — LinuxMate AI",
        ),
        "repair_packages": (
            _package_repair_command(),
            "Reparar paquetes — LinuxMate AI",
        ),
        "repair_home_permissions": (
            'sudo chown -R "$(id -un):$(id -gn)" "$HOME" && chmod u+rwx "$HOME"',
            "Restaurar permisos de carpeta personal — LinuxMate AI",
        ),
        "inspect_boot_blame": (
            "systemd-analyze time; echo ''; systemd-analyze blame --no-pager | head -n 20; echo ''; systemctl --failed --no-pager",
            "Diagnóstico de arranque — LinuxMate AI",
        ),
        "inspect_graphics_logs": (
            "lspci -nnk | grep -EA3 'VGA|3D|Display'; echo ''; journalctl -b -p 3 --no-pager | tail -n 30",
            "Controladores gráficos y errores — LinuxMate AI",
        ),
    }

    if clean_id not in terminal_actions:
        return {"success": False, "message": "Acción de reparación no reconocida."}

    command, title = terminal_actions[clean_id]
    ok, message = launch_in_terminal(command, title)
    if ok:
        return {
            "success": True,
            "message": "Se abrió una terminal con la reparación guiada. Revisa el resultado y vuelve a ejecutar las comprobaciones.",
        }
    return {"success": False, "message": f"No se pudo abrir la terminal: {message}"}

"""Comprobaciones locales y reparaciones guiadas para la interfaz web."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import configparser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import psutil

from src.core.tools import launch_in_terminal


def _run(args: list[str], timeout: int = 8) -> tuple[int | None, str]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
        return result.returncode, (result.stdout or result.stderr).strip()
    except (OSError, subprocess.SubprocessError):
        return None, ""


def _check_storage() -> dict[str, Any]:
    try:
        disk = shutil.disk_usage("/")
    except OSError:
        return {"id": "storage", "title": "Almacenamiento", "status": "unknown", "detail": "No se pudo leer el espacio del disco."}
    free_gb = disk.free / 1024 ** 3
    used_percent = disk.used / disk.total * 100 if disk.total else 0
    status = "warning" if free_gb < 2 or used_percent >= 90 else "ok"
    detail = f"{free_gb:.1f} GB libres; {used_percent:.0f}% del disco en uso."
    if status == "warning":
        detail += " Libera archivos antes de instalar o actualizar."
    return {"id": "storage", "title": "Almacenamiento", "status": status, "detail": detail}


def _check_memory() -> dict[str, Any]:
    try:
        memory = psutil.virtual_memory()
    except Exception:
        return {"id": "memory", "title": "Memoria", "status": "unknown", "detail": "No se pudo leer el estado de la memoria."}
    available_mb = memory.available / 1024 ** 2
    status = "warning" if memory.percent >= 90 and available_mb < 1024 else "ok"
    detail = f"{available_mb:.0f} MB disponibles; {memory.percent:.0f}% en uso."
    if status == "warning":
        detail += " Cierra aplicaciones que no estés usando."
    return {"id": "memory", "title": "Memoria", "status": status, "detail": detail}


def _check_cpu() -> dict[str, Any]:
    try:
        usage = psutil.cpu_percent(interval=0.25)
    except Exception:
        return {"id": "cpu", "title": "Procesador", "status": "unknown", "detail": "No se pudo medir el uso del procesador."}
    status = "warning" if usage >= 95 else "ok"
    detail = f"Uso durante una medición breve: {usage:.0f}%."
    if status == "warning":
        detail += " La carga es alta en este momento; vuelve a analizar si estabas abriendo aplicaciones."
    return {"id": "cpu", "title": "Procesador", "status": status, "detail": detail}


def _check_updates() -> dict[str, Any]:
    """Lists available updates from cached metadata; it never refreshes repositories."""
    from src.core.distro import detect_distro

    manager = detect_distro().native_package_manager
    commands = {
        "apt": (["apt", "list", "--upgradable"], 0),
        "dnf": (["dnf", "--cacheonly", "check-update"], 100),
        "pacman": (["pacman", "-Qu"], 0),
        "zypper": (["zypper", "--no-refresh", "list-updates"], 0),
    }
    entry = commands.get(manager)
    if not entry or not shutil.which(manager):
        return {
            "id": "updates", "title": "Actualizaciones", "status": "unknown",
            "detail": f"No hay una consulta local de actualizaciones configurada para {manager}.",
        }

    command, updates_exit_code = entry
    code, output = _run(command, timeout=18)
    if code is None or code not in (0, updates_exit_code):
        detail = "No se pudieron leer las actualizaciones con los datos guardados. Revisa los repositorios desde el gestor de tu distribución."
        return {"id": "updates", "title": "Actualizaciones", "status": "unknown", "detail": detail}

    if manager == "apt":
        count = sum("[upgradable from:" in line.lower() for line in output.splitlines())
    elif manager == "dnf":
        count = sum(
            bool(re.match(r"^\S+\.(?:x86_64|i\d86|aarch64|armv\w+|noarch|ppc64le|s390x)\s+\S+\s+\S+", line))
            for line in output.splitlines()
        )
    elif manager == "pacman":
        count = sum(bool(line.strip()) for line in output.splitlines())
    else:
        count = sum(bool(re.match(r"^\s*v\s*\|", line)) for line in output.splitlines())

    status = "warning" if count else "ok"
    if count:
        detail = f"Hay {count} actualización{'' if count == 1 else 'es'} disponible{'' if count == 1 else 's'} según los índices guardados."
    else:
        detail = "No aparecen actualizaciones en los índices guardados."
    detail += " LinuxMate no actualizó repositorios durante el diagnóstico; el resultado puede estar desactualizado."
    return {"id": "updates", "title": "Actualizaciones", "status": status, "detail": detail}


def _check_repositories() -> dict[str, Any]:
    """Checks local repository configuration without contacting remote servers."""
    from src.core.distro import detect_distro

    manager = detect_distro().native_package_manager
    if manager == "apt":
        files = [Path("/etc/apt/sources.list")]
        source_dir = Path("/etc/apt/sources.list.d")
        if source_dir.is_dir():
            files.extend(sorted(source_dir.glob("*.list")))
            files.extend(sorted(source_dir.glob("*.sources")))
        if not any(path.exists() for path in files):
            return {"id": "repositories", "title": "Repositorios", "status": "unknown", "detail": "No se encontraron archivos de fuentes de APT."}
        count = 0
        try:
            for path in files:
                if not path.is_file():
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
                if path.suffix == ".sources":
                    for block in re.split(r"\n\s*\n", content):
                        fields = {
                            match.group(1).lower(): match.group(2).strip()
                            for match in re.finditer(r"^(Types|URIs):\s*(.+)$", block, re.MULTILINE | re.IGNORECASE)
                        }
                        if fields.get("types") and fields.get("uris"):
                            count += 1
                else:
                    count += sum(
                        bool(re.match(r"^deb(?:-src)?\s+(?:\[[^\]]+\]\s+)?\S+:\S+\s+\S+", line.strip()))
                        for line in content.splitlines()
                        if line.strip() and not line.lstrip().startswith("#")
                    )
        except OSError:
            return {"id": "repositories", "title": "Repositorios", "status": "unknown", "detail": "No se pudieron leer las fuentes configuradas para APT."}
    elif manager in {"dnf", "zypper"}:
        directories = [Path("/etc/yum.repos.d"), Path("/etc/dnf/repos.d")] if manager == "dnf" else [Path("/etc/zypp/repos.d")]
        files = sorted({path for directory in directories if directory.is_dir() for path in directory.glob("*.repo")})
        if not files:
            return {"id": "repositories", "title": "Repositorios", "status": "warning", "detail": f"No se encontraron archivos de repositorio para {manager.upper()}."}
        count = 0
        try:
            for path in files:
                parser = configparser.ConfigParser(interpolation=None)
                parser.read(path, encoding="utf-8")
                for section in parser.sections():
                    if parser.get(section, "enabled", fallback="1").strip() == "0":
                        continue
                    keys = {key.lower() for key, _ in parser.items(section)}
                    if keys.intersection({"baseurl", "mirrorlist", "metalink"}):
                        count += 1
        except (OSError, configparser.Error):
            return {"id": "repositories", "title": "Repositorios", "status": "unknown", "detail": f"No se pudieron leer las fuentes configuradas para {manager.upper()}."}
    elif manager == "pacman":
        config_path = Path("/etc/pacman.conf")
        if not config_path.is_file():
            return {"id": "repositories", "title": "Repositorios", "status": "unknown", "detail": "No se encontró /etc/pacman.conf."}
        count = 0
        active_section = False
        try:
            for raw_line in config_path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                section = re.match(r"^\[([^]]+)\]$", line)
                if section:
                    active_section = section.group(1).lower() != "options"
                    continue
                if active_section and re.match(r"^(?:Server|Include)\s*=\s*\S+", line, re.IGNORECASE):
                    count += 1
        except OSError:
            return {"id": "repositories", "title": "Repositorios", "status": "unknown", "detail": "No se pudo leer /etc/pacman.conf."}
    else:
        return {"id": "repositories", "title": "Repositorios", "status": "unknown", "detail": f"No hay una comprobación de fuentes configurada para {manager}."}

    if count == 0:
        return {
            "id": "repositories", "title": "Repositorios", "status": "warning",
            "detail": f"No se detectaron fuentes activas de paquetes para {manager.upper()}. Revisa la configuración de repositorios.",
        }
    return {
        "id": "repositories", "title": "Repositorios", "status": "ok",
        "detail": f"Se detectaron {count} fuente{'' if count == 1 else 's'} configurada{'' if count == 1 else 's'} para {manager.upper()}. No se comprobó la conexión ni la firma de los servidores.",
    }


def _check_battery() -> dict[str, Any]:
    try:
        battery = psutil.sensors_battery()
    except Exception:
        battery = None
    if battery is None:
        return {"id": "battery", "title": "Batería", "status": "unknown", "detail": "No se detectó una batería o el equipo no expone ese sensor."}
    percent = max(0, min(100, int(round(battery.percent))))
    plugged = battery.power_plugged
    state = "conectada a corriente" if plugged is True else "usando batería" if plugged is False else "estado de corriente desconocido"
    status = "warning" if percent <= 15 and plugged is False else "ok"
    detail = f"Carga: {percent}%; {state}."
    if status == "warning":
        detail += " Conecta el equipo a la corriente pronto."
    return {"id": "battery", "title": "Batería", "status": status, "detail": detail}


def _check_temperature() -> dict[str, Any]:
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False)
    except Exception:
        sensors = {}
    readings = [
        (sensor.label or name, sensor.current)
        for name, entries in (sensors or {}).items()
        for sensor in entries
        if sensor.current is not None
    ]
    if not readings:
        return {"id": "temperature", "title": "Temperatura", "status": "unknown", "detail": "No hay un sensor de temperatura disponible en este equipo."}
    label, highest = max(readings, key=lambda item: item[1])
    status = "warning" if highest >= 90 else "ok"
    detail = f"Lectura más alta: {highest:.0f} °C ({label})."
    if status == "warning":
        detail += " Comprueba la ventilación y evita bloquear las salidas de aire."
    return {"id": "temperature", "title": "Temperatura", "status": status, "detail": detail}


def _check_permissions() -> dict[str, Any]:
    home = Path.home()
    if not os.access(home, os.R_OK | os.W_OK | os.X_OK):
        return {
            "id": "permissions", "title": "Permisos básicos", "status": "warning",
            "detail": f"El usuario actual no puede leer, escribir y entrar a {home}.",
        }
    return {
        "id": "permissions", "title": "Permisos básicos", "status": "ok",
        "detail": "El usuario actual puede leer, escribir y acceder a su carpeta personal.",
    }


def _check_packages() -> dict[str, Any]:
    from src.core.distro import detect_distro
    manager = detect_distro().native_package_manager
    if manager == "apt":
        if not shutil.which("dpkg") or not shutil.which("apt-get"):
            return {"id": "packages", "title": "Paquetes", "status": "unknown", "detail": "APT y DPKG no están disponibles en este equipo."}
        audit_code, audit_output = _run(["dpkg", "--audit"], timeout=8)
        repair_code, repair_output = _run(["apt-get", "-s", "-f", "install"], timeout=12)
        if audit_code is None or repair_code is None:
            return {"id": "packages", "title": "Paquetes", "status": "unknown", "detail": "No se pudo completar la comprobación de paquetes."}
        if repair_code != 0 and ("Unable to acquire" in repair_output or "Permission denied" in repair_output):
            return {"id": "packages", "title": "Paquetes", "status": "unknown", "detail": "No se pudo consultar APT por falta de permisos."}
        planned_changes = any(line.startswith(("Inst ", "Remv ")) for line in repair_output.splitlines())
        if audit_code != 0 or audit_output or repair_code != 0 or planned_changes:
            detail = "DPKG detectó instalaciones incompletas." if audit_output or audit_code != 0 else "APT detectó dependencias que requieren atención."
            if repair_output and repair_code != 0:
                detail += " " + repair_output.splitlines()[-1][:180]
            return {
                "id": "packages", "title": "Paquetes", "status": "warning", "detail": detail,
                "action": {"id": "repair_packages", "label": "Reparar paquetes"},
            }
        return {"id": "packages", "title": "Paquetes", "status": "ok", "detail": "DPKG y las dependencias de APT no reportan errores."}

    checks = {
        "dnf": (["dnf", "check"], "DNF"),
        "pacman": (["pacman", "-Dk"], "Pacman"),
        "zypper": (["zypper", "verify", "--dry-run"], "Zypper"),
    }
    if manager not in checks:
        return {"id": "packages", "title": "Paquetes", "status": "unknown", "detail": f"No hay una comprobación de dependencias configurada para {manager}."}
    command, label = checks[manager]
    if not shutil.which(manager):
        return {"id": "packages", "title": "Paquetes", "status": "unknown", "detail": f"{label} no está disponible en este equipo."}
    code, output = _run(command, timeout=20)
    if code is None:
        return {"id": "packages", "title": "Paquetes", "status": "unknown", "detail": f"No se pudo completar la comprobación de {label}."}
    if code != 0:
        return {
            "id": "packages",
            "title": "Paquetes",
            "status": "warning",
            "detail": f"{label} encontró un problema. {output[:180]}".strip(),
            "action": {"id": "repair_packages", "label": "Reparar paquetes"},
        }
    return {"id": "packages", "title": "Paquetes", "status": "ok", "detail": f"{label} no reporta problemas de dependencias."}


def _check_services() -> dict[str, Any]:
    if not shutil.which("systemctl"):
        return {"id": "services", "title": "Servicios", "status": "unknown", "detail": "Systemd no está disponible."}
    code, output = _run(["systemctl", "--failed", "--no-legend", "--plain", "--no-pager"], timeout=8)
    if code != 0:
        return {"id": "services", "title": "Servicios", "status": "unknown", "detail": "No se pudo consultar el estado de los servicios."}
    units = [line.split()[0] for line in output.splitlines() if line.strip()]
    if units:
        names = ", ".join(units[:4]) + ("…" if len(units) > 4 else "")
        return {
            "id": "services", "title": "Servicios", "status": "warning",
            "detail": f"{len(units)} servicio(s) fallidos: {names}.",
            "action": {"id": "inspect_services", "label": "Ver errores"},
        }
    return {"id": "services", "title": "Servicios", "status": "ok", "detail": "No hay servicios del sistema en estado fallido."}


def _check_network() -> dict[str, Any]:
    if not shutil.which("ip"):
        return {"id": "network", "title": "Red", "status": "unknown", "detail": "No se pudo consultar la ruta de red."}
    route_code, route = _run(["ip", "route", "show", "default"], timeout=5)
    if route_code != 0:
        return {"id": "network", "title": "Red", "status": "unknown", "detail": "No se pudo consultar la ruta de red."}
    if not route:
        detail = "No hay ruta de salida a Internet. Revisa Wi-Fi o el cable de red."
        status = "warning"
    elif shutil.which("getent"):
        dns_code, _ = _run(["getent", "ahostsv4", "example.com"], timeout=5)
        status = "ok" if dns_code == 0 else ("unknown" if dns_code is None else "warning")
        detail = {
            "ok": "Hay ruta de red y la resolución DNS responde.",
            "warning": "Hay ruta de red, pero la resolución DNS no respondió. Comprueba tu conexión.",
            "unknown": "Hay ruta de red; no se pudo comprobar DNS.",
        }[status]
    else:
        status = "unknown"
        detail = "Hay ruta de red; no se pudo comprobar DNS."
    result: dict[str, Any] = {"id": "network", "title": "Red", "status": status, "detail": detail}
    if status == "warning" and shutil.which("systemctl"):
        manager_code, manager_state = _run(["systemctl", "is-active", "NetworkManager"], timeout=5)
        if manager_code == 0 and manager_state == "active":
            result["action"] = {"id": "restart_network", "label": "Reiniciar red"}
    return result


def diagnose_system() -> dict[str, Any]:
    checks = (
        _check_storage,
        _check_memory,
        _check_cpu,
        _check_packages,
        _check_updates,
        _check_repositories,
        _check_services,
        _check_network,
        _check_permissions,
        _check_battery,
        _check_temperature,
    )
    with ThreadPoolExecutor(max_workers=len(checks)) as executor:
        results = list(executor.map(lambda check: check(), checks))
    problems = sum(check["status"] == "warning" for check in results)
    unknown = sum(check["status"] == "unknown" for check in results)
    return {"checks": results, "problems": problems, "unknown": unknown}


def _package_repair_command() -> str:
    try:
        from src.core.distro import detect_distro
        manager = detect_distro().native_package_manager
    except Exception:
        manager = "apt"
    commands = {
        "apt": "sudo dpkg --configure -a && sudo apt --fix-broken install",
        "dnf": "sudo dnf check && sudo dnf distro-sync",
        "pacman": "sudo pacman -Syyu",
        "zypper": "sudo zypper verify",
    }
    return commands.get(manager, commands["apt"])


def run_diagnostic_fix(action_id: str) -> dict[str, Any]:
    if action_id == "repair_packages":
        if _check_packages().get("action", {}).get("id") != action_id:
            return {"success": False, "message": "No hay un problema de paquetes confirmado que reparar."}
        command = _package_repair_command()
        title = "Reparar paquetes — LinuxMate AI"
    elif action_id == "restart_network":
        if _check_network().get("action", {}).get("id") != action_id:
            return {"success": False, "message": "No se confirmó un problema de red que requiera reiniciar NetworkManager."}
        command = "sudo systemctl restart NetworkManager"
        title = "Reiniciar red — LinuxMate AI"
    elif action_id == "inspect_services":
        command = "systemctl --failed --no-pager; journalctl -p 3 -b -n 80 --no-pager"
        title = "Errores del sistema — LinuxMate AI"
    else:
        return {"success": False, "message": "Acción de diagnóstico no reconocida."}

    ok, message = launch_in_terminal(command, title)
    if ok:
        return {"success": True, "message": "Se abrió una terminal con la acción seleccionada. Revisa el resultado y vuelve a analizar."}
    return {"success": False, "message": f"No se pudo abrir la terminal: {message}"}

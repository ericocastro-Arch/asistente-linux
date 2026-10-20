"""Lecturas locales del monitor de recursos para la interfaz de LinuxMate."""

from __future__ import annotations

import configparser
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil


_MAX_DISKS = 10
_MAX_PROCESSES = 8
_MAX_STARTUP_APPS = 20
_network_lock = threading.Lock()
_network_previous: dict[str, tuple[int, int]] | None = None
_network_previous_at = 0.0


def _temperature_readings() -> list[dict[str, Any]]:
    """Devuelve solo temperaturas reales que psutil exponga en este equipo."""
    readings: list[dict[str, Any]] = []
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False)
    except (AttributeError, OSError, psutil.Error):
        return readings

    for sensor_name, entries in (sensors or {}).items():
        for entry in entries:
            current = getattr(entry, "current", None)
            if current is None:
                continue
            try:
                value = float(current)
            except (TypeError, ValueError):
                continue
            if not (-20 <= value <= 150):
                continue
            label = str(getattr(entry, "label", "") or sensor_name).strip()
            high = getattr(entry, "high", None)
            critical = getattr(entry, "critical", None)
            readings.append({
                "sensor": str(sensor_name),
                "label": label[:80],
                "celsius": round(value, 1),
                "high": round(float(high), 1) if isinstance(high, (int, float)) else None,
                "critical": round(float(critical), 1) if isinstance(critical, (int, float)) else None,
            })
    readings.sort(key=lambda item: item["celsius"], reverse=True)
    return readings[:12]


def get_cpu_temperature() -> float | None:
    """Selecciona una lectura identificada por el sensor como temperatura de CPU."""
    cpu_readings = [
        item["celsius"] for item in _temperature_readings()
        if any(token in f"{item['sensor']} {item['label']}".casefold() for token in ("cpu", "core", "package", "k10temp", "zenpower", "coretemp"))
    ]
    return max(cpu_readings) if cpu_readings else None


def _network_rates() -> dict[str, Any]:
    """Calcula velocidades aproximadas entre dos consultas locales."""
    global _network_previous, _network_previous_at
    try:
        counters = psutil.net_io_counters(pernic=True, nowrap=True) or {}
        current = {
            name: (int(counter.bytes_recv), int(counter.bytes_sent))
            for name, counter in counters.items()
            if name != "lo"
        }
    except (OSError, psutil.Error):
        return {"download_bytes_sec": None, "upload_bytes_sec": None, "sampled": False, "interfaces": 0}

    now = time.monotonic()
    with _network_lock:
        previous = _network_previous
        elapsed = now - _network_previous_at if _network_previous_at else 0
        _network_previous = current
        _network_previous_at = now

    if previous is None or elapsed <= 0:
        return {"download_bytes_sec": 0, "upload_bytes_sec": 0, "sampled": False, "interfaces": len(current)}
    received = sum(max(0, pair[0] - previous.get(name, pair)[0]) for name, pair in current.items())
    sent = sum(max(0, pair[1] - previous.get(name, pair)[1]) for name, pair in current.items())
    return {
        "download_bytes_sec": round(received / elapsed),
        "upload_bytes_sec": round(sent / elapsed),
        "sampled": True,
        "interfaces": len(current),
    }


def _disk_overview() -> list[dict[str, Any]]:
    virtual_fs = {"autofs", "binfmt_misc", "cgroup", "cgroup2", "configfs", "debugfs", "devpts", "devtmpfs", "fusectl", "mqueue", "overlay", "proc", "pstore", "securityfs", "sysfs", "tmpfs", "tracefs"}
    home = Path.home()
    results: list[dict[str, Any]] = []
    seen_mounts: set[str] = set()
    try:
        partitions = psutil.disk_partitions(all=False)
    except (OSError, psutil.Error):
        partitions = []

    for partition in partitions:
        mountpoint = str(partition.mountpoint or "")
        if not mountpoint or mountpoint in seen_mounts or partition.fstype.lower() in virtual_fs:
            continue
        seen_mounts.add(mountpoint)
        try:
            usage = psutil.disk_usage(mountpoint)
        except (OSError, PermissionError, psutil.Error):
            continue
        display_mount = mountpoint
        try:
            relative = Path(mountpoint).relative_to(home)
            display_mount = "~" if str(relative) == "." else f"~/{relative.as_posix()}"
        except ValueError:
            pass
        label = "Sistema" if mountpoint == "/" else ("Carpeta personal" if mountpoint == str(home) else "Unidad montada")
        results.append({
            "mountpoint": display_mount,
            "label": label,
            "filesystem": str(partition.fstype or "desconocido")[:24],
            "total_bytes": int(usage.total),
            "used_bytes": int(usage.used),
            "free_bytes": int(usage.free),
            "percent": round(float(usage.percent), 1),
        })
    results.sort(key=lambda item: (item["mountpoint"] != "/", item["mountpoint"].casefold()))
    return results[:_MAX_DISKS]


def _battery_overview() -> dict[str, Any]:
    """Consulta el estado de la batería local mediante psutil o /sys/class/power_supply."""
    try:
        battery = psutil.sensors_battery()
    except (AttributeError, OSError, psutil.Error):
        battery = None

    if battery is not None and battery.percent is not None:
        percent = round(float(battery.percent), 1)
        plugged = bool(battery.power_plugged) if battery.power_plugged is not None else None
        secsleft = int(battery.secsleft) if isinstance(battery.secsleft, (int, float)) and battery.secsleft > 0 else None
        if plugged is True:
            status = "Completa" if percent >= 99.0 else "Cargando"
        elif plugged is False:
            status = "Descargando"
        else:
            status = "Detectada"
        if secsleft and secsleft < 86400 * 2:
            hours, remainder = divmod(secsleft, 3600)
            minutes = remainder // 60
            detail = f"Tiempo estimado: {hours} h {minutes} min" if hours else f"Tiempo estimado: {minutes} min"
        elif plugged is True:
            detail = "Conectado a la corriente"
        else:
            detail = "Con energía de batería"
        return {
            "present": True,
            "percent": percent,
            "power_plugged": plugged,
            "status": status,
            "secsleft": secsleft,
            "detail": detail,
        }

    power_root = Path("/sys/class/power_supply")
    try:
        supplies = sorted(power_root.glob("BAT*")) if power_root.exists() else []
    except OSError:
        supplies = []
    for supply in supplies:
        try:
            capacity_text = (supply / "capacity").read_text(encoding="utf-8", errors="ignore").strip()
            raw_status = (supply / "status").read_text(encoding="utf-8", errors="ignore").strip().lower()
            percent = round(float(capacity_text), 1)
        except (OSError, ValueError):
            continue
        status_map = {
            "charging": "Cargando",
            "discharging": "Descargando",
            "full": "Completa",
            "not charging": "Conectada",
        }
        plugged = raw_status in {"charging", "full", "not charging"}
        status = status_map.get(raw_status, "Detectada")
        return {
            "present": True,
            "percent": percent,
            "power_plugged": plugged,
            "status": status,
            "secsleft": None,
            "detail": f"{supply.name} · {'Conectado a corriente' if plugged else 'Usando batería'}",
        }

    return {
        "present": False,
        "percent": None,
        "power_plugged": True,
        "status": "Corriente directa",
        "secsleft": None,
        "detail": "Equipo de escritorio o sin batería detectada.",
    }


def _process_overview() -> dict[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    current_uid = os.getuid() if hasattr(os, "getuid") else -1
    protected_pids = {os.getpid(), os.getppid(), 1}
    try:
        iterator = psutil.process_iter(attrs=["pid", "name", "memory_percent", "memory_info", "uids"])
        for process in iterator:
            try:
                info = process.info
                pid = int(info.get("pid") or 0)
                name = str(info.get("name") or "Proceso sin nombre").strip()
                memory_info = info.get("memory_info")
                memory_bytes = int(memory_info.rss) if memory_info else 0
                uids = info.get("uids")
                owner_uid = int(getattr(uids, "real", -2)) if uids is not None else -2
                can_stop = pid > 1 and pid not in protected_pids and owner_uid == current_uid
                rows.append({
                    "pid": pid,
                    "name": name[:100],
                    "cpu_percent": round(float(process.cpu_percent(interval=None)), 1),
                    "memory_percent": round(float(info.get("memory_percent") or 0), 1),
                    "memory_bytes": memory_bytes,
                    "can_stop": can_stop,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError, TypeError, ValueError):
                continue
    except (OSError, psutil.Error):
        pass

    top_cpu = sorted(rows, key=lambda item: (item["cpu_percent"], item["memory_bytes"]), reverse=True)[:_MAX_PROCESSES]
    top_memory = sorted(rows, key=lambda item: (item["memory_bytes"], item["cpu_percent"]), reverse=True)[:_MAX_PROCESSES]
    return {"top_cpu": top_cpu, "top_memory": top_memory}


def _autostart_dirs() -> tuple[Path, list[Path]]:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    system_dirs = [Path(item) for item in os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg").split(os.pathsep) if item]
    return config_home, [config_home, *system_dirs]


def _startup_apps() -> list[dict[str, Any]]:
    """Lee nombres y estado de accesos directos .desktop de autoinicio."""
    _, config_dirs = _autostart_dirs()
    found: dict[str, dict[str, Any]] = {}
    seen_keys: set[str] = set()
    for scope, config_dir in enumerate(config_dirs):
        folder = config_dir / "autostart"
        try:
            entries = sorted(folder.glob("*.desktop"))
        except OSError:
            continue
        for entry in entries:
            key = entry.name.casefold()
            if key in seen_keys or not entry.is_file():
                continue
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                parser.read(entry, encoding="utf-8")
                section = parser["Desktop Entry"]
            except (OSError, configparser.Error, KeyError):
                continue
            seen_keys.add(key)
            hidden = section.get("hidden", "false").strip().lower() in {"true", "1", "yes"}
            if hidden and scope > 0:
                continue
            gnome_enabled = section.get("x-gnome-autostart-enabled", "true").strip().lower() not in {"false", "0", "no"}
            enabled = (not hidden) and gnome_enabled
            name = section.get("name[es]", "").strip() or section.get("name", "").strip() or entry.stem
            found[key] = {
                "id": entry.name,
                "name": name[:100],
                "enabled": enabled,
                "scope": "Usuario" if scope == 0 else "Sistema",
            }

    return sorted(found.values(), key=lambda item: (not item["enabled"], item["name"].casefold()))[:_MAX_STARTUP_APPS]


def toggle_startup_app(desktop_id: str, enabled: bool) -> dict[str, Any]:
    """Activa o desactiva una aplicación de inicio en ~/.config/autostart."""
    clean_id = (desktop_id or "").strip()
    if (
        not clean_id.endswith(".desktop")
        or Path(clean_id).name != clean_id
        or "/" in clean_id
        or "\\" in clean_id
        or ".." in clean_id
    ):
        return {"success": False, "message": "Identificador de aplicación de inicio no válido."}

    config_home, config_dirs = _autostart_dirs()
    user_autostart = config_home / "autostart"
    target_path = user_autostart / clean_id
    source_path: Path | None = None
    for config_dir in config_dirs:
        candidate = config_dir / "autostart" / clean_id
        if candidate.is_file() and not candidate.is_symlink():
            source_path = candidate
            break
    if source_path is None:
        return {"success": False, "message": "No se encontró el acceso de inicio seleccionado."}

    try:
        raw_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"success": False, "message": f"No se pudo leer el archivo de inicio: {exc}"}

    desired_enabled = "true" if bool(enabled) else "false"
    lines = raw_text.splitlines()
    updated_lines: list[str] = []
    in_desktop_entry = False
    wrote_enabled = False
    wrote_hidden = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_desktop_entry:
                if not wrote_enabled:
                    updated_lines.append(f"X-GNOME-Autostart-enabled={desired_enabled}")
                    wrote_enabled = True
                if not wrote_hidden:
                    updated_lines.append("Hidden=false")
                    wrote_hidden = True
            in_desktop_entry = stripped == "[Desktop Entry]"
            updated_lines.append(line)
            continue
        if in_desktop_entry and "=" in stripped and not stripped.startswith("#"):
            key_part = stripped.split("=", 1)[0].strip().lower()
            if key_part == "x-gnome-autostart-enabled":
                updated_lines.append(f"X-GNOME-Autostart-enabled={desired_enabled}")
                wrote_enabled = True
                continue
            if key_part == "hidden":
                updated_lines.append("Hidden=false")
                wrote_hidden = True
                continue
        updated_lines.append(line)

    if in_desktop_entry:
        if not wrote_enabled:
            updated_lines.append(f"X-GNOME-Autostart-enabled={desired_enabled}")
        if not wrote_hidden:
            updated_lines.append("Hidden=false")

    try:
        user_autostart.mkdir(parents=True, exist_ok=True)
        target_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"success": False, "message": f"No se pudo guardar la preferencia de inicio: {exc}"}

    state_label = "activada" if enabled else "desactivada"
    return {
        "success": True,
        "id": clean_id,
        "enabled": bool(enabled),
        "message": f"Aplicación de inicio {state_label} para tu usuario.",
        "startup_apps": _startup_apps(),
    }


def stop_user_process(pid: int) -> dict[str, Any]:
    """Envía SIGTERM a un proceso perteneciente al usuario actual."""
    try:
        target_pid = int(pid)
    except (TypeError, ValueError):
        return {"success": False, "message": "Identificador de proceso (PID) no válido."}

    if target_pid <= 1 or target_pid in {os.getpid(), os.getppid()}:
        return {"success": False, "message": "Por seguridad, no se puede finalizar este proceso."}

    try:
        proc = psutil.Process(target_pid)
        name = str(proc.name() or f"PID {target_pid}")
        current_uid = os.getuid() if hasattr(os, "getuid") else -1
        uids = proc.uids() if hasattr(proc, "uids") else None
        if uids is not None and int(uids.real) != current_uid:
            return {"success": False, "message": "Solo se pueden finalizar procesos iniciados por tu usuario."}
        proc.terminate()
    except psutil.NoSuchProcess:
        return {"success": False, "message": "El proceso ya no está en ejecución."}
    except (psutil.AccessDenied, PermissionError):
        return {"success": False, "message": "No tienes permisos para finalizar este proceso."}
    except (OSError, psutil.Error) as exc:
        return {"success": False, "message": f"No se pudo finalizar el proceso: {exc}"}

    return {
        "success": True,
        "pid": target_pid,
        "message": f"Se solicitó cerrar el proceso {name} (PID {target_pid}).",
    }


def get_resource_overview() -> dict[str, Any]:
    """Obtiene una instantánea de recursos; solo consulta datos locales de lectura."""
    try:
        cpu_percent = round(float(psutil.cpu_percent(interval=0.12)), 1)
        cpu_count = int(psutil.cpu_count(logical=True) or 0)
        frequency = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        process_count = len(psutil.pids())
        load_average = tuple(round(float(value), 2) for value in os.getloadavg())
    except (OSError, psutil.Error, AttributeError):
        cpu_percent = 0.0
        cpu_count = int(psutil.cpu_count(logical=True) or 0)
        frequency = None
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        process_count = 0
        load_average = ()

    try:
        cpu_frequency_mhz = round(float(frequency.current), 0) if frequency and frequency.current else None
    except (AttributeError, TypeError, ValueError):
        cpu_frequency_mhz = None

    return {
        "success": True,
        "sampled_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "cpu": {"percent": cpu_percent, "logical_cores": cpu_count, "frequency_mhz": cpu_frequency_mhz, "load_average": list(load_average)},
        "memory": {
            "percent": round(float(memory.percent), 1),
            "total_bytes": int(memory.total),
            "used_bytes": int(memory.used),
            "available_bytes": int(memory.available),
        },
        "swap": {"percent": round(float(swap.percent), 1), "total_bytes": int(swap.total), "used_bytes": int(swap.used), "free_bytes": int(swap.free)},
        "battery": _battery_overview(),
        "disks": _disk_overview(),
        "network": _network_rates(),
        "temperatures": _temperature_readings(),
        "processes": _process_overview(),
        "process_count": process_count,
        "startup_apps": _startup_apps(),
    }

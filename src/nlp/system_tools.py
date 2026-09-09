"""Herramientas locales del sistema Linux."""

import os
import re
import shutil
import subprocess
from datetime import datetime


def _run_read_only(args: list[str], timeout: int = 5) -> tuple[int | None, str, str]:
    """Ejecuta una consulta local sin shell y conserva salida y codigo de retorno."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "", str(exc)


def get_current_time_date() -> str:
    """Devuelve la fecha y hora actual en formato amigable en español."""
    now = datetime.now()
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    dia_semana = dias[now.weekday()]
    mes = meses[now.month - 1]
    hora = now.strftime("%H:%M:%S")
    return f"🕒 Son las {hora} del {dia_semana}, {now.day} de {mes} de {now.year}."


def get_system_status() -> str:
    """Devuelve un informe de recursos del sistema Linux (RAM, Disco, CPU, Kernel)."""
    # Memoria RAM
    mem_total_mb = 0
    mem_avail_mb = 0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total_mb = int(line.split()[1]) // 1024
                elif line.startswith("MemAvailable:"):
                    mem_avail_mb = int(line.split()[1]) // 1024
        mem_used_mb = mem_total_mb - mem_avail_mb
        mem_pct = (mem_used_mb / mem_total_mb * 100) if mem_total_mb else 0
        mem_str = f"• RAM: {mem_used_mb} MB / {mem_total_mb} MB ({mem_pct:.1f}% en uso)"
    except Exception:
        mem_str = "• RAM: No se pudo leer /proc/meminfo"

    # Espacio en Disco
    try:
        disk = shutil.disk_usage("/")
        total_gb = disk.total / (1024 ** 3)
        used_gb = disk.used / (1024 ** 3)
        free_gb = disk.free / (1024 ** 3)
        pct_disk = (disk.used / disk.total) * 100
        disk_str = f"• Disco (/): {used_gb:.1f} GB usados de {total_gb:.1f} GB ({pct_disk:.1f}% usado, {free_gb:.1f} GB libres)"
    except Exception:
        disk_str = "• Disco: No disponible"

    # Kernel y SO
    try:
        uname = os.uname()
        os_str = f"• Sistema: {uname.sysname} {uname.release} ({uname.machine})"
    except Exception:
        os_str = "• Sistema: Linux"

    # Uptime
    uptime_str = ""
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as f:
            uptime_seconds = float(f.readline().split()[0])
            horas = int(uptime_seconds // 3600)
            minutos = int((uptime_seconds % 3600) // 60)
            uptime_str = f"• Tiempo encendido: {horas} horas, {minutos} minutos"
    except Exception:
        pass

    lines = [
        "📊 Estado actual de tu sistema Linux:",
        os_str,
        mem_str,
        disk_str,
    ]
    if uptime_str:
        lines.append(uptime_str)

    return "\n".join(lines)


def get_performance_diagnostic() -> str:
    """Explica causas probables de lentitud usando metricas locales de solo lectura."""
    findings: list[str] = []
    recommendations: list[str] = []

    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as mem_file:
            memory = {
                parts[0].rstrip(":"): int(parts[1])
                for line in mem_file
                if len(parts := line.split()) >= 2 and parts[1].isdigit()
            }
        total_kb = memory.get("MemTotal", 0)
        available_kb = memory.get("MemAvailable", 0)
        memory_pct = ((total_kb - available_kb) / total_kb * 100) if total_kb else 0
        findings.append(f"RAM en uso: {memory_pct:.1f}% ({available_kb // 1024} MB disponibles).")
        if memory_pct >= 85:
            recommendations.append("La memoria esta muy ocupada; revisa y cierra aplicaciones que no uses.")
    except OSError:
        findings.append("No se pudo leer el estado de la memoria.")

    try:
        load_1, load_5, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        load_pct = load_1 / cpu_count * 100
        findings.append(f"Carga de CPU: {load_1:.2f} ahora y {load_5:.2f} a 5 min ({cpu_count} nucleos).")
        if load_pct >= 100:
            recommendations.append("La CPU esta saturada; identifica el proceso que mas CPU consume.")
    except OSError:
        findings.append("No se pudo leer la carga de CPU.")

    try:
        disk = shutil.disk_usage("/")
        disk_pct = disk.used / disk.total * 100
        findings.append(f"Disco raiz en uso: {disk_pct:.1f}% ({disk.free / 1024 ** 3:.1f} GB libres).")
        if disk_pct >= 90:
            recommendations.append("El disco tiene poco espacio; libera archivos antes de actualizar o instalar.")
    except OSError:
        findings.append("No se pudo leer el uso del disco.")

    code, output, _ = _run_read_only(
        ["ps", "-eo", "comm=,%cpu=,%mem=", "--sort=-%cpu"],
    )
    if code == 0 and output:
        processes = [line.strip() for line in output.splitlines()[:5] if line.strip()]
        if processes:
            findings.append("Procesos con mayor CPU: " + "; ".join(processes) + ".")

    if not recommendations:
        recommendations.append(
            "No detecte una saturacion evidente en esta lectura. Observa los procesos mientras ocurre la lentitud."
        )

    return "\n".join([
        "Diagnostico local de rendimiento:",
        *(f"- {item}" for item in findings),
        "",
        "Recomendacion:",
        *(f"- {item}" for item in recommendations),
        "",
        "Comandos equivalentes consultados: `free`, `uptime`, `df` y `ps`.",
        "No se modifico el sistema.",
    ])


def get_network_diagnostic() -> str:
    """Comprueba interfaz, ruta y acceso IP/DNS sin modificar la configuracion."""
    checks: list[str] = []
    recommendations: list[str] = []

    ip_code, ip_output, _ = _run_read_only(["ip", "-brief", "address"])
    active_interfaces = []
    if ip_code == 0:
        active_interfaces = [
            line for line in ip_output.splitlines()
            if " UP " in f" {line} " and not line.startswith("lo ")
        ]
        checks.append(
            "Interfaz activa: " + "; ".join(active_interfaces)
            if active_interfaces else "No se encontro una interfaz de red activa."
        )
    else:
        checks.append("No se pudo consultar las interfaces con `ip`.")

    route_code, route_output, _ = _run_read_only(["ip", "route", "show", "default"])
    has_route = route_code == 0 and bool(route_output)
    checks.append("Ruta predeterminada: disponible." if has_route else "Ruta predeterminada: no encontrada.")

    ping_ip_code, _, _ = _run_read_only(["ping", "-c", "1", "-W", "2", "1.1.1.1"], timeout=4)
    ip_reachable = ping_ip_code == 0
    checks.append("Acceso a Internet por IP: correcto." if ip_reachable else "Acceso a Internet por IP: sin respuesta.")

    ping_dns_code, _, _ = _run_read_only(["ping", "-c", "1", "-W", "2", "example.com"], timeout=4)
    dns_reachable = ping_dns_code == 0
    checks.append("Resolucion DNS: correcta." if dns_reachable else "Resolucion DNS: sin respuesta.")

    if not active_interfaces:
        recommendations.append("Activa Wi-Fi o conecta el cable de red y vuelve a probar.")
    elif not has_route:
        recommendations.append("La interfaz esta activa pero no tiene puerta de enlace; reconecta la red.")
    elif not ip_reachable:
        recommendations.append("Hay red local, pero no salida a Internet; revisa el router o proveedor.")
    elif not dns_reachable:
        recommendations.append("Internet responde por IP, pero falla DNS; revisa la configuracion DNS.")
    else:
        recommendations.append("La conectividad basica funciona; el problema puede estar en una aplicacion o sitio concreto.")

    return "\n".join([
        "Diagnostico local de red:",
        *(f"- {item}" for item in checks),
        "",
        "Recomendacion:",
        *(f"- {item}" for item in recommendations),
        "",
        "Comandos equivalentes consultados: `ip address`, `ip route` y `ping`.",
        "No se modifico la configuracion de red.",
    ])


def _format_temperature(value: float) -> str:
    return f"{value:.1f} °C"


def _read_cpu_temperatures_from_sysfs() -> list[tuple[str, float]]:
    readings: list[tuple[str, float]] = []
    thermal_root = "/sys/class/thermal"
    try:
        thermal_zones = sorted(
            name for name in os.listdir(thermal_root) if name.startswith("thermal_zone")
        )
    except Exception:
        return readings

    for zone in thermal_zones:
        zone_path = os.path.join(thermal_root, zone)
        try:
            with open(os.path.join(zone_path, "temp"), "r", encoding="utf-8") as f:
                raw_temp = f.read().strip()
            value = float(raw_temp)
            if value > 1000:
                value /= 1000
            if not 0 < value < 130:
                continue

            sensor_type = zone
            type_path = os.path.join(zone_path, "type")
            if os.path.exists(type_path):
                with open(type_path, "r", encoding="utf-8") as f:
                    sensor_type = f.read().strip() or zone
            readings.append((sensor_type, value))
        except Exception:
            continue

    return readings


def _read_cpu_temperatures_from_sensors() -> list[tuple[str, float]]:
    if not shutil.which("sensors"):
        return []

    try:
        result = subprocess.run(
            ["sensors"],
            capture_output=True,
            text=True,
            timeout=4,
        )
    except Exception:
        return []

    readings: list[tuple[str, float]] = []
    for line in result.stdout.splitlines():
        match = re.search(r"^\s*([^:]+):\s*\+?(-?\d+(?:\.\d+)?)\s*°?C", line)
        if not match:
            continue
        label = match.group(1).strip()
        value = float(match.group(2))
        if 0 < value < 130:
            readings.append((label, value))
    return readings


def get_cpu_temperature_status() -> str:
    """Devuelve la temperatura actual de CPU usando sensores locales disponibles."""
    readings = _read_cpu_temperatures_from_sysfs()
    if not readings:
        readings = _read_cpu_temperatures_from_sensors()

    if not readings:
        return (
            "🌡️ No pude leer la temperatura de la CPU en este equipo.\n\n"
            "En Ubuntu normalmente puedes habilitar sensores con:\n"
            "```bash\nsudo apt install lm-sensors\nsudo sensors-detect\n```\n"
            "Después vuelve a pedirme la temperatura."
        )

    hottest_name, hottest_value = max(readings, key=lambda item: item[1])
    average = sum(value for _, value in readings) / len(readings)
    lines = [
        "🌡️ Temperatura de la CPU:",
        f"• Sensor más caliente: {hottest_name} ({_format_temperature(hottest_value)})",
        f"• Promedio de sensores: {_format_temperature(average)}",
    ]

    visible_readings = readings[:6]
    if len(visible_readings) > 1:
        lines.append("• Lecturas:")
        lines.extend(f"  - {name}: {_format_temperature(value)}" for name, value in visible_readings)
    if len(readings) > len(visible_readings):
        lines.append(f"  - ... y {len(readings) - len(visible_readings)} sensores más")

    return "\n".join(lines)


def open_wallpaper_settings() -> str:
    """Abre directamente el panel grafico para cambiar el fondo de pantalla."""
    candidates = [
        ["gnome-control-center", "background"],
        ["gnome-control-center", "appearance"],
        ["xdg-open", "gnome-control-center://background"],
        ["systemsettings", "kcm_wallpaper"],
    ]

    for args in candidates:
        binary = args[0]
        if not shutil.which(binary):
            continue
        try:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return (
                "¡Listo! Abrí el panel de fondo de pantalla para que puedas elegir "
                "una imagen o cambiar el estilo."
            )
        except Exception:
            continue

    return (
        "No encontré el panel gráfico de fondo de pantalla en este sistema.\n\n"
        "Puedes intentar abrir Configuración manualmente y entrar en Apariencia o Fondo."
    )


def _installed_java_major_version() -> int | None:
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None

    output = f"{result.stdout}\n{result.stderr}"
    match = re.search(r'version\s+"(\d+)', output)
    if not match:
        return None
    return int(match.group(1))


def _netbeans_java_diagnostic() -> str | None:
    java_version = _installed_java_major_version()
    if java_version is None:
        return (
            "NetBeans necesita Java 21 o más nuevo, pero no pude detectar Java instalado.\n\n"
            "Solución recomendada:\n"
            "```bash\nsudo apt update\nsudo apt install openjdk-21-jdk\n```\n"
            "Después abre NetBeans otra vez."
        )
    if java_version < 21:
        return (
            f"NetBeans está instalado, pero tu sistema usa Java {java_version}. "
            "Esta versión de NetBeans requiere Java 21 o más nuevo.\n\n"
            "Solución recomendada:\n"
            "```bash\nsudo apt update\nsudo apt install openjdk-21-jdk\n```\n"
            "Luego verifica con:\n"
            "```bash\njava -version\n```\n"
            "y vuelve a abrir NetBeans."
        )
    return None


def open_application(app_name: str) -> tuple[bool, str]:
    """Abre una aplicación de escritorio común en Linux/Ubuntu."""
    app_map = {
        "terminal": ["gnome-terminal", "x-terminal-emulator", "xterm"],
        "explorador": ["nautilus", "nemo", "thunar", "dolphin"],
        "archivos": ["nautilus", "nemo", "thunar", "dolphin"],
        "navegador": ["firefox", "google-chrome", "chromium-browser", "xdg-open"],
        "calculadora": ["gnome-calculator", "kcalc", "galculator", "xcalc"],
        "monitor": ["gnome-system-monitor", "ksysguard", "htop"],
        "configuracion": ["gnome-control-center", "systemsettings"],
        "editor": ["gedit", "kate", "mousepad", "gnome-text-editor"],
        "wine": ["winecfg"],
        "winecfg": ["winecfg"],
        "netbeans": ["netbeans", "apache-netbeans"],
        "apache-netbeans": ["apache-netbeans", "netbeans"],
    }
    flatpak_app_map = {
        "trilium": ("org.triliumnotes.Trilium", "Trilium Notes"),
        "trilium notes": ("org.triliumnotes.Trilium", "Trilium Notes"),
        "trilium-notes": ("org.triliumnotes.Trilium", "Trilium Notes"),
    }

    target = app_name.lower().strip()
    flatpak_app = flatpak_app_map.get(target)
    if flatpak_app:
        app_id, friendly_name = flatpak_app
        if not shutil.which("flatpak"):
            return False, "Flatpak no esta disponible en este sistema."
        installed = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application,name"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if app_id not in installed.stdout:
            return False, (
                f"{friendly_name} parece ser una app Flatpak, pero no la veo instalada.\n"
                f"Instalala con:\n```bash\nflatpak install flathub {app_id}\n```"
            )
        try:
            subprocess.Popen(["flatpak", "run", app_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"🚀 Abriendo {friendly_name} con Flatpak..."
        except Exception as e:
            return False, f"Error al intentar abrir {friendly_name} con Flatpak: {e}"

    target_commands = app_map.get(target, [target])

    if target in {"netbeans", "apache-netbeans"}:
        diagnostic = _netbeans_java_diagnostic()
        if diagnostic:
            return False, diagnostic

    for cmd in target_commands:
        if shutil.which(cmd):
            try:
                subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, f"🚀 Abriendo {app_name} ({cmd})..."
            except Exception as e:
                return False, f"Error al intentar abrir {app_name}: {e}"

    return False, f"No se encontró un ejecutable para '{app_name}' instalado en el sistema."

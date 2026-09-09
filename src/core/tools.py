# Definicion y ejecutor de herramientas del sistema Linux (Ubuntu) para el Agente.

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.core.security import assess_command, assess_file_write, is_safe_name
from src.core.storage import log_tool_run


PACKAGE_ALIASES = {
    "obs": ("apt", "obs-studio", "OBS Studio"),
    "obs studio": ("apt", "obs-studio", "OBS Studio"),
    "vs code": ("apt", "code", "Visual Studio Code"),
    "visual code": ("apt", "code", "Visual Studio Code"),
    "visual studio code": ("apt", "code", "Visual Studio Code"),
    "vscode": ("apt", "code", "Visual Studio Code"),
    "chrome": ("apt", "google-chrome-stable", "Google Chrome"),
    "google chrome": ("apt", "google-chrome-stable", "Google Chrome"),
    "spotify": ("apt", "spotify-client", "Spotify"),
    "trilium": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium notes": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium-notes": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
}

SOURCE_PACKAGE_ALIASES = {
    "flatpak": {
        "trilium": ("org.triliumnotes.Trilium", "Trilium Notes"),
        "trilium notes": ("org.triliumnotes.Trilium", "Trilium Notes"),
        "trilium-notes": ("org.triliumnotes.Trilium", "Trilium Notes"),
        "com.github.zadam.trilium": ("com.github.zadam.trilium", "Trilium Notes"),
    },
    "snap": {
        "trilium": ("trilium-notes", "Trilium Notes"),
        "trilium notes": ("trilium-notes", "Trilium Notes"),
        "trilium-notes": ("trilium-notes", "Trilium Notes"),
    },
}

INSTALL_SOURCE_ORDER = ("apt", "flatpak", "snap")
LAST_INSTALLED_APP: dict[str, str] = {}

APP_ALIASES = {
    "trilium": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium notes": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium-notes": ("flatpak", "org.triliumnotes.Trilium", "Trilium Notes"),
}


def _quote(value: str) -> str:
    return shlex.quote(value.strip())


def launch_in_terminal(command: str, title: str = "Asistente Linux") -> Tuple[bool, str]:
    """Abre una ventana de terminal interactiva ejecutando un comando de Linux."""
    terminal_candidates = [
        "ptyxis",
        "gnome-terminal",
        "x-terminal-emulator",
        "kgx",
        "tilix",
        "konsole",
        "xfce4-terminal",
        "xterm",
    ]
    shell_cmd = f"{command}; echo; echo 'Presiona Enter para cerrar esta ventana...'; read"

    for term in terminal_candidates:
        if shutil.which(term):
            # Probar sintaxis moderna (--) y clásica (-e) con argumentos separados
            for flag in ["--", "-e"]:
                try:
                    args = [term, flag, "bash", "-c", shell_cmd]
                    subprocess.Popen(
                        args,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True, f"Se abrió una terminal ({term}) ejecutando: {command}"
                except Exception:
                    continue

    return False, "No se encontró ningún emulador de terminal compatible instalado."


def tool_update_system(mode: str = "gui") -> str:
    if mode == "gui":
        if shutil.which("update-manager"):
            try:
                subprocess.Popen(["update-manager"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "Exito: Se ha abierto la interfaz grafica del Actualizador de Software de Ubuntu (update-manager)."
            except Exception as e:
                pass
        if shutil.which("gnome-software"):
            try:
                subprocess.Popen(["gnome-software", "--mode=updates"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "Exito: Se ha abierto la seccion de actualizaciones de la Tienda de Software de Ubuntu."
            except Exception:
                pass

    success, msg = launch_in_terminal("sudo apt update && sudo apt upgrade -y", title="Actualizacion de Ubuntu")
    if success:
        return "Exito: Se ha abierto una ventana de terminal con 'sudo apt update && sudo apt upgrade -y'. Ingresa tu contrasena en la terminal para continuar."
    return f"Fallo al ejecutar actualizacion: {msg}"


def tool_manage_firmware(action: str = "check") -> str:
    """Revisa o instala actualizaciones de firmware usando fwupd."""
    action = action.strip().lower()
    if action not in {"check", "update"}:
        return "Accion de firmware no reconocida. Usa check o update."
    if not shutil.which("fwupdmgr"):
        return (
            "No encontre fwupdmgr, que es la herramienta de Ubuntu para firmware.\n\n"
            "Puedes instalarla con:\n```bash\nsudo apt install fwupd\n```"
        )

    if action == "check":
        command = "fwupdmgr refresh --force; echo; fwupdmgr get-updates"
        success, msg = launch_in_terminal(command, title="Revisando firmware")
        if success:
            return (
                "Abrí una terminal para revisar actualizaciones de firmware.\n\n"
                "Comando ejecutado:\n```bash\n"
                f"{command}\n"
                "```\n"
                "Si no aparecen dispositivos o actualizaciones, tu firmware ya está al día o tu hardware no publica updates por fwupd."
            )
        return f"No pude revisar firmware: {msg}"

    command = "fwupdmgr refresh --force; echo; fwupdmgr get-updates; echo; fwupdmgr update"
    success, msg = launch_in_terminal(command, title="Actualizando firmware")
    if success:
        return (
            "Abrí una terminal para buscar e instalar actualizaciones de firmware con fwupd.\n\n"
            "Comando ejecutado:\n```bash\n"
            f"{command}\n"
            "```\n"
            "Lee la terminal antes de aceptar: algunas actualizaciones pueden pedir reiniciar el equipo."
        )
    return f"No pude iniciar la actualización de firmware: {msg}"


def tool_open_software_center(app_name: str = "") -> str:
    for sc in ["gnome-software", "snap-store", "ubuntu-software"]:
        if shutil.which(sc):
            try:
                args = [sc]
                if app_name:
                    args.append(f"--search={app_name}")
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Exito: Se abrio el Centro de Software ({sc})."
            except Exception as e:
                return f"Error al abrir la tienda de software: {e}"

    return "No se encontro un Centro de Software grafico instalado."


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
            "```bash\nsudo apt update\nsudo apt install openjdk-21-jdk\n```"
        )
    if java_version < 21:
        return (
            f"NetBeans está instalado, pero tu sistema usa Java {java_version}. "
            "Esta versión de NetBeans requiere Java 21 o más nuevo.\n\n"
            "Solución recomendada:\n"
            "```bash\nsudo apt update\nsudo apt install openjdk-21-jdk\n```\n"
            "Después verifica con `java -version` y vuelve a abrir NetBeans."
        )
    return None


def tool_open_application(app_name: str) -> str:
    app_map = {
        "terminal": ["gnome-terminal", "x-terminal-emulator", "xterm"],
        "explorador": ["nautilus", "nemo", "thunar", "dolphin"],
        "archivos": ["nautilus", "nemo", "thunar", "dolphin"],
        "navegador": ["firefox", "google-chrome", "chromium-browser", "xdg-open https://google.com"],
        "calculadora": ["gnome-calculator", "kcalc", "galculator", "xcalc"],
        "monitor": ["gnome-system-monitor", "ksysguard", "htop"],
        "configuracion": ["gnome-control-center", "systemsettings"],
        "editor": ["gedit", "kate", "mousepad", "gnome-text-editor"],
        "wine": ["winecfg"],
        "winecfg": ["winecfg"],
        "netbeans": ["netbeans", "apache-netbeans"],
        "apache-netbeans": ["apache-netbeans", "netbeans"],
    }

    target = app_name.lower().strip()
    if any(phrase in target for phrase in ["la aplicacion que instalaste", "la aplicación que instalaste", "lo que instalaste", "ultima aplicacion", "última aplicación"]):
        if LAST_INSTALLED_APP.get("source") and LAST_INSTALLED_APP.get("package"):
            source = LAST_INSTALLED_APP["source"]
            package = LAST_INSTALLED_APP["package"]
            friendly_name = LAST_INSTALLED_APP.get("friendly_name", package)
            return _open_resolved_application(source, package, friendly_name)
        return "Todavía no tengo registrada una aplicación instalada en esta sesión."

    alias = APP_ALIASES.get(target)
    if alias:
        source, package, friendly_name = alias
        return _open_resolved_application(source, package, friendly_name)

    executables = app_map.get(target, [target])

    if target in {"netbeans", "apache-netbeans"}:
        diagnostic = _netbeans_java_diagnostic()
        if diagnostic:
            return diagnostic

    for cmd in executables:
        parts = cmd.split()
        binary = parts[0]
        if shutil.which(binary):
            try:
                subprocess.Popen(parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Exito: Se ha abierto la aplicacion {app_name}."
            except Exception as e:
                return f"Error al abrir {app_name}: {e}"

    return f"No se encontro el ejecutable para la aplicacion '{app_name}'."


def _open_resolved_application(source: str, package: str, friendly_name: str) -> str:
    if source == "flatpak":
        if not shutil.which("flatpak"):
            return "Flatpak no esta disponible en este sistema."
        installed = _run_probe(["flatpak", "list", "--app", "--columns=application,name"], timeout=8)
        if package not in installed:
            return (
                f"{friendly_name} parece ser una app Flatpak, pero no la veo instalada.\n"
                f"Instalala con:\n```bash\nflatpak install flathub {package}\n```"
            )
        try:
            subprocess.Popen(["flatpak", "run", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abriendo {friendly_name} con Flatpak (`flatpak run {package}`)."
        except Exception as exc:
            return f"No pude abrir {friendly_name} con Flatpak: {exc}"

    if source == "snap":
        if not shutil.which("snap"):
            return "Snap no esta disponible en este sistema."
        try:
            subprocess.Popen(["snap", "run", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abriendo {friendly_name} con Snap (`snap run {package}`)."
        except Exception as exc:
            return f"No pude abrir {friendly_name} con Snap: {exc}"

    if shutil.which(package):
        try:
            subprocess.Popen([package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abriendo {friendly_name} (`{package}`)."
        except Exception as exc:
            return f"No pude abrir {friendly_name}: {exc}"
    return f"No encontre el ejecutable para {friendly_name}."


def tool_open_terminal_command(command: str, explanation: str = "") -> str:
    decision = assess_command(command, allow_confirmation=False)
    if decision.is_blocked:
        return f"Accion bloqueada por seguridad ({decision.risk.value}): {decision.message}"
    success, msg = launch_in_terminal(command, title=f"Comando: {command[:20]}")
    if success:
        return f"Exito: Se ha abierto una terminal ejecutando `{command}`."
    return f"Fallo al abrir terminal: {msg}"


def tool_install_deb_package(package_name: str = "") -> str:
    """Busca e instala un archivo .deb en Descargas o Downloads de forma interactiva."""
    folders = [
        os.path.expanduser("~/Descargas"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~"),
    ]
    candidates = []
    for f in folders:
        if os.path.isdir(f):
            try:
                for item in os.listdir(f):
                    if item.endswith(".deb"):
                        candidates.append(os.path.join(f, item))
            except Exception:
                pass

    if not candidates:
        return "No se encontró ningún archivo .deb en tu carpeta de Descargas."

    target_file = None
    if package_name:
        query = package_name.lower().replace(".deb", "").strip()
        matched = [c for c in candidates if query in os.path.basename(c).lower()]
        if matched:
            target_file = matched[0]

    if not target_file:
        if len(candidates) == 1:
            target_file = candidates[0]
        else:
            names = [os.path.basename(c) for c in candidates]
            return f"Encontré varios paquetes .deb: {', '.join(names)}. ¿Cuál de ellos deseas instalar?"

    cmd = f"sudo dpkg -i {shlex.quote(target_file)} && sudo apt-get install -f -y"
    success, msg = launch_in_terminal(cmd, title=f"Instalando {os.path.basename(target_file)}")
    if success:
        return f"Éxito: Se abrió la terminal para instalar '{os.path.basename(target_file)}'. Ingresa tu contraseña en la terminal para completar la instalación."
    return f"Error al abrir la terminal: {msg}"


def build_deb_install_args(file_path: str, privilege_tool: str = "pkexec") -> list[str]:
    """Valida una ruta .deb y genera argumentos seguros, sin usar un shell."""
    path = Path(file_path).expanduser().resolve()
    if path.suffix.lower() != ".deb":
        raise ValueError("El archivo seleccionado no tiene extension .deb.")
    if not path.is_file():
        raise ValueError("El archivo .deb seleccionado no existe.")
    return [privilege_tool, "apt", "install", "-y", str(path)]


def _parse_program_request(program_name: str, preferred_source: str = "auto") -> tuple[str, str, str]:
    source = preferred_source.strip().lower() or "auto"
    name = program_name.strip().lower()
    name = re.sub(r"\b(por favor|porfa|please)\b", "", name).strip()
    name = re.sub(r"\b(en|para)\s+(mi\s+)?(ubuntu|linux|sistema|computadora|pc)\b", "", name).strip()

    source_match = re.match(r"^(?:por|con|desde|usando|en)?\s*(apt|apt-get|snap|flatpak)\s+(.+)$", name)
    if source_match:
        source = "apt" if source_match.group(1) == "apt-get" else source_match.group(1)
        name = source_match.group(2).strip()

    alias = PACKAGE_ALIASES.get(name)
    if alias and source == "auto":
        return alias

    source_alias = SOURCE_PACKAGE_ALIASES.get(source, {}).get(name)
    if source_alias:
        package, friendly_name = source_alias
        return source, package, friendly_name

    package = name.replace(" ", "-")
    return source, package, program_name.strip()


def _run_probe(args: list[str], timeout: int = 8) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return ""
    return f"{result.stdout}\n{result.stderr}".strip()


def _apt_has_candidate(package: str) -> bool:
    output = _run_probe(["apt-cache", "policy", package])
    for line in output.splitlines():
        text = line.strip().lower()
        if text.startswith("candidato:") or text.startswith("candidate:"):
            value = text.split(":", 1)[1].strip()
            return value not in {"(ninguno)", "(none)", "none", ""}
    return False


def _flatpak_has_match(package: str) -> bool:
    if not shutil.which("flatpak"):
        return False
    output = _run_probe(["flatpak", "search", package], timeout=12)
    needle = package.lower()
    return any(needle in line.lower().split() for line in output.splitlines())


def _snap_has_match(package: str) -> bool:
    if not shutil.which("snap"):
        return False
    output = _run_probe(["snap", "find", package], timeout=12)
    needle = package.lower()
    for line in output.splitlines():
        parts = line.split()
        if parts and parts[0].lower() == needle:
            return True
    return False


def _source_has_package(source: str, package: str) -> bool:
    if source == "apt":
        return _apt_has_candidate(package)
    if source == "flatpak":
        return _flatpak_has_match(package)
    if source == "snap":
        return _snap_has_match(package)
    return False


def _resolve_install_source(source: str, package: str, friendly_name: str) -> tuple[str | None, str, str, str]:
    if source != "auto":
        if _source_has_package(source, package):
            return source, package, friendly_name, ""
        return (
            None,
            package,
            friendly_name,
            f"No encontre '{friendly_name}' como paquete disponible en {source}. "
            "No voy a ejecutar un comando que probablemente fallara.",
        )

    alias = PACKAGE_ALIASES.get(package.lower())
    candidates = [alias] if alias else []
    for candidate_source in INSTALL_SOURCE_ORDER:
        source_alias = SOURCE_PACKAGE_ALIASES.get(candidate_source, {}).get(package.lower())
        if source_alias:
            candidate_package, candidate_name = source_alias
            candidates.append((candidate_source, candidate_package, candidate_name))
        candidates.append((candidate_source, package, friendly_name))

    seen = set()
    for candidate_source, candidate_package, candidate_name in candidates:
        key = (candidate_source, candidate_package)
        if key in seen:
            continue
        seen.add(key)
        if _source_has_package(candidate_source, candidate_package):
            return candidate_source, candidate_package, candidate_name, ""

    return (
        None,
        package,
        friendly_name,
        f"No encontre '{friendly_name}' en apt, Flatpak ni Snap. "
        "Puede que necesite descargarse desde su pagina oficial o que falte configurar un repositorio.",
    )


def tool_install_program(program_name: str, preferred_source: str = "auto") -> str:
    """Resuelve lenguaje natural a un comando de instalacion y lo abre de forma confirmable."""
    if not program_name.strip():
        return "Indica que programa quieres instalar."

    source, package, friendly_name = _parse_program_request(program_name, preferred_source)

    if source not in {"auto", "apt", "snap", "flatpak"}:
        return "Metodo de instalacion no reconocido. Puedo usar apt, snap o flatpak."
    if not re.fullmatch(r"[A-Za-z0-9.+_-]+", package) and source != "flatpak":
        return f"No pude convertir '{program_name}' a un nombre seguro de paquete."

    resolved_source, package, friendly_name, problem = _resolve_install_source(source, package, friendly_name)
    if not resolved_source:
        return (
            f"{problem}\n\n"
            "Sugerencia: prueba pedirlo por una fuente concreta, por ejemplo "
            "`instala trilium notes por flatpak`, o abre la tienda de aplicaciones."
        )
    source = resolved_source

    if source == "apt":
        command = f"sudo apt install {shlex.quote(package)}"
    elif source == "snap":
        command = f"sudo snap install {shlex.quote(package)}"
    else:
        command = f"flatpak install flathub {shlex.quote(package)}"

    success, msg = launch_in_terminal(command, title=f"Instalando {friendly_name[:24]}")
    if success:
        LAST_INSTALLED_APP.clear()
        LAST_INSTALLED_APP.update({
            "source": source,
            "package": package,
            "friendly_name": friendly_name,
        })
        return (
            f"Voy a instalar {friendly_name} usando {source}.\n"
            f"Comando ejecutado en terminal:\n```bash\n{command}\n```\n"
            "Si Ubuntu pide contraseña o confirmación, acéptala en la ventana que se abrió."
        )
    return f"No pude abrir la terminal para instalar {friendly_name}: {msg}\n\nComando recomendado:\n```bash\n{command}\n```"


def tool_get_system_status() -> str:
    from src.nlp.system_tools import get_system_status
    return get_system_status()


# ─── NUEVAS HERRAMIENTAS ────────────────────────────────────────────────────


def _run_command_silent(command: str) -> tuple[str, str, str, int | None]:
    command = command.strip()
    decision = assess_command(command, allow_confirmation=False)
    if decision.is_blocked:
        message = f"⛔ {decision.message}\n\nComando: `{command}`"
        return message, "", decision.message, None
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "LANG": "es_ES.UTF-8"},
        )
        output = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if output:
            message = f"```\n{output}\n```"
        elif stderr:
            message = f"⚠️ Salida de error:\n```\n{stderr}\n```"
        else:
            message = "✅ Comando ejecutado sin salida."
        return message, output, stderr, result.returncode
    except subprocess.TimeoutExpired:
        message = "⏱️ El comando tardó demasiado (más de 15 s) y fue cancelado."
        return message, "", message, None
    except Exception as e:
        message = f"❌ Error al ejecutar el comando: {e}"
        return message, "", str(e), None


def tool_run_command_silent(command: str) -> str:
    """Ejecuta un comando no interactivo y devuelve su salida directamente en el chat."""
    return _run_command_silent(command)[0]


def tool_manage_service(service_name: str, action: str) -> str:
    """Gestiona un servicio systemd (start/stop/restart/status)."""
    valid_actions = {"start", "stop", "restart", "status", "enable", "disable"}
    service_name = service_name.strip()
    action = action.lower().strip()
    if action not in valid_actions:
        return f"Acción inválida: '{action}'. Usa: {', '.join(valid_actions)}."
    if not is_safe_name(service_name):
        return "❌ Nombre de servicio inválido. Usa sólo letras, números, puntos, guiones, @, dos puntos o guiones bajos."

    if action == "status":
        # Status se puede mostrar directamente en el chat
        return tool_run_command_silent(f"systemctl {action} {_quote(service_name)} --no-pager")
    else:
        # Acciones que modifican el servicio abren terminal con sudo
        quoted_service = _quote(service_name)
        cmd = f"sudo systemctl {action} {quoted_service} && systemctl status {quoted_service} --no-pager"
        success, msg = launch_in_terminal(cmd, title=f"Servicio: {service_name}")
        if success:
            return f"✅ Se abrió una terminal para ejecutar `systemctl {action} {service_name}`."
        return f"❌ No se pudo abrir terminal: {msg}"


def tool_search_package(query: str) -> str:
    """Busca paquetes disponibles en apt y devuelve los resultados en el chat."""
    query = query.strip()
    if not query:
        return "❌ Indica qué paquete quieres buscar."
    result = tool_run_command_silent(f"apt-cache search {_quote(query)} | head -20")
    if "```" in result and len(result) > 10:
        return f"📦 Resultados para '{query}':\n{result}"
    return f"No se encontraron paquetes para '{query}' en apt."


def tool_remove_package(package_name: str) -> str:
    """Desinstala un paquete apt abriendo una terminal interactiva."""
    package_name = package_name.strip()
    if not is_safe_name(package_name):
        return "❌ Nombre de paquete inválido. Usa el nombre exacto del paquete apt, sin espacios ni símbolos de shell."
    cmd = f"sudo apt remove --purge {_quote(package_name)} && sudo apt autoremove"
    success, msg = launch_in_terminal(cmd, title=f"Desinstalando {package_name}")
    if success:
        return f"✅ Se abrió una terminal para desinstalar '{package_name}'. Ingresa tu contraseña para confirmar."
    return f"❌ No se pudo abrir terminal: {msg}"


def tool_read_file(file_path: str) -> str:
    """Lee y devuelve el contenido de un archivo del sistema en el chat."""
    if not file_path.strip():
        return "❌ Indica la ruta del archivo que quieres leer."
    path = os.path.abspath(os.path.expanduser(file_path))
    if not os.path.exists(path):
        return f"❌ El archivo no existe: `{path}`"
    if not os.path.isfile(path):
        return f"❌ La ruta no es un archivo: `{path}`"
    try:
        size = os.path.getsize(path)
        if size > 50_000:
            return f"⚠️ El archivo es demasiado grande ({size // 1024} KB). Usa `head` o `tail` para verlo parcialmente."
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        lines = content.splitlines()
        preview = "\n".join(lines[:100])
        suffix = f"\n... ({len(lines) - 100} líneas más)" if len(lines) > 100 else ""
        return f"📄 `{path}`:\n```\n{preview}{suffix}\n```"
    except Exception as e:
        return f"❌ Error al leer el archivo: {e}"


def tool_write_file(file_path: str, content: str) -> str:
    """Crea o sobreescribe un archivo de texto en la ruta dada."""
    if not file_path.strip():
        return "❌ Indica la ruta donde quieres guardar el archivo."
    path = os.path.abspath(os.path.expanduser(file_path))
    decision = assess_file_write(path)
    if decision.is_blocked:
        return f"⛔ {decision.message}\n\nRuta: `{path}`"
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Archivo guardado exitosamente: `{path}` ({len(content)} caracteres)"
    except Exception as e:
        return f"❌ Error al escribir el archivo: {e}"


# ─── DEFINICIÓN DE HERRAMIENTAS PARA EL AGENTE ─────────────────────────────

LINUX_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "install_program",
            "description": "Instala un programa solicitado en lenguaje natural. Resuelve nombres comunes a paquetes apt/snap/flatpak y abre una terminal interactiva con el comando correcto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "program_name": {
                        "type": "string",
                        "description": "Nombre del programa que el usuario quiere instalar, por ejemplo 'trilium notes', 'vlc', 'netbeans', 'spotify'."
                    },
                    "preferred_source": {
                        "type": "string",
                        "enum": ["auto", "apt", "snap", "flatpak"],
                        "description": "Metodo preferido si el usuario lo menciono. Usa auto cuando no lo diga."
                    }
                },
                "required": ["program_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_firmware",
            "description": "Revisa o instala actualizaciones de firmware del equipo con fwupd/fwupdmgr. Usar cuando el usuario diga firmware, BIOS, UEFI, drivers de dispositivo o actualizar componentes internos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["check", "update"],
                        "description": "check solo busca actualizaciones; update busca e intenta instalarlas con confirmaciones en terminal."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_system",
            "description": "Actualiza el sistema operativo Ubuntu y sus paquetes. Por defecto abre la interfaz grafica del Actualizador de Software (update-manager) o una terminal interactiva si el usuario lo pide o si no hay GUI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["gui", "terminal"],
                        "description": "gui para abrir el Gestor de Actualizaciones visual de Ubuntu (update-manager); terminal para abrir una consola interactiva ejecutando apt upgrade."
                    }
                },
                "required": ["mode"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_deb_package",
            "description": "Busca e instala automáticamente un paquete de software descargado (.deb) en la carpeta Descargas o Downloads mediante dpkg y apt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Nombre o palabra clave del paquete a instalar (ej: wps-office, chrome, cursor, discord)."
                    }
                },
                "required": ["package_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_software_center",
            "description": "Abre la Tienda de Software / Centro de Aplicaciones de Ubuntu para buscar o instalar programas graficamente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Nombre de la aplicacion a buscar en la tienda (opcional)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Abre una aplicacion de escritorio instalada en Ubuntu. Soporta ejecutables normales, apps Flatpak/Snap conocidas y referencias como 'la aplicacion que instalaste ahora'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Nombre de la aplicacion a abrir (ej: terminal, explorador, navegador, calculadora, monitor, configuracion, editor)."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_terminal_command",
            "description": "Abre una ventana de terminal real en Ubuntu para ejecutar interactivamente un comando que requiere interacción del usuario, sudo, o es de larga duración (ej: sudo apt install htop, htop, ping google.com). NO usar para comandos de solo lectura/diagnóstico rápido como ls, df, free, cat, ip a — para esos usar run_command_silent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "El comando exacto a ejecutar en la terminal."
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Breve explicacion de que hace el comando."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Consulta el uso en tiempo real de memoria RAM, espacio en disco, tiempo encendido y estado del sistema Linux.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command_silent",
            "description": "Ejecuta un comando de Linux no interactivo (sin sudo, sin entrada del usuario) y muestra la salida directamente en el chat. Ideal para: ls, df -h, free -h, ip a, cat archivo, uname -a, whoami, ps aux, lsblk, lscpu, env, echo, find, grep, etc. NO usar para comandos con sudo o que requieran interacción.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "El comando exacto a ejecutar (sin sudo). Ejemplo: 'df -h', 'free -m', 'ls -la ~/Documentos', 'cat /etc/os-release'."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_service",
            "description": "Gestiona servicios del sistema Linux con systemd: iniciar, detener, reiniciar, ver estado, habilitar o deshabilitar un servicio (ej: nginx, ssh, bluetooth, NetworkManager, cups).",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Nombre del servicio systemd (ej: ssh, nginx, bluetooth, cups, NetworkManager)."
                    },
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop", "restart", "status", "enable", "disable"],
                        "description": "Acción a realizar sobre el servicio."
                    }
                },
                "required": ["service_name", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_package",
            "description": "Busca paquetes disponibles en los repositorios apt de Ubuntu sin instalar nada. Útil para descubrir el nombre exacto de un paquete antes de instalarlo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Término de búsqueda del paquete (ej: vlc, python3, nodejs, ffmpeg)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_package",
            "description": "Desinstala completamente un paquete apt del sistema Ubuntu, incluyendo sus archivos de configuración (purge) y dependencias huérfanas (autoremove).",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Nombre exacto del paquete apt a desinstalar (ej: vlc, gimp, libreoffice)."
                    }
                },
                "required": ["package_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lee y muestra el contenido de un archivo de texto en el chat. Útil para ver archivos de configuración, logs, scripts, etc. (ej: ~/.bashrc, /etc/hosts, ~/script.sh).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Ruta absoluta o relativa al archivo a leer (soporta ~ para home). Ejemplo: '~/.bashrc', '/etc/hosts'."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Crea o sobreescribe un archivo de texto en el sistema del usuario. Útil para crear scripts, archivos de configuración personales, notas, etc. No permite escribir en rutas del sistema (/etc, /usr, /bin).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Ruta del archivo a crear o sobreescribir (soporta ~). Ejemplo: '~/scripts/mi_script.sh', '~/notas.txt'."
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenido de texto a escribir en el archivo."
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
]


def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    if name == "install_program":
        program_name = arguments.get("program_name", "")
        preferred_source = arguments.get("preferred_source", "auto")
        result = tool_install_program(program_name, preferred_source)
    elif name == "manage_firmware":
        action = arguments.get("action", "check")
        result = tool_manage_firmware(action)
    elif name == "update_system":
        mode = arguments.get("mode", "gui")
        result = tool_update_system(mode)
    elif name == "install_deb_package":
        package_name = arguments.get("package_name", "")
        result = tool_install_deb_package(package_name)
    elif name == "open_software_center":
        app_name = arguments.get("app_name", "")
        result = tool_open_software_center(app_name)
    elif name == "open_application":
        app_name = arguments.get("app_name", "")
        result = tool_open_application(app_name)
    elif name == "open_terminal_command":
        command = arguments.get("command", "")
        explanation = arguments.get("explanation", "")
        result = tool_open_terminal_command(command, explanation)
    elif name == "get_system_status":
        result = tool_get_system_status()
    elif name == "run_command_silent":
        command = arguments.get("command", "")
        result, stdout, stderr, exit_code = _run_command_silent(command)
    elif name == "manage_service":
        service_name = arguments.get("service_name", "")
        action = arguments.get("action", "status")
        result = tool_manage_service(service_name, action)
    elif name == "search_package":
        query = arguments.get("query", "")
        result = tool_search_package(query)
    elif name == "remove_package":
        package_name = arguments.get("package_name", "")
        result = tool_remove_package(package_name)
    elif name == "read_file":
        file_path = arguments.get("file_path", "")
        result = tool_read_file(file_path)
    elif name == "write_file":
        file_path = arguments.get("file_path", "")
        content = arguments.get("content", "")
        result = tool_write_file(file_path, content)
    else:
        result = f"Herramienta '{name}' no reconocida."

    if name == "run_command_silent":
        log_tool_run(
            name,
            str(arguments),
            result,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )
    else:
        log_tool_run(name, str(arguments), result)
    return result

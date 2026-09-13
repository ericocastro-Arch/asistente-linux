"""
LinuxMate AI — Liquid Glass Edition (PyWebView GUI Backend)
High-performance Chromium/WebKit hardware-accelerated frontend with Python system bridge.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Prevenir abortos de sandbox de Chromium en Linux cuando no hay privilegios de kernel
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

import psutil
import webview

from src.core.agent import create_agent
from src.core.storage import init_db, start_session
from src.core.tools import launch_in_terminal
from src.nlp.processor import NLPProcessor


class JsApi:
    """API expuesta a JavaScript a través de window.pywebview.api."""

    def __init__(self) -> None:
        self.window: Optional[webview.Window] = None
        self._maximized: bool = False
        
        # Iniciar base de datos local y sesiones
        try:
            init_db()
        except Exception:
            pass

        # Iniciar agente IA y procesador NLP
        try:
            self.agent = create_agent()
            self.session_id = self.agent.session_id if self.agent else start_session("webview-gui")
        except Exception:
            self.agent = None
            self.session_id = None

        self.nlp = NLPProcessor()
        self._cached_updates: int = 0
        self._last_updates_check: float = 0.0

    # =========================================================================
    # 1. CONTROLES DE VENTANA
    # =========================================================================
    def window_control(self, action: str) -> None:
        """Controla minimizar, maximizar y cerrar desde la barra de título personalizada."""
        if not self.window:
            return

        action = (action or "").lower().strip()
        if action == "min":
            self.window.minimize()
        elif action == "max":
            if self._maximized:
                self.window.restore()
                self._maximized = False
            else:
                self.window.maximize()
                self._maximized = True
        elif action == "close":
            self.window.destroy()

    # =========================================================================
    # 2. CHAT IA Y PROCESAMIENTO NLP
    # =========================================================================
    def chat(self, user_input: str) -> str:
        """Procesa una consulta del usuario mediante NLP local o delegación al agente IA."""
        text = (user_input or "").strip()
        if not text:
            return "Por favor ingresa una pregunta o comando."

        try:
            # Procesar localmente primero o enviar al Agente
            response = self.nlp.process(text, agent=self.agent)
            if response and response.strip():
                return response.strip()
            
            if self.agent:
                return self.agent.chat(text)
            
            return (
                f"He recibido: '{text}'.\n\n"
                "💡 Para respuestas inteligentes con IA, recuerda configurar tu clave `GROQ_API_KEY` en el archivo `.env`."
            )
        except Exception as exc:
            return f"⚠️ No se pudo procesar la solicitud: {exc}"

    # =========================================================================
    # 3. TELEMETRÍA DEL SISTEMA EN TIEMPO REAL
    # =========================================================================
    def get_system_stats(self) -> Dict[str, Any]:
        """Devuelve porcentaje de CPU, RAM y estado de actualizaciones."""
        try:
            cpu = round(psutil.cpu_percent(interval=None), 1)
            ram = round(psutil.virtual_memory().percent, 1)
            
            # Chequeo periódico de actualizaciones (cada 30 seg para no saturar disco)
            now = time.time()
            if now - self._last_updates_check > 30.0:
                self._cached_updates = self._check_pending_updates()
                self._last_updates_check = now

            return {
                "cpu_percent": cpu,
                "ram_percent": ram,
                "updates_pending": self._cached_updates,
            }
        except Exception:
            return {
                "cpu_percent": 0.0,
                "ram_percent": 0.0,
                "updates_pending": 0,
            }

    def _check_pending_updates(self) -> int:
        """Comprueba paquetes actualizables en distros basadas en Debian/Ubuntu."""
        up_file = Path("/var/lib/update-notifier/updates-available")
        if up_file.is_file():
            try:
                for line in up_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if "packages can be updated" in line or "actualizaciones se pueden aplicar" in line:
                        parts = line.strip().split()
                        if parts and parts[0].isdigit():
                            return int(parts[0])
            except Exception:
                pass
        return 0

    def get_distro_info(self) -> Dict[str, str]:
        """Obtiene la distribución y versión de Linux activa."""
        distro_name = "Linux"
        distro_version = ""

        os_release = Path("/etc/os-release")
        if os_release.is_file():
            try:
                lines = os_release.read_text(encoding="utf-8", errors="ignore").splitlines()
                data = {}
                for l in lines:
                    if "=" in l:
                        k, v = l.split("=", 1)
                        data[k.strip()] = v.strip().strip('"')
                distro_name = data.get("PRETTY_NAME") or data.get("NAME") or "Linux"
                distro_version = data.get("VERSION_ID") or ""
            except Exception:
                pass

        return {
            "name": distro_name,
            "version": distro_version,
            "kernel": platform.release(),
            "arch": platform.machine(),
        }

    # =========================================================================
    # 4. ACCIONES RÁPIDAS Y HERRAMIENTAS
    # =========================================================================
    def run_action(self, action_id: str) -> str:
        """Ejecuta una de las acciones del dashboard de forma guiada y segura."""
        action_id = (action_id or "").strip()

        if action_id == "update_system":
            # Lanzar actualización en terminal con confirmación del usuario
            cmd = "sudo apt update && sudo apt upgrade"
            ok, msg = launch_in_terminal(cmd, "Actualizar Sistema — LinuxMate AI")
            if ok:
                return "🚀 Se abrió la ventana de terminal para actualizar el sistema de forma segura. Ingresa tu contraseña si te la solicita."
            return f"Comando para actualizar tu sistema:\n```bash\nsudo apt update && sudo apt upgrade\n```"

        elif action_id == "install_programs":
            return (
                "📦 **Centro de Aplicaciones Recomendadas**:\n"
                "- **Navegadores**: Google Chrome, Brave, Firefox, Edge\n"
                "- **Ofimática**: LibreOffice, OnlyOffice\n"
                "- **Desarrollo**: VS Code, Git, Docker, Node.js\n"
                "- **Multimedia**: VLC Player, GIMP, OBS Studio, Spotify\n\n"
                "💡 Puedes hacer clic en 'Instalar' en la lista de la derecha o pedirme en el chat: `instalar vlc`."
            )

        elif action_id == "clean_system":
            # Limpiar miniaturas de usuario y sugerir autoremove
            cleaned_mb = self._clean_user_cache()
            cmd = "sudo apt autoremove --purge && sudo apt clean"
            ok, _ = launch_in_terminal(cmd, "Limpieza de Paquetes — LinuxMate AI")
            return (
                f"🧹 Se liberaron **{cleaned_mb:.1f} MB** de caché local de miniaturas.\n"
                f"Se ha iniciado la limpieza profunda de paquetes obsoletos en tu terminal."
            )

        elif action_id == "config_network":
            # Diagnóstico rápido de red
            try:
                gateways = psutil.net_if_addrs()
                ips = []
                for iface, addrs in gateways.items():
                    if iface.startswith("lo"):
                        continue
                    for addr in addrs:
                        if addr.family == 2:  # IPv4
                            ips.append(f"• **{iface}**: `{addr.address}`")
                ip_str = "\n".join(ips) if ips else "Sin conexión local detectada."
                return f"🌐 **Estado de Red Local**:\n{ip_str}\n\nPara verificar conectividad hacia internet:\n```bash\nping -c 4 1.1.1.1\n```"
            except Exception as exc:
                return f"Error leyendo interfaces de red: {exc}"

        elif action_id == "gaming_hub":
            steam_installed = shutil.which("steam") is not None
            lutris_installed = shutil.which("lutris") is not None
            status_steam = "✓ Instalado" if steam_installed else "No instalado"
            status_lutris = "✓ Instalado" if lutris_installed else "No instalado"
            return (
                f"🎮 **Gaming en Linux (Steam & Proton)**:\n\n"
                f"• **Steam**: {status_steam}\n"
                f"• **Lutris**: {status_lutris}\n\n"
                "Proton te permite jugar títulos de Windows en Linux con un solo clic en Steam: "
                "`Steam > Parámetros > Compatibilidad > Activar Steam Play`.\n\n"
                "Para instalar Steam por terminal:\n```bash\nsudo apt install -y steam\n```"
            )

        elif action_id == "terminal_guide":
            return (
                "💻 **Comandos Esenciales para Principiantes**:\n\n"
                "• `ls -la` : Lista archivos detallados, incluyendo ocultos.\n"
                "• `cd <carpeta>` : Navega a una carpeta.\n"
                "• `pwd` : Muestra en qué carpeta te encuentras.\n"
                "• `mkdir <nombre>` : Crea una carpeta nueva.\n"
                "• `sudo apt update` : Actualiza la lista de programas disponibles.\n"
                "• `htop` : Monitor visual interactivo de procesos y RAM."
            )

        elif action_id == "drivers_manager":
            try:
                lspci = subprocess.check_output(["lspci"], text=True, errors="ignore")
                vga_lines = [line.strip() for line in lspci.splitlines() if "VGA" in line or "3D" in line]
                vga_info = "\n".join(f"• {line}" for line in vga_lines) if vga_lines else "Gráficos integrados estándar."
            except Exception:
                vga_info = "No se pudo consultar lspci."

            return (
                f"⚙️ **Controladores y Tarjeta Gráfica**:\n{vga_info}\n\n"
                "Para buscar controladores propietarios recomendados en Ubuntu:\n"
                "```bash\nubuntu-drivers devices\n```\n"
                "O ejecuta `Software y Actualizaciones > Controladores Adicionales`."
            )

        elif action_id == "backup_timeshift":
            ts_installed = shutil.which("timeshift") is not None
            if ts_installed:
                subprocess.Popen(["timeshift-gtk"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "🛡️ Abriendo la aplicación **Timeshift** para crear o restaurar copias de seguridad..."
            else:
                return (
                    "🛡️ **Timeshift Backup**:\n"
                    "Timeshift es la mejor herramienta para restaurar tu sistema ante cualquier fallo (equivalente a Puntos de Restauración en Windows).\n\n"
                    "Pulsa **Instalar** en la sección de apps o ejecuta:\n```bash\nsudo apt install -y timeshift\n```"
                )

        elif action_id == "troubleshooter":
            # Diagnóstico de problemas comunes
            disk = shutil.disk_usage("/")
            free_gb = disk.free / (1024 ** 3)
            status = "✅ Espacio en disco OK" if free_gb > 5.0 else f"⚠️ Poco espacio en disco: {free_gb:.1f} GB libres"
            return (
                "🛠️ **Diagnóstico Rápido de Problemas**:\n\n"
                f"• **Almacenamiento**: {status} ({free_gb:.1f} GB disponibles en `/`).\n"
                "• **Paquetes rotos**: Si una instalación falló, repara con:\n"
                "```bash\nsudo apt --fix-broken install\n```\n"
                "• **Reinicio de audio (PulseAudio/PipeWire)**:\n"
                "```bash\nsystemctl --user restart wireplumber pipewire\n```"
            )

        elif action_id == "uninstall_manager":
            return (
                "🗑️ **Desinstalador Seguro de Aplicaciones**:\n\n"
                "Para desinstalar una app sin dañar el resto del sistema:\n"
                "1. `sudo apt remove <nombre-app>` : Desinstala la app conservando tus configuraciones.\n"
                "2. `sudo apt purge <nombre-app>` : Desinstala la app y elimina sus configuraciones.\n"
                "3. `sudo apt autoremove` : Elimina paquetes que ya no son necesarios."
            )

        return f"Acción '{action_id}' reconocida y registrada."

    def _clean_user_cache(self) -> float:
        """Limpia la carpeta de miniaturas ~/.cache/thumbnails y devuelve MB liberados."""
        thumb_dir = Path.home() / ".cache" / "thumbnails"
        bytes_freed = 0
        if thumb_dir.is_dir():
            try:
                for item in thumb_dir.rglob("*"):
                    if item.is_file():
                        try:
                            sz = item.stat().st_size
                            item.unlink()
                            bytes_freed += sz
                        except Exception:
                            pass
            except Exception:
                pass
        return bytes_freed / (1024 * 1024)

    # =========================================================================
    # 5. INSTALADOR DE APLICACIONES EN 1 CLIC
    # =========================================================================
    def install_app(self, app_id: str) -> Dict[str, Any]:
        """Instala aplicaciones populares mediante la terminal segura del sistema."""
        app_id = (app_id or "").strip().lower()

        app_commands = {
            "code": "sudo apt install -y code || sudo snap install --classic code",
            "google-chrome": "wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && sudo apt install -y /tmp/chrome.deb && rm /tmp/chrome.deb",
            "steam": "sudo apt update && sudo apt install -y steam",
            "timeshift": "sudo apt update && sudo apt install -y timeshift",
        }

        cmd = app_commands.get(app_id)
        if not cmd:
            return {"success": False, "message": f"Aplicación '{app_id}' no reconocida en el catálogo rápido."}

        # Ejecutar en terminal interactiva para que el usuario pueda autenticar con sudo
        ok, msg = launch_in_terminal(cmd, f"Instalando {app_id} — LinuxMate AI")
        if ok:
            return {
                "success": True,
                "message": f"Se inició la instalación de '{app_id}' en una ventana de terminal guiada.",
            }
        return {
            "success": False,
            "message": f"No se pudo abrir la terminal para instalar '{app_id}': {msg}",
        }


def run_webview(debug: bool = False) -> None:
    """Inicia la interfaz gráfica de PyWebView con PyQt6-WebEngine."""
    api = JsApi()
    html_file = Path(__file__).resolve().parent / "web" / "index.html"

    if not html_file.is_file():
        raise FileNotFoundError(f"No se encontró el archivo HTML en {html_file}")

    # Configuración de ventana de PyWebView
    window = webview.create_window(
        title="LinuxMate AI — Liquid Glass Edition",
        url=str(html_file.resolve()),
        js_api=api,
        width=1180,
        height=720,
        min_size=(1020, 600),
        frameless=False,
        background_color="#080816",
        easy_drag=True,
    )
    api.window = window

    # Iniciar con backend Qt (Chromium acelerado por hardware)
    webview.start(gui="qt", debug=debug)


if __name__ == "__main__":
    run_webview(debug=True)

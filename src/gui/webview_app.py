"""
LinuxMate AI — Liquid Glass Edition (PyWebView GUI Backend)
High-performance Chromium/WebKit hardware-accelerated frontend with Python system bridge.
"""

from __future__ import annotations

import os
import platform
import re
import secrets
import shlex
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
from src.core.code_workspace import CodeWorkspace, WorkspaceError, contains_likely_secret
from src.core.storage import init_db, start_session
from src.core.tools import build_interactive_uninstall_command, find_uninstall_candidates, launch_in_terminal
from src.gui.app_catalog import clear_installed_cache, get_app_icon, get_catalog
from src.gui.academy import AcademyWindow
from src.gui.guided_explanations import explain_command, explain_error
from src.gui.system_diagnostics import diagnose_system, run_diagnostic_fix as execute_diagnostic_fix
from src.gui.problem_solver import get_problem_guides, run_problem_action as execute_problem_action, run_problem_checks
from src.gui.log_analyzer import get_system_logs as read_system_logs
from src.gui.resource_monitor import (
    get_cpu_temperature,
    get_resource_overview as read_resource_overview,
    stop_user_process as terminate_user_process,
    toggle_startup_app as update_startup_app,
)
from src.gui.setup_wizard import (
    get_setup_plan as read_setup_plan,
    run_setup_action as execute_setup_action,
)
from src.gui.service_manager import (
    get_service_overview as read_service_overview,
    manage_system_service as apply_system_service_action,
)
from src.gui.backup_manager import (
    get_backup_overview as read_backup_overview,
    get_backup_task as read_backup_task,
    open_timeshift as launch_timeshift,
    preview_backup_restore as inspect_backup_restore,
    register_custom_backup_source as add_custom_backup_source,
    remove_custom_backup_source as discard_custom_backup_source,
    start_backup_restore as begin_backup_restore,
    start_personal_backup as begin_personal_backup,
)
from src.core.settings_manager import (
    clear_assistant_memory,
    get_settings,
    get_system_diagnostics,
    run_system_cleanup,
    save_settings,
    test_llm_connection,
    list_llm_models,
    migrate_keys_to_keyring,
)
from src.gui.windows_guide import search_windows_guide
from src.nlp.processor import NLPProcessor


class JsApi:
    """API expuesta a JavaScript a través de window.pywebview.api."""

    def __init__(self) -> None:
        self.window: Optional[webview.Window] = None
        self._maximized: bool = False
        self._academy = AcademyWindow()
        
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
        self._chat_window: Optional[webview.Window] = None
        self._chat_lock = threading.Lock()
        self._pending_catalog_installs: Dict[str, Dict[str, str]] = {}
        self._code_workspace = CodeWorkspace()

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

    def explain_text(self, kind: str, content: str) -> str:
        """Explica texto localmente, sin enviarlo al agente ni ejecutar herramientas."""
        if kind == "command":
            return explain_command(content)
        if kind == "error":
            return explain_error(content)
        return "Selecciona un tipo de explicación válido."

    def get_windows_guide(self, query: str = "", kind: str = "all") -> list[Dict[str, Any]]:
        """Busca equivalencias de Windows sin instalar ni modificar programas."""
        return search_windows_guide(query, kind)

    def get_windows_guide_icons(self, packages: list[str]) -> Dict[str, str]:
        """Obtiene iconos oficiales de tienda/AppStream para apps recomendadas."""
        if not isinstance(packages, list):
            return {}
        return {
            package: icon
            for value in packages[:40]
            if isinstance(value, str)
            for package in [value.strip()[:100]]
            if package
            for icon in [get_app_icon(package)]
            if icon
        }

    def open_learning(self) -> Dict[str, Any]:
        """Abre o recupera la ventana independiente de cursos."""
        return self._academy.open()

    def open_chat_window(self) -> Dict[str, Any]:
        """Abre o restaura la ventana flotante independiente del Asistente IA."""
        lock = getattr(self, "_chat_lock", None)
        if lock is None:
            lock = threading.Lock()
            self._chat_lock = lock

        with lock:
            try:
                chat_win = getattr(self, "_chat_window", None)
                if chat_win is not None:
                    chat_win.restore()
                    chat_win.show()
                    return {"success": True}

                chat_html = Path(__file__).resolve().parent / "web" / "chat.html"
                if not chat_html.is_file():
                    return {"success": False, "message": "No se encontró la plantilla del chat."}

                window = webview.create_window(
                    "Asistente IA — LinuxMate",
                    url=str(chat_html.resolve()),
                    js_api=self,
                    width=540,
                    height=750,
                    min_size=(420, 520),
                    background_color="#080816",
                    text_select=True,
                )
                if window is None:
                    raise RuntimeError("No se pudo crear la ventana de chat.")

                self._chat_window = window

                def _on_chat_closed():
                    self._chat_window = None

                window.events.closed += _on_chat_closed
                return {"success": True}
            except Exception as exc:
                self._chat_window = None
                return {"success": False, "message": f"No se pudo abrir la ventana del chat: {exc}"}


    def open_settings_window(self) -> Dict[str, Any]:
        """Abre o restaura la ventana de configuración."""
        lock = getattr(self, "_settings_lock", None)
        if lock is None:
            lock = __import__("threading").Lock()
            self._settings_lock = lock

        with lock:
            try:
                settings_win = getattr(self, "_settings_window", None)
                if settings_win is not None:
                    settings_win.restore()
                    settings_win.show()
                    return {"success": True}

                settings_html = __import__("pathlib").Path(__file__).resolve().parent / "web" / "settings.html"
                if not settings_html.is_file():
                    return {"success": False, "message": "No se encontró la plantilla de settings."}

                window = __import__("webview").create_window(
                    "Configuración — LinuxMate",
                    url=str(settings_html.resolve()),
                    js_api=self,
                    width=800,
                    height=700,
                    min_size=(600, 500),
                    background_color="#080816",
                    text_select=True,
                )
                if window is None:
                    raise RuntimeError("No se pudo crear la ventana de configuración.")

                self._settings_window = window

                def _on_settings_closed():
                    self._settings_window = None

                window.events.closed += _on_settings_closed
                return {"success": True}
            except Exception as exc:
                self._settings_window = None
                return {"success": False, "message": f"No se pudo abrir la ventana de configuración: {exc}"}
    def get_learning_summary(self) -> Dict[str, Any]:
        return self._academy.summary()

    def get_code_projects(self) -> Dict[str, Any]:
        try:
            return self._workspace().list_projects()
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def create_code_project(self, name: str, template: str) -> Dict[str, Any]:
        try:
            return self._workspace().create_project(name, template)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def list_code_files(self, project: str) -> Dict[str, Any]:
        try:
            return self._workspace().list_files(project)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def read_code_file(self, project: str, relative_path: str) -> Dict[str, Any]:
        try:
            return self._workspace().read_file(project, relative_path)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def preview_code_change(self, project: str, relative_path: str, content: str) -> Dict[str, Any]:
        try:
            return self._workspace().propose_file_change(project, relative_path, content)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def request_code_change(
        self, project: str, relative_path: str, instruction: str, consent: bool = False
    ) -> Dict[str, Any]:
        """Pide al proveedor configurado una propuesta; nunca escribe directamente."""
        if consent is not True:
            return {"success": False, "message": "Confirma primero que autorizas enviar este archivo al proveedor de IA."}
        if not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 2000:
            return {"success": False, "message": "Describe el cambio en 2.000 caracteres o menos."}
        try:
            current = self._workspace().read_file(project, relative_path)["content"]
            if contains_likely_secret(current):
                return {
                    "success": False,
                    "message": "Detecté texto parecido a una clave o contraseña. Quita ese dato antes de enviar el archivo al modelo.",
                }
            if len(current) > 60_000:
                return {"success": False, "message": "El archivo supera el límite de 60.000 caracteres para una propuesta IA."}
            agent = getattr(self, "agent", None)
            if not agent or not getattr(agent, "_client", None):
                return {"success": False, "message": "Configura un proveedor de IA para pedir propuestas de código."}
            from src.core.providers import completion_options
            provider = getattr(agent, "provider", "groq")
            model = agent.model
            response = agent._client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un tutor de programación. Responde únicamente con el contenido completo y actualizado "
                            "del archivo solicitado. No uses bloques Markdown ni agregues explicación antes o después. "
                            "Conserva las partes no relacionadas y no inventes archivos adicionales."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Lenguaje/archivo: {relative_path}\nInstrucción: {instruction.strip()}\n\n"
                            f"Contenido actual:\n{current}"
                        ),
                    },
                ],
                **completion_options(provider, model, 0.1, 4000),
                timeout=90,
            )
            choices = getattr(response, "choices", [])
            content = choices[0].message.content if choices else None
            if not isinstance(content, str) or not content.strip():
                return {"success": False, "message": "El modelo no devolvió una propuesta de código."}
            proposed = content
            wrapped = content.strip()
            if wrapped.startswith("```") and wrapped.endswith("```"):
                proposed = wrapped.split("\n", 1)[1].rsplit("```", 1)[0]
                proposed = proposed.rstrip("\n") + "\n"
            return self._workspace().propose_file_change(project, relative_path, proposed)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}
        except Exception as exc:
            detail = str(exc)
            secret = getattr(getattr(self, "agent", None), "api_key", "")
            if secret:
                detail = detail.replace(secret, "[clave oculta]")
            return {"success": False, "message": f"No se pudo obtener una propuesta: {detail[:240]}"}

    def apply_code_change(self, token: str, confirmed: bool) -> Dict[str, Any]:
        try:
            label = "Antes de cambio aceptado" if confirmed is True else None
            return self._workspace().apply_proposed_change(token, confirmed, checkpoint_label=label)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def save_code_file(self, project: str, relative_path: str, content: str) -> Dict[str, Any]:
        try:
            return self._workspace().write_file(project, relative_path, content)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def open_dev_window(self) -> Dict[str, Any]:
        """Abre o restaura la ventana independiente del Módulo Dev (IDE con Agente IA)."""
        lock = getattr(self, "_dev_lock", None)
        if lock is None:
            lock = threading.Lock()
            self._dev_lock = lock

        with lock:
            try:
                dev_win = getattr(self, "_dev_window", None)
                if dev_win is not None:
                    dev_win.restore()
                    dev_win.show()
                    return {"success": True}

                dev_html = Path(__file__).resolve().parent / "web" / "dev.html"
                if not dev_html.is_file():
                    return {"success": False, "message": "No se encontró la plantilla del Módulo Dev."}

                window = webview.create_window(
                    "LinuxMate Dev Studio — Agente de Programación IA",
                    url=str(dev_html.resolve()),
                    js_api=self,
                    width=1360,
                    height=840,
                    min_size=(1040, 660),
                    background_color="#0d1117",
                    text_select=True,
                )
                if window is None:
                    raise RuntimeError("No se pudo crear la ventana del Módulo Dev.")

                self._dev_window = window

                def _on_dev_closed():
                    self._dev_window = None

                window.events.closed += _on_dev_closed
                return {"success": True}
            except Exception as exc:
                self._dev_window = None
                return {"success": False, "message": f"No se pudo abrir la ventana del Módulo Dev: {exc}"}

    def get_dev_status(self) -> Dict[str, Any]:
        """Devuelve el estado del sandbox bwrap, runtimes, proveedores IA, plantillas y tutoriales del Módulo Dev."""
        from src.core.dev_agent import STARTER_RECIPES, TUTORIALS

        orch = self._dev_orchestrator()
        status = orch.sandbox.status()
        projects = orch.ensure_starter_project()
        cfg = get_settings()
        llm_cfg = cfg.get("llm", {})
        active_provider = llm_cfg.get("provider", "groq")
        providers_list = []
        for item in cfg.get("providers", []):
            pid = item["id"]
            key_val = llm_cfg.get(f"{pid}_api_key", "")
            model_val = llm_cfg.get(f"{pid}_model", item.get("model", ""))
            url_val = llm_cfg.get(f"{pid}_base_url", item.get("base_url", ""))
            providers_list.append(
                {
                    **item,
                    "configured": bool(key_val) or pid == "ollama",
                    "masked_key": (f"{key_val[:6]}…{key_val[-4:]}" if len(key_val) > 10 else ("Configurada" if key_val else "")),
                    "current_model": model_val,
                    "current_base_url": url_val,
                }
            )
        return {
            "success": True,
            "sandbox": status,
            "projects": projects.get("projects", []),
            "root": projects.get("root", ""),
            "active_provider": active_provider,
            "active_model": llm_cfg.get(f"{active_provider}_model", ""),
            "providers": providers_list,
            "recipes": [
                {"id": key, "title": val["title"], "template": val["template"], "description": val["description"]}
                for key, val in STARTER_RECIPES.items()
            ],
            "tutorials": TUTORIALS,
        }

    def save_dev_provider(
        self,
        provider: str,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        set_active: bool = True,
    ) -> Dict[str, Any]:
        """Guarda credenciales/modelo de cualquier proveedor desde el Módulo Dev y recarga el agente."""
        provider = (provider or "").strip().lower()
        llm_payload: Dict[str, Any] = {}
        if set_active:
            llm_payload["provider"] = provider
        if api_key.strip():
            llm_payload[f"{provider}_api_key"] = api_key.strip()
        if model.strip():
            llm_payload[f"{provider}_model"] = model.strip()
        if base_url.strip():
            llm_payload[f"{provider}_base_url"] = base_url.strip()

        res = self.save_settings({"llm": llm_payload, "security": {}, "appearance": {}})
        return res

    def test_dev_provider(
        self, provider: str, api_key: str = "", model: str = "", base_url: str = ""
    ) -> Dict[str, Any]:
        """Prueba en vivo la conexión con el proveedor seleccionado desde el Módulo Dev."""
        provider = (provider or "").strip().lower()
        cfg = get_settings().get("llm", {})
        resolved_key = api_key.strip() or cfg.get(f"{provider}_api_key", "")
        resolved_model = model.strip() or cfg.get(f"{provider}_model", "")
        resolved_url = base_url.strip() or cfg.get(f"{provider}_base_url", "")
        return test_llm_connection(provider, resolved_key, resolved_model, resolved_url)

    def fetch_dev_provider_models(
        self, provider: str, api_key: str = "", base_url: str = ""
    ) -> Dict[str, Any]:
        provider = (provider or "").strip().lower()
        cfg = get_settings().get("llm", {})
        resolved_key = api_key.strip() or cfg.get(f"{provider}_api_key", "")
        resolved_url = base_url.strip() or cfg.get(f"{provider}_base_url", "")
        return list_llm_models(provider, resolved_key, resolved_url)

    def create_dev_recipe_project(self, name: str, recipe_id: str) -> Dict[str, Any]:
        try:
            return self._dev_orchestrator().create_from_recipe(name, recipe_id)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def search_dev_project(self, project: str, query: str) -> Dict[str, Any]:
        try:
            return self._dev_orchestrator().search_in_project(project, query)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def run_code_in_sandbox(self, project: str, relative_path: str, stdin_text: str = "") -> Dict[str, Any]:
        try:
            session_id = getattr(self, "session_id", None)
            return self._dev_orchestrator().run_project_file(
                project, relative_path, stdin_text=stdin_text, session_id=session_id
            )
        except (OSError, WorkspaceError, ValueError) as exc:
            return {"success": False, "message": str(exc)}

    def explain_dev_failure(self, project: str, raw_error: str = "") -> Dict[str, Any]:
        from src.core.dev_agent import translate_dev_error

        orch = self._dev_orchestrator()
        last = orch.last_run_by_project.get(project) or {}
        err_text = raw_error or last.get("stderr") or last.get("stdout") or ""
        exp = translate_dev_error(err_text, last.get("stdout", ""), last.get("exit_code"))
        return {"success": True, "explanation": exp}

    def dev_agent_chat(
        self,
        project: str,
        active_file: str,
        message: str,
        mode: str = "guided",
        provider: str = "",
        model: str = "",
    ) -> Dict[str, Any]:
        try:
            agent = getattr(self, "agent", None)
            return self._dev_orchestrator().chat_with_agent(
                project=project,
                active_file=active_file,
                message=message,
                agent=agent,
                mode=mode,
                provider=provider,
                model=model,
            )
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def clear_dev_chat(self, project: str) -> Dict[str, Any]:
        self._dev_orchestrator().clear_project_history(project)
        return {"success": True}

    def list_code_checkpoints(self, project: str) -> Dict[str, Any]:
        try:
            return self._workspace().list_checkpoints(project)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def create_code_checkpoint(self, project: str, label: str = "") -> Dict[str, Any]:
        try:
            return self._workspace().create_checkpoint(project, label or "Checkpoint manual")
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def restore_code_checkpoint(self, project: str, checkpoint_id: str) -> Dict[str, Any]:
        try:
            return self._workspace().restore_checkpoint(project, checkpoint_id)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def export_code_project(self, project: str, destination: str = "Documentos") -> Dict[str, Any]:
        try:
            return self._dev_orchestrator().export_project(project, destination)
        except (OSError, WorkspaceError) as exc:
            return {"success": False, "message": str(exc)}

    def lookup_dev_docs(self, query: str) -> Dict[str, Any]:
        return self._dev_orchestrator().sandbox.lookup_docs(query)

    def _workspace(self) -> CodeWorkspace:
        workspace = getattr(self, "_code_workspace", None)
        if workspace is None:
            workspace = CodeWorkspace()
            self._code_workspace = workspace
        return workspace

    def _dev_orchestrator(self):
        import importlib
        import src.core.dev_agent as dev_agent_mod

        dev_file = getattr(dev_agent_mod, "__file__", "")
        try:
            current_mtime = os.path.getmtime(dev_file) if dev_file else 0.0
        except OSError:
            current_mtime = 0.0

        last_mtime = getattr(self, "_dev_agent_mtime", 0.0)
        orch = getattr(self, "_dev_orch", None)
        ws = self._workspace()

        if last_mtime and current_mtime > last_mtime:
            try:
                dev_agent_mod = importlib.reload(dev_agent_mod)
                orch = None
            except Exception:
                pass

        if orch is None or orch.workspace is not ws:
            orch = dev_agent_mod.DevOrchestrator(ws)
            self._dev_orch = orch
            self._dev_agent_mtime = current_mtime
        return orch

    # =========================================================================
    # 3. TELEMETRÍA DEL SISTEMA EN TIEMPO REAL
    # =========================================================================
    def get_system_stats(self) -> Dict[str, Any]:
        """Devuelve porcentaje de CPU, RAM, disco, paquetes y estado de actualizaciones."""
        try:
            cpu = round(psutil.cpu_percent(interval=None), 1)
            vmem = psutil.virtual_memory()
            ram = round(vmem.percent, 1)
            ram_used_gb = round(vmem.used / (1024**3), 1)
            ram_total_gb = round(vmem.total / (1024**3), 1)
            ram_avail_gb = round(vmem.available / (1024**3), 1)
            cpu_temp = get_cpu_temperature()

            disk = psutil.disk_usage("/")
            disk_percent = round(disk.percent, 1)
            disk_used_gb = round(disk.used / (1024**3), 1)
            disk_total_gb = round(disk.total / (1024**3), 1)
            disk_free_gb = round(disk.free / (1024**3), 1)

            try:
                pids_count = len(psutil.pids())
            except Exception:
                pids_count = 180

            try:
                load_avg = round(os.getloadavg()[0], 2)
            except Exception:
                load_avg = round(cpu / 50.0, 2)

            now = time.time()
            last_check = getattr(self, "_last_updates_check", 0.0)
            if now - last_check > 30.0:
                self._cached_updates = self._check_pending_updates()
                self._last_updates_check = now

            cached_updates = getattr(self, "_cached_updates", 0)

            # Resumen de academia
            academy = getattr(self, "_academy", None)
            academy_completed = 0
            academy_total = 60
            if academy:
                try:
                    summ = academy.summary()
                    if isinstance(summ, dict):
                        academy_completed = summ.get("completed", 0)
                        academy_total = summ.get("total", 60)
                except Exception:
                    pass

            pkg_count = self._get_packages_count()

            return {
                "cpu_percent": cpu,
                "ram_percent": ram,
                "ram_used_gb": ram_used_gb,
                "ram_total_gb": ram_total_gb,
                "ram_available_gb": ram_avail_gb,
                "disk_percent": disk_percent,
                "disk_used_gb": disk_used_gb,
                "disk_total_gb": disk_total_gb,
                "disk_free_gb": disk_free_gb,
                "process_count": pids_count,
                "load_avg": load_avg,
                "cpu_temp": cpu_temp,
                "updates_pending": cached_updates,
                "packages_count": pkg_count,
                "academy_completed": academy_completed,
                "academy_total": academy_total,
            }
        except Exception:
            return {
                "cpu_percent": 0.0,
                "ram_percent": 0.0,
                "updates_pending": 0,
            }

    def _get_packages_count(self) -> int:
        status_file = Path("/var/lib/dpkg/status")
        if status_file.is_file():
            try:
                return status_file.read_text(encoding="utf-8", errors="ignore").count("Package: ")
            except Exception:
                pass
        return 2802

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
        from src.core.distro import detect_distro
        distro = detect_distro()

        return {
            "name": distro.pretty_name,
            "version": distro.version_id,
            "kernel": platform.release(),
            "arch": platform.machine(),
            "family": distro.family.value,
            "package_manager": distro.native_package_manager,
            "available_package_managers": distro.available_package_managers,
        }

    # =========================================================================
    # 4. ACCIONES RÁPIDAS Y HERRAMIENTAS
    # =========================================================================
    def run_action(self, action_id: str) -> str:
        """Ejecuta una de las acciones del dashboard de forma guiada y segura."""
        action_id = (action_id or "").strip()

        if action_id == "update_system":
            from src.core.distro import get_package_profile
            cmd = get_package_profile().update
            # Keep this guided entry interactive so the package manager can show
            # its proposed changes and ask the user before applying them.
            cmd = re.sub(r"\s+(?:-y|--noconfirm)(?=\s|$)", "", cmd)
            ok, msg = launch_in_terminal(cmd, "Actualizar Sistema — LinuxMate AI")
            if ok:
                return "🚀 Se abrió la ventana de terminal para actualizar el sistema. Revisa los cambios propuestos por el gestor antes de aceptarlos."
            return f"Comando para actualizar tu sistema:\n```bash\n{cmd}\n```"

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
            from src.core.distro import get_package_profile
            cmd = get_package_profile().clean
            ok, _ = launch_in_terminal(cmd, "Limpieza de Paquetes — LinuxMate AI")
            return (
                f"🧹 Se liberaron **{cleaned_mb:.1f} MB** de caché local de miniaturas.\n"
                f"Se abrió el gestor de paquetes ({get_package_profile().manager}) para revisar la limpieza."
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

            try:
                from src.core.distro import detect_distro
                distro = detect_distro()
                manager = distro.native_package_manager
                distro_name = distro.pretty_name
            except Exception:
                manager = "apt"
                distro_name = "tu distribución"

            driver_commands = {
                "apt": "ubuntu-drivers devices\nlspci -nnk | grep -EA3 'VGA|3D|Display'",
                "dnf": "lspci -nnk | grep -EA3 'VGA|3D|Display'\ndnf list installed '*nvidia*' '*mesa*' '*firmware*'",
                "pacman": "lspci -nnk | grep -EA3 'VGA|3D|Display'\npacman -Qs 'mesa|nvidia|vulkan|firmware'",
                "zypper": "lspci -nnk | grep -EA3 'VGA|3D|Display'\nzypper se -i mesa kernel-firmware",
            }
            driver_cmd = driver_commands.get(manager, driver_commands["apt"])

            return (
                f"⚙️ **Controladores y Tarjeta Gráfica ({distro_name})**:\n{vga_info}\n\n"
                f"Para revisar los controladores activos y recomendados en {distro_name}:\n"
                f"```bash\n{driver_cmd}\n```"
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
            report = diagnose_system()
            lines = ["Diagnóstico del sistema:"]
            lines.extend(f"- {check['title']}: {check['detail']}" for check in report["checks"])
            return "\n".join(lines)

        elif action_id == "uninstall_manager":
            return (
                "🗑️ **Desinstalador Seguro de Aplicaciones**:\n\n"
                "Para desinstalar una app sin dañar el resto del sistema:\n"
                "1. `sudo apt remove <nombre-app>` : Desinstala la app conservando tus configuraciones.\n"
                "2. `sudo apt purge <nombre-app>` : Desinstala la app y elimina sus configuraciones.\n"
                "3. `sudo apt autoremove` : Elimina paquetes que ya no son necesarios."
            )

        return f"Acción '{action_id}' reconocida y registrada."

    def search_installed_apps(self, query: str, source: str = "auto") -> list[Dict[str, Any]]:
        """Busca aplicaciones instaladas sin modificar el sistema."""
        query = (query or "").strip()
        source = (source or "auto").strip().lower()
        if not query:
            return []
        if source not in {"auto", "apt", "dnf", "pacman", "zypper", "snap", "flatpak", "desktop"}:
            source = "auto"

        try:
            candidates = find_uninstall_candidates(query, source=source)
        except Exception:
            return []

        results: list[Dict[str, Any]] = []
        for candidate in candidates[:8]:
            package = str(candidate.get("package") or "").strip()
            if not package:
                continue
            results.append(
                {
                    "source": str(candidate.get("source") or "auto"),
                    "package": package,
                    "name": str(candidate.get("name") or candidate.get("display_name") or package),
                    "score": float(candidate.get("score") or 0.0),
                }
            )
        return results

    def uninstall_app(self, package_name: str, source: str = "auto") -> str:
        """Prepara una desinstalación validada en una terminal interactiva."""
        package_name = (package_name or "").strip()
        source = (source or "auto").strip().lower()
        if not package_name:
            return "Indica qué aplicación quieres desinstalar."

        try:
            command, resolved_source, resolved_package = build_interactive_uninstall_command(
                package_name,
                source,
            )
        except ValueError as exc:
            return str(exc)
        except Exception as exc:
            return f"No se pudo preparar la desinstalación: {exc}"

        ok, message = launch_in_terminal(
            command,
            f"Desinstalar {resolved_package} — LinuxMate AI",
        )
        if ok:
            return (
                f"Se abrió una terminal para quitar '{resolved_package}' mediante "
                f"{resolved_source}. Revisa el comando y confirma en la terminal."
            )
        return f"No se pudo abrir la terminal: {message}"

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
    def get_app_catalog(
        self,
        source: str = "all",
        category: str = "all",
        query: str = "",
        offset: int = 0,
        limit: int = 16,
        refresh_installed: bool = False,
    ) -> Dict[str, Any]:
        """Combina los catálogos disponibles con estado, distribución y gestor recomendado."""
        return get_catalog(
            source=source,
            category=category,
            query=query,
            offset=offset,
            limit=limit,
            refresh_installed=refresh_installed,
        )

    def get_system_diagnostic(self) -> Dict[str, Any]:
        """Comprueba el equipo sin modificarlo."""
        return diagnose_system()

    def get_setup_plan(self, profile: str = "daily") -> Dict[str, Any]:
        """Genera la ruta del configurador guiado adaptada a la distribución detectada."""
        return read_setup_plan(profile)

    def run_setup_action(self, action_id: str, profile: str = "daily") -> Dict[str, Any]:
        """Ejecuta en una terminal interactiva un paso del configurador guiado."""
        return execute_setup_action(action_id, profile)

    def get_problem_guides(self) -> Dict[str, Any]:
        """Devuelve flujos guiados para problemas frecuentes."""
        return get_problem_guides()

    def run_problem_checks(self, issue_id: str, application: str = "", target_path: str = "") -> Dict[str, Any]:
        """Ejecuta solo consultas locales predefinidas para el problema elegido."""
        return run_problem_checks(issue_id, application, target_path)

    def run_problem_action(self, action_id: str) -> Dict[str, Any]:
        """Ejecuta una acción de reparación guiada tras confirmación explícita del usuario."""
        return execute_problem_action(action_id)

    def get_system_logs(
        self, priority: str = "err", period: str = "24h", source: str = "system", query: str = ""
    ) -> Dict[str, Any]:
        """Consulta registros locales con filtros permitidos y redacta datos sensibles."""
        return read_system_logs(priority, period, source, query)

    def get_service_overview(self) -> Dict[str, Any]:
        """Lista servicios systemd instalados y su estado actual, sin modificarlos."""
        return read_service_overview()

    def get_resource_overview(self) -> Dict[str, Any]:
        """Devuelve métricas locales de recursos, procesos y aplicaciones de inicio."""
        return read_resource_overview()

    def toggle_startup_app(self, desktop_id: str, enabled: bool = True) -> Dict[str, Any]:
        """Activa o desactiva un acceso de autoinicio en la sesión del usuario."""
        return update_startup_app(desktop_id, bool(enabled))

    def stop_user_process(self, pid: int) -> Dict[str, Any]:
        """Solicita terminar un proceso propiedad del usuario actual."""
        return terminate_user_process(pid)

    def manage_system_service(self, unit: str, action: str, confirmed: bool = False) -> Dict[str, Any]:
        """Controla un servicio permitido tras confirmación visible en la interfaz."""
        return apply_system_service_action(unit, action, confirmed)

    def get_backup_overview(self) -> Dict[str, Any]:
        """Devuelve carpetas personales disponibles y respaldos registrados."""
        return read_backup_overview()

    def choose_backup_destination(self) -> Dict[str, Any]:
        """Abre el selector nativo para elegir dónde guardar la copia."""
        if self.window is None:
            return {"success": False, "message": "La ventana de LinuxMate no está disponible."}
        try:
            selection = self.window.create_file_dialog(
                webview.FileDialog.FOLDER,
                directory=str(Path.home()),
                allow_multiple=False,
            )
        except (OSError, RuntimeError, ValueError):
            return {"success": False, "message": "No se pudo abrir el selector de carpetas."}
        if not selection:
            return {"success": False, "cancelled": True, "message": "No se seleccionó una carpeta."}
        selected = selection[0] if isinstance(selection, (list, tuple)) else selection
        return {"success": True, "path": str(selected)}

    def choose_custom_backup_source(self) -> Dict[str, Any]:
        """Añade una carpeta personal desde el selector nativo del sistema."""
        if self.window is None:
            return {"success": False, "message": "La ventana de LinuxMate no está disponible."}
        try:
            selection = self.window.create_file_dialog(
                webview.FileDialog.FOLDER,
                directory=str(Path.home()),
                allow_multiple=False,
            )
        except (OSError, RuntimeError, ValueError):
            return {"success": False, "message": "No se pudo abrir el selector de carpetas."}
        if not selection:
            return {"success": False, "cancelled": True, "message": "No se añadió ninguna carpeta."}
        selected = selection[0] if isinstance(selection, (list, tuple)) else selection
        return add_custom_backup_source(str(selected))

    def remove_custom_backup_source(self, source_id: str) -> Dict[str, Any]:
        """Quita una carpeta añadida de la selección temporal del respaldo."""
        return discard_custom_backup_source(source_id)

    def start_personal_backup(self, categories: list[str], destination: str) -> Dict[str, Any]:
        """Inicia una copia comprimida en segundo plano, sin seguir enlaces simbólicos."""
        return begin_personal_backup(categories, destination)

    def get_backup_task(self, task_id: str) -> Dict[str, Any]:
        """Consulta el progreso de una creación o restauración en curso."""
        return read_backup_task(task_id)

    def preview_backup_restore(self, backup_id: str) -> Dict[str, Any]:
        """Inspecciona el contenido y el destino aislado antes de restaurar."""
        return inspect_backup_restore(backup_id)

    def start_backup_restore(self, backup_id: str) -> Dict[str, Any]:
        """Restaura en una carpeta nueva dentro del home; no sobrescribe archivos."""
        return begin_backup_restore(backup_id)

    def open_timeshift(self) -> Dict[str, Any]:
        """Abre Timeshift para gestionar snapshots del sistema con su propia confirmación."""
        return launch_timeshift()

    def run_diagnostic_fix(self, action_id: str) -> Dict[str, Any]:
        """Ejecuta solo una acción guiada y permitida tras la confirmación en la vista."""
        return execute_diagnostic_fix(action_id)

    def install_catalog_app(self, package: str, source: str, name: str = "") -> Dict[str, Any]:
        """Prepara una vista previa; instalar requiere confirm_catalog_app_install."""
        package = (package or "").strip()
        source = (source or "").strip().lower()
        display_name = (name or package).strip()

        if source not in {"apt", "dnf", "pacman", "zypper", "snap", "flatpak"}:
            return {"success": False, "message": "Origen de paquete no reconocido."}
        if not re.fullmatch(r"[A-Za-z0-9@._:+-]+", package):
            return {"success": False, "message": "El identificador del paquete no es seguro."}

        required_binary = {
            "apt": "apt", "dnf": "dnf", "pacman": "pacman", "zypper": "zypper",
            "snap": "snap", "flatpak": "flatpak",
        }[source]
        if not shutil.which(required_binary):
            return {
                "success": False,
                "message": f"{required_binary} no está instalado o no está disponible en este equipo.",
            }

        if source == "apt":
            command = f"sudo apt install {package}"
        elif source == "dnf":
            command = f"sudo dnf install {package}"
        elif source == "pacman":
            command = f"sudo pacman -S {package}"
        elif source == "zypper":
            command = f"sudo zypper install {package}"
        elif source == "snap":
            classic = package in {"code", "pycharm-community", "intellij-idea-community"}
            command = f"sudo snap install {package}{' --classic' if classic else ''}"
        else:
            command = f"flatpak install {package}"

        token = secrets.token_urlsafe(24)
        if not hasattr(self, "_pending_catalog_installs"):
            self._pending_catalog_installs = {}
        self._pending_catalog_installs[token] = {
            "package": package,
            "source": source,
            "name": display_name,
            "command": command,
        }
        return {
            "success": True,
            "preview": {
                "token": token,
                "name": display_name,
                "package": package,
                "source": source,
                "command": command,
                "size_and_dependencies": "El gestor de paquetes los mostrará antes de aplicar cambios.",
            },
            "message": "Revisa el paquete, el origen y el comando antes de confirmar.",
        }

    def confirm_catalog_app_install(self, token: str, confirmed: bool) -> Dict[str, Any]:
        """Consume una vista previa una sola vez y solo abre el gestor tras confirmación."""
        plan = self._pending_catalog_installs.pop((token or "").strip(), None)
        if plan is None:
            return {"success": False, "message": "La vista previa expiró o ya fue utilizada. Prepara otra vez la instalación."}
        if confirmed is not True:
            return {"success": False, "cancelled": True, "message": "Instalación cancelada; no se abrió ninguna terminal."}

        if plan.get("kind") == "appimage":
            from src.core.appimage import AppImageError, install_appimage
            try:
                destination = install_appimage(plan["path"])
            except AppImageError as exc:
                return {"success": False, "message": str(exc)}
            return {
                "success": True,
                "message": f"{plan['name']} quedó en {destination} y aparecerá en el menú de aplicaciones. LinuxMate no la ejecutó.",
            }

        ok, message = launch_in_terminal(
            plan["command"],
            f"Instalando {plan['name'][:28]} — LinuxMate AI",
        )
        if not ok:
            return {"success": False, "message": f"No se pudo abrir la terminal: {message}"}

        clear_installed_cache()
        return {
            "success": True,
            "message": (
                f"Se abrió una terminal para instalar '{plan['name']}' desde {plan['source'].upper()}. "
                "El gestor mostrará el tamaño y las dependencias y pedirá confirmación antes de instalarlos."
            ),
        }

    def choose_local_package(self) -> Dict[str, Any]:
        """Abre un selector y prepara una vista previa para un .deb o AppImage."""
        if self.window is None:
            return {"success": False, "message": "La ventana no está disponible."}
        try:
            selection = self.window.create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=False,
                file_types=("Aplicaciones Linux (*.deb;*.AppImage)",),
            )
        except (OSError, RuntimeError, ValueError):
            return {"success": False, "message": "No se pudo abrir el selector de archivos."}
        if not selection:
            return {"success": False, "cancelled": True, "message": "No se seleccionó ningún archivo."}
        path_text = selection[0] if isinstance(selection, (list, tuple)) else selection
        return self.prepare_local_package(str(path_text))

    def prepare_local_package(self, path_text: str) -> Dict[str, Any]:
        """Valida archivo local y prepara sus acciones antes de pedir confirmación."""
        from pathlib import Path

        selected = Path(path_text).expanduser()
        if selected.is_symlink():
            return {"success": False, "message": "No instalaré un archivo seleccionado que sea un enlace simbólico."}
        try:
            path = selected.resolve(strict=True)
        except OSError:
            return {"success": False, "message": "No se encontró el archivo seleccionado."}
        if not path.is_file():
            return {"success": False, "message": "La selección no es un archivo normal."}

        suffix = path.suffix.lower()
        if suffix == ".deb":
            from src.core.distro import detect_distro
            if detect_distro().family.value != "debian":
                return {"success": False, "message": "Los paquetes .deb son para Debian, Ubuntu y distribuciones derivadas. En este equipo usa el gestor nativo o un AppImage oficial."}
            if not shutil.which("apt"):
                return {"success": False, "message": "APT no está disponible en este equipo."}
            try:
                with path.open("rb") as handle:
                    if handle.read(8) != b"!<arch>\n":
                        raise ValueError
            except (OSError, ValueError):
                return {"success": False, "message": "El archivo no parece ser un paquete .deb válido."}
            source = "deb-local"
            command = f"sudo apt install {shlex.quote(str(path))}"
            action_label = "Comando exacto"
            size_and_dependencies = "APT resolverá las dependencias y mostrará cualquier cambio antes de instalar."
            plan_kind = "deb"
        elif suffix == ".appimage":
            from src.core.appimage import AppImageError, validate_appimage
            try:
                path = validate_appimage(str(path))
            except AppImageError as exc:
                return {"success": False, "message": str(exc)}
            source = "AppImage local"
            command = f"Copiar a ~/Applications/{path.stem}.AppImage y crear un acceso en el menú."
            action_label = "Acción prevista"
            size_and_dependencies = "No requiere permisos de administrador. Usa AppImages descargados del sitio oficial: al abrirlos, ejecutan código con los permisos de tu usuario."
            plan_kind = "appimage"
        else:
            return {"success": False, "message": "Elige un archivo .deb o .AppImage."}

        token = secrets.token_urlsafe(24)
        if not hasattr(self, "_pending_catalog_installs"):
            self._pending_catalog_installs = {}
        name = path.name
        self._pending_catalog_installs[token] = {
            "kind": plan_kind,
            "path": str(path),
            "name": name,
            "source": source,
            "command": command,
        }
        return {
            "success": True,
            "preview": {
                "token": token,
                "name": name,
                "package": str(path),
                "source": source,
                "command": command,
                "action_label": action_label,
                "size_and_dependencies": size_and_dependencies,
            },
            "message": "Revisa el archivo y la acción antes de confirmar.",
        }

    def install_app(self, app_id: str) -> Dict[str, Any]:
        """Prepara una vista previa para las acciones heredadas de instalación rápida."""
        app_id = (app_id or "").strip().lower()

        app_commands = {
            "code": "sudo apt install -y code || sudo snap install --classic code",
            "google-chrome": "wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && sudo apt install -y /tmp/chrome.deb && rm /tmp/chrome.deb",
            "steam": "sudo apt update && sudo apt install -y steam",
            "timeshift": "sudo apt update && sudo apt install -y timeshift",
        }

        command = app_commands.get(app_id)
        if not command:
            return {"success": False, "message": f"Aplicación '{app_id}' no reconocida en el catálogo rápido."}
        token = secrets.token_urlsafe(24)
        if not hasattr(self, "_pending_catalog_installs"):
            self._pending_catalog_installs = {}
        self._pending_catalog_installs[token] = {
            "package": app_id,
            "source": "apt",
            "name": app_id,
            "command": command,
        }
        return {
            "success": True,
            "preview": {
                "token": token,
                "name": app_id,
                "package": app_id,
                "source": "apt",
                "command": command,
                "size_and_dependencies": "El gestor de paquetes los mostrará antes de aplicar cambios.",
            },
        }

    # =========================================================================
    # 7. CONFIGURACIÓN Y GESTIÓN DE MODELOS
    # =========================================================================
    def get_settings(self) -> Dict[str, Any]:
        """Obtiene la configuración completa para la vista de ajustes."""
        return get_settings()

    def save_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda configuraciones en .env y recarga el agente en caliente."""
        result = save_settings(payload)
        if result.get("success"):
            try:
                self.agent = create_agent()
                self.session_id = self.agent.session_id if self.agent else self.session_id
            except Exception:
                pass
            self.nlp = NLPProcessor()
        return result

    def test_llm_connection(
        self,
        provider: str,
        api_key: str,
        model: str,
        base_url: str = "",
    ) -> Dict[str, Any]:
        """Prueba de conexión en vivo con el proveedor LLM."""
        return test_llm_connection(provider, api_key, model, base_url)

    def list_llm_models(self, provider: str, api_key: str, base_url: str = "") -> Dict[str, Any]:
        return list_llm_models(provider, api_key, base_url)

    def clear_chat_memory(self) -> Dict[str, Any]:
        """Vacia la memoria persistente del asistente."""
        res = clear_assistant_memory()
        if self.agent and hasattr(self.agent, "clear_session_history"):
            try:
                self.agent.clear_session_history(clear_persistent=True)
            except Exception:
                pass
        return res

    def run_system_cleanup(self) -> Dict[str, Any]:
        """Ejecuta limpieza segura de archivos temporales y miniaturas."""
        return run_system_cleanup()

    def get_system_environment_diagnostics(self) -> Dict[str, Any]:
        """Diagnóstico de herramientas del sistema."""
        return get_system_diagnostics()

    def get_keyring_status(self) -> Dict[str, Any]:
        """Obtiene el estado del almacén seguro de claves (Keyring)."""
        from src.core.keyring_manager import get_keyring_status
        return get_keyring_status()

    def migrate_api_keys_to_keyring(self) -> Dict[str, Any]:
        """Migra las claves de API existentes en .env hacia el keyring del escritorio."""
        return migrate_keys_to_keyring()

    def get_polkit_status(self) -> Dict[str, Any]:
        """Obtiene el estado de PolicyKit (pkexec) y elevación de privilegios."""
        from src.core.privilege import get_privilege_status
        return get_privilege_status()


def run_webview(debug: bool = False, learning: bool = False) -> None:
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
    webview.start(func=api.open_learning if learning else None, gui="qt", debug=debug)


if __name__ == "__main__":
    run_webview(debug=True)

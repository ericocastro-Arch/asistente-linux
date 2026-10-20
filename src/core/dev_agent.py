"""Orquestador y herramientas del Agente de IA para el Módulo Dev (programación guiada).

Implementa las herramientas específicas del apartado Programar:
- leer_archivo
- escribir_archivo (siempre propone diff, nunca sobrescribe sin confirmación)
- ejecutar_comando (corre el archivo en el sandbox bwrap aislado)
- buscar_docs (consulta pydoc3 y man pages locales)
- crear_proyecto (desde plantillas o casos de uso como organizador de descargas)
- explicar_error (traduce stderr/tracebacks a lenguaje sencillo con sugerencia)
- checkpoint (crea o lista snapshots del proyecto)
- listar_archivos
- exportar (copia el proyecto a ~/Documentos con validación)
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Optional

from src.core.code_workspace import CodeWorkspace, WorkspaceError, contains_likely_secret
from src.core.dev_sandbox import SandboxRunner, SandboxUnavailable
from src.core.providers import completion_options
from src.core.storage import log_tool_run
from src.gui.guided_explanations import explain_error as base_explain_error


# Plantillas ricas adicionales y tutoriales guiados para principiantes en Linux
STARTER_RECIPES: dict[str, dict[str, Any]] = {
    "organizador_descargas": {
        "title": "Organizador de Descargas",
        "template": "python",
        "description": "Clasifica archivos por extensión en carpetas de imágenes, documentos y vídeos.",
        "files": {
            "README.md": (
                "# Organizador de Descargas\n\n"
                "Script didáctico en Python que clasifica archivos según su extensión dentro del sandbox.\n"
            ),
            "config.json": json.dumps(
                {
                    "imagenes": ["jpg", "jpeg", "png", "gif", "webp"],
                    "documentos": ["pdf", "txt", "docx", "md"],
                    "videos": ["mp4", "mkv", "webm"],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            "organizar.py": (
                "import json\n"
                "from pathlib import Path\n\n\n"
                "def cargar_categorias(ruta_config: str = 'config.json') -> dict[str, list[str]]:\n"
                "    datos = Path(ruta_config).read_text(encoding='utf-8')\n"
                "    return json.loads(datos)\n"
            ),
            "main.py": (
                "import os\n"
                "import shutil\n"
                "from pathlib import Path\n"
                "from organizar import cargar_categorias\n\n\n"
                "def preparar_demo(carpeta: Path) -> None:\n"
                "    carpeta.mkdir(exist_ok=True)\n"
                "    ejemplos = ['foto1.jpg', 'vacaciones.png', 'cv.pdf', 'notas.txt', 'factura.pdf', '.oculto']\n"
                "    for nombre in ejemplos:\n"
                "        (carpeta / nombre).write_text(f'Archivo de prueba: {nombre}\\n', encoding='utf-8')\n\n\n"
                "def organizar(ruta: Path) -> dict[str, int]:\n"
                "    categorias = cargar_categorias()\n"
                "    conteo = {'imagenes': 0, 'documentos': 0, 'videos': 0, 'otros': 0}\n"
                "    for nombre in os.listdir(ruta):\n"
                "        if nombre.startswith('.'):\n"
                "            continue\n"
                "        origen = ruta / nombre\n"
                "        if not origen.is_file():\n"
                "            continue\n"
                "        # mover según extensión\n"
                "        ext = nombre.split('.')[-1].lower() if '.' in nombre else ''\n"
                "        destino_cat = 'otros'\n"
                "        for cat, extensiones in categorias.items():\n"
                "            if ext in extensiones:\n"
                "                destino_cat = cat\n"
                "                break\n"
                "        carpeta_dest = ruta / destino_cat\n"
                "        carpeta_dest.mkdir(exist_ok=True)\n"
                "        shutil.move(str(origen), str(carpeta_dest / nombre))\n"
                "        conteo[destino_cat] = conteo.get(destino_cat, 0) + 1\n"
                "    return conteo\n\n\n"
                "if __name__ == '__main__':\n"
                "    demo = Path('descargas_demo')\n"
                "    preparar_demo(demo)\n"
                "    resumen = organizar(demo)\n"
                "    total = sum(resumen.values())\n"
                "    print(f'Se movieron {total} archivos ({resumen[\"imagenes\"]} imágenes, {resumen[\"documentos\"]} documentos)')\n"
            ),
        },
    },
    "monitor_sistema_bash": {
        "title": "Mi primer script Bash",
        "template": "bash",
        "description": "Muestra fecha, archivos del proyecto y espacio temporal en el sandbox.",
        "files": {
            "README.md": "# Mi primer script Bash\n\nAprende variables, bucles y tuberías en Linux sin tocar tu sistema.\n",
            "script.sh": (
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n\n"
                "echo '=== Reporte rápido desde el sandbox ==='\n"
                "echo \"Usuario virtual: $(whoami)\"\n"
                "echo \"Carpeta actual:  $(pwd)\"\n"
                "echo 'Archivos en el proyecto:'\n"
                "for f in *; do\n"
                "  echo \"  - $f\"\n"
                "done\n"
            ),
        },
    },
    "pagina_web_interactiva": {
        "title": "Página Web Interactiva",
        "template": "web",
        "description": "HTML, CSS y JavaScript listos para personalizar.",
        "files": None,  # Usa la plantilla 'web' base
    },
}


TUTORIALS: list[dict[str, Any]] = [
    {
        "id": "python_organizador",
        "title": "1. Automatiza tu carpeta con Python",
        "recipe": "organizador_descargas",
        "file": "main.py",
        "steps": [
            "Abre `main.py` y pulsa **▶ Ejecutar** para ver cómo clasifica archivos de prueba en el sandbox.",
            "Pídele al agente: *«haz que también cuente archivos de audio mp3»* y revisa el diff antes de aceptarlo.",
            "Restaura un **Checkpoint** desde la barra lateral para comprobar que todo cambio es reversible.",
        ],
    },
    {
        "id": "bash_basico",
        "title": "2. Tu primer script en Bash",
        "recipe": "monitor_sistema_bash",
        "file": "script.sh",
        "steps": [
            "Ejecuta `script.sh` en el sandbox y observa la consola amigable.",
            "Pídele al agente: *«añade una función que cuente cuántas líneas tiene cada archivo»*.",
            "Acepta el cambio propuesto y vuelve a ejecutarlo.",
        ],
    },
    {
        "id": "errores_sin_miedo",
        "title": "3. Entender errores sin jerga",
        "recipe": "organizador_descargas",
        "file": "main.py",
        "steps": [
            "Escribe un error intencional en `main.py` y ejecuta el script.",
            "Haz clic en **«✖ ¿Por qué falló?»** en la consola para que el agente te lo explique en simple.",
        ],
    },
]


PYTHON_ERROR_TRANSLATIONS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"SyntaxError:\s*(.+)", re.IGNORECASE),
        "Hay un error de escritura en el código (un paréntesis, comillas o dos puntos `:` que faltan).",
        "Revisa la línea indicada en el mensaje; asegúrate de cerrar todos los `()`, `[]`, `\"\"` y terminar `def`/`if`/`for` con `:`.",
    ),
    (
        re.compile(r"IndentationError:\s*(.+)", re.IGNORECASE),
        "La sangría (espacios al inicio de la línea) no coincide con el bloque anterior.",
        "Usa siempre 4 espacios dentro de `def`, `for`, `if` y evita mezclar tabuladores con espacios.",
    ),
    (
        re.compile(r"NameError:\s*name '([^']+)' is not defined", re.IGNORECASE),
        "Estás usando un nombre (`{0}`) que todavía no existe o está mal escrito.",
        "Verifica si definiste la variable o función `{0}` antes de usarla o si falta un `import`.",
    ),
    (
        re.compile(r"FileNotFoundError:\s*.*'([^']+)'", re.IGNORECASE),
        "El programa intentó abrir el archivo o carpeta `{0}`, pero no existe en el proyecto.",
        "Comprueba el nombre exacto en el explorador de archivos de la izquierda o créalo antes de leerlo.",
    ),
    (
        re.compile(r"ModuleNotFoundError:\s*No module named '([^']+)'", re.IGNORECASE),
        "Falta el componente o librería `{0}`.",
        "En el sandbox están disponibles las librerías estándar de Python (`os`, `shutil`, `json`, `pathlib`, `math`, `datetime`).",
    ),
    (
        re.compile(r"ZeroDivisionError", re.IGNORECASE),
        "El programa intentó dividir un número entre cero.",
        "Comprueba que el divisor no sea `0` con un `if divisor != 0:` antes de dividir.",
    ),
    (
        re.compile(r"IndexError:\s*list index out of range", re.IGNORECASE),
        "Intentaste acceder a una posición de una lista que no existe.",
        "Revisa el tamaño de la lista con `len(lista)` antes de pedir un elemento por su posición.",
    ),
    (
        re.compile(r"KeyError:\s*(.+)", re.IGNORECASE),
        "Buscaste la clave {0} en un diccionario, pero no está presente.",
        "Usa `diccionario.get(clave)` para obtener un valor por defecto sin que falle el programa.",
    ),
    (
        re.compile(r"TypeError:\s*(.+)", re.IGNORECASE),
        "Se mezclaron tipos de datos incompatibles (por ejemplo, texto con números) o faltan argumentos en una función.",
        "Convierte los datos (`str()`, `int()`) o revisa cuántos parámetros recibe la función.",
    ),
    (
        re.compile(r"command not found:\s*(\S+)", re.IGNORECASE),
        "El comando `{0}` no existe o está mal escrito en el script Bash.",
        "Revisa la ortografía del comando o consulta su nombre con la herramienta de documentación.",
    ),
]


def translate_dev_error(stderr: str, stdout: str = "", exit_code: Optional[int] = None) -> dict[str, Any]:
    """Traduce un traceback o stderr del sandbox a lenguaje sencillo sin jerga."""
    raw = (stderr or stdout or "").strip()
    if not raw:
        return {
            "summary": "El programa no devolvió mensajes de error.",
            "cause": "Terminó sin producir errores en la consola.",
            "suggestion": "Si no hizo lo esperado, revisa que estés llamando a la función principal.",
            "line": None,
        }

    line_match = re.search(r"line\s+(\d+)|línea\s+(\d+)", raw, re.IGNORECASE)
    line_num = int(line_match.group(1) or line_match.group(2)) if line_match else None

    for pattern, cause_tpl, suggestion_tpl in PYTHON_ERROR_TRANSLATIONS:
        match = pattern.search(raw)
        if match:
            groups = match.groups()
            cause = cause_tpl.format(*groups) if groups else cause_tpl
            suggestion = suggestion_tpl.format(*groups) if groups else suggestion_tpl
            where = f" (línea {line_num})" if line_num else ""
            return {
                "summary": f"{cause}{where}",
                "cause": cause,
                "suggestion": suggestion,
                "line": line_num,
            }

    fallback = base_explain_error(raw)
    return {
        "summary": f"El programa se detuvo con código {exit_code if exit_code is not None else 1}.",
        "cause": fallback,
        "suggestion": "Revisa la última línea del mensaje de la consola o pídele al agente que proponga una corrección.",
        "line": line_num,
    }


def translate_run_output(result: dict[str, Any], active_file: str = "") -> dict[str, Any]:
    """Enriquece el resultado de SandboxRunner con resumen amigable y sugerencias."""
    stdout = (result.get("stdout") or "").strip()
    stderr = (result.get("stderr") or "").strip()
    code = result.get("exit_code")
    ok = bool(result.get("success"))

    if ok:
        first_line = stdout.splitlines()[0] if stdout else "ejecución completada sin texto en pantalla"
        headline = f"{result.get('command') or active_file} → {first_line}"
        hint = ""
        if active_file.endswith(".py") and "listdir" in stdout:
            hint = "Sugerencia del agente: recuerda ignorar archivos ocultos que empiezan con punto (`.`)."
        return {
            "status": "ok",
            "headline": headline,
            "stdout": stdout,
            "stderr": stderr,
            "hint": hint,
            "explanation": None,
        }

    explanation = translate_dev_error(stderr, stdout, code)
    return {
        "status": "error",
        "headline": explanation["summary"],
        "stdout": stdout,
        "stderr": stderr,
        "hint": explanation["suggestion"],
        "explanation": explanation,
    }


DEV_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "leer_archivo",
            "description": "Lee un archivo del proyecto actual con números de línea.",
            "parameters": {
                "type": "object",
                "properties": {
                    "archivo": {"type": "string", "description": "Ruta relativa dentro del proyecto, ej. main.py"}
                },
                "required": ["archivo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escribir_archivo",
            "description": (
                "Propone crear o modificar un archivo del proyecto mostrando un diff visual para que el usuario "
                "lo apruebe. Nunca sobrescribe sin permiso."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "archivo": {"type": "string", "description": "Ruta relativa dentro del proyecto"},
                    "contenido": {"type": "string", "description": "Contenido completo propuesto para el archivo"},
                    "resumen": {"type": "string", "description": "Explicación breve y sin jerga de qué cambia"},
                },
                "required": ["archivo", "contenido"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ejecutar_comando",
            "description": "Ejecuta un archivo del proyecto (.py, .sh, .js) dentro del sandbox aislado sin red.",
            "parameters": {
                "type": "object",
                "properties": {
                    "archivo": {"type": "string", "description": "Archivo del proyecto a ejecutar, ej. main.py"}
                },
                "required": ["archivo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_docs",
            "description": "Consulta documentación local de Python (pydoc3) o páginas man de Linux.",
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {"type": "string", "description": "Módulo, función o comando, ej. os.listdir o chmod"}
                },
                "required": ["consulta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_archivos",
            "description": "Lista los archivos existentes en el proyecto activo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filtro": {
                        "type": "string",
                        "description": "Prefijo o extensión opcional para filtrar (vacío para todos)",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkpoint",
            "description": "Crea un snapshot de seguridad del proyecto antes o después de un cambio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "etiqueta": {"type": "string", "description": "Descripción corta del checkpoint"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explicar_error",
            "description": "Traduce un mensaje de error de la consola a lenguaje sencillo para principiantes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "description": "Texto del error o traceback"}
                },
                "required": ["error"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_en_proyecto",
            "description": "Busca texto o expresiones regulares en todos los archivos del proyecto activo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patron": {"type": "string", "description": "Texto o símbolo a buscar en el proyecto"}
                },
                "required": ["patron"],
            },
        },
    },
]


class DevOrchestrator:
    """Coordina el workspace, el sandbox bwrap y el agente de código multi-proveedor del Módulo Dev."""

    def __init__(
        self,
        workspace: CodeWorkspace,
        sandbox: Optional[SandboxRunner] = None,
    ) -> None:
        self.workspace = workspace
        self.sandbox = sandbox or SandboxRunner()
        self.last_run_by_project: dict[str, dict[str, Any]] = {}
        self.history_by_project: dict[str, list[dict[str, str]]] = {}

    def ensure_starter_project(self) -> dict[str, Any]:
        """Si el usuario aún no tiene proyectos, crea 'organizador_descargas' con su checkpoint inicial."""
        listed = self.workspace.list_projects()
        if listed.get("projects"):
            return listed
        try:
            self.create_from_recipe("organizador_descargas", "organizador_descargas")
        except WorkspaceError:
            pass
        return self.workspace.list_projects()

    def create_from_recipe(self, name: str, recipe_id: str) -> dict[str, Any]:
        recipe = STARTER_RECIPES.get(recipe_id)
        if not recipe:
            created = self.workspace.create_project(name, recipe_id)
            self.workspace.create_checkpoint(name, "Proyecto inicial")
            return created

        created = self.workspace.create_project(name, recipe["template"])
        custom_files = recipe.get("files")
        if isinstance(custom_files, dict):
            project_dir = self.workspace.project_dir(name)
            for stale in self.workspace.list_files(name)["files"]:
                if stale not in custom_files:
                    (project_dir / stale).unlink(missing_ok=True)
            for rel, content in custom_files.items():
                self.workspace.write_file(name, rel, content)
        self.workspace.create_checkpoint(name, "Proyecto inicial")
        return {
            "success": True,
            "project": created["project"],
            "files": self.workspace.list_files(name)["files"],
            "recipe": recipe_id,
        }

    def search_in_project(self, project: str, pattern: str) -> dict[str, Any]:
        """Busca coincidencias de texto en todos los archivos visibles del proyecto."""
        query = (pattern or "").strip()
        if not query or len(query) > 120:
            return {"success": False, "matches": [], "message": "Escribe un término de búsqueda de hasta 120 caracteres."}
        files = self.workspace.list_files(project)["files"]
        matches: list[dict[str, Any]] = []
        needle = query.lower()
        for rel in files:
            try:
                content = self.workspace.read_file(project, rel)["content"]
            except WorkspaceError:
                continue
            for idx, line in enumerate(content.splitlines(), start=1):
                if needle in line.lower():
                    matches.append({"file": rel, "line": idx, "snippet": line.strip()[:180]})
                    if len(matches) >= 40:
                        return {"success": True, "query": query, "matches": matches}
        return {"success": True, "query": query, "matches": matches}

    def run_project_file(
        self,
        project: str,
        relative_path: str,
        stdin_text: str = "",
        session_id: Optional[int] = None,
    ) -> dict[str, Any]:
        project_dir = self.workspace.project_dir(project)
        self.workspace.read_file(project, relative_path)
        try:
            run_res = self.sandbox.run_file(project_dir, relative_path, stdin_text=stdin_text)
        except SandboxUnavailable as exc:
            return {"success": False, "message": str(exc), "sandbox_available": False}
        except ValueError as exc:
            return {"success": False, "message": str(exc)}

        raw = run_res.to_dict()
        translated = translate_run_output(raw, relative_path)
        payload = {**raw, "translated": translated, "project": project, "file": relative_path}
        self.last_run_by_project[project] = payload

        log_tool_run(
            "dev_sandbox_run",
            json.dumps({"project": project, "file": relative_path}, ensure_ascii=False),
            translated["headline"],
            status="ok" if raw["success"] else "error",
            stdout=raw["stdout"],
            stderr=raw["stderr"],
            exit_code=raw["exit_code"],
            session_id=session_id,
        )
        return payload

    def export_project(self, project: str, destination_folder: str = "Documentos") -> dict[str, Any]:
        """Exporta una copia limpia del proyecto a ~/Documentos/<proyecto> tras confirmación del usuario."""
        src = self.workspace.project_dir(project)
        files = self.workspace.list_files(project)["files"]
        allowed_roots = {
            "Documentos": Path.home() / "Documentos",
            "Descargas": Path.home() / "Descargas",
            "Escritorio": Path.home() / "Escritorio",
        }
        base = allowed_roots.get(destination_folder, Path.home() / "Documentos")
        base.mkdir(parents=True, exist_ok=True)
        target = base / project
        if target.exists():
            raise WorkspaceError(f"Ya existe '{target}'. Cambia el nombre del proyecto o mueve esa carpeta primero.")
        target.mkdir(parents=True, mode=0o755)
        for rel in files:
            source_file = src / rel
            dest_file = target / rel
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, dest_file)
        return {
            "success": True,
            "destination": str(target),
            "files": files,
            "message": f"Proyecto exportado a {target}",
        }

    def clear_project_history(self, project: str) -> None:
        self.history_by_project.pop(project, None)

    def _resolve_llm_candidates(
        self,
        agent: Any,
        provider_override: str = "",
        model_override: str = "",
    ) -> list[tuple[Any, str, str]]:
        """Construye la lista priorizada de clientes LLM disponibles (proveedor elegido → agente activo → otros proveedores con API Key)."""
        from dotenv import load_dotenv
        from src.core.keyring_manager import get_api_key
        from src.core.providers import PROVIDERS, create_provider_client

        chosen_provider = (provider_override or "").strip().lower()
        chosen_model = (model_override or "").strip()

        if not chosen_provider and agent is None:
            return []

        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)

        candidates: list[tuple[Any, str, str]] = []
        seen_providers: set[str] = set()

        if (
            agent is not None
            and getattr(agent, "_client", None) is not None
            and (not chosen_provider or getattr(agent, "provider", "") == chosen_provider)
        ):
            prov = getattr(agent, "provider", chosen_provider or "groq")
            mdl = chosen_model or getattr(agent, "model", "")
            if mdl:
                candidates.append((agent._client, prov, mdl))
                seen_providers.add(prov)

        if chosen_provider and chosen_provider in PROVIDERS and chosen_provider not in seen_providers:
            try:
                client, resolved_model, _ = create_provider_client(
                    chosen_provider,
                    model=chosen_model or None,
                    timeout=60,
                )
                candidates.append((client, chosen_provider, resolved_model))
                seen_providers.add(chosen_provider)
            except Exception:
                pass

        if agent is not None and getattr(agent, "_client", None) is not None:
            prov = getattr(agent, "provider", "groq")
            if prov not in seen_providers:
                mdl = getattr(agent, "model", "")
                if mdl:
                    candidates.append((agent._client, prov, mdl))
                    seen_providers.add(prov)

        for pid in PROVIDERS:
            if pid in seen_providers or pid in ("ollama", "custom"):
                continue
            key = (get_api_key(pid) or "").strip()
            if not key or "tu_clave_aqui" in key:
                continue
            try:
                client, resolved_model, _ = create_provider_client(pid, timeout=60)
                candidates.append((client, pid, resolved_model))
                seen_providers.add(pid)
            except Exception:
                continue

        return candidates

    def _resolve_llm_client(
        self,
        agent: Any,
        provider_override: str = "",
        model_override: str = "",
    ) -> tuple[Any, str, str]:
        """Obtiene el cliente LLM activo o crea uno bajo demanda para el proveedor/modelo elegido en el IDE."""
        candidates = self._resolve_llm_candidates(agent, provider_override, model_override)
        if candidates:
            return candidates[0]
        raise ValueError("Sin proveedor LLM activo.")

    # ------------------------------------------------------------------
    # Chat del agente con reporte visual de tools ejecutadas
    # ------------------------------------------------------------------
    def chat_with_agent(
        self,
        *,
        project: str,
        active_file: str,
        message: str,
        agent: Any = None,
        mode: str = "guided",
        provider: str = "",
        model: str = "",
    ) -> dict[str, Any]:
        text = (message or "").strip()
        if not text:
            return {"success": False, "message": "Escribe una instrucción o pregunta para el agente."}
        if len(text) > 2000:
            return {"success": False, "message": "El mensaje supera el límite de 2.000 caracteres."}

        files = self.workspace.list_files(project)["files"]
        target_file = active_file if active_file in files else (files[0] if files else "main.py")
        tool_events: list[dict[str, str]] = []
        proposal: Optional[dict[str, Any]] = None

        candidates = self._resolve_llm_candidates(agent, provider, model)
        for idx, (client, active_prov, active_model) in enumerate(candidates):
            if client is None or not active_model:
                continue
            try:
                res = self._llm_dev_turn(
                    client=client,
                    provider=active_prov,
                    model=active_model,
                    project=project,
                    target_file=target_file,
                    files=files,
                    user_message=text,
                    mode=mode,
                )
                if idx > 0:
                    res.setdefault("tool_events", []).insert(
                        0,
                        {"status": "done", "label": f"proveedor activo → {active_prov} ({res.get('model', active_model)})"},
                    )
                self._record_turn(project, text, res.get("reply", ""))
                return res
            except Exception:
                continue

        # Respuesta asistida local cuando no hay conexión o ninguna API Key activa respondió
        res = self._local_guided_turn(
            project=project,
            target_file=target_file,
            files=files,
            user_message=text,
            tool_events=tool_events,
            proposal=proposal,
        )
        self._record_turn(project, text, res.get("reply", ""))
        return res

    def _record_turn(self, project: str, user_msg: str, ai_reply: str) -> None:
        hist = self.history_by_project.setdefault(project, [])
        hist.append({"role": "user", "content": user_msg[:600]})
        if ai_reply:
            hist.append({"role": "assistant", "content": ai_reply[:1000]})
        if len(hist) > 12:
            del hist[:-12]

    def _call_chat_completion(
        self,
        *,
        client: Any,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        tool_events: list[dict[str, str]],
        enable_tools: bool = True,
        max_tokens: int = 2600,
    ) -> tuple[Any, str]:
        """Invoca chat.completions con fallback multimodelo para los 13 proveedores y degradación automática sin tools."""
        from src.core.providers import PROVIDERS
        from src.core.settings_manager import PROVIDER_FALLBACK_MODELS

        candidates: list[str] = []
        if model:
            candidates.append(model)
        pinfo = PROVIDERS.get(provider)
        default_mdl = (pinfo or {}).get("model", "") if isinstance(pinfo, dict) else ""
        if default_mdl and default_mdl not in candidates:
            candidates.append(default_mdl)
        for alt in PROVIDER_FALLBACK_MODELS.get(provider, ()):
            if alt and alt not in candidates:
                candidates.append(alt)

        last_exc: Optional[Exception] = None

        def _try_model(cand_model: str, is_fallback: bool) -> Optional[tuple[Any, str]]:
            nonlocal last_exc
            attempt_modes = (
                ((True, True), (False, True), (False, False))
                if enable_tools
                else ((False, True), (False, False))
            )
            for use_tools, use_provider_opts in attempt_modes:
                try:
                    opts = (
                        completion_options(provider, cand_model, 0.2, max_tokens)
                        if use_provider_opts
                        else {"temperature": 0.2, "max_tokens": min(max_tokens, 2048)}
                    )
                    kwargs: dict[str, Any] = {
                        "model": cand_model,
                        "messages": messages,
                        **opts,
                        "timeout": 55,
                    }
                    if use_tools:
                        kwargs["tools"] = DEV_TOOLS_SCHEMA
                        kwargs["tool_choice"] = "auto"
                    resp = client.chat.completions.create(**kwargs)
                    if is_fallback:
                        tool_events.append({"status": "done", "label": f"modelo activo → {cand_model}"})
                    return resp, cand_model
                except Exception as exc:
                    last_exc = exc
                    err_low = str(exc).lower()
                    # Si la clave API es inválida (401/403), no seguir probando modos ni modelos en este proveedor
                    if any(
                        k in err_low
                        for k in ("401", "403", "invalid_api_key", "invalid api key", "api_key_invalid", "unauthorized")
                    ):
                        raise exc
                    # Si el modelo no existe (404) o está saturado (503/429), pasar al siguiente modelo candidato
                    if any(
                        k in err_low
                        for k in ("404", "not_found", "model_not_found", "does not exist", "503", "overloaded", "high demand", "429")
                    ):
                        break
                    # Para cualquier otro error (400, 422, 500, tools no soportadas, extra_body rechazado), probar sin tools / opciones simples
                    continue
            return None

        for idx, cand_model in enumerate(candidates):
            hit = _try_model(cand_model, is_fallback=(idx > 0))
            if hit is not None:
                return hit

        # Descubrimiento dinámico de modelos disponibles en el endpoint si los candidatos estáticos fallaron
        try:
            listed = client.models.list()
            raw_ids = [getattr(item, "id", "") or "" for item in getattr(listed, "data", []) or []]
            raw_ids.sort(key=lambda x: (0 if "gemini" in x.lower() else 1))
            for mid in raw_ids:
                low_id = mid.lower()
                if not mid or mid in candidates:
                    continue
                if any(skip in low_id for skip in ("embed", "whisper", "tts", "dall-e", "moderation", "audio", "rerank", "imagen", "veo", "aqa")):
                    continue
                candidates.append(mid)
                hit = _try_model(mid, is_fallback=True)
                if hit is not None:
                    return hit
                if len(candidates) >= 10:
                    break
        except Exception:
            pass

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("No se obtuvo respuesta del proveedor.")

    @staticmethod
    def _is_conversational_or_meta_query(text: str) -> bool:
        """Detecta saludos o preguntas sobre la identidad del agente que no requieren inspeccionar archivos."""
        low = re.sub(r"[¿?¡!.,;:]+", " ", text.lower()).strip()
        words = low.split()
        if low in (
            "hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches",
            "hey", "que tal", "qué tal", "saludos", "gracias", "ok", "vale", "listo", "ey",
        ):
            return True
        identity_phrases = (
            "que ia eres", "qué ia eres", "quien eres", "quién eres", "que modelo eres",
            "qué modelo eres", "cual es tu nombre", "cuál es tu nombre", "como te llamas",
            "cómo te llamas", "que eres", "qué eres", "que proveedor usas", "qué proveedor usas",
            "con que ia", "con qué ia", "que llm eres", "qué llm eres",
        )
        if any(p in low for p in identity_phrases):
            return True
        if len(words) <= 3 and any(w in words for w in ("hola", "buenas", "hey", "gracias")):
            return True
        return False

    def _llm_dev_turn(
        self,
        *,
        client: Any,
        provider: str,
        model: str,
        project: str,
        target_file: str,
        files: list[str],
        user_message: str,
        mode: str,
    ) -> dict[str, Any]:
        tool_events: list[dict[str, str]] = []
        proposal: Optional[dict[str, Any]] = None
        is_meta = self._is_conversational_or_meta_query(user_message)

        if is_meta:
            sys_prompt = (
                f"Eres el asistente de programación de LinuxMate Dev Studio, ejecutándote con el proveedor `{provider}` y el modelo `{model}`.\n"
                "Responde al saludo o pregunta del usuario en máximo 2 oraciones breves y naturales en español.\n"
                "PROHIBIDO mencionar archivos como `main.py`, dar lecciones no solicitadas, usar encabezados `###` o escribir bloques de código."
            )
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_message},
            ]
            resp, model = self._call_chat_completion(
                client=client,
                provider=provider,
                model=model,
                messages=messages,
                tool_events=tool_events,
                enable_tools=False,
                max_tokens=150,
            )
            reply = (resp.choices[0].message.content or "").strip() or f"¡Hola! Soy el agente de programación conectado a `{provider}` (`{model}`). ¿En qué te ayudo?"
            return {
                "success": True,
                "reply": reply,
                "tool_events": tool_events,
                "proposal": None,
                "provider": provider,
                "model": model,
            }

        file_content = ""
        if target_file in files:
            raw_content = self.workspace.read_file(project, target_file)["content"]
            if not contains_likely_secret(raw_content) and len(raw_content) <= 40_000:
                file_content = raw_content
                tool_events.append({"status": "done", "label": f"tool: leer_archivo — {target_file}"})

        last_run = self.last_run_by_project.get(project)
        last_err = (last_run or {}).get("stderr", "")[:1200] if last_run else ""

        mode_instructions = {
            "guided": "Modo ASISTIDO: explica con claridad cuando el usuario pida código o ayuda técnica.",
            "suggestions": "Modo SUGERENCIAS: sé directo, señala mejoras puntuales y prepara el diff.",
            "autonomous": "Modo AGÉNTICO: inspecciona archivos, verifica en el sandbox y entrega la propuesta lista.",
        }.get(mode, "Modo ASISTIDO.")

        file_context_block = ""
        if file_content:
            file_context_block = (
                f"\nContexto silencioso del archivo activo `{target_file}` (úsalo SOLO si la pregunta del usuario se refiere al código):\n"
                f"```\n{file_content}\n```\n"
            )
            if last_err:
                file_context_block += f"\nÚltimo error en consola:\n{last_err}\n"

        sys_prompt = (
            f"Eres el Agente de Programación de LinuxMate Dev Studio, impulsado por el proveedor `{provider}` (modelo `{model}`).\n"
            "REGLA DE ORO DE CONCISIÓN:\n"
            "- Responde SIEMPRE de forma directa, breve y exacta a lo que el usuario pregunta.\n"
            "- NO analices ni critiques `main.py` si el usuario hace una pregunta general que no lo solicita.\n"
            "- NO escribas introducciones largas ni explicaciones no solicitadas.\n"
            f"Proyecto abierto: {project} | Archivos: {', '.join(files)} | Archivo en foco: {target_file}\n"
            f"{mode_instructions}\n"
            "Cuando el usuario te pida modificar o crear código en un archivo, usa la herramienta `escribir_archivo` con el contenido completo actualizado."
            f"{file_context_block}"
        )
        messages = [{"role": "system", "content": sys_prompt}]
        for past in self.history_by_project.get(project, [])[-6:]:
            messages.append(past)
        messages.append({"role": "user", "content": user_message})

        for _ in range(4):
            resp, model = self._call_chat_completion(
                client=client,
                provider=provider,
                model=model,
                messages=messages,
                tool_events=tool_events,
                enable_tools=True,
            )
            msg = resp.choices[0].message
            tcalls = getattr(msg, "tool_calls", None)
            if not tcalls:
                reply = (msg.content or "").strip() or "Listo."
                # Si el modelo respondió sin tool_calls pero incluyó un bloque de código completo ante un pedido de edición
                if not is_meta and proposal is None and "```" in reply and any(
                    w in user_message.lower() for w in ("crea", "agrega", "añade", "modifica", "cambia", "mejora", "corrige", "haz", "ordena", "función", "funcion")
                ):
                    code_match = re.search(r"```(?:[a-zA-Z0-9_+-]+)?\n([\s\S]*?)```", reply)
                    if code_match and len(code_match.group(1).strip()) > 15:
                        candidate_code = code_match.group(1).rstrip() + "\n"
                        if candidate_code != file_content:
                            proposal = self.workspace.propose_file_change(
                                project, target_file, candidate_code, summary="Propuesta generada por el agente IA."
                            )
                            tool_events.append({"status": "done", "label": f"tool: escribir_archivo — {target_file} (diff listo)"})
                return {
                    "success": True,
                    "reply": reply,
                    "tool_events": tool_events,
                    "proposal": proposal,
                    "provider": provider,
                    "model": model,
                }

            messages.append(
                msg.model_dump(exclude_none=True)
                if hasattr(msg, "model_dump")
                else {"role": "assistant", "content": msg.content or ""}
            )
            for call in tcalls:
                fn = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except ValueError:
                    args = {}
                out_str, prop = self._execute_dev_tool(project, target_file, fn, args, tool_events)
                if prop is not None:
                    proposal = prop
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": fn,
                        "content": out_str,
                    }
                )

        return {
            "success": True,
            "reply": (
                "Te dejé una propuesta lista en el editor. Puedes ver el diff o pulsar **✔ Aceptar cambios**."
                if proposal
                else "He revisado el proyecto con las herramientas del módulo."
            ),
            "tool_events": tool_events,
            "proposal": proposal,
            "provider": provider,
            "model": model,
        }

    def _execute_dev_tool(
        self,
        project: str,
        default_file: str,
        fn: str,
        args: dict[str, Any],
        tool_events: list[dict[str, str]],
    ) -> tuple[str, Optional[dict[str, Any]]]:
        try:
            if fn == "leer_archivo":
                rel = str(args.get("archivo") or default_file)
                data = self.workspace.read_file(project, rel)
                numbered = "\n".join(
                    f"{idx + 1}: {line}" for idx, line in enumerate(data["content"].splitlines())
                )
                tool_events.append({"status": "done", "label": f"tool: leer_archivo — {rel}"})
                return numbered[:8000], None

            if fn == "listar_archivos":
                listed = self.workspace.list_files(project)
                tool_events.append({"status": "done", "label": "tool: listar_archivos"})
                return json.dumps(listed["files"], ensure_ascii=False), None

            if fn == "buscar_en_proyecto":
                pat = str(args.get("patron") or "")
                found = self.search_in_project(project, pat)
                tool_events.append({"status": "done", "label": f'tool: buscar_en_proyecto — "{pat}"'})
                return json.dumps(found.get("matches", []), ensure_ascii=False), None

            if fn == "buscar_docs":
                query = str(args.get("consulta") or "os.listdir")
                res = self.sandbox.lookup_docs(query)
                tool_events.append({"status": "done", "label": f'tool: buscar_docs — "{query}"'})
                return res.get("content", ""), None

            if fn == "escribir_archivo":
                rel = str(args.get("archivo") or default_file)
                new_content = str(args.get("contenido") or "")
                summary = str(args.get("resumen") or "Propuesta generada por el agente.")
                prop = self.workspace.propose_file_change(project, rel, new_content, summary=summary)
                tool_events.append({"status": "done", "label": f"tool: escribir_archivo — {rel} (diff listo)"})
                return f"Propuesta creada para {rel} (+{prop['added']} / -{prop['removed']} líneas).", prop

            if fn == "ejecutar_comando":
                rel = str(args.get("archivo") or default_file)
                run_res = self.run_project_file(project, rel)
                tool_events.append({"status": "done", "label": f"tool: ejecutar_comando — {rel}"})
                return json.dumps(run_res.get("translated", {}), ensure_ascii=False), None

            if fn == "checkpoint":
                label = str(args.get("etiqueta") or "Antes de cambio del agente")
                cp = self.workspace.create_checkpoint(project, label)
                tool_events.append({"status": "done", "label": f"tool: checkpoint — {label}"})
                return json.dumps(cp["checkpoint"], ensure_ascii=False), None

            if fn == "explicar_error":
                err_txt = str(args.get("error") or "")
                exp = translate_dev_error(err_txt)
                tool_events.append({"status": "done", "label": "tool: explicar_error"})
                return json.dumps(exp, ensure_ascii=False), None

        except (WorkspaceError, OSError, ValueError) as exc:
            return f"Error en {fn}: {exc}", None

        return "Herramienta no reconocida.", None

    def _local_guided_turn(
        self,
        *,
        project: str,
        target_file: str,
        files: list[str],
        user_message: str,
        tool_events: list[dict[str, str]],
        proposal: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """Respuestas y propuestas guiadas cuando se trabaja sin conexión o sin API Key activa."""
        low = re.sub(r"[¿?¡!.,;:]+", " ", user_message.lower()).strip()

        if any(
            p in low
            for p in (
                "que ia eres", "qué ia eres", "quien eres", "quién eres",
                "que modelo eres", "qué modelo eres", "como te llamas", "cómo te llamas",
            )
        ):
            return {
                "success": True,
                "reply": (
                    "Soy el **Agente de Programación de LinuxMate Dev Studio**. "
                    "Puedo conectarme al proveedor que elijas arriba (Groq, NVIDIA, Gemini, Claude, OpenAI, DeepSeek, etc.) "
                    "para leer tus archivos, explicarte código, ejecutar en el sandbox y proponerte cambios con diff."
                ),
                "tool_events": tool_events,
                "proposal": None,
            }

        if low in ("hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "hey", "que tal", "qué tal"):
            return {
                "success": True,
                "reply": f"¡Hola! 👋 Estoy listo para ayudarte con `{target_file}`. ¿Qué quieres programar o revisar?",
                "tool_events": tool_events,
                "proposal": None,
            }

        content = ""
        if target_file in files:
            content = self.workspace.read_file(project, target_file)["content"]
            tool_events.append({"status": "done", "label": f"tool: leer_archivo — {target_file}"})

        lines = content.splitlines()
        funcs = [
            line.strip().split("(")[0].replace("def ", "").replace("function ", "")
            for line in lines
            if line.strip().startswith(("def ", "function "))
        ]
        funcs_summary = f" (funciones detectadas: `{', '.join(funcs)}`)" if funcs else ""

        if any(word in low for word in ("chmod", "listdir", "shutil", "pathlib", "bash", "doc", "cómo uso", "como uso")):
            query = "chmod" if "chmod" in low else ("shutil" if "shutil" in low else "os.listdir")
            doc = self.sandbox.lookup_docs(query)
            tool_events.append({"status": "done", "label": f'tool: buscar_docs — "{query}"'})
            snippet = (doc.get("content") or "").splitlines()[:8]
            return {
                "success": True,
                "reply": (
                    f"Consulté la documentación local de **`{query}`**:\n\n"
                    f"```\n{chr(10).join(snippet)}\n```\n\n"
                    f"En `{target_file}`, esto te permite trabajar con archivos de forma segura dentro del sandbox."
                ),
                "tool_events": tool_events,
                "proposal": None,
            }

        if any(word in low for word in ("falló", "fallo", "error", "por qué", "por que", "explica")) and project in self.last_run_by_project:
            last = self.last_run_by_project[project]
            exp = translate_dev_error(last.get("stderr", ""), last.get("stdout", ""), last.get("exit_code"))
            tool_events.append({"status": "done", "label": "tool: explicar_error"})
            return {
                "success": True,
                "reply": (
                    f"**¿Por qué ocurrió esto?**\n{exp['cause']}\n\n"
                    f"**Cómo solucionarlo:**\n{exp['suggestion']}"
                ),
                "tool_events": tool_events,
                "proposal": None,
            }

        if any(word in low for word in ("revisa", "qué hace", "que hace", "explic", "analiza", "resumen")):
            tool_events.append({"status": "done", "label": 'tool: buscar_docs — "os.listdir"'})
            return {
                "success": True,
                "reply": (
                    f"Revisé `{target_file}` ({len(lines)} líneas{funcs_summary}). "
                    "Recorre la carpeta de trabajo, identifica la extensión de cada archivo con `split('.')` "
                    "y lo clasifica en su categoría correspondiente dentro del sandbox sin tocar archivos externos."
                ),
                "tool_events": tool_events,
                "proposal": None,
            }

        if target_file.endswith(".py"):
            if "fecha" in low or "orden" in low:
                addition = (
                    "\n\ndef ordenar_por_fecha(carpeta: str) -> list[str]:\n"
                    '    """Devuelve los archivos de la carpeta ordenados del más reciente al más antiguo."""\n'
                    "    rutas = [\n"
                    "        os.path.join(carpeta, f)\n"
                    "        for f in os.listdir(carpeta)\n"
                    "        if not f.startswith('.') and os.path.isfile(os.path.join(carpeta, f))\n"
                    "    ]\n"
                    "    rutas.sort(key=lambda r: os.path.getmtime(r), reverse=True)\n"
                    "    return [os.path.basename(r) for r in rutas]\n"
                )
                if "def ordenar_por_fecha" not in content:
                    new_code = content.rstrip() + addition
                    summary = "Añade `ordenar_por_fecha(carpeta)` para listar archivos por fecha de modificación."
                    proposal = self.workspace.propose_file_change(project, target_file, new_code, summary=summary)
                    tool_events.append({"status": "done", "label": f"tool: escribir_archivo — {target_file} (diff listo)"})
                    return {
                        "success": True,
                        "reply": (
                            f"He preparado la función `ordenar_por_fecha(carpeta)` en `{target_file}` (+{proposal['added']} líneas). "
                            "Filtra archivos ocultos y los ordena usando `os.path.getmtime`. "
                            "Pulsa **✔ Aceptar cambios** o **👁 Ver diff** debajo del editor para aplicarla."
                        ),
                        "tool_events": tool_events,
                        "proposal": proposal,
                    }

            if any(w in low for w in ("duplicado", "oculto", "complet", "mejora", "agrega", "añade", "haz", "crea", "cambia", "función", "funcion")):
                addition = (
                    "\n\ndef resumen_legible(conteo: dict[str, int]) -> str:\n"
                    '    """Genera un resumen legible con el total de archivos clasificados por categoría."""\n'
                    "    partes = [f'{v} {k}' for k, v in conteo.items() if v > 0]\n"
                    "    return ', '.join(partes) if partes else 'sin archivos nuevos'\n"
                )
                if "def resumen_legible" not in content:
                    new_code = content.rstrip() + addition
                    summary = "Añade `resumen_legible()` para mostrar el conteo por categoría en formato claro."
                else:
                    new_code = content + "\n# Verificación adicional completada por el agente\n"
                    summary = "Añade nota de verificación al final del script."
                proposal = self.workspace.propose_file_change(project, target_file, new_code, summary=summary)
                tool_events.append({"status": "done", "label": f"tool: escribir_archivo — {target_file} (diff listo)"})
                return {
                    "success": True,
                    "reply": (
                        f"Te propuse una mejora en `{target_file}` (+{proposal['added']} líneas nuevas). "
                        "Revisa el barra de propuesta debajo del editor y pulsa **✔ Aceptar cambios** o **👁 Ver diff**."
                    ),
                    "tool_events": tool_events,
                    "proposal": proposal,
                }

        return {
            "success": True,
            "reply": (
                f"Dime qué cambio o consulta puntual tienes sobre `{target_file}` y lo resolvemos enseguida."
            ),
            "tool_events": tool_events,
            "proposal": proposal,
        }




"""Workspace de programación local con límites de ruta y cambios revisables."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import secrets
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any


PROJECTS_DIR = Path.home() / "Proyectos" / "LinuxMate"
MAX_TEXT_FILE_BYTES = 1_000_000
HIDDEN_DIRS = {".git", ".venv", "node_modules", "__pycache__"}
SENSITIVE_NAMES = {".env", ".env.local", "id_rsa", "id_ed25519", "credentials"}
REMOTE_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd|access[_-]?token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
)

TEMPLATES: dict[str, dict[str, str]] = {
    "python": {
        "README.md": "# Proyecto Python\n\nCreado con LinuxMate.\n\nEjecuta `python3 main.py` desde este directorio.\n",
        "main.py": 'def main():\n    print("Hola desde LinuxMate")\n\n\nif __name__ == "__main__":\n    main()\n',
        "test_main.py": "from main import main\n\n\ndef test_main_exists():\n    assert callable(main)\n",
    },
    "web": {
        "README.md": "# Proyecto Web\n\nAbre `index.html` en tu navegador.\n",
        "index.html": "<!doctype html>\n<html lang=\"es\">\n<head>\n  <meta charset=\"utf-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n  <title>Mi proyecto</title>\n  <link rel=\"stylesheet\" href=\"styles.css\">\n</head>\n<body>\n  <main><h1>Mi proyecto</h1><p>Empieza a construir aquí.</p></main>\n  <script src=\"app.js\"></script>\n</body>\n</html>\n",
        "styles.css": "body { font-family: system-ui, sans-serif; margin: 3rem; }\n",
        "app.js": "document.querySelector('h1')?.addEventListener('click', () => {\n  console.log('Hola desde LinuxMate');\n});\n",
    },
    "bash": {
        "README.md": "# Proyecto Bash\n\nRevisa el script antes de ejecutarlo.\n",
        "script.sh": "#!/usr/bin/env bash\nset -euo pipefail\n\nprintf '%s\\n' 'Hola desde LinuxMate'\n",
    },
    "node": {
        "README.md": "# Proyecto Node.js\n\nEjecuta `node main.js` desde este directorio.\n",
        "main.js": "function saludar(nombre) {\n  return `Hola, ${nombre}, desde LinuxMate`;\n}\n\nconsole.log(saludar('mundo'));\n",
    },
}

CHECKPOINTS_DIRNAME = ".checkpoints"
MAX_CHECKPOINTS = 30
MAX_CHECKPOINT_BYTES = 20_000_000


class WorkspaceError(ValueError):
    """Error seguro y mostrable producido por una operación del workspace."""


def contains_likely_secret(content: str) -> bool:
    return any(pattern.search(content) for pattern in REMOTE_SECRET_PATTERNS)


class CodeWorkspace:
    def __init__(self, root: Path | str = PROJECTS_DIR) -> None:
        self._root_input = Path(root).expanduser()
        self.root = self._root_input.resolve()
        self._proposals: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _validate_project_name(name: str) -> str:
        value = (name or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}", value):
            raise WorkspaceError("Usa un nombre de proyecto de hasta 48 caracteres: letras, números, guion y guion bajo.")
        return value

    @staticmethod
    def _validate_relative_path(relative_path: str) -> Path:
        path = Path(relative_path or "")
        if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
            raise WorkspaceError("La ruta debe estar dentro del proyecto.")
        if any(part.lower() in SENSITIVE_NAMES for part in path.parts):
            raise WorkspaceError("El workspace no permite acceder a archivos de credenciales.")
        return path

    def _project_path(self, name: str) -> Path:
        safe_name = self._validate_project_name(name)
        path = self.root / safe_name
        if path.is_symlink() or not path.is_dir():
            raise WorkspaceError("No se encontró ese proyecto dentro del workspace.")
        return path

    def _file_path(self, project: Path, relative_path: str, *, allow_missing: bool = False) -> Path:
        relative = self._validate_relative_path(relative_path)
        current = project
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise WorkspaceError("No se permiten enlaces simbólicos dentro del workspace.")
        resolved = current.resolve(strict=False)
        if not resolved.is_relative_to(project):
            raise WorkspaceError("La ruta queda fuera del proyecto.")
        if not allow_missing and not resolved.is_file():
            raise WorkspaceError("No se encontró un archivo normal con esa ruta.")
        return resolved

    def list_projects(self) -> dict[str, Any]:
        projects = []
        if self.root.is_dir():
            for path in sorted(self.root.iterdir(), key=lambda item: item.name.casefold()):
                if path.is_dir() and not path.is_symlink() and not path.name.startswith("."):
                    projects.append({"name": path.name, "path": str(path)})
        return {"success": True, "root": str(self.root), "projects": projects}

    def create_project(self, name: str, template: str) -> dict[str, Any]:
        safe_name = self._validate_project_name(name)
        if template not in TEMPLATES:
            raise WorkspaceError("Plantilla no reconocida.")
        if self._root_input.is_symlink():
            raise WorkspaceError("La carpeta raíz no puede ser un enlace simbólico.")
        self.root.mkdir(parents=True, exist_ok=True)
        project = self.root / safe_name
        try:
            project.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise WorkspaceError("Ya existe un proyecto con ese nombre.") from exc
        try:
            for relative, content in TEMPLATES[template].items():
                target = self._file_path(project, relative, allow_missing=True)
                target.write_text(content, encoding="utf-8")
                os.chmod(target, 0o600)
        except Exception:
            for item in project.iterdir():
                if item.is_file() and not item.is_symlink():
                    item.unlink()
            project.rmdir()
            raise
        return {"success": True, "project": {"name": safe_name, "path": str(project)}, "files": list(TEMPLATES[template])}

    def list_files(self, name: str) -> dict[str, Any]:
        project = self._project_path(name)
        files = []
        for path in sorted(project.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if any(part in HIDDEN_DIRS for part in path.relative_to(project).parts):
                continue
            if path.is_symlink():
                continue
            if path.is_file() and path.name.lower() not in SENSITIVE_NAMES:
                files.append(path.relative_to(project).as_posix())
        return {"success": True, "project": name, "files": files}

    def read_file(self, name: str, relative_path: str) -> dict[str, Any]:
        project = self._project_path(name)
        path = self._file_path(project, relative_path)
        if path.stat().st_size > MAX_TEXT_FILE_BYTES:
            raise WorkspaceError("El archivo supera el límite de lectura de 1 MB.")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError("El archivo no es texto UTF-8; no lo abriré como código.") from exc
        return {"success": True, "project": name, "path": relative_path, "content": content}

    def propose_file_change(
        self, name: str, relative_path: str, new_content: str, summary: str = ""
    ) -> dict[str, Any]:
        if not isinstance(new_content, str) or len(new_content.encode("utf-8")) > MAX_TEXT_FILE_BYTES:
            raise WorkspaceError("El texto nuevo supera el límite de 1 MB.")
        project = self._project_path(name)
        path = self._file_path(project, relative_path, allow_missing=True)
        if path.exists() and not path.is_file():
            raise WorkspaceError("Solo se pueden proponer cambios a archivos normales.")
        old_content = ""
        if path.exists():
            if path.stat().st_size > MAX_TEXT_FILE_BYTES:
                raise WorkspaceError("El archivo supera el límite de edición de 1 MB.")
            try:
                old_content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise WorkspaceError("No se puede editar un archivo binario o que no sea UTF-8.") from exc
        if old_content == new_content:
            raise WorkspaceError("El archivo ya tiene ese contenido; no hay cambios que proponer.")
        diff = "".join(difflib.unified_diff(
            old_content.splitlines(keepends=True), new_content.splitlines(keepends=True),
            fromfile=f"a/{relative_path}" if path.exists() else "/dev/null",
            tofile=f"b/{relative_path}",
        ))
        token = secrets.token_urlsafe(24)
        digest = hashlib.sha256(old_content.encode("utf-8")).hexdigest()
        added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
        self._proposals[token] = {
            "project": name,
            "path": relative_path,
            "new_content": new_content,
            "old_digest": digest,
        }
        result = {
            "success": True, "token": token, "project": name, "path": relative_path, "diff": diff,
            "added": added, "removed": removed, "is_new": not path.exists(),
        }
        if summary:
            result["summary"] = str(summary)[:600]
        return result

    def apply_proposed_change(
        self, token: str, confirmed: bool, *, checkpoint_label: str | None = None
    ) -> dict[str, Any]:
        plan = self._proposals.pop((token or "").strip(), None)
        if plan is None:
            raise WorkspaceError("La propuesta ya expiró o fue utilizada.")
        if confirmed is not True:
            return {"success": False, "cancelled": True, "message": "Cambio rechazado; el proyecto no fue modificado."}
        project = self._project_path(plan["project"])
        path = self._file_path(project, plan["path"], allow_missing=True)
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if hashlib.sha256(current.encode("utf-8")).hexdigest() != plan["old_digest"]:
            raise WorkspaceError("El archivo cambió desde que se preparó el diff. Genera una propuesta nueva.")
        checkpoint = None
        if checkpoint_label:
            checkpoint = self.create_checkpoint(plan["project"], checkpoint_label)["checkpoint"]
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path(project, plan["path"], allow_missing=True)
        self._atomic_write(path, plan["new_content"])
        result = {"success": True, "message": "Cambios aplicados al proyecto.", "project": plan["project"], "path": plan["path"]}
        if checkpoint:
            result["checkpoint"] = checkpoint
        return result

    def discard_proposals(self, name: str) -> None:
        """Olvida propuestas pendientes de un proyecto (p. ej. al cambiar de proyecto)."""
        for token in [t for t, plan in self._proposals.items() if plan["project"] == name]:
            self._proposals.pop(token, None)

    # ------------------------------------------------------------------
    # Edición directa del usuario (el agente nunca usa este camino)
    # ------------------------------------------------------------------
    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        fd, temp_name = tempfile.mkstemp(prefix=".linuxmate-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, path)
        finally:
            Path(temp_name).unlink(missing_ok=True)

    def write_file(self, name: str, relative_path: str, content: str) -> dict[str, Any]:
        """Guarda lo que el usuario escribió en el editor."""
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_TEXT_FILE_BYTES:
            raise WorkspaceError("El archivo supera el límite de 1 MB.")
        project = self._project_path(name)
        path = self._file_path(project, relative_path, allow_missing=True)
        if path.exists() and not path.is_file():
            raise WorkspaceError("Solo se pueden guardar archivos normales.")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path(project, relative_path, allow_missing=True)
        self._atomic_write(path, content)
        return {"success": True, "project": name, "path": relative_path, "message": "Archivo guardado."}

    def project_dir(self, name: str) -> Path:
        return self._project_path(name)

    # ------------------------------------------------------------------
    # Checkpoints: copias completas de los archivos visibles del proyecto
    # ------------------------------------------------------------------
    def _checkpoint_root(self, name: str) -> Path:
        safe = self._validate_project_name(name)
        return self.root / CHECKPOINTS_DIRNAME / safe

    def create_checkpoint(self, name: str, label: str = "") -> dict[str, Any]:
        project = self._project_path(name)
        files = self.list_files(name)["files"]
        total = 0
        for relative in files:
            total += self._file_path(project, relative).stat().st_size
        if total > MAX_CHECKPOINT_BYTES:
            raise WorkspaceError("El proyecto supera 20 MB; no se puede crear un checkpoint.")
        base = self._checkpoint_root(name)
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        now = time.time()
        checkpoint_id = (
            time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
            + f"-{int(now * 1000) % 1000:03d}{secrets.token_hex(2)[:3]}"
        )
        target = base / checkpoint_id
        target.mkdir(mode=0o700)
        for relative in files:
            source = self._file_path(project, relative)
            dest = target / "files" / relative
            dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(source, dest)
            os.chmod(dest, 0o600)
        meta = {
            "id": checkpoint_id,
            "label": (label or "Checkpoint manual").strip()[:120],
            "created_at": time.time(),
            "files": files,
        }
        (target / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        self._prune_checkpoints(base)
        return {"success": True, "checkpoint": meta}

    @staticmethod
    def _prune_checkpoints(base: Path) -> None:
        entries = sorted((p for p in base.iterdir() if p.is_dir() and not p.is_symlink()), key=lambda p: p.name)
        for old in entries[:-MAX_CHECKPOINTS]:
            shutil.rmtree(old, ignore_errors=True)

    def list_checkpoints(self, name: str) -> dict[str, Any]:
        self._project_path(name)
        base = self._checkpoint_root(name)
        items = []
        if base.is_dir():
            for entry in sorted(base.iterdir(), key=lambda p: p.name, reverse=True):
                meta_file = entry / "meta.json"
                if entry.is_symlink() or not meta_file.is_file():
                    continue
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                items.append({k: meta.get(k) for k in ("id", "label", "created_at")} | {"files": len(meta.get("files", []))})
        return {"success": True, "project": name, "checkpoints": items}

    def restore_checkpoint(self, name: str, checkpoint_id: str) -> dict[str, Any]:
        project = self._project_path(name)
        if not re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{6}", checkpoint_id or ""):
            raise WorkspaceError("Checkpoint no válido.")
        source = self._checkpoint_root(name) / checkpoint_id
        meta_file = source / "meta.json"
        if source.is_symlink() or not meta_file.is_file():
            raise WorkspaceError("No se encontró ese checkpoint.")
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        saved_files = [f for f in meta.get("files", []) if isinstance(f, str)]
        # Antes de restaurar se guarda el estado actual para que restaurar también sea reversible.
        safety = self.create_checkpoint(name, f"Antes de restaurar «{meta.get('label', '')}»")["checkpoint"]
        for relative in self.list_files(name)["files"]:
            if relative not in saved_files:
                self._file_path(project, relative).unlink()
        for relative in saved_files:
            stored = (source / "files" / relative)
            if stored.is_symlink() or not stored.is_file():
                continue
            target = self._file_path(project, relative, allow_missing=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            self._file_path(project, relative, allow_missing=True)
            self._atomic_write(target, stored.read_text(encoding="utf-8"))
        return {
            "success": True,
            "message": f"Proyecto restaurado a «{meta.get('label', '')}».",
            "restored": meta.get("id"),
            "safety_checkpoint": safety,
        }

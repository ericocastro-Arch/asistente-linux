"""Ejecutor aislado del Módulo Dev basado en bubblewrap (bwrap).

El aislamiento real lo da el sandbox, no una lista de comandos permitidos:
- sin red (``--unshare-all``) ni acceso a la carpeta personal;
- ``/usr`` montado en solo lectura y solo la carpeta del proyecto con escritura;
- límites de CPU, memoria, tamaño de archivo y tiempo de pared;
- el proceso muere con la aplicación (``--die-with-parent``) y la salida se recorta.

Si bwrap no puede crear namespaces, el ejecutor se niega a correr código en lugar
de degradarse a una ejecución sin aislamiento.
"""

from __future__ import annotations

import os
import resource
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

SANDBOX_HOME = "/home/linuxmate"
SANDBOX_PROJECT = f"{SANDBOX_HOME}/proyecto"
DEFAULT_TIMEOUT = 15.0
MAX_TIMEOUT = 60.0
MAX_OUTPUT_BYTES = 64_000
MAX_STDIN_BYTES = 16_000
MEMORY_LIMIT_BYTES = 768 * 1024 * 1024
FILE_SIZE_LIMIT_BYTES = 20 * 1024 * 1024

# Intérprete por extensión: el agente y la interfaz solo eligen archivo, nunca una línea de shell.
# V8 reserva mucho espacio virtual al arrancar, así que Node usa su propio límite de heap
# en vez de RLIMIT_AS.
_NODE = {"label": "Node.js", "binary": "node", "args": ["--max-old-space-size=512"], "limit_as": False}
RUNTIMES: dict[str, dict[str, Any]] = {
    ".py": {"label": "Python", "binary": "python3", "args": ["-u"], "limit_as": True},
    ".sh": {"label": "Bash", "binary": "bash", "args": [], "limit_as": True},
    ".bash": {"label": "Bash", "binary": "bash", "args": [], "limit_as": True},
    ".js": _NODE,
    ".mjs": _NODE,
}

_RO_ETC = (
    "/etc/alternatives",
    "/etc/ld.so.cache",
    "/etc/ld.so.conf",
    "/etc/ld.so.conf.d",
    "/etc/localtime",
    "/etc/manpath.config",
    "/etc/mime.types",
    "/etc/python3",
    "/etc/ssl/certs",
)


@dataclass
class RunResult:
    success: bool
    exit_code: Optional[int]
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    timed_out: bool = False
    truncated: bool = False
    runtime: str = ""
    command: str = ""
    message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": round(self.duration, 3),
            "timed_out": self.timed_out,
            "truncated": self.truncated,
            "runtime": self.runtime,
            "command": self.command,
            "message": self.message,
            **self.extra,
        }


class SandboxUnavailable(RuntimeError):
    """bwrap no está instalado o el kernel/AppArmor no permite crear namespaces."""


def _set_limits(cpu_seconds: int, limit_address_space: bool = True) -> Callable[[], None]:
    def apply() -> None:
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        if limit_address_space:
            resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
        resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_SIZE_LIMIT_BYTES, FILE_SIZE_LIMIT_BYTES))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    return apply


class SandboxRunner:
    def __init__(self, bwrap_path: Optional[str] = None) -> None:
        self.bwrap = bwrap_path or shutil.which("bwrap")
        self._status: Optional[dict[str, Any]] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ estado
    def status(self, refresh: bool = False) -> dict[str, Any]:
        """Comprueba una sola vez (cacheado) que bwrap puede crear un sandbox real."""
        with self._lock:
            if self._status is not None and not refresh:
                return self._status
            runtimes = {
                info["label"]: bool(shutil.which(info["binary"]))
                for info in RUNTIMES.values()
            }
            python_version = ""
            if shutil.which("python3"):
                try:
                    out = subprocess.run(["python3", "--version"], capture_output=True, text=True, timeout=5)
                    python_version = (out.stdout or out.stderr).strip().replace("Python ", "")
                except (OSError, subprocess.SubprocessError):
                    python_version = ""
            if not self.bwrap:
                self._status = {
                    "available": False,
                    "runtimes": runtimes,
                    "python_version": python_version,
                    "message": "Falta bubblewrap. Instálalo con: sudo apt install bubblewrap",
                }
                return self._status
            try:
                probe = subprocess.run(
                    self._base_args(None) + ["true"],
                    capture_output=True, text=True, timeout=10,
                )
                ok = probe.returncode == 0
                detail = (probe.stderr or "").strip()
            except (OSError, subprocess.SubprocessError) as exc:
                ok, detail = False, str(exc)
            self._status = {
                "available": ok,
                "runtimes": runtimes,
                "python_version": python_version,
                "message": "Sandbox activo" if ok else (
                    "bubblewrap no pudo crear el entorno aislado"
                    + (f": {detail[:160]}" if detail else ".")
                ),
            }
            return self._status

    # ------------------------------------------------------------- argumentos
    def _base_args(self, project: Optional[Path]) -> list[str]:
        args = [
            self.bwrap or "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--hostname", "linuxmate-sandbox",
            "--ro-bind", "/usr", "/usr",
            "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/sbin", "/sbin",
            "--symlink", "usr/lib", "/lib",
        ]
        if Path("/usr/lib64").exists():
            args += ["--symlink", "usr/lib64", "/lib64"]
        for path in _RO_ETC:
            args += ["--ro-bind-try", path, path]
        args += [
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--tmpfs", "/home",
            "--dir", SANDBOX_HOME,
            "--clearenv",
            "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
            "--setenv", "HOME", SANDBOX_HOME,
            "--setenv", "USER", "linuxmate",
            "--setenv", "LANG", "C.UTF-8",
            "--setenv", "LC_ALL", "C.UTF-8",
            "--setenv", "TERM", "dumb",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
            "--setenv", "PYTHONUNBUFFERED", "1",
            "--setenv", "PYTHONIOENCODING", "utf-8",
        ]
        if project is not None:
            args += ["--bind", str(project), SANDBOX_PROJECT, "--chdir", SANDBOX_PROJECT]
        return args

    @staticmethod
    def runtime_for(relative_path: str) -> Optional[dict[str, Any]]:
        return RUNTIMES.get(Path(relative_path).suffix.lower())

    def build_command(self, project: Path, relative_path: str) -> tuple[list[str], dict[str, Any]]:
        runtime = self.runtime_for(relative_path)
        if runtime is None:
            raise ValueError(
                "Solo se pueden ejecutar archivos .py, .sh o .js. "
                "Los proyectos web se abren en el navegador."
            )
        if not shutil.which(runtime["binary"]):
            raise ValueError(f"{runtime['label']} no está instalado en este equipo.")
        inner = [runtime["binary"], *runtime["args"], relative_path]
        return self._base_args(project) + ["--", *inner], runtime

    # --------------------------------------------------------------- ejecutar
    def run_file(
        self,
        project: Path,
        relative_path: str,
        *,
        stdin_text: str = "",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> RunResult:
        status = self.status()
        if not status.get("available"):
            raise SandboxUnavailable(status.get("message") or "Sandbox no disponible.")
        project = Path(project).resolve()
        target = (project / relative_path).resolve()
        if not target.is_relative_to(project) or not target.is_file():
            raise ValueError("El archivo a ejecutar debe existir dentro del proyecto.")
        if len((stdin_text or "").encode("utf-8")) > MAX_STDIN_BYTES:
            raise ValueError("La entrada del programa supera 16 KB.")
        timeout = max(1.0, min(float(timeout or DEFAULT_TIMEOUT), MAX_TIMEOUT))

        command, runtime = self.build_command(project, relative_path)
        shown = f"{runtime['binary']} {relative_path}"
        started = time.monotonic()
        try:
            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=_set_limits(int(timeout) + 1, runtime.get("limit_as", True)),
                close_fds=True,
            )
        except OSError as exc:
            raise SandboxUnavailable(f"No se pudo iniciar el sandbox: {exc}") from exc

        stdout, stderr, truncated = bytearray(), bytearray(), False

        def pump(stream, sink: bytearray) -> None:
            nonlocal truncated
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                room = MAX_OUTPUT_BYTES - len(sink)
                if room > 0:
                    sink.extend(chunk[:room])
                if len(chunk) > max(room, 0):
                    truncated = True
            stream.close()

        readers = [
            threading.Thread(target=pump, args=(proc.stdout, stdout), daemon=True),
            threading.Thread(target=pump, args=(proc.stderr, stderr), daemon=True),
        ]
        for reader in readers:
            reader.start()
        try:
            if stdin_text:
                proc.stdin.write(stdin_text.encode("utf-8"))
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

        timed_out = False
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            proc.wait()
        for reader in readers:
            reader.join(timeout=2)

        duration = time.monotonic() - started
        code = proc.returncode
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        if code == -signal.SIGXCPU or code == 128 + signal.SIGXCPU:
            err += "\n[LinuxMate] El programa superó el límite de tiempo de CPU."
        if timed_out:
            message = f"El programa tardó más de {timeout:.0f} s y se detuvo."
        elif code == 0:
            message = "El programa terminó correctamente."
        else:
            message = f"El programa terminó con error (código {code})."
        return RunResult(
            success=(code == 0 and not timed_out),
            exit_code=code,
            stdout=out,
            stderr=err,
            duration=duration,
            timed_out=timed_out,
            truncated=truncated,
            runtime=runtime["label"],
            command=shown,
            message=message,
        )

    # ------------------------------------------------------------ documentación
    def lookup_docs(self, query: str) -> dict[str, Any]:
        """Consulta documentación local (pydoc3 o man) dentro del sandbox o en modo lectura segura."""
        import re

        clean = (query or "").strip()
        if clean.lower().startswith("python "):
            clean = clean[7:].strip()
        elif clean.lower().startswith("man "):
            clean = clean[4:].strip()
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", clean) or len(clean) > 64:
            return {"success": False, "query": query, "content": "Consulta inválida. Usa un nombre como 'os.listdir' o 'chmod'."}

        # Intentar primero pydoc3 si parece módulo/función Python o comando general
        candidates: list[tuple[str, list[str]]] = []
        if shutil.which("pydoc3"):
            candidates.append(("pydoc3", ["pydoc3", clean]))
        if shutil.which("man") and "." not in clean:
            candidates.append(("man", ["man", "-P", "cat", clean]))

        for source, inner_cmd in candidates:
            try:
                cmd = (self._base_args(None) + ["--", *inner_cmd]) if self.status().get("available") else inner_cmd
                env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "MANWIDTH": "90"}
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, env=env)
                text_out = (res.stdout or "").strip()
                if res.returncode == 0 and text_out and "No Python documentation found" not in text_out:
                    lines = [line for line in text_out.splitlines() if line.strip()][:45]
                    return {
                        "success": True,
                        "query": clean,
                        "source": source,
                        "content": "\n".join(lines)[:2800],
                    }
            except (OSError, subprocess.SubprocessError):
                continue

        return {
            "success": False,
            "query": clean,
            "source": "local",
            "content": f"No se encontró documentación local para '{clean}'.",
        }


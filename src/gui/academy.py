"""Ventana de aprendizaje y almacenamiento local, independientes del agente IA."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer
from socketserver import ThreadingMixIn

import bottle
import webview


class AcademyApi:
    """La academia solo expone lectura y guardado de su propio progreso."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".config/asistente-linux/learning.json"
        self._media_dir = self._path.parent / "learning-videos"
        self._media_index = self._path.parent / "learning-videos.json"
        self._lock = threading.Lock()
        self._window = None
        self._media_address = None

    def _video_url(self, path: Path) -> str:
        if self._media_address is None:
            app = bottle.Bottle()
            token = uuid.uuid4().hex

            @app.get(f"/{token}/<name>")
            def media(name):
                if name != Path(name).name or Path(name).suffix.lower() not in {".mp4", ".webm", ".ogv", ".mov", ".mkv"}:
                    return bottle.HTTPError(404)
                return bottle.static_file(name, root=str(self._media_dir))

            class Server(ThreadingMixIn, WSGIServer):
                daemon_threads = True

            class QuietHandler(WSGIRequestHandler):
                def log_message(self, *args):
                    pass

            server = make_server("127.0.0.1", 0, app, server_class=Server, handler_class=QuietHandler)
            self._media_address = f"http://127.0.0.1:{server.server_port}/{token}/"
            threading.Thread(target=server.serve_forever, daemon=True).start()
        return self._media_address + quote(path.name)

    def _read_videos(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self._media_index.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        videos = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("file")
            video_id = item.get("id")
            if not isinstance(name, str) or not isinstance(video_id, str):
                continue
            path = self._media_dir / name
            try:
                if path.is_file() and path.parent == self._media_dir:
                    videos.append({
                        "id": video_id,
                        "title": str(item.get("title") or path.stem)[:120],
                        "file": path.name,
                        "url": self._video_url(path),
                        "size": path.stat().st_size,
                    })
            except OSError:
                continue
        return videos

    def _write_videos(self, videos: list[dict[str, Any]]) -> None:
        self._media_index.parent.mkdir(parents=True, exist_ok=True)
        payload = [{"id": item["id"], "title": item["title"], "file": item["file"]} for item in videos]
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self._media_index.parent, delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(self._media_index)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def list_learning_videos(self) -> dict[str, Any]:
        with self._lock:
            return {"success": True, "videos": self._read_videos()}

    def add_learning_video(self) -> dict[str, Any]:
        """Elige un video local y guarda una copia privada para la academia."""
        if self._window is None:
            return {"success": False, "message": "La ventana no está disponible."}
        try:
            selection = self._window.create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=False,
                file_types=("Videos (*.mp4;*.webm;*.ogv;*.mov;*.mkv)",),
            )
        except (OSError, RuntimeError, ValueError):
            return {"success": False, "message": "No se pudo abrir el selector de videos."}
        if not selection:
            return {"success": False, "cancelled": True}
        source = Path(selection[0] if isinstance(selection, (list, tuple)) else selection)
        allowed = {".mp4", ".webm", ".ogv", ".mov", ".mkv"}
        try:
            if not source.is_file() or source.suffix.lower() not in allowed:
                return {"success": False, "message": "Selecciona un archivo de video compatible."}
            if source.stat().st_size > 4 * 1024**3:
                return {"success": False, "message": "El video supera el límite de 4 GB."}
            with self._lock:
                self._media_dir.mkdir(parents=True, exist_ok=True)
                video_id = uuid.uuid4().hex
                destination = self._media_dir / f"{video_id}{source.suffix.lower()}"
                shutil.copy2(source, destination)
                videos = self._read_videos()
                videos.append({"id": video_id, "title": source.stem[:120], "file": destination.name, "url": self._video_url(destination), "size": destination.stat().st_size})
                self._write_videos(videos)
                return {"success": True, "video": videos[-1]}
        except OSError:
            return {"success": False, "message": "No se pudo copiar el video a la biblioteca local."}

    def remove_learning_video(self, video_id: str) -> dict[str, Any]:
        if not isinstance(video_id, str):
            return {"success": False, "message": "Video inválido."}
        with self._lock:
            videos = self._read_videos()
            match = next((item for item in videos if item["id"] == video_id), None)
            if match is None:
                return {"success": False, "message": "El video ya no está en la biblioteca."}
            try:
                (self._media_dir / match["file"]).unlink(missing_ok=True)
                self._write_videos([item for item in videos if item["id"] != video_id])
                return {"success": True}
            except OSError:
                return {"success": False, "message": "No se pudo quitar el video."}

    def prepare_learning_video(self, video_id: str) -> dict[str, Any]:
        """Crea una copia WebM reproducible sin borrar el archivo importado."""
        if not isinstance(video_id, str):
            return {"success": False, "message": "Video inválido."}
        converter = shutil.which("gst-launch-1.0")
        if not converter:
            return {"success": False, "message": "Falta GStreamer para preparar el video."}
        with self._lock:
            videos = self._read_videos()
            match = next((item for item in videos if item["id"] == video_id), None)
            if match is None:
                return {"success": False, "message": "El video ya no está en la biblioteca."}
            source = self._media_dir / match["file"]
            new_id = uuid.uuid4().hex
            destination = self._media_dir / f"{new_id}.webm"
        # GStreamer parses its own pipeline; quote paths for that parser, not a shell.
        def location(path: Path) -> str:
            return 'location="' + str(path).replace('\\', '\\\\').replace('"', '\\"') + '"'
        command = [converter, "-e", "filesrc", location(source), "!", "decodebin", "name=decode",
                   "webmmux", "name=mux", "!", "filesink", location(destination),
                   "decode.", "!", "queue", "!", "videoconvert", "!", "vp9enc",
                   "deadline=1", "cpu-used=4", "threads=4", "target-bitrate=1500000",
                   "!", "queue", "!", "mux.", "decode.", "!", "queue", "!",
                   "audioconvert", "!", "audioresample", "!", "opusenc", "!", "queue", "!", "mux."]
        try:
            discoverer = shutil.which("gst-discoverer-1.0")
            if discoverer:
                info = subprocess.run([discoverer, str(source)], capture_output=True, text=True,
                                      timeout=30, check=False)
                if info.returncode == 0 and "video #" in info.stdout and "audio #" not in info.stdout:
                    command = command[:command.index("mux.") + 1]
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=1800, check=False)
            if result.returncode or not destination.is_file() or not destination.stat().st_size:
                raise ValueError("conversion failed")
            with self._lock:
                videos = self._read_videos()
                video = {"id": new_id, "title": match["title"] + " (compatible)",
                         "file": destination.name, "url": self._video_url(destination),
                         "size": destination.stat().st_size}
                self._write_videos([*videos, video])
            return {"success": True, "video": video}
        except (OSError, ValueError, subprocess.TimeoutExpired):
            destination.unlink(missing_ok=True)
            return {"success": False, "message": "No se pudo convertir el video. Puede estar dañado o faltar un códec de GStreamer."}

    def export_learning_certificate(self, course_id: str, text: str) -> dict[str, Any]:
        """Exporta una constancia de autoestudio a la ubicación elegida en el diálogo."""
        if course_id not in ("fundamentos", "terminal", "administracion", "redes", "git", "contenedores") or not isinstance(text, str) or len(text) > 10000:
            return {"success": False, "message": "Constancia inválida."}
        if self._window is None:
            return {"success": False, "message": "La ventana no está disponible."}
        try:
            selection = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename=f"constancia-linuxmate-{course_id}.txt",
                file_types=("Archivos de texto (*.txt)",),
            )
            if not selection:
                return {"success": False, "cancelled": True}
            path = selection[0] if isinstance(selection, (list, tuple)) else selection
            Path(path).write_text(text, encoding="utf-8")
            return {"success": True}
        except (OSError, ValueError):
            return {"success": False, "message": "No se pudo escribir la constancia en esa ubicación."}

    def load_learning(self) -> dict[str, Any]:
        with self._lock:
            try:
                state = json.loads(self._path.read_text(encoding="utf-8"))
                if not isinstance(state, dict) or state.get("version") != 1:
                    raise ValueError("Formato de progreso desconocido")
                return {"success": True, "state": state}
            except FileNotFoundError:
                return {"success": True, "state": {"version": 1, "courses": {}}}
            except (OSError, ValueError):
                return {"success": False, "message": "No se pudo leer el progreso guardado. Cierra y vuelve a abrir la academia para reintentar."}

    def save_learning(self, state: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(state, dict) or state.get("version") != 1 or not isinstance(state.get("courses"), dict):
            return {"success": False, "message": "Formato de progreso inválido."}
        try:
            payload = json.dumps(state, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError):
            return {"success": False, "message": "No se pudo preparar el progreso."}
        if len(payload.encode("utf-8")) > 1_000_000:
            return {"success": False, "message": "El progreso supera el tamaño permitido."}
        with self._lock:
            temporary = None
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self._path.parent, delete=False) as handle:
                    temporary = Path(handle.name)
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                temporary.replace(self._path)
            except OSError:
                return {"success": False, "message": "No se pudo guardar. Comprueba el espacio y los permisos de tu carpeta personal."}
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return {"success": True}


class AcademyWindow:
    """Reutiliza una sola ventana; al cerrarla permite crear otra."""

    def __init__(self, api: AcademyApi | None = None) -> None:
        self._api = api or AcademyApi()
        self._window = None
        self._lock = threading.Lock()

    def open(self) -> dict[str, Any]:
        with self._lock:
            try:
                if self._window is not None:
                    self._window.restore()
                    self._window.show()
                else:
                    window = webview.create_window(
                        "Aprende Linux · LinuxMate Academy",
                        url=str(Path(__file__).resolve().parent / "web/academy.html") + "#desktop",
                        js_api=self._api, width=1280, height=840,
                        min_size=(760, 560), background_color="#0a0816", text_select=True,
                    )
                    if window is None:
                        raise RuntimeError("La ventana no está disponible")
                    self._window = window
                    self._api._window = window
                    window.events.closed += self._closed
                return {"success": True}
            except Exception:
                self._window = None
                return {"success": False, "message": "No se pudo abrir la academia. Inténtalo de nuevo."}

    def _closed(self) -> None:
        with self._lock:
            self._window = None
            self._api._window = None

    def summary(self) -> dict[str, Any]:
        result = self._api.load_learning()
        if not result["success"]:
            return result
        courses = result["state"].get("courses", {})
        completed = 0
        for course_id in ("fundamentos", "terminal", "administracion", "redes", "git", "contenedores"):
            course = courses.get(course_id, {}) if isinstance(courses, dict) else {}
            lessons = course.get("completed", []) if isinstance(course, dict) else []
            if isinstance(lessons, list):
                completed += len({item for item in lessons if type(item) is int and 0 <= item < 15})
        return {"success": True, "completed": completed, "total": 90}

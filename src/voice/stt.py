"""Módulo de reconocimiento de voz (Speech-To-Text) con Vosk y SoundDevice."""

import json
import os
import queue
import threading
from pathlib import Path
from typing import Callable, Optional


class STTEngine:
    """Reconocedor de voz offline con Vosk y captura de audio con sounddevice."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.samplerate = 16000
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._is_listening = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._model_path = model_path
        self._model_load_attempted = False
        self.model = None

    def _load_model(self, model_path: Optional[str]):
        """Carga el modelo de Vosk en español desde una ruta local o el idioma del sistema."""
        try:
            import vosk
        except ImportError:
            return None
        candidate_paths = [
            model_path,
            str(Path(__file__).resolve().parents[2] / "assets" / "vosk-model-small-es-0.42"),
            str(Path(__file__).resolve().parents[2] / "assets" / "model"),
            str(Path(__file__).resolve().parents[2] / "model"),
            os.path.expanduser("~/.cache/vosk/vosk-model-small-es-0.42"),
        ]

        for path in candidate_paths:
            if path and os.path.isdir(path):
                try:
                    vosk.SetLogLevel(-1)
                    return vosk.Model(path)
                except Exception:
                    pass

        # Intento de cargar o descargar el modelo ligero en español con Vosk
        try:
            vosk.SetLogLevel(-1)
            return vosk.Model(lang="es")
        except Exception:
            return None

    @property
    def is_available(self) -> bool:
        """Indica si el modelo Vosk está listo para usarse."""
        if not self._model_load_attempted:
            self._model_load_attempted = True
            self.model = self._load_model(self._model_path)
        return self.model is not None

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def start_listening(
        self,
        on_text_recognized: Callable[[str], None],
        on_status_change: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Inicia la captura continua de voz en un hilo secundario."""
        if not self.is_available:
            if on_status_change:
                on_status_change("Modelo Vosk en español no encontrado.")
            return False

        if self._is_listening:
            return True

        self._stop_event.clear()
        self._is_listening = True
        self._thread = threading.Thread(
            target=self._listen_worker,
            args=(on_text_recognized, on_status_change),
            daemon=True,
        )
        self._thread.start()
        return True

    def stop_listening(self) -> None:
        """Detiene la captura de voz."""
        self._stop_event.set()
        self._is_listening = False

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback invocado por sounddevice con nuevos fragmentos de audio PCM."""
        if status and status.input_overflow:
            pass
        self._audio_queue.put(bytes(indata))

    def _listen_worker(
        self,
        on_text_recognized: Callable[[str], None],
        on_status_change: Optional[Callable[[str], None]],
    ) -> None:
        """Hilo de escucha y procesamiento de audio con Vosk."""
        if not self.model:
            return

        try:
            import sounddevice as sd
            import vosk
        except ImportError:
            if on_status_change:
                on_status_change("Faltan dependencias de reconocimiento de voz.")
            self._is_listening = False
            return

        recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)

        if on_status_change:
            on_status_change("Escuchando...")

        try:
            with sd.RawInputStream(
                samplerate=self.samplerate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self._audio_callback,
            ):
                while not self._stop_event.is_set():
                    try:
                        data = self._audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            on_text_recognized(text)
                            if on_status_change:
                                on_status_change("Voz reconocida")
        except Exception as exc:
            if on_status_change:
                on_status_change(f"Error de micrófono: {exc}")
        finally:
            self._is_listening = False
            if on_status_change:
                on_status_change("Micrófono detenido")

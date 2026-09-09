"""Módulo de síntesis de voz (Text-To-Speech) con pyttsx3."""

import queue
import re
import threading
from typing import Optional


def clean_markdown_for_speech(text: str) -> str:
    """Limpia sintaxis markdown para que la lectura de voz suene fluida y natural."""
    # Quitar bloques de código
    text = re.sub(r"```[\s\S]*?```", " código omitido en audio. ", text)
    # Quitar código en línea
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Quitar encabezados (#, ##, etc)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    # Quitar negritas y cursivas
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    # Quitar tablas y barras verticales
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"-{3,}", "", text)
    # Quitar enlaces markdown [texto](url)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Quitar emojis o caracteres extraños repetidos
    text = re.sub(r"\s+", " ", text).strip()
    return text


class TTSEngine:
    """Motor de voz en segundo plano para no congelar la interfaz gráfica."""

    def __init__(self, rate: int = 160) -> None:
        self.rate = rate
        self._queue: queue.Queue[Optional[str]] = queue.Queue()
        self._is_enabled = True
        self._is_speaking = False
        self._worker_thread: Optional[threading.Thread] = None

    def _ensure_worker(self) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._worker_thread.start()

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    @is_enabled.setter
    def is_enabled(self, value: bool) -> None:
        self._is_enabled = value

    def speak(self, text: str) -> None:
        """Encola un texto para ser reproducido en voz alta si está habilitado."""
        if not self._is_enabled or not text.strip():
            return
        clean_text = clean_markdown_for_speech(text)
        if clean_text:
            self._ensure_worker()
            self._queue.put(clean_text)

    def stop(self) -> None:
        """Detiene y limpia la cola de habla pendiente."""
        with self._queue.mutex:
            self._queue.queue.clear()

    def _select_spanish_voice(self, engine) -> None:
        """Intenta configurar una voz en español disponible en el sistema."""
        try:
            voices = engine.getProperty("voices")
            for voice in voices:
                voice_id = voice.id.lower()
                voice_langs = [str(lang).lower() for lang in getattr(voice, "languages", [])]
                if "es" in voice_id or any("es" in l for l in voice_langs) or "spanish" in voice.name.lower():
                    engine.setProperty("voice", voice.id)
                    return
        except Exception:
            pass

    def _run_loop(self) -> None:
        """Bucle que consume mensajes de la cola y los reproduce con pyttsx3."""
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            self._select_spanish_voice(engine)
        except Exception:
            engine = None

        while True:
            text = self._queue.get()
            if text is None:
                break

            if engine and self._is_enabled:
                try:
                    self._is_speaking = True
                    engine.say(text)
                    engine.runAndWait()
                except Exception:
                    pass
                finally:
                    self._is_speaking = False

            self._queue.task_done()

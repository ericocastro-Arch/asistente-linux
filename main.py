#!/usr/bin/env python3
"""Punto de entrada de LinuxMate AI — Liquid Glass Edition."""

import os
import sys

# Auto-activación / re-ejecución con el entorno virtual si falta alguna librería
base_dir = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(base_dir, "venv", "bin", "python")
if os.path.exists(venv_python) and os.path.realpath(sys.executable) != os.path.realpath(venv_python):
    try:
        import webview  # noqa: F401
    except ImportError:
        os.execv(venv_python, [venv_python] + sys.argv)


def start_app() -> None:
    """Inicia la interfaz de LinuxMate AI priorizando PyWebView con fallback seguro."""
    force_tk = "--tk" in sys.argv or "--customtkinter" in sys.argv

    if not force_tk:
        try:
            from src.gui.webview_app import run_webview
            print("🚀 Iniciando LinuxMate AI (PyWebView Liquid Glass)...")
            run_webview(debug="--debug" in sys.argv)
            return
        except Exception as exc:
            print(f"⚠️ Aviso: PyWebView no pudo iniciarse ({exc}).")
            print("🔄 Iniciando modo de respaldo seguro (CustomTkinter)...")

    # Respaldo seguro garantizado con CustomTkinter
    from src.gui.app import run
    run()


if __name__ == "__main__":
    start_app()

#!/usr/bin/env python3
"""Prueba rápida de todas las librerías instaladas"""

import sys
print(f"✓ Python: {sys.version}")

# CustomTkinter
try:
    import customtkinter as ctk
    print(f"✓ CustomTkinter: {ctk.__version__}")
except Exception as e:
    print(f"✗ CustomTkinter: {e}")

# Vosk
try:
    import vosk
    print("✓ Vosk: OK")
except Exception as e:
    print(f"✗ Vosk: {e}")

# pyttsx3
try:
    import pyttsx3
    engine = pyttsx3.init()
    print("✓ pyttsx3: OK")
except Exception as e:
    print(f"✗ pyttsx3: {e}")

# Groq
try:
    from groq import Groq
    print("✓ Groq: OK")
except Exception as e:
    print(f"✗ Groq: {e}")

print("\n🎉 ¡Todo funciona correctamente!")

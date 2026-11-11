"""Read-only discovery and deterministic routing; never executes user input."""
import os
import platform
import shutil
import subprocess
from pathlib import Path

import psutil


DETECTORS = {
    "wine": (("wine", "wine64"), None),
    "bottles": (("bottles",), "com.usebottles.bottles"),
    "lutris": (("lutris",), "net.lutris.Lutris"),
    "proton": (("steam",), "com.valvesoftware.Steam"),
    "heroic": (("heroic",), "com.heroicgameslauncher.hgl"),
    "winboat": (("winboat",), None),
    "wineboot": (("wineboot",), None),
}
ROUTES = {
    "application": ("bottles", "Una botella separada permite probar una aplicación y sus dependencias.", ["wine", "winboat"]),
    "steam": ("proton", "Steam integra Proton para sus juegos de Windows.", ["lutris"]),
    "stores": ("heroic", "Heroic reúne Epic, GOG y Amazon Games.", ["lutris"]),
    "other-game": ("lutris", "Lutris permite gestionar instaladores y runners por juego.", ["bottles"]),
    "full-windows": ("winboat", "Evalúa un Windows virtualizado cuando necesitas el entorno completo.", ["bottles"]),
}


def recommend_compatibility(payload):
    if not isinstance(payload, dict):
        raise ValueError("La consulta debe ser un objeto.")
    use = payload.get("use_case", "application")
    if not isinstance(use, str) or use not in ROUTES:
        raise ValueError("Selecciona un tipo de uso válido.")
    name = payload.get("application", "")
    if not isinstance(name, str) or len(name) > 160:
        raise ValueError("Usa como máximo 160 caracteres para la aplicación y versión.")
    special = payload.get("special_requirements", False)
    if not isinstance(special, bool):
        raise ValueError("Los requisitos especiales deben ser verdadero o falso.")
    tool, reason, alternatives = ROUTES[use]
    steps = ["Busca la versión exacta y sus complementos en las fuentes de la ficha.",
             "Prueba instalación, apertura y guardado con una copia de tus datos."]
    if special:
        steps.insert(0, "Confirma con el fabricante el anti-cheat, controlador, dongle o acceso a GPU requerido. Ni Wine ni una VM garantizan ese soporte; conserva acceso a Windows mientras lo verificas.")
    return {"tool": tool, "alternatives": list(alternatives), "reason": reason,
            "application": name.strip(), "needs_review": True, "checks": steps,
            "notice": "Ruta sugerida por tipo de uso. No se ha verificado la compatibilidad de esta aplicación."}


def compatibility_overview():
    flatpaks = set()
    flatpak_error = None
    if shutil.which("flatpak"):
        try:
            result = subprocess.run(["flatpak", "list", "--app", "--columns=application"],
                                    capture_output=True, text=True, timeout=5, check=False)
            if result.returncode == 0:
                flatpaks = set(result.stdout.splitlines())
            else:
                flatpak_error = "No se pudo leer la lista de Flatpak."
        except (OSError, subprocess.TimeoutExpired):
            flatpak_error = "La consulta Flatpak no respondió. Puedes volver a intentarlo."
    tools = {}
    for key, (binaries, flatpak) in DETECTORS.items():
        native = any(shutil.which(binary) for binary in binaries)
        formats = (["Ejecutable en PATH"] if native else []) + (["Flatpak"] if flatpak in flatpaks else [])
        tools[key] = {"detected": bool(formats), "formats": formats,
                      "status": "Detectado" if formats else "Sin comprobar" if flatpak and flatpak_error else "No detectado",
                      "note": "Steam detectado; Proton y cada juego se verifican dentro de Steam." if key == "proton" else ""}
    try:
        memory = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except (OSError, RuntimeError):
        memory = None
    try:
        free = round(shutil.disk_usage(Path.home()).free / (1024 ** 3), 1)
    except OSError:
        free = None
    kvm = os.path.exists("/dev/kvm")
    return {"tools": tools, "machine": {
        "architecture": platform.machine(), "ram_gib": memory, "cpu_threads": os.cpu_count(),
        "home_free_gib": free, "kvm_present": kvm,
        "kvm_access": kvm and os.access("/dev/kvm", os.R_OK | os.W_OK),
        "docker": bool(shutil.which("docker")), "podman": bool(shutil.which("podman")),
        "freerdp": any(shutil.which(name) for name in ("xfreerdp3", "xfreerdp", "sdl-freerdp3", "sdl-freerdp")),
    }, "notices": [*([flatpak_error] if flatpak_error else []),
        "Detección limitada a PATH y Flatpak. Las AppImage, instalaciones portátiles y runners internos pueden no aparecer.",
        "Encontrar un ejecutable no verifica versiones, servicios, Compose, Vulkan ni compatibilidad. El disco mostrado es el de tu carpeta personal, no necesariamente el destino de WinBoat."]}

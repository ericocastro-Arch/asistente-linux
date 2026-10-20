"""Equivalencias orientativas de funciones y programas de Windows en Linux."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _item(
    item_id: str,
    kind: str,
    windows: str,
    linux: str,
    note: str,
    searches: tuple[tuple[str, str], ...] = (),
    keywords: str = "",
) -> dict[str, Any]:
    return {
        "id": item_id,
        "kind": kind,
        "windows": windows,
        "linux": linux,
        "note": note,
        "searches": [{"name": name, "query": query} for name, query in searches],
        "keywords": keywords,
    }


WINDOWS_ITEMS = (
    _item("task-manager", "feature", "Administrador de tareas", "Monitor del sistema (GNOME) o Monitor del sistema (KDE)", "Permite ver procesos y uso de recursos; los nombres varían según el escritorio.", (("Monitor del sistema", "gnome-system-monitor"),), "procesos cpu ram rendimiento"),
    _item("file-explorer", "feature", "Explorador de archivos", "Archivos (GNOME) o Dolphin (KDE)", "La carpeta personal equivale al lugar habitual para tus documentos.", (("Archivos", "nautilus"), ("Dolphin", "dolphin")), "carpetas documentos archivos"),
    _item("control-panel", "feature", "Panel de control / Configuración", "Configuración del escritorio", "Busca Red, Pantallas, Sonido o Usuarios en el menú del sistema.", keywords="ajustes settings preferencias"),
    _item("windows-update", "feature", "Windows Update", "Actualizador de software o gestor de paquetes", "En Debian/Ubuntu, APT actualiza paquetes; otras distribuciones usan gestores diferentes.", keywords="actualizaciones apt update upgrade"),
    _item("disk-management", "feature", "Administración de discos", "Discos (GNOME) o GParted", "Modificar particiones puede borrar datos: haz una copia de seguridad antes.", (("Discos", "gnome-disk-utility"), ("GParted", "gparted")), "particiones almacenamiento"),
    _item("event-viewer", "feature", "Visor de eventos", "Registros (GNOME) o journalctl", "Los registros ayudan a investigar servicios y aplicaciones que fallaron.", (("Registros", "gnome-logs"),), "logs errores servicios"),
    _item("notepad", "feature", "Bloc de notas", "Editor de texto (GNOME) o Kate", "Son editores de texto simple; no sustituyen a un procesador de documentos.", (("Editor de texto", "gnome-text-editor"), ("Kate", "kate")), "texto editor"),
    _item("snipping-tool", "feature", "Recortes / Captura de pantalla", "Captura de pantalla del escritorio o Flameshot", "La herramienta integrada depende del escritorio que utilices.", (("Flameshot", "flameshot"),), "captura screenshot pantalla"),
    _item("system-restore", "feature", "Restaurar sistema", "Timeshift", "Crea instantáneas del sistema; no reemplaza una copia de tus documentos personales.", (("Timeshift", "timeshift"),), "punto restauración backup copia"),
    _item("device-manager", "feature", "Administrador de dispositivos", "Información del sistema y herramientas de hardware", "Para controladores, revisa la configuración de tu distribución; no todos se instalan igual.", keywords="drivers hardware gpu wifi bluetooth"),
    _item("start-menu", "feature", "Menú Inicio y búsqueda", "Menú de aplicaciones del escritorio", "Busca aplicaciones y archivos desde el menú; su ubicación cambia según GNOME, KDE u otro escritorio.", keywords="inicio launcher aplicaciones buscar programas"),
    _item("uninstall-programs", "feature", "Agregar o quitar programas", "Centro de software o gestor de paquetes", "Desinstala desde la misma tienda o gestor con el que instalaste la aplicación.", keywords="desinstalar instalar software aplicaciones borrar quitar"),
    _item("wifi-network", "feature", "Conectarse a una red Wi-Fi", "Configuración de Red del escritorio", "Abre el menú de red, elige la conexión y escribe la contraseña; los nombres varían por distribución.", keywords="internet wifi inalámbrica ethernet red conexión"),
    _item("bluetooth", "feature", "Conectar dispositivos Bluetooth", "Configuración de Bluetooth", "Activa Bluetooth desde la configuración del sistema y empareja el dispositivo.", keywords="audífonos auriculares mouse teclado inalámbrico emparejar"),
    _item("printers", "feature", "Impresoras y escáneres", "Configuración de Impresoras del sistema", "La compatibilidad depende del modelo; algunos equipos requieren instalar controladores del fabricante.", keywords="impresión escaner scanner impresora documentos"),
    _item("virtual-desktops", "feature", "Escritorios virtuales", "Áreas de trabajo del escritorio", "Permiten organizar ventanas en espacios separados; los atajos dependen del escritorio.", keywords="ventanas escritorios areas trabajo multitarea"),
    _item("default-apps", "feature", "Aplicaciones predeterminadas", "Aplicaciones predeterminadas en Configuración", "Puedes elegir qué navegador, correo o reproductor abre cada tipo de archivo.", keywords="predeterminado navegador correo abrir archivos formato"),
    _item("powershell", "feature", "PowerShell / Símbolo del sistema", "Terminal de Linux", "Los comandos de Bash no son idénticos a los de PowerShell.", keywords="cmd consola bash shell"),
    _item("photoshop", "app", "Adobe Photoshop", "GIMP para edición de imágenes; Krita para pintura digital", "No son reemplazos idénticos. Revisa tus formatos y funciones antes de migrar proyectos.", (("GIMP", "gimp"), ("Krita", "krita")), "fotografía imagen diseño pintura psd"),
    _item("office", "app", "Microsoft Office", "LibreOffice u ONLYOFFICE", "La apariencia de algunos documentos de Office puede cambiar.", (("LibreOffice", "libreoffice"), ("ONLYOFFICE", "onlyoffice")), "ofimática documentos"),
    _item("word", "app", "Microsoft Word", "LibreOffice Writer", "Puede abrir DOCX, aunque el diseño de documentos complejos puede variar.", (("LibreOffice Writer", "libreoffice-writer"),), "docx procesador texto"),
    _item("excel", "app", "Microsoft Excel", "LibreOffice Calc", "Comprueba fórmulas y macros de tus archivos XLSX antes de depender de ellos.", (("LibreOffice Calc", "libreoffice-calc"),), "xlsx hojas cálculo tablas"),
    _item("powerpoint", "app", "Microsoft PowerPoint", "LibreOffice Impress", "Revisa animaciones y diseño al abrir presentaciones PPTX.", (("LibreOffice Impress", "libreoffice-impress"),), "pptx presentaciones diapositivas"),
    _item("illustrator", "app", "Adobe Illustrator", "Inkscape", "Editor vectorial; los proyectos de Illustrator pueden requerir exportación previa.", (("Inkscape", "inkscape"),), "vectores svg ilustración"),
    _item("premiere", "app", "Adobe Premiere Pro", "Kdenlive o Shotcut", "Editan video, pero no abren directamente todos los proyectos de Premiere.", (("Kdenlive", "kdenlive"), ("Shotcut", "shotcut")), "video edición montaje"),
    _item("audition", "app", "Adobe Audition", "Audacity", "Sirve para grabar y editar audio; las sesiones y flujos de trabajo son distintos.", (("Audacity", "audacity"),), "audio grabación sonido"),
    _item("paint", "app", "Microsoft Paint", "Pinta o Krita", "Pinta es sencillo; Krita está orientado a ilustración digital.", (("Pinta", "pinta"), ("Krita", "krita")), "dibujar imagen"),
    _item("notepad-plus", "app", "Notepad++", "Kate", "Editor de código y texto con pestañas y resaltado de sintaxis.", (("Kate", "kate"),), "programación código editor"),
    _item("winrar", "app", "WinRAR", "Gestor de archivadores o Ark", "El soporte de formatos depende de los componentes instalados.", (("Ark", "ark"),), "rar zip comprimir descomprimir"),
    _item("vscode", "app", "Visual Studio Code", "Visual Studio Code para Linux", "Es la misma aplicación; revisa las extensiones que utilizas.", (("Visual Studio Code", "code"),), "vscode programación editor"),
    _item("chrome", "app", "Google Chrome", "Google Chrome para Linux", "Es la misma aplicación; la sincronización depende de tu cuenta.", (("Google Chrome", "chrome"),), "navegador browser web"),
    _item("steam", "app", "Steam", "Steam para Linux", "No todos los juegos de Windows funcionan; consulta su compatibilidad antes de instalarlos.", (("Steam", "steam"),), "gaming juegos proton"),
)


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


_SEARCH_FILLER = {
    "a", "alternativa", "como", "de", "del", "donde", "el", "en", "equivalente",
    "esta", "esto", "la", "las", "linux", "lo", "los", "mi", "para", "que",
    "un", "una", "windows",
}


def search_windows_guide(query: str = "", kind: str = "all") -> list[dict[str, Any]]:
    """Filtra referencias locales; no consulta red ni realiza instalaciones."""
    selected_kind = kind if kind in {"all", "feature", "app"} else "all"
    terms = [term for term in re.findall(r"[a-z0-9]+", _fold((query or "")[:100])) if term not in _SEARCH_FILLER]
    results = []
    for item in WINDOWS_ITEMS:
        if selected_kind != "all" and item["kind"] != selected_kind:
            continue
        searchable = _fold(" ".join((item["windows"], item["linux"], item["keywords"])))
        if all(term in searchable for term in terms):
            results.append({key: value for key, value in item.items() if key != "keywords"})
    return results

"""Enrutamiento determinista entre acciones locales y consultas para la IA."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


VISUAL_INTENTS = frozenset({
    "SHOW_PROCESSES",
    "SHOW_NETWORK",
    "UPDATE_SYSTEM",
    "INSTALL_PACKAGE",
    "INSTALL_DEB",
})


@dataclass(frozen=True)
class RequestRoute:
    """Resultado estable del analisis de una solicitud del usuario."""

    intent: Optional[str] = None
    param: Optional[str] = None
    destination: str = "ai"
    reason: str = "No coincide con una accion local conocida."

    @property
    def is_local(self) -> bool:
        return self.destination == "local"

    @property
    def is_visual(self) -> bool:
        return self.intent in VISUAL_INTENTS


def _fold_text(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in folded if not unicodedata.combining(char))


def normalize_text(text: str) -> str:
    """Normaliza mayusculas, tildes y puntuacion para comparar frases."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", _fold_text(text))).strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    return f" {normalize_text(phrase)} " in f" {text} "


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_contains_phrase(text, phrase) for phrase in phrases)


OPEN_ACTIONS = (
    "abrir", "abre", "abreme", "abras", "arir", "habre", "ejecutar", "ejecuta",
    "iniciar", "inicia", "lanzar", "lanza",
)
VIEW_ACTIONS = (
    "ver", "ve", "mostrar", "muestra", "muestrame", "revisar", "revisa",
    "listar", "lista", "consultar", "consulta",
)
CHANGE_ACTIONS = (
    "cambiar", "cambia", "cambiame", "configurar", "configura", "poner", "pon",
)
INSTALL_ACTIONS = (
    "instalar", "instala", "instalame", "instalarme", "intalar", "intala", "intalarme",
)


def _has_action(text: str, actions: tuple[str, ...]) -> bool:
    return _contains_any(text, actions)


def _is_explanation_request(text: str) -> bool:
    patterns = (
        r"\bcomo\s+(?:puedo\s+|se\s+|debo\s+|hago\s+para\s+)?(?:abrir|cambiar|configurar|instalar|actualizar|ver)\b",
        r"\b(?:explica|explicame|ensena|ensenarme|quiero saber)\b.*\b(?:abrir|cambiar|configurar|instalar|actualizar)\b",
        r"\b(?:cual|que)\s+(?:es\s+)?(?:el\s+)?comando\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _is_negated_action(text: str) -> bool:
    actions = "|".join((*OPEN_ACTIONS, *CHANGE_ACTIONS, *INSTALL_ACTIONS, "actualizar", "actualiza"))
    return bool(re.search(rf"\b(?:no|nunca)\b(?:\s+\w+){{0,5}}\s+(?:{actions})\b", text))


def _local(intent: str, param: Optional[str] = None, reason: str = "") -> RequestRoute:
    return RequestRoute(intent=intent, param=param, destination="local", reason=reason)


def _extract_action_target(text: str, actions: tuple[str, ...]) -> str:
    action_pattern = "|".join(sorted((re.escape(action) for action in actions), key=len, reverse=True))
    match = re.search(rf"\b(?:{action_pattern})\b\s+(?P<target>.+)", text)
    if not match:
        return ""

    target = match.group("target").strip(" .,:;!?¿¡\"'")
    target = re.sub(r"^(?:el|la|los|las|un|una)\s+", "", target)
    target = re.sub(r"\b(?:por favor|porfa|please)\b", "", target)
    target = re.sub(
        r"\b(?:en|de)\s+(?:mi\s+)?(?:ubuntu|linux|sistema|computadora|ordenador|pc)\b.*$",
        "",
        target,
    )
    return re.sub(r"\s+", " ", target).strip(" .,:;!?¿¡\"'")


APP_ALIASES = {
    "terminal": ("terminal", "consola", "shell", "bash"),
    "explorador": (
        "explorador de archivos", "gestor de archivos", "explorador", "archivos",
        "carpetas", "nautilus", "nemo", "thunar", "dolphin",
    ),
    "navegador": ("navegador", "internet", "web"),
    "firefox": ("mozilla firefox", "firefox"),
    "google-chrome": ("google chrome", "chrome"),
    "chromium": ("chromium browser", "chromium"),
    "calculadora": ("calculadora", "calc"),
    "monitor": ("monitor", "administrador de tareas"),
    "editor": ("editor de texto", "bloc de notas", "editor", "notas", "gedit"),
    "configuracion": ("panel de control", "configuracion", "ajustes"),
    "wine": ("interfaz de wine", "configuracion de wine", "winecfg", "wine"),
    "netbeans": ("apache netbeans", "apache-netbeans", "netbeans"),
    "trilium notes": ("trilium notes", "trilium-notes", "trilium"),
    "code": ("visual studio code", "vs code", "vscode"),
    "libreoffice": ("libreoffice",),
    "proton vpn": (
        "proton vpn", "protonvpn", "proton-vpn", "la vpn de proton", "vpn de proton", "vpn proton", "proton",
    ),
    "proton mail": ("proton mail", "protonmail"),
    "brave": ("brave browser", "brave", "navegador brave"),
    "discord": ("discord",),
    "telegram": ("telegram desktop", "telegram"),
    "spotify": ("spotify",),
}


def _resolve_app_target(target: str) -> str:
    normalized_target = normalize_text(target)
    for app_name, aliases in APP_ALIASES.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if _contains_phrase(normalized_target, alias):
                return app_name
    return target.strip()


def _extract_package(text: str) -> str:
    package = _extract_action_target(text, INSTALL_ACTIONS)
    package = re.sub(r"^(?:el\s+)?(?:programa|paquete|aplicacion|app)\s+", "", package)
    package = re.sub(r"\b(?:para|en)\s+(?:mi\s+)?(?:ubuntu|linux|sistema|computadora|pc)\b.*$", "", package)

    source_suffix = re.fullmatch(r"(.+?)\s+(?:con|por|usando|desde)\s+(apt(?:-get)?|snap|flatpak)", package)
    if source_suffix:
        package = f"{source_suffix.group(2)} {source_suffix.group(1)}"

    return re.sub(r"\s+", " ", package).strip(" .,:;!?¿¡\"'")


def route_request(user_text: str) -> RequestRoute:
    """Decide si una solicitud se resuelve localmente o necesita razonamiento de IA."""
    folded_text = _fold_text(user_text).strip()
    text = normalize_text(user_text)
    if not text:
        return RequestRoute(reason="Solicitud vacia.")

    explanation_request = _is_explanation_request(text)
    negated_action = _is_negated_action(text)

    slow_system_phrases = (
        "mi maquina esta lenta", "mi computadora esta lenta", "mi pc esta lenta",
        "mi equipo esta lento", "el sistema esta lento", "ubuntu esta lento",
        "linux esta lento", "todo esta lento", "se traba mi computadora",
        "se congela mi computadora", "por que esta lenta mi computadora",
    )
    if _contains_any(text, slow_system_phrases):
        return _local(
            "DIAGNOSE_PERFORMANCE",
            reason="Diagnostico local de CPU, memoria, disco y procesos.",
        )

    network_problem_phrases = (
        "no tengo internet", "no hay internet", "sin internet", "internet no funciona",
        "no me funciona internet", "no tengo conexion", "sin conexion", "wifi no funciona",
        "no funciona el wifi", "problemas de internet", "problemas de red",
    )
    if _contains_any(text, network_problem_phrases):
        return _local(
            "DIAGNOSE_NETWORK",
            reason="Diagnostico local de interfaces, ruta y conectividad.",
        )

    temperature_terms = (
        "temperatura", "temperaruta", "temepratura", "temp", "calor", "caliente", "grados",
    )
    cpu_terms = ("cpu", "procesador", "microprocesador")
    advice_terms = ("normal", "ideal", "maxima", "bajar", "reducir", "enfriar", "peligrosa")
    if _contains_any(text, temperature_terms) and _contains_any(text, cpu_terms):
        if not explanation_request and not _contains_any(text, advice_terms):
            return _local("CPU_TEMPERATURE", reason="Consulta directa a sensores locales.")

    time_phrases = (
        "que hora", "dime la hora", "hora actual", "que fecha", "dime la fecha",
        "fecha de hoy", "que dia es", "que dia estamos", "dia de hoy",
    )
    if _contains_any(text, time_phrases):
        return _local("TIME_DATE", reason="La fecha y hora estan disponibles localmente.")

    wallpaper_terms = ("fondo de pantalla", "fondo pantalla", "wallpaper", "papel tapiz", "background")
    if _contains_any(text, wallpaper_terms):
        if not explanation_request and not negated_action and _has_action(text, (*OPEN_ACTIONS, *VIEW_ACTIONS, *CHANGE_ACTIONS)):
            return _local("WALLPAPER_SETTINGS", reason="Acceso directo al panel de fondo de pantalla.")

    process_terms = (
        "procesos activos", "aplicaciones activas", "administrador de tareas",
        "monitor del sistema", "lista de procesos", "los procesos", "procesos",
    )
    if _contains_any(text, process_terms):
        if not explanation_request and not negated_action and _has_action(text, (*OPEN_ACTIONS, *VIEW_ACTIONS)):
            return _local("SHOW_PROCESSES", reason="Vista grafica local de procesos.")

    network_terms = (
        "estado de red", "estado red", "direccion ip", "mi ip", "interfaces de red",
        "conexion wifi", "red wifi", "conectividad", "ver red", "ver la red",
        "mostrar red", "mostrar la red", "revisar red", "revisar la red", "ip a",
        "ver conexion", "mostrar conexion",
    )
    direct_network_query = _contains_any(text, ("mi ip", "direccion ip"))
    if _contains_any(text, network_terms) or (_contains_phrase(text, "wifi") and _has_action(text, (*OPEN_ACTIONS, *VIEW_ACTIONS))):
        if not explanation_request and not negated_action and (direct_network_query or _has_action(text, (*OPEN_ACTIONS, *VIEW_ACTIONS))):
            return _local("SHOW_NETWORK", reason="Vista grafica local del estado de red.")

    update_phrases = (
        "actualizar sistema", "actualiza el sistema", "actualiza mi sistema", "actualizar ubuntu",
        "actualiza ubuntu", "apt update", "instala las actualizaciones", "buscar actualizaciones",
        "busca actualizaciones", "revisar actualizaciones", "revisa las actualizaciones",
        "hay actualizaciones", "actualisar sistema", "actualisa el sistema", "actualisar ubuntu",
    )
    if _contains_any(text, update_phrases) and not explanation_request and not negated_action:
        return _local("UPDATE_SYSTEM", reason="Actualizacion mediante la vista local con confirmacion.")

    if _has_action(text, INSTALL_ACTIONS) and not explanation_request and not negated_action:
        deb_match = re.search(r"([^\s\"']+\.deb)\b", user_text, flags=re.IGNORECASE)
        mentions_deb = deb_match or _contains_any(text, ("archivo deb", "paquete deb", "un deb"))
        if mentions_deb:
            deb_path = deb_match.group(1) if deb_match and deb_match.group(1) != ".deb" else None
            return _local("INSTALL_DEB", deb_path, "Instalador visual de paquetes Debian con confirmacion.")
        package = _extract_package(folded_text)
        if package:
            return _local("INSTALL_PACKAGE", package, "Instalador visual local con confirmacion.")

    store_terms = (
        "tienda de aplicaciones", "tienda de apps", "centro de software", "software center",
        "snap store", "tienda", "tiemda",
    )
    if _contains_any(text, store_terms):
        if not explanation_request and not negated_action and _has_action(text, (*OPEN_ACTIONS, *VIEW_ACTIONS)):
            return _local("OPEN_STORE", reason="Apertura directa de la tienda instalada.")

    status_subjects = (
        "estado del sistema", "estado sistema", "recursos", "memoria ram", "memoria", "ram", "disco",
        "espacio libre", "uso del sistema", "uso de cpu", "cpu",
    )
    status_queries = (
        "estado", "mostrar", "muestra", "muestrame", "ver", "dime", "cuanto", "cuanta",
        "revisa", "revisar", "uso", "usada", "usado", "libre", "disponible", "tengo", "queda",
    )
    status_advice = ("liberar", "aumentar", "ampliar", "mejorar", "optimizar", "reparar")
    if _contains_any(text, status_subjects) and _contains_any(text, status_queries):
        if not explanation_request and not _contains_any(text, status_advice):
            return _local("SYSTEM_STATUS", reason="Lectura local de recursos del sistema.")

    if _has_action(text, OPEN_ACTIONS) and not explanation_request and not negated_action:
        target = _extract_action_target(folded_text, OPEN_ACTIONS)
        if target:
            installed_reference = (
                "la aplicacion que instalaste", "la aplicacion instalada", "lo que instalaste",
                "ultima aplicacion", "ultimo programa instalado",
            )
            normalized_target = normalize_text(target)
            if _contains_any(normalized_target, installed_reference):
                return _local("OPEN_APP", normalized_target, "Referencia a la ultima aplicacion instalada.")
            if not re.match(r"^(?:https?://|www\.)", target):
                return _local("OPEN_APP", _resolve_app_target(target), "Apertura directa de una aplicacion local.")

    return RequestRoute(reason="La solicitud necesita contexto, explicacion o razonamiento.")

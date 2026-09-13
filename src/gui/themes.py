"""Sistema de temas Liquid Glass para LinuxMate AI.

Permite alternar en tiempo real entre múltiples paletas inspiradas en estética
Glassmorphism de alta definición con rebordes especulares y acentos neón.
"""

import json
import os
from typing import Dict

CONFIG_FILE = os.path.expanduser("~/.config/linuxmate/theme.json")

# ─── DEFINICIÓN DE PALETAS DE TEMAS ──────────────────────────────────────────

THEMES: Dict[str, Dict[str, str]] = {
    "Liquid Violet": {
        "name": "Liquid Violet",
        "bg_base": "#080510",
        "bg_sidebar": "#140720",
        "bg_panel": "#10091c",
        "bg_card": "#201a32",
        "bg_card_hover": "#2b2240",
        "border": "#3f315a",
        "border_hover": "#7b2cbf",
        "border_focus": "#c084fc",
        "glass_shine": "#8b5cf6",
        "glass_pill": "#2d263f",
        "glass_pill_border": "#5e467f",
        "accent": "#9d4edd",
        "accent_light": "#c084fc",
        "accent_dark": "#7b2cbf",
        "text_main": "#f1f5f9",
        "text_muted": "#9aa4bc",
        "success": "#10b981",
        "success_bg": "#0b3a32",
        "yellow": "#f59e0b",
        "yellow_d": "#352309",
        "red": "#ef4444",
        "red_d": "#351212",
        "input_bg": "#100a1a",
        "code_bg": "#0b0712",
        "code_border": "#3f315a",
    },
    "Cyberpunk Neon": {
        "name": "Cyberpunk Neon",
        "bg_base": "#050510",
        "bg_sidebar": "#090a1c",
        "bg_panel": "#0e1128",
        "bg_card": "#131838",
        "bg_card_hover": "#1c2352",
        "border": "#f72585",
        "border_hover": "#4cc9f0",
        "border_focus": "#7209b7",
        "glass_shine": "#4cc9f0",
        "glass_pill": "#1f1847",
        "glass_pill_border": "#f72585",
        "accent": "#f72585",
        "accent_light": "#4cc9f0",
        "accent_dark": "#7209b7",
        "text_main": "#ffffff",
        "text_muted": "#818cf8",
        "success": "#06d6a0",
        "success_bg": "#0b2b24",
        "yellow": "#ffd166",
        "yellow_d": "#3d3215",
        "red": "#ef476f",
        "red_d": "#3b121c",
        "input_bg": "#0a0b1f",
        "code_bg": "#050614",
        "code_border": "#4338ca",
    },
    "Emerald Matrix": {
        "name": "Emerald Matrix",
        "bg_base": "#030c07",
        "bg_sidebar": "#06160d",
        "bg_panel": "#0a1f14",
        "bg_card": "#0f2e1e",
        "bg_card_hover": "#16452c",
        "border": "#059669",
        "border_hover": "#10b981",
        "border_focus": "#34d399",
        "glass_shine": "#34d399",
        "glass_pill": "#113824",
        "glass_pill_border": "#10b981",
        "accent": "#10b981",
        "accent_light": "#34d399",
        "accent_dark": "#047857",
        "text_main": "#f0fdf4",
        "text_muted": "#6ee7b7",
        "success": "#10b981",
        "success_bg": "#064e3b",
        "yellow": "#f59e0b",
        "yellow_d": "#352309",
        "red": "#ef4444",
        "red_d": "#351212",
        "input_bg": "#071c11",
        "code_bg": "#020d07",
        "code_border": "#065f46",
    },
    "Midnight Ocean": {
        "name": "Midnight Ocean",
        "bg_base": "#020b14",
        "bg_sidebar": "#041424",
        "bg_panel": "#071e36",
        "bg_card": "#0c2847",
        "bg_card_hover": "#133863",
        "border": "#0284c7",
        "border_hover": "#38bdf8",
        "border_focus": "#7dd3fc",
        "glass_shine": "#38bdf8",
        "glass_pill": "#0e345b",
        "glass_pill_border": "#0284c7",
        "accent": "#0284c7",
        "accent_light": "#38bdf8",
        "accent_dark": "#0369a1",
        "text_main": "#f0f9ff",
        "text_muted": "#7dd3fc",
        "success": "#10b981",
        "success_bg": "#064e3b",
        "yellow": "#f59e0b",
        "yellow_d": "#352309",
        "red": "#f43f5e",
        "red_d": "#3b0d18",
        "input_bg": "#05182c",
        "code_bg": "#020f1c",
        "code_border": "#075985",
    },
    "Obsidian Amber": {
        "name": "Obsidian Amber",
        "bg_base": "#0c0702",
        "bg_sidebar": "#170d05",
        "bg_panel": "#211409",
        "bg_card": "#2d1a0c",
        "bg_card_hover": "#3f2512",
        "border": "#d97706",
        "border_hover": "#f59e0b",
        "border_focus": "#fbbf24",
        "glass_shine": "#fbbf24",
        "glass_pill": "#38200d",
        "glass_pill_border": "#d97706",
        "accent": "#f59e0b",
        "accent_light": "#fbbf24",
        "accent_dark": "#b45309",
        "text_main": "#fffbeb",
        "text_muted": "#fcd34d",
        "success": "#10b981",
        "success_bg": "#143323",
        "yellow": "#f59e0b",
        "yellow_d": "#38200d",
        "red": "#ef4444",
        "red_d": "#351212",
        "input_bg": "#1a0f07",
        "code_bg": "#0e0803",
        "code_border": "#92400e",
    },
}

DEFAULT_THEME = "Liquid Violet"


def get_available_themes() -> list[str]:
    """Retorna la lista de nombres de temas disponibles."""
    return list(THEMES.keys())


def load_theme_name() -> str:
    """Carga el nombre del tema guardado por el usuario, o el predeterminado."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                theme = data.get("theme")
                if theme in THEMES:
                    return theme
    except Exception:
        pass
    return DEFAULT_THEME


def save_theme_name(theme_name: str) -> None:
    """Guarda el tema elegido por el usuario."""
    if theme_name not in THEMES:
        return
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"theme": theme_name}, f, indent=2)
    except Exception:
        pass


def get_theme(theme_name: str = None) -> Dict[str, str]:
    """Obtiene el diccionario de colores para un tema dado o el guardado."""
    if not theme_name:
        theme_name = load_theme_name()
    return THEMES.get(theme_name, THEMES[DEFAULT_THEME])

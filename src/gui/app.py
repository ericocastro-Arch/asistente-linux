"""Interfaz gráfica rediseñada del Agente Autónomo para Linux — Diseño moderno e intuitivo."""

import os
import platform
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime
from tkinter import END
from typing import Any, Optional

import customtkinter as ctk
import psutil

from src.core.agent import create_agent
from src.core.llm import format_llm_error
from src.core.memory import clear_memory, get_memory_count
from src.core.storage import close_session, init_db, log_message, log_system_snapshot, start_session
from src.gui import themes, visual_views
from src.nlp.processor import NLPProcessor
from src.nlp.router import RequestRoute
from src.voice.stt import STTEngine
from src.voice.tts import TTSEngine

# ─── Paleta LinuxMate AI — Motor de Temas Liquid Glass ──────────────────────
_cur_theme_name = themes.load_theme_name()
_t = themes.get_theme(_cur_theme_name)

C_BG_BASE       = _t["bg_base"]
C_BG_SIDEBAR    = _t["bg_sidebar"]
C_BG_PANEL      = _t["bg_panel"]
C_BG_CARD       = _t["bg_card"]
C_BG_CARD_HOVER = _t["bg_card_hover"]
C_BORDER        = _t["border"]
C_BORDER_HOVER  = _t["border_hover"]
C_BORDER_FOCUS  = _t["border_focus"]
C_GLASS_SHINE   = _t["glass_shine"]
C_GLASS_PILL    = _t["glass_pill"]
C_GLASS_PILL_BORDER = _t["glass_pill_border"]
C_ACCENT        = _t["accent"]
C_ACCENT_LIGHT  = _t["accent_light"]
C_ACCENT_DARK   = _t["accent_dark"]
C_TEXT_MAIN     = _t["text_main"]
C_TEXT_MUTED    = _t["text_muted"]
C_SUCCESS       = _t["success"]
C_SUCCESS_BG    = _t["success_bg"]
C_YELLOW        = _t["yellow"]
C_YELLOW_D      = _t["yellow_d"]
C_RED           = _t["red"]
C_RED_D         = _t["red_d"]
C_INPUT_BG      = _t["input_bg"]
C_CODE_BG       = _t["code_bg"]
C_CODE_BORDER   = _t["code_border"]

# Alias de compatibilidad
C_BG          = C_BG_BASE
C_SIDEBAR     = C_BG_SIDEBAR
C_SIDEBAR_ACT = C_BG_CARD
C_PANEL       = C_BG_PANEL
C_CARD        = C_BG_CARD
C_CARD_HOVER  = C_BG_CARD_HOVER
C_ORANGE      = C_ACCENT
C_ORANGE_H    = C_ACCENT_LIGHT
C_ORANGE_D    = C_GLASS_PILL
C_GREEN       = C_SUCCESS
C_GREEN_D     = C_SUCCESS_BG
C_BLUE        = C_ACCENT_LIGHT
C_BLUE_D      = C_GLASS_PILL
C_BLUE_BORDER = C_BORDER_HOVER
C_TEXT        = C_TEXT_MAIN
C_MUTED       = C_TEXT_MUTED
C_MUTED2      = "#9d8bb8"
C_PURPLE      = C_ACCENT
C_PURPLE_D    = C_GLASS_PILL


def update_global_colors(t: dict) -> None:
    """Actualiza todas las variables globales de color al cambiar de tema."""
    global C_BG_BASE, C_BG_SIDEBAR, C_BG_PANEL, C_BG_CARD, C_BG_CARD_HOVER
    global C_BORDER, C_BORDER_HOVER, C_BORDER_FOCUS, C_GLASS_SHINE, C_GLASS_PILL
    global C_GLASS_PILL_BORDER, C_ACCENT, C_ACCENT_LIGHT, C_ACCENT_DARK
    global C_TEXT_MAIN, C_TEXT_MUTED, C_SUCCESS, C_SUCCESS_BG, C_YELLOW, C_YELLOW_D
    global C_RED, C_RED_D, C_INPUT_BG, C_CODE_BG, C_CODE_BORDER
    global C_BG, C_SIDEBAR, C_SIDEBAR_ACT, C_PANEL, C_CARD, C_CARD_HOVER
    global C_ORANGE, C_ORANGE_H, C_ORANGE_D, C_GREEN, C_GREEN_D, C_BLUE, C_BLUE_D, C_BLUE_BORDER, C_TEXT, C_MUTED, C_PURPLE, C_PURPLE_D

    C_BG_BASE       = t["bg_base"]
    C_BG_SIDEBAR    = t["bg_sidebar"]
    C_BG_PANEL      = t["bg_panel"]
    C_BG_CARD       = t["bg_card"]
    C_BG_CARD_HOVER = t["bg_card_hover"]
    C_BORDER        = t["border"]
    C_BORDER_HOVER  = t["border_hover"]
    C_BORDER_FOCUS  = t["border_focus"]
    C_GLASS_SHINE   = t["glass_shine"]
    C_GLASS_PILL    = t["glass_pill"]
    C_GLASS_PILL_BORDER = t["glass_pill_border"]
    C_ACCENT        = t["accent"]
    C_ACCENT_LIGHT  = t["accent_light"]
    C_ACCENT_DARK   = t["accent_dark"]
    C_TEXT_MAIN     = t["text_main"]
    C_TEXT_MUTED    = t["text_muted"]
    C_SUCCESS       = t["success"]
    C_SUCCESS_BG    = t["success_bg"]
    C_YELLOW        = t["yellow"]
    C_YELLOW_D      = t["yellow_d"]
    C_RED           = t["red"]
    C_RED_D         = t["red_d"]
    C_INPUT_BG      = t["input_bg"]
    C_CODE_BG       = t["code_bg"]
    C_CODE_BORDER   = t["code_border"]

    C_BG          = C_BG_BASE
    C_SIDEBAR     = C_BG_SIDEBAR
    C_SIDEBAR_ACT = C_BG_CARD
    C_PANEL       = C_BG_PANEL
    C_CARD        = C_BG_CARD
    C_CARD_HOVER  = C_BG_CARD_HOVER
    C_ORANGE      = C_ACCENT
    C_ORANGE_H    = C_ACCENT_LIGHT
    C_ORANGE_D    = C_GLASS_PILL
    C_GREEN       = C_SUCCESS
    C_GREEN_D     = C_SUCCESS_BG
    C_BLUE        = C_ACCENT_LIGHT
    C_BLUE_D      = C_GLASS_PILL
    C_BLUE_BORDER = C_BORDER_HOVER
    C_TEXT        = C_TEXT_MAIN
    C_MUTED       = C_TEXT_MUTED
    C_PURPLE      = C_ACCENT
    C_PURPLE_D    = C_GLASS_PILL


def _format_bytes(value: float) -> str:
    """Convierte bytes a una unidad amigable para la interfaz."""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size:.0f} {unit}"
        size /= 1024


def _get_system_stats() -> dict:
    """Recoge métricas del sistema en tiempo real."""
    try:
        cpu    = psutil.cpu_percent(interval=0.1)
        mem    = psutil.virtual_memory()
        disk   = psutil.disk_usage("/")
        net    = psutil.net_io_counters()
        boot   = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot
        h, r   = divmod(int(uptime.total_seconds()), 3600)
        m      = r // 60
        uname  = platform.uname()
        try:
            pkgs = int(subprocess.check_output(
                ["dpkg", "--get-selections"], stderr=subprocess.DEVNULL
            ).decode().count("\n"))
        except Exception:
            pkgs = 0

        return {
            "cpu":     cpu,
            "mem_gb":  mem.used / 1e9,
            "mem_tot": mem.total / 1e9,
            "mem_pct": mem.percent,
            "disk_gb": disk.used / 1e9,
            "disk_tot": disk.total / 1e9,
            "disk_pct": disk.percent,
            "uptime":  f"{h}h {m:02d}m",
            "procs":   len(psutil.pids()),
            "net_rx":  net.bytes_recv / 1e6,
            "kernel":  uname.release,
            "gnome":   uname.version[:7] if uname.version else "—",
            "pkgs":    pkgs,
        }
    except Exception:
        return {}


class SidebarNavButton(ctk.CTkButton):
    """Botón de navegación elegante con estilo Liquid Glass para la barra lateral."""

    def __init__(self, parent, icon: str, text: str, command=None, active: bool = False):
        bg_color = C_BG_CARD if active else "transparent"
        text_color = C_ACCENT_LIGHT if active else C_TEXT_MUTED
        hover_color = C_BG_CARD_HOVER
        border_width = 1 if active else 0
        border_color = C_BORDER_HOVER if active else C_BORDER
        super().__init__(
            parent,
            text=f" {icon}  {text}",
            anchor="w",
            height=32,
            font=ctk.CTkFont(size=11, weight="bold" if active else "normal"),
            fg_color=bg_color,
            hover_color=hover_color,
            text_color=text_color,
            border_width=border_width,
            border_color=border_color,
            corner_radius=8,
            command=command,
        )


SidebarIcon = SidebarNavButton  # compatibilidad con llamadas anteriores


class AssistantApp(ctk.CTk):
    """Ventana principal LinuxMate AI — Liquid Glass Edition."""

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("LinuxMate AI — Liquid Glass Edition")
        self.geometry("1155x600")
        self.minsize(1080, 600)
        self.configure(fg_color=C_BG_BASE)

        self.current_theme = _cur_theme_name
        self.right_col_width = 280
        self._is_chat_expanded = False
        self._chat_history_records = []

        self._update_theme_attributes()
        self._format_bytes = _format_bytes

        # Módulos del backend
        self.agent      = create_agent()
        self.session_id = self.agent.session_id if self.agent else start_session("desktop-gui")
        self.nlp        = NLPProcessor()
        self.tts        = TTSEngine()
        self.stt        = STTEngine()
        self._speaking  = False
        self._listening = False
        self._msg_count = 0
        self._thinking_label: Optional[ctk.CTkLabel] = None
        self._last_snapshot_at = 0.0
        init_db()

        self._build_layout()
        self._start_system_monitor()
        self._show_welcome()

    def _update_theme_attributes(self) -> None:
        """Actualiza atributos de compatibilidad con colores de tema."""
        self.C_BG = C_BG_BASE
        self.C_SIDEBAR = C_BG_SIDEBAR
        self.C_PANEL = C_BG_PANEL
        self.C_CARD = C_BG_CARD
        self.C_CARD_HOVER = C_BG_CARD_HOVER
        self.C_BORDER = C_BORDER
        self.C_BORDER_HOVER = C_BORDER_HOVER
        self.C_INPUT_BG = C_INPUT_BG
        self.C_CODE_BG = C_CODE_BG
        self.C_CODE_BORDER = C_CODE_BORDER
        self.C_ORANGE = C_ACCENT
        self.C_ORANGE_H = C_BORDER_HOVER
        self.C_GREEN = C_SUCCESS
        self.C_GREEN_D = C_SUCCESS_BG
        self.C_YELLOW = C_YELLOW
        self.C_RED = C_RED
        self.C_BLUE = C_ACCENT_LIGHT
        self.C_MUTED = C_TEXT_MUTED
        self.C_MUTED2 = C_MUTED2
        self.C_TEXT = C_TEXT_MAIN
        self.C_PURPLE = C_ACCENT
        self.C_ACCENT = C_ACCENT
        self.C_ACCENT_LIGHT = C_ACCENT_LIGHT
        self.C_ACCENT_DARK = C_ACCENT_DARK

    def change_theme(self, theme_name: str) -> None:
        """Aplica un tema visual seleccionado en tiempo real."""
        themes.save_theme_name(theme_name)
        cur_t = themes.get_theme(theme_name)
        update_global_colors(cur_t)
        self.current_theme = theme_name
        self._update_theme_attributes()

        saved_history = list(self._chat_history_records)

        for w in self.winfo_children():
            w.destroy()

        self.configure(fg_color=C_BG_BASE)
        self._build_layout()

        if saved_history:
            for sender, text, source in saved_history:
                self._add_bubble(sender, text, source)
        else:
            self._show_welcome()

    def _on_window_close(self) -> None:
        self.destroy()

    def _on_window_min(self) -> None:
        self.iconify()

    def _on_window_max(self) -> None:
        try:
            if self.state() == "zoomed":
                self.state("normal")
            else:
                self.state("zoomed")
        except Exception:
            try:
                cur = self.attributes("-zoomed")
                self.attributes("-zoomed", not cur)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # LAYOUT PRINCIPAL (HEADER + 3 COLUMNAS CON SPLITTER AJUSTABLE)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        # Barra superior estilo ventana OS con selector de temas y traffic lights
        self.window_header = ctk.CTkFrame(self, height=34, fg_color="#12091c", corner_radius=0, border_width=1, border_color=C_BORDER)
        self.window_header.pack(side="top", fill="x")
        self.window_header.pack_propagate(False)

        # Reflejo especular superior
        ctk.CTkFrame(self.window_header, height=2, fg_color=C_GLASS_SHINE).pack(side="top", fill="x")

        h_content = ctk.CTkFrame(self.window_header, fg_color="transparent")
        h_content.pack(fill="both", expand=True, padx=18)

        left_title = ctk.CTkFrame(h_content, fg_color="transparent")
        left_title.pack(side="left")
        ctk.CTkLabel(left_title, text="🐧", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(left_title, text="LinuxMate AI — Liquid Glass Edition", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_TEXT_MAIN).pack(side="left")

        right_controls = ctk.CTkFrame(h_content, fg_color="transparent")
        right_controls.pack(side="right")

        ctk.CTkLabel(right_controls, text="Tema", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_MUTED).pack(side="left", padx=(0, 6))
        self.theme_selector = ctk.CTkOptionMenu(
            right_controls,
            values=themes.get_available_themes(),
            command=self.change_theme,
            width=124,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=C_GLASS_PILL,
            button_color=C_BORDER,
            button_hover_color=C_BORDER_HOVER,
            dropdown_fg_color=C_BG_CARD,
            dropdown_text_color=C_TEXT_MAIN,
            dropdown_hover_color=C_BG_CARD_HOVER,
            corner_radius=8,
        )
        self.theme_selector.set(self.current_theme)
        self.theme_selector.pack(side="left", padx=(0, 16))

        dots_box = ctk.CTkFrame(right_controls, fg_color="transparent")
        dots_box.pack(side="left")

        # Botón Minimizar (Amarillo)
        ctk.CTkButton(
            dots_box, text="", width=12, height=12, corner_radius=99,
            fg_color="#ffbd2e", hover_color="#dea123",
            border_width=1, border_color="#dea123",
            command=self._on_window_min
        ).pack(side="left", padx=3)

        # Botón Maximizar (Verde)
        ctk.CTkButton(
            dots_box, text="", width=12, height=12, corner_radius=99,
            fg_color="#27c93f", hover_color="#1aab29",
            border_width=1, border_color="#1aab29",
            command=self._on_window_max
        ).pack(side="left", padx=3)

        # Botón Cerrar (Rojo)
        ctk.CTkButton(
            dots_box, text="", width=12, height=12, corner_radius=99,
            fg_color="#ff5f56", hover_color="#e0443e",
            border_width=1, border_color="#e0443e",
            command=self._on_window_close
        ).pack(side="left", padx=3)

        # Contenedor principal de 3 columnas
        self.body_container = ctk.CTkFrame(self, fg_color=C_BG_BASE, corner_radius=0)
        self.body_container.pack(fill="both", expand=True, padx=14, pady=14)

        # 1. Sidebar izquierda (mockup liquid glass)
        self.sidebar = ctk.CTkFrame(self.body_container, width=200, corner_radius=18, fg_color=C_BG_SIDEBAR, border_width=1, border_color=C_BORDER)
        self.sidebar.pack(side="left", fill="y", padx=(0, 14), pady=0)
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        # 2. Columna derecha: Chat IA + Perfil de Distro (Ancho ajustable)
        self.right_col = ctk.CTkFrame(self.body_container, width=self.right_col_width, corner_radius=18, fg_color=C_BG_SIDEBAR, border_width=1, border_color=C_BORDER)
        self.right_col.pack(side="right", fill="y", padx=(14, 0), pady=0)
        self.right_col.pack_propagate(False)

        # 3. Divisor interactivo / Splitter arrastrable para redimensionar el chat
        self.splitter = ctk.CTkFrame(self.body_container, width=2, fg_color=C_BORDER, cursor="sb_h_double_arrow")
        self.splitter.pack(side="right", fill="y", padx=0, pady=0)
        self.splitter.pack_propagate(False)
        self.splitter.bind("<Button-1>", self._on_splitter_press)
        self.splitter.bind("<B1-Motion>", self._on_splitter_drag)
        self.splitter.bind("<ButtonRelease-1>", self._on_splitter_release)
        self.splitter.bind("<Enter>", lambda e: self.splitter.configure(fg_color=C_BORDER_HOVER))
        self.splitter.bind("<Leave>", lambda e: self.splitter.configure(fg_color=C_BORDER))

        # 4. Columna central expandible: Dashboard principal
        self.center_col = ctk.CTkFrame(self.body_container, fg_color=C_BG_BASE)
        self.center_col.pack(side="left", fill="both", expand=True)
        self._build_center_dashboard()

        # Construir contenido de la columna derecha
        self._build_right_column()

    # ─────────────────────────────────────────────────────────────────────────
    # AJUSTE DINÁMICO DE TAMAÑO DEL CHAT (SPLITTER & CONTROLES)
    # ─────────────────────────────────────────────────────────────────────────

    def _on_splitter_press(self, event) -> None:
        self._drag_start_x = event.x_root
        self._initial_right_width = self.right_col.winfo_width()

    def _on_splitter_drag(self, event) -> None:
        dx = self._drag_start_x - event.x_root
        new_width = max(280, min(850, self._initial_right_width + dx))
        self.right_col_width = new_width
        self.right_col.configure(width=new_width)

    def _on_splitter_release(self, event) -> None:
        pass

    def _toggle_chat_size(self) -> None:
        """Alterna el chat entre tamaño estándar y expandido/amplio."""
        if self._is_chat_expanded:
            self.right_col_width = 280
            self._is_chat_expanded = False
            if hasattr(self, "_chat_resize_btn"):
                self._chat_resize_btn.configure(text="⤢")
        else:
            self.right_col_width = 540
            self._is_chat_expanded = True
            if hasattr(self, "_chat_resize_btn"):
                self._chat_resize_btn.configure(text="⤡")
        self.right_col.configure(width=self.right_col_width)

    # ─────────────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ─────────────────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        # 1. Branding (Logo + Título)
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(16, 10))

        logo_box = ctk.CTkFrame(brand, width=34, height=34, fg_color=C_ACCENT, corner_radius=10, border_width=1.5, border_color=C_BORDER_HOVER)
        logo_box.pack(side="left", padx=(0, 10))
        logo_box.pack_propagate(False)
        ctk.CTkLabel(logo_box, text="🐧", font=ctk.CTkFont(size=17), text_color="#ffffff").pack(expand=True)

        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(brand_text, text="LinuxMate AI", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(brand_text, text="Guía para principiantes", font=ctk.CTkFont(size=9), text_color=C_TEXT_MUTED).pack(anchor="w")

        # 2. Tarjeta Ruta de aprendizaje
        user_card = ctk.CTkFrame(self.sidebar, fg_color=C_CODE_BG, corner_radius=12, border_width=1, border_color=C_BORDER)
        user_card.pack(fill="x", padx=14, pady=(0, 14))

        # Reflejo especular superior
        ctk.CTkFrame(user_card, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=12, pady=(2, 0))

        ctk.CTkLabel(user_card, text="Ruta de aprendizaje", font=ctk.CTkFont(size=9, weight="bold"), text_color=C_TEXT_MUTED).pack(anchor="w", padx=12, pady=(8, 2))

        lvl_row = ctk.CTkFrame(user_card, fg_color="transparent")
        lvl_row.pack(fill="x", padx=12)
        ctk.CTkLabel(lvl_row, text="Nivel básico", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(lvl_row, text="68%", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_ACCENT_LIGHT).pack(side="right")

        prog = ctk.CTkProgressBar(user_card, height=7, corner_radius=99, fg_color=C_BG_BASE, progress_color=C_ACCENT)
        prog.pack(fill="x", padx=12, pady=(6, 12))
        prog.set(0.68)

        # 3. Menú de navegación principal
        ctk.CTkLabel(self.sidebar, text="MENÚ PRINCIPAL", font=ctk.CTkFont(size=9, weight="bold"), text_color="#566078").pack(anchor="w", padx=18, pady=(0, 6))

        nav_items = [
            ("🏠", "Inicio", self._focus_dashboard, True),
            ("💬", "Asistente IA", lambda: self.input_entry.focus(), False),
            ("📦", "Instalar apps", self._show_package_installer, False),
            ("💻", "Terminal guiada", lambda: visual_views.show_terminal_guide(self), False),
            ("🛠️", "Solución de errores", lambda: visual_views.show_troubleshooter(self), False),
            ("🗑️", "Desinstalador", lambda: visual_views.show_package_remover(self), False),
        ]
        self._nav_buttons = []
        for icon, label, cmd, active in nav_items:
            btn = SidebarNavButton(self.sidebar, icon, label, command=cmd, active=active)
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_buttons.append(btn)

        # 4. Footer con consejo de hoy
        tip_card = ctk.CTkFrame(self.sidebar, fg_color=C_BG_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        tip_card.pack(side="bottom", fill="x", padx=14, pady=14)

        ctk.CTkFrame(tip_card, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=12, pady=(2, 0))

        ctk.CTkLabel(tip_card, text="💡 Consejo de hoy", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_MAIN).pack(anchor="w", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            tip_card,
            text="Antes de copiar comandos, LinuxMate te explica qué hace cada instrucción de forma segura para tu sistema.",
            font=ctk.CTkFont(size=9),
            text_color=C_TEXT_MUTED,
            wraplength=150,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def _focus_dashboard(self) -> None:
        try:
            self.center_scroll._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def _clear_search(self) -> None:
        if hasattr(self, "top_search_entry"):
            self.top_search_entry.delete(0, END)

    # ─────────────────────────────────────────────────────────────────────────
    # DASHBOARD CENTRAL (DISEÑO EXACTO LIQUID GLASS EDITION)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_center_dashboard(self) -> None:
        self.center_scroll = ctk.CTkScrollableFrame(self.center_col, fg_color=C_BG_BASE, corner_radius=0)
        self.center_scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # ── 1. HERO BANNER PRINCIPAL (ANCHO COMPLETO) ──
        hero_card = ctk.CTkFrame(self.center_scroll, fg_color=C_BG_CARD, corner_radius=18, border_width=1.5, border_color=C_BORDER)
        hero_card.pack(fill="x", pady=(0, 12))

        ctk.CTkFrame(hero_card, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=16, pady=(2, 0))

        h_wrap = ctk.CTkFrame(hero_card, fg_color="transparent")
        h_wrap.pack(fill="both", expand=True, padx=20, pady=(8, 16))

        # Contenedor izquierdo con textos y acciones
        h_left = ctk.CTkFrame(h_wrap, fg_color="transparent")
        h_left.pack(side="left", fill="both", expand=True)

        badge = ctk.CTkLabel(
            h_left,
            text="✨ Asistente personalizado para Linux",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_ACCENT_LIGHT,
            fg_color=C_GLASS_PILL,
            corner_radius=99,
            padx=12,
            pady=3,
        )
        badge.pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            h_left,
            text="Aprende Linux sin miedo, paso a paso.",
            font=ctk.CTkFont(size=21, weight="bold"),
            text_color=C_TEXT_MAIN,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        ctk.CTkLabel(
            h_left,
            text="Una interfaz pensada para usuarios nuevos: explica comandos, recomienda aplicaciones, detecta problemas comunes y guía la configuración inicial de Ubuntu y distribuciones Linux.",
            font=ctk.CTkFont(size=11),
            text_color=C_TEXT_MUTED,
            wraplength=620,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        h_actions = ctk.CTkFrame(h_left, fg_color="transparent")
        h_actions.pack(anchor="w")

        ctk.CTkButton(
            h_actions,
            text="🚀 Empezar diagnóstico",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=C_ACCENT,
            hover_color=C_BORDER_HOVER,
            text_color="#ffffff",
            border_width=1,
            border_color=C_BORDER_HOVER,
            corner_radius=10,
            height=30,
            command=lambda: visual_views.show_troubleshooter(self),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            h_actions,
            text="📖 Ver guía inicial",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=C_GLASS_PILL,
            hover_color=C_BG_CARD_HOVER,
            text_color=C_TEXT_MAIN,
            border_width=1.5,
            border_color=C_GLASS_PILL_BORDER,
            corner_radius=10,
            height=30,
            command=lambda: visual_views.show_terminal_guide(self),
        ).pack(side="left")

        # Silueta pingüino decorativa a la derecha (watermark estilo mockup)
        ctk.CTkLabel(
            h_wrap,
            text="🐧",
            font=ctk.CTkFont(size=68),
            text_color=C_GLASS_PILL,
        ).pack(side="right", padx=16)

        # ── 2. ESTADO DEL SISTEMA (3 TARJETAS HORIZONTALES) ──
        status_sec = ctk.CTkFrame(self.center_scroll, fg_color="transparent")
        status_sec.pack(fill="x", pady=(0, 10))

        s_head = ctk.CTkFrame(status_sec, fg_color="transparent")
        s_head.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(s_head, text="Estado del sistema", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(
            s_head,
            text="🛡️ Seguro",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_SUCCESS,
            fg_color=C_SUCCESS_BG,
            corner_radius=99,
            padx=10,
            pady=3,
        ).pack(side="right")

        status_grid = ctk.CTkFrame(status_sec, fg_color="transparent")
        status_grid.pack(fill="x")
        status_grid.columnconfigure(0, weight=1, uniform="stat")
        status_grid.columnconfigure(1, weight=1, uniform="stat")
        status_grid.columnconfigure(2, weight=1, uniform="stat")

        # 1. RAM
        ram_c = ctk.CTkFrame(status_grid, fg_color=C_BG_CARD, corner_radius=14, border_width=1.5, border_color=C_BORDER)
        ram_c.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkFrame(ram_c, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=8, pady=(2, 0))
        r_inner = ctk.CTkFrame(ram_c, fg_color="transparent")
        r_inner.pack(fill="both", expand=True, padx=12, pady=10)
        ctk.CTkLabel(r_inner, text="🧠 Memoria RAM", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_MUTED).pack(anchor="w")
        self._hero_mem_lbl = ctk.CTkLabel(r_inner, text="42%", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_ACCENT_LIGHT)
        self._hero_mem_lbl.pack(anchor="w", pady=(3, 5))
        self._hero_mem_bar = ctk.CTkProgressBar(r_inner, height=5, corner_radius=99, fg_color=C_BG_BASE, progress_color=C_ACCENT_LIGHT)
        self._hero_mem_bar.pack(fill="x")
        self._hero_mem_bar.set(0.42)

        # 2. CPU
        cpu_c = ctk.CTkFrame(status_grid, fg_color=C_BG_CARD, corner_radius=14, border_width=1.5, border_color=C_BORDER)
        cpu_c.grid(row=0, column=1, padx=6, sticky="nsew")
        ctk.CTkFrame(cpu_c, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=8, pady=(2, 0))
        c_inner = ctk.CTkFrame(cpu_c, fg_color="transparent")
        c_inner.pack(fill="both", expand=True, padx=12, pady=10)
        ctk.CTkLabel(c_inner, text="⚡ Uso de CPU", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_MUTED).pack(anchor="w")
        self._hero_cpu_lbl = ctk.CTkLabel(c_inner, text="18%", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_YELLOW)
        self._hero_cpu_lbl.pack(anchor="w", pady=(4, 6))
        self._hero_cpu_bar = ctk.CTkProgressBar(c_inner, height=5, corner_radius=99, fg_color=C_BG_BASE, progress_color=C_YELLOW)
        self._hero_cpu_bar.pack(fill="x")
        self._hero_cpu_bar.set(0.18)

        # 3. Actualizaciones
        upd_c = ctk.CTkFrame(status_grid, fg_color=C_BG_CARD, corner_radius=14, border_width=1.5, border_color=C_BORDER)
        upd_c.grid(row=0, column=2, padx=(6, 0), sticky="nsew")
        ctk.CTkFrame(upd_c, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=8, pady=(2, 0))
        u_inner = ctk.CTkFrame(upd_c, fg_color="transparent")
        u_inner.pack(fill="both", expand=True, padx=12, pady=10)
        ctk.CTkLabel(u_inner, text="🔄 Actualizaciones", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_MUTED).pack(anchor="w")
        self._hero_pkgs_lbl = ctk.CTkLabel(u_inner, text="Al día ✓", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_SUCCESS)
        self._hero_pkgs_lbl.pack(anchor="w", pady=(4, 6))
        self._hero_pkgs_bar = ctk.CTkProgressBar(u_inner, height=5, corner_radius=99, fg_color=C_BG_BASE, progress_color=C_SUCCESS)
        self._hero_pkgs_bar.pack(fill="x")
        self._hero_pkgs_bar.set(1.0)

        # ── 3. ACCIONES RÁPIDAS RECOMENDADAS (GRID 2x2 PRINCIPAL) ──
        act_sec = ctk.CTkFrame(self.center_scroll, fg_color="transparent")
        act_sec.pack(fill="x", pady=(0, 10))

        act_head = ctk.CTkFrame(act_sec, fg_color="transparent")
        act_head.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(act_head, text="Acciones rápidas recomendadas", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(act_head, text="Diseñadas para usuarios de Windows", font=ctk.CTkFont(size=11), text_color=C_TEXT_MUTED).pack(side="right")

        act_grid = ctk.CTkFrame(act_sec, fg_color="transparent")
        act_grid.pack(fill="x")
        act_grid.columnconfigure(0, weight=1, uniform="act")
        act_grid.columnconfigure(1, weight=1, uniform="act")

        featured_cards = [
            ("🔄", "Actualizar sistema", "Ejecuta actualizaciones con explicación antes de aplicar cambios en el sistema.", "Ejecutar guía →", self._show_update_runner),
            ("📦", "Instalar programas", "Busca apps equivalentes a Windows: Office, navegadores, editores y más.", "Buscar apps →", self._show_package_installer),
            ("🧹", "Limpiar paquetes", "Libera espacio removiendo caché, dependencias viejas y paquetes huérfanos.", "Optimizar →", lambda: visual_views.show_system_cleaner(self)),
            ("🌐", "Configurar red", "Ayuda para Wi-Fi, DNS, IP local, puertos, SSH y conectividad.", "Revisar red →", self._show_network_viewer),
        ]

        for i, (icon, title, desc, btn_text, cmd) in enumerate(featured_cards):
            r = i // 2
            c = i % 2
            px = (0, 6) if c == 0 else (6, 0)
            card = ctk.CTkFrame(act_grid, fg_color=C_BG_CARD, corner_radius=14, border_width=1.5, border_color=C_BORDER)
            card.grid(row=r, column=c, padx=px, pady=6, sticky="nsew")

            ctk.CTkFrame(card, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=12, pady=(2, 0))

            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill="both", expand=True, padx=16, pady=12)

            top_row = ctk.CTkFrame(card_inner, fg_color="transparent")
            top_row.pack(fill="x", pady=(0, 6))

            icon_box = ctk.CTkFrame(top_row, width=34, height=34, fg_color=C_GLASS_PILL, corner_radius=10, border_width=1.5, border_color=C_GLASS_PILL_BORDER)
            icon_box.pack(side="left", padx=(0, 10))
            icon_box.pack_propagate(False)
            ctk.CTkLabel(icon_box, text=icon, font=ctk.CTkFont(size=16)).pack(expand=True)

            ctk.CTkLabel(top_row, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT_MAIN).pack(side="left")

            ctk.CTkLabel(
                card_inner,
                text=desc,
                font=ctk.CTkFont(size=11),
                text_color=C_TEXT_MUTED,
                wraplength=260,
                justify="left",
            ).pack(anchor="w", pady=(0, 12))

            ctk.CTkButton(
                card_inner,
                text=btn_text,
                height=30,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=C_GLASS_PILL,
                hover_color=C_BG_CARD_HOVER,
                text_color=C_TEXT_MAIN,
                border_width=1.5,
                border_color=C_GLASS_PILL_BORDER,
                corner_radius=10,
                command=cmd,
            ).pack(fill="x")

        # ── 5. MÁS HERRAMIENTAS DEL SISTEMA (ACCESOS RÁPIDOS COMPLETOS) ──
        extra_sec = ctk.CTkFrame(self.center_scroll, fg_color="transparent")
        extra_sec.pack(fill="x", pady=(0, 18))

        e_head = ctk.CTkFrame(extra_sec, fg_color="transparent")
        e_head.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(e_head, text="Más herramientas del sistema", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(e_head, text="Accesos rápidos avanzados", font=ctk.CTkFont(size=11), text_color=C_TEXT_MUTED).pack(side="right")

        e_grid = ctk.CTkFrame(extra_sec, fg_color="transparent")
        e_grid.pack(fill="x")
        e_grid.columnconfigure(0, weight=1, uniform="eact")
        e_grid.columnconfigure(1, weight=1, uniform="eact")

        extra_cards = [
            ("🎮", "Gaming en Linux", "Configura Steam, Proton, Lutris, Wine y optimizaciones para juegos.", "Configurar gaming →", lambda: visual_views.show_gaming_hub(self)),
            ("💻", "Terminal guiada", "Aprende comandos Linux con ayuda interactiva y validación de seguridad.", "Abrir terminal →", lambda: visual_views.show_terminal_guide(self)),
            ("⚙️", "Controladores y Drivers", "Detecta e instala drivers para tarjetas gráficas, Wi-Fi y periféricos.", "Revisar drivers →", lambda: visual_views.show_drivers_manager(self)),
            ("🛡️", "Copia de seguridad", "Crea instantáneas del sistema con Timeshift para restaurar tu equipo.", "Abrir Timeshift →", lambda: visual_views.show_package_installer(self, "timeshift")),
            ("🩺", "Solución de problemas", "Diagnóstico guiado para audio, pantalla, repositorios y conexión.", "Diagnosticar →", lambda: visual_views.show_troubleshooter(self)),
            ("🎨", "Personalizar apariencia", "Cambia fondos, extensiones de escritorio, temas del sistema y tipografías.", "Personalizar →", lambda: visual_views.show_appearance_manager(self)),
        ]

        for i, (icon, title, desc, btn_text, cmd) in enumerate(extra_cards):
            r = i // 2
            c = i % 2
            px = (0, 6) if c == 0 else (6, 0)
            card = ctk.CTkFrame(e_grid, fg_color=C_BG_CARD, corner_radius=14, border_width=1.5, border_color=C_BORDER)
            card.grid(row=r, column=c, padx=px, pady=6, sticky="nsew")

            ctk.CTkFrame(card, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=12, pady=(2, 0))

            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill="both", expand=True, padx=16, pady=12)

            top_row = ctk.CTkFrame(card_inner, fg_color="transparent")
            top_row.pack(fill="x", pady=(0, 6))

            icon_box = ctk.CTkFrame(top_row, width=34, height=34, fg_color=C_GLASS_PILL, corner_radius=10, border_width=1.5, border_color=C_GLASS_PILL_BORDER)
            icon_box.pack(side="left", padx=(0, 10))
            icon_box.pack_propagate(False)
            ctk.CTkLabel(icon_box, text=icon, font=ctk.CTkFont(size=16)).pack(expand=True)

            ctk.CTkLabel(top_row, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT_MAIN).pack(side="left")

            ctk.CTkLabel(
                card_inner,
                text=desc,
                font=ctk.CTkFont(size=11),
                text_color=C_TEXT_MUTED,
                wraplength=260,
                justify="left",
            ).pack(anchor="w", pady=(0, 12))

            ctk.CTkButton(
                card_inner,
                text=btn_text,
                height=30,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=C_GLASS_PILL,
                hover_color=C_BG_CARD_HOVER,
                text_color=C_TEXT_MAIN,
                border_width=1.5,
                border_color=C_GLASS_PILL_BORDER,
                corner_radius=10,
                command=cmd,
            ).pack(fill="x")

        # ── 6. SECCIÓN INFERIOR: ROADMAP & TERMINAL EXPLICADA ──
        bottom_grid = ctk.CTkFrame(self.center_scroll, fg_color="transparent")
        bottom_grid.pack(fill="x", pady=(0, 16))
        bottom_grid.columnconfigure(0, weight=1, uniform="bottom")
        bottom_grid.columnconfigure(1, weight=1, uniform="bottom")

        # Roadmap
        roadmap_card = ctk.CTkFrame(bottom_grid, fg_color=C_BG_CARD, corner_radius=16, border_width=1.5, border_color=C_BORDER)
        roadmap_card.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkFrame(roadmap_card, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=16, pady=(2, 0))

        rm_inner = ctk.CTkFrame(roadmap_card, fg_color="transparent")
        rm_inner.pack(fill="both", expand=True, padx=16, pady=(10, 14))

        ctk.CTkLabel(rm_inner, text="Ruta para nuevos usuarios", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(rm_inner, text="Flujo recomendado de aprendizaje", font=ctk.CTkFont(size=10), text_color=C_TEXT_MUTED).pack(anchor="w", pady=(0, 8))

        steps = [
            ("1", "Conoce tu distribución", "Identifica si usas Ubuntu, Mint o Debian y qué gestor de paquetes corresponde."),
            ("2", "Aprende comandos esenciales", "Practica cd, ls, pwd, sudo, apt y systemctl sin riesgo."),
            ("3", "Configura tu entorno", "Instala herramientas, activa drivers y deja el sistema listo para trabajar."),
        ]
        for num, stitle, sdesc in steps:
            s_row = ctk.CTkFrame(rm_inner, fg_color=C_GLASS_PILL, corner_radius=10, border_width=1, border_color=C_GLASS_PILL_BORDER)
            s_row.pack(fill="x", pady=3)

            s_num = ctk.CTkFrame(s_row, width=26, height=26, fg_color=C_ACCENT_DARK, corner_radius=8)
            s_num.pack(side="left", padx=8, pady=6)
            s_num.pack_propagate(False)
            ctk.CTkLabel(s_num, text=num, font=ctk.CTkFont(size=11, weight="bold"), text_color="#ffffff").pack(expand=True)

            s_text = ctk.CTkFrame(s_row, fg_color="transparent")
            s_text.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=4)
            ctk.CTkLabel(s_text, text=stitle, font=ctk.CTkFont(size=11, weight="bold"), text_color=C_TEXT_MAIN).pack(anchor="w")
            ctk.CTkLabel(s_text, text=sdesc, font=ctk.CTkFont(size=10), text_color=C_TEXT_MUTED, wraplength=210, justify="left").pack(anchor="w")

        # Terminal Explicada
        term_card = ctk.CTkFrame(bottom_grid, fg_color=C_CODE_BG, corner_radius=16, border_width=1.5, border_color=C_BORDER)
        term_card.grid(row=0, column=1, padx=(6, 0), sticky="nsew")
        ctk.CTkFrame(term_card, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=16, pady=(2, 0))

        t_inner = ctk.CTkFrame(term_card, fg_color="transparent")
        t_inner.pack(fill="both", expand=True, padx=16, pady=(10, 14))

        t_top = ctk.CTkFrame(t_inner, fg_color="transparent")
        t_top.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(t_top, text="● ● ●", font=ctk.CTkFont(size=11), text_color="#ff5f57").pack(side="left")
        ctk.CTkLabel(t_top, text="Comando explicado", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_ACCENT_LIGHT).pack(side="right")

        t_body = ctk.CTkFrame(t_inner, fg_color="transparent")
        t_body.pack(fill="both", expand=True)

        lines = [
            ("erick@linux:~$ sudo apt update", C_ACCENT_LIGHT, True),
            ("# LinuxMate AI:", C_TEXT_MUTED, False),
            ("✓ Actualiza la lista de paquetes disponibles sin instalar nada.", C_SUCCESS, False),
            ("✓ Es seguro ejecutarlo antes de actualizar el sistema.", C_SUCCESS, False),
            ("erick@linux:~$ sudo apt upgrade", C_TEXT_MAIN, True),
        ]
        for line, col, is_cmd in lines:
            font = ctk.CTkFont(family="Courier", size=10, weight="bold" if is_cmd else "normal")
            ctk.CTkLabel(t_body, text=line, font=font, text_color=col, justify="left").pack(anchor="w", pady=1)

        ctk.CTkButton(
            t_inner,
            text="▶ Probar comando en terminal",
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=C_GLASS_PILL,
            hover_color=C_BG_CARD_HOVER,
            text_color=C_TEXT_MAIN,
            border_width=1.5,
            border_color=C_GLASS_PILL_BORDER,
            corner_radius=99,
            command=lambda: visual_views.show_terminal_guide(self),
        ).pack(anchor="w", pady=(8, 0))

    def _on_top_search(self) -> None:
        if not hasattr(self, "top_search_entry"):
            self.input_entry.focus()
            return
        query = self.top_search_entry.get().strip()
        if not query:
            return
        self.top_search_entry.delete(0, END)
        self._send_text(query)

    # ─────────────────────────────────────────────────────────────────────────
    # COLUMNA DERECHA (CHAT ASISTENTE + PERFIL DE DISTRO Y APPS)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_right_column(self) -> None:
        # Contenedor del Chat estilo Glass Card
        chat_container = ctk.CTkFrame(self.right_col, fg_color=C_CODE_BG, corner_radius=14, border_width=1, border_color=C_BORDER)
        chat_container.pack(fill="both", expand=True, padx=12, pady=(16, 8))

        ctk.CTkFrame(chat_container, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=12, pady=(2, 0))

        # Header del chat
        chat_head = ctk.CTkFrame(chat_container, height=42, fg_color="transparent")
        chat_head.pack(fill="x", padx=10, pady=(6, 2))
        chat_head.pack_propagate(False)

        avatar = ctk.CTkFrame(chat_head, width=30, height=30, fg_color=C_ACCENT, corner_radius=9, border_width=1, border_color=C_BORDER_HOVER)
        avatar.pack(side="left", padx=(0, 8))
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text="🤖", font=ctk.CTkFont(size=14)).pack(expand=True)

        info = ctk.CTkFrame(chat_head, fg_color="transparent")
        info.pack(side="left", fill="y", expand=True)
        ctk.CTkLabel(info, text="LinuxMate Assistant", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(info, text="Activo · lenguaje simple", font=ctk.CTkFont(size=8), text_color=C_TEXT_MUTED).pack(anchor="w")

        # Botón para redimensionar/expandir el chat
        self._chat_resize_btn = ctk.CTkButton(
            chat_head,
            text="⤢",
            width=24,
            height=22,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=C_GLASS_PILL,
            hover_color=C_BG_CARD_HOVER,
            text_color=C_TEXT_MAIN,
            border_width=1,
            border_color=C_GLASS_PILL_BORDER,
            corner_radius=6,
            command=self._toggle_chat_size,
        )
        self._chat_resize_btn.pack(side="right", padx=(6, 0))

        self.status_dot = ctk.CTkLabel(
            chat_head,
            text="● En línea",
            font=ctk.CTkFont(size=8, weight="bold"),
            text_color=C_SUCCESS,
            fg_color=C_SUCCESS_BG,
            corner_radius=99,
            padx=8,
            pady=2,
        )
        self.status_dot.pack(side="right")

        # Scroll de mensajes de chat
        self.chat_scroll = ctk.CTkScrollableFrame(chat_container, fg_color="transparent", corner_radius=0)
        self.chat_scroll.pack(fill="both", expand=True, padx=8, pady=(4, 4))
        self.chat_scroll.columnconfigure(0, weight=1)

        # Chips de sugerencias rápidas
        sugg_frame = ctk.CTkFrame(chat_container, fg_color="transparent")
        sugg_frame.pack(fill="x", padx=8, pady=(0, 4))

        suggs = [
            ("Actualizar sistema", "actualizar el sistema"),
            ("Instalar Chrome", "instalar google chrome"),
            ("Explicar sudo", "¿qué es sudo y para qué sirve?"),
            ("Temperatura", "revisar temperatura del equipo"),
        ]
        s_row1 = ctk.CTkFrame(sugg_frame, fg_color="transparent")
        s_row1.pack(fill="x", pady=1)
        s_row2 = ctk.CTkFrame(sugg_frame, fg_color="transparent")
        s_row2.pack(fill="x", pady=1)

        for i, (txt, p) in enumerate(suggs):
            parent = s_row1 if i < 2 else s_row2
            ctk.CTkButton(
                parent,
                text=txt,
                height=22,
                font=ctk.CTkFont(size=8, weight="bold"),
                fg_color=C_GLASS_PILL,
                hover_color=C_BG_CARD_HOVER,
                text_color=C_ACCENT_LIGHT,
                border_width=1.5,
                border_color=C_GLASS_PILL_BORDER,
                corner_radius=99,
                command=lambda prompt=p: self._send_text(prompt),
            ).pack(side="left", padx=2, expand=True, fill="x")

        # Barra de entrada de texto
        entry_card = ctk.CTkFrame(chat_container, fg_color=C_BG_PANEL, corner_radius=12, border_width=1, border_color=C_BORDER)
        entry_card.pack(fill="x", padx=8, pady=(4, 8))

        self.voice_label = ctk.CTkLabel(entry_card, text="", font=ctk.CTkFont(size=9, weight="bold"), text_color=C_ACCENT_LIGHT)
        self.voice_label.pack(anchor="w", padx=8, pady=(2, 0))

        entry_row = ctk.CTkFrame(entry_card, fg_color="transparent")
        entry_row.pack(fill="x", padx=4, pady=(0, 4))

        self.input_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="Escribe tu duda sobre Linux...",
            height=32,
            font=ctk.CTkFont(size=10),
            fg_color=C_BG_BASE,
            border_width=1.5,
            border_color=C_BORDER,
            text_color=C_TEXT_MAIN,
            corner_radius=8,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(2, 4))
        self.input_entry.bind("<Return>", lambda e: self._on_send())

        self.mic_btn = ctk.CTkButton(
            entry_row,
            text="🎙️",
            width=30,
            height=30,
            font=ctk.CTkFont(size=13),
            fg_color=C_GLASS_PILL,
            hover_color=C_BG_CARD_HOVER,
            border_width=1.5,
            border_color=C_GLASS_PILL_BORDER,
            corner_radius=8,
            command=self._toggle_mic,
        )
        self.mic_btn.pack(side="left", padx=2)

        self.send_btn = ctk.CTkButton(
            entry_row,
            text="➤",
            width=30,
            height=30,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C_ACCENT,
            hover_color=C_ACCENT_DARK,
            border_width=1,
            border_color=C_GLASS_SHINE,
            text_color="#ffffff",
            corner_radius=8,
            command=self._on_send,
        )
        self.send_btn.pack(side="left", padx=(2, 2))

        # Tarjeta Perfil Detectado & Apps Sugeridas (Liquid Glass)
        distro_card = ctk.CTkFrame(self.right_col, fg_color=C_BG_CARD, corner_radius=14, border_width=1, border_color=C_BORDER)
        distro_card.pack(fill="x", padx=12, pady=(0, 16))

        ctk.CTkFrame(distro_card, height=2, fg_color=C_GLASS_SHINE, corner_radius=1).pack(fill="x", padx=12, pady=(2, 0))

        d_head = ctk.CTkFrame(distro_card, fg_color="transparent")
        d_head.pack(fill="x", padx=12, pady=(8, 4))

        d_logo = ctk.CTkFrame(d_head, width=30, height=30, fg_color=C_GLASS_PILL, corner_radius=8, border_width=1.5, border_color=C_GLASS_PILL_BORDER)
        d_logo.pack(side="left", padx=(0, 8))
        d_logo.pack_propagate(False)
        ctk.CTkLabel(d_logo, text="🐧", font=ctk.CTkFont(size=16)).pack(expand=True)

        d_title = ctk.CTkFrame(d_head, fg_color="transparent")
        d_title.pack(side="left")
        ctk.CTkLabel(d_title, text="Perfil detectado", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(d_title, text="Ubuntu / Debian compatible", font=ctk.CTkFont(size=9), text_color=C_TEXT_MUTED).pack(anchor="w")

        tags_row = ctk.CTkFrame(distro_card, fg_color="transparent")
        tags_row.pack(fill="x", padx=10, pady=(0, 6))
        for tag in ["APT", "GNOME", "Systemd", "Principiante"]:
            ctk.CTkLabel(
                tags_row,
                text=tag,
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=C_ACCENT_LIGHT,
                fg_color=C_GLASS_PILL,
                corner_radius=99,
                padx=8,
                pady=2,
            ).pack(side="left", padx=2)

        apps = [
            ("Visual Studio Code", "💙", lambda: visual_views.show_package_installer(self, "code")),
            ("Google Chrome", "🌐", lambda: visual_views.show_package_installer(self, "google-chrome")),
            ("Steam + Proton", "🎮", lambda: visual_views.show_gaming_hub(self)),
            ("Timeshift Backup", "🛡️", lambda: visual_views.show_package_installer(self, "timeshift")),
        ]
        for aname, aico, acallback in apps:
            arow = ctk.CTkFrame(distro_card, fg_color=C_BG_PANEL, corner_radius=8, border_width=1, border_color=C_BORDER)
            arow.pack(fill="x", padx=10, pady=2)

            left_app = ctk.CTkFrame(arow, fg_color="transparent")
            left_app.pack(side="left", padx=6, pady=4)
            ctk.CTkLabel(left_app, text=aico, font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(left_app, text=aname, font=ctk.CTkFont(size=10, weight="bold"), text_color=C_TEXT_MAIN).pack(side="left")

            ctk.CTkButton(
                arow,
                text="Instalar",
                width=58,
                height=20,
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=C_GLASS_PILL,
                hover_color=C_BG_CARD_HOVER,
                text_color=C_ACCENT_LIGHT,
                border_width=1.5,
                border_color=C_GLASS_PILL_BORDER,
                corner_radius=99,
                command=acallback,
            ).pack(side="right", padx=6, pady=2)

        ctk.CTkFrame(distro_card, height=4, fg_color="transparent").pack()

    def _add_bubble(self, sender: str, text: str, source: str = "SISTEMA") -> None:
        """Agrega una burbuja de mensaje al chat con diseño moderno y soporte de bloques terminal."""
        time_str = datetime.now().strftime("%H:%M")
        is_user = (sender == "user")

        if not hasattr(self, "_chat_history_records"):
            self._chat_history_records = []
        self._chat_history_records.append((sender, text, source))

        if is_user:
            self._msg_count += 1
            self._update_footer_counter()

        # Fila exterior
        row = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 12))

        if is_user:
            # ── Burbuja usuario (derecha) ──
            bubble = ctk.CTkFrame(
                row,
                fg_color=C_GLASS_PILL,
                border_width=1.5,
                border_color=C_GLASS_PILL_BORDER,
                corner_radius=16,
            )
            bubble.pack(side="right", padx=(20, 4))

            # Reflejo especular
            ctk.CTkFrame(bubble, height=2, fg_color=C_GLASS_SHINE, corner_radius=99).pack(fill="x", padx=4, pady=(2, 0))

            top = ctk.CTkFrame(bubble, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(6, 2))

            ctk.CTkLabel(
                top,
                text="👤 Tú",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=C_ACCENT_LIGHT,
            ).pack(side="left")

            ctk.CTkLabel(
                top,
                text=time_str,
                font=ctk.CTkFont(size=10),
                text_color=C_TEXT_MUTED,
            ).pack(side="right", padx=(8, 0))

            ctk.CTkLabel(
                bubble,
                text=text,
                font=ctk.CTkFont(size=12),
                text_color=C_TEXT_MAIN,
                justify="left",
                wraplength=270,
                anchor="w",
            ).pack(anchor="w", padx=12, pady=(2, 10))

        else:
            # ── Burbuja asistente (izquierda) ──
            bubble = ctk.CTkFrame(
                row,
                fg_color=C_BG_CARD,
                border_width=1.5,
                border_color=C_BORDER,
                corner_radius=16,
            )
            bubble.pack(side="left", padx=(4, 20))

            # Reflejo especular
            ctk.CTkFrame(bubble, height=2, fg_color=C_GLASS_SHINE, corner_radius=99).pack(fill="x", padx=4, pady=(2, 0))

            top = ctk.CTkFrame(bubble, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(6, 4))

            # Avatar y nombre
            ctk.CTkLabel(
                top,
                text="🤖 LinuxMate",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=C_TEXT_MAIN,
            ).pack(side="left")

            # Badge de modo de ejecución
            badge_styles = {
                "LOCAL": (C_GREEN, C_GREEN_D, "💻 LOCAL"),
                "IA": (C_ACCENT_LIGHT, C_GLASS_PILL, "⚡ IA"),
                "SISTEMA": (C_ACCENT_LIGHT, C_GLASS_PILL, "🛡️ SISTEMA"),
            }
            badge_info = badge_styles.get(source, (C_TEXT_MUTED, C_GLASS_PILL, source))
            ctk.CTkLabel(
                top,
                text=badge_info[2],
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=badge_info[0],
                fg_color=badge_info[1],
                corner_radius=99,
                padx=8, pady=2,
            ).pack(side="left", padx=8)

            # Botón copiar mensaje completo
            copy_btn = ctk.CTkButton(
                top,
                text="📋 Copiar",
                width=64,
                height=22,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="transparent",
                hover_color=C_BG_CARD_HOVER,
                text_color=C_TEXT_MUTED,
                corner_radius=6,
                command=lambda t=text: self._copy_to_clipboard(t),
            )
            copy_btn.pack(side="right", padx=(8, 0))

            ctk.CTkLabel(
                top,
                text=time_str,
                font=ctk.CTkFont(size=10),
                text_color=C_TEXT_MUTED,
            ).pack(side="right")

            # Alerta de acción destructiva o administrativa
            action_kws = [
                "instalando", "actualizando", "desinstalando", "eliminando",
                "se instalara", "se instalará", "se eliminara", "se eliminará",
                "peligro", "atención", "cuidado", "advertencia",
            ]
            if any(k in text.lower() for k in action_kws):
                alert_box = ctk.CTkFrame(bubble, fg_color="#2b1111", corner_radius=8, border_width=1, border_color="#7f1d1d")
                alert_box.pack(fill="x", padx=12, pady=(0, 6))
                ctk.CTkLabel(
                    alert_box,
                    text="⚠️ Esta acción requiere permisos o modifica componentes del sistema.",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color="#fca5a5",
                    justify="left",
                    wraplength=250,
                ).pack(anchor="w", padx=8, pady=4)

            # Renderizar fragmentos: texto normal y bloques terminal para código
            pattern = r"```([a-zA-Z0-9_-]*)\n?(.*?)```"
            segments = []
            last_idx = 0
            for match in re.finditer(pattern, text, flags=re.DOTALL):
                start, end = match.span()
                if start > last_idx:
                    normal = text[last_idx:start].strip()
                    if normal:
                        segments.append(("text", normal, ""))
                lang = match.group(1).strip().lower() or "bash"
                code = match.group(2).strip()
                if code:
                    segments.append(("code", code, lang))
                last_idx = end
            if last_idx < len(text):
                remaining = text[last_idx:].strip()
                if remaining:
                    segments.append(("text", remaining, ""))
            if not segments:
                segments.append(("text", text.strip(), ""))

            content_frame = ctk.CTkFrame(bubble, fg_color="transparent")
            content_frame.pack(fill="x", padx=12, pady=(4, 8))

            for kind, val, lang in segments:
                if kind == "text":
                    ctk.CTkLabel(
                        content_frame,
                        text=val,
                        font=ctk.CTkFont(size=12),
                        text_color=C_TEXT_MAIN,
                        justify="left",
                        wraplength=270,
                        anchor="w",
                    ).pack(anchor="w", fill="x", pady=(2, 4))
                elif kind == "code":
                    code_card = ctk.CTkFrame(
                        content_frame,
                        fg_color=C_BG_BASE,
                        border_width=1.5,
                        border_color=C_BORDER,
                        corner_radius=10,
                    )
                    code_card.pack(fill="x", pady=(4, 6))

                    top_bar = ctk.CTkFrame(code_card, fg_color=C_BG_PANEL, height=26, corner_radius=10)
                    top_bar.pack(fill="x")
                    top_bar.pack_propagate(False)

                    ctk.CTkLabel(top_bar, text="● ● ●", font=ctk.CTkFont(size=9), text_color=C_BORDER_HOVER).pack(side="left", padx=(8, 4))
                    ctk.CTkLabel(top_bar, text=lang.upper(), font=ctk.CTkFont(size=9, weight="bold"), text_color=C_TEXT_MUTED).pack(side="left")

                    copy_snippet_btn = ctk.CTkButton(
                        top_bar,
                        text="📋",
                        width=28,
                        height=18,
                        font=ctk.CTkFont(size=9),
                        fg_color="transparent",
                        hover_color=C_BG_CARD_HOVER,
                        text_color=C_TEXT_MUTED,
                        corner_radius=4,
                        command=lambda c=val: self._copy_to_clipboard(c),
                    )
                    copy_snippet_btn.pack(side="right", padx=4)

                    lines_count = len(val.splitlines())
                    box_height = min(200, max(38, lines_count * 18 + 10))
                    code_box = ctk.CTkTextbox(
                        code_card,
                        fg_color=C_BG_BASE,
                        text_color="#e9d5ff",
                        font=ctk.CTkFont(family="Courier", size=11),
                        height=box_height,
                        border_width=0,
                        corner_radius=0,
                    )
                    code_box.pack(fill="x", padx=6, pady=(2, 4))
                    code_box.insert("1.0", val)
                    code_box.configure(state="disabled")

        # Scroll automático al final
        self.update_idletasks()
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _add_thinking_indicator(self) -> None:
        """Agrega una burbuja estilizada de procesamiento con IA."""
        if self._thinking_label is not None:
            return
        row = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8))
        row._is_thinking = True

        bubble = ctk.CTkFrame(row, fg_color=C_GLASS_PILL, border_width=1.5,
                               border_color=C_GLASS_PILL_BORDER, corner_radius=14)
        bubble.pack(side="left", padx=(4, 20))

        # Reflejo especular
        ctk.CTkFrame(bubble, height=2, fg_color=C_GLASS_SHINE, corner_radius=99).pack(fill="x", padx=4, pady=(2, 0))

        self._thinking_label = ctk.CTkLabel(
            bubble,
            text="✨ Procesando con IA...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_ACCENT_LIGHT,
        )
        self._thinking_label.pack(padx=16, pady=8)
        self._thinking_row = row

        self.update_idletasks()
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _remove_thinking_indicator(self) -> None:
        """Elimina la burbuja de procesamiento con IA."""
        if self._thinking_label is not None:
            try:
                self._thinking_row.destroy()
            except Exception:
                pass
            self._thinking_label = None

    def _copy_to_clipboard(self, text: str) -> None:
        """Copia texto al portapapeles del sistema."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # BARRA DE ENTRADA
    # ─────────────────────────────────────────────────────────────────────────

    def _build_input_bar(self) -> None:
        # Indicador de voz
        self.voice_indicator = ctk.CTkFrame(
            self.center_col, height=22, fg_color=C_BG
        )
        self.voice_indicator.pack(fill="x", padx=16)

        self.voice_label = ctk.CTkLabel(
            self.voice_indicator,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C_ORANGE,
        )
        self.voice_label.pack(side="left")

        # Fila de entrada flotante
        bar = ctk.CTkFrame(
            self.center_col,
            fg_color=C_INPUT_BG,
            corner_radius=16,
            border_width=1.5,
            border_color=C_BORDER,
        )
        bar.pack(fill="x", padx=16, pady=(2, 6))

        self.input_entry = ctk.CTkEntry(
            bar,
            placeholder_text="Escribe una instrucción o pide una tarea para tu equipo Ubuntu...",
            height=46,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=0,
            text_color=C_TEXT,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(16, 6), pady=6)
        self.input_entry.bind("<Return>", lambda e: self._on_send())

        # Botón micrófono
        self.mic_btn = ctk.CTkButton(
            bar,
            text="🎙️",
            width=44,
            height=40,
            font=ctk.CTkFont(size=16),
            fg_color=C_CARD,
            hover_color=C_CARD_HOVER,
            corner_radius=10,
            command=self._toggle_mic,
        )
        self.mic_btn.pack(side="left", padx=4, pady=6)

        # Botón enviar
        self.send_btn = ctk.CTkButton(
            bar,
            text="➤ Enviar",
            width=96,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=C_ORANGE,
            hover_color=C_ORANGE_H,
            text_color="#ffffff",
            corner_radius=10,
            command=self._on_send,
        )
        self.send_btn.pack(side="left", padx=(4, 8), pady=6)

    # ─────────────────────────────────────────────────────────────────────────
    # FOOTER
    # ─────────────────────────────────────────────────────────────────────────

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self.center_col, height=30, corner_radius=0,
                              fg_color=C_BG_PANEL, border_width=1, border_color=C_BORDER)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        # Contador de mensajes en sesión
        self.footer_msgs = ctk.CTkLabel(
            footer,
            text="Sesión: 0 mensajes",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_TEXT_MUTED,
        )
        self.footer_msgs.pack(side="left", padx=16)

        # Badge memoria persistente
        mem_count = get_memory_count()
        mem_text = f"💾 Memoria activa: {mem_count // 2} intercambios" if mem_count else "💾 Sin memoria previa"
        self.footer_mem = ctk.CTkLabel(
            footer,
            text=mem_text,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_ACCENT_LIGHT,
        )
        self.footer_mem.pack(side="right", padx=16)

    def _update_footer_counter(self) -> None:
        try:
            self.footer_msgs.configure(text=f"Sesión: {self._msg_count} mensajes")
        except Exception:
            pass

    def _update_footer_memory(self) -> None:
        try:
            mem_count = get_memory_count()
            mem_text = f"💾 Memoria activa: {mem_count // 2} intercambios" if mem_count else "💾 Sin memoria previa"
            self.footer_mem.configure(text=mem_text)
        except Exception:
            pass

    def _build_system_panel(self) -> None:
        """Compatibilidad con versiones previas."""
        pass

    def _update_system_panel(self, s: dict) -> None:
        """Actualiza los valores del panel de sistema desde el hilo principal."""
        if not s:
            return

        # Actualizar métricas del dashboard central (Hero System Card)
        try:
            cpu_val = float(s.get("cpu", 0))
            self._hero_cpu_lbl.configure(text=f"{cpu_val:.0f}%")
            self._hero_cpu_bar.set(max(0.0, min(1.0, cpu_val / 100)))

            mem_pct = float(s.get("mem_pct", 0))
            mem_gb = float(s.get("mem_gb", 0))
            self._hero_mem_lbl.configure(text=f"{mem_pct:.0f}% ({mem_gb:.1f} GB)")
            self._hero_mem_bar.set(max(0.0, min(1.0, mem_pct / 100)))

            pkgs = int(s.get("pkgs", 0))
            self._hero_pkgs_lbl.configure(text=f"{pkgs} paquetes" if pkgs else "Al día")
            self._hero_pkgs_bar.set(0.7 if pkgs else 1.0)
        except Exception:
            pass

        now = time.monotonic()
        if now - self._last_snapshot_at >= 60:
            log_system_snapshot(
                s.get("cpu"),
                s.get("mem_pct"),
                s.get("disk_pct"),
                s,
                self.session_id,
            )
            self._last_snapshot_at = now

    def _start_system_monitor(self) -> None:
        """Inicia el hilo de monitoreo del sistema cada 3 segundos."""
        def _loop():
            while True:
                try:
                    stats = _get_system_stats()
                    self.after(0, lambda s=stats: self._update_system_panel(s))
                except Exception:
                    break
                time.sleep(3)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    # ─────────────────────────────────────────────────────────────────────────
    # LÓGICA DE MENSAJES
    # ─────────────────────────────────────────────────────────────────────────

    def _show_welcome(self) -> None:
        mem_count = get_memory_count()
        mem_info = f"\n\n💾 Memoria cargada: {mem_count // 2} intercambios previos." if mem_count else ""
        msg = (
            "¡Hola! Soy LinuxMate AI 🤖.\n\n"
            "Puedo ayudarte a resolver dudas, ejecutar tareas en tu sistema, "
            "explicar comandos o configurar aplicaciones.\n\n"
            "Pulsa una acción rápida del panel o escribe tu duda aquí abajo." + mem_info
        )
        self._add_bubble("assistant", msg)

    def _send_text(self, text: str) -> None:
        """Envía texto directamente (usado por chips y botones del panel)."""
        self.input_entry.delete(0, END)
        self.input_entry.insert(0, text)
        self._on_send()

    def _on_send(self) -> None:
        text = self.input_entry.get().strip()
        if not text:
            return

        if text.lower() in {"salir", "exit", "cerrar"}:
            self._add_bubble("user", text)
            self._add_bubble("assistant", "¡Hasta pronto! Cerrando el asistente...")
            self.tts.speak("Hasta pronto.")
            self.after(600, self.destroy)
            return

        route = self.nlp.route(text)
        if route.is_local or not self.agent:
            log_message("user", text, self.session_id)
        if self._handle_visual_request(text, route):
            self.input_entry.delete(0, END)
            return

        self.input_entry.delete(0, END)
        self._add_bubble("user", text)
        self._set_input_state(False)
        self._set_status("● Pensando...", C_YELLOW, "#2a2200")
        self._add_thinking_indicator()

        threading.Thread(target=self._process_thread, args=(text, route), daemon=True).start()

    def _handle_visual_request(self, text: str, route: RequestRoute) -> bool:
        """Ejecuta solamente rutas visuales ya validadas por el enrutador central."""
        handlers = {
            "SHOW_PROCESSES": self._show_process_viewer,
            "SHOW_NETWORK": self._show_network_viewer,
            "UPDATE_SYSTEM": self._show_update_runner,
        }

        if not route.is_visual:
            return False

        self._add_bubble("user", text)
        try:
            if route.intent == "INSTALL_PACKAGE":
                self._show_package_installer(route.param or "")
            elif route.intent == "INSTALL_DEB":
                visual_views.show_package_installer(self, route.param or "", deb_mode=True)
            elif route.intent == "REMOVE_PACKAGE":
                visual_views.show_package_remover(self, route.param or "")
            else:
                handler = handlers.get(route.intent or "")
                if handler is None:
                    raise RuntimeError("No hay una vista registrada para esta accion.")
                handler()
            log_message(
                "assistant",
                f"Vista visual abierta: {route.intent}.",
                self.session_id,
            )
        except Exception as exc:
            log_message("assistant", f"No pude abrir la vista local: {exc}", self.session_id)
            self._add_bubble(
                "assistant",
                f"No pude abrir la vista local: {exc}",
                source="SISTEMA",
            )
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # VISTAS GRAFICAS PARA USUARIOS NUEVOS
    # ─────────────────────────────────────────────────────────────────────────

    def _make_window(self, title: str, size: str = "760x560") -> ctk.CTkToplevel:
        window = ctk.CTkToplevel(self)
        window.title(title)
        window.geometry(size)
        window.minsize(560, 420)
        window.configure(fg_color=C_PANEL)
        window.grab_set()
        return window

    def _show_process_viewer(self) -> None:
        visual_views.show_process_viewer(self)
        return
        window = self._make_window("Procesos activos", "820x620")

        header = ctk.CTkFrame(window, fg_color=C_PANEL, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(
            header,
            text="Procesos y aplicaciones activas",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            header,
            text="Las barras muestran que aplicaciones consumen mas CPU y memoria ahora mismo.",
            font=ctk.CTkFont(size=12),
            text_color=C_MUTED2,
        ).pack(anchor="w", padx=18, pady=(0, 14))

        summary = ctk.CTkFrame(window, fg_color=C_PANEL)
        summary.pack(fill="x", padx=16, pady=12)
        cpu_lbl, cpu_bar = self._visual_metric(summary, "CPU total", C_RED)
        mem_lbl, mem_bar = self._visual_metric(summary, "Memoria total", C_PURPLE)

        list_frame = ctk.CTkScrollableFrame(window, fg_color=C_PANEL, corner_radius=0)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        rows = [self._create_process_row(list_frame) for _ in range(14)]

        def refresh():
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory().percent
                cpu_lbl.configure(text=f"{cpu:.0f}%")
                cpu_bar.set(cpu / 100)
                mem_lbl.configure(text=f"{mem:.0f}%")
                mem_bar.set(mem / 100)

                processes = []
                for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                    try:
                        info = proc.info
                        processes.append(info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                processes.sort(key=lambda p: (p.get("cpu_percent") or 0, p.get("memory_percent") or 0), reverse=True)

                for index, widgets in enumerate(rows):
                    proc = processes[index] if index < len(processes) else None
                    self._update_process_row(widgets, proc)
            except Exception as exc:
                self._add_bubble("assistant", f"No pude actualizar la vista de procesos: {exc}")

            if window.winfo_exists():
                window.after(2500, refresh)

        refresh()

    def _visual_metric(self, parent, label: str, color: str):
        frame = ctk.CTkFrame(parent, fg_color=C_CARD, border_width=0, corner_radius=8)
        frame.pack(side="left", fill="x", expand=True, padx=4)
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(top, text=label, text_color=C_MUTED2, font=ctk.CTkFont(size=12)).pack(side="left")
        value = ctk.CTkLabel(top, text="—", text_color=C_TEXT, font=ctk.CTkFont(size=16, weight="bold"))
        value.pack(side="right")
        bar = ctk.CTkProgressBar(frame, height=8, fg_color=C_BORDER, progress_color=color)
        bar.pack(fill="x", padx=12, pady=(0, 12))
        bar.set(0)
        return value, bar

    def _create_process_row(self, parent) -> dict[str, Any]:
        row = ctk.CTkFrame(parent, fg_color=C_CARD, border_width=0, corner_radius=8)
        row.pack(fill="x", pady=4)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(8, 2))
        name_lbl = ctk.CTkLabel(top, text="—", text_color=C_TEXT, font=ctk.CTkFont(size=13, weight="bold"))
        name_lbl.pack(side="left")
        pid_lbl = ctk.CTkLabel(top, text="PID —", text_color=C_MUTED, font=ctk.CTkFont(family="Courier", size=10))
        pid_lbl.pack(side="right")

        bars = ctk.CTkFrame(row, fg_color="transparent")
        bars.pack(fill="x", padx=12, pady=(2, 10))
        cpu_widgets = self._small_bar(bars, "CPU", 0, C_RED)
        mem_widgets = self._small_bar(bars, "RAM", 0, C_PURPLE)
        return {"row": row, "name": name_lbl, "pid": pid_lbl, "cpu": cpu_widgets, "mem": mem_widgets}

    def _update_process_row(self, widgets: dict[str, Any], proc: Optional[dict]) -> None:
        if not proc:
            widgets["name"].configure(text="—")
            widgets["pid"].configure(text="PID —")
            self._update_small_bar(widgets["cpu"], 0)
            self._update_small_bar(widgets["mem"], 0)
            return

        name = (proc.get("name") or "Proceso sin nombre")[:32]
        pid = proc.get("pid", "—")
        cpu = float(proc.get("cpu_percent") or 0)
        mem = float(proc.get("memory_percent") or 0)
        widgets["name"].configure(text=name)
        widgets["pid"].configure(text=f"PID {pid}")
        self._update_small_bar(widgets["cpu"], cpu)
        self._update_small_bar(widgets["mem"], mem)

    def _small_bar(self, parent, label: str, percent: float, color: str) -> dict[str, Any]:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=1)
        ctk.CTkLabel(frame, text=label, width=38, text_color=C_MUTED2, font=ctk.CTkFont(size=10)).pack(side="left")
        bar = ctk.CTkProgressBar(frame, height=6, fg_color=C_BORDER, progress_color=color)
        bar.pack(side="left", fill="x", expand=True, padx=6)
        bar.set(max(0, min(percent, 100)) / 100)
        value = ctk.CTkLabel(frame, text=f"{percent:.1f}%", width=52, text_color=C_TEXT, font=ctk.CTkFont(size=10))
        value.pack(side="right")
        return {"bar": bar, "value": value}

    def _update_small_bar(self, widgets: dict[str, Any], percent: float) -> None:
        widgets["bar"].set(max(0, min(percent, 100)) / 100)
        widgets["value"].configure(text=f"{percent:.1f}%")

    def _show_network_viewer(self) -> None:
        visual_views.show_network_viewer(self)
        return
        window = self._make_window("Red e internet", "760x560")
        ctk.CTkLabel(
            window,
            text="Red e internet",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(
            window,
            text="Vista simple de interfaces, trafico recibido/enviado y direcciones IP.",
            font=ctk.CTkFont(size=12),
            text_color=C_MUTED2,
        ).pack(anchor="w", padx=18, pady=(0, 12))

        totals = ctk.CTkFrame(window, fg_color=C_PANEL)
        totals.pack(fill="x", padx=16, pady=(0, 8))
        rx_lbl, rx_bar = self._visual_metric(totals, "Descarga", C_GREEN)
        tx_lbl, tx_bar = self._visual_metric(totals, "Subida", C_BLUE)

        interfaces = ctk.CTkScrollableFrame(window, fg_color=C_PANEL, corner_radius=0)
        interfaces.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        last = {"time": time.time(), "counters": psutil.net_io_counters()}
        network_rows: dict[str, dict[str, Any]] = {}

        def refresh():
            try:
                now = time.time()
                counters = psutil.net_io_counters()
                elapsed = max(now - last["time"], 0.1)
                rx_speed = (counters.bytes_recv - last["counters"].bytes_recv) / elapsed
                tx_speed = (counters.bytes_sent - last["counters"].bytes_sent) / elapsed
                last["time"] = now
                last["counters"] = counters

                rx_lbl.configure(text=f"{_format_bytes(rx_speed)}/s")
                tx_lbl.configure(text=f"{_format_bytes(tx_speed)}/s")
                rx_bar.set(min(rx_speed / (5 * 1024 * 1024), 1))
                tx_bar.set(min(tx_speed / (2 * 1024 * 1024), 1))

                addrs = psutil.net_if_addrs()
                stats = psutil.net_if_stats()
                io = psutil.net_io_counters(pernic=True)
                current_names = set(addrs)

                for name in list(network_rows):
                    if name not in current_names:
                        network_rows[name]["row"].destroy()
                        del network_rows[name]

                for name in sorted(addrs):
                    if name not in network_rows:
                        network_rows[name] = self._create_network_row(interfaces)
                    self._update_network_row(network_rows[name], name, addrs.get(name, []), stats.get(name), io.get(name))
            except Exception as exc:
                self._add_bubble("assistant", f"No pude actualizar la vista de red: {exc}")

            if window.winfo_exists():
                window.after(2500, refresh)

        refresh()

    def _create_network_row(self, parent) -> dict[str, Any]:
        row = ctk.CTkFrame(parent, fg_color=C_CARD, border_width=0, corner_radius=8)
        row.pack(fill="x", pady=4)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(8, 2))
        name_lbl = ctk.CTkLabel(top, text="—", text_color=C_TEXT, font=ctk.CTkFont(size=13, weight="bold"))
        name_lbl.pack(side="left")
        status_lbl = ctk.CTkLabel(top, text="—", text_color=C_MUTED, font=ctk.CTkFont(size=11, weight="bold"))
        status_lbl.pack(side="right")

        ip_lbl = ctk.CTkLabel(row, text="Sin IP visible", text_color=C_MUTED2, font=ctk.CTkFont(size=11))
        ip_lbl.pack(anchor="w", padx=12)
        data_lbl = ctk.CTkLabel(row, text="", text_color=C_MUTED, font=ctk.CTkFont(size=10))
        data_lbl.pack(anchor="w", padx=12, pady=(2, 10))
        return {"row": row, "name": name_lbl, "status": status_lbl, "ip": ip_lbl, "data": data_lbl}

    def _update_network_row(self, widgets: dict[str, Any], name: str, addrs, stat, counters) -> None:
        is_up = bool(stat and stat.isup)
        color = C_GREEN if is_up else C_MUTED
        widgets["name"].configure(text=name)
        widgets["status"].configure(text="Conectada" if is_up else "Inactiva", text_color=color)

        ips = []
        for addr in addrs:
            family = str(getattr(addr, "family", ""))
            if "AF_INET" in family and not addr.address.startswith("127."):
                ips.append(addr.address)
        ip_text = ", ".join(ips) if ips else "Sin IP visible"
        data_text = ""
        if counters:
            data_text = f"Recibido {_format_bytes(counters.bytes_recv)} · Enviado {_format_bytes(counters.bytes_sent)}"

        widgets["ip"].configure(text=ip_text)
        widgets["data"].configure(text=data_text)

    def _show_package_installer(self, package_name: str = "") -> None:
        visual_views.show_package_installer(self, package_name)
        return
        window = self._make_window("Instalar paquete", "760x560")

        ctk.CTkLabel(window, text="Instalar programa", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXT).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(window, text="Escribe el nombre del paquete apt. La instalacion pedira tu contraseña si hace falta.", font=ctk.CTkFont(size=12), text_color=C_MUTED2).pack(anchor="w", padx=18, pady=(0, 12))

        form = ctk.CTkFrame(window, fg_color=C_CARD, border_width=0, corner_radius=8)
        form.pack(fill="x", padx=16, pady=(0, 10))
        entry = ctk.CTkEntry(form, placeholder_text="Ejemplo: vlc, gimp, htop", height=38, text_color=C_TEXT)
        entry.pack(side="left", fill="x", expand=True, padx=12, pady=12)
        if package_name:
            entry.insert(0, package_name)

        progress = ctk.CTkProgressBar(window, height=10, fg_color=C_BORDER, progress_color=C_ORANGE)
        progress.pack(fill="x", padx=16, pady=(4, 8))
        progress.set(0)

        log = ctk.CTkTextbox(window, fg_color=C_BG, text_color=C_TEXT, border_width=0, corner_radius=8)
        log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        log.insert("end", "Listo para instalar. Primero puedes buscar para confirmar el nombre del paquete.\n")
        log.configure(state="disabled")

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.pack(side="right", padx=(0, 12))

        def append(line: str):
            log.configure(state="normal")
            log.insert("end", line + "\n")
            log.see("end")
            log.configure(state="disabled")

        def package() -> str:
            return entry.get().strip()

        def search():
            pkg = package()
            if not pkg:
                append("Escribe primero que programa quieres buscar.")
                return
            self._run_command_in_view(["apt-cache", "search", pkg], progress, append, limit_lines=30)

        def install():
            pkg = package()
            if not pkg:
                append("Escribe primero que programa quieres instalar.")
                return
            if not re.fullmatch(r"[A-Za-z0-9.+_-]+", pkg):
                append("Nombre de paquete invalido. Usa solo letras, numeros, punto, guion o guion bajo.")
                return
            if not shutil.which("pkexec"):
                append("No encontre pkexec. Abre una terminal y usa: sudo apt install " + pkg)
                return
            self._run_command_in_view(["pkexec", "apt", "install", "-y", pkg], progress, append)

        ctk.CTkButton(buttons, text="Buscar", width=82, fg_color=C_CARD, hover_color=C_BORDER, border_width=1, border_color=C_BORDER, command=search).pack(side="left", padx=3)
        ctk.CTkButton(buttons, text="Instalar", width=90, fg_color=C_ORANGE, hover_color=C_ORANGE_H, command=install).pack(side="left", padx=3)

    def _show_update_runner(self) -> None:
        visual_views.show_update_runner(self)
        return
        window = self._make_window("Actualizar sistema", "760x520")
        ctk.CTkLabel(window, text="Actualizar sistema", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXT).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(window, text="Se abrira una autorizacion grafica para actualizar la lista de paquetes y mejoras.", font=ctk.CTkFont(size=12), text_color=C_MUTED2).pack(anchor="w", padx=18, pady=(0, 12))
        progress = ctk.CTkProgressBar(window, height=10, fg_color=C_BORDER, progress_color=C_ORANGE)
        progress.pack(fill="x", padx=16, pady=(4, 8))
        progress.set(0)
        log = ctk.CTkTextbox(window, fg_color=C_BG, text_color=C_TEXT, border_width=0, corner_radius=8)
        log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        log.insert("end", "Pulsa el boton para iniciar la actualizacion grafica.\n")
        log.configure(state="disabled")

        def append(line: str):
            log.configure(state="normal")
            log.insert("end", line + "\n")
            log.see("end")
            log.configure(state="disabled")

        def start():
            if shutil.which("update-manager"):
                try:
                    subprocess.Popen(["update-manager"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    append("Se abrio el Actualizador de Software de Ubuntu.")
                    progress.set(1)
                    return
                except Exception as exc:
                    append(f"No pude abrir update-manager: {exc}")
            if not shutil.which("pkexec"):
                append("No encontre pkexec. Abre una terminal y usa: sudo apt update && sudo apt upgrade")
                return
            self._run_command_in_view(["pkexec", "bash", "-lc", "apt update && apt upgrade -y"], progress, append)

        ctk.CTkButton(window, text="Iniciar actualizacion", height=36, fg_color=C_ORANGE, hover_color=C_ORANGE_H, command=start).pack(fill="x", padx=16, pady=(0, 14))

    def _run_command_in_view(self, args: list[str], progress, append, limit_lines: Optional[int] = None) -> None:
        visual_views.run_command_in_view(self, args, progress, append, limit_lines)
        return
        def worker():
            self.after(0, lambda: self._set_status("● Ejecutando...", C_YELLOW, "#2a2200"))
            self.after(0, lambda: progress.start())
            try:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                count = 0
                if proc.stdout:
                    for line in proc.stdout:
                        count += 1
                        if limit_lines is None or count <= limit_lines:
                            self.after(0, lambda l=line.rstrip(): append(l))
                code = proc.wait()
                final = "Terminado correctamente." if code == 0 else f"El comando termino con codigo {code}."
                self.after(0, lambda: append(final))
            except Exception as exc:
                self.after(0, lambda: append(f"Error: {exc}"))
            finally:
                self.after(0, progress.stop)
                self.after(0, lambda: progress.set(1))
                self.after(0, lambda: self._set_status("● Listo", C_GREEN, C_GREEN_D))

        threading.Thread(target=worker, daemon=True).start()

    def _set_input_state(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.input_entry.configure(state=state)
        self.send_btn.configure(state=state)

    def _set_status(self, text: str, color: str = C_GREEN, bg: str = C_GREEN_D) -> None:
        self.status_dot.configure(text=text, text_color=color, fg_color=bg)

    def _process_thread(self, user_text: str, route: RequestRoute) -> None:
        try:
            result = self.nlp.process_with_source(user_text, self.agent, route)
            reply, source = result.text, result.source
        except Exception as exc:
            reply = format_llm_error(exc)
            source = "IA" if not route.is_local else "LOCAL"
        self.after(0, lambda: self._show_reply(reply, source))

    def _show_reply(self, reply: str, source: str = "SISTEMA") -> None:
        self._remove_thinking_indicator()
        self._add_bubble("assistant", reply, source=source)
        self._set_status("● Listo", C_GREEN, C_GREEN_D)
        self._set_input_state(True)
        if source != "IA":
            log_message("assistant", reply, self.session_id)
        self._update_footer_memory()
        self.tts.speak(reply)

    # ─────────────────────────────────────────────────────────────────────────
    # HISTORIAL Y MEMORIA
    # ─────────────────────────────────────────────────────────────────────────

    def _show_memory_summary(self) -> None:
        """Muestra el historial persistente en una ventana visual."""
        visual_views.show_history_viewer(self)

    def _confirm_clear_memory(self) -> None:
        """Muestra confirmación antes de borrar la memoria persistente."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirmar")
        dialog.geometry("380x160")
        dialog.resizable(False, False)
        dialog.configure(fg_color=C_PANEL)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="¿Borrar toda la memoria persistente?\nEsto eliminará el historial de sesiones anteriores.",
            font=ctk.CTkFont(size=13),
            text_color=C_TEXT,
            justify="center",
        ).pack(pady=(24, 12))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(
            btn_frame, text="Cancelar", width=100,
            fg_color=C_CARD, hover_color=C_BORDER, text_color=C_MUTED2,
            command=dialog.destroy,
        ).pack(side="left", padx=8)

        def _do_clear():
            clear_memory()
            dialog.destroy()
            self._add_bubble("assistant", "🗑️ Memoria persistente borrada. La próxima sesión comenzará desde cero.")
            self._update_footer_memory()

        ctk.CTkButton(
            btn_frame, text="Borrar", width=100,
            fg_color=C_RED, hover_color="#b91c1c", text_color="#fff",
            command=_do_clear,
        ).pack(side="left", padx=8)

    # ─────────────────────────────────────────────────────────────────────────
    # CONTROLES DE VOZ Y SESIÓN
    # ─────────────────────────────────────────────────────────────────────────

    def _toggle_speaker(self) -> None:
        self.tts.is_enabled = not self.tts.is_enabled
        if self.tts.is_enabled:
            self.voice_btn.configure(text="● Voz activa", fg_color=C_ORANGE, hover_color=C_ORANGE_H)
        else:
            self.tts.stop()
            self.voice_btn.configure(text="○ Voz silenciada", fg_color=C_CARD, hover_color=C_BORDER)

    def _toggle_mic(self) -> None:
        if self.stt.is_listening:
            self.stt.stop_listening()
            self.mic_btn.configure(text="🎤", fg_color=C_CARD, hover_color=C_BORDER)
            self.voice_label.configure(text="")
            self._set_status("● Listo", C_GREEN, C_GREEN_D)
            return

        if not self.stt.is_available:
            self._add_bubble("assistant",
                "Para usar el micrófono offline, asegúrate de tener el modelo Vosk en español.")
            return

        ok = self.stt.start_listening(
            on_text_recognized=self._on_voice_recognized,
            on_status_change=self._on_voice_status,
        )
        if ok:
            self.mic_btn.configure(text="🔴", fg_color="#7f1d1d", hover_color="#991b1b")
            self.voice_label.configure(text="ESCUCHANDO  ▮▮▮▮▮▮▯▯▯▯")
            self._set_status("● Escuchando voz...", C_ORANGE, C_ORANGE_D)

    def _on_voice_recognized(self, text: str) -> None:
        def _handle():
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, text)
            self._on_send()
        self.after(0, _handle)

    def _on_voice_status(self, status: str) -> None:
        if "Escuchando" in status:
            self.after(0, lambda: self._set_status("● Escuchando...", C_ORANGE, C_ORANGE_D))
        elif "reconocida" in status:
            self.after(0, lambda: self.voice_label.configure(text=""))
            self.after(0, lambda: self._set_status("● Procesando...", C_BLUE, C_BLUE_D))
        else:
            self.after(0, lambda: self.voice_label.configure(text=""))
            self.after(0, lambda: self._set_status("● Listo", C_GREEN, C_GREEN_D))

    def _clear_chat(self) -> None:
        for w in self.chat_scroll.winfo_children():
            w.destroy()
        if self.agent:
            self.agent.reset_chat(clear_persistent=False)
        self._msg_count = 0
        self._chat_history_records = []
        self._update_footer_counter()
        self._show_welcome()

    def destroy(self) -> None:
        try:
            self.tts.stop()
            if self.stt.is_listening:
                self.stt.stop_listening()
            close_session(self.session_id)
        except Exception:
            pass
        super().destroy()


def run() -> None:
    app = AssistantApp()
    app.mainloop()

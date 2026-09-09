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
from src.gui import visual_views
from src.nlp.processor import NLPProcessor
from src.nlp.router import RequestRoute
from src.voice.stt import STTEngine
from src.voice.tts import TTSEngine

# ─── Paleta de colores ────────────────────────────────────────────────────────
C_BG       = "#0f1117"   # Fondo general
C_SIDEBAR  = "#141720"   # Sidebar izquierda
C_PANEL    = "#181c25"   # Paneles/tarjetas
C_CARD     = "#1e2130"   # Tarjetas interiores
C_BORDER   = "#282d3e"   # Bordes sutiles
C_ORANGE   = "#f97316"   # Acento naranja principal
C_ORANGE_H = "#ea6005"   # Naranja hover
C_ORANGE_D = "#431a00"   # Naranja oscuro (fondos badge)
C_GREEN    = "#22c55e"   # Verde éxito / activo
C_GREEN_D  = "#14290e"   # Verde oscuro (fondo badge)
C_YELLOW   = "#facc15"   # Amarillo advertencia
C_RED      = "#ef4444"   # Rojo error / peligro
C_BLUE     = "#3b82f6"   # Azul usuario
C_BLUE_D   = "#0f1f3d"   # Azul oscuro (fondo burbuja usuario)
C_TEXT     = "#e2e8f0"   # Texto principal
C_MUTED    = "#64748b"   # Texto secundario apagado
C_MUTED2   = "#94a3b8"   # Texto gris medio
C_PURPLE   = "#a855f7"   # Morado (memoria)
C_PURPLE_D = "#2d1550"   # Morado oscuro (fondo badge memoria)


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


class SidebarIcon(ctk.CTkButton):
    """Botón de ícono en la barra lateral."""

    def __init__(self, parent, icon: str, tooltip: str, command=None, active: bool = False):
        color = C_ORANGE if active else "transparent"
        super().__init__(
            parent,
            text=icon,
            width=44,
            height=44,
            font=ctk.CTkFont(size=18),
            fg_color=color,
            hover_color="#232840",
            corner_radius=10,
            command=command,
        )
        self._tooltip = tooltip


class AssistantApp(ctk.CTk):
    """Ventana principal rediseñada del Agente Autónomo para Linux."""

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Agente Linux — Ubuntu")
        self.geometry("1150x740")
        self.minsize(920, 600)
        self.configure(fg_color=C_BG)
        self.C_BG = C_BG
        self.C_PANEL = C_PANEL
        self.C_CARD = C_CARD
        self.C_BORDER = C_BORDER
        self.C_ORANGE = C_ORANGE
        self.C_ORANGE_H = C_ORANGE_H
        self.C_GREEN = C_GREEN
        self.C_GREEN_D = C_GREEN_D
        self.C_YELLOW = C_YELLOW
        self.C_RED = C_RED
        self.C_BLUE = C_BLUE
        self.C_MUTED = C_MUTED
        self.C_MUTED2 = C_MUTED2
        self.C_TEXT = C_TEXT
        self.C_PURPLE = C_PURPLE
        self._format_bytes = _format_bytes

        # Módulos del backend
        self.agent      = create_agent()
        self.session_id = self.agent.session_id if self.agent else start_session("desktop-gui")
        self.nlp        = NLPProcessor()
        self.tts        = TTSEngine()
        self.stt        = STTEngine()
        self._speaking  = False
        self._listening = False
        self._msg_count = 0  # contador de mensajes en sesión actual
        self._thinking_label: Optional[ctk.CTkLabel] = None
        self._last_snapshot_at = 0.0
        init_db()

        self._build_layout()
        self._start_system_monitor()
        self._show_welcome()

    # ─────────────────────────────────────────────────────────────────────────
    # LAYOUT PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        # Sidebar izquierda
        self.sidebar = ctk.CTkFrame(self, width=62, corner_radius=0, fg_color=C_SIDEBAR)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        # Columna central: header + chat + input
        self.center_col = ctk.CTkFrame(self, fg_color=C_BG)
        self.center_col.pack(side="left", fill="both", expand=True)
        self._build_header()
        self._build_chips_bar()
        self._build_chat_area()
        self._build_input_bar()
        self._build_footer()

        # Panel derecho: estado del sistema
        self.right_panel = ctk.CTkFrame(self, width=235, corner_radius=0, fg_color=C_PANEL)
        self.right_panel.pack(side="right", fill="y", padx=0, pady=0)
        self.right_panel.pack_propagate(False)
        self._build_system_panel()

    # ─────────────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ─────────────────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        # Logo
        logo = ctk.CTkLabel(
            self.sidebar,
            text="🐧",
            font=ctk.CTkFont(size=26),
            fg_color=C_ORANGE,
            corner_radius=10,
            width=40,
            height=40,
        )
        logo.pack(pady=(14, 20))

        icons = [
            ("💬", "Chat", None),
            ("📦", "Instalar paquete", self._show_package_installer),
            ("🗂️", "Abrir archivos", lambda: self._send_text("abrir el explorador de archivos")),
            ("🕒", "Ver historial", self._show_memory_summary),
            ("📊", "Estado del sistema", lambda: self._send_text("muéstrame el estado del sistema")),
        ]
        for i, (icon, tip, cmd) in enumerate(icons):
            btn = SidebarIcon(self.sidebar, icon, tip, active=(i == 0), command=cmd)
            btn.pack(pady=4)

        # Separador
        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=C_BORDER)
        sep.pack(fill="x", padx=10, pady=12)

        # Botón limpiar memoria
        SidebarIcon(self.sidebar, "🗑️", "Limpiar memoria", command=self._confirm_clear_memory).pack(pady=4)

        # Ajustes al fondo
        SidebarIcon(self.sidebar, "⚙️", "Ajustes").pack(side="bottom", pady=14)

    # ─────────────────────────────────────────────────────────────────────────
    # HEADER
    # ─────────────────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.center_col, height=68, corner_radius=0,
                              fg_color=C_PANEL, border_width=1, border_color=C_BORDER)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Izquierda: título y subtítulo
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=18)

        ctk.CTkLabel(
            left,
            text="Agente Autónomo — Ubuntu",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text="control del sistema por voz e IA",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=C_MUTED,
        ).pack(anchor="w")

        # Derecha: modelo, estado, voz, limpiar
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=14)

        # Badge modelo activo
        model_name = self.agent.model_name if self.agent else "sin API key"
        self.model_badge = ctk.CTkLabel(
            right,
            text=f"⚡ {model_name}",
            font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
            text_color=C_ORANGE,
            fg_color=C_ORANGE_D,
            corner_radius=6,
            padx=8, pady=2,
        )
        self.model_badge.pack(side="left", padx=4)

        # Badge estado
        self.status_dot = ctk.CTkLabel(
            right,
            text="● Listo",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C_GREEN,
            fg_color=C_GREEN_D,
            corner_radius=20,
            padx=12, pady=3,
        )
        self.status_dot.pack(side="left", padx=6)

        # Botón voz
        self.voice_btn = ctk.CTkButton(
            right,
            text="● Voz activa",
            width=100,
            height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=C_ORANGE,
            hover_color=C_ORANGE_H,
            text_color="#fff",
            corner_radius=20,
            command=self._toggle_speaker,
        )
        self.voice_btn.pack(side="left", padx=6)

        # Botón limpiar sesión
        ctk.CTkButton(
            right,
            text="Limpiar sesión",
            width=100,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color=C_CARD,
            hover_color=C_BORDER,
            text_color=C_MUTED2,
            corner_radius=20,
            command=self._clear_chat,
        ).pack(side="left", padx=6)

    # ─────────────────────────────────────────────────────────────────────────
    # CHIPS DE ACCIONES RÁPIDAS
    # ─────────────────────────────────────────────────────────────────────────

    def _build_chips_bar(self) -> None:
        bar = ctk.CTkFrame(self.center_col, height=40, corner_radius=0,
                           fg_color=C_BG)
        bar.pack(fill="x", padx=16, pady=(8, 0))

        chips = [
            ("apt update",       self._show_update_runner),
            ("estado sistema",   "muéstrame el estado del sistema"),
            ("ver logs",         "muéstrame los últimos logs del sistema: journalctl -n 50 --no-pager"),
            ("procesos activos", self._show_process_viewer),
            ("servicios",        "muestra el estado de los servicios systemd más importantes: systemctl list-units --type=service --state=running"),
            ("abrir terminal",   "abre la terminal"),
            ("tienda de apps",   "abrir la tienda de apps"),
        ]

        for label, action in chips:
            command = action if callable(action) else (lambda p=action: self._send_text(p))
            ctk.CTkButton(
                bar,
                text=label,
                height=28,
                font=ctk.CTkFont(family="Courier", size=10),
                fg_color=C_CARD,
                hover_color=C_BORDER,
                text_color=C_MUTED2,
                border_width=1,
                border_color=C_BORDER,
                corner_radius=6,
                command=command,
            ).pack(side="left", padx=3)

    # ─────────────────────────────────────────────────────────────────────────
    # ÁREA DE CHAT
    # ─────────────────────────────────────────────────────────────────────────

    def _build_chat_area(self) -> None:
        self.chat_scroll = ctk.CTkScrollableFrame(
            self.center_col,
            fg_color=C_BG,
            corner_radius=0,
            border_width=0,
        )
        self.chat_scroll.pack(fill="both", expand=True, padx=16, pady=8)
        self.chat_scroll.columnconfigure(0, weight=1)

    def _add_bubble(self, sender: str, text: str, source: str = "SISTEMA") -> None:
        """Agrega una burbuja de mensaje al chat con diseño moderno."""
        time_str = datetime.now().strftime("%H:%M")
        is_user = (sender == "user")

        if is_user:
            self._msg_count += 1
            self._update_footer_counter()

        # Fila exterior
        row = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 10))

        if is_user:
            # ── Burbuja usuario (derecha) ──
            bubble = ctk.CTkFrame(
                row,
                fg_color=C_BLUE_D,
                border_width=1,
                border_color=C_BLUE,
                corner_radius=12,
            )
            bubble.pack(side="right", padx=(100, 4))

            top = ctk.CTkFrame(bubble, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(8, 0))

            ctk.CTkLabel(top, text="Tú", font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C_BLUE).pack(side="left")
            ctk.CTkLabel(top, text=time_str, font=ctk.CTkFont(size=10),
                         text_color=C_MUTED).pack(side="right")

            ctk.CTkLabel(
                bubble, text=text,
                font=ctk.CTkFont(size=13),
                text_color=C_TEXT,
                justify="left",
                wraplength=560,
                anchor="w",
            ).pack(anchor="w", padx=14, pady=(4, 12))

        else:
            # ── Burbuja asistente (izquierda) ──
            bubble = ctk.CTkFrame(
                row,
                fg_color=C_CARD,
                border_width=1,
                border_color=C_BORDER,
                corner_radius=12,
            )
            bubble.pack(side="left", padx=(4, 100))

            top = ctk.CTkFrame(bubble, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(8, 0))

            ctk.CTkLabel(top, text="Asistente Linux",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C_TEXT).pack(side="left")

            badge_styles = {
                "LOCAL": (C_GREEN, C_GREEN_D),
                "IA": (C_ORANGE, C_ORANGE_D),
                "SISTEMA": (C_MUTED2, C_BORDER),
            }
            badge_text = source if source in badge_styles else "SISTEMA"
            badge_color, badge_bg = badge_styles[badge_text]
            ctk.CTkLabel(
                top,
                text=badge_text,
                font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
                text_color=badge_color,
                fg_color=badge_bg,
                corner_radius=4,
                padx=6, pady=1,
            ).pack(side="left", padx=6)

            ctk.CTkLabel(top, text=time_str, font=ctk.CTkFont(size=10),
                         text_color=C_MUTED).pack(side="right")

            # Botón copiar al portapapeles
            copy_btn = ctk.CTkButton(
                top,
                text="📋",
                width=24,
                height=20,
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                hover_color=C_BORDER,
                corner_radius=4,
                command=lambda t=text: self._copy_to_clipboard(t),
            )
            copy_btn.pack(side="right", padx=(0, 4))

            # Advertencia si contiene acciones al sistema
            action_kws = [
                "instalando", "actualizando", "desinstalando", "eliminando",
                "se instalara", "se instalará", "se eliminara", "se eliminará",
            ]
            if any(kw.lower() in text.lower() for kw in action_kws):
                warn = ctk.CTkFrame(bubble, fg_color="#2a2200", corner_radius=6)
                warn.pack(fill="x", padx=14, pady=(6, 0))
                ctk.CTkLabel(
                    warn,
                    text="⚠  Esta acción modifica el sistema y requiere confirmación.",
                    font=ctk.CTkFont(size=10),
                    text_color=C_YELLOW,
                    justify="left",
                    wraplength=520,
                ).pack(anchor="w", padx=10, pady=4)

            ctk.CTkLabel(
                bubble, text=text,
                font=ctk.CTkFont(size=13),
                text_color=C_TEXT,
                justify="left",
                wraplength=560,
                anchor="w",
            ).pack(anchor="w", padx=14, pady=(4, 12))

        # Scroll automático al final
        self.update_idletasks()
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _add_thinking_indicator(self) -> None:
        """Agrega una burbuja animada de 'Escribiendo...' mientras el agente procesa."""
        if self._thinking_label is not None:
            return
        row = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 6))
        row._is_thinking = True  # marcador para identificar y eliminar

        bubble = ctk.CTkFrame(row, fg_color=C_CARD, border_width=1,
                               border_color=C_BORDER, corner_radius=12)
        bubble.pack(side="left", padx=(4, 100))

        self._thinking_label = ctk.CTkLabel(
            bubble,
            text="✦ Escribiendo...",
            font=ctk.CTkFont(size=12),
            text_color=C_MUTED2,
        )
        self._thinking_label.pack(padx=14, pady=10)
        self._thinking_row = row

        self.update_idletasks()
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _remove_thinking_indicator(self) -> None:
        """Elimina la burbuja de 'Escribiendo...'."""
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
            self.center_col, height=24, fg_color=C_BG
        )
        self.voice_indicator.pack(fill="x", padx=16)

        self.voice_label = ctk.CTkLabel(
            self.voice_indicator,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=C_ORANGE,
        )
        self.voice_label.pack(side="left")

        # Fila de entrada
        bar = ctk.CTkFrame(
            self.center_col,
            fg_color=C_CARD,
            corner_radius=12,
            border_width=1,
            border_color=C_BORDER,
        )
        bar.pack(fill="x", padx=16, pady=(2, 4))

        self.input_entry = ctk.CTkEntry(
            bar,
            placeholder_text="Escribe una instrucción o pulsa el micrófono...",
            height=44,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=0,
            text_color=C_TEXT,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(14, 4), pady=6)
        self.input_entry.bind("<Return>", lambda e: self._on_send())

        # Botón micrófono
        self.mic_btn = ctk.CTkButton(
            bar,
            text="🎤",
            width=44,
            height=40,
            font=ctk.CTkFont(size=16),
            fg_color=C_CARD,
            hover_color=C_BORDER,
            corner_radius=8,
            command=self._toggle_mic,
        )
        self.mic_btn.pack(side="left", padx=4, pady=6)

        # Botón enviar
        self.send_btn = ctk.CTkButton(
            bar,
            text="Enviar →",
            width=90,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=C_ORANGE,
            hover_color=C_ORANGE_H,
            text_color="#fff",
            corner_radius=8,
            command=self._on_send,
        )
        self.send_btn.pack(side="left", padx=(4, 10), pady=6)

    # ─────────────────────────────────────────────────────────────────────────
    # FOOTER
    # ─────────────────────────────────────────────────────────────────────────

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self.center_col, height=26, corner_radius=0,
                              fg_color=C_PANEL, border_width=0)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        # Contador de mensajes en sesión
        self.footer_msgs = ctk.CTkLabel(
            footer,
            text="Sesión: 0 mensajes",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=C_MUTED,
        )
        self.footer_msgs.pack(side="left", padx=14)

        # Badge memoria persistente
        mem_count = get_memory_count()
        mem_text = f"💾 Memoria: {mem_count // 2} intercambios guardados" if mem_count else "💾 Sin memoria previa"
        self.footer_mem = ctk.CTkLabel(
            footer,
            text=mem_text,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=C_PURPLE,
        )
        self.footer_mem.pack(side="right", padx=14)

    def _update_footer_counter(self) -> None:
        try:
            self.footer_msgs.configure(text=f"Sesión: {self._msg_count} mensajes")
        except Exception:
            pass

    def _update_footer_memory(self) -> None:
        try:
            mem_count = get_memory_count()
            mem_text = f"💾 Memoria: {mem_count // 2} intercambios guardados" if mem_count else "💾 Sin memoria previa"
            self.footer_mem.configure(text=mem_text)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # PANEL DERECHO — ESTADO DEL SISTEMA
    # ─────────────────────────────────────────────────────────────────────────

    def _build_system_panel(self) -> None:
        # Título
        ctk.CTkLabel(
            self.right_panel,
            text="ESTADO DEL SISTEMA",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=C_MUTED,
        ).pack(anchor="w", padx=14, pady=(16, 8))

        # Métricas con barra de progreso
        self._cpu_bar   = self._metric_row("CPU",     "%",   C_RED)
        self._mem_bar   = self._metric_row("Memoria", "GB",  "#a855f7")
        self._disk_bar  = self._metric_row("Disco",   "GB",  C_GREEN)

        sep = ctk.CTkFrame(self.right_panel, height=1, fg_color=C_BORDER)
        sep.pack(fill="x", padx=14, pady=10)

        # Métricas de texto simples
        self._uptime_lbl  = self._info_row("Tiempo activo")
        self._procs_lbl   = self._info_row("Procesos")
        self._net_lbl     = self._info_row("Red recibida")
        self._pkgs_lbl    = self._info_row("Paquetes apt")

        sep2 = ctk.CTkFrame(self.right_panel, height=1, fg_color=C_BORDER)
        sep2.pack(fill="x", padx=14, pady=10)

        # Kernel card
        kernel_card = ctk.CTkFrame(self.right_panel, fg_color=C_CARD,
                                   corner_radius=8, border_width=1, border_color=C_BORDER)
        kernel_card.pack(fill="x", padx=14, pady=(0, 4))

        ctk.CTkLabel(
            kernel_card,
            text="KERNEL",
            font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
            text_color=C_MUTED,
        ).pack(anchor="w", padx=10, pady=(8, 0))

        self._kernel_lbl = ctk.CTkLabel(
            kernel_card,
            text="—",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=C_ORANGE,
            justify="left",
        )
        self._kernel_lbl.pack(anchor="w", padx=10, pady=(2, 8))

        # Separador
        sep3 = ctk.CTkFrame(self.right_panel, height=1, fg_color=C_BORDER)
        sep3.pack(fill="x", padx=14, pady=8)

        # Acciones rápidas del panel
        ctk.CTkLabel(
            self.right_panel,
            text="ACCIONES RÁPIDAS",
            font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
            text_color=C_MUTED,
        ).pack(anchor="w", padx=14, pady=(0, 4))

        quick_actions = [
            ("🔄 Actualizar sistema", self._show_update_runner),
            ("⚡ Revisar rendimiento", "mi máquina está lenta"),
            ("📋 Ver procesos", self._show_process_viewer),
            ("🌐 Ver red", self._show_network_viewer),
            ("📁 Mi directorio", "muéstrame el contenido de mi directorio home: ls -la ~"),
        ]
        for label, action in quick_actions:
            command = action if callable(action) else (lambda p=action: self._send_text(p))
            ctk.CTkButton(
                self.right_panel,
                text=label,
                height=28,
                font=ctk.CTkFont(size=11),
                fg_color=C_CARD,
                hover_color=C_BORDER,
                text_color=C_MUTED2,
                border_width=1,
                border_color=C_BORDER,
                corner_radius=6,
                anchor="w",
                command=command,
            ).pack(fill="x", padx=14, pady=2)

    def _metric_row(self, label: str, unit: str, color: str):
        """Crea una fila con etiqueta, valor y barra de progreso."""
        frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        frame.pack(fill="x", padx=14, pady=2)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(top, text=label, font=ctk.CTkFont(size=12),
                     text_color=C_MUTED2).pack(side="left")
        val_lbl = ctk.CTkLabel(top, text="—", font=ctk.CTkFont(size=11, weight="bold"),
                               text_color=C_TEXT)
        val_lbl.pack(side="right")

        bar = ctk.CTkProgressBar(frame, height=5, corner_radius=3,
                                 fg_color=C_BORDER, progress_color=color)
        bar.pack(fill="x", pady=(3, 0))
        bar.set(0)

        return val_lbl, bar

    def _info_row(self, label: str):
        """Crea una fila clave → valor para métricas de texto."""
        frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        frame.pack(fill="x", padx=14, pady=1)

        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).pack(side="left")
        val = ctk.CTkLabel(frame, text="—", font=ctk.CTkFont(size=11, weight="bold"),
                           text_color=C_TEXT)
        val.pack(side="right")
        return val

    def _update_system_panel(self, s: dict) -> None:
        """Actualiza los valores del panel de sistema desde el hilo principal."""
        if not s:
            return

        # CPU
        cpu_lbl, cpu_bar = self._cpu_bar
        cpu_lbl.configure(text=f"{s['cpu']:.0f}%")
        cpu_bar.set(s["cpu"] / 100)

        # Memoria
        mem_lbl, mem_bar = self._mem_bar
        mem_lbl.configure(text=f"{s['mem_gb']:.1f} / {s['mem_tot']:.0f} GB")
        mem_bar.set(s["mem_pct"] / 100)

        # Disco
        dsk_lbl, dsk_bar = self._disk_bar
        dsk_lbl.configure(text=f"{s['disk_gb']:.0f} / {s['disk_tot']:.0f} GB")
        dsk_bar.set(s["disk_pct"] / 100)

        # Info rows
        self._uptime_lbl.configure(text=s.get("uptime", "—"))
        self._procs_lbl.configure(text=str(s.get("procs", "—")))
        rx = s.get("net_rx", 0)
        self._net_lbl.configure(text=f"↓ {rx:.1f} MB")
        pkgs = s.get("pkgs", 0)
        self._pkgs_lbl.configure(text=f"{pkgs}" if pkgs else "—")

        # Kernel
        self._kernel_lbl.configure(text=f"{s.get('kernel','—')}\nx86_64 · Linux")

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
                stats = _get_system_stats()
                self.after(0, lambda s=stats: self._update_system_panel(s))
                time.sleep(3)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    # ─────────────────────────────────────────────────────────────────────────
    # LÓGICA DE MENSAJES
    # ─────────────────────────────────────────────────────────────────────────

    def _show_welcome(self) -> None:
        mem_count = get_memory_count()
        if self.agent:
            mem_info = f"\n\n💾 Memoria cargada: {mem_count // 2} intercambios de sesiones anteriores." if mem_count else ""
            msg = (
                "Hola. Soy tu agente autónomo para Ubuntu — puedo ejecutar tareas del sistema "
                "directamente (actualizar paquetes, abrir programas, instalar archivos .deb, "
                "leer/escribir archivos, gestionar servicios) y responder dudas técnicas.\n\n"
                "Escribe una instrucción, usa los chips de acceso rápido, "
                "o pulsa el micrófono para hablar." + mem_info
            )
        else:
            msg = (
                "¡Hola! Soy tu asistente de Linux.\n"
                "⚠️  No se detectó una API key válida en tu archivo .env. "
                "Configura GROQ_API_KEY o NVIDIA_API_KEY para habilitar la IA."
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
        self._update_footer_counter()
        self._add_bubble("assistant", "Sesión limpiada. La memoria de sesiones anteriores se conserva. ¿En qué puedo ayudarte?")

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

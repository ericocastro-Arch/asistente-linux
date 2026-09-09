"""Vistas graficas orientadas a usuarios nuevos."""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable, Optional

import customtkinter as ctk
import psutil

from src.core.memory import clear_memory, load_memory, memory_summary
from src.core.storage import log_tool_run
from src.core.tools import build_deb_install_args


PACKAGE_ALIASES = {
    "obs": ("obs-studio", "OBS Studio"),
    "obs studio": ("obs-studio", "OBS Studio"),
    "vs": ("code", "Visual Studio Code"),
    "vs code": ("code", "Visual Studio Code"),
    "visual": ("code", "Visual Studio Code"),
    "visual code": ("code", "Visual Studio Code"),
    "visual studio": ("code", "Visual Studio Code"),
    "chrome": ("google-chrome-stable", "Google Chrome"),
    "google chrome": ("google-chrome-stable", "Google Chrome"),
    "visual studio code": ("code", "Visual Studio Code"),
    "vscode": ("code", "Visual Studio Code"),
    "spotify": ("spotify-client", "Spotify"),
}

SNAP_ALIASES = {
    "trilium": ("trilium-notes", "Trilium Notes"),
    "trilium notes": ("trilium-notes", "Trilium Notes"),
    "trilium-notes": ("trilium-notes", "Trilium Notes"),
}

FLATPAK_ALIASES = {
    "trilium": ("org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium notes": ("org.triliumnotes.Trilium", "Trilium Notes"),
    "trilium-notes": ("org.triliumnotes.Trilium", "Trilium Notes"),
    "com.github.zadam.trilium": ("com.github.zadam.trilium", "Trilium Notes"),
}

GENERIC_PACKAGE_TERMS = {
    "editor",
    "programa",
    "aplicacion",
    "aplicación",
    "visual",
    "video",
    "audio",
    "musica",
    "música",
    "internet",
    "navegador",
}


def show_history_viewer(app) -> None:
    window = app._make_window("Historial guardado", "820x620")
    _header(window, "Historial guardado", "Conversaciones recordadas entre sesiones. Puedes revisarlas sin llenar el chat.")

    top = ctk.CTkFrame(window, fg_color=app.C_PANEL)
    top.pack(fill="x", padx=16, pady=(0, 10))

    summary_lbl = ctk.CTkLabel(
        top,
        text=memory_summary(),
        text_color=app.C_MUTED2,
        font=ctk.CTkFont(size=12),
        anchor="w",
    )
    summary_lbl.pack(side="left", fill="x", expand=True)

    body = ctk.CTkScrollableFrame(window, fg_color=app.C_PANEL, corner_radius=0)
    body.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    def render_messages():
        for child in body.winfo_children():
            child.destroy()

        messages = load_memory()
        summary_lbl.configure(text=memory_summary())
        if not messages:
            empty = ctk.CTkFrame(body, fg_color=app.C_CARD, border_width=0, corner_radius=8)
            empty.pack(fill="x", pady=4)
            ctk.CTkLabel(
                empty,
                text="Todavia no hay conversaciones guardadas.",
                text_color=app.C_TEXT,
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(anchor="w", padx=14, pady=(12, 2))
            ctk.CTkLabel(
                empty,
                text="Cuando hables con el asistente, apareceran aqui los mensajes recordados.",
                text_color=app.C_MUTED2,
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=14, pady=(0, 12))
            return

        for index, message in enumerate(messages, start=1):
            _history_row(app, body, index, message)

    def clear_and_refresh():
        def confirmed():
            clear_memory()
            app._update_footer_memory()
            render_messages()

        confirm_action(
            app,
            "Borrar historial",
            "Se borraran las conversaciones guardadas. La sesion actual seguira abierta.",
            confirmed,
        )

    actions = ctk.CTkFrame(window, fg_color="transparent")
    actions.pack(fill="x", padx=16, pady=(0, 14))
    ctk.CTkButton(actions, text="Actualizar", fg_color=app.C_CARD, hover_color=app.C_BORDER, command=render_messages).pack(side="left", fill="x", expand=True, padx=(0, 6))
    ctk.CTkButton(actions, text="Borrar historial", fg_color=app.C_RED, hover_color="#b91c1c", command=clear_and_refresh).pack(side="left", fill="x", expand=True, padx=(6, 0))

    render_messages()


def show_process_viewer(app) -> None:
    window = app._make_window("Procesos activos", "820x620")
    _header(window, "Procesos y aplicaciones activas", "Mira que aplicaciones consumen mas recursos en este momento.")

    summary = ctk.CTkFrame(window, fg_color=app.C_PANEL)
    summary.pack(fill="x", padx=16, pady=12)
    cpu_lbl, cpu_bar = _visual_metric(app, summary, "CPU total", app.C_RED)
    mem_lbl, mem_bar = _visual_metric(app, summary, "Memoria total", app.C_PURPLE)

    list_frame = ctk.CTkScrollableFrame(window, fg_color=app.C_PANEL, corner_radius=0)
    list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
    rows = [_create_process_row(app, list_frame) for _ in range(14)]

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
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            processes.sort(key=lambda p: (p.get("cpu_percent") or 0, p.get("memory_percent") or 0), reverse=True)

            for index, widgets in enumerate(rows):
                _update_process_row(widgets, processes[index] if index < len(processes) else None)
        except Exception as exc:
            app._add_bubble("assistant", f"No pude actualizar la vista de procesos: {exc}")

        if window.winfo_exists():
            window.after(2500, refresh)

    refresh()


def show_network_viewer(app) -> None:
    window = app._make_window("Red e internet", "760x560")
    _header(window, "Red e internet", "Estado de tus conexiones, direcciones IP y trafico de red.")

    totals = ctk.CTkFrame(window, fg_color=app.C_PANEL)
    totals.pack(fill="x", padx=16, pady=(0, 8))
    rx_lbl, rx_bar = _visual_metric(app, totals, "Descarga", app.C_GREEN)
    tx_lbl, tx_bar = _visual_metric(app, totals, "Subida", app.C_BLUE)

    interfaces = ctk.CTkScrollableFrame(window, fg_color=app.C_PANEL, corner_radius=0)
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

            rx_lbl.configure(text=f"{app._format_bytes(rx_speed)}/s")
            tx_lbl.configure(text=f"{app._format_bytes(tx_speed)}/s")
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
                    network_rows[name] = _create_network_row(app, interfaces)
                _update_network_row(app, network_rows[name], name, addrs.get(name, []), stats.get(name), io.get(name))
        except Exception as exc:
            app._add_bubble("assistant", f"No pude actualizar la vista de red: {exc}")

        if window.winfo_exists():
            window.after(2500, refresh)

    refresh()


def show_package_installer(app, package_name: str = "", deb_mode: bool = False) -> None:
    window = app._make_window("Instalar paquete", "760x560")
    _header(window, "Instalar programa", "Busca el paquete antes de instalar para confirmar que es el correcto.")

    form = ctk.CTkFrame(window, fg_color=app.C_CARD, border_width=0, corner_radius=8)
    form.pack(fill="x", padx=16, pady=(0, 10))
    entry = ctk.CTkEntry(form, placeholder_text="Ejemplo: vlc, gimp, htop", height=38, text_color=app.C_TEXT)
    entry.pack(side="left", fill="x", expand=True, padx=12, pady=12)
    if package_name:
        entry.insert(0, package_name)

    progress = ctk.CTkProgressBar(window, height=10, fg_color=app.C_BORDER, progress_color=app.C_ORANGE)
    progress.pack(fill="x", padx=16, pady=(4, 8))
    progress.set(0)

    log = ctk.CTkTextbox(window, fg_color=app.C_BG, text_color=app.C_TEXT, border_width=0, corner_radius=8)
    log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
    _append_log(log, "Listo para instalar. Si no sabes el nombre exacto, usa Buscar primero.")

    buttons = ctk.CTkFrame(form, fg_color="transparent")
    buttons.pack(side="right", padx=(0, 12))
    state = {"busy": False, "deb_path": ""}

    def append(line: str):
        _append_log(log, line)

    def clear_log(message: str = ""):
        log.configure(state="normal")
        log.delete("1.0", "end")
        if message:
            log.insert("end", message + "\n")
        log.configure(state="disabled")

    def package() -> str:
        return _parse_install_request(entry.get().strip())[1]

    def requested_source() -> Optional[str]:
        return _parse_install_request(entry.get().strip())[0]

    def set_busy(value: bool):
        state["busy"] = value
        new_state = "disabled" if value else "normal"
        entry.configure(state=new_state)
        search_btn.configure(state=new_state)
        install_btn.configure(state=new_state)
        deb_btn.configure(state=new_state)

    def choose_deb():
        if state["busy"]:
            return
        initial_dir = Path.home() / "Descargas"
        if not initial_dir.is_dir():
            initial_dir = Path.home() / "Downloads"
        selected = filedialog.askopenfilename(
            parent=window,
            title="Seleccionar paquete Debian",
            initialdir=str(initial_dir if initial_dir.is_dir() else Path.home()),
            filetypes=[("Paquetes Debian", "*.deb")],
        )
        if not selected:
            return

        try:
            install_args = build_deb_install_args(selected)
        except ValueError as exc:
            clear_log(str(exc))
            return

        if not shutil.which("dpkg-deb"):
            clear_log("No encontre dpkg-deb para validar el paquete seleccionado.")
            return

        clear_log(f"Validando {Path(selected).name}...")
        set_busy(True)

        def inspected(code: int, output: str):
            set_busy(False)
            if code != 0:
                clear_log("El archivo no parece ser un paquete Debian valido.\n")
                append(output.strip() or "dpkg-deb no pudo leer sus metadatos.")
                return

            clear_log("Paquete Debian validado:\n")
            append(output.strip())

            def confirmed():
                if not shutil.which("pkexec"):
                    append("No encontre pkexec; no puedo solicitar permisos graficamente.")
                    return
                set_busy(True)
                append("\nInstalando el paquete. Ubuntu puede pedir tu contrasena...")

                def installed(exit_code: int, install_output: str):
                    set_busy(False)
                    if exit_code == 0:
                        clear_log(f"{Path(selected).name} se instalo correctamente.")
                    else:
                        append(install_output.strip() or f"La instalacion termino con codigo {exit_code}.")

                run_command_in_view(app, install_args, progress, append, on_done=installed)

            confirm_action(
                app,
                "Confirmar paquete .deb",
                f"Se instalara '{Path(selected).name}'. Ubuntu solicitara permisos de administrador.",
                confirmed,
            )

        run_command_in_view(
            app,
            ["dpkg-deb", "--show", selected],
            progress,
            append,
            limit_lines=20,
            on_done=inspected,
        )

    def search():
        if state["busy"]:
            return
        source = requested_source()
        pkg = package()
        if not pkg:
            clear_log()
            append("Escribe primero que programa quieres buscar.")
            return

        if source:
            clear_log(f"Buscando '{pkg}' por {source}...")
            set_busy(True)
            _search_source(app, source, pkg, progress, append, set_busy, clear_log)
            return

        alias = _package_alias(pkg)
        if alias:
            real_pkg, friendly_name = alias
            clear_log(
                f"'{pkg}' parece referirse a {friendly_name}.\n"
                f"Nombre tecnico recomendado: {real_pkg}\n\n"
                "Buscando ese paquete..."
            )
            pkg = real_pkg
            entry.delete(0, "end")
            entry.insert(0, real_pkg)
        else:
            clear_log(f"Buscando paquetes relacionados con '{pkg}'...")

        set_busy(True)

        def done(code: int, output: str):
            set_busy(False)
            if output.strip():
                clear_log("Resultados encontrados:\n")
                append(_friendly_search_results(output, pkg))
            else:
                clear_log(f"No encontre '{pkg}' en los repositorios apt.\n")
                append("Buscando alternativas por nombre comun...")
                _search_other_sources(app, pkg, progress, append, set_busy)

        run_command_in_view(app, ["apt-cache", "search", pkg], progress, append, limit_lines=None, on_done=done)

    def install():
        if state["busy"]:
            return
        source = requested_source()
        pkg = package()
        if not pkg:
            clear_log()
            append("Escribe primero que programa quieres instalar.")
            return

        if source:
            _install_from_source(app, source, pkg, progress, append, clear_log, set_busy)
            return

        snap_alias = _snap_alias(pkg)
        alias = _package_alias(pkg)
        if alias:
            real_pkg, friendly_name = alias
            clear_log(
                f"'{pkg}' es un nombre comun para {friendly_name}.\n"
                f"Voy a usar el paquete correcto: {real_pkg}"
            )
            pkg = real_pkg
            entry.delete(0, "end")
            entry.insert(0, real_pkg)
        elif snap_alias:
            real_pkg, friendly_name = snap_alias
            clear_log(
                f"'{pkg}' parece referirse a {friendly_name}.\n"
                f"No suele instalarse desde apt; lo intentare con Snap: {real_pkg}"
            )
            pkg = real_pkg
            entry.delete(0, "end")
            entry.insert(0, real_pkg)
        elif _is_generic_package_term(pkg):
            clear_log(
                f"'{pkg}' es una palabra muy general, no un nombre seguro de paquete.\n\n"
                "Usa Buscar para ver opciones, o escribe un nombre mas especifico como:\n"
                "• code para Visual Studio Code\n"
                "• obs-studio para OBS Studio\n"
                "• vlc para reproductor de video\n"
                "• gimp para editor de imagenes"
            )
            return
        elif not re.fullmatch(r"[A-Za-z0-9.+_-]+", pkg):
            clear_log(
                f"'{pkg}' no parece ser un nombre tecnico de paquete.\n\n"
                "Prueba con el nombre comun completo, por ejemplo:\n"
                "• visual code\n"
                "• obs\n"
                "• chrome\n\n"
                "O usa Buscar para ver opciones."
            )
            return

        def confirmed():
            clear_log(f"Verificando si '{pkg}' existe en los repositorios...")
            set_busy(True)

            def policy_done(code: int, output: str):
                if _has_install_candidate(output):
                    if not shutil.which("pkexec"):
                        set_busy(False)
                        append("No encontre pkexec. Abre una terminal y usa: sudo apt install " + pkg)
                        return
                    clear_log(f"Instalando '{pkg}'...\nUbuntu puede pedir tu contraseña.")

                    def install_done(_code: int, install_output: str):
                        set_busy(False)
                        if _code == 0:
                            clear_log(f"'{pkg}' se instalo correctamente.")
                        else:
                            append(_friendly_apt_error(install_output, pkg))

                    run_command_in_view(app, ["pkexec", "apt", "install", "-y", pkg], progress, append, on_done=install_done)
                    return

                snap_info = _snap_alias(pkg)
                if snap_info and shutil.which("snap"):
                    real_pkg, friendly_name = snap_info
                    clear_log(
                        f"No encontre '{pkg}' en apt, pero {friendly_name} esta identificado como paquete Snap.\n"
                        "Instalando con Snap..."
                    )

                    def snap_done(_code: int, install_output: str):
                        set_busy(False)
                        if _code == 0:
                            clear_log(f"'{real_pkg}' se instalo correctamente con Snap.")
                        else:
                            append(_friendly_snap_error(install_output, real_pkg))

                    run_command_in_view(app, ["pkexec", "snap", "install", real_pkg], progress, append, on_done=snap_done)
                    return

                clear_log(f"'{pkg}' no parece ser el nombre correcto del paquete.\n")

                def search_done(_code: int, search_output: str):
                    set_busy(False)
                    suggestions = _friendly_search_results(search_output, pkg)
                    append("Sugerencias disponibles:")
                    if suggestions.strip() and f"No encontre resultados para '{pkg}'." not in suggestions:
                        append(suggestions)
                        return
                    append("No encontre alternativas en apt.")
                    _search_other_sources(app, pkg, progress, append, set_busy)

                run_command_in_view(app, ["apt-cache", "search", pkg], progress, append, limit_lines=None, on_done=search_done)

            run_command_in_view(app, ["apt-cache", "policy", pkg], progress, append, limit_lines=None, on_done=policy_done)

        confirm_action(
            app,
            "Confirmar instalacion",
            f"Se instalara el paquete '{pkg}'. Ubuntu puede pedir tu contraseña.",
            confirmed,
        )

    search_btn = ctk.CTkButton(buttons, text="Buscar", width=82, fg_color=app.C_CARD, hover_color=app.C_BORDER, command=search)
    search_btn.pack(side="left", padx=3)
    install_btn = ctk.CTkButton(buttons, text="Instalar", width=90, fg_color=app.C_ORANGE, hover_color=app.C_ORANGE_H, command=install)
    install_btn.pack(side="left", padx=3)
    deb_btn = ctk.CTkButton(buttons, text="Archivo .deb", width=96, fg_color=app.C_CARD, hover_color=app.C_BORDER, command=choose_deb)
    deb_btn.pack(side="left", padx=3)

    if deb_mode or package_name.lower().endswith(".deb"):
        window.after(100, choose_deb)


def show_update_runner(app) -> None:
    window = app._make_window("Actualizar sistema", "760x520")
    _header(window, "Actualizar sistema", "Instala actualizaciones disponibles usando las herramientas graficas de Ubuntu cuando sea posible.")

    progress = ctk.CTkProgressBar(window, height=10, fg_color=app.C_BORDER, progress_color=app.C_ORANGE)
    progress.pack(fill="x", padx=16, pady=(4, 8))
    progress.set(0)

    log = ctk.CTkTextbox(window, fg_color=app.C_BG, text_color=app.C_TEXT, border_width=0, corner_radius=8)
    log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
    _append_log(log, "Pulsa el boton para iniciar la actualizacion.")

    def append(line: str):
        _append_log(log, line)

    def start():
        def confirmed():
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
            app._run_command_in_view(["pkexec", "bash", "-lc", "apt update && apt upgrade -y"], progress, append)

        confirm_action(
            app,
            "Confirmar actualizacion",
            "Se buscaran e instalaran actualizaciones del sistema. Ubuntu puede pedir tu contraseña.",
            confirmed,
        )

    ctk.CTkButton(window, text="Iniciar actualizacion", height=36, fg_color=app.C_ORANGE, hover_color=app.C_ORANGE_H, command=start).pack(fill="x", padx=16, pady=(0, 14))


def confirm_action(app, title: str, message: str, on_confirm: Callable[[], None]) -> None:
    dialog = ctk.CTkToplevel(app)
    dialog.title(title)
    dialog.geometry("420x190")
    dialog.resizable(False, False)
    dialog.configure(fg_color=app.C_PANEL)
    dialog.grab_set()

    ctk.CTkLabel(dialog, text=title, font=ctk.CTkFont(size=16, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=20, pady=(20, 6))
    ctk.CTkLabel(dialog, text=message, font=ctk.CTkFont(size=12), text_color=app.C_MUTED2, justify="left", wraplength=370).pack(anchor="w", padx=20)

    buttons = ctk.CTkFrame(dialog, fg_color="transparent")
    buttons.pack(fill="x", padx=20, pady=(18, 0))

    ctk.CTkButton(buttons, text="Cancelar", fg_color=app.C_CARD, hover_color=app.C_BORDER, text_color=app.C_MUTED2, command=dialog.destroy).pack(side="left", fill="x", expand=True, padx=(0, 6))

    def accept():
        dialog.destroy()
        on_confirm()

    ctk.CTkButton(buttons, text="Continuar", fg_color=app.C_ORANGE, hover_color=app.C_ORANGE_H, command=accept).pack(side="left", fill="x", expand=True, padx=(6, 0))


def run_command_in_view(
    app,
    args: list[str],
    progress,
    append,
    limit_lines: Optional[int] = None,
    on_done: Optional[Callable[[int, str], None]] = None,
) -> None:
    def worker():
        app.after(0, lambda: app._set_status("● Ejecutando...", app.C_YELLOW, "#2a2200"))
        app.after(0, lambda: progress.start())
        output_lines = []
        code = 1
        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            count = 0
            if proc.stdout:
                for line in proc.stdout:
                    output_lines.append(line)
                    count += 1
                    if limit_lines is None or count <= limit_lines:
                        app.after(0, lambda l=line.rstrip(): append(l))
            code = proc.wait()
            if on_done is None:
                final = "Terminado correctamente." if code == 0 else f"El comando termino con codigo {code}."
                app.after(0, lambda: append(final))
        except Exception as exc:
            output_lines.append(str(exc))
            app.after(0, lambda: append(f"Error: {exc}"))
        finally:
            combined_output = "".join(output_lines)
            log_tool_run(
                "visual_command",
                " ".join(args),
                combined_output,
                "ok" if code == 0 else "error",
                stdout=combined_output,
                exit_code=code,
            )
            if on_done is not None:
                app.after(0, lambda c=code, o=combined_output: on_done(c, o))
            app.after(0, progress.stop)
            app.after(0, lambda: progress.set(1))
            app.after(0, lambda: app._set_status("● Listo", app.C_GREEN, app.C_GREEN_D))

    threading.Thread(target=worker, daemon=True).start()


def _header(parent, title: str, subtitle: str) -> None:
    ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color="#e2e8f0").pack(anchor="w", padx=18, pady=(16, 2))
    ctk.CTkLabel(parent, text=subtitle, font=ctk.CTkFont(size=12), text_color="#94a3b8", wraplength=680, justify="left").pack(anchor="w", padx=18, pady=(0, 12))


def _history_row(app, parent, index: int, message: dict[str, Any]) -> None:
    role = message.get("role", "")
    is_user = role == "user"
    title = "Usuario" if is_user else "Asistente"
    color = app.C_BLUE if is_user else app.C_ORANGE
    content = str(message.get("content", "")).strip() or "(mensaje vacío)"
    content = content[:1200] + "\n..." if len(content) > 1200 else content

    row = ctk.CTkFrame(parent, fg_color=app.C_CARD, border_width=0, corner_radius=8)
    row.pack(fill="x", pady=4)

    head = ctk.CTkFrame(row, fg_color="transparent")
    head.pack(fill="x", padx=14, pady=(10, 2))
    ctk.CTkLabel(head, text=f"{index}. {title}", text_color=color, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

    def copy():
        app.clipboard_clear()
        app.clipboard_append(content)
        app.update()

    ctk.CTkButton(head, text="Copiar", width=64, height=24, fg_color="transparent", hover_color=app.C_BORDER, text_color=app.C_MUTED2, command=copy).pack(side="right")
    ctk.CTkLabel(row, text=content, text_color=app.C_TEXT, font=ctk.CTkFont(size=12), justify="left", wraplength=720).pack(anchor="w", padx=14, pady=(4, 12))


def _visual_metric(app, parent, label: str, color: str):
    frame = ctk.CTkFrame(parent, fg_color=app.C_CARD, border_width=0, corner_radius=8)
    frame.pack(side="left", fill="x", expand=True, padx=4)
    top = ctk.CTkFrame(frame, fg_color="transparent")
    top.pack(fill="x", padx=12, pady=(10, 4))
    ctk.CTkLabel(top, text=label, text_color=app.C_MUTED2, font=ctk.CTkFont(size=12)).pack(side="left")
    value = ctk.CTkLabel(top, text="—", text_color=app.C_TEXT, font=ctk.CTkFont(size=16, weight="bold"))
    value.pack(side="right")
    bar = ctk.CTkProgressBar(frame, height=8, fg_color=app.C_BORDER, progress_color=color)
    bar.pack(fill="x", padx=12, pady=(0, 12))
    bar.set(0)
    return value, bar


def _create_process_row(app, parent) -> dict[str, Any]:
    row = ctk.CTkFrame(parent, fg_color=app.C_CARD, border_width=0, corner_radius=8)
    row.pack(fill="x", pady=4)
    top = ctk.CTkFrame(row, fg_color="transparent")
    top.pack(fill="x", padx=12, pady=(8, 2))
    name_lbl = ctk.CTkLabel(top, text="—", text_color=app.C_TEXT, font=ctk.CTkFont(size=13, weight="bold"))
    name_lbl.pack(side="left")
    pid_lbl = ctk.CTkLabel(top, text="PID —", text_color=app.C_MUTED, font=ctk.CTkFont(family="Courier", size=10))
    pid_lbl.pack(side="right")
    bars = ctk.CTkFrame(row, fg_color="transparent")
    bars.pack(fill="x", padx=12, pady=(2, 10))
    return {"name": name_lbl, "pid": pid_lbl, "cpu": _small_bar(app, bars, "CPU", app.C_RED), "mem": _small_bar(app, bars, "RAM", app.C_PURPLE)}


def _update_process_row(widgets: dict[str, Any], proc: Optional[dict]) -> None:
    if not proc:
        widgets["name"].configure(text="—")
        widgets["pid"].configure(text="PID —")
        _update_small_bar(widgets["cpu"], 0)
        _update_small_bar(widgets["mem"], 0)
        return
    widgets["name"].configure(text=(proc.get("name") or "Proceso sin nombre")[:32])
    widgets["pid"].configure(text=f"PID {proc.get('pid', '—')}")
    _update_small_bar(widgets["cpu"], float(proc.get("cpu_percent") or 0))
    _update_small_bar(widgets["mem"], float(proc.get("memory_percent") or 0))


def _small_bar(app, parent, label: str, color: str) -> dict[str, Any]:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", pady=1)
    ctk.CTkLabel(frame, text=label, width=38, text_color=app.C_MUTED2, font=ctk.CTkFont(size=10)).pack(side="left")
    bar = ctk.CTkProgressBar(frame, height=6, fg_color=app.C_BORDER, progress_color=color)
    bar.pack(side="left", fill="x", expand=True, padx=6)
    value = ctk.CTkLabel(frame, text="0.0%", width=52, text_color=app.C_TEXT, font=ctk.CTkFont(size=10))
    value.pack(side="right")
    return {"bar": bar, "value": value}


def _update_small_bar(widgets: dict[str, Any], percent: float) -> None:
    widgets["bar"].set(max(0, min(percent, 100)) / 100)
    widgets["value"].configure(text=f"{percent:.1f}%")


def _create_network_row(app, parent) -> dict[str, Any]:
    row = ctk.CTkFrame(parent, fg_color=app.C_CARD, border_width=0, corner_radius=8)
    row.pack(fill="x", pady=4)
    top = ctk.CTkFrame(row, fg_color="transparent")
    top.pack(fill="x", padx=12, pady=(8, 2))
    name_lbl = ctk.CTkLabel(top, text="—", text_color=app.C_TEXT, font=ctk.CTkFont(size=13, weight="bold"))
    name_lbl.pack(side="left")
    status_lbl = ctk.CTkLabel(top, text="—", text_color=app.C_MUTED, font=ctk.CTkFont(size=11, weight="bold"))
    status_lbl.pack(side="right")
    ip_lbl = ctk.CTkLabel(row, text="Sin IP visible", text_color=app.C_MUTED2, font=ctk.CTkFont(size=11))
    ip_lbl.pack(anchor="w", padx=12)
    data_lbl = ctk.CTkLabel(row, text="", text_color=app.C_MUTED, font=ctk.CTkFont(size=10))
    data_lbl.pack(anchor="w", padx=12, pady=(2, 10))
    return {"row": row, "name": name_lbl, "status": status_lbl, "ip": ip_lbl, "data": data_lbl}


def _update_network_row(app, widgets: dict[str, Any], name: str, addrs, stat, counters) -> None:
    is_up = bool(stat and stat.isup)
    widgets["name"].configure(text=name)
    widgets["status"].configure(text="Conectada" if is_up else "Inactiva", text_color=app.C_GREEN if is_up else app.C_MUTED)
    ips = []
    for addr in addrs:
        family = str(getattr(addr, "family", ""))
        if "AF_INET" in family and not addr.address.startswith("127."):
            ips.append(addr.address)
    widgets["ip"].configure(text=", ".join(ips) if ips else "Sin IP visible")
    if counters:
        widgets["data"].configure(text=f"Recibido {app._format_bytes(counters.bytes_recv)} · Enviado {app._format_bytes(counters.bytes_sent)}")


def _append_log(log, line: str) -> None:
    log.configure(state="normal")
    log.insert("end", line + "\n")
    log.see("end")
    log.configure(state="disabled")


def _has_install_candidate(policy_output: str) -> bool:
    for line in policy_output.splitlines():
        text = line.strip().lower()
        if text.startswith("candidato:") or text.startswith("candidate:"):
            value = text.split(":", 1)[1].strip()
            return value not in {"(ninguno)", "(none)", "none", ""}
    return False


def _package_alias(package: str) -> Optional[tuple[str, str]]:
    return PACKAGE_ALIASES.get(package.strip().lower())


def _snap_alias(package: str) -> Optional[tuple[str, str]]:
    return SNAP_ALIASES.get(package.strip().lower())


def _flatpak_alias(package: str) -> Optional[tuple[str, str]]:
    return FLATPAK_ALIASES.get(package.strip().lower())


def _parse_install_request(text: str) -> tuple[Optional[str], str]:
    value = text.strip().lower()
    source_patterns = [
        ("flatpak", r"^(?:por|con|desde|usando|en)?\s*flatpak\s+(.+)$"),
        ("snap", r"^(?:por|con|desde|usando|en)?\s*snap\s+(.+)$"),
        ("apt", r"^(?:por|con|desde|usando|en)?\s*apt\s+(.+)$"),
        ("apt", r"^(?:por|con|desde|usando|en)?\s*apt-get\s+(.+)$"),
    ]
    for source, pattern in source_patterns:
        match = re.match(pattern, value)
        if match:
            return source, match.group(1).strip()
    return None, text.strip()


def _is_generic_package_term(package: str) -> bool:
    return package.strip().lower() in GENERIC_PACKAGE_TERMS


def _friendly_search_results(output: str, query: str, limit: int = 12) -> str:
    lines = []
    for raw in output.splitlines():
        if " - " not in raw:
            continue
        name, desc = raw.split(" - ", 1)
        name = name.strip()
        desc = desc.strip()
        if not name:
            continue
        lines.append(f"• {name}: {desc}")
        if len(lines) >= limit:
            break

    if lines:
        return "\n".join(lines)

    clean = output.strip()
    if clean:
        return "\n".join(clean.splitlines()[:limit])
    return f"No encontre resultados para '{query}'."


def _friendly_snap_results(output: str, query: str, limit: int = 8) -> str:
    lines = []
    for raw in output.splitlines():
        raw = raw.strip()
        if not raw or raw.lower().startswith("name "):
            continue
        parts = re.split(r"\s{2,}", raw)
        if len(parts) >= 2:
            name = parts[0]
            summary = parts[-1]
            lines.append(f"• snap install {name}: {summary}")
        else:
            lines.append(f"• {raw}")
        if len(lines) >= limit:
            break
    return "\n".join(lines) if lines else f"No encontre resultados Snap para '{query}'."


def _friendly_flatpak_results(output: str, query: str, limit: int = 8) -> str:
    lines = []
    for raw in output.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split("\t")
        if len(parts) >= 2:
            lines.append(f"• flatpak install {parts[1]}: {parts[0]}")
        else:
            lines.append(f"• {raw}")
        if len(lines) >= limit:
            break
    return "\n".join(lines) if lines else f"No encontre resultados Flatpak para '{query}'."


def _search_source(
    app,
    source: str,
    query: str,
    progress,
    append,
    set_busy: Callable[[bool], None],
    clear_log: Callable[[str], None],
) -> None:
    if source == "apt":
        def apt_done(_code: int, output: str):
            set_busy(False)
            if output.strip():
                clear_log("Resultados encontrados en apt:\n")
                append(_friendly_search_results(output, query))
            else:
                clear_log(f"No encontre '{query}' en apt.")

        run_command_in_view(app, ["apt-cache", "search", query], progress, append, limit_lines=None, on_done=apt_done)
        return

    if source == "snap":
        if not shutil.which("snap"):
            clear_log("Snap no esta instalado o no esta disponible en este sistema.")
            set_busy(False)
            return

        def snap_done(_code: int, output: str):
            set_busy(False)
            clear_log("Resultados encontrados en Snap:\n")
            append(_friendly_snap_results(output, query))

        run_command_in_view(app, ["snap", "find", query], progress, append, limit_lines=None, on_done=snap_done)
        return

    if source == "flatpak":
        alias = _flatpak_alias(query)
        if alias:
            app_id, friendly_name = alias
            set_busy(False)
            clear_log(
                f"Reconoci el programa como {friendly_name}.\n"
                f"ID Flatpak recomendado: {app_id}\n\n"
                "Comando recomendado:\n"
                f"```bash\nflatpak install flathub {app_id}\n```"
            )
            return
        if not shutil.which("flatpak"):
            clear_log("Flatpak no esta instalado o no esta disponible en este sistema.")
            set_busy(False)
            return

        def flatpak_done(_code: int, output: str):
            set_busy(False)
            clear_log("Resultados encontrados en Flatpak:\n")
            append(_friendly_flatpak_results(output, query))

        run_command_in_view(app, ["flatpak", "search", query], progress, append, limit_lines=None, on_done=flatpak_done)


def _install_from_source(
    app,
    source: str,
    query: str,
    progress,
    append,
    clear_log: Callable[[str], None],
    set_busy: Callable[[bool], None],
) -> None:
    if source == "apt":
        pkg = query.replace(" ", "-")
        if not re.fullmatch(r"[A-Za-z0-9.+_-]+", pkg):
            clear_log(f"'{query}' no parece ser un nombre valido para apt. Usa Buscar para ver opciones.")
            return
        command = ["pkexec", "apt", "install", "-y", pkg]
        label = f"Se instalara '{pkg}' usando apt. Ubuntu puede pedir tu contraseña."
    elif source == "snap":
        alias = _snap_alias(query)
        pkg = alias[0] if alias else query.replace(" ", "-")
        if not re.fullmatch(r"[A-Za-z0-9.+_-]+", pkg):
            clear_log(f"'{query}' no parece ser un nombre valido para Snap. Usa Buscar para ver opciones.")
            return
        command = ["pkexec", "snap", "install", pkg]
        label = f"Se instalara '{pkg}' usando Snap. Ubuntu puede pedir tu contraseña."
    elif source == "flatpak":
        alias = _flatpak_alias(query)
        pkg = alias[0] if alias else query
        if not shutil.which("flatpak"):
            clear_log("Flatpak no esta instalado o no esta disponible en este sistema.")
            return
        command = ["flatpak", "install", "-y", "flathub", pkg]
        label = f"Se instalara '{pkg}' usando Flatpak."
    else:
        clear_log("No reconozco ese metodo de instalacion. Usa apt, snap o flatpak.")
        return

    if source in {"apt", "snap"} and not shutil.which("pkexec"):
        clear_log("No encontre pkexec. Abre una terminal y usa:\n```bash\n" + " ".join(command[1:]) + "\n```")
        return

    def confirmed():
        clear_log(label)
        set_busy(True)

        def done(code: int, output: str):
            set_busy(False)
            if code == 0:
                clear_log(f"Instalacion completada: {pkg}")
            elif source == "snap":
                append(_friendly_snap_error(output, pkg))
            elif source == "apt":
                append(_friendly_apt_error(output, pkg))
            else:
                append(_friendly_flatpak_error(output, pkg))

        run_command_in_view(app, command, progress, append, on_done=done)

    confirm_action(app, "Confirmar instalacion", label, confirmed)


def _search_other_sources(app, query: str, progress, append, set_busy: Callable[[bool], None]) -> None:
    snap_info = _snap_alias(query)
    if snap_info:
        real_pkg, friendly_name = snap_info
        append(
            f"Reconoci el programa como {friendly_name}.\n"
            f"Comando recomendado:\n```bash\nsudo snap install {real_pkg}\n```"
        )
        set_busy(False)
        return

    if shutil.which("snap"):
        set_busy(True)

        def snap_done(_code: int, snap_output: str):
            if snap_output.strip():
                append("\nResultados de Snap:")
                append(_friendly_snap_results(snap_output, query))
            elif shutil.which("flatpak"):
                append("\nNo encontre resultados en Snap. Buscando en Flatpak...")

                def flatpak_done(_flat_code: int, flatpak_output: str):
                    set_busy(False)
                    append("\nResultados de Flatpak:")
                    append(_friendly_flatpak_results(flatpak_output, query))

                run_command_in_view(app, ["flatpak", "search", query], progress, append, limit_lines=None, on_done=flatpak_done)
                return
            else:
                append("\nNo encontre resultados en Snap. Flatpak no esta instalado o no esta disponible.")
            set_busy(False)

        run_command_in_view(app, ["snap", "find", query], progress, append, limit_lines=None, on_done=snap_done)
        return

    if shutil.which("flatpak"):
        set_busy(True)

        def flatpak_done(_code: int, flatpak_output: str):
            set_busy(False)
            append("\nResultados de Flatpak:")
            append(_friendly_flatpak_results(flatpak_output, query))

        run_command_in_view(app, ["flatpak", "search", query], progress, append, limit_lines=None, on_done=flatpak_done)
        return

    append(
        "No encontre alternativas automaticas. Puedes abrir la tienda de apps o probar el nombre oficial del proyecto."
    )
    set_busy(False)


def _friendly_apt_error(output: str, package: str) -> str:
    lowered = output.lower()
    if "no tiene un candidato" in lowered or "has no installation candidate" in lowered:
        return (
            f"\n'{package}' no esta disponible con ese nombre.\n"
            "Usa Buscar para ver alternativas. Por ejemplo, OBS Studio suele aparecer como 'obs-studio'."
        )
    if "unable to locate package" in lowered or "no se ha podido localizar" in lowered:
        return f"\nNo encontre el paquete '{package}'. Revisa el nombre o busca alternativas."
    return "\nNo se pudo completar la instalacion. Revisa el mensaje anterior para ver el detalle."


def _friendly_snap_error(output: str, package: str) -> str:
    lowered = output.lower()
    if "not found" in lowered or "no snap found" in lowered:
        return f"\nNo encontre el paquete Snap '{package}'. Prueba Buscar para ver alternativas."
    if "permission denied" in lowered or "authentication" in lowered:
        return "\nUbuntu no autorizo la instalacion. Vuelve a intentar y acepta la ventana de permisos."
    return "\nNo se pudo completar la instalacion con Snap. Revisa el mensaje anterior para ver el detalle."


def _friendly_flatpak_error(output: str, package: str) -> str:
    lowered = output.lower()
    if "no remote refs found" in lowered or "nothing matches" in lowered:
        return f"\nNo encontre '{package}' en Flatpak/Flathub. Usa Buscar para ver el ID correcto."
    if "flathub" in lowered and "not found" in lowered:
        return "\nParece que Flathub no esta configurado. Puedes instalarlo con:\n```bash\nflatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo\n```"
    return "\nNo se pudo completar la instalacion con Flatpak. Revisa el mensaje anterior para ver el detalle."

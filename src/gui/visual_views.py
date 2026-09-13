"""Vistas graficas orientadas a usuarios nuevos."""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable, Optional

import customtkinter as ctk
import psutil

from src.core.memory import clear_memory, load_memory, memory_summary
from src.core.storage import log_tool_run
from src.core.tools import build_deb_install_args, build_uninstall_args, is_critical_system_package, launch_in_terminal


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
    window = app._make_window("Instalar paquete", "820x560")
    _header(window, "Instalar programa", "Busca el paquete antes de instalar para confirmar que es el correcto.")

    form = ctk.CTkFrame(window, fg_color=app.C_CARD, border_width=0, corner_radius=8)
    form.pack(fill="x", padx=16, pady=(0, 10))
    entry = ctk.CTkEntry(form, placeholder_text="Ejemplo: vlc, gimp, htop, docker desktop", height=38, text_color=app.C_TEXT)
    entry.pack(side="left", fill="x", expand=True, padx=12, pady=12)
    if package_name:
        entry.insert(0, package_name)

    progress = ctk.CTkProgressBar(window, height=10, fg_color=app.C_BORDER, progress_color=app.C_ORANGE)
    progress.pack(fill="x", padx=16, pady=(4, 8))
    progress.set(0)

    log = ctk.CTkTextbox(window, fg_color=app.C_BG, text_color=app.C_TEXT, border_width=0, corner_radius=8)
    log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
    _append_log(log, "Listo para instalar. Si no sabes el nombre exacto, usa Buscar o consulta a la IA.")

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
        ai_btn.configure(state=new_state)

    def ask_ai(target_pkg: str = ""):
        if state["busy"]:
            return
        query = (target_pkg or package()).strip()
        if not query:
            clear_log("Escribe primero qué programa o herramienta deseas consultar a la IA.")
            return

        clear_log(f"🤖 Consultando a la IA sobre cómo instalar '{query}' en Ubuntu...")
        set_busy(True)
        progress.set(0.35)

        def worker():
            try:
                recommendation = _get_ai_package_recommendation(app, query)
            except Exception as exc:
                recommendation = f"No pude obtener respuesta de la IA: {exc}"

            def finish():
                set_busy(False)
                progress.set(1.0)
                clear_log(
                    f"💡 Recomendación de la IA para instalar '{query}':\n"
                    "──────────────────────────────────────────────────────────────────\n\n"
                    f"{recommendation}\n\n"
                    "──────────────────────────────────────────────────────────────────\n"
                    "Puedes copiar cualquier comando arriba para usarlo, o pulsar 'Archivo .deb' si descargaste el paquete oficial."
                )

            window.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

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
                f"'{pkg}' es un término general y no un paquete directo.\n"
                "Consultando a la IA sugerencias y recomendaciones de instalación..."
            )
            ask_ai(pkg)
            return
        elif not re.fullmatch(r"[A-Za-z0-9.+_-]+", pkg):
            clear_log(
                f"'{pkg}' no parece ser un nombre técnico directo de paquete Debian/Ubuntu.\n"
                "Consultando a la IA la mejor recomendación para instalarlo (repositorio oficial, .deb, snap o docker-ce)..."
            )
            ask_ai(pkg)
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
                    if suggestions.strip() and f"No encontre resultados para '{pkg}'." not in suggestions:
                        append("Sugerencias disponibles:")
                        append(suggestions)
                        append("\n💡 Si buscas el paquete oficial o externo, puedes pulsar '💡 Preguntar a la IA'.")
                        return
                    append("No encontré alternativas en los repositorios estándar.")
                    append("\nConsultando a la IA la recomendación para instalar este programa...")
                    ask_ai(pkg)

                run_command_in_view(app, ["apt-cache", "search", pkg], progress, append, limit_lines=None, on_done=search_done)

            run_command_in_view(app, ["apt-cache", "policy", pkg], progress, append, limit_lines=None, on_done=policy_done)

        confirm_action(
            app,
            "Confirmar instalacion",
            f"Se instalara el paquete '{pkg}'. Ubuntu puede pedir tu contraseña.",
            confirmed,
        )

    search_btn = ctk.CTkButton(buttons, text="Buscar", width=74, fg_color=app.C_CARD, hover_color=app.C_BORDER, command=search)
    search_btn.pack(side="left", padx=2)
    install_btn = ctk.CTkButton(buttons, text="Instalar", width=82, fg_color=app.C_ORANGE, hover_color=app.C_ORANGE_H, command=install)
    install_btn.pack(side="left", padx=2)
    deb_btn = ctk.CTkButton(buttons, text="Archivo .deb", width=96, fg_color=app.C_CARD, hover_color=app.C_BORDER, command=choose_deb)
    deb_btn.pack(side="left", padx=2)
    ai_btn = ctk.CTkButton(buttons, text="💡 Preguntar a la IA", width=130, fg_color=app.C_PURPLE, hover_color="#7e22ce", command=lambda: ask_ai())
    ai_btn.pack(side="left", padx=2)

    if deb_mode or package_name.lower().endswith(".deb"):
        window.after(100, choose_deb)


def show_package_remover(app, package_name: str = "") -> None:
    window = app._make_window("Desinstalar aplicacion", "760x540")
    _header(window, "Desinstalar aplicacion", "Busca una app instalada y confirma antes de quitarla del sistema.")

    form = ctk.CTkFrame(window, fg_color=app.C_CARD, border_width=0, corner_radius=8)
    form.pack(fill="x", padx=16, pady=(0, 10))
    entry = ctk.CTkEntry(form, placeholder_text="Ejemplo: vlc, spotify, org.app.Id", height=38, text_color=app.C_TEXT)
    entry.pack(side="left", fill="x", expand=True, padx=12, pady=12)
    if package_name:
        entry.insert(0, package_name)

    buttons = ctk.CTkFrame(form, fg_color="transparent")
    buttons.pack(side="right", padx=(0, 12))

    progress = ctk.CTkProgressBar(window, height=10, fg_color=app.C_BORDER, progress_color=app.C_ORANGE)
    progress.pack(fill="x", padx=16, pady=(4, 8))
    progress.set(0)

    log = ctk.CTkTextbox(window, fg_color=app.C_BG, text_color=app.C_TEXT, border_width=0, corner_radius=8)
    log.pack(fill="both", expand=True, padx=16, pady=(0, 12))
    _append_log(log, "Escribe el nombre de la aplicacion y usa Buscar antes de desinstalar.")

    state = {"busy": False, "recommended_source": "", "recommended_package": ""}

    def append(line: str):
        _append_log(log, line)

    def clear_log(message: str = ""):
        log.configure(state="normal")
        log.delete("1.0", "end")
        if message:
            log.insert("end", message + "\n")
        log.configure(state="disabled")

    def set_busy(value: bool):
        state["busy"] = value
        new_state = "disabled" if value else "normal"
        entry.configure(state=new_state)
        search_btn.configure(state=new_state)
        remove_btn.configure(state=new_state)
        store_btn.configure(state=new_state)

    def request() -> tuple[str, str]:
        source, pkg = _parse_install_request(entry.get().strip())
        return source or "auto", pkg

    def open_store():
        from src.core.tools import tool_open_software_center
        res = tool_open_software_center(mode="gestionar")
        append(f"\n🛒 {res}\nPuedes buscar la app o desinstalarla desde la sección 'Gestionar' en la tienda.")

    def search():
        if state["busy"]:
            return
        source, pkg = request()
        if not pkg:
            clear_log("Escribe primero que aplicacion quieres buscar.")
            return
        if is_critical_system_package(pkg):
            clear_log(
                f"'{pkg}' parece ser parte critica del sistema operativo.\n"
                "No lo marco como aplicacion removible desde esta pantalla."
            )
            return

        clear_log(f"Buscando instalaciones que coincidan con '{pkg}'...")
        set_busy(True)
        state["recommended_source"] = ""
        state["recommended_package"] = ""
        commands: list[tuple[str, list[str]]] = []
        if source in {"auto", "apt"}:
            commands.append(("apt", ["dpkg-query", "-W", "-f=${binary:Package}\t${Status}\t${binary:Summary}\n", f"*{pkg}*"]))
        if source in {"auto", "snap"} and shutil.which("snap"):
            commands.append(("snap", ["snap", "list"]))
        if source in {"auto", "flatpak"} and shutil.which("flatpak"):
            commands.append(("flatpak", ["flatpak", "list", "--app", "--columns=application,name"]))
        if not commands:
            set_busy(False)
            append("No hay gestores disponibles para buscar esa aplicacion.")
            return

        results: list[str] = []

        def run_next(index: int = 0):
            if index >= len(commands):
                set_busy(False)
                clear_log("Resultados encontrados:\n" if results else f"No se encontró '{pkg}' como aplicación instalada.\n")
                if results:
                    append("\n".join(results))
                else:
                    append(
                        "No se encontró el paquete en apt, snap ni flatpak.\n"
                        "Abriendo el Centro de aplicaciones de Ubuntu en el apartado 'Gestionar'..."
                    )
                    open_store()
                return

            label, args = commands[index]

            def done(_code: int, output: str):
                lowered_pkg = pkg.lower().strip()
                norm_pkg = re.sub(r"[^a-z0-9]+", "", lowered_pkg)
                lines = []
                for raw in output.splitlines():
                    raw_lowered = raw.lower()
                    raw_norm = re.sub(r"[^a-z0-9]+", "", raw_lowered)
                    if lowered_pkg in raw_lowered or (norm_pkg and norm_pkg in raw_norm):
                        lines.append(raw.strip())
                        if not state["recommended_source"]:
                            parts = raw.split()
                            if parts:
                                state["recommended_source"] = label
                                state["recommended_package"] = parts[0]
                    if len(lines) >= 8:
                        break
                if lines:
                    results.append(f"{label}:\n" + "\n".join(lines))
                run_next(index + 1)

            run_command_in_view(app, args, progress, append, limit_lines=0, on_done=done)

        run_next()

    def remove():
        if state["busy"]:
            return
        source, pkg = request()
        if not pkg:
            clear_log("Escribe primero que aplicacion quieres desinstalar.")
            return

        if source == "auto":
            recommended_src = state.get("recommended_source")
            recommended_pkg = state.get("recommended_package")
            if recommended_src:
                source = recommended_src
                pkg = recommended_pkg or pkg
            else:
                from src.core.tools import find_uninstall_candidates
                candidates = find_uninstall_candidates(pkg, source="auto")
                if candidates:
                    source = candidates[0]["source"]
                    pkg = candidates[0]["package"]
                    state["recommended_source"] = source
                    state["recommended_package"] = pkg
                else:
                    clear_log(
                        f"No se encontró ninguna aplicación instalada con el nombre '{pkg}'.\n"
                        "Abriendo el Centro de aplicaciones de Ubuntu en el apartado 'Gestionar'..."
                    )
                    open_store()
                    return

        try:
            command = build_uninstall_args(pkg, source)
        except ValueError as exc:
            clear_log(str(exc))
            return

        if command[0] == "pkexec" and not shutil.which("pkexec"):
            clear_log("No encontre pkexec. Abre una terminal y usa:\n```bash\n" + " ".join(command[1:]) + "\n```")
            return
        if command[0] == "flatpak" and not shutil.which("flatpak"):
            clear_log("Flatpak no esta instalado o no esta disponible en este sistema.")
            return

        label = (
            f"Se desinstalara '{command[-1]}' usando {source}.\n\n"
            "Esto quitara la aplicacion, pero no debe tocar componentes criticos del sistema."
        )

        def confirmed():
            clear_log(f"Desinstalando '{command[-1]}'...")
            set_busy(True)

            def done(code: int, output: str):
                set_busy(False)
                if code == 0:
                    clear_log(f"'{command[-1]}' se desinstalo correctamente.")
                else:
                    append(output.strip() or f"La desinstalacion termino con codigo {code}.")
                    output_lower = output.lower()
                    not_found_markers = (
                        "no se ha podido localizar",
                        "unable to locate",
                        "no matching",
                        "is not installed",
                        "not installed",
                        "no se encontro",
                        "no se encontró",
                    )
                    if any(marker in output_lower for marker in not_found_markers):
                        append("\n⚠️ No se encontró la aplicación en el gestor de paquetes.")
                        append("Abriendo el Centro de aplicaciones de Ubuntu en 'Gestionar'...")
                        open_store()

            run_command_in_view(app, command, progress, append, on_done=done)

        confirm_action(app, "Confirmar desinstalacion", label, confirmed)

    search_btn = ctk.CTkButton(buttons, text="Buscar", width=76, fg_color=app.C_CARD, hover_color=app.C_BORDER, command=search)
    search_btn.pack(side="left", padx=2)
    remove_btn = ctk.CTkButton(buttons, text="Desinstalar", width=95, fg_color=app.C_RED, hover_color="#b91c1c", command=remove)
    remove_btn.pack(side="left", padx=2)
    store_btn = ctk.CTkButton(buttons, text="🛒 Tienda", width=80, fg_color=app.C_CARD, hover_color=app.C_BORDER, command=open_store)
    store_btn.pack(side="left", padx=2)


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
    head_frame = ctk.CTkFrame(parent, fg_color="transparent")
    head_frame.pack(fill="x", padx=18, pady=(16, 12))

    title_row = ctk.CTkFrame(head_frame, fg_color="transparent")
    title_row.pack(fill="x")

    bar = ctk.CTkFrame(title_row, width=4, height=20, fg_color="#a855f7", corner_radius=99)
    bar.pack(side="left", padx=(0, 10))

    ctk.CTkLabel(
        title_row,
        text=title,
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#f5edff",
    ).pack(side="left")

    ctk.CTkLabel(
        head_frame,
        text=subtitle,
        font=ctk.CTkFont(size=12),
        text_color="#a79bb7",
        wraplength=700,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))


def _history_row(app, parent, index: int, message: dict[str, Any]) -> None:
    role = message.get("role", "")
    is_user = role == "user"
    title = "Usuario" if is_user else "Asistente"
    color = app.C_BLUE if is_user else app.C_ORANGE
    content = str(message.get("content", "")).strip() or "(mensaje vacío)"
    content = content[:1200] + "\n..." if len(content) > 1200 else content

    row = ctk.CTkFrame(parent, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=10)
    row.pack(fill="x", pady=5)

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
    frame = ctk.CTkFrame(parent, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=10)
    frame.pack(side="left", fill="x", expand=True, padx=4)
    top = ctk.CTkFrame(frame, fg_color="transparent")
    top.pack(fill="x", padx=12, pady=(10, 4))
    ctk.CTkLabel(top, text=label, text_color=app.C_MUTED2, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
    value = ctk.CTkLabel(top, text="—", text_color=app.C_TEXT, font=ctk.CTkFont(size=16, weight="bold"))
    value.pack(side="right")
    bar = ctk.CTkProgressBar(frame, height=8, fg_color=app.C_BORDER, progress_color=color, corner_radius=4)
    bar.pack(fill="x", padx=12, pady=(0, 12))
    bar.set(0)
    return value, bar


def _create_process_row(app, parent) -> dict[str, Any]:
    row = ctk.CTkFrame(parent, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=10)
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
    row = ctk.CTkFrame(parent, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=10)
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


def _get_ai_package_recommendation(app, query: str) -> str:
    """Obtiene una recomendación paso a paso de la IA para instalar una aplicación en Ubuntu."""
    query = query.strip()
    if not query:
        return "Escribe el nombre del programa para consultar a la IA."

    prompt = (
        f"El usuario quiere instalar '{query}' en Ubuntu Linux. "
        "Explica de forma concisa, clara y amigable la forma recomendada u oficial de instalarlo paso a paso en Ubuntu "
        "(si requiere descargar un paquete .deb oficial de su web, agregar repositorios del desarrollador, usar Snap, Flatpak o paquetes apt). "
        "Proporciona los comandos de terminal exactos en bloques ```bash y explica brevemente qué hace cada paso. "
        "Si existen requisitos previos importantes (como habilitar virtualización KVM para Docker Desktop), menciónalos con claridad."
    )

    agent = getattr(app, "agent", None)
    if agent and getattr(agent, "_client", None):
        try:
            completion = agent._client.chat.completions.create(
                model=agent.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un asistente experto en Ubuntu Linux. "
                            "Tu objetivo es dar instrucciones precisas, prácticas y concisas sobre cómo instalar "
                            "aplicaciones y herramientas en Ubuntu. Responde en español y usa bloques ```bash para los comandos."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=900,
            )
            reply = (completion.choices[0].message.content or "").strip()
            if reply:
                return reply
        except Exception:
            pass

    if agent and hasattr(agent, "chat"):
        try:
            return agent.chat(prompt)
        except Exception:
            pass

    try:
        from src.core.llm import GroqClient
        client = GroqClient()
        return client.chat(prompt)
    except Exception:
        pass

    lowered = query.lower()
    if "docker" in lowered:
        return (
            "Para instalar Docker en Ubuntu dispones de dos alternativas principales:\n\n"
            "1. **Docker Desktop (interfaz gráfica oficial)**:\n"
            "   • Requiere virtualización KVM habilitada en tu CPU (`kvm-ok`).\n"
            "   • Descarga el paquete `.deb` oficial de 64 bits desde:\n"
            "     https://docs.docker.com/desktop/install/ubuntu/\n"
            "   • Luego instálalo pulsando el botón 'Archivo .deb' de esta ventana, o por terminal:\n"
            "     ```bash\n"
            "     sudo apt update\n"
            "     sudo apt install ./docker-desktop-*-amd64.deb\n"
            "     systemctl --user start docker-desktop\n"
            "     ```\n\n"
            "2. **Docker Engine / CLI (Recomendado para servidores y desarrollo)**:\n"
            "   ```bash\n"
            "   sudo apt update\n"
            "   sudo apt install -y docker.io docker-compose\n"
            "   sudo usermod -aG docker $USER\n"
            "   ```\n"
            "   *(Cierra sesión y vuelve a entrar para usar Docker sin sudo)*."
        )

    return (
        f"No se pudo consultar al modelo de IA en este momento para '{query}'. "
        "Verifica tu conexión a internet o la clave en el archivo .env, "
        "o prueba buscando el nombre técnico con el botón 'Buscar'."
    )


def show_gaming_hub(app) -> None:
    window = app._make_window("Centro de Gaming y Juegos", "820x620")
    _header(
        window,
        "Gaming en Linux y Compatibilidad",
        "Configuración de Steam, Proton, Wine, Lutris y compatibilidad para jugar en Ubuntu sin complicaciones.",
    )

    body = ctk.CTkScrollableFrame(window, fg_color=app.C_PANEL, corner_radius=0)
    body.pack(fill="both", expand=True, padx=16, pady=(0, 14))

    steam_installed = shutil.which("steam") is not None
    wine_installed = shutil.which("wine") is not None
    lutris_installed = shutil.which("lutris") is not None

    gpu_info = "Gráficos integrados / Desconocido"
    try:
        lspci = subprocess.check_output(["lspci"], text=True, stderr=subprocess.DEVNULL)
        for line in lspci.splitlines():
            if any(k in line.lower() for k in ["vga", "3d", "display"]):
                parts = line.split(":", 2)
                gpu_info = parts[-1].strip() if len(parts) > 2 else line
                break
    except Exception:
        pass

    status_frame = ctk.CTkFrame(body, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
    status_frame.pack(fill="x", pady=(0, 12))

    ctk.CTkLabel(status_frame, text="🎮 Estado de herramientas gaming", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=16, pady=(12, 6))

    grid = ctk.CTkFrame(status_frame, fg_color="transparent")
    grid.pack(fill="x", padx=14, pady=(0, 14))
    grid.columnconfigure((0, 1, 2), weight=1)

    def _badge(parent, col, name, installed, icon):
        f = ctk.CTkFrame(parent, fg_color=app.C_PANEL, corner_radius=8, border_width=1, border_color=app.C_BORDER)
        f.grid(row=0, column=col, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(f, text=f"{icon} {name}", font=ctk.CTkFont(size=12, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=10, pady=(8, 2))
        color = app.C_GREEN if installed else app.C_MUTED2
        text = "✓ Instalado" if installed else "○ No instalado"
        ctk.CTkLabel(f, text=text, font=ctk.CTkFont(size=11), text_color=color).pack(anchor="w", padx=10, pady=(0, 8))

    _badge(grid, 0, "Steam", steam_installed, "🕹️")
    _badge(grid, 1, "Wine", wine_installed, "🍷")
    _badge(grid, 2, "Lutris", lutris_installed, "🎮")

    gpu_box = ctk.CTkFrame(status_frame, fg_color=app.C_PANEL, corner_radius=8)
    gpu_box.pack(fill="x", padx=14, pady=(0, 12))
    ctk.CTkLabel(gpu_box, text=f"⚡ GPU detectada: {gpu_info}", font=ctk.CTkFont(size=11), text_color=app.C_MUTED2).pack(anchor="w", padx=10, pady=6)

    actions_box = ctk.CTkFrame(body, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
    actions_box.pack(fill="x", pady=(0, 12))
    ctk.CTkLabel(actions_box, text="⚡ Acciones rápidas de instalación y lanzamiento", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=16, pady=(12, 8))

    btn_row = ctk.CTkFrame(actions_box, fg_color="transparent")
    btn_row.pack(fill="x", padx=14, pady=(0, 6))

    if steam_installed:
        ctk.CTkButton(
            btn_row,
            text="🚀 Abrir Steam",
            fg_color=app.C_GREEN,
            hover_color="#2ea043",
            text_color="#ffffff",
            command=lambda: subprocess.Popen(["steam"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
        ).pack(side="left", fill="x", expand=True, padx=4)
    else:
        ctk.CTkButton(
            btn_row,
            text="📥 Instalar Steam",
            fg_color=app.C_ORANGE,
            hover_color=app.C_ORANGE_H,
            command=lambda: (window.destroy(), show_package_installer(app, "steam")),
        ).pack(side="left", fill="x", expand=True, padx=4)

    if lutris_installed:
        ctk.CTkButton(
            btn_row,
            text="🚀 Abrir Lutris",
            fg_color=app.C_GREEN,
            hover_color="#2ea043",
            text_color="#ffffff",
            command=lambda: subprocess.Popen(["lutris"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
        ).pack(side="left", fill="x", expand=True, padx=4)
    else:
        ctk.CTkButton(
            btn_row,
            text="📥 Instalar Lutris",
            fg_color=app.C_CARD,
            hover_color=app.C_BORDER,
            border_width=1,
            border_color=app.C_BORDER,
            command=lambda: (window.destroy(), show_package_installer(app, "lutris")),
        ).pack(side="left", fill="x", expand=True, padx=4)

    btn_row2 = ctk.CTkFrame(actions_box, fg_color="transparent")
    btn_row2.pack(fill="x", padx=14, pady=(4, 14))

    ctk.CTkButton(
        btn_row2,
        text="🍷 Instalar / Configurar Wine",
        fg_color=app.C_CARD,
        hover_color=app.C_BORDER,
        border_width=1,
        border_color=app.C_BORDER,
        command=lambda: (window.destroy(), show_package_installer(app, "wine")),
    ).pack(side="left", fill="x", expand=True, padx=4)

    ctk.CTkButton(
        btn_row2,
        text="🌐 Consultar ProtonDB en la Web",
        fg_color=app.C_CARD,
        hover_color=app.C_BORDER,
        border_width=1,
        border_color=app.C_BORDER,
        command=lambda: webbrowser.open("https://www.protondb.com"),
    ).pack(side="left", fill="x", expand=True, padx=4)

    guide_box = ctk.CTkFrame(body, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
    guide_box.pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(guide_box, text="📖 Guía paso a paso: Cómo activar Proton para jugar a títulos de Windows", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=16, pady=(12, 6))

    guide_text = (
        "Proton es la capa de compatibilidad de Valve (basada en Wine) que permite ejecutar juegos de Windows en Linux.\n\n"
        "1. Abre Steam y ve a: Parámetros (Settings) ➔ Compatibilidad (Compatibility).\n"
        "2. Marca la casilla: 'Habilitar Steam Play para todos los demás títulos'.\n"
        "3. En el desplegable, selecciona 'Proton Experimental' o la versión más reciente (ej. Proton 9).\n"
        "4. Reinicia Steam si te lo pide. ¡Ahora puedes instalar y jugar a casi cualquier juego de tu biblioteca!\n"
        "5. Para juegos fuera de Steam (Epic Games, GOG, Ubisoft, etc.), te recomendamos usar Lutris o Heroic Games Launcher."
    )
    ctk.CTkLabel(guide_box, text=guide_text, font=ctk.CTkFont(size=11), text_color=app.C_MUTED2, justify="left", wraplength=740).pack(anchor="w", padx=16, pady=(0, 14))


def show_drivers_manager(app) -> None:
    window = app._make_window("Controladores y Hardware", "820x620")
    _header(
        window,
        "Controladores y Hardware del Sistema",
        "Detecta tarjetas de video, adaptadores Wi-Fi y administra controladores propietarios o adicionales.",
    )

    hw_frame = ctk.CTkFrame(window, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
    hw_frame.pack(fill="x", padx=16, pady=(0, 10))

    ctk.CTkLabel(hw_frame, text="💻 Resumen de Hardware Detectado", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=16, pady=(10, 4))

    gpu_desc = "No detectado"
    net_desc = "No detectado"
    try:
        lspci = subprocess.check_output(["lspci"], text=True, stderr=subprocess.DEVNULL)
        for line in lspci.splitlines():
            low = line.lower()
            if any(k in low for k in ["vga", "3d", "display"]) and gpu_desc == "No detectado":
                parts = line.split(":", 2)
                gpu_desc = parts[-1].strip() if len(parts) > 2 else line
            elif any(k in low for k in ["network", "ethernet", "wireless", "wi-fi"]) and net_desc == "No detectado":
                parts = line.split(":", 2)
                net_desc = parts[-1].strip() if len(parts) > 2 else line
    except Exception:
        pass

    labels_grid = ctk.CTkFrame(hw_frame, fg_color="transparent")
    labels_grid.pack(fill="x", padx=14, pady=(0, 10))
    ctk.CTkLabel(labels_grid, text=f"• Gráficos (GPU): {gpu_desc}", font=ctk.CTkFont(size=11), text_color=app.C_MUTED2).pack(anchor="w", pady=1)
    ctk.CTkLabel(labels_grid, text=f"• Red / Wi-Fi: {net_desc}", font=ctk.CTkFont(size=11), text_color=app.C_MUTED2).pack(anchor="w", pady=1)

    btns = ctk.CTkFrame(window, fg_color="transparent")
    btns.pack(fill="x", padx=16, pady=(0, 10))

    progress = ctk.CTkProgressBar(window, height=8, fg_color=app.C_BORDER, progress_color=app.C_ORANGE)
    progress.pack(fill="x", padx=16, pady=(0, 8))
    progress.set(0)

    log = ctk.CTkTextbox(window, fg_color=app.C_BG, text_color=app.C_TEXT, border_width=0, corner_radius=8)
    log.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    _append_log(log, "Selecciona una opción para diagnosticar o gestionar controladores.")

    def append(msg: str):
        _append_log(log, msg)

    def detect_drivers():
        progress.set(0)
        append("\n🔍 Buscando controladores disponibles con ubuntu-drivers...")
        run_command_in_view(app, ["ubuntu-drivers", "devices"], progress, append)

    def open_additional_drivers_gui():
        opened = False
        for cmd in [["software-properties-gtk", "--open-tab=4"], ["software-properties-gtk"], ["gnome-control-center", "system"], ["gnome-control-center"]]:
            if shutil.which(cmd[0]):
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    append(f"✓ Se abrió la ventana de configuración: {' '.join(cmd)}")
                    opened = True
                    break
                except Exception:
                    continue
        if not opened:
            append("No se encontró una herramienta gráfica instalada para controladores. Usa 'Detectar Controladores' aquí mismo.")

    def install_recommended():
        def confirmed():
            append("\n⚙️ Instalando controladores recomendados...")
            run_command_in_view(app, ["pkexec", "ubuntu-drivers", "install"], progress, append)

        confirm_action(
            app,
            "Instalar controladores recomendados",
            "Ubuntu detectará e instalará los controladores propietarios óptimos para tu tarjeta gráfica o Wi-Fi. Puede requerir reiniciar después.",
            confirmed,
        )

    def show_lspci():
        progress.set(0)
        append("\n📋 Información completa de dispositivos PCI (lspci):")
        run_command_in_view(app, ["lspci"], progress, append)

    ctk.CTkButton(btns, text="🔍 Detectar Controladores", fg_color=app.C_ORANGE, hover_color=app.C_ORANGE_H, command=detect_drivers).pack(side="left", fill="x", expand=True, padx=(0, 4))
    ctk.CTkButton(btns, text="🖥️ Abrir Controladores (GUI)", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=open_additional_drivers_gui).pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkButton(btns, text="⚙️ Autoinstalar Recomendados", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=install_recommended).pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkButton(btns, text="📋 Ver Hardware (lspci)", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=show_lspci).pack(side="left", fill="x", expand=True, padx=(4, 0))


def show_system_cleaner(app) -> None:
    window = app._make_window("Limpieza y Optimización del Sistema", "820x620")
    _header(
        window,
        "Limpieza y Optimización del Sistema",
        "Libera espacio en disco eliminando caché vieja, dependencias huérfanas y paquetes residuales con seguridad.",
    )

    stats_frame = ctk.CTkFrame(window, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
    stats_frame.pack(fill="x", padx=16, pady=(0, 10))

    top_stats = ctk.CTkFrame(stats_frame, fg_color="transparent")
    top_stats.pack(fill="x", padx=14, pady=12)

    disk = psutil.disk_usage("/")
    used_gb = disk.used / (1024 ** 3)
    total_gb = disk.total / (1024 ** 3)
    percent = disk.percent

    thumb_path = Path.home() / ".cache" / "thumbnails"
    thumb_size_mb = 0.0
    if thumb_path.exists():
        try:
            thumb_size_mb = sum(f.stat().st_size for f in thumb_path.rglob("*") if f.is_file()) / (1024 ** 2)
        except Exception:
            pass

    apt_cache_path = Path("/var/cache/apt/archives")
    apt_cache_mb = 0.0
    if apt_cache_path.exists():
        try:
            apt_cache_mb = sum(f.stat().st_size for f in apt_cache_path.glob("*.deb")) / (1024 ** 2)
        except Exception:
            pass

    col1 = ctk.CTkFrame(top_stats, fg_color=app.C_PANEL, corner_radius=8, border_width=1, border_color=app.C_BORDER)
    col1.pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkLabel(col1, text="💽 Espacio en disco (/)", font=ctk.CTkFont(size=11, weight="bold"), text_color=app.C_MUTED2).pack(anchor="w", padx=10, pady=(8, 2))
    ctk.CTkLabel(col1, text=f"{used_gb:.1f} GB de {total_gb:.1f} GB ({percent}%)", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=10, pady=(0, 8))

    col2 = ctk.CTkFrame(top_stats, fg_color=app.C_PANEL, corner_radius=8, border_width=1, border_color=app.C_BORDER)
    col2.pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkLabel(col2, text="📦 Caché de paquetes APT", font=ctk.CTkFont(size=11, weight="bold"), text_color=app.C_MUTED2).pack(anchor="w", padx=10, pady=(8, 2))
    ctk.CTkLabel(col2, text=f"~{apt_cache_mb:.1f} MB acumulados", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=10, pady=(0, 8))

    col3 = ctk.CTkFrame(top_stats, fg_color=app.C_PANEL, corner_radius=8, border_width=1, border_color=app.C_BORDER)
    col3.pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkLabel(col3, text="🖼️ Caché de miniaturas", font=ctk.CTkFont(size=11, weight="bold"), text_color=app.C_MUTED2).pack(anchor="w", padx=10, pady=(8, 2))
    ctk.CTkLabel(col3, text=f"~{thumb_size_mb:.1f} MB en caché", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=10, pady=(0, 8))

    btns = ctk.CTkFrame(window, fg_color="transparent")
    btns.pack(fill="x", padx=16, pady=(0, 10))

    progress = ctk.CTkProgressBar(window, height=8, fg_color=app.C_BORDER, progress_color=app.C_ORANGE)
    progress.pack(fill="x", padx=16, pady=(0, 8))
    progress.set(0)

    log = ctk.CTkTextbox(window, fg_color=app.C_BG, text_color=app.C_TEXT, border_width=0, corner_radius=8)
    log.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    _append_log(log, "Selecciona una tarea de optimización para comenzar.")

    def append(msg: str):
        _append_log(log, msg)

    def clean_apt():
        def confirmed():
            append("\n🧹 Limpiando caché de paquetes APT descargados (apt-get clean)...")
            run_command_in_view(app, ["pkexec", "apt-get", "clean"], progress, append)

        confirm_action(app, "Limpiar caché APT", "Eliminará los archivos .deb temporales descargados por APT en /var/cache/apt/archives.", confirmed)

    def autoremove_apt():
        def confirmed():
            append("\n📦 Eliminando dependencias huérfanas en desuso (apt-get autoremove)...")
            run_command_in_view(app, ["pkexec", "apt-get", "autoremove", "-y"], progress, append)

        confirm_action(app, "Eliminar paquetes huérfanos", "Eliminará librerías y dependencias antiguas que ya no son utilizadas por ninguna aplicación instalada.", confirmed)

    def clean_thumbnails():
        try:
            if thumb_path.exists():
                count = 0
                for f in thumb_path.rglob("*"):
                    if f.is_file():
                        try:
                            f.unlink()
                            count += 1
                        except Exception:
                            pass
                append(f"\n🖼️ Miniaturas eliminadas con éxito ({count} archivos liberados).")
            else:
                append("\n🖼️ La carpeta de miniaturas ya estaba limpia.")
        except Exception as exc:
            append(f"\nError al limpiar miniaturas: {exc}")

    def open_baobab():
        if shutil.which("baobab"):
            try:
                subprocess.Popen(["baobab", "/"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                append("\n✓ Se abrió el Analizador de Uso de Disco (Baobab).")
            except Exception as exc:
                append(f"\nNo se pudo abrir Baobab: {exc}")
        else:
            append("\nBaobab no está instalado. Puedes instalarlo con el botón 'Instalar programas' (paquete: baobab).")

    def full_maintenance():
        def confirmed():
            append("\n⚡ Iniciando optimización completa del sistema...")
            clean_thumbnails()
            run_command_in_view(
                app,
                ["pkexec", "bash", "-lc", "apt-get clean && apt-get autoremove -y"],
                progress,
                append,
            )

        confirm_action(app, "Optimización completa", "Ejecutará limpieza de miniaturas, eliminación de caché APT y remoción de librerías huérfanas.", confirmed)

    ctk.CTkButton(btns, text="⚡ Optimización completa", fg_color=app.C_ORANGE, hover_color=app.C_ORANGE_H, command=full_maintenance).pack(side="left", fill="x", expand=True, padx=(0, 4))
    ctk.CTkButton(btns, text="📦 Paquetes huérfanos", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=autoremove_apt).pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkButton(btns, text="🧹 Caché APT", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=clean_apt).pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkButton(btns, text="🖼️ Miniaturas", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=clean_thumbnails).pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkButton(btns, text="📊 Analizador (Baobab)", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=open_baobab).pack(side="left", fill="x", expand=True, padx=(4, 0))


def show_appearance_manager(app) -> None:
    window = app._make_window("Personalizar Apariencia", "820x580")
    _header(
        window,
        "Personalización y Apariencia",
        "Modifica el tema oscuro/claro, fondos de pantalla, extensiones y aspecto visual de Ubuntu.",
    )

    body = ctk.CTkScrollableFrame(window, fg_color=app.C_PANEL, corner_radius=0)
    body.pack(fill="both", expand=True, padx=16, pady=(0, 14))

    theme_card = ctk.CTkFrame(body, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
    theme_card.pack(fill="x", pady=(0, 12))
    ctk.CTkLabel(theme_card, text="🌓 Estilo de Color del Sistema", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=16, pady=(12, 6))

    theme_row = ctk.CTkFrame(theme_card, fg_color="transparent")
    theme_row.pack(fill="x", padx=14, pady=(0, 14))

    feedback_lbl = ctk.CTkLabel(theme_card, text="", font=ctk.CTkFont(size=11), text_color=app.C_GREEN)
    feedback_lbl.pack(anchor="w", padx=16, pady=(0, 8))

    def set_color_scheme(scheme: str):
        try:
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", scheme], check=True)
            txt = "🌙 Modo Oscuro activado." if scheme == "prefer-dark" else "☀️ Modo Claro activado."
            feedback_lbl.configure(text=txt, text_color=app.C_GREEN)
        except Exception as exc:
            feedback_lbl.configure(text=f"No se pudo cambiar el tema: {exc}", text_color=app.C_RED)

    ctk.CTkButton(
        theme_row,
        text="🌙 Activar Modo Oscuro (Dark)",
        fg_color=app.C_CARD,
        hover_color=app.C_CARD_HOVER,
        border_width=1,
        border_color=app.C_BORDER,
        text_color=app.C_TEXT,
        height=38,
        corner_radius=12,
        command=lambda: set_color_scheme("prefer-dark"),
    ).pack(side="left", fill="x", expand=True, padx=(0, 6))

    ctk.CTkButton(
        theme_row,
        text="☀️ Activar Modo Claro (Light)",
        fg_color=app.C_PANEL,
        hover_color=app.C_CARD_HOVER,
        border_width=1,
        border_color=app.C_BORDER,
        text_color=app.C_MUTED,
        height=38,
        corner_radius=12,
        command=lambda: set_color_scheme("default"),
    ).pack(side="left", fill="x", expand=True, padx=(6, 0))

    tools_card = ctk.CTkFrame(body, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
    tools_card.pack(fill="x", pady=(0, 12))
    ctk.CTkLabel(tools_card, text="⚙️ Herramientas de Configuración Gráfica", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=16, pady=(12, 6))

    def open_gui_tool(args: list[str], fallback_msg: str):
        if shutil.which(args[0]):
            try:
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                feedback_lbl.configure(text=f"✓ Se abrió {args[0]}.", text_color=app.C_GREEN)
            except Exception as exc:
                feedback_lbl.configure(text=f"Error al abrir {args[0]}: {exc}", text_color=app.C_RED)
        else:
            feedback_lbl.configure(text=fallback_msg, text_color=app.C_ORANGE)

    tgrid = ctk.CTkFrame(tools_card, fg_color="transparent")
    tgrid.pack(fill="x", padx=14, pady=(0, 14))
    tgrid.columnconfigure((0, 1), weight=1)

    ctk.CTkButton(
        tgrid,
        text="🖼️ Cambiar Fondo de Pantalla",
        fg_color=app.C_PANEL,
        hover_color=app.C_BORDER,
        border_width=1,
        border_color=app.C_BORDER,
        command=lambda: open_gui_tool(["gnome-control-center", "background"], "gnome-control-center no disponible"),
    ).grid(row=0, column=0, padx=4, pady=4, sticky="nsew")

    ctk.CTkButton(
        tgrid,
        text="🎨 Configuración de Ubuntu (Apariencia)",
        fg_color=app.C_PANEL,
        hover_color=app.C_BORDER,
        border_width=1,
        border_color=app.C_BORDER,
        command=lambda: open_gui_tool(["gnome-control-center", "ubuntu"], "gnome-control-center no disponible"),
    ).grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

    tweaks_installed = shutil.which("gnome-tweaks") is not None
    tweaks_btn_text = "🪟 Abrir Retoques (GNOME Tweaks)" if tweaks_installed else "📥 Instalar GNOME Tweaks"
    tweaks_cmd = (
        (lambda: open_gui_tool(["gnome-tweaks"], "gnome-tweaks no encontrado"))
        if tweaks_installed
        else (lambda: (window.destroy(), show_package_installer(app, "gnome-tweaks")))
    )

    ctk.CTkButton(
        tgrid,
        text=tweaks_btn_text,
        fg_color=app.C_PANEL,
        hover_color=app.C_BORDER,
        border_width=1,
        border_color=app.C_BORDER,
        command=tweaks_cmd,
    ).grid(row=1, column=0, padx=4, pady=4, sticky="nsew")

    ctk.CTkButton(
        tgrid,
        text="🧩 Extensiones de GNOME (Web)",
        fg_color=app.C_PANEL,
        hover_color=app.C_BORDER,
        border_width=1,
        border_color=app.C_BORDER,
        command=lambda: webbrowser.open("https://extensions.gnome.org"),
    ).grid(row=1, column=1, padx=4, pady=4, sticky="nsew")


def show_terminal_guide(app) -> None:
    window = app._make_window("Terminal Guiada y Comandos Esenciales", "840x640")
    _header(
        window,
        "Terminal Guiada y Comandos Esenciales",
        "Aprende y prueba los comandos más importantes de Ubuntu Linux de forma segura y visual.",
    )

    top_bar = ctk.CTkFrame(window, fg_color="transparent")
    top_bar.pack(fill="x", padx=16, pady=(0, 10))

    def open_real_terminal():
        ok, msg = launch_in_terminal("bash", "Terminal Ubuntu")
        if not ok:
            for term in ["x-terminal-emulator", "gnome-terminal", "ptyxis", "konsole"]:
                if shutil.which(term):
                    subprocess.Popen([term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    ok = True
                    break
        if ok:
            app._set_status("● Terminal abierta", app.C_GREEN, app.C_GREEN_D)

    ctk.CTkButton(
        top_bar,
        text="💻 Abrir Terminal del Sistema",
        fg_color=app.C_ORANGE,
        hover_color=app.C_ORANGE_H,
        height=34,
        command=open_real_terminal,
    ).pack(side="left", padx=(0, 8))

    ctk.CTkLabel(
        top_bar,
        text="Prueba comandos seguros abajo sin riesgo para tu sistema.",
        font=ctk.CTkFont(size=11),
        text_color=app.C_MUTED2,
    ).pack(side="left")

    body = ctk.CTkScrollableFrame(window, fg_color=app.C_PANEL, corner_radius=0)
    body.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    runner_frame = ctk.CTkFrame(body, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
    runner_frame.pack(fill="x", pady=(0, 12))

    ctk.CTkLabel(runner_frame, text="⚡ Ejecutor de Comandos Seguros (Salida en vivo)", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=16, pady=(10, 4))

    quick_cmds = ctk.CTkFrame(runner_frame, fg_color="transparent")
    quick_cmds.pack(fill="x", padx=14, pady=(0, 8))

    output_box = ctk.CTkTextbox(runner_frame, height=120, fg_color=app.C_BG, text_color=app.C_TEXT, font=ctk.CTkFont(family="Courier", size=11), corner_radius=8)
    output_box.pack(fill="x", padx=14, pady=(0, 12))
    _append_log(output_box, "Pulsa cualquiera de los botones para ver la salida real del comando:")

    def run_safe_cmd(cmd_list: list[str]):
        output_box.configure(state="normal")
        output_box.delete("1.0", "end")
        output_box.insert("end", f"$ {' '.join(cmd_list)}\n\n")
        try:
            out = subprocess.check_output(cmd_list, text=True, stderr=subprocess.STDOUT)
            output_box.insert("end", out)
        except Exception as exc:
            output_box.insert("end", f"Error: {exc}")
        output_box.configure(state="disabled")

    commands_to_test = [
        ("Discos (df -h)", ["df", "-h", "/"]),
        ("Memoria (free -h)", ["free", "-h"]),
        ("Kernel (uname -r)", ["uname", "-r"]),
        ("Usuario (whoami)", ["whoami"]),
        ("Archivos en Home", ["ls", "-la", str(Path.home())]),
    ]
    for label, cmd_arr in commands_to_test:
        ctk.CTkButton(
            quick_cmds,
            text=label,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=app.C_PANEL,
            hover_color=app.C_BORDER,
            border_width=1,
            border_color=app.C_BORDER,
            command=lambda c=cmd_arr: run_safe_cmd(c),
        ).pack(side="left", padx=3)

    def _add_catalog_section(title, icon, items):
        sec = ctk.CTkFrame(body, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
        sec.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(sec, text=f"{icon} {title}", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=16, pady=(10, 4))
        for cmd_name, desc in items:
            row = ctk.CTkFrame(sec, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=cmd_name, font=ctk.CTkFont(family="Courier", size=11, weight="bold"), text_color=app.C_ORANGE).pack(side="left")
            ctk.CTkLabel(row, text=f"➔  {desc}", font=ctk.CTkFont(size=11), text_color=app.C_MUTED2).pack(side="left", padx=10)
        ctk.CTkFrame(sec, height=8, fg_color="transparent").pack()

    _add_catalog_section(
        "Navegación y Archivos",
        "📁",
        [
            ("ls -lh", "Lista los archivos y carpetas con su tamaño detallado."),
            ("cd carpeta", "Entra a una carpeta específica (ej. `cd Descargas` o `cd ..` para subir)."),
            ("pwd", "Muestra la ruta exacta de la carpeta en la que te encuentras."),
            ("mkdir nombre", "Crea una nueva carpeta con el nombre indicado."),
            ("cp origen destino", "Copia un archivo o carpeta hacia otra ubicación."),
        ],
    )

    _add_catalog_section(
        "Administración de Programas (APT)",
        "📦",
        [
            ("sudo apt update", "Actualiza la lista de programas disponibles desde los repositorios."),
            ("sudo apt upgrade", "Descarga e instala las actualizaciones disponibles."),
            ("sudo apt install paquete", "Instala una aplicación por su nombre técnico."),
            ("apt search palabra", "Busca paquetes disponibles en el catálogo de Ubuntu."),
        ],
    )

    _add_catalog_section(
        "Atajos de Teclado Imprescindibles",
        "⌨️",
        [
            ("Ctrl + C", "Cancela o detiene de inmediato el programa o proceso que se está ejecutando."),
            ("Ctrl + L", "Limpia la pantalla de la terminal."),
            ("Tecla Tab (↹)", "Autocompleta automáticamente nombres de comandos, archivos y carpetas."),
            ("Flecha Arriba (↑)", "Vuelve a mostrar el último comando ejecutado para no tener que escribirlo."),
        ],
    )


def show_troubleshooter(app) -> None:
    window = app._make_window("Solución de Errores y Diagnóstico", "840x640")
    _header(
        window,
        "Diagnóstico y Solución de Problemas",
        "Detecta incidencias en el sistema (paquetes rotos, servicios fallidos, red) y ejecuta reparaciones con un clic.",
    )

    status_card = ctk.CTkFrame(window, fg_color=app.C_CARD, border_width=1, border_color=app.C_BORDER, corner_radius=12)
    status_card.pack(fill="x", padx=16, pady=(0, 10))

    ctk.CTkLabel(status_card, text="🩺 Estado de Salud del Sistema", font=ctk.CTkFont(size=13, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=16, pady=(10, 4))

    grid = ctk.CTkFrame(status_card, fg_color="transparent")
    grid.pack(fill="x", padx=14, pady=(0, 10))
    grid.columnconfigure((0, 1, 2), weight=1)

    dpkg_clean = True
    try:
        res = subprocess.run(["dpkg", "--audit"], capture_output=True, text=True)
        dpkg_clean = (len(res.stdout.strip()) == 0)
    except Exception:
        pass

    failed_services_count = 0
    try:
        res = subprocess.run(["systemctl", "--failed", "--no-legend"], capture_output=True, text=True)
        lines = [line for line in res.stdout.splitlines() if line.strip()]
        failed_services_count = len(lines)
    except Exception:
        pass

    disk = psutil.disk_usage("/")
    disk_ok = disk.percent < 90

    def _diag_badge(parent, col, title, ok, ok_text, bad_text):
        f = ctk.CTkFrame(parent, fg_color=app.C_PANEL, corner_radius=8, border_width=1, border_color=app.C_BORDER)
        f.grid(row=0, column=col, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color=app.C_TEXT).pack(anchor="w", padx=10, pady=(6, 2))
        color = app.C_GREEN if ok else app.C_RED
        text = ok_text if ok else bad_text
        ctk.CTkLabel(f, text=text, font=ctk.CTkFont(size=11), text_color=color).pack(anchor="w", padx=10, pady=(0, 6))

    _diag_badge(grid, 0, "Paquetes DPKG", dpkg_clean, "✓ Sin inconsistencias", "⚠️ Hay paquetes rotos")
    _diag_badge(grid, 1, "Servicios Systemd", failed_services_count == 0, "✓ Todos activos", f"⚠️ {failed_services_count} fallidos")
    _diag_badge(grid, 2, "Espacio en Disco", disk_ok, f"✓ {disk.percent}% ocupado", f"⚠️ Crítico: {disk.percent}%")

    btns = ctk.CTkFrame(window, fg_color="transparent")
    btns.pack(fill="x", padx=16, pady=(0, 10))

    progress = ctk.CTkProgressBar(window, height=8, fg_color=app.C_BORDER, progress_color=app.C_ORANGE)
    progress.pack(fill="x", padx=16, pady=(0, 8))
    progress.set(0)

    log = ctk.CTkTextbox(window, fg_color=app.C_BG, text_color=app.C_TEXT, border_width=0, corner_radius=8)
    log.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    _append_log(log, "Selecciona una herramienta para diagnosticar o reparar:")

    def append(msg: str):
        _append_log(log, msg)

    def fix_broken_packages():
        def confirmed():
            append("\n🔧 Reparando paquetes rotos y configuraciones pendientes...")
            run_command_in_view(
                app,
                ["pkexec", "bash", "-lc", "dpkg --configure -a && apt-get --fix-broken install -y"],
                progress,
                append,
            )

        confirm_action(
            app,
            "Reparar paquetes",
            "Ejecutará 'dpkg --configure -a' y 'apt --fix-broken install' para resolver bloqueos o instalaciones interrumpidas.",
            confirmed,
        )

    def check_failed_services():
        progress.set(0)
        append("\n🔍 Inspeccionando servicios de systemd que han fallado:")
        run_command_in_view(app, ["systemctl", "--failed"], progress, append)

    def restart_network():
        def confirmed():
            append("\n🌐 Reiniciando el servicio de red (NetworkManager)...")
            run_command_in_view(app, ["pkexec", "systemctl", "restart", "NetworkManager"], progress, append)

        confirm_action(app, "Reiniciar red", "Se reiniciará NetworkManager. La conexión Wi-Fi/cable se restablecerá en pocos segundos.", confirmed)

    def show_system_errors():
        progress.set(0)
        append("\n📋 Últimos errores críticos registrados en el sistema (journalctl):")
        run_command_in_view(app, ["journalctl", "-p", "3", "-xb", "-n", "35", "--no-pager"], progress, append)

    ctk.CTkButton(btns, text="🔧 Reparar paquetes rotos", fg_color=app.C_ORANGE, hover_color=app.C_ORANGE_H, command=fix_broken_packages).pack(side="left", fill="x", expand=True, padx=(0, 4))
    ctk.CTkButton(btns, text="⚠️ Ver servicios fallidos", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=check_failed_services).pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkButton(btns, text="🌐 Reiniciar red", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=restart_network).pack(side="left", fill="x", expand=True, padx=4)
    ctk.CTkButton(btns, text="📋 Registro de errores", fg_color=app.C_CARD, hover_color=app.C_BORDER, border_width=1, border_color=app.C_BORDER, command=show_system_errors).pack(side="left", fill="x", expand=True, padx=(4, 0))



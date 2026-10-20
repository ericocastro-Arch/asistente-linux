"""Pruebas del puente entre la interfaz web y las herramientas del sistema."""

import json
from types import SimpleNamespace

import pytest

from src.gui import app_catalog, webview_app
from src.core.code_workspace import CodeWorkspace


def make_api():
    return webview_app.JsApi.__new__(webview_app.JsApi)


def test_explanations_use_local_bridge_without_agent(monkeypatch):
    api = make_api()
    monkeypatch.setattr(webview_app, "explain_command", lambda content: f"Comando: {content}")
    monkeypatch.setattr(webview_app, "explain_error", lambda content: f"Error: {content}")

    assert api.explain_text("command", "ls -la") == "Comando: ls -la"
    assert api.explain_text("error", "Permission denied") == "Error: Permission denied"
    assert "válido" in api.explain_text("other", "texto")


def test_windows_guide_bridge_returns_local_references(monkeypatch):
    expected = [{"id": "task-manager", "windows": "Administrador de tareas"}]
    monkeypatch.setattr(webview_app, "search_windows_guide", lambda query, kind: expected if (query, kind) == ("tareas", "feature") else [])

    assert make_api().get_windows_guide("tareas", "feature") == expected


def test_diagnostic_bridge_returns_checks_and_guided_action(monkeypatch):
    report = {"checks": [{"id": "packages", "status": "warning", "title": "Paquetes", "detail": "Error"}], "problems": 1, "unknown": 0}
    monkeypatch.setattr(webview_app, "diagnose_system", lambda: report)
    monkeypatch.setattr(webview_app, "execute_diagnostic_fix", lambda action: {"success": action == "repair_packages", "message": "Terminal abierta"})

    assert make_api().get_system_diagnostic() == report
    assert make_api().run_diagnostic_fix("repair_packages")["success"] is True
    assert "Paquetes: Error" in make_api().run_action("troubleshooter")


def test_search_installed_apps_returns_serializable_candidates(monkeypatch):
    monkeypatch.setattr(
        webview_app,
        "find_uninstall_candidates",
        lambda query, source: [
            {
                "source": "apt",
                "package": "vlc",
                "name": "VLC media player",
                "score": 1.0,
            }
        ],
    )

    assert make_api().search_installed_apps("vlc", "auto") == [
        {
            "source": "apt",
            "package": "vlc",
            "name": "VLC media player",
            "score": 1.0,
        }
    ]


def test_uninstall_app_opens_validated_interactive_terminal(monkeypatch):
    monkeypatch.setattr(
        webview_app,
        "build_interactive_uninstall_command",
        lambda package, source: ("sudo apt remove vlc", "apt", "vlc"),
    )
    calls = []
    monkeypatch.setattr(
        webview_app,
        "launch_in_terminal",
        lambda command, title: calls.append((command, title)) or (True, "ok"),
    )

    result = make_api().uninstall_app("vlc", "auto")

    assert calls == [("sudo apt remove vlc", "Desinstalar vlc — LinuxMate AI")]
    assert "Revisa el comando" in result


def test_uninstall_app_reports_safety_rejection(monkeypatch):
    def reject(_package, _source):
        raise ValueError("Paquete crítico bloqueado.")

    monkeypatch.setattr(webview_app, "build_interactive_uninstall_command", reject)
    monkeypatch.setattr(
        webview_app,
        "launch_in_terminal",
        lambda *_args: (_ for _ in ()).throw(AssertionError("No debe abrir terminal")),
    )

    assert make_api().uninstall_app("systemd", "auto") == "Paquete crítico bloqueado."


def test_catalog_filters_sources_categories_and_installed_state(monkeypatch):
    monkeypatch.setattr(
        app_catalog,
        "_source_catalog",
        lambda source, query, category, refresh: (
            [
                app_catalog._app("flatpak", "com.visualstudio.code", "Code", "Editor", "development"),
                app_catalog._app("flatpak", "io.podman_desktop.PodmanDesktop", "Podman", "Contenedores", "development"),
                app_catalog._app("flatpak", "org.videolan.VLC", "VLC", "Video", "multimedia"),
            ],
            "",
        ),
    )
    monkeypatch.setattr(
        app_catalog,
        "_installed_packages",
        lambda force=False: {
            "apt": {"git"},
            "snap": set(),
            "flatpak": {"io.podman_desktop.PodmanDesktop"},
        },
    )

    result = app_catalog.get_catalog(source="flatpak", category="development", limit=20)

    assert {app["package"] for app in result["apps"]} == {
        "com.visualstudio.code",
        "io.podman_desktop.PodmanDesktop",
    }
    installed = {app["package"]: app["installed"] for app in result["apps"]}
    assert installed["io.podman_desktop.PodmanDesktop"] is True
    assert installed["com.visualstudio.code"] is False


def test_catalog_includes_application_icon(monkeypatch):
    monkeypatch.setattr(
        app_catalog,
        "_source_catalog",
        lambda source, query, category, refresh: ([app_catalog._app("apt", "firefox", "Firefox", "Web", "internet")], ""),
    )
    monkeypatch.setattr(
        app_catalog,
        "_installed_packages",
        lambda force=False: {"apt": set(), "snap": set(), "flatpak": set()},
    )
    monkeypatch.setattr(
        app_catalog,
        "_icon_data",
        lambda app: f"data:image/png;base64,icon-{app['package']}",
    )

    result = app_catalog.get_catalog(source="apt", query="firefox", limit=4)

    assert result["apps"][0]["icon"] == "data:image/png;base64,icon-firefox"


def test_catalog_search_puts_exact_application_before_technical_packages(monkeypatch):
    monkeypatch.setattr(
        app_catalog,
        "_source_catalog",
        lambda source, query, category, refresh: ([
            app_catalog._app("apt", "libvlc-dev", "libvlc-dev", "Development files", "development"),
            app_catalog._app("apt", "vlc-plugin-base", "vlc-plugin-base", "VLC plugin", "multimedia"),
            app_catalog._app("apt", "vlc", "VLC", "Media player", "multimedia"),
        ], ""),
    )
    monkeypatch.setattr(
        app_catalog,
        "_installed_packages",
        lambda force=False: {"apt": {"vlc"}, "snap": set(), "flatpak": set()},
    )

    result = app_catalog.get_catalog(source="apt", query="vlc", limit=10)

    assert result["apps"][0]["package"] == "vlc"
    assert result["apps"][0]["installed"] is True


def test_catalog_lists_only_real_packages_and_paginates(monkeypatch):
    packages = [app_catalog._app("apt", f"example-{n}", f"Example {n}", "Package", "other") for n in range(60)]
    monkeypatch.setattr(app_catalog, "_source_catalog", lambda source, query, category, refresh: (packages, ""))
    monkeypatch.setattr(app_catalog, "_installed_packages", lambda force=False: {"apt": set(), "snap": set(), "flatpak": set()})
    monkeypatch.setattr(app_catalog, "_icon_data", lambda app: "")

    first = app_catalog.get_catalog(source="apt", limit=16)
    second = app_catalog.get_catalog(source="apt", offset=16, limit=16)

    assert first["total"] == 60
    assert first["has_more"] is True
    assert len(second["apps"]) == 16
    assert {app["package"] for app in first["apps"]}.isdisjoint({app["package"] for app in second["apps"]})
    assert "firefox" not in {app["package"] for app in first["apps"]}


def test_catalog_mixes_package_sources_on_first_page(monkeypatch):
    packages = {
        "apt": [
            app_catalog._app("apt", "firefox", "Firefox", "Browser", "internet"),
            app_catalog._app("apt", "libreoffice", "LibreOffice", "Office", "office"),
        ],
        "snap": [
            app_catalog._app("snap", "code", "Code", "Editor", "development"),
            app_catalog._app("snap", "spotify", "Spotify", "Music", "multimedia"),
        ],
        "flatpak": [
            app_catalog._app("flatpak", "org.mozilla.firefox", "Firefox", "Browser", "internet"),
            app_catalog._app("flatpak", "org.libreoffice.LibreOffice", "LibreOffice", "Office", "office"),
        ],
    }
    monkeypatch.setattr(app_catalog.shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(app_catalog, "_source_catalog", lambda source, query, category, refresh: (packages.get(source, []), ""))
    monkeypatch.setattr(app_catalog, "_installed_packages", lambda force=False: {key: set() for key in packages})
    monkeypatch.setattr(app_catalog, "_icon_data", lambda app: "")

    result = app_catalog.get_catalog(limit=6)

    assert [app["source"] for app in result["apps"]] == ["apt", "snap", "flatpak", "apt", "snap", "flatpak"]


def test_apt_catalog_uses_available_package_metadata(monkeypatch):
    monkeypatch.setattr(app_catalog, "_run_checked", lambda args, timeout=12: ("firefox - Web browser\nlibfoo-dev - Files for development\n", ""))

    apps, notice = app_catalog._load_apt()

    assert notice == ""
    assert [app["package"] for app in apps] == ["firefox", "libfoo-dev"]
    assert apps[0]["name"] == "Firefox"


def test_flatpak_catalog_uses_configured_remote_and_offline_fallback(monkeypatch):
    calls = []

    def remote_ls(args, timeout=12):
        calls.append(args)
        if "--cached" not in args:
            return "", "network unavailable"
        return "org.videolan.VLC\tVLC\tMedia player\tflathub\n", ""

    monkeypatch.setattr(app_catalog, "_run_checked", remote_ls)
    apps, notice = app_catalog._load_flatpak()

    assert apps[0]["origin"] == "flathub"
    assert apps[0]["package"] == "org.videolan.VLC"
    assert "guardados" in notice
    assert any("--cached" in call for call in calls)


def test_snap_catalog_reads_store_metadata_and_icon(monkeypatch):
    requests = []

    class StoreResponse:
        status = 200

        def read(self):
            return json.dumps({"result": [{
                "name": "sample-browser",
                "title": "Sample Browser",
                "summary": "Web browser for Linux",
                "icon": "https://dashboard.snapcraft.io/site_media/appmedia/icon.png",
                "publisher": {"validation": "verified"},
                "categories": [{"name": "productivity"}],
            }]}).encode()

    class StoreConnection:
        def __init__(self, host, timeout):
            pass

        def request(self, method, path):
            requests.append((method, path))

        def getresponse(self):
            return StoreResponse()

        def close(self):
            pass

    monkeypatch.setattr(app_catalog, "_SnapdConnection", StoreConnection)
    apps = app_catalog._snapd_find("browser", "internet")

    assert apps[0]["category"] == "internet"
    assert apps[0]["verified"] is True
    assert apps[0]["icon"].startswith("https://dashboard.snapcraft.io/")
    assert requests == [("GET", "/v2/find?q=browser")]


def test_snap_browse_combines_store_sections(monkeypatch):
    seen = []

    def find(query, category):
        seen.append(category)
        return [
            app_catalog._app("snap", "shared-app", "Shared", "", "other"),
            app_catalog._app("snap", f"app-{category}", category, "", "other"),
        ]

    monkeypatch.setattr(app_catalog, "_snapd_find", find)

    apps, notice = app_catalog._load_snap("", "all")

    assert notice == ""
    assert len(apps) == 11
    assert {app["package"] for app in apps} == {"shared-app"} | {f"app-{category}" for category in seen}
    assert {"all", "internet", "games", "development"}.issubset(seen)


def test_installed_apt_excludes_removed_packages(monkeypatch):
    app_catalog.clear_installed_cache()
    monkeypatch.setattr(app_catalog.shutil, "which", lambda command: None)
    monkeypatch.setattr(
        app_catalog,
        "_run",
        lambda args, timeout=8: "install ok installed\tvlc\ndeinstall ok config-files\told-app\n",
    )

    installed = app_catalog._installed_packages(force=True)

    assert installed["apt"] == {"vlc"}
    app_catalog.clear_installed_cache()


def test_catalog_install_previews_then_confirms_selected_package_source(monkeypatch):
    calls = []
    monkeypatch.setattr(webview_app.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        webview_app,
        "launch_in_terminal",
        lambda command, title: calls.append((command, title)) or (True, "ok"),
    )
    monkeypatch.setattr(webview_app, "clear_installed_cache", lambda: None)

    api = make_api()
    result = api.install_catalog_app("org.videolan.VLC", "flatpak", "VLC")

    assert result["success"] is True
    assert result["preview"]["package"] == "org.videolan.VLC"
    assert result["preview"]["source"] == "flatpak"
    assert result["preview"]["command"] == "flatpak install org.videolan.VLC"
    assert calls == []

    installed = api.confirm_catalog_app_install(result["preview"]["token"], True)
    assert installed["success"] is True
    assert calls == [("flatpak install org.videolan.VLC", "Instalando VLC — LinuxMate AI")]


def test_catalog_install_cancel_consumes_preview_without_launch(monkeypatch):
    monkeypatch.setattr(webview_app.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(webview_app, "launch_in_terminal", lambda *_args: (_ for _ in ()).throw(AssertionError("No debe abrir terminal")))

    api = make_api()
    preview = api.install_catalog_app("vlc", "apt", "VLC")["preview"]
    result = api.confirm_catalog_app_install(preview["token"], False)

    assert result["cancelled"] is True
    assert "expiró" in api.confirm_catalog_app_install(preview["token"], True)["message"]


def test_quick_install_requires_confirmation(monkeypatch):
    calls = []
    monkeypatch.setattr(webview_app, "launch_in_terminal", lambda command, title: calls.append((command, title)) or (True, "ok"))
    api = make_api()

    preview = api.install_app("steam")["preview"]

    assert calls == []
    assert "sudo apt install -y steam" in preview["command"]
    assert api.confirm_catalog_app_install(preview["token"], True)["success"] is True
    assert len(calls) == 1


def test_code_workspace_api_exposes_review_then_apply(tmp_path):
    api = make_api()
    api._code_workspace = CodeWorkspace(tmp_path / "projects")

    created = api.create_code_project("api-demo", "python")
    assert created["success"] is True
    assert api.list_code_files("api-demo")["files"] == ["main.py", "README.md", "test_main.py"]
    original = api.read_code_file("api-demo", "main.py")["content"]
    modified = original.replace("Hola desde LinuxMate", "Hola desde API")
    preview = api.preview_code_change("api-demo", "main.py", modified)
    assert "Hola desde API" in preview["diff"]
    assert api.read_code_file("api-demo", "main.py")["content"] == original

    applied = api.apply_code_change(preview["token"], True)
    assert applied["success"] is True
    assert api.read_code_file("api-demo", "main.py")["content"] == modified


def test_code_workspace_api_reports_unsafe_paths(tmp_path):
    api = make_api()
    api._code_workspace = CodeWorkspace(tmp_path / "projects")
    api.create_code_project("safe", "web")

    result = api.read_code_file("safe", "../../outside.txt")

    assert result["success"] is False
    assert "ruta" in result["message"].lower()


def test_ai_code_request_returns_reviewable_diff_without_writing(tmp_path):
    api = make_api()
    api._code_workspace = CodeWorkspace(tmp_path / "projects")
    api.create_code_project("tutor", "python")
    current = api.read_code_file("tutor", "main.py")["content"]
    proposed = current.replace("Hola desde LinuxMate", "Hola, estudiante")
    requests = []
    api.agent = SimpleNamespace(
        provider="groq",
        model="test-model",
        api_key="test-secret",
        _client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: requests.append(kwargs) or SimpleNamespace(choices=[
                SimpleNamespace(message=SimpleNamespace(content=proposed))
            ])
        ))),
    )

    preview = api.request_code_change("tutor", "main.py", "Cambia el saludo", True)

    assert preview["success"] is True
    assert "Hola, estudiante" in preview["diff"]
    assert "Contenido actual" in requests[0]["messages"][1]["content"]
    assert api.read_code_file("tutor", "main.py")["content"] == current
    assert api.apply_code_change(preview["token"], True)["success"] is True
    assert api.read_code_file("tutor", "main.py")["content"] == proposed


def test_ai_code_request_blocks_likely_secrets_before_provider_call(tmp_path):
    api = make_api()
    api._code_workspace = CodeWorkspace(tmp_path / "projects")
    api.create_code_project("secret-demo", "python")
    project_file = tmp_path / "projects" / "secret-demo" / "main.py"
    project_file.write_text('API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"\n', encoding="utf-8")
    api.agent = SimpleNamespace(_client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **_kwargs: pytest.fail("No debe enviar secretos al proveedor")
    ))))

    result = api.request_code_change("secret-demo", "main.py", "Explica la clave", True)

    assert result["success"] is False
    assert "clave" in result["message"].lower()


def test_ai_code_request_requires_explicit_consent(tmp_path):
    api = make_api()
    api._code_workspace = CodeWorkspace(tmp_path / "projects")
    api.create_code_project("consent-demo", "python")
    api.agent = SimpleNamespace(_client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **_kwargs: pytest.fail("No debe llamar al proveedor sin consentimiento")
    ))))

    result = api.request_code_change("consent-demo", "main.py", "Agrega una función")

    assert result["success"] is False
    assert "Confirma" in result["message"]


def test_catalog_install_rejects_shell_syntax(monkeypatch):
    monkeypatch.setattr(
        webview_app,
        "launch_in_terminal",
        lambda *_args: (_ for _ in ()).throw(AssertionError("No debe abrir terminal")),
    )

    result = make_api().install_catalog_app("vlc; reboot", "apt", "VLC")

    assert result["success"] is False
    assert "no es seguro" in result["message"]


def test_setup_wizard_generates_distro_aware_plan_and_runs_action(monkeypatch):
    from src.gui import setup_wizard

    # 1. Verify against real DistroInfo (no mock) so attribute names match DistroInfo
    real_plan = make_api().get_setup_plan("daily")
    assert real_plan["success"] is True
    assert isinstance(real_plan["distro"]["family"], str)

    # 2. Verify Fedora / DNF adaptation and check_drivers report
    monkeypatch.setattr(
        setup_wizard,
        "detect_distro",
        lambda: SimpleNamespace(
            id="fedora",
            name="Fedora Linux",
            pretty_name="Fedora Linux 41",
            version_id="41",
            family="fedora",
            native_package_manager="dnf",
            available_package_managers=["dnf", "flatpak"],
        ),
    )
    plan = make_api().get_setup_plan("development")
    assert plan["success"] is True
    assert plan["distro"]["package_manager"] == "dnf"
    step_ids = [step["id"] for step in plan["steps"]]
    assert {"updates", "codecs", "locale", "drivers", "tools", "firewall", "backup"} <= set(step_ids)
    updates_step = next(step for step in plan["steps"] if step["id"] == "updates")
    assert "dnf upgrade" in updates_step["command"]

    launched = []
    monkeypatch.setattr(
        setup_wizard,
        "launch_in_terminal",
        lambda cmd, title: launched.append((cmd, title)) or (True, "Terminal lanzada"),
    )
    res = make_api().run_setup_action("update_distro", "development")
    assert res["success"] is True
    assert launched and "dnf upgrade" in launched[0][0]

    drv_res = make_api().run_setup_action("check_drivers", "development")
    assert drv_res["success"] is True
    assert isinstance(drv_res.get("driver_report"), list) and len(drv_res["driver_report"]) >= 1


def test_problem_solver_boot_guide_and_guided_repairs(monkeypatch):
    from src.gui import problem_solver

    guides_resp = make_api().get_problem_guides()
    assert guides_resp["success"] is True
    guide_ids = {g["id"] for g in guides_resp["guides"]}
    assert "boot" in guide_ids
    for guide in guides_resp["guides"]:
        assert any(a.get("kind") == "repair" for a in guide.get("actions", []))

    checks_resp = make_api().run_problem_checks("boot")
    assert checks_resp["success"] is True
    assert len(checks_resp["results"]) >= 2

    launched = []
    monkeypatch.setattr(
        problem_solver,
        "launch_in_terminal",
        lambda cmd, title: launched.append((cmd, title)) or (True, "Terminal lanzada"),
    )
    repair_resp = make_api().run_problem_action("restart_network")
    assert repair_resp["success"] is True
    assert launched and "NetworkManager" in launched[0][0]


def test_resource_monitor_battery_startup_toggle_and_stop_process(monkeypatch, tmp_path):
    import os
    from pathlib import Path

    autostart_dir = tmp_path / ".config" / "autostart"
    autostart_dir.mkdir(parents=True)
    desktop_file = autostart_dir / "demo-app.desktop"
    desktop_file.write_text(
        "[Desktop Entry]\nType=Application\nName=Demo App\nExec=demo-app\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    toggle_off = make_api().toggle_startup_app("demo-app.desktop", False)
    assert toggle_off["success"] is True
    assert "X-GNOME-Autostart-enabled=false" in desktop_file.read_text(encoding="utf-8")

    toggle_on = make_api().toggle_startup_app("demo-app.desktop", True)
    assert toggle_on["success"] is True
    assert "X-GNOME-Autostart-enabled=true" in desktop_file.read_text(encoding="utf-8")

    # Reject stopping LinuxMate's own PID
    self_stop = make_api().stop_user_process(os.getpid())
    assert self_stop["success"] is False


def test_search_installed_apps_accepts_dnf_pacman_zypper_and_desktop(monkeypatch):
    api = make_api()
    monkeypatch.setattr(
        webview_app,
        "find_uninstall_candidates",
        lambda query, source="auto": [
            {"package": "vlc", "name": "VLC", "source": source, "score": 1.0}
        ],
    )
    for src in ("dnf", "pacman", "zypper", "desktop"):
        resp = api.search_installed_apps("vlc", src)
        assert isinstance(resp, list) and len(resp) == 1
        assert resp[0]["source"] == src

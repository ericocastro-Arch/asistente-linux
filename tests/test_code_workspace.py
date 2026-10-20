"""Pruebas del workspace de programación y sus límites de acceso."""

from pathlib import Path

import pytest

from src.core.code_workspace import CodeWorkspace, WorkspaceError


def test_create_project_from_supported_templates(tmp_path):
    workspace = CodeWorkspace(tmp_path / "projects")

    project = workspace.create_project("aprendo-python", "python")
    web = workspace.create_project("mi-web", "web")
    bash = workspace.create_project("scripts", "bash")

    assert (Path(project["project"]["path"]) / "main.py").is_file()
    assert (Path(web["project"]["path"]) / "index.html").is_file()
    assert (Path(bash["project"]["path"]) / "script.sh").is_file()
    assert workspace.list_projects()["projects"] == [
        {"name": "aprendo-python", "path": str(tmp_path / "projects" / "aprendo-python")},
        {"name": "mi-web", "path": str(tmp_path / "projects" / "mi-web")},
        {"name": "scripts", "path": str(tmp_path / "projects" / "scripts")},
    ]


@pytest.mark.parametrize("name", ["../fuera", "/tmp/externo", "con espacios", "a" * 49])
def test_reject_unsafe_project_names(tmp_path, name):
    with pytest.raises(WorkspaceError):
        CodeWorkspace(tmp_path).create_project(name, "python")


def test_reject_existing_project_and_unknown_template(tmp_path):
    workspace = CodeWorkspace(tmp_path)
    workspace.create_project("demo", "python")

    with pytest.raises(WorkspaceError, match="Ya existe"):
        workspace.create_project("demo", "web")
    with pytest.raises(WorkspaceError, match="Plantilla"):
        workspace.create_project("otra", "unknown")


def test_file_access_stays_inside_project_and_rejects_credentials(tmp_path):
    workspace = CodeWorkspace(tmp_path / "projects")
    workspace.create_project("demo", "python")

    with pytest.raises(WorkspaceError):
        workspace.read_file("demo", "../../outside.txt")
    with pytest.raises(WorkspaceError, match="credenciales"):
        workspace.read_file("demo", ".env")

    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    link = tmp_path / "projects" / "demo" / "shortcut.txt"
    link.symlink_to(outside)
    with pytest.raises(WorkspaceError, match="enlaces simbólicos"):
        workspace.read_file("demo", "shortcut.txt")


def test_diff_is_reviewed_before_apply_and_is_one_use(tmp_path):
    workspace = CodeWorkspace(tmp_path / "projects")
    workspace.create_project("demo", "python")
    original = workspace.read_file("demo", "main.py")["content"]
    proposed = original.replace("Hola desde LinuxMate", "Hola desde el proyecto")

    preview = workspace.propose_file_change("demo", "main.py", proposed)
    assert "-    print(\"Hola desde LinuxMate\")" in preview["diff"]
    assert workspace.read_file("demo", "main.py")["content"] == original

    result = workspace.apply_proposed_change(preview["token"], True)
    assert result["success"] is True
    assert workspace.read_file("demo", "main.py")["content"] == proposed
    with pytest.raises(WorkspaceError, match="expiró"):
        workspace.apply_proposed_change(preview["token"], True)


def test_reject_or_stale_diff_does_not_overwrite_file(tmp_path):
    workspace = CodeWorkspace(tmp_path / "projects")
    workspace.create_project("demo", "python")
    preview = workspace.propose_file_change("demo", "main.py", "print('proposed')\n")
    rejected = workspace.apply_proposed_change(preview["token"], False)
    assert rejected["cancelled"] is True
    assert "Hola desde LinuxMate" in workspace.read_file("demo", "main.py")["content"]

    preview = workspace.propose_file_change("demo", "main.py", "print('proposed')\n")
    (tmp_path / "projects" / "demo" / "main.py").write_text("changed externally\n", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="cambió"):
        workspace.apply_proposed_change(preview["token"], True)
    assert workspace.read_file("demo", "main.py")["content"] == "changed externally\n"


def test_new_file_proposal_is_atomic_and_private(tmp_path):
    workspace = CodeWorkspace(tmp_path / "projects")
    workspace.create_project("demo", "python")
    preview = workspace.propose_file_change("demo", "notes/todo.txt", "Primera tarea\n")

    workspace.apply_proposed_change(preview["token"], True)

    target = tmp_path / "projects" / "demo" / "notes" / "todo.txt"
    assert target.read_text(encoding="utf-8") == "Primera tarea\n"
    assert target.stat().st_mode & 0o777 == 0o600


def test_checkpoints_create_list_and_restore(tmp_path):
    workspace = CodeWorkspace(tmp_path / "projects")
    workspace.create_project("demo", "python")
    original = workspace.read_file("demo", "main.py")["content"]

    cp = workspace.create_checkpoint("demo", "Proyecto inicial")
    assert cp["success"] is True

    workspace.write_file("demo", "main.py", "print('modificado')\n")
    assert workspace.read_file("demo", "main.py")["content"] == "print('modificado')\n"

    listed = workspace.list_checkpoints("demo")
    assert len(listed["checkpoints"]) == 1
    assert listed["checkpoints"][0]["label"] == "Proyecto inicial"

    restored = workspace.restore_checkpoint("demo", cp["checkpoint"]["id"])
    assert restored["success"] is True
    assert workspace.read_file("demo", "main.py")["content"] == original


def test_dev_orchestrator_recipes_and_error_translation(tmp_path):
    from src.core.dev_agent import DevOrchestrator, translate_dev_error

    workspace = CodeWorkspace(tmp_path / "projects")
    orch = DevOrchestrator(workspace)

    ensured = orch.ensure_starter_project()
    assert any(p["name"] == "organizador_descargas" for p in ensured["projects"])
    files = workspace.list_files("organizador_descargas")["files"]
    assert "main.py" in files and "organizar.py" in files and "config.json" in files

    chat_res = orch.chat_with_agent(
        project="organizador_descargas",
        active_file="main.py",
        message="Haz que también ignore duplicados",
        agent=None,
    )
    assert chat_res["success"] is True
    assert chat_res["proposal"] is not None
    assert chat_res["proposal"]["token"]

    err_info = translate_dev_error("  File 'main.py', line 7\nSyntaxError: '[' was never closed")
    assert err_info["line"] == 7
    assert "error de escritura" in err_info["cause"].lower()


def test_search_in_project_and_standalone_dev_window(tmp_path, monkeypatch):
    from src.core.dev_agent import DevOrchestrator
    import src.gui.webview_app as webview_mod

    workspace = CodeWorkspace(tmp_path / "projects")
    orch = DevOrchestrator(workspace)
    orch.ensure_starter_project()

    found = orch.search_in_project("organizador_descargas", "cargar_categorias")
    assert found["success"] is True
    assert any(hit["file"] == "main.py" for hit in found["matches"])

    created_windows = []

    class DummyHook:
        def __init__(self):
            self.callbacks = []

        def __iadd__(self, cb):
            self.callbacks.append(cb)
            return self

    class DummyEvents:
        def __init__(self):
            self.closed = DummyHook()

    class DummyWindow:
        def __init__(self, title, url):
            self.title = title
            self.url = url
            self.events = DummyEvents()
            self.restored = False

        def restore(self):
            self.restored = True

        def show(self):
            pass

    def fake_create_window(title, url="", **kwargs):
        win = DummyWindow(title, url)
        created_windows.append(win)
        return win

    monkeypatch.setattr(webview_mod.webview, "create_window", fake_create_window)

    api = webview_mod.JsApi.__new__(webview_mod.JsApi)
    api._code_workspace = workspace
    api._dev_orch = orch

    res1 = api.open_dev_window()
    assert res1["success"] is True
    assert len(created_windows) == 1
    assert "dev.html" in created_windows[0].url

    # Segunda llamada restaura la misma ventana sin duplicarla
    res2 = api.open_dev_window()
    assert res2["success"] is True
    assert len(created_windows) == 1
    assert created_windows[0].restored is True

    status = api.get_dev_status()
    assert status["success"] is True
    assert len(status["providers"]) >= 10
    assert any(p["id"] == "anthropic" for p in status["providers"])
    assert any(p["id"] == "openai" for p in status["providers"])
    assert any(p["id"] == "groq" for p in status["providers"])


def test_dev_orchestrator_all_providers_resilience(tmp_path):
    """Verifica que cualquiera de los 13 proveedores recupere ante 503/404 o falta de soporte de tools."""
    from types import SimpleNamespace
    from src.core.dev_agent import DevOrchestrator
    from src.core.providers import PROVIDERS
    from src.core.settings_manager import PROVIDER_FALLBACK_MODELS

    workspace = CodeWorkspace(tmp_path / "projects")
    orch = DevOrchestrator(workspace)
    orch.ensure_starter_project()

    # Todos los proveedores con clave deben tener modelos de respaldo configurados
    for pid in PROVIDERS:
        assert pid in PROVIDER_FALLBACK_MODELS

    # Simula un proveedor cuyo primer modelo da 503 y cuyo segundo modelo rechaza tools (500/422) pero responde sin tools
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        if kwargs["model"] == "gemini-3.8-flash":
            raise RuntimeError("Error code: 503 - high demand")
        if "tools" in kwargs:
            raise RuntimeError("Error code: 422 - tools not supported for this endpoint")
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="¡Hola! He revisado `main.py` con éxito.",
                        tool_calls=None,
                    )
                )
            ]
        )

    dummy_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    dummy_agent = SimpleNamespace(_client=dummy_client, provider="gemini", model="gemini-3.8-flash")

    res_meta = orch.chat_with_agent(
        project="organizador_descargas",
        active_file="main.py",
        message="que ia eres",
        agent=dummy_agent,
        provider="gemini",
        model="gemini-3.8-flash",
    )
    assert res_meta["success"] is True
    assert not any("leer_archivo" in ev["label"] for ev in res_meta["tool_events"])
    assert calls[-1]["messages"][-1]["content"] == "que ia eres"

    res = orch.chat_with_agent(
        project="organizador_descargas",
        active_file="main.py",
        message="Revisa main.py",
        agent=dummy_agent,
        provider="gemini",
        model="gemini-3.8-flash",
    )
    assert res["success"] is True
    assert "revisado" in res["reply"]
    assert res["model"] == "gemini-2.5-flash"
    assert not any("no disponible" in ev["label"] for ev in res["tool_events"])





"""Regresiones de llamadas reales y arranque de terminal, sin cambiar paquetes."""

import json
import os
import pty
import subprocess
from types import SimpleNamespace

import pytest

from src.core import agent as agent_module
from src.core import tools


def response(*calls, content=""):
    tool_calls = [
        SimpleNamespace(
            id=f"call_{index}",
            function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
        )
        for index, (name, arguments) in enumerate(calls)
    ]
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
        content=content, tool_calls=tool_calls,
    ))])


def make_agent(monkeypatch, responses, history=()):
    pending = iter(responses)
    requests = []

    def create(**kwargs):
        requests.append(kwargs)
        result = next(pending)
        if isinstance(result, Exception):
            raise result
        return result

    agent = agent_module.LinuxAgent.__new__(agent_module.LinuxAgent)
    agent.model = "test-model"
    agent.session_id = 1
    agent._history = [{"role": "system", "content": "test"}, *history]
    agent._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(agent_module, "log_message", lambda *args: None)
    return agent, requests


def test_compatible_provider_preserves_reasoning_and_tool_signature(monkeypatch):
    from openai.types.chat import ChatCompletionMessage
    message = ChatCompletionMessage.model_validate({
        "role": "assistant", "content": "", "reasoning_content": "provider-context",
        "tool_calls": [{"id": "call_1", "type": "function",
                        "function": {"name": "respond_to_user", "arguments": '{"message":"Hola"}'},
                        "extra_content": {"google": {"thought_signature": "test-signature"}}}],
    })
    model, requests = make_agent(monkeypatch, [SimpleNamespace(choices=[SimpleNamespace(message=message)])])
    model.provider = "gemini"
    model.chat("Hola")
    stored = next(item for item in model._history if item.get("tool_calls"))
    assert stored["reasoning_content"] == "provider-context"
    assert stored["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "test-signature"
    assert requests[0]["tool_choice"] == "auto"


@pytest.mark.parametrize("name,args", [
    ("remove_package", {"package_name": "OfficeWebDesktop", "source": "auto"}),
])
def test_agent_returns_actual_action_failure(monkeypatch, name, args):
    call = ("confirm_package_removal", {"confirmed": True}) if name == "remove_package" else (name, args)
    agent, requests = make_agent(monkeypatch, [response(call)])
    if name == "remove_package":
        agent._pending_removal = args
    executed = []

    def execute(tool_name, arguments):
        executed.append((tool_name, arguments))
        return "No se pudo abrir la terminal: error de arranque."

    monkeypatch.setattr(agent_module, "execute_tool", execute)
    assert agent.chat("adelante") == "No se pudo abrir la terminal: error de arranque."
    assert executed == [(name, args)]
    assert len(requests) == 1
    assert requests[0]["tool_choice"] == "required"


def test_agent_previews_install_before_opening_terminal(monkeypatch):
    plan = {
        "source": "apt", "package": "btop", "friendly_name": "btop",
        "command": "sudo apt install btop",
    }
    agent, _ = make_agent(monkeypatch, [
        response(("install_program", {"program_name": "btop"})),
        response(("confirm_pending_action", {"confirmed": True})),
    ])
    monkeypatch.setattr(tools, "prepare_install_program", lambda *_args: plan)
    executed = []
    monkeypatch.setattr(
        agent_module, "execute_tool",
        lambda name, args: executed.append((name, args)) or "Instalación iniciada.",
    )

    preview = agent.chat("instala btop")
    assert "sudo apt install btop" in preview
    assert "¿Confirmas" in preview
    assert executed == []

    assert agent.chat("sí") == "Instalación iniciada."
    assert executed[0][0] == "install_program"
    assert executed[0][1]["_prepared_install_plan"] == plan


def test_agent_does_not_execute_rejected_install(monkeypatch):
    agent, _ = make_agent(monkeypatch, [
        response(("install_program", {"program_name": "btop"})),
        response(("confirm_pending_action", {"confirmed": False})),
    ])
    plan = {"source": "apt", "package": "btop", "friendly_name": "btop", "command": "sudo apt install btop"}
    monkeypatch.setattr(tools, "prepare_install_program", lambda *_args: plan)
    monkeypatch.setattr(agent_module, "execute_tool", lambda *_args: pytest.fail("No debe ejecutar"))

    assert "Vista previa" in agent.chat("instala btop")
    assert "cancelada" in agent.chat("no").lower()


def test_agent_retries_unexecuted_success_as_a_real_tool_call(monkeypatch):
    agent, requests = make_agent(monkeypatch, [
        response(content="Listo, se abrio la terminal para instalar btop."),
        response(("install_program", {"program_name": "btop"})),
        response(("confirm_pending_action", {"confirmed": True})),
    ])
    calls = []
    monkeypatch.setattr(agent_module, "execute_tool", lambda name, args: calls.append(name) or "Apertura verificada.")
    monkeypatch.setattr(tools, "prepare_install_program", lambda *_args: {
        "source": "apt", "package": "btop", "friendly_name": "btop", "command": "sudo apt install btop",
    })

    assert "Vista previa" in agent.chat("puedes instaalr btop")
    assert agent.chat("sí") == "Apertura verificada."
    assert calls == ["install_program"]
    assert all(request["tool_choice"] == "required" for request in requests)
    assert not any("Listo" in item.get("content", "") for item in agent._history)


def test_agent_does_not_fallback_to_fictional_success(monkeypatch):
    agent, requests = make_agent(monkeypatch, [
        RuntimeError("Invalid tool call"),
        response(content="Listo, se abrio una terminal."),
    ])
    monkeypatch.setattr(agent_module, "execute_tool", lambda *args: pytest.fail("No hay llamada real"))

    with pytest.raises(RuntimeError, match="No se ejecuto"):
        agent.chat("instala btop")
    assert len(requests) == 2
    assert all(request["tools"] and request["tool_choice"] == "required" for request in requests)
    assert len(agent._history) == 1


def test_confirmation_context_survives_provider_retry(monkeypatch):
    confirmation = {"role": "assistant", "content": "Confirmas que quieres desinstalar Zed?"}
    agent, requests = make_agent(monkeypatch, [
        RuntimeError("Invalid tool call"),
        response(("confirm_package_removal", {"confirmed": True})),
    ], history=[confirmation])
    agent._pending_removal = {"package_name": "zed", "source": "auto"}
    monkeypatch.setattr(agent_module, "execute_tool", lambda *args: "Resultado real.")

    assert agent.chat("si") == "Resultado real."
    assert confirmation in requests[1]["messages"]


def test_confirmation_reply_does_not_execute_an_action(monkeypatch):
    agent, _ = make_agent(monkeypatch, [
        response(("remove_package", {"package_name": "zed", "source": "auto"})),
    ])
    monkeypatch.setattr(agent_module, "execute_tool", lambda *args: pytest.fail("Falta confirmacion"))
    assert "Confirmas" in agent.chat("desinstala zed")
    assert agent._pending_removal == {"package_name": "zed", "source": "auto"}


@pytest.mark.parametrize("confirmed", [True, False])
def test_uninstall_requires_confirmation_on_a_later_turn(monkeypatch, confirmed):
    agent, _ = make_agent(monkeypatch, [
        response(
            ("remove_package", {"package_name": "zed"}),
            ("confirm_package_removal", {"confirmed": True}),
        ),
        response(("confirm_package_removal", {"confirmed": confirmed})),
        response(("confirm_package_removal", {"confirmed": True})),
    ])
    calls = []
    monkeypatch.setattr(agent_module, "execute_tool", lambda name, args: calls.append((name, args)) or "Resultado real.")
    assert "Confirmas" in agent.chat("desinstala zed")
    assert calls == []
    result = agent.chat("si" if confirmed else "mejor no")
    assert result == ("Resultado real." if confirmed else "Desinstalacion cancelada.")
    assert calls == ([("remove_package", {"package_name": "zed", "source": "auto"})] if confirmed else [])
    assert agent._pending_removal is None
    assert "No hay" in agent.chat("si")


def test_agent_answers_questions_without_executing_commands(monkeypatch):
    agent, _ = make_agent(monkeypatch, [response(("respond_to_user", {"message": "btop muestra los recursos del equipo."}))])
    monkeypatch.setattr(agent_module, "execute_tool", lambda *args: pytest.fail("Es una pregunta"))
    assert "recursos" in agent.chat("que es btop")


def test_multiple_tool_calls_have_results_before_return(monkeypatch):
    agent, _ = make_agent(monkeypatch, [response(
        ("remove_package", {"package_name": "example"}),
        ("install_program", {"program_name": "btop"}),
    )])
    monkeypatch.setattr(agent_module, "execute_tool", lambda name, args: name)
    monkeypatch.setattr(tools, "prepare_install_program", lambda *_args: {
        "source": "apt", "package": "btop", "friendly_name": "btop", "command": "sudo apt install btop",
    })
    result = agent.chat("adelante")
    assert "¿Confirmas que quieres desinstalar 'example'?" in result
    assert "Vista previa de instalación" in result
    assert agent._pending_removal is None
    assert [item["tool_call_id"] for item in agent._history if item["role"] == "tool"] == ["call_0", "call_1"]


def test_terminal_falls_back_after_startup_failure_and_accepts_input(monkeypatch):
    real_popen = subprocess.Popen
    master, slave = pty.openpty()
    children = []
    commands = []

    def popen(args, **kwargs):
        commands.append(args)
        if args[0].endswith("ptyxis"):
            child = real_popen(["bash", "-c", "echo 'opcion no compatible' >&2; exit 1"], **kwargs)
        else:
            child = real_popen(args[-3:], stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        children.append(child)
        return child

    monkeypatch.setattr(tools.shutil, "which", lambda name: f"/usr/bin/{name}" if name in {"ptyxis", "gnome-terminal"} else None)
    monkeypatch.setattr(tools.subprocess, "Popen", popen)
    monkeypatch.setattr(tools, "TERMINAL_START_TIMEOUT", 1)
    try:
        success, message = tools.launch_in_terminal("read -r value; test \"$value\" = confirmar", title="Prueba")
        assert success, message
        assert "gnome-terminal" in message
        assert len(commands) == 2
        os.write(master, b"confirmar\n\n")
        assert children[-1].wait(timeout=2) == 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=2)
        os.close(master)
        os.close(slave)


def test_terminal_launch_failure_is_reported_with_stderr(monkeypatch):
    real_popen = subprocess.Popen
    monkeypatch.setattr(tools.shutil, "which", lambda name: "/usr/bin/ptyxis" if name == "ptyxis" else None)
    monkeypatch.setattr(tools.subprocess, "Popen", lambda args, **kwargs: real_popen(
        ["bash", "-c", "echo 'Failed to open display' >&2; exit 1"], **kwargs,
    ))
    success, message = tools.launch_in_terminal("true")
    assert not success
    assert "Failed to open display" in message


def test_exited_launcher_without_tty_ack_is_not_success_and_cannot_run_late(monkeypatch, tmp_path):
    real_popen = subprocess.Popen
    captured = []

    def popen(args, **kwargs):
        captured.append(args)
        return real_popen(["true"], **kwargs)

    monkeypatch.setattr(tools.shutil, "which", lambda name: "/usr/bin/ptyxis" if name == "ptyxis" else None)
    monkeypatch.setattr(tools.subprocess, "Popen", popen)
    monkeypatch.setattr(tools, "TERMINAL_START_TIMEOUT", 0.1)
    target = tmp_path / "must-not-run"
    success, _ = tools.launch_in_terminal(f"touch {target}")
    assert not success

    master, slave = pty.openpty()
    try:
        child = real_popen(captured[0][-3:], stdin=slave, stdout=slave, stderr=slave)
        assert child.wait(timeout=2) == 1
        assert not target.exists()
    finally:
        os.close(master)
        os.close(slave)


@pytest.mark.parametrize("action", ["install", "remove"])
def test_package_operations_use_interactive_terminal(monkeypatch, action):
    monkeypatch.setattr(tools, "_resolve_install_source", lambda *args: ("apt", "btop", "btop", ""))
    monkeypatch.setattr(tools, "_resolve_uninstall_source", lambda *args: "apt")
    calls = []
    monkeypatch.setattr(tools, "launch_in_terminal", lambda command, title: calls.append(command) or (True, "Arranque verificado."))
    if action == "install":
        tools.tool_install_program("btop")
    else:
        tools.tool_remove_package("btop")
    assert calls == [f"sudo apt {action} btop"]


@pytest.mark.parametrize(("manager", "expected"), [
    ("dnf", "sudo dnf install btop"),
    ("pacman", "sudo pacman -S btop"),
    ("zypper", "sudo zypper install btop"),
])
def test_install_preview_uses_native_package_manager(monkeypatch, manager, expected):
    from src.core import distro
    monkeypatch.setattr(distro, "get_active_package_manager", lambda: manager)
    monkeypatch.setattr(tools.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(tools, "_native_has_candidate", lambda source, package: source == manager and package == "btop")
    monkeypatch.setattr(tools, "_source_has_package", lambda source, package: source == manager and package == "btop")

    plan = tools.prepare_install_program("btop")

    assert plan["source"] == manager
    assert plan["command"] == expected


def test_undo_and_write_require_confirmation_on_a_later_turn(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    target = tmp_path / "nota.txt"
    agent, _ = make_agent(monkeypatch, [
        response(("write_file", {"file_path": str(target), "content": "hola"})),
        response(("confirm_pending_action", {"confirmed": True})),
        response(("undo_last_change", {})),
        response(("confirm_pending_action", {"confirmed": True})),
    ])

    assert "Plan de acción" in agent.chat("crea nota.txt")
    assert not target.exists()
    assert "Archivo guardado" in agent.chat("sí")
    assert target.read_text(encoding="utf-8") == "hola"

    plan = agent.chat("deshaz el último cambio")
    assert "Plan de acción" in plan and "nota.txt" in plan
    assert target.exists()
    assert "Eliminé" in agent.chat("sí")
    assert not target.exists()


def test_agent_executes_run_diagnostic(monkeypatch):
    agent, requests = make_agent(monkeypatch, [
        response(("run_diagnostic", {"name": "uptime_load"})),
        response(("respond_to_user", {"message": "El sistema está funcionando correctamente."})),
    ])
    ans = agent.chat("cómo va el sistema")
    assert "funcionando correctamente" in ans
    assert len(requests) == 2
    tool_entry = next(m for m in agent._history if m.get("role") == "tool")
    assert "uptime" in tool_entry["content"].lower() or "tiempo" in tool_entry["content"].lower()


def test_agent_enforces_policy_in_readonly_mode(monkeypatch):
    monkeypatch.setenv("SECURITY_MODE", "readonly")
    agent, requests = make_agent(monkeypatch, [
        response(("install_program", {"program_name": "htop"})),
    ])
    ans = agent.chat("instala htop")
    assert "solo lectura" in ans.lower()
    assert "⛔" in ans

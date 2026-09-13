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


@pytest.mark.parametrize("name,args", [
    ("install_program", {"program_name": "btop"}),
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


def test_agent_retries_unexecuted_success_as_a_real_tool_call(monkeypatch):
    agent, requests = make_agent(monkeypatch, [
        response(content="Listo, se abrio la terminal para instalar btop."),
        response(("install_program", {"program_name": "btop"})),
    ])
    calls = []
    monkeypatch.setattr(agent_module, "execute_tool", lambda name, args: calls.append(name) or "Apertura verificada.")

    assert agent.chat("puedes instaalr btop") == "Apertura verificada."
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
    assert agent.chat("adelante") == "¿Confirmas que quieres desinstalar 'example'?\n\ninstall_program"
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

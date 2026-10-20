"""Pruebas de explicaciones locales sin ejecucion de comandos."""

from src.gui.guided_explanations import explain_command, explain_error


def test_install_command_explains_privileges_and_automatic_confirmation():
    result = explain_command("sudo apt install -y vlc")

    assert "Instala los paquetes" in result
    assert "privilegios de administrador" in result
    assert "acepta automáticamente" in result
    assert "No se ejecutó ningún comando" in result


def test_destructive_command_is_marked_as_dangerous():
    result = explain_command("rm -rf /")

    assert "puede dañar o borrar datos" in result
    assert "recursiva" in result


def test_shell_operators_are_explained():
    result = explain_command("ls | grep foto > resultado.txt")

    assert "pasa la salida" in result
    assert "sobrescribe un archivo" in result
    assert "cada orden adicional" in result


def test_multiline_script_is_not_partially_explained_as_one_command():
    result = explain_command("echo seguro\nrm archivo")

    assert "Pega una sola orden" in result
    assert "No se ejecutó nada" in result


def test_unclosed_quote_is_not_treated_as_valid_command():
    assert "comillas sin cerrar" in explain_command("echo 'incompleto")


def test_unknown_command_does_not_claim_to_be_safe():
    result = explain_command("herramienta-desconocida --hacer-algo")

    assert "No tengo una explicación específica" in result
    assert "no he verificado" in result


def test_error_explanations_offer_safe_next_step():
    package_error = explain_error("E: Unable to locate package ejemplo")
    lock_error = explain_error("Could not get lock /var/lib/dpkg/lock-frontend")

    assert "repositorios configurados" in package_error
    assert "No se ejecutó ninguna reparación" in package_error
    assert "No borres el archivo de bloqueo" in lock_error


def test_unknown_or_oversized_error_never_invents_repair():
    assert "No reconozco este error" in explain_error("fallo xyz sin detalles")
    assert "demasiado largo" in explain_error("x" * 4001)

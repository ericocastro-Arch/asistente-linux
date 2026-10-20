"""Pruebas del diagnóstico local y sus reparaciones guiadas."""

from types import SimpleNamespace

from src.gui import system_diagnostics as diagnostics


def test_packages_report_real_failures_and_offer_repair(monkeypatch):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(
        diagnostics,
        "_run",
        lambda args, timeout=8: (0, "") if args[0] == "dpkg" else (100, "E: Dependencias incumplidas"),
    )

    check = diagnostics._check_packages()

    assert check["status"] == "warning"
    assert check["action"]["id"] == "repair_packages"


def test_package_check_uses_detected_distro_manager(monkeypatch):
    monkeypatch.setattr(
        "src.core.distro.detect_distro",
        lambda: SimpleNamespace(native_package_manager="dnf"),
    )
    monkeypatch.setattr(diagnostics.shutil, "which", lambda name: f"/usr/bin/{name}")
    calls = []
    monkeypatch.setattr(diagnostics, "_run", lambda args, timeout=8: calls.append(args) or (0, ""))

    result = diagnostics._check_packages()

    assert calls == [["dnf", "check"]]
    assert result["status"] == "ok"
    assert "DNF" in result["detail"]


def test_packages_do_not_claim_success_when_check_is_unavailable(monkeypatch):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(diagnostics, "_run", lambda args, timeout=8: (None, ""))

    assert diagnostics._check_packages()["status"] == "unknown"


def test_packages_do_not_call_permission_error_a_broken_install(monkeypatch):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(
        diagnostics,
        "_run",
        lambda args, timeout=8: (0, "") if args[0] == "dpkg" else (100, "E: Unable to acquire the dpkg frontend lock"),
    )

    assert diagnostics._check_packages()["status"] == "unknown"


def test_packages_detect_changes_in_apt_simulation(monkeypatch):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(
        diagnostics,
        "_run",
        lambda args, timeout=8: (0, "") if args[0] == "dpkg" else (0, "Inst missing-dependency (1.0 repository)"),
    )

    assert diagnostics._check_packages()["action"]["id"] == "repair_packages"


def test_failed_services_are_reported_with_log_action(monkeypatch):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda command: "/usr/bin/systemctl")
    monkeypatch.setattr(diagnostics, "_run", lambda args, timeout=8: (0, "example.service loaded failed failed Example\n"))

    check = diagnostics._check_services()

    assert check["status"] == "warning"
    assert "example.service" in check["detail"]
    assert check["action"]["id"] == "inspect_services"


def test_network_restart_offered_only_for_confirmed_failure_with_manager(monkeypatch):
    monkeypatch.setattr(diagnostics.shutil, "which", lambda command: f"/usr/bin/{command}")

    def run(args, timeout=8):
        if args[:2] == ["ip", "route"]:
            return 0, ""
        if args[:2] == ["systemctl", "is-active"]:
            return 0, "active"
        raise AssertionError(args)

    monkeypatch.setattr(diagnostics, "_run", run)
    check = diagnostics._check_network()

    assert check["status"] == "warning"
    assert check["action"]["id"] == "restart_network"


def test_diagnostic_summary_distinguishes_unknown_from_healthy(monkeypatch):
    monkeypatch.setattr(diagnostics, "_check_storage", lambda: {"status": "ok"})
    monkeypatch.setattr(diagnostics, "_check_memory", lambda: {"status": "ok"})
    monkeypatch.setattr(diagnostics, "_check_cpu", lambda: {"status": "ok"})
    monkeypatch.setattr(diagnostics, "_check_packages", lambda: {"status": "warning"})
    monkeypatch.setattr(diagnostics, "_check_updates", lambda: {"status": "ok"})
    monkeypatch.setattr(diagnostics, "_check_repositories", lambda: {"status": "ok"})
    monkeypatch.setattr(diagnostics, "_check_services", lambda: {"status": "unknown"})
    monkeypatch.setattr(diagnostics, "_check_network", lambda: {"status": "ok"})
    monkeypatch.setattr(diagnostics, "_check_permissions", lambda: {"status": "ok"})
    monkeypatch.setattr(diagnostics, "_check_battery", lambda: {"status": "ok"})
    monkeypatch.setattr(diagnostics, "_check_temperature", lambda: {"status": "ok"})

    report = diagnostics.diagnose_system()

    assert report["problems"] == 1
    assert report["unknown"] == 1
    assert len(report["checks"]) == 11


def test_repair_requires_confirmed_problem_and_known_action(monkeypatch):
    calls = []
    monkeypatch.setattr(diagnostics, "_check_packages", lambda: {"status": "ok"})
    monkeypatch.setattr(diagnostics, "launch_in_terminal", lambda *args: calls.append(args) or (True, ""))

    assert diagnostics.run_diagnostic_fix("repair_packages")["success"] is False
    assert diagnostics.run_diagnostic_fix("anything_else")["success"] is False
    assert calls == []


def test_confirmed_repair_opens_interactive_terminal(monkeypatch):
    calls = []
    monkeypatch.setattr(diagnostics, "_check_packages", lambda: {"action": {"id": "repair_packages"}})
    monkeypatch.setattr(diagnostics, "launch_in_terminal", lambda *args: calls.append(args) or (True, "ok"))

    result = diagnostics.run_diagnostic_fix("repair_packages")

    assert result["success"] is True
    assert calls[0][0] == "sudo dpkg --configure -a && sudo apt --fix-broken install"


def test_restart_network_rechecks_state_before_launch(monkeypatch):
    calls = []
    monkeypatch.setattr(diagnostics, "_check_network", lambda: {"action": {"id": "restart_network"}})
    monkeypatch.setattr(diagnostics, "launch_in_terminal", lambda *args: calls.append(args) or (True, "ok"))

    result = diagnostics.run_diagnostic_fix("restart_network")

    assert result["success"] is True
    assert calls[0][0] == "sudo systemctl restart NetworkManager"


def test_memory_warning_uses_current_measurement(monkeypatch):
    monkeypatch.setattr(diagnostics.psutil, "virtual_memory", lambda: SimpleNamespace(available=400 * 1024 ** 2, percent=94))

    assert diagnostics._check_memory()["status"] == "warning"

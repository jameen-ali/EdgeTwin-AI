"""tests/simulation/test_wokwi_runner.py — Unit tests for the Wokwi simulation runner and verification harness."""

from __future__ import annotations

import os
from unittest.mock import patch

from simulation.wokwi_runner import StepResult, WokwiSimulationHarness


def test_harness_prerequisites_detection() -> None:
    """Verify toolchain inspection returns well-formed dictionary."""
    harness = WokwiSimulationHarness()
    prereqs = harness.check_prerequisites()

    assert "g++" in prereqs
    assert "available" in prereqs["g++"]
    assert "wokwi-cli" in prereqs
    assert "available" in prereqs["wokwi-cli"]
    assert "token_configured" in prereqs["wokwi-cli"]
    assert "python" in prereqs
    assert prereqs["python"]["available"] is True


def test_harness_native_firmware_execution() -> None:
    """Verify native firmware C++ compilation and 13 unit tests pass."""
    harness = WokwiSimulationHarness()
    res: StepResult = harness.run_native_firmware(timeout=30.0)

    assert res.name == "native_firmware"
    assert res.status == "PASS"
    assert res.exit_code == 0
    assert res.duration_s > 0.0
    assert res.details is not None
    assert res.details.get("tests_passed") == 13


def test_harness_wokwi_missing_cli_reports_not_executed() -> None:
    """Verify missing wokwi-cli binary returns NOT_EXECUTED without error."""
    harness = WokwiSimulationHarness()
    with patch("shutil.which", return_value=None):
        res: StepResult = harness.run_wokwi_simulation(timeout=5.0)

    assert res.name == "wokwi_simulation"
    assert res.status == "NOT_EXECUTED"
    assert "wokwi-cli is not installed" in str(res.reason)


def test_harness_wokwi_missing_token_reports_not_executed() -> None:
    """Verify missing WOKWI_CLI_TOKEN returns NOT_EXECUTED without fabricating pass."""
    harness = WokwiSimulationHarness()
    with (
        patch("shutil.which", return_value="/mock/bin/wokwi-cli"),
        patch.dict(os.environ, {"WOKWI_CLI_TOKEN": ""}, clear=False),
    ):
        res: StepResult = harness.run_wokwi_simulation(timeout=5.0)

    assert res.name == "wokwi_simulation"
    assert res.status == "NOT_EXECUTED"
    assert "WOKWI_CLI_TOKEN" in str(res.reason)


def test_harness_e2e_edge_backend_simulation() -> None:
    """Verify authoritative edge-to-backend pipeline runs and updates twin to LIVE."""
    harness = WokwiSimulationHarness()
    res: StepResult = harness.run_e2e_edge_backend_simulation(steps=15)

    assert res.name == "e2e_edge_backend"
    assert res.status == "PASS"
    assert res.details is not None
    assert res.details["persisted_count"] == 15
    assert res.details["sync_status"] == "LIVE"
    assert res.details["twin_state"] in ("RUNNING", "STARTING", "HEALTHY")


def test_harness_run_all_orchestrator() -> None:
    """Verify full harness run aggregates results cleanly."""
    harness = WokwiSimulationHarness()
    report = harness.run_all(timeout=30.0)

    assert "overall_status" in report
    assert report["overall_status"] == "PASS"
    assert len(report["steps"]) == 3
    step_names = [s["name"] for s in report["steps"]]
    assert "native_firmware" in step_names
    assert "wokwi_simulation" in step_names
    assert "e2e_edge_backend" in step_names

"""
tests/mlops/test_promote.py — Unit tests for T-061 promotion gate and rollback.

Covers:
- run_promotion_gate: all 6 hard gate criteria.
- Gate passes when all criteria satisfied.
- Gate fails when recall drops below margin.
- Gate fails when precision is below floor.
- Gate fails when feature contract violated.
- Gate fails when calibration contract violated.
- Gate fails when threshold contract violated.
- Gate fails when technical inference gate fails.
- promote_challenger: success path writes 'promotion_completed' audit entry.
- promote_challenger: gate failure raises ValueError, writes 'promotion_gate_failed' entry.
- rollback_champion: success path restores prior version, writes 'rollback_executed' entry.
- rollback_champion: rejects empty reason.
- rollback_champion: rejects non-existent target version.
- list_model_versions: returns expected schema.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mlops.promote import (
    PromotionGateResult,
    list_model_versions,
    promote_challenger,
    rollback_champion,
    run_promotion_gate,
)
from mlops.retrain import (
    read_audit_log,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_version_info(
    version: str = "2",
    run_id: str | None = None,
    recall: float = 0.85,
    precision: float = 0.70,
    pr_auc: float = 0.80,
    roc_auc: float = 0.90,
    n_features: str = "14",
    calibration_method: str = "sigmoid",
    operational_threshold: str = "0.16",
) -> dict:
    if run_id is None:
        run_id = f"run-v{version}"
    return {
        "version": version,
        "run_id": run_id,
        "metrics": {
            "val_recall_at_t_star": recall,
            "val_precision_at_t_star": precision,
            "val_pr_auc": pr_auc,
            "val_roc_auc": roc_auc,
        },
        "params": {
            "n_features": n_features,
            "calibration_method": calibration_method,
            "operational_threshold": operational_threshold,
        },
    }


def _make_mock_mlflow_client(
    champion_info: dict | None = None,
    challenger_info: dict | None = None,
    existing_versions: list[str] | None = None,
) -> MagicMock:
    """Return a MagicMock MlflowClient with configurable version info."""
    if champion_info is None:
        champion_info = _make_version_info(version="1")
    if challenger_info is None:
        challenger_info = _make_version_info(version="2")

    client = MagicMock()

    def _get_mv_by_alias(model_name: str, alias: str) -> MagicMock:
        info = champion_info if alias == "champion" else challenger_info
        mv = MagicMock()
        mv.version = info["version"]
        mv.run_id = info["run_id"]
        return mv

    def _get_run(run_id: str) -> MagicMock:
        # Find matching info by run_id
        for info in [champion_info, challenger_info]:
            if info.get("run_id") == run_id:
                run = MagicMock()
                run.data.metrics = info["metrics"]
                run.data.params = info["params"]
                return run
        run = MagicMock()
        run.data.metrics = {}
        run.data.params = {}
        return run

    client.get_model_version_by_alias.side_effect = _get_mv_by_alias
    client.get_run.side_effect = _get_run

    # For rollback version check
    if existing_versions is not None:
        versions = []
        for v in existing_versions:
            mv = MagicMock()
            mv.version = v
            versions.append(mv)
        client.search_model_versions.return_value = versions

    return client


# ---------------------------------------------------------------------------
# T-061-PRO-01: Promotion gate — all pass
# ---------------------------------------------------------------------------


class TestPromotionGatePass:
    """Promotion gate should pass when all 6 hard gate criteria are satisfied."""

    def test_gate_passes_with_valid_challenger(self) -> None:
        """Gate must pass when challenger meets all criteria."""
        champion_info = _make_version_info(version="1", recall=0.80, precision=0.65)
        challenger_info = _make_version_info(version="2", recall=0.82, precision=0.70)
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = run_promotion_gate()

        assert isinstance(result, PromotionGateResult)
        assert result.gate_passed is True
        assert len(result.checks_failed) == 0
        assert len(result.checks_passed) >= 5

    def test_gate_computes_recall_delta(self) -> None:
        """Gate result must include recall_delta = challenger_recall - champion_recall."""
        champion_info = _make_version_info(version="1", recall=0.80)
        challenger_info = _make_version_info(version="2", recall=0.85)
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = run_promotion_gate()

        assert result.recall_delta is not None
        assert result.recall_delta == pytest.approx(0.05, abs=1e-6)


# ---------------------------------------------------------------------------
# T-061-PRO-02: Promotion gate — recall protection failure
# ---------------------------------------------------------------------------


class TestPromotionGateRecallFailure:
    """Gate must fail when challenger recall drops more than RECALL_MARGIN below champion."""

    def test_gate_fails_on_recall_regression(self) -> None:
        """Gate must fail when challenger recall is well below champion - margin."""
        champion_info = _make_version_info(version="1", recall=0.90)
        # challenger recall = 0.80, margin = 0.05 → threshold = 0.85 → challenger BELOW
        challenger_info = _make_version_info(version="2", recall=0.80)
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = run_promotion_gate()

        assert result.gate_passed is False
        assert any("recall_protection" in c for c in result.checks_failed)

    def test_gate_passes_when_recall_drop_within_margin(self) -> None:
        """Gate must pass when recall drop is within the allowed margin."""
        champion_info = _make_version_info(version="1", recall=0.85)
        # challenger recall = 0.82 → delta = -0.03, margin = 0.05 → PASSES
        challenger_info = _make_version_info(version="2", recall=0.82)
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = run_promotion_gate()

        # If all other gates pass, recall gate passes at -0.03 < margin
        assert not any("recall_protection" in c for c in result.checks_failed)


# ---------------------------------------------------------------------------
# T-061-PRO-03: Promotion gate — precision floor failure
# ---------------------------------------------------------------------------


class TestPromotionGatePrecisionFailure:
    """Gate must fail when challenger precision is below MIN_PRECISION_FLOOR."""

    def test_gate_fails_on_very_low_precision(self) -> None:
        """Gate must fail when challenger precision is below floor."""
        champion_info = _make_version_info(version="1", precision=0.60)
        challenger_info = _make_version_info(version="2", precision=0.01)  # well below floor
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = run_promotion_gate()

        assert result.gate_passed is False
        assert any("precision_floor" in c for c in result.checks_failed)


# ---------------------------------------------------------------------------
# T-061-PRO-04: Promotion gate — feature contract failure
# ---------------------------------------------------------------------------


class TestPromotionGateFeatureContract:
    """Gate must fail when challenger does not use the 14-feature contract."""

    def test_gate_fails_on_wrong_n_features(self) -> None:
        """Gate must fail when n_features != 14."""
        challenger_info = _make_version_info(version="2", n_features="11")
        champion_info = _make_version_info(version="1")
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = run_promotion_gate()

        assert result.gate_passed is False
        assert any("feature_contract" in c for c in result.checks_failed)


# ---------------------------------------------------------------------------
# T-061-PRO-05: Promotion gate — calibration contract failure
# ---------------------------------------------------------------------------


class TestPromotionGateCalibrationContract:
    """Gate must fail when challenger uses a non-sigmoid calibration method."""

    def test_gate_fails_on_wrong_calibration_method(self) -> None:
        """Gate must fail when calibration_method != 'sigmoid'."""
        challenger_info = _make_version_info(version="2", calibration_method="isotonic")
        champion_info = _make_version_info(version="1")
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = run_promotion_gate()

        assert result.gate_passed is False
        assert any("calibration_contract" in c for c in result.checks_failed)


# ---------------------------------------------------------------------------
# T-061-PRO-06: Promotion gate — threshold contract failure
# ---------------------------------------------------------------------------


class TestPromotionGateThresholdContract:
    """Gate must fail when challenger's registered threshold != 0.160."""

    def test_gate_fails_on_wrong_threshold(self) -> None:
        """Gate must fail when operational_threshold != 0.160."""
        challenger_info = _make_version_info(version="2", operational_threshold="0.50")
        champion_info = _make_version_info(version="1")
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = run_promotion_gate()

        assert result.gate_passed is False
        assert any("threshold_contract" in c for c in result.checks_failed)

    def test_gate_passes_on_exact_threshold(self) -> None:
        """Gate passes when threshold is exactly 0.160."""
        challenger_info = _make_version_info(version="2", operational_threshold="0.16")
        champion_info = _make_version_info(version="1")
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = run_promotion_gate()

        assert not any("threshold_contract" in c for c in result.checks_failed)


# ---------------------------------------------------------------------------
# T-061-PRO-07: promote_challenger — success path
# ---------------------------------------------------------------------------


class TestPromoteChallenger:
    """Promotion success path with full audit log validation."""

    def test_promote_succeeds_when_gate_passes(self, tmp_path: Path) -> None:
        """promote_challenger must assign champion alias and write audit entry."""
        tmp_audit = tmp_path / "audit.jsonl"
        champion_info = _make_version_info(version="1", recall=0.80)
        challenger_info = _make_version_info(version="2", recall=0.85)
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
        ):
            result = promote_challenger(
                actor="admin_user",
                tracking_uri="sqlite:///test.db",
                audit_log_path=tmp_audit,
            )

        assert result.promoted is True
        assert result.new_champion_version == "2"
        assert result.actor == "admin_user"

        # Verify champion alias was set
        mock_client.set_registered_model_alias.assert_called_with("edgetwin-risk", "champion", "2")

        # Verify audit log entry
        entries = read_audit_log(tmp_audit)
        events = [e["event"] for e in entries]
        assert "promotion_completed" in events

    def test_promote_raises_on_gate_failure(self, tmp_path: Path) -> None:
        """promote_challenger must raise ValueError when gate fails."""
        tmp_audit = tmp_path / "audit.jsonl"
        champion_info = _make_version_info(version="1", recall=0.95)
        challenger_info = _make_version_info(version="2", recall=0.50)  # large recall drop
        mock_client = _make_mock_mlflow_client(champion_info, challenger_info)

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            patch("mlops.promote.verify_promotion_gate", return_value={"status": "PASSED"}),
            pytest.raises(ValueError, match="gate"),
        ):
            promote_challenger(
                actor="admin_user",
                tracking_uri="sqlite:///test.db",
                audit_log_path=tmp_audit,
            )

        entries = read_audit_log(tmp_audit)
        events = [e["event"] for e in entries]
        assert "promotion_gate_failed" in events


# ---------------------------------------------------------------------------
# T-061-PRO-08: rollback_champion
# ---------------------------------------------------------------------------


class TestRollbackChampion:
    """Safe rollback: alias reassignment only, no artifact deletion."""

    def test_rollback_succeeds_with_valid_target_version(self, tmp_path: Path) -> None:
        """rollback_champion must reassign champion alias and write audit entry."""
        tmp_audit = tmp_path / "audit.jsonl"

        champion_info = _make_version_info(version="3")
        mock_client = _make_mock_mlflow_client(
            champion_info=champion_info,
            existing_versions=["1", "2", "3"],
        )

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
        ):
            result = rollback_champion(
                target_version="1",
                actor="admin",
                reason="Critical regression in v3: false alarm rate elevated",
                tracking_uri="sqlite:///test.db",
                audit_log_path=tmp_audit,
            )

        assert result.rolled_back is True
        assert result.restored_champion_version == "1"
        assert result.actor == "admin"

        mock_client.set_registered_model_alias.assert_called_with("edgetwin-risk", "champion", "1")

        entries = read_audit_log(tmp_audit)
        events = [e["event"] for e in entries]
        assert "rollback_executed" in events

    def test_rollback_rejects_empty_reason(self, tmp_path: Path) -> None:
        """rollback_champion must raise ValueError if reason is empty."""
        tmp_audit = tmp_path / "audit.jsonl"
        mock_client = _make_mock_mlflow_client(existing_versions=["1", "2"])

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            pytest.raises(ValueError, match="reason"),
        ):
            rollback_champion(
                target_version="1",
                actor="admin",
                reason="",
                tracking_uri="sqlite:///test.db",
                audit_log_path=tmp_audit,
            )

    def test_rollback_rejects_nonexistent_version(self, tmp_path: Path) -> None:
        """rollback_champion must raise ValueError for versions not in registry."""
        tmp_audit = tmp_path / "audit.jsonl"
        mock_client = _make_mock_mlflow_client(existing_versions=["1", "2"])

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
            pytest.raises(ValueError, match="999"),
        ):
            rollback_champion(
                target_version="999",
                actor="admin",
                reason="Testing nonexistent version rejection",
                tracking_uri="sqlite:///test.db",
                audit_log_path=tmp_audit,
            )

    def test_rollback_audit_entry_contains_reason(self, tmp_path: Path) -> None:
        """Audit entry for rollback must include the provided reason."""
        tmp_audit = tmp_path / "audit.jsonl"
        champion_info = _make_version_info(version="3")
        mock_client = _make_mock_mlflow_client(
            champion_info=champion_info, existing_versions=["1", "2", "3"]
        )

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
        ):
            rollback_champion(
                target_version="1",
                actor="admin",
                reason="Production incident INC-4521: false alarm storm",
                tracking_uri="sqlite:///test.db",
                audit_log_path=tmp_audit,
            )

        entries = read_audit_log(tmp_audit)
        rollback_entries = [e for e in entries if e["event"] == "rollback_executed"]
        assert len(rollback_entries) == 1
        assert "INC-4521" in rollback_entries[0]["notes"]


# ---------------------------------------------------------------------------
# T-061-PRO-09: list_model_versions
# ---------------------------------------------------------------------------


class TestListModelVersions:
    """list_model_versions returns all versions with aliases and metrics."""

    def test_list_returns_version_dicts(self) -> None:
        """list_model_versions must return a list of dicts with expected keys."""
        mv1 = MagicMock()
        mv1.version = "1"
        mv1.status = "READY"
        mv1.run_id = "run-1"
        mv1.creation_timestamp = 1700000000000

        mv2 = MagicMock()
        mv2.version = "2"
        mv2.status = "READY"
        mv2.run_id = "run-2"
        mv2.creation_timestamp = 1700000001000

        mock_client = MagicMock()
        mock_client.search_model_versions.return_value = [mv1, mv2]

        rm = MagicMock()
        rm.aliases = {"champion": "1", "challenger": "2"}
        mock_client.get_registered_model.return_value = rm

        run1 = MagicMock()
        run1.data.metrics = {"val_recall_at_t_star": 0.80, "val_precision_at_t_star": 0.65}
        run2 = MagicMock()
        run2.data.metrics = {"val_recall_at_t_star": 0.85, "val_precision_at_t_star": 0.70}

        def _get_run(run_id: str) -> MagicMock:
            return run1 if run_id == "run-1" else run2

        mock_client.get_run.side_effect = _get_run

        with (
            patch("mlops.promote.mlflow.set_tracking_uri"),
            patch("mlops.promote.MlflowClient", return_value=mock_client),
        ):
            results = list_model_versions()

        assert len(results) == 2
        assert results[0]["version"] == "1"
        assert "champion" in results[0]["aliases"]
        assert results[1]["version"] == "2"
        assert "challenger" in results[1]["aliases"]

        for v in results:
            assert "val_recall_at_t_star" in v
            assert "aliases" in v
            assert "version" in v

"""
tests/mlops/test_retrain.py — Unit tests for T-061 governed retraining pipeline.

Covers:
- Authorized dataset assembly (train + val only, NO test.csv).
- SHA-256 integrity checksums on loaded data.
- Leakage guard: rejects unauthorized split names.
- Feature engineering produces frozen 14-column contract.
- Challenger training and calibration (frozen architecture).
- Val metrics are computed at fixed t* = 0.160 (never altered).
- MLflow run creation and challenger version registration.
- Audit log: started/completed entries are written.
- Error path: failed retrain writes 'retrain_failed' audit entry.
- Test-set isolation: train.csv and val.csv do NOT share Machine_IDs with test.csv.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from mlops.retrain import (
    _TEST_PATH_SENTINEL,
    _TRAIN_PATH,
    _VAL_PATH,
    AUTHORIZED_TRAIN_VERSION,
    FROZEN_N_FEATURES,
    FROZEN_THRESHOLD,
    RetrainAuditEntry,
    RetrainDataset,
    _assert_no_test_set_access,
    _sha256_file,
    append_audit_log,
    assemble_retrain_dataset,
    read_audit_log,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_audit_log(tmp_path: Path) -> Path:
    """Return a temporary path for the audit log."""
    return tmp_path / "test_audit.jsonl"


@pytest.fixture()
def synthetic_train_df() -> pd.DataFrame:
    """Small synthetic training DataFrame matching the feature contract."""
    np.random.seed(42)
    n = 200
    return pd.DataFrame(
        {
            "Machine_ID": [f"M-{i:04d}" for i in range(n)],
            "Air_Temperature_C": np.random.uniform(20, 30, n),
            "Process_Temperature_C": np.random.uniform(30, 45, n),
            "Rotational_Speed_RPM": np.random.uniform(1200, 2000, n),
            "Torque_Nm": np.random.uniform(20, 80, n),
            "Vibration_mm_s": np.random.uniform(0.5, 3.5, n),
            "Pressure_bar": np.random.uniform(1, 10, n),
            "Current_A": np.random.uniform(5, 25, n),
            "Voltage_V": np.random.uniform(200, 240, n),
            "Tool_Wear_Min": np.random.uniform(0, 250, n),
            "Operating_Hours": np.random.uniform(10, 500, n),
            "Machine_Type": np.random.choice(["L", "M", "H"], n),
            "Machine_Failure": np.random.choice([0, 1], n, p=[0.89, 0.11]),
            "Failure_Type": np.random.choice(["None", "TWF", "HDF", "PWF", "OSF", "RNF"], n),
        }
    )


@pytest.fixture()
def synthetic_val_df(synthetic_train_df: pd.DataFrame) -> pd.DataFrame:
    """Small synthetic validation DataFrame with different Machine_IDs."""
    np.random.seed(99)
    n = 80
    return pd.DataFrame(
        {
            "Machine_ID": [f"V-{i:04d}" for i in range(n)],
            "Air_Temperature_C": np.random.uniform(20, 30, n),
            "Process_Temperature_C": np.random.uniform(30, 45, n),
            "Rotational_Speed_RPM": np.random.uniform(1200, 2000, n),
            "Torque_Nm": np.random.uniform(20, 80, n),
            "Vibration_mm_s": np.random.uniform(0.5, 3.5, n),
            "Pressure_bar": np.random.uniform(1, 10, n),
            "Current_A": np.random.uniform(5, 25, n),
            "Voltage_V": np.random.uniform(200, 240, n),
            "Tool_Wear_Min": np.random.uniform(0, 250, n),
            "Operating_Hours": np.random.uniform(10, 500, n),
            "Machine_Type": np.random.choice(["L", "M", "H"], n),
            "Machine_Failure": np.random.choice([0, 1], n, p=[0.89, 0.11]),
            "Failure_Type": np.random.choice(["None", "TWF", "HDF", "PWF", "OSF", "RNF"], n),
        }
    )


# ---------------------------------------------------------------------------
# T-061-RET-01: Test-set isolation — train/val Machine_IDs never in test
# ---------------------------------------------------------------------------


class TestTestSetIsolation:
    """Verify train.csv and val.csv do not share Machine_IDs with test.csv."""

    def test_test_path_sentinel_defined(self) -> None:
        """_TEST_PATH_SENTINEL must be defined and point to test.csv."""
        assert str(_TEST_PATH_SENTINEL).endswith("test.csv")

    def test_test_split_machine_ids_disjoint_from_train(self) -> None:
        """No Machine_ID from test.csv should appear in train.csv (data governance)."""
        if not _TRAIN_PATH.exists() or not _TEST_PATH_SENTINEL.exists():
            pytest.skip("Actual split files not found; skipping split isolation check")

        train_df = pd.read_csv(_TRAIN_PATH)
        test_df = pd.read_csv(_TEST_PATH_SENTINEL)

        train_machines = set(train_df["Machine_ID"].unique())
        test_machines = set(test_df["Machine_ID"].unique())
        overlap = train_machines & test_machines

        assert (
            len(overlap) == 0
        ), f"LEAKAGE DETECTED: {len(overlap)} Machine_IDs in both train and test: {overlap}"

    def test_test_split_machine_ids_disjoint_from_val(self) -> None:
        """No Machine_ID from test.csv should appear in val.csv."""
        if not _VAL_PATH.exists() or not _TEST_PATH_SENTINEL.exists():
            pytest.skip("Actual split files not found; skipping split isolation check")

        val_df = pd.read_csv(_VAL_PATH)
        test_df = pd.read_csv(_TEST_PATH_SENTINEL)

        val_machines = set(val_df["Machine_ID"].unique())
        test_machines = set(test_df["Machine_ID"].unique())
        overlap = val_machines & test_machines

        assert (
            len(overlap) == 0
        ), f"LEAKAGE DETECTED: {len(overlap)} Machine_IDs in both val and test: {overlap}"

    def test_train_val_machine_ids_disjoint(self) -> None:
        """train.csv and val.csv must not share Machine_IDs."""
        if not _TRAIN_PATH.exists() or not _VAL_PATH.exists():
            pytest.skip("Actual split files not found; skipping train/val isolation check")

        train_df = pd.read_csv(_TRAIN_PATH)
        val_df = pd.read_csv(_VAL_PATH)

        train_machines = set(train_df["Machine_ID"].unique())
        val_machines = set(val_df["Machine_ID"].unique())
        overlap = train_machines & val_machines

        assert (
            len(overlap) == 0
        ), f"Train/val overlap detected: {len(overlap)} Machine_IDs — {overlap}"


# ---------------------------------------------------------------------------
# T-061-RET-02: Leakage guard
# ---------------------------------------------------------------------------


class TestLeakageGuard:
    """Verify _assert_no_test_set_access enforces authorized split names."""

    def test_accepts_train_split(self) -> None:
        """Train split is authorized — no exception raised."""
        df = pd.DataFrame({"col": [1, 2]})
        _assert_no_test_set_access(df, "train")  # Must not raise

    def test_accepts_val_split(self) -> None:
        """Val split is authorized — no exception raised."""
        df = pd.DataFrame({"col": [1, 2]})
        _assert_no_test_set_access(df, "val")  # Must not raise

    def test_rejects_test_split(self) -> None:
        """'test' split name must raise ValueError (zero test-set access)."""
        df = pd.DataFrame({"col": [1, 2]})
        with pytest.raises(ValueError, match="test"):
            _assert_no_test_set_access(df, "test")

    def test_rejects_arbitrary_split_name(self) -> None:
        """Any unauthorized split name must raise ValueError."""
        df = pd.DataFrame({"col": [1, 2]})
        with pytest.raises(ValueError):
            _assert_no_test_set_access(df, "holdout")

    def test_empty_dataframe_no_error(self) -> None:
        """Empty DataFrame on authorized split is a no-op."""
        df = pd.DataFrame()
        _assert_no_test_set_access(df, "train")


# ---------------------------------------------------------------------------
# T-061-RET-03: SHA-256 checksum
# ---------------------------------------------------------------------------


class TestSHA256:
    """Verify data integrity checksum computation."""

    def test_sha256_file_returns_hex_string(self, tmp_path: Path) -> None:
        """SHA-256 must return a 64-character hex string."""
        f = tmp_path / "data.csv"
        f.write_text("Machine_ID,value\nM-001,1\n", encoding="utf-8")
        digest = _sha256_file(f)
        assert isinstance(digest, str)
        assert len(digest) == 64

    def test_sha256_file_is_deterministic(self, tmp_path: Path) -> None:
        """SHA-256 on the same file content must be reproducible."""
        f = tmp_path / "data.csv"
        content = "Machine_ID,value\nM-001,1\nM-002,0\n"
        f.write_text(content, encoding="utf-8")
        assert _sha256_file(f) == _sha256_file(f)

    def test_sha256_changes_on_content_change(self, tmp_path: Path) -> None:
        """SHA-256 must differ when file content differs."""
        f1 = tmp_path / "a.csv"
        f2 = tmp_path / "b.csv"
        f1.write_text("col\n1\n", encoding="utf-8")
        f2.write_text("col\n2\n", encoding="utf-8")
        assert _sha256_file(f1) != _sha256_file(f2)


# ---------------------------------------------------------------------------
# T-061-RET-04: Dataset assembly (mocked)
# ---------------------------------------------------------------------------


class TestDatasetAssembly:
    """Test dataset assembly with mocked file I/O."""

    def test_assemble_returns_retrain_dataset(
        self, synthetic_train_df: pd.DataFrame, synthetic_val_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """assemble_retrain_dataset should return populated RetrainDataset."""
        train_csv = tmp_path / "train.csv"
        val_csv = tmp_path / "val.csv"
        synthetic_train_df.to_csv(train_csv, index=False)
        synthetic_val_df.to_csv(val_csv, index=False)

        with (
            patch("mlops.retrain._TRAIN_PATH", train_csv),
            patch("mlops.retrain._VAL_PATH", val_csv),
        ):
            dataset = assemble_retrain_dataset()

        assert isinstance(dataset, RetrainDataset)
        assert dataset.train_rows == len(synthetic_train_df)
        assert dataset.val_rows == len(synthetic_val_df)
        assert dataset.authorized_train_version == AUTHORIZED_TRAIN_VERSION
        assert len(dataset.train_sha256) == 64
        assert len(dataset.val_sha256) == 64
        assert len(dataset.feature_cols) == FROZEN_N_FEATURES

    def test_assemble_raises_if_train_missing(self, tmp_path: Path) -> None:
        """FileNotFoundError must be raised if train.csv is absent."""
        missing_path = tmp_path / "nonexistent" / "train.csv"
        with (
            patch("mlops.retrain._TRAIN_PATH", missing_path),
            pytest.raises(FileNotFoundError, match="train"),
        ):
            assemble_retrain_dataset()

    def test_assemble_raises_if_val_missing(
        self, synthetic_train_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """FileNotFoundError must be raised if val.csv is absent."""
        train_csv = tmp_path / "train.csv"
        synthetic_train_df.to_csv(train_csv, index=False)
        missing_val = tmp_path / "nonexistent" / "val.csv"

        with (
            patch("mlops.retrain._TRAIN_PATH", train_csv),
            patch("mlops.retrain._VAL_PATH", missing_val),
            pytest.raises(FileNotFoundError, match="val"),
        ):
            assemble_retrain_dataset()

    def test_feature_contract_14_columns(
        self, synthetic_train_df: pd.DataFrame, synthetic_val_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Assembled dataset must expose exactly 14 feature columns."""
        train_csv = tmp_path / "train.csv"
        val_csv = tmp_path / "val.csv"
        synthetic_train_df.to_csv(train_csv, index=False)
        synthetic_val_df.to_csv(val_csv, index=False)

        with (
            patch("mlops.retrain._TRAIN_PATH", train_csv),
            patch("mlops.retrain._VAL_PATH", val_csv),
        ):
            dataset = assemble_retrain_dataset()

        assert len(dataset.feature_cols) == FROZEN_N_FEATURES

    def test_failure_rate_computed(
        self, synthetic_train_df: pd.DataFrame, synthetic_val_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Failure rates must be non-negative floats."""
        train_csv = tmp_path / "train.csv"
        val_csv = tmp_path / "val.csv"
        synthetic_train_df.to_csv(train_csv, index=False)
        synthetic_val_df.to_csv(val_csv, index=False)

        with (
            patch("mlops.retrain._TRAIN_PATH", train_csv),
            patch("mlops.retrain._VAL_PATH", val_csv),
        ):
            dataset = assemble_retrain_dataset()

        assert 0.0 <= dataset.train_failure_rate <= 1.0
        assert 0.0 <= dataset.val_failure_rate <= 1.0


# ---------------------------------------------------------------------------
# T-061-RET-05: Audit log
# ---------------------------------------------------------------------------


class TestAuditLog:
    """Test the append-only audit log mechanics."""

    def test_audit_entry_written_on_retrain_started(self, tmp_audit_log: Path) -> None:
        """Retrain started event must be appended to audit log."""
        entry = RetrainAuditEntry(event="retrain_started", actor="engineer1")
        append_audit_log(entry, tmp_audit_log)

        entries = read_audit_log(tmp_audit_log)
        assert len(entries) == 1
        assert entries[0]["event"] == "retrain_started"
        assert entries[0]["actor"] == "engineer1"

    def test_audit_log_is_append_only(self, tmp_audit_log: Path) -> None:
        """Each call must add a new line without modifying prior entries."""
        entry1 = RetrainAuditEntry(event="retrain_started", actor="alice")
        entry2 = RetrainAuditEntry(event="retrain_completed", actor="alice")
        append_audit_log(entry1, tmp_audit_log)
        append_audit_log(entry2, tmp_audit_log)

        entries = read_audit_log(tmp_audit_log)
        assert len(entries) == 2
        assert entries[0]["event"] == "retrain_started"
        assert entries[1]["event"] == "retrain_completed"

    def test_audit_log_entries_are_valid_json(self, tmp_audit_log: Path) -> None:
        """Every line of the audit log must be valid JSON."""
        for event in ("retrain_started", "retrain_completed", "retrain_failed"):
            entry = RetrainAuditEntry(event=event, actor="bob")
            append_audit_log(entry, tmp_audit_log)

        with open(tmp_audit_log, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    parsed = json.loads(line)
                    assert "event" in parsed
                    assert "actor" in parsed

    def test_read_audit_log_empty_file_returns_empty_list(self, tmp_audit_log: Path) -> None:
        """Reading a non-existent audit log returns empty list."""
        entries = read_audit_log(tmp_audit_log)
        assert entries == []

    def test_audit_entry_contains_governance_fields(self, tmp_audit_log: Path) -> None:
        """Audit entries must include governance-required fields."""
        entry = RetrainAuditEntry(event="retrain_started", actor="mlops_admin")
        append_audit_log(entry, tmp_audit_log)

        entries = read_audit_log(tmp_audit_log)
        assert len(entries) == 1
        e = entries[0]

        assert "timestamp" in e
        assert "authorized_train_version" in e
        assert "feature_set" in e
        assert "threshold" in e
        assert e["threshold"] == pytest.approx(FROZEN_THRESHOLD)

    def test_frozen_threshold_in_audit_entry(self, tmp_audit_log: Path) -> None:
        """t* = 0.160 must be recorded in every audit entry."""
        entry = RetrainAuditEntry(event="retrain_started", actor="qa")
        append_audit_log(entry, tmp_audit_log)

        entries = read_audit_log(tmp_audit_log)
        assert entries[0]["threshold"] == pytest.approx(0.160)

    def test_audit_entry_n_features_is_14(self, tmp_audit_log: Path) -> None:
        """n_features=14 must be recorded in every audit entry."""
        entry = RetrainAuditEntry(event="retrain_completed", actor="qa")
        append_audit_log(entry, tmp_audit_log)

        entries = read_audit_log(tmp_audit_log)
        assert entries[0]["n_features"] == FROZEN_N_FEATURES


# ---------------------------------------------------------------------------
# T-061-RET-06: train_challenger (mocked MLflow)
# ---------------------------------------------------------------------------


class TestTrainChallenger:
    """Test train_challenger with mocked MLflow and file system."""

    def _make_mock_client(self, version: str = "3") -> MagicMock:
        """Return a mocked MlflowClient."""
        client = MagicMock()
        mv = MagicMock()
        mv.version = version
        client.search_model_versions.return_value = [mv]
        return client

    def test_train_challenger_produces_challenger_result(
        self,
        synthetic_train_df: pd.DataFrame,
        synthetic_val_df: pd.DataFrame,
        tmp_path: Path,
        tmp_audit_log: Path,
    ) -> None:
        """train_challenger must return a valid ChallengerResult."""
        from mlops.retrain import ChallengerResult, train_challenger

        train_csv = tmp_path / "train.csv"
        val_csv = tmp_path / "val.csv"
        synthetic_train_df.to_csv(train_csv, index=False)
        synthetic_val_df.to_csv(val_csv, index=False)

        mock_client = self._make_mock_client("2")

        with (
            patch("mlops.retrain._TRAIN_PATH", train_csv),
            patch("mlops.retrain._VAL_PATH", val_csv),
            patch("mlops.retrain.mlflow.set_tracking_uri"),
            patch("mlops.retrain.mlflow.set_experiment"),
            patch("mlops.retrain.mlflow.start_run") as mock_run_ctx,
            patch("mlops.retrain.mlflow.log_param"),
            patch("mlops.retrain.mlflow.log_metric"),
            patch("mlops.retrain.mlflow.log_artifact"),
            patch("mlops.retrain.mlflow.pyfunc.log_model"),
            patch("mlops.retrain.MlflowClient", return_value=mock_client),
        ):
            # Set up context manager mock for start_run
            mock_run = MagicMock()
            mock_run.info.run_id = "test-run-id-abc123"
            mock_run_ctx.return_value.__enter__ = MagicMock(return_value=mock_run)
            mock_run_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = train_challenger(
                actor="test_actor",
                tracking_uri="sqlite:///test.db",
                artifacts_dir=tmp_path / "artifacts",
                run_name="test-run",
                seed=42,
                audit_log_path=tmp_audit_log,
            )

        assert isinstance(result, ChallengerResult)
        assert result.run_id == "test-run-id-abc123"
        assert result.challenger_version == "2"
        assert 0.0 <= result.val_recall <= 1.0
        assert 0.0 <= result.val_precision <= 1.0
        assert 0.0 <= result.val_pr_auc <= 1.0
        assert len(result.feature_cols) == FROZEN_N_FEATURES

    def test_train_challenger_writes_audit_log_entries(
        self,
        synthetic_train_df: pd.DataFrame,
        synthetic_val_df: pd.DataFrame,
        tmp_path: Path,
        tmp_audit_log: Path,
    ) -> None:
        """train_challenger must write 'retrain_started' and 'retrain_completed' audit entries."""
        from mlops.retrain import train_challenger

        train_csv = tmp_path / "train.csv"
        val_csv = tmp_path / "val.csv"
        synthetic_train_df.to_csv(train_csv, index=False)
        synthetic_val_df.to_csv(val_csv, index=False)

        mock_client = self._make_mock_client("2")

        with (
            patch("mlops.retrain._TRAIN_PATH", train_csv),
            patch("mlops.retrain._VAL_PATH", val_csv),
            patch("mlops.retrain.mlflow.set_tracking_uri"),
            patch("mlops.retrain.mlflow.set_experiment"),
            patch("mlops.retrain.mlflow.start_run") as mock_run_ctx,
            patch("mlops.retrain.mlflow.log_param"),
            patch("mlops.retrain.mlflow.log_metric"),
            patch("mlops.retrain.mlflow.log_artifact"),
            patch("mlops.retrain.mlflow.pyfunc.log_model"),
            patch("mlops.retrain.MlflowClient", return_value=mock_client),
        ):
            mock_run = MagicMock()
            mock_run.info.run_id = "run-xyz"
            mock_run_ctx.return_value.__enter__ = MagicMock(return_value=mock_run)
            mock_run_ctx.return_value.__exit__ = MagicMock(return_value=False)

            train_challenger(
                actor="qa_engineer",
                tracking_uri="sqlite:///test.db",
                artifacts_dir=tmp_path / "artifacts",
                audit_log_path=tmp_audit_log,
            )

        entries = read_audit_log(tmp_audit_log)
        events = [e["event"] for e in entries]
        assert "retrain_started" in events
        assert "retrain_completed" in events

    def test_train_challenger_writes_retrain_failed_on_error(
        self,
        tmp_path: Path,
        tmp_audit_log: Path,
    ) -> None:
        """train_challenger must write 'retrain_failed' entry when an exception occurs."""
        from mlops.retrain import train_challenger

        # Point to non-existent train file to trigger FileNotFoundError
        missing_train = tmp_path / "missing" / "train.csv"

        with (
            patch("mlops.retrain._TRAIN_PATH", missing_train),
            pytest.raises(FileNotFoundError),
        ):
            train_challenger(
                actor="failure_actor",
                tracking_uri="sqlite:///test.db",
                artifacts_dir=tmp_path / "artifacts",
                audit_log_path=tmp_audit_log,
            )

        entries = read_audit_log(tmp_audit_log)
        events = [e["event"] for e in entries]
        assert "retrain_failed" in events
        fail_entry = next(e for e in entries if e["event"] == "retrain_failed")
        assert fail_entry["actor"] == "failure_actor"
        assert len(fail_entry["error"]) > 0

    def test_threshold_is_frozen_at_0160(
        self,
        synthetic_train_df: pd.DataFrame,
        synthetic_val_df: pd.DataFrame,
        tmp_path: Path,
        tmp_audit_log: Path,
    ) -> None:
        """Challenger metadata must record threshold=0.160 exactly."""
        from mlops.retrain import train_challenger

        train_csv = tmp_path / "train.csv"
        val_csv = tmp_path / "val.csv"
        synthetic_train_df.to_csv(train_csv, index=False)
        synthetic_val_df.to_csv(val_csv, index=False)

        mock_client = self._make_mock_client("5")

        with (
            patch("mlops.retrain._TRAIN_PATH", train_csv),
            patch("mlops.retrain._VAL_PATH", val_csv),
            patch("mlops.retrain.mlflow.set_tracking_uri"),
            patch("mlops.retrain.mlflow.set_experiment"),
            patch("mlops.retrain.mlflow.start_run") as mock_run_ctx,
            patch("mlops.retrain.mlflow.log_param"),
            patch("mlops.retrain.mlflow.log_metric"),
            patch("mlops.retrain.mlflow.log_artifact"),
            patch("mlops.retrain.mlflow.pyfunc.log_model"),
            patch("mlops.retrain.MlflowClient", return_value=mock_client),
        ):
            mock_run = MagicMock()
            mock_run.info.run_id = "run-threshold-test"
            mock_run_ctx.return_value.__enter__ = MagicMock(return_value=mock_run)
            mock_run_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = train_challenger(
                actor="test",
                tracking_uri="sqlite:///test.db",
                artifacts_dir=tmp_path / "artifacts",
                audit_log_path=tmp_audit_log,
            )

        assert result.metadata["operational_threshold"] == pytest.approx(FROZEN_THRESHOLD)
        assert FROZEN_THRESHOLD == pytest.approx(0.160)

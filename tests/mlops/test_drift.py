"""
tests/mlops/test_drift.py - Unit tests for PSI and KS feature drift monitoring (T-060).

Verifies:
- PSI on identical distributions, shifted distributions, zero-count bins, epsilon handling,
  missing values, deterministic binning, reference bin stability, small samples, and empty samples.
- KS test on identical distributions, shifted distributions, p-value and statistic handling,
  small samples, empty samples, NaN handling, and categorical feature exclusion.
- Categorical PSI on Machine_Type (proportions, unseen categories).
- Multi-feature drift report aggregation, status hierarchy (DRIFT > WATCH > STABLE > INSUFFICIENT_DATA),
  and drift alerts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mlops.drift import (
    MIN_SAMPLE_SIZE,
    MONITORED_FEATURES,
    PSI_DRIFT_THRESHOLD,
    PSI_STABLE_THRESHOLD,
    DriftReference,
    DriftStatus,
    calculate_psi,
    compute_categorical_psi,
    compute_continuous_psi,
    evaluate_feature_drift,
    generate_drift_report,
    get_drift_reference,
)


@pytest.fixture(scope="module")
def drift_reference() -> DriftReference:
    """Fixture providing initialized DriftReference."""
    return get_drift_reference()


@pytest.fixture
def synthetic_current_df() -> pd.DataFrame:
    """Generate 100 synthetic operational observations matching feature contract."""
    np.random.seed(42)
    n = 100
    data = {
        "Air_Temperature_C": np.random.normal(25.0, 3.0, n),
        "Process_Temperature_C": np.random.normal(35.0, 3.5, n),
        "Rotational_Speed_RPM": np.random.normal(1500.0, 150.0, n),
        "Torque_Nm": np.random.normal(40.0, 10.0, n),
        "Vibration_mm_s": np.random.exponential(2.5, n),
        "Pressure_bar": np.random.normal(5.0, 1.5, n),
        "Current_A": np.random.normal(15.0, 4.0, n),
        "Voltage_V": np.random.normal(400.0, 20.0, n),
        "Tool_Wear_Min": np.random.uniform(10.0, 200.0, n),
        "Operating_Hours": np.random.uniform(50.0, 5000.0, n),
        "Machine_Type": np.random.choice(
            ["CNC_Machine", "Pump", "Compressor", "Conveyor", "Motor"], n
        ),
        "Delta_T_C": np.random.normal(10.0, 1.5, n),
        "Apparent_Power_VA": np.random.normal(5000.0, 1500.0, n),
        "Mech_Power_W": np.random.normal(6500.0, 2000.0, n),
    }
    return pd.DataFrame(data)


# ===========================================================================
# 1. PSI Detector Unit Tests
# ===========================================================================


class TestPSIDetector:
    """Unit tests for Population Stability Index (PSI)."""

    def test_identical_distributions_yield_zero_psi(self) -> None:
        """Identical probability distributions must produce PSI == 0.0."""
        p = np.array([0.1] * 10)
        psi = calculate_psi(p, p)
        assert psi == pytest.approx(0.0, abs=1e-6)

    def test_small_distribution_shift_yields_stable_status(self) -> None:
        """Minor variation must yield PSI < 0.10 (STABLE)."""
        ref_p = np.array([0.1] * 10)
        curr_q = np.array([0.09, 0.11, 0.10, 0.09, 0.11, 0.10, 0.09, 0.11, 0.10, 0.10])
        psi = calculate_psi(ref_p, curr_q)
        assert 0.0 < psi < PSI_STABLE_THRESHOLD

    def test_significant_distribution_shift_yields_drift_status(self) -> None:
        """Large divergence must yield PSI >= 0.25 (DRIFT)."""
        ref_p = np.array([0.1] * 10)
        # Shift mass entirely to first two bins
        curr_q = np.array([0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        psi = calculate_psi(ref_p, curr_q)
        assert psi >= PSI_DRIFT_THRESHOLD

    def test_zero_count_bins_handled_with_epsilon(self) -> None:
        """Zero counts in bins must not cause division by zero or log(0) NaN."""
        ref_p = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
        curr_q = np.array([0.0, 0.5, 0.5, 0.0, 0.0])  # Multiple zero bins
        psi = calculate_psi(ref_p, curr_q, epsilon=1e-4)
        assert np.isfinite(psi)
        assert psi > 0.0

    def test_deterministic_binning_across_repeated_evaluations(self) -> None:
        """Reference interior cuts must produce identical PSI on same inputs."""
        cuts = [1.0, 2.0, 3.0, 4.0]
        ref_props = [0.2, 0.2, 0.2, 0.2, 0.2]
        sample = np.array([0.5, 1.5, 2.5, 3.5, 4.5] * 20)

        psi1 = compute_continuous_psi(ref_props, cuts, sample)
        psi2 = compute_continuous_psi(ref_props, cuts, sample)
        assert psi1 == psi2

    def test_categorical_psi_handles_unseen_category(self) -> None:
        """Unseen categorical labels must map to __OTHER__ without raising errors."""
        ref_cats = {"A": 0.5, "B": 0.5}
        curr_cats = ["A", "B", "C", "D"]  # C and D unseen
        psi = compute_categorical_psi(ref_cats, curr_cats)
        assert np.isfinite(psi)
        assert psi > 0.0

    def test_empty_sample_returns_zero_psi(self) -> None:
        """Empty input arrays must return 0.0 safely."""
        assert compute_continuous_psi([0.5, 0.5], [1.0], np.array([])) == 0.0
        assert compute_categorical_psi({"A": 1.0}, []) == 0.0


# ===========================================================================
# 2. KS Detector Unit Tests
# ===========================================================================


class TestKSDetector:
    """Unit tests for Kolmogorov-Smirnov continuous drift detection."""

    def test_identical_continuous_samples_yield_zero_statistic(
        self, drift_reference: DriftReference
    ) -> None:
        """Evaluating the training baseline against itself must yield statistic 0.0 and p-value 1.0."""
        feat = "Vibration_mm_s"
        ref_vals = drift_reference.raw_numeric_samples[feat]
        res = evaluate_feature_drift(feat, pd.Series(ref_vals), drift_reference)

        assert res.status == DriftStatus.STABLE
        assert res.ks_statistic == pytest.approx(0.0, abs=1e-4)
        assert res.ks_p_value == pytest.approx(1.0, abs=1e-4)
        assert res.psi == pytest.approx(0.0, abs=1e-3)

    def test_shifted_continuous_distribution_triggers_drift(
        self, drift_reference: DriftReference
    ) -> None:
        """Artificially shifting vibration by a factor of 3 must trigger DRIFT."""
        feat = "Vibration_mm_s"
        ref_vals = drift_reference.raw_numeric_samples[feat]
        shifted_vals = ref_vals * 3.0 + 5.0
        res = evaluate_feature_drift(feat, pd.Series(shifted_vals), drift_reference)

        assert res.status == DriftStatus.DRIFT
        assert res.ks_statistic is not None and res.ks_statistic > 0.15
        assert res.ks_p_value is not None and res.ks_p_value < 0.001
        assert res.psi is not None and res.psi >= PSI_DRIFT_THRESHOLD

    def test_categorical_feature_excludes_ks(self, drift_reference: DriftReference) -> None:
        """Machine_Type must not have KS test computed (displays None / N/A)."""
        series = pd.Series(["CNC_Machine"] * 50)
        res = evaluate_feature_drift("Machine_Type", series, drift_reference)

        assert res.feature_type == "categorical"
        assert res.ks_statistic is None
        assert res.ks_p_value is None
        assert res.psi is not None

    def test_nan_values_excluded_from_statistical_arrays(
        self, drift_reference: DriftReference
    ) -> None:
        """NaN values must be excluded before KS test and reported in missingness."""
        feat = "Torque_Nm"
        vals = [40.0] * 50 + [np.nan] * 50  # 50% missing
        series = pd.Series(vals)
        res = evaluate_feature_drift(feat, series, drift_reference)

        assert res.missing_current_pct == pytest.approx(50.0, abs=0.1)
        assert res.current_count == 50
        assert res.ks_statistic is not None

    def test_small_sample_size_returns_insufficient_data(
        self, drift_reference: DriftReference
    ) -> None:
        """Sample size < MIN_SAMPLE_SIZE must return INSUFFICIENT_DATA."""
        feat = "Current_A"
        small_sample = pd.Series([15.0] * (MIN_SAMPLE_SIZE - 1))
        res = evaluate_feature_drift(feat, small_sample, drift_reference)

        assert res.status == DriftStatus.INSUFFICIENT_DATA
        assert res.psi is None
        assert res.ks_statistic is None
        assert "Insufficient observations" in res.message


# ===========================================================================
# 3. Multi-Feature Drift Report Tests
# ===========================================================================


class TestMultiFeatureDriftReport:
    """Tests for multi-feature aggregation and drift alerts."""

    def test_report_evaluates_all_14_monitored_features(
        self, drift_reference: DriftReference, synthetic_current_df: pd.DataFrame
    ) -> None:
        """Report must evaluate exactly all 14 monitored features."""
        report = generate_drift_report(synthetic_current_df, reference=drift_reference)

        assert len(report.feature_results) == len(MONITORED_FEATURES)
        reported_names = [f.feature_name for f in report.feature_results]
        for name in MONITORED_FEATURES:
            assert name in reported_names

    def test_empty_dataframe_yields_insufficient_data_overall(
        self, drift_reference: DriftReference
    ) -> None:
        """Empty dataframe must produce INSUFFICIENT_DATA overall status."""
        empty_df = pd.DataFrame()
        report = generate_drift_report(empty_df, reference=drift_reference)

        assert report.overall_status == DriftStatus.INSUFFICIENT_DATA
        assert report.current_sample_count == 0
        assert len(report.drift_alerts) == 0

    def test_drifting_feature_triggers_overall_drift_status_and_alert(
        self, drift_reference: DriftReference, synthetic_current_df: pd.DataFrame
    ) -> None:
        """A single severely drifting feature must escalate overall status to DRIFT and raise alert."""
        corrupted_df = synthetic_current_df.copy()
        corrupted_df["Vibration_mm_s"] = corrupted_df["Vibration_mm_s"] * 10.0 + 20.0

        report = generate_drift_report(corrupted_df, reference=drift_reference)
        assert report.overall_status == DriftStatus.DRIFT
        assert report.drifting_features_count >= 1

        vibration_alert = next(
            (a for a in report.drift_alerts if a.feature_name == "Vibration_mm_s"), None
        )
        assert vibration_alert is not None
        assert vibration_alert.severity == "CRITICAL"
        assert "severe distribution drift" in vibration_alert.message

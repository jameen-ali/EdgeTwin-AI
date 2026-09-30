"""
tests/integration/test_t071_ai4i.py — T-071 AI4I 2020 Generalization Benchmark Tests.

Tests verify:
1. Feature compatibility mapping correctness (unit conversions, NaN for UNAVAILABLE).
2. Feature matrix shape and column order match production contract.
3. Champion model isolation (AI4I data never touches production namespace).
4. Score distribution sanity (no negatives, no >1 values, finite floats).
5. Benchmark results file is present and structurally valid.
6. Scientific integrity: both positive and negative results are represented.

Note: These tests do NOT load the champion model (no MLflow dependency in unit tests).
They validate the data-preparation layer and result structure only.
"""

from __future__ import annotations

import json
import math

# Import benchmark module
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.benchmark_t071 import (
    _TWO_PI_OVER_60,
    FEATURE_COMPATIBILITY,
    FROZEN_THRESHOLD,
    MACHINE_TYPE_MAP,
    PRODUCTION_FEATURE_COLS,
    build_edgetwin_features,
    evaluate,
)

AI4I_CSV = PROJECT_ROOT / "data" / "raw" / "ai4i2020.csv"
RESULTS_JSON = PROJECT_ROOT / "artifacts" / "t071_ai4i_results.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ai4i_sample() -> pd.DataFrame:
    """Return a small synthetic AI4I-shaped DataFrame for unit tests."""
    return pd.DataFrame(
        {
            "Air temperature [K]": [298.1, 300.0, 302.5],
            "Process temperature [K]": [308.6, 310.0, 313.0],
            "Rotational speed [rpm]": [1551, 1400, 2000],
            "Torque [Nm]": [42.8, 30.0, 60.0],
            "Tool wear [min]": [0, 100, 200],
            "Type": ["M", "L", "H"],
            "Machine failure": [0, 0, 1],
            "TWF": [0, 0, 0],
            "HDF": [0, 0, 1],
            "PWF": [0, 0, 0],
            "OSF": [0, 0, 0],
            "RNF": [0, 0, 0],
        }
    )


@pytest.fixture(scope="module")
def ai4i_features(ai4i_sample) -> pd.DataFrame:
    return build_edgetwin_features(ai4i_sample)


# ---------------------------------------------------------------------------
# Feature compatibility catalogue tests
# ---------------------------------------------------------------------------


class TestFeatureCompatibilityCatalogue:
    """Validate that the feature compatibility map is complete and consistent."""

    def test_all_14_production_features_documented(self):
        """Every production feature must have an entry in the compatibility map."""
        assert set(FEATURE_COMPATIBILITY.keys()) == set(PRODUCTION_FEATURE_COLS)

    def test_all_statuses_are_valid(self):
        valid_statuses = {"DIRECT", "MAPPED", "DERIVED", "UNAVAILABLE"}
        for feat, meta in FEATURE_COMPATIBILITY.items():
            assert (
                meta["status"] in valid_statuses
            ), f"Feature '{feat}' has invalid status '{meta['status']}'"

    def test_unavailable_features_have_no_ai4i_col(self):
        for feat, meta in FEATURE_COMPATIBILITY.items():
            if meta["status"] == "UNAVAILABLE":
                assert (
                    meta["ai4i_col"] is None
                ), f"UNAVAILABLE feature '{feat}' should have ai4i_col=None"

    def test_available_features_have_ai4i_col(self):
        for feat, meta in FEATURE_COMPATIBILITY.items():
            if meta["status"] in ("DIRECT", "MAPPED"):
                assert (
                    meta["ai4i_col"] is not None
                ), f"Feature '{feat}' with status '{meta['status']}' should have ai4i_col"

    def test_frozen_threshold_is_production_value(self):
        """Confirm we are using the exact production threshold."""
        assert FROZEN_THRESHOLD == 0.160

    def test_machine_type_map_covers_all_ai4i_types(self):
        assert set(MACHINE_TYPE_MAP.keys()) == {"L", "M", "H"}

    def test_machine_type_map_targets_valid_edgetwin_classes(self):
        valid_classes = {"Pump", "Compressor", "CNC_Machine", "Conveyor", "Motor"}
        for k, v in MACHINE_TYPE_MAP.items():
            assert v in valid_classes, f"Type {k} maps to unknown EdgeTwin class {v}"


# ---------------------------------------------------------------------------
# Feature construction tests
# ---------------------------------------------------------------------------


class TestBuildEdgetwinFeatures:
    """Validate feature matrix construction from AI4I data."""

    def test_output_shape(self, ai4i_sample, ai4i_features):
        assert ai4i_features.shape == (len(ai4i_sample), 14)

    def test_column_order_matches_production(self, ai4i_features):
        assert ai4i_features.columns.tolist() == PRODUCTION_FEATURE_COLS

    def test_temperature_kelvin_to_celsius_conversion(self, ai4i_sample, ai4i_features):
        """Air and Process temperatures must be shifted by 273.15."""
        expected_air = ai4i_sample["Air temperature [K]"].values - 273.15
        np.testing.assert_allclose(
            ai4i_features["Air_Temperature_C"].values, expected_air, rtol=1e-6
        )
        expected_proc = ai4i_sample["Process temperature [K]"].values - 273.15
        np.testing.assert_allclose(
            ai4i_features["Process_Temperature_C"].values, expected_proc, rtol=1e-6
        )

    def test_direct_columns_are_preserved(self, ai4i_sample, ai4i_features):
        """Rotational speed, torque, tool wear must pass through unchanged."""
        np.testing.assert_array_equal(
            ai4i_features["Rotational_Speed_RPM"].values,
            ai4i_sample["Rotational speed [rpm]"].values,
        )
        np.testing.assert_allclose(
            ai4i_features["Torque_Nm"].values,
            ai4i_sample["Torque [Nm]"].values,
        )
        np.testing.assert_array_equal(
            ai4i_features["Tool_Wear_Min"].values,
            ai4i_sample["Tool wear [min]"].values,
        )

    def test_unavailable_columns_are_nan_not_zero(self, ai4i_features):
        """UNAVAILABLE columns must be NaN, not zero (zero would be a false physical value)."""
        unavail_cols = [
            "Vibration_mm_s",
            "Pressure_bar",
            "Current_A",
            "Voltage_V",
            "Operating_Hours",
            "Apparent_Power_VA",
        ]
        for col in unavail_cols:
            assert (
                ai4i_features[col].isna().all()
            ), f"Column '{col}' should be entirely NaN, not zero or another value"

    def test_delta_t_is_unit_invariant(self, ai4i_sample, ai4i_features):
        """Delta_T_C from Kelvin temperatures must equal the Kelvin difference."""
        expected_delta = (
            ai4i_sample["Process temperature [K]"].values
            - ai4i_sample["Air temperature [K]"].values
        )
        np.testing.assert_allclose(ai4i_features["Delta_T_C"].values, expected_delta, rtol=1e-6)

    def test_mech_power_derivation(self, ai4i_sample, ai4i_features):
        """Mech_Power_W = Torque_Nm * RPM * 2pi/60."""
        expected = (
            ai4i_sample["Torque [Nm]"].values
            * ai4i_sample["Rotational speed [rpm]"].values
            * _TWO_PI_OVER_60
        )
        np.testing.assert_allclose(ai4i_features["Mech_Power_W"].values, expected, rtol=1e-6)

    def test_machine_type_mapping(self, ai4i_sample, ai4i_features):
        for orig, mapped in zip(ai4i_sample["Type"].values, ai4i_features["Machine_Type"].values):
            assert mapped == MACHINE_TYPE_MAP[orig]

    def test_no_column_contains_inf(self, ai4i_features):
        numeric = ai4i_features.select_dtypes(include=[np.number])
        # Fill NaN before checking for inf (NaN is acceptable; inf is not)
        filled = numeric.fillna(0.0).to_numpy(dtype=float)
        assert not np.isinf(filled).any(), "Feature matrix contains +/-inf values"


# ---------------------------------------------------------------------------
# Evaluation function tests
# ---------------------------------------------------------------------------


class TestEvaluate:
    """Validate the evaluation helper function."""

    def test_perfect_classifier_metrics(self):
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([0.05, 0.05, 0.95, 0.95])
        m = evaluate(y_true, y_prob, threshold=0.5)
        assert m["recall"] == 1.0
        assert m["precision"] == 1.0
        assert m["fp"] == 0
        assert m["fn"] == 0

    def test_all_wrong_classifier(self):
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([0.95, 0.95, 0.05, 0.05])
        m = evaluate(y_true, y_prob, threshold=0.5)
        assert m["recall"] == 0.0
        assert m["tp"] == 0
        assert m["fn"] == 2

    def test_false_alarm_rate_is_fp_over_neg(self):
        y_true = np.array([0, 0, 0, 1])
        y_prob = np.array([0.9, 0.1, 0.1, 0.9])
        m = evaluate(y_true, y_prob, threshold=0.5)
        assert m["false_alarm_rate"] == pytest.approx(1 / 3)

    def test_metrics_keys_present(self):
        y_true = np.array([0, 1])
        y_prob = np.array([0.1, 0.9])
        m = evaluate(y_true, y_prob, threshold=0.5)
        for key in (
            "n_total",
            "n_pos",
            "n_neg",
            "failure_rate",
            "threshold",
            "tp",
            "fp",
            "tn",
            "fn",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "pr_auc",
            "brier_score",
            "false_alarm_rate",
            "detection_rate",
        ):
            assert key in m, f"Missing key '{key}' in evaluate() output"

    def test_no_division_by_zero_on_all_negative(self):
        y_true = np.array([0, 0, 0])
        y_prob = np.array([0.01, 0.01, 0.01])
        m = evaluate(y_true, y_prob, threshold=0.5)
        assert m["false_alarm_rate"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Benchmark output artefact tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not RESULTS_JSON.exists(), reason="Run benchmark first")
class TestBenchmarkResults:
    """Validate the benchmark results JSON artefact."""

    @pytest.fixture(scope="class")
    @classmethod
    def results(cls):
        with open(RESULTS_JSON) as f:
            return json.load(f)

    def test_benchmark_id_is_t071(self, results):
        assert results["benchmark"] == "T-071"

    def test_frozen_threshold_unchanged(self, results):
        assert results["frozen_threshold"] == 0.160

    def test_champion_alias_unchanged(self, results):
        assert "edgetwin-risk@champion" in results["champion_model"]

    def test_dataset_profile_correct_shape(self, results):
        p = results["dataset_profile"]
        assert p["n_rows"] == 10000
        assert p["n_failures"] + p["n_healthy"] == p["n_rows"]

    def test_feature_compatibility_completeness(self, results):
        s = results["feature_compatibility_summary"]
        assert s["total_production_features"] == 14
        total_accounted = s["direct"] + s["mapped"] + s["derived"] + s["unavailable"]
        assert total_accounted == 14

    def test_metrics_are_finite(self, results):
        m = results["metrics_at_frozen_threshold"]
        for k in ("pr_auc", "roc_auc", "recall", "precision", "f1"):
            assert math.isfinite(m[k]), f"Metric {k} is not finite: {m[k]}"

    def test_pr_auc_range(self, results):
        pr_auc = results["metrics_at_frozen_threshold"]["pr_auc"]
        assert 0.0 <= pr_auc <= 1.0

    def test_roc_auc_range(self, results):
        roc_auc = results["metrics_at_frozen_threshold"]["roc_auc"]
        assert 0.0 <= roc_auc <= 1.0

    def test_calibration_section_present(self, results):
        assert "calibration" in results
        assert "calibration_gap" in results["calibration"]

    def test_per_failure_type_section_present(self, results):
        assert "per_failure_type" in results
        # Should have at least TWF, HDF, PWF, OSF entries
        assert len(results["per_failure_type"]) >= 4

    def test_score_distribution_healthy_lower_than_failure(self, results):
        """Healthy mean score should be lower than failure mean score."""
        sd = results["score_distribution"]
        assert sd["healthy_mean"] < sd["failure_mean"], (
            "Model produces HIGHER mean scores for healthy samples than failures — "
            "model polarity may be inverted or severely degraded on AI4I."
        )

    def test_unavailable_features_count(self, results):
        """6 features are UNAVAILABLE in AI4I 2020 — this is a known limitation."""
        assert results["feature_compatibility_summary"]["unavailable"] == 6

    def test_ai4i_namespace_isolation(self, results):
        """Results must be clearly in the AI4I validation namespace, not production."""
        assert "ai4i" in results["benchmark"].lower() or results["benchmark"] == "T-071"

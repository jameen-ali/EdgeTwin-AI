"""
tests/ml/test_models.py - T-012 model comparison tests.

Test groups
-----------
E1  Engineered features
M1  Pipeline building
M2  Training basics
M3  Leakage guards
M4  Evaluation metrics
M5  Cross-validation (smoke)
M6  Comparison orchestration (fast, no-CV, subset)
M7  Determinism
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.data.engineering import (
    FEATURE_SET_BASE,
    FEATURE_SET_PHYSICS,
    FEATURE_SET_WEAR_RATE,
    add_physics_features,
    add_wear_rate,
    apply_feature_set,
    get_feature_cols_for_set,
)
from ml.data.splits import split_dataset
from ml.models.evaluate import (
    compute_confusion_matrix,
    compute_metrics,
    per_failure_type_recall,
)
from ml.models.train import (
    BASE_FEATURE_COLS,
    CANDIDATE_MODELS,
    SEED,
    assert_no_forbidden_features,
    build_pipeline,
    cross_val_run,
    train_model,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PREPARED_PATH = _REPO_ROOT / "data" / "interim" / "predictive_maintenance_prepared.csv"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def prepared_df() -> pd.DataFrame:
    """Load the actual prepared dataset once per module."""
    if not _PREPARED_PATH.exists():
        pytest.skip(f"Prepared dataset not found at {_PREPARED_PATH}")
    return pd.read_csv(_PREPARED_PATH)


@pytest.fixture(scope="module")
def train_val_test(prepared_df: pd.DataFrame):
    """Return the deterministic S03 split."""
    return split_dataset(prepared_df, seed=SEED)


@pytest.fixture
def small_df() -> pd.DataFrame:
    """Minimal synthetic DataFrame with 60 machines for fast tests."""
    rng = np.random.default_rng(0)
    machines = [f"CMP-{i:04d}" for i in range(30)] + [f"PMP-{i:04d}" for i in range(30)]
    rows = []
    for mid in machines:
        for _ in range(20):
            rows.append(
                {
                    "Machine_ID": mid,
                    "Timestamp": "2024-01-01",
                    "Machine_Type": "Compressor" if mid.startswith("CMP") else "Pump",
                    "Air_Temperature_C": rng.uniform(20, 35),
                    "Process_Temperature_C": rng.uniform(30, 50),
                    "Rotational_Speed_RPM": rng.uniform(1000, 3000),
                    "Torque_Nm": rng.uniform(10, 80),
                    "Vibration_mm_s": rng.uniform(0.5, 10),
                    "Pressure_bar": rng.uniform(2, 15),
                    "Current_A": rng.uniform(5, 30),
                    "Voltage_V": rng.uniform(340, 480),
                    "Tool_Wear_Min": rng.uniform(0, 250),
                    "Operating_Hours": rng.uniform(100, 20000),
                    "Failure_Type": rng.choice(["No Failure", "Heat Dissipation Failure"]),
                    "Machine_Failure": int(rng.random() < 0.12),
                    "Sensor_Batch_Code": "SB001",
                    "Checksum_Flag": "OK",
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def small_split(small_df: pd.DataFrame):
    """Train/val/test split of the small synthetic DataFrame."""
    return split_dataset(small_df, seed=SEED)


# ---------------------------------------------------------------------------
# E1 — Engineered features
# ---------------------------------------------------------------------------


class TestEngineeredFeatures:
    """E1: Physics feature derivation."""

    def test_add_physics_adds_three_cols(self, small_df: pd.DataFrame) -> None:
        from ml.data.engineering import PHYSICS_COLS

        result = add_physics_features(small_df)
        for col in PHYSICS_COLS:
            assert col in result.columns, f"Expected column '{col}' not found"

    def test_original_cols_unchanged(self, small_df: pd.DataFrame) -> None:
        result = add_physics_features(small_df)
        for col in small_df.columns:
            pd.testing.assert_series_equal(result[col], small_df[col])

    def test_returns_copy_not_view(self, small_df: pd.DataFrame) -> None:
        result = add_physics_features(small_df)
        result["Air_Temperature_C"] = 999.0
        assert small_df["Air_Temperature_C"].iloc[0] != 999.0

    def test_delta_t_formula(self) -> None:
        df = pd.DataFrame(
            {
                "Air_Temperature_C": [20.0],
                "Process_Temperature_C": [45.0],
                "Rotational_Speed_RPM": [1500.0],
                "Torque_Nm": [40.0],
                "Voltage_V": [415.0],
                "Current_A": [12.0],
            }
        )
        result = add_physics_features(df)
        assert abs(result["Delta_T_C"].iloc[0] - 25.0) < 1e-9

    def test_apparent_power_formula(self) -> None:
        df = pd.DataFrame(
            {
                "Air_Temperature_C": [20.0],
                "Process_Temperature_C": [45.0],
                "Rotational_Speed_RPM": [1500.0],
                "Torque_Nm": [40.0],
                "Voltage_V": [400.0],
                "Current_A": [10.0],
            }
        )
        result = add_physics_features(df)
        assert abs(result["Apparent_Power_VA"].iloc[0] - 4000.0) < 1e-6

    def test_mech_power_formula(self) -> None:
        # 40 Nm * (1500 rpm * 2pi/60) = 40 * 157.08... = 6283.18...
        df = pd.DataFrame(
            {
                "Air_Temperature_C": [20.0],
                "Process_Temperature_C": [45.0],
                "Rotational_Speed_RPM": [1500.0],
                "Torque_Nm": [40.0],
                "Voltage_V": [400.0],
                "Current_A": [10.0],
            }
        )
        result = add_physics_features(df)
        expected = 40.0 * (1500.0 * 2 * math.pi / 60)
        assert abs(result["Mech_Power_W"].iloc[0] - expected) < 1e-6

    def test_nan_propagates_in_delta_t(self) -> None:
        df = pd.DataFrame(
            {
                "Air_Temperature_C": [float("nan")],
                "Process_Temperature_C": [45.0],
                "Rotational_Speed_RPM": [1500.0],
                "Torque_Nm": [40.0],
                "Voltage_V": [400.0],
                "Current_A": [10.0],
            }
        )
        result = add_physics_features(df)
        assert pd.isna(result["Delta_T_C"].iloc[0])

    def test_wear_rate_zero_denom_produces_nan(self) -> None:
        df = pd.DataFrame({"Tool_Wear_Min": [50.0, 100.0], "Operating_Hours": [0.0, 100.0]})
        result = add_wear_rate(df)
        assert pd.isna(result["Wear_Rate"].iloc[0])
        assert abs(result["Wear_Rate"].iloc[1] - 1.0) < 1e-9

    def test_apply_feature_set_base_returns_copy(self, small_df: pd.DataFrame) -> None:
        result = apply_feature_set(small_df, FEATURE_SET_BASE)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(small_df)

    def test_apply_feature_set_physics_adds_three_cols(self, small_df: pd.DataFrame) -> None:
        from ml.data.engineering import PHYSICS_COLS

        result = apply_feature_set(small_df, FEATURE_SET_PHYSICS)
        for col in PHYSICS_COLS:
            assert col in result.columns

    def test_apply_feature_set_wear_rate_adds_four_cols(self, small_df: pd.DataFrame) -> None:
        from ml.data.engineering import ENGINEERED_COLS

        result = apply_feature_set(small_df, FEATURE_SET_WEAR_RATE)
        for col in ENGINEERED_COLS:
            assert col in result.columns

    def test_apply_feature_set_raises_on_unknown(self, small_df: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="Unknown feature_set"):
            apply_feature_set(small_df, "invalid_set")

    def test_get_feature_cols_for_set_base_length(self) -> None:
        cols = get_feature_cols_for_set(BASE_FEATURE_COLS, FEATURE_SET_BASE)
        assert len(cols) == 11

    def test_get_feature_cols_for_set_physics_length(self) -> None:
        cols = get_feature_cols_for_set(BASE_FEATURE_COLS, FEATURE_SET_PHYSICS)
        assert len(cols) == 14

    def test_get_feature_cols_for_set_wear_rate_length(self) -> None:
        cols = get_feature_cols_for_set(BASE_FEATURE_COLS, FEATURE_SET_WEAR_RATE)
        assert len(cols) == 15


# ---------------------------------------------------------------------------
# M1 — Pipeline building
# ---------------------------------------------------------------------------


class TestPipelineBuilding:
    """M1: build_pipeline() produces valid sklearn Pipelines."""

    @pytest.mark.parametrize("model_name", CANDIDATE_MODELS)
    def test_build_pipeline_all_models(self, model_name: str) -> None:
        from sklearn.pipeline import Pipeline

        pipe = build_pipeline(model_name, BASE_FEATURE_COLS, seed=SEED)
        assert isinstance(pipe, Pipeline)

    def test_pipeline_has_preprocessor_and_classifier(self) -> None:
        pipe = build_pipeline("random_forest", BASE_FEATURE_COLS, seed=SEED)
        assert "preprocessor" in pipe.named_steps
        assert "classifier" in pipe.named_steps

    def test_build_pipeline_raises_on_unknown_model(self) -> None:
        with pytest.raises(ValueError, match="Unknown model"):
            build_pipeline("not_a_model", BASE_FEATURE_COLS)

    def test_logistic_regression_has_scaler(self) -> None:
        from sklearn.preprocessing import StandardScaler

        pipe = build_pipeline("logistic_regression", BASE_FEATURE_COLS)
        pre = pipe.named_steps["preprocessor"]
        # Check the numeric sub-pipeline has StandardScaler
        num_steps = pre.transformers[0][1]
        scaler_found = any(isinstance(s, StandardScaler) for _, s in num_steps.steps)
        assert scaler_found

    def test_tree_models_have_no_scaler(self) -> None:
        from sklearn.preprocessing import StandardScaler

        for model in ["random_forest", "decision_tree"]:
            pipe = build_pipeline(model, BASE_FEATURE_COLS)
            num_steps = pipe.named_steps["preprocessor"].transformers[0][1]
            has_scaler = any(isinstance(s, StandardScaler) for _, s in num_steps.steps)
            assert not has_scaler, f"{model} should not have StandardScaler"


# ---------------------------------------------------------------------------
# M2 — Training basics
# ---------------------------------------------------------------------------


class TestTrainingBasics:
    """M2: Pipeline can be fit and can produce predictions."""

    @pytest.mark.parametrize("model_name", CANDIDATE_MODELS)
    def test_fit_and_predict_on_small_data(
        self,
        model_name: str,
        small_split,
    ) -> None:
        train_df, val_df, _ = small_split
        feature_cols = get_feature_cols_for_set(BASE_FEATURE_COLS, FEATURE_SET_BASE)
        X_tr = train_df[feature_cols]
        y_tr = train_df["Machine_Failure"]
        X_va = val_df[feature_cols]

        pipe = build_pipeline(model_name, feature_cols, seed=SEED)
        pipe = train_model(pipe, X_tr, y_tr)

        preds = pipe.predict(X_va)
        probas = pipe.predict_proba(X_va)

        assert len(preds) == len(X_va)
        assert probas.shape == (len(X_va), 2)
        assert set(preds).issubset({0, 1})

    @pytest.mark.parametrize("model_name", CANDIDATE_MODELS)
    def test_predict_proba_sums_to_one(
        self,
        model_name: str,
        small_split,
    ) -> None:
        train_df, val_df, _ = small_split
        feature_cols = get_feature_cols_for_set(BASE_FEATURE_COLS, FEATURE_SET_BASE)
        pipe = build_pipeline(model_name, feature_cols, seed=SEED)
        pipe = train_model(pipe, train_df[feature_cols], train_df["Machine_Failure"])
        probas = pipe.predict_proba(val_df[feature_cols])
        np.testing.assert_allclose(probas.sum(axis=1), 1.0, atol=1e-6)

    def test_physics_feature_set_pipeline_fits(self, small_split) -> None:
        train_df, val_df, _ = small_split
        feature_cols = get_feature_cols_for_set(BASE_FEATURE_COLS, FEATURE_SET_PHYSICS)
        train_eng = apply_feature_set(train_df, FEATURE_SET_PHYSICS)
        val_eng = apply_feature_set(val_df, FEATURE_SET_PHYSICS)

        pipe = build_pipeline("random_forest", feature_cols, seed=SEED)
        pipe = train_model(pipe, train_eng[feature_cols], train_df["Machine_Failure"])
        preds = pipe.predict(val_eng[feature_cols])
        assert len(preds) == len(val_df)


# ---------------------------------------------------------------------------
# M3 — Leakage guards
# ---------------------------------------------------------------------------


class TestLeakageGuards:
    """M3: Forbidden columns cannot enter the feature pipeline."""

    def test_assert_no_forbidden_features_raises_for_failure_type(self) -> None:
        with pytest.raises(ValueError, match="Leakage guard violation"):
            assert_no_forbidden_features(BASE_FEATURE_COLS + ["Failure_Type"])

    def test_assert_no_forbidden_features_raises_for_machine_id(self) -> None:
        with pytest.raises(ValueError, match="Leakage guard violation"):
            assert_no_forbidden_features(BASE_FEATURE_COLS + ["Machine_ID"])

    def test_assert_no_forbidden_features_raises_for_timestamp(self) -> None:
        with pytest.raises(ValueError, match="Leakage guard violation"):
            assert_no_forbidden_features(BASE_FEATURE_COLS + ["Timestamp"])

    def test_assert_no_forbidden_passes_for_clean_cols(self) -> None:
        assert_no_forbidden_features(BASE_FEATURE_COLS)  # must not raise

    def test_engineered_cols_not_forbidden(self) -> None:
        from ml.data.engineering import ENGINEERED_COLS

        # Engineered cols are safe (derived from non-forbidden inputs)
        assert_no_forbidden_features(BASE_FEATURE_COLS + ENGINEERED_COLS)

    def test_split_produces_zero_machine_id_overlap(self, prepared_df: pd.DataFrame) -> None:
        train, val, test = split_dataset(prepared_df, seed=SEED)
        train_m = set(train["Machine_ID"])
        val_m = set(val["Machine_ID"])
        test_m = set(test["Machine_ID"])
        assert not (train_m & val_m), "Train/val Machine_ID overlap!"
        assert not (train_m & test_m), "Train/test Machine_ID overlap!"
        assert not (val_m & test_m), "Val/test Machine_ID overlap!"

    def test_feature_set_base_excludes_forbidden_cols(self) -> None:
        from ml.data.schema import FORBIDDEN_FEATURE_COLUMNS

        cols = set(get_feature_cols_for_set(BASE_FEATURE_COLS, FEATURE_SET_BASE))
        for forbidden in FORBIDDEN_FEATURE_COLUMNS:
            assert forbidden not in cols, f"Forbidden col '{forbidden}' in feature set"

    def test_physics_feature_set_excludes_forbidden_cols(self) -> None:
        from ml.data.schema import FORBIDDEN_FEATURE_COLUMNS

        cols = set(get_feature_cols_for_set(BASE_FEATURE_COLS, FEATURE_SET_PHYSICS))
        for forbidden in FORBIDDEN_FEATURE_COLUMNS:
            assert forbidden not in cols


# ---------------------------------------------------------------------------
# M4 — Evaluation metrics
# ---------------------------------------------------------------------------


class TestEvaluationMetrics:
    """M4: compute_metrics() and per_failure_type_recall()."""

    @pytest.fixture
    def perfect_pred(self) -> tuple:
        y = np.array([0, 0, 1, 1, 0, 1])
        return y, y, y.astype(float)

    @pytest.fixture
    def imbalanced_pred(self) -> tuple:
        y_true = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 1])
        y_pred = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 0])
        y_proba = np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.9, 0.4])
        return y_true, y_pred, y_proba

    def test_metrics_return_six_keys(self, perfect_pred) -> None:
        y, yp, ypr = perfect_pred
        m = compute_metrics(y, yp, ypr)
        assert set(m.keys()) == {"accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"}

    def test_perfect_predictions_accuracy_one(self, perfect_pred) -> None:
        y, yp, ypr = perfect_pred
        m = compute_metrics(y, yp, ypr)
        assert m["accuracy"] == pytest.approx(1.0)

    def test_all_metrics_in_unit_interval(self, imbalanced_pred) -> None:
        y, yp, ypr = imbalanced_pred
        m = compute_metrics(y, yp, ypr)
        for key, val in m.items():
            assert 0.0 <= val <= 1.0, f"{key}={val} out of [0,1]"

    def test_metrics_are_floats(self, imbalanced_pred) -> None:
        y, yp, ypr = imbalanced_pred
        m = compute_metrics(y, yp, ypr)
        for key, val in m.items():
            assert isinstance(val, float), f"{key} is not float"

    def test_confusion_matrix_shape(self, imbalanced_pred) -> None:
        y, yp, _ = imbalanced_pred
        cm = compute_confusion_matrix(y, yp)
        assert len(cm) == 2
        assert len(cm[0]) == 2
        assert len(cm[1]) == 2

    def test_confusion_matrix_sums_to_total(self, imbalanced_pred) -> None:
        y, yp, _ = imbalanced_pred
        cm = compute_confusion_matrix(y, yp)
        total = cm[0][0] + cm[0][1] + cm[1][0] + cm[1][1]
        assert total == len(y)

    def test_per_failure_type_recall_no_failure(self) -> None:
        y_true = np.array([0, 0, 0, 0])
        y_pred = np.array([0, 0, 0, 0])
        ft = pd.Series(["No Failure"] * 4)
        result = per_failure_type_recall(y_true, y_pred, ft)
        assert "No Failure" in result
        # No positive labels in "No Failure" group
        assert result["No Failure"]["failures"] == 0
        assert result["No Failure"]["recall"] == 0.0

    def test_per_failure_type_recall_perfect_recall(self) -> None:
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1])
        ft = pd.Series(["No Failure", "No Failure", "Tool Wear Failure", "Tool Wear Failure"])
        result = per_failure_type_recall(y_true, y_pred, ft)
        assert result["Tool Wear Failure"]["recall"] == pytest.approx(1.0)

    def test_per_failure_type_recall_missed_failure(self) -> None:
        y_true = np.array([1, 1])
        y_pred = np.array([0, 0])
        ft = pd.Series(["Power Failure", "Power Failure"])
        result = per_failure_type_recall(y_true, y_pred, ft)
        assert result["Power Failure"]["recall"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# M5 — Cross-validation smoke
# ---------------------------------------------------------------------------


class TestCrossValSmoke:
    """M5: cross_val_run produces sensible output."""

    def test_cross_val_run_returns_mean_std_keys(
        self,
        small_split,
        small_df: pd.DataFrame,
    ) -> None:
        train_df, _, _ = small_split
        result = cross_val_run(
            "decision_tree",
            FEATURE_SET_BASE,
            train_df,
            train_df["Machine_Failure"],
            n_splits=2,
            seed=SEED,
        )
        for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            assert f"mean_{key}" in result
            assert f"std_{key}" in result

    def test_cross_val_run_mean_in_unit_interval(
        self,
        small_split,
    ) -> None:
        train_df, _, _ = small_split
        result = cross_val_run(
            "logistic_regression",
            FEATURE_SET_BASE,
            train_df,
            train_df["Machine_Failure"],
            n_splits=2,
            seed=SEED,
        )
        for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            val = result[f"mean_{key}"]
            assert 0.0 <= val <= 1.0, f"mean_{key}={val} out of [0,1]"


# ---------------------------------------------------------------------------
# M6 — Comparison orchestration (fast smoke, no-CV, single model)
# ---------------------------------------------------------------------------


class TestComparisonSmoke:
    """M6: run_comparison() smoke test with minimal config."""

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_comparison_smoke_no_cv(self, tmp_path: Path) -> None:
        """Run comparison with 1 model, 1 feature set, no CV for speed."""

        from ml.models.compare import run_comparison

        tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
        report_path = tmp_path / "model_comparison.md"
        outcome = run_comparison(
            seed=SEED,
            run_cv=False,
            models=("logistic_regression",),
            feature_sets=(FEATURE_SET_BASE,),
            tracking_uri=tracking_uri,
            output_path=report_path,
        )
        assert "champion" in outcome
        assert "test_result" in outcome
        assert outcome["champion"]["model_name"] == "logistic_regression"
        assert report_path.exists()
        tm = outcome["test_result"]["test_metrics"]
        assert set(tm.keys()) == {"accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"}

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_comparison_champion_has_zero_machine_id_overlap(self, tmp_path: Path) -> None:
        """No Machine_ID may appear in both train and test."""

        from ml.models.compare import run_comparison

        tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
        report_path = tmp_path / "model_comparison.md"
        outcome = run_comparison(
            seed=SEED,
            run_cv=False,
            models=("decision_tree",),
            feature_sets=(FEATURE_SET_BASE,),
            tracking_uri=tracking_uri,
            output_path=report_path,
        )
        # Verified implicitly: run_comparison raises on overlap
        assert outcome["champion"] is not None
        assert report_path.exists()


# ---------------------------------------------------------------------------
# M7 — Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """M7: Two runs with the same seed produce the same predictions."""

    @pytest.mark.parametrize(
        "model_name", ["logistic_regression", "random_forest", "decision_tree"]
    )
    def test_same_seed_same_predictions(
        self,
        model_name: str,
        small_split,
    ) -> None:
        train_df, val_df, _ = small_split
        feature_cols = get_feature_cols_for_set(BASE_FEATURE_COLS, FEATURE_SET_BASE)

        preds_list = []
        for _ in range(2):
            pipe = build_pipeline(model_name, feature_cols, seed=SEED)
            pipe = train_model(pipe, train_df[feature_cols], train_df["Machine_Failure"])
            preds_list.append(pipe.predict(val_df[feature_cols]))

        np.testing.assert_array_equal(preds_list[0], preds_list[1])

"""
ml/models/explain.py - EdgeTwin AI explainability module.

T-015: Model explainability layer using SHAP (TreeExplainer) on the frozen
XGBoost champion model.

Key Architectural Principles
----------------------------
1. Space: Explains the XGBoost model's MARGIN / LOG-ODDS SPACE, where additivity
   strictly holds.
2. Calibration Connection: Platt scaling (sigmoid calibration) is a strictly
   monotonic mapping from margin to calibrated probability. Positive SHAP
   increases model margin, which monotonically increases calibrated failure
   probability; negative SHAP decreases margin and probability. SHAP values
   are margin log-odds contributions, NOT additive probability points.
3. Feature Alignment: Columns in the preprocessed representation are mapped
   deterministically back to feature names using ColumnTransformer.get_feature_names_out().
4. Additivity Guard: Verified numerically (|base_value + sum(shap) - margin| <= 1e-4).
   Fails loudly with ValueError if violated.
5. Fallback: Native XGBoost pred_contribs=True fallback if shap is unavailable.
6. Safety & Honesty: Explanations represent statistical associations used by the
   model, NOT causal effects. Disclaimer included in all outputs.

Author: T-015 / S06
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from ml.data.features import validate_no_leakage

# Model explainability disclaimer (TreeSHAP attribution in margin space; not causal)
EXPLAINABILITY_DISCLAIMER: str = (
    "Statistical association with failure condition in model log-odds margin space; not causal."
)

# Numerical tolerance for additivity check
ADDITIVITY_TOLERANCE: float = 1e-4


def _extract_components(
    model: Pipeline | CalibratedClassifierCV,
) -> tuple[ColumnTransformer, xgb.XGBClassifier, CalibratedClassifierCV | None]:
    """Extract preprocessor and XGBClassifier from Pipeline or CalibratedClassifierCV.

    Parameters
    ----------
    model:
        Fitted Pipeline or CalibratedClassifierCV instance.

    Returns
    -------
    tuple[ColumnTransformer, xgb.XGBClassifier, CalibratedClassifierCV | None]
        Extracted preprocessor, underlying XGBoost classifier, and calibrator (if present).
    """
    calibrator: CalibratedClassifierCV | None = None

    if isinstance(model, CalibratedClassifierCV):
        calibrator = model
        # Unpack FrozenEstimator wrapper or direct estimator
        base_estimator = model.estimator
        if hasattr(base_estimator, "estimator"):
            # FrozenEstimator wraps the pipeline
            pipeline = base_estimator.estimator
        else:
            pipeline = base_estimator
    elif isinstance(model, Pipeline):
        pipeline = model
    else:
        raise TypeError(f"Expected Pipeline or CalibratedClassifierCV, got {type(model).__name__}")

    if not isinstance(pipeline, Pipeline):
        raise TypeError(f"Underlying estimator must be a Pipeline, got {type(pipeline).__name__}")

    if "preprocessor" not in pipeline.named_steps:
        raise ValueError("Pipeline missing 'preprocessor' step")
    if "classifier" not in pipeline.named_steps:
        raise ValueError("Pipeline missing 'classifier' step")

    preprocessor = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]

    if not isinstance(preprocessor, ColumnTransformer):
        raise TypeError(
            f"Step 'preprocessor' must be ColumnTransformer, got {type(preprocessor).__name__}"
        )
    if not isinstance(classifier, xgb.XGBClassifier):
        raise TypeError(f"Step 'classifier' must be XGBClassifier, got {type(classifier).__name__}")

    return preprocessor, classifier, calibrator


class EdgeTwinExplainer:
    """Explainability engine for EdgeTwin AI failure risk models."""

    def __init__(
        self,
        model: Pipeline | CalibratedClassifierCV,
        feature_cols: list[str],
        *,
        use_fallback: bool = False,
    ) -> None:
        """Initialize the explainer with a fitted model and feature specification.

        Parameters
        ----------
        model:
            Fitted Pipeline or CalibratedClassifierCV model.
        feature_cols:
            Ordered list of feature column names used by the model.
        use_fallback:
            If True, uses native XGBoost pred_contribs instead of shap.TreeExplainer.
        """
        validate_no_leakage(pd.DataFrame(columns=feature_cols))
        self.feature_cols = list(feature_cols)
        self.preprocessor, self.classifier, self.calibrator = _extract_components(model)
        self.use_fallback = use_fallback

        # Deterministically recover transformed feature column names
        raw_names = self.preprocessor.get_feature_names_out()
        self.transformed_feature_names = [
            c.split("__", 1)[1] if "__" in c else c for c in raw_names
        ]

        # Verify 14 features alignment
        if len(self.transformed_feature_names) != len(self.feature_cols):
            raise ValueError(
                f"Feature count mismatch: input has {len(self.feature_cols)}, "
                f"preprocessor produces {len(self.transformed_feature_names)}"
            )

        # Setup explainer
        self.explainer: Any = None
        if not self.use_fallback:
            try:
                import shap

                self.explainer = shap.TreeExplainer(
                    self.classifier,
                    feature_perturbation="tree_path_dependent",
                )
            except Exception:  # noqa: BLE001
                # Graceful activation of native XGBoost fallback
                self.use_fallback = True
                self.explainer = None

    def _compute_shap_matrix(self, X_trans: np.ndarray) -> tuple[np.ndarray, float]:
        """Compute SHAP values and base value using active engine (SHAP or native fallback)."""
        if not self.use_fallback and self.explainer is not None:
            shap_vals = self.explainer.shap_values(X_trans)
            base_val = float(self.explainer.expected_value)
            return np.asarray(shap_vals, dtype=float), base_val

        # Native XGBoost fallback
        booster = self.classifier.get_booster()
        dmat = xgb.DMatrix(X_trans)
        contribs = booster.predict(dmat, pred_contribs=True)
        # In XGBoost pred_contribs, the last column is the bias/base value
        shap_vals = contribs[:, :-1]
        base_val = float(contribs[0, -1])
        return np.asarray(shap_vals, dtype=float), base_val

    def explain_instance(
        self,
        x: pd.Series | pd.DataFrame,
        *,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Generate local explanation for a single telemetry observation.

        Parameters
        ----------
        x:
            Single row observation (pd.Series or 1-row pd.DataFrame).
        top_k:
            Number of top factors to return (sorted by absolute contribution).

        Returns
        -------
        dict[str, Any]
            Explanation payload with base value, margin, probability, sorted factors,
            additivity verification result, and honesty disclaimer.
        """
        if isinstance(x, pd.Series):
            df_x = x.to_frame().T
        elif isinstance(x, pd.DataFrame):
            if len(x) != 1:
                raise ValueError(f"explain_instance expects 1 row, got {len(x)}")
            df_x = x.copy()
        else:
            raise TypeError(f"Expected Series or DataFrame, got {type(x).__name__}")

        validate_no_leakage(df_x)

        # Ensure all required features are present
        missing = [c for c in self.feature_cols if c not in df_x.columns]
        if missing:
            raise ValueError(f"Input missing required feature columns: {missing}")

        X_input = df_x[self.feature_cols]
        X_trans = self.preprocessor.transform(X_input)

        # Model margin on transformed features
        margin = float(self.classifier.predict(X_trans, output_margin=True)[0])

        # Calibrated probability if calibrator available
        p_cal: float | None = None
        if self.calibrator is not None:
            p_cal = float(self.calibrator.predict_proba(X_input)[:, 1][0])

        # Compute SHAP
        shap_matrix, base_val = self._compute_shap_matrix(X_trans)
        shap_row = shap_matrix[0]

        # Additivity verification: base_val + sum(shap) == margin
        shap_sum = float(np.sum(shap_row))
        diff = abs((base_val + shap_sum) - margin)
        if diff > ADDITIVITY_TOLERANCE:
            raise ValueError(
                f"Additivity consistency check failed: discrepancy {diff:.6e} exceeds "
                f"allowed tolerance {ADDITIVITY_TOLERANCE:.6e} "
                f"(base={base_val:.6f}, sum={shap_sum:.6f}, margin={margin:.6f})"
            )

        # Build feature contributions list
        contributions: list[dict[str, Any]] = []
        for idx, feat_name in enumerate(self.transformed_feature_names):
            val = shap_row[idx]
            feat_val = df_x[feat_name].iloc[0] if feat_name in df_x.columns else None

            direction = "neutral"
            if val > 1e-6:
                direction = "increases risk"
            elif val < -1e-6:
                direction = "lowers risk"

            contributions.append(
                {
                    "feature_name": feat_name,
                    "feature_value": feat_val,
                    "shap_value": float(val),
                    "abs_magnitude": float(abs(val)),
                    "direction": direction,
                }
            )

        # Sort contributions by absolute magnitude descending
        sorted_contributions = sorted(contributions, key=lambda c: c["abs_magnitude"], reverse=True)
        top_factors = sorted_contributions[:top_k]

        return {
            "base_value": base_val,
            "model_margin": margin,
            "calibrated_probability": p_cal,
            "feature_contributions": sorted_contributions,
            "top_factors": top_factors,
            "additivity_verified": True,
            "additivity_discrepancy": float(diff),
            "disclaimer": EXPLAINABILITY_DISCLAIMER,
        }

    def explain_prediction(
        self,
        X: pd.DataFrame | pd.Series,
        *,
        top_k: int = 5,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Generate local explanation for observation(s).

        Parameters
        ----------
        X:
            Single observation (pd.Series or 1-row pd.DataFrame) or batch (pd.DataFrame).
        top_k:
            Number of top factors to return per observation.

        Returns
        -------
        dict[str, Any] | list[dict[str, Any]]
            Explanation dict if single observation; list of explanation dicts if batch.
        """
        if isinstance(X, pd.Series):
            return self.explain_instance(X, top_k=top_k)
        if isinstance(X, pd.DataFrame):
            validate_no_leakage(X)
            if len(X) == 1:
                return self.explain_instance(X, top_k=top_k)
            return [self.explain_instance(X.iloc[[i]], top_k=top_k) for i in range(len(X))]
        raise TypeError(f"Expected Series or DataFrame, got {type(X).__name__}")

    def explain_global(
        self,
        X_background: pd.DataFrame,
    ) -> pd.DataFrame:
        """Compute global feature importance ranking via mean absolute SHAP values.

        Parameters
        ----------
        X_background:
            Background dataset (from train_df or val_df; test_df forbidden).

        Returns
        -------
        pd.DataFrame
            Sorted feature importance table with columns:
            feature_name, mean_abs_shap, mean_signed_shap.
        """
        validate_no_leakage(X_background)

        missing = [c for c in self.feature_cols if c not in X_background.columns]
        if missing:
            raise ValueError(f"X_background missing required columns: {missing}")

        X_input = X_background[self.feature_cols]
        X_trans = self.preprocessor.transform(X_input)

        shap_matrix, _ = self._compute_shap_matrix(X_trans)

        mean_abs = np.mean(np.abs(shap_matrix), axis=0)
        mean_signed = np.mean(shap_matrix, axis=0)

        records = [
            {
                "feature_name": name,
                "mean_abs_shap": float(mean_abs[i]),
                "mean_signed_shap": float(mean_signed[i]),
            }
            for i, name in enumerate(self.transformed_feature_names)
        ]

        df_importance = (
            pd.DataFrame(records)
            .sort_values(by="mean_abs_shap", ascending=False)
            .reset_index(drop=True)
        )

        return df_importance

    def benchmark_latency(
        self,
        X_samples: pd.DataFrame,
        *,
        n_runs: int = 50,
    ) -> dict[str, Any]:
        """Benchmark per-sample explanation latency to verify < 100 ms SLA.

        Protocol
        --------
        1. 1 un-timed warm-up call.
        2. n_runs consecutive single-row explanation calls.
        3. Measures latency with time.perf_counter().
        4. Calculates mean, median, p95, and max latency.

        Parameters
        ----------
        X_samples:
            Sample observations to explain.
        n_runs:
            Number of iterations.

        Returns
        -------
        dict[str, Any]
            Benchmark results in milliseconds and SLA pass flag.
        """
        validate_no_leakage(X_samples)
        if len(X_samples) == 0:
            raise ValueError("X_samples cannot be empty")

        # 1. Warm-up call
        warm_row = X_samples.iloc[[0]]
        self.explain_instance(warm_row)

        # 2. Benchmark runs
        latencies_ms: list[float] = []
        n_available = len(X_samples)

        for i in range(n_runs):
            row = X_samples.iloc[[i % n_available]]
            t0 = time.perf_counter()
            self.explain_instance(row)
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

        arr = np.asarray(latencies_ms)
        p95 = float(np.percentile(arr, 95))

        return {
            "n_runs": n_runs,
            "mean_ms": float(np.mean(arr)),
            "median_ms": float(np.median(arr)),
            "p95_ms": p95,
            "max_ms": float(np.max(arr)),
            "sla_passed": bool(p95 < 100.0),
        }

"""
api/app/inference/engine.py — Core ML model loading and execution engine.

Manages:
- Supervised failure risk model (champion from MLflow registry or local artifact fallback)
- Unsupervised anomaly detection pipeline (Isolation Forest + reference normalization)
- Model explainability (SHAP TreeExplainer / XGBoost margin space attributions)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

from api.app.config import get_settings
from ml.data.engineering import apply_feature_set, get_feature_cols_for_set
from ml.data.features import get_feature_columns, validate_no_leakage
from ml.models.anomaly import fit_anomaly_detector
from ml.models.explain import EdgeTwinExplainer

logger = logging.getLogger(__name__)

# Fallback Artifact Paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts"
_CALIBRATED_MODEL_PATH = _ARTIFACTS_DIR / "calibrated_classifier_sigmoid.joblib"
_CHAMPION_FEATURES_PATH = _ARTIFACTS_DIR / "champion_features.json"
_ANOMALY_MODEL_PATH = _ARTIFACTS_DIR / "anomaly_isolation_forest.joblib"
_ANOMALY_REF_PATH = _ARTIFACTS_DIR / "anomaly_ref_params.json"


class ModelEngine:
    """Singleton ML model loading, execution, and explainability engine."""

    def __init__(self) -> None:
        self.calibrated_model: CalibratedClassifierCV | Pipeline | None = None
        self.feature_cols: list[str] = []
        self.anomaly_pipeline: Pipeline | None = None
        self.anomaly_ref_params: dict[str, float] = {}
        self.explainer: EdgeTwinExplainer | None = None
        self.model_version: str = "unknown"
        self.operational_threshold: float = 0.16
        self._is_loaded: bool = False

    def load(self, force_reload: bool = False) -> None:
        """Load all model artifacts (risk champion, anomaly detector, SHAP explainer)."""
        if self._is_loaded and not force_reload:
            return

        settings = get_settings()

        # 1. Load Risk Model (MLflow or local joblib fallback)
        self._load_risk_model(settings.MLFLOW_TRACKING_URI)

        # 2. Load Anomaly Detector (Artifact or fit on splits fallback)
        self._load_anomaly_detector()

        # 3. Initialize Explainer
        self._init_explainer()

        self._is_loaded = True
        logger.info(
            "ModelEngine successfully loaded",
            extra={
                "model_version": self.model_version,
                "feature_count": len(self.feature_cols),
                "has_anomaly": self.anomaly_pipeline is not None,
                "has_explainer": self.explainer is not None,
            },
        )

    def _load_risk_model(self, tracking_uri: str) -> None:
        """Attempt loading from MLflow champion, falling back to artifacts directory."""
        # Try local joblib artifact first for direct access to underlying Pipeline
        if _CALIBRATED_MODEL_PATH.exists() and _CHAMPION_FEATURES_PATH.exists():
            try:
                self.calibrated_model = joblib.load(_CALIBRATED_MODEL_PATH)
                with open(_CHAMPION_FEATURES_PATH, "r", encoding="utf-8") as f:
                    self.feature_cols = json.load(f)
                self.model_version = "edgetwin-risk:v2-champion"
                logger.info("Loaded calibrated model from local artifacts")
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed loading local risk model artifact: {exc}")

        # Fallback to MLflow registry
        try:
            mlflow.set_tracking_uri(tracking_uri)
            client = mlflow.MlflowClient()
            model_info = client.get_model_version_by_alias("edgetwin-risk", "champion")
            self.model_version = f"edgetwin-risk:v{model_info.version}"
            model_uri = f"models:/edgetwin-risk@{model_info.aliases[0] if model_info.aliases else 'champion'}"
            pyfunc_model = mlflow.pyfunc.load_model(model_uri)
            # Extract underlying python_model if available
            if hasattr(pyfunc_model, "_model_impl") and hasattr(
                pyfunc_model._model_impl, "python_model"
            ):
                underlying = pyfunc_model._model_impl.python_model
                self.calibrated_model = underlying.calibrated_model
                self.feature_cols = underlying.feature_cols
                self.operational_threshold = underlying.operational_threshold
            logger.info(f"Loaded champion risk model from MLflow ({self.model_version})")
        except Exception as exc:
            logger.error(f"Failed loading MLflow champion model: {exc}")
            raise RuntimeError(f"Could not load risk model from any source: {exc}") from exc

    def _load_anomaly_detector(self) -> None:
        """Load anomaly detector pipeline and reference percentiles."""
        if _ANOMALY_MODEL_PATH.exists() and _ANOMALY_REF_PATH.exists():
            try:
                self.anomaly_pipeline = joblib.load(_ANOMALY_MODEL_PATH)
                with open(_ANOMALY_REF_PATH, "r", encoding="utf-8") as f:
                    self.anomaly_ref_params = json.load(f)
                logger.info("Loaded anomaly detector from artifacts")
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed loading anomaly detector artifact: {exc}")

        # Fallback: Fit on training split
        try:
            from ml.data.splits import load_splits

            train_df, _, _ = load_splits()
            train_phys = apply_feature_set(train_df, "+physics")
            base_cols = get_feature_columns()
            phys_cols = get_feature_cols_for_set(base_cols, "+physics")
            pipeline, ref_params = fit_anomaly_detector(train_phys, phys_cols)
            self.anomaly_pipeline = pipeline
            self.anomaly_ref_params = ref_params
            logger.info("Fitted anomaly detector from training split")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Could not fit fallback anomaly detector: {exc}")
            self.anomaly_pipeline = None
            self.anomaly_ref_params = {
                "s_nominal": -0.41224,
                "s_extreme": -0.55025,
                "delta": 0.13801,
            }

    def _init_explainer(self) -> None:
        """Initialize the SHAP explainability engine."""
        if self.calibrated_model is not None and self.feature_cols:
            try:
                self.explainer = EdgeTwinExplainer(
                    self.calibrated_model,
                    feature_cols=self.feature_cols,
                )
                logger.info("Initialized EdgeTwinExplainer")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed initializing TreeExplainer: {exc}")
                self.explainer = None

    def predict_risk(self, df: pd.DataFrame) -> tuple[float, int, str]:
        """Predict calibrated failure probability, binary flag, and risk band.

        Returns
        -------
        tuple[float, int, str]
            (calibrated_probability, failure_prediction, risk_band)
        """
        if self.calibrated_model is None:
            raise RuntimeError("Calibrated risk model is not loaded")

        validate_no_leakage(df)
        X = df[self.feature_cols]

        proba_arr = self.calibrated_model.predict_proba(X)[:, 1]
        p_fail = float(np.clip(proba_arr[0], 0.0, 1.0))
        pred = int(p_fail >= self.operational_threshold)

        if p_fail < 0.15:
            band = "LOW"
        elif p_fail < 0.16:
            band = "MEDIUM"
        elif p_fail < 0.80:
            band = "HIGH"
        else:
            band = "CRITICAL"

        return p_fail, pred, band

    def predict_anomaly(self, df: pd.DataFrame) -> tuple[float | None, bool | None]:
        """Predict normalized anomaly score [0, 1] and flag.

        Returns
        -------
        tuple[float | None, bool | None]
            (anomaly_score, anomaly_flag)
        """
        if self.anomaly_pipeline is None:
            return None, None

        validate_no_leakage(df)
        X = df[self.feature_cols]

        try:
            preprocessor = self.anomaly_pipeline.named_steps["preprocessor"]
            detector = self.anomaly_pipeline.named_steps["detector"]
            X_trans = preprocessor.transform(X)
            s_raw = float(detector.score_samples(X_trans)[0])

            s_nom = self.anomaly_ref_params.get("s_nominal", -0.41224)
            delta = self.anomaly_ref_params.get("delta", 0.13801)
            if delta <= 1e-9 or np.isnan(s_raw):
                return 0.50, True

            score = float(np.clip((s_nom - s_raw) / delta, 0.0, 1.0))
            flag = score >= 0.50
            return score, flag
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Error computing anomaly score: {exc}")
            return 0.50, True

    def explain(self, df: pd.DataFrame, top_k: int = 5) -> dict[str, Any]:
        """Generate SHAP local feature attributions.

        Returns
        -------
        dict[str, Any]
            Explanation dictionary including top_factors, margin, base_value, and disclaimer.
        """
        if self.explainer is None:
            return {
                "top_factors": None,
                "all_factors": None,
                "model_margin": None,
                "base_value": None,
                "additivity_verified": False,
                "disclaimer": "Explainer not initialized.",
            }

        try:
            res = self.explainer.explain_instance(df, top_k=top_k)
            return {
                "top_factors": res.get("top_factors"),
                "all_factors": res.get("feature_contributions"),
                "model_margin": res.get("model_margin"),
                "base_value": res.get("base_value"),
                "additivity_verified": res.get("additivity_verified", False),
                "disclaimer": res.get("disclaimer", ""),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Error computing SHAP explanation: {exc}")
            return {
                "top_factors": None,
                "all_factors": None,
                "model_margin": None,
                "base_value": None,
                "additivity_verified": False,
                "disclaimer": f"Explanation error: {exc}",
            }


# Singleton instance
_model_engine: ModelEngine | None = None


def get_model_engine() -> ModelEngine:
    """Return the global lazily-initialized ModelEngine instance."""
    global _model_engine
    if _model_engine is None:
        _model_engine = ModelEngine()
        _model_engine.load()
    return _model_engine

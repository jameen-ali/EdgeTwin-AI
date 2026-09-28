"""
api/app/inference/service.py — High-level ML inference and health assessment service.

Orchestrates:
1. Wire telemetry normalization and feature engineering
2. Supervised risk inference (XGBoost + Platt calibration)
3. Unsupervised anomaly detection (Isolation Forest)
4. Model explainability (SHAP attributions)
5. Multi-layer health assessment (Layers 1-6)
6. Database persistence of predictions and alerts
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from api.app.inference.engine import ModelEngine, get_model_engine
from api.app.inference.health_engine import HealthEngine
from api.app.inference.persistence import persist_prediction
from api.app.inference.schemas import InferenceResult
from api.app.models.alert import AlertRecord
from api.app.models.prediction import PredictionRecord
from ml.data.engineering import apply_feature_set
from simulation.contract import telemetry_to_feature_df

logger = logging.getLogger(__name__)


class InferenceService:
    """Production ML Inference and Health Engine Service."""

    def __init__(
        self,
        model_engine: ModelEngine | None = None,
        health_engine: HealthEngine | None = None,
    ) -> None:
        self.model_engine = model_engine or get_model_engine()
        self.health_engine = health_engine or HealthEngine()

    def run_inference(
        self,
        payload: dict[str, Any],
        telemetry_id: int | None = None,
        *,
        top_k: int = 5,
        technician_confirmed_maintenance: bool = False,
        is_offline: bool = False,
    ) -> InferenceResult:
        """Execute end-to-end inference, anomaly detection, SHAP attribution, and health assessment.

        Parameters
        ----------
        payload:
            Validated telemetry payload dictionary.
        telemetry_id:
            Optional primary key of the associated TelemetryRecord in PostgreSQL/SQLite.
        top_k:
            Number of top SHAP factors to return.
        technician_confirmed_maintenance:
            Technician maintenance override flag.
        is_offline:
            Machine offline flag.

        Returns
        -------
        InferenceResult
            Complete structured inference bundle.
        """
        start_time = time.perf_counter()

        machine_id = str(payload.get("machine_id", "UNKNOWN"))
        raw_ts = payload.get("ts")
        if isinstance(raw_ts, str):
            try:
                ts = datetime.fromisoformat(raw_ts)
            except ValueError:
                ts = datetime.now(UTC)
        elif isinstance(raw_ts, datetime):
            ts = raw_ts
        else:
            ts = datetime.now(UTC)

        # 1. Feature Extraction and Engineering
        df_base = telemetry_to_feature_df(payload)
        df_phys = apply_feature_set(df_base, "+physics")

        # 2. Supervised Risk Prediction (Layer 2)
        p_fail, failure_pred, risk_band = self.model_engine.predict_risk(df_phys)

        # 3. Unsupervised Anomaly Detection (Layer 3)
        anomaly_score, anomaly_flag = self.model_engine.predict_anomaly(df_phys)

        # 4. Explainability Attributions (SHAP)
        explanation = self.model_engine.explain(df_phys, top_k=top_k)
        top_factors = explanation.get("top_factors")
        all_factors = explanation.get("all_factors")
        model_margin = explanation.get("model_margin")
        base_value = explanation.get("base_value")
        additivity_verified = explanation.get("additivity_verified", False)
        disclaimer = explanation.get("disclaimer", "")

        # 5. Multi-Layer Health Evaluation (Layers 1-6)
        health_assessment = self.health_engine.evaluate_payload(
            payload,
            failure_probability=p_fail,
            anomaly_score=anomaly_score,
            top_factors=top_factors,
            technician_confirmed_maintenance=technician_confirmed_maintenance,
            is_offline=is_offline,
        )

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000.0

        return InferenceResult(
            machine_id=machine_id,
            ts=ts,
            telemetry_id=telemetry_id,
            failure_probability=p_fail,
            failure_prediction=failure_pred,
            risk_band=risk_band,
            anomaly_score=anomaly_score,
            anomaly_flag=anomaly_flag,
            health_score=health_assessment.health_score,
            health_state=health_assessment.health_state,
            top_factors=top_factors,
            all_factors=all_factors,
            model_margin=model_margin,
            base_value=base_value,
            additivity_verified=additivity_verified,
            disclaimer=disclaimer,
            health_assessment=health_assessment,
            model_version=self.model_engine.model_version,
            inference_latency_ms=latency_ms,
        )

    def process_and_persist(
        self,
        db: Session,
        payload: dict[str, Any],
        telemetry_id: int | None = None,
        *,
        top_k: int = 5,
        create_alert: bool = True,
    ) -> tuple[InferenceResult, PredictionRecord, AlertRecord | None]:
        """Execute inference and persist the results in the database.

        Parameters
        ----------
        db:
            Active SQLAlchemy database session.
        payload:
            Validated telemetry dictionary.
        telemetry_id:
            Primary key of the associated TelemetryRecord.
        top_k:
            Number of top SHAP features to compute.
        create_alert:
            Whether to persist AlertRecord if warning/critical.

        Returns
        -------
        tuple[InferenceResult, PredictionRecord, AlertRecord | None]
            Result bundle, persisted prediction entity, and optional alert entity.
        """
        result = self.run_inference(payload, telemetry_id=telemetry_id, top_k=top_k)
        pred_record, alert_record = persist_prediction(db, result, create_alert=create_alert)
        return result, pred_record, alert_record


# Singleton instance
_inference_service: InferenceService | None = None


def get_inference_service() -> InferenceService:
    """Return the global lazily-initialized InferenceService singleton."""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service

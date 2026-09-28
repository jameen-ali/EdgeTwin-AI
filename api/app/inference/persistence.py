"""
api/app/inference/persistence.py — Database persistence for ML predictions and alerts.

Persists:
- PredictionRecord (Layer 2 Risk, Layer 3 Anomaly, Layer 4 Health, Layer 5 SHAP factors)
- AlertRecord (Layer 5 alerts when severity is WARNING or CRITICAL)
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.inference.schemas import InferenceResult
from api.app.models.alert import AlertRecord
from api.app.models.prediction import PredictionRecord

logger = logging.getLogger(__name__)


def persist_prediction(
    db: Session,
    result: InferenceResult,
    *,
    create_alert: bool = True,
) -> tuple[PredictionRecord, AlertRecord | None]:
    """Persist an InferenceResult as a PredictionRecord and manage associated alerts.

    Parameters
    ----------
    db:
        Active SQLAlchemy database session.
    result:
        Computed InferenceResult object.
    create_alert:
        If True, auto-creates an AlertRecord when alert_severity is WARNING or CRITICAL.

    Returns
    -------
    tuple[PredictionRecord, AlertRecord | None]
        Persisted prediction record and optional alert record.
    """
    # 1. Create PredictionRecord
    pred_record = PredictionRecord(
        machine_id=result.machine_id,
        telemetry_id=result.telemetry_id,
        ts=result.ts,
        failure_probability=result.failure_probability,
        failure_prediction=result.failure_prediction,
        risk_band=result.risk_band,
        anomaly_score=result.anomaly_score,
        anomaly_flag=result.anomaly_flag,
        health_score=result.health_score,
        health_state=result.health_state,
        top_factors=result.top_factors,
        model_version=result.model_version,
        inference_latency_ms=result.inference_latency_ms,
    )
    db.add(pred_record)

    # 2. Check and create AlertRecord if necessary
    alert_record: AlertRecord | None = None
    severity = result.health_assessment.alert_severity

    if create_alert and severity in ("WARNING", "CRITICAL"):
        alert_type = result.health_assessment.alert_type or "UNSPECIFIED_ALERT"

        # Check if an OPEN alert of the same type already exists for this machine to prevent flooding
        stmt = (
            select(AlertRecord)
            .where(
                AlertRecord.machine_id == result.machine_id,
                AlertRecord.alert_type == alert_type,
                AlertRecord.status == "OPEN",
            )
            .limit(1)
        )
        existing_alert = db.execute(stmt).scalar_one_or_none()

        if existing_alert is None:
            # Build informative alert message
            msg = _build_alert_message(result)
            alert_record = AlertRecord(
                machine_id=result.machine_id,
                alert_type=alert_type,
                severity=severity,
                status="OPEN",
                message=msg,
                trigger_conditions=result.health_assessment.trigger_conditions,
                top_factors=result.top_factors,
                triggered_at=result.ts,
            )
            db.add(alert_record)
            logger.warning(
                f"Raised {severity} alert for {result.machine_id}: {msg}",
                extra={
                    "machine_id": result.machine_id,
                    "alert_type": alert_type,
                    "severity": severity,
                },
            )

    try:
        db.commit()
        db.refresh(pred_record)
        if alert_record is not None:
            db.refresh(alert_record)
    except Exception as exc:
        db.rollback()
        logger.error(
            f"Failed to persist prediction for {result.machine_id}: {exc}",
            extra={"machine_id": result.machine_id, "error": str(exc)},
        )
        raise

    return pred_record, alert_record


def _build_alert_message(result: InferenceResult) -> str:
    """Build a concise, actionable alert message."""
    state = result.health_state
    p_fail = result.failure_probability
    rec = result.health_assessment.recommendation

    parts = [f"Machine {result.machine_id} entered state {state}"]
    if p_fail >= 0.16:
        parts.append(f"(Failure Probability: {p_fail:.1%})")
    if rec and rec.recommendation_text:
        parts.append(f"— {rec.action_code}: {rec.recommendation_text}")

    return " ".join(parts)[:255]

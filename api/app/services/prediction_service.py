"""Prediction service for querying historical ML risk and health assessments."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models.machine import MachineRecord
from api.app.models.prediction import PredictionRecord
from api.app.schemas.prediction import PredictionDTO, PredictionListResponse


class PredictionService:
    """Service layer for querying historical prediction records."""

    @staticmethod
    def get_predictions(
        db: Session,
        machine_id: str,
        limit: int = 50,
        offset: int = 0,
        before: datetime | None = None,
        after: datetime | None = None,
    ) -> PredictionListResponse:
        """Query bounded prediction history for a specific machine without recomputing ML inference."""
        # 1. Verify machine exists
        machine_exists = db.execute(
            select(MachineRecord.machine_id).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if machine_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        # 2. Build filtered queries
        query = select(PredictionRecord).where(PredictionRecord.machine_id == machine_id)
        count_query = select(func.count(PredictionRecord.id)).where(
            PredictionRecord.machine_id == machine_id
        )

        if before is not None:
            query = query.where(PredictionRecord.ts <= before)
            count_query = count_query.where(PredictionRecord.ts <= before)

        if after is not None:
            query = query.where(PredictionRecord.ts >= after)
            count_query = count_query.where(PredictionRecord.ts >= after)

        total = db.execute(count_query).scalar_one()

        records = (
            db.execute(query.order_by(PredictionRecord.ts.desc()).limit(limit).offset(offset))
            .scalars()
            .all()
        )

        items = [
            PredictionDTO(
                id=r.id,
                machine_id=r.machine_id,
                telemetry_id=r.telemetry_id,
                ts=r.ts,
                failure_probability=r.failure_probability,
                failure_prediction=r.failure_prediction,
                risk_band=r.risk_band,
                anomaly_score=r.anomaly_score,
                anomaly_flag=r.anomaly_flag,
                health_score=r.health_score,
                health_state=r.health_state,
                top_factors=r.top_factors,
                model_version=r.model_version,
                inference_latency_ms=r.inference_latency_ms,
                created_at=r.created_at,
            )
            for r in records
        ]

        return PredictionListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

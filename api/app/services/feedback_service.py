"""Feedback service for recording operator/technician verifications."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.models.alert import AlertRecord
from api.app.models.feedback import FeedbackRecord
from api.app.models.machine import MachineRecord
from api.app.models.prediction import PredictionRecord
from api.app.schemas.feedback import FeedbackCreateRequest, FeedbackDTO


class FeedbackService:
    """Service layer for operator and technician feedback submission."""

    @staticmethod
    def create_feedback(
        db: Session,
        machine_id: str,
        payload: FeedbackCreateRequest,
    ) -> FeedbackDTO:
        """Validate references and persist an engineer feedback record."""
        # 1. Validate machine exists
        machine_exists = db.execute(
            select(MachineRecord.machine_id).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if machine_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        # 2. If prediction_id is provided, validate it exists for this machine
        if payload.prediction_id is not None:
            prediction_exists = db.execute(
                select(PredictionRecord.id).where(
                    PredictionRecord.id == payload.prediction_id,
                    PredictionRecord.machine_id == machine_id,
                )
            ).scalar_one_or_none()

            if prediction_exists is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Prediction '{payload.prediction_id}' not found for machine '{machine_id}'.",
                )

        # 3. If alert_id is provided, validate it exists for this machine
        if payload.alert_id is not None:
            alert_exists = db.execute(
                select(AlertRecord.id).where(
                    AlertRecord.id == payload.alert_id,
                    AlertRecord.machine_id == machine_id,
                )
            ).scalar_one_or_none()

            if alert_exists is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Alert '{payload.alert_id}' not found for machine '{machine_id}'.",
                )

        # 4. Feedback type is guaranteed normalized by Pydantic model validator
        feedback_type = payload.feedback_type or "CONFIRMED"

        record = FeedbackRecord(
            machine_id=machine_id,
            alert_id=payload.alert_id,
            feedback_type=feedback_type,
            notes=payload.notes,
            user_id=payload.technician_id,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return FeedbackDTO(
            id=record.id,
            machine_id=record.machine_id,
            alert_id=record.alert_id,
            feedback_type=record.feedback_type,
            notes=record.notes,
            user_id=record.user_id,
            created_at=record.created_at,
        )

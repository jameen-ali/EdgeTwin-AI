"""Feedback service for recording operator/technician verifications."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models.alert import AlertRecord
from api.app.models.feedback import FeedbackRecord
from api.app.models.machine import MachineRecord
from api.app.models.prediction import PredictionRecord
from api.app.schemas.feedback import FeedbackCreateRequest, FeedbackDTO, FeedbackListResponse


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

            # Prevent duplicate feedback on the same alert
            existing_feedback = db.execute(
                select(FeedbackRecord.id).where(
                    FeedbackRecord.machine_id == machine_id,
                    FeedbackRecord.alert_id == payload.alert_id,
                )
            ).scalar_one_or_none()

            if existing_feedback is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Feedback has already been submitted for alert '{payload.alert_id}'.",
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

    @staticmethod
    def get_feedback_by_machine(
        db: Session,
        machine_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> FeedbackListResponse:
        """Query bounded operator feedback history for a specific machine."""
        machine_exists = db.execute(
            select(MachineRecord.machine_id).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if machine_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        query = select(FeedbackRecord).where(FeedbackRecord.machine_id == machine_id)
        count_query = select(func.count(FeedbackRecord.id)).where(
            FeedbackRecord.machine_id == machine_id
        )

        total = db.execute(count_query).scalar_one()

        records = (
            db.execute(query.order_by(FeedbackRecord.created_at.desc()).limit(limit).offset(offset))
            .scalars()
            .all()
        )

        items = [
            FeedbackDTO(
                id=r.id,
                machine_id=r.machine_id,
                alert_id=r.alert_id,
                feedback_type=r.feedback_type,
                notes=r.notes,
                user_id=r.user_id,
                created_at=r.created_at,
            )
            for r in records
        ]

        return FeedbackListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

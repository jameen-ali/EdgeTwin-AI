"""Alert service for querying and managing alert lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models.alert import AlertRecord
from api.app.models.machine import MachineRecord
from api.app.schemas.alert import AlertDTO, AlertListResponse


class AlertService:
    """Service layer for alert queries and lifecycle status changes."""

    @staticmethod
    def get_alerts(
        db: Session,
        severity: str | None = None,
        alert_status: str | None = None,
        acknowledged: bool | None = None,
        machine_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        before: datetime | None = None,
        after: datetime | None = None,
    ) -> AlertListResponse:
        """Query bounded fleet-wide alerts with optional filters."""
        query = select(AlertRecord)
        count_query = select(func.count(AlertRecord.id))

        if machine_id is not None:
            query = query.where(AlertRecord.machine_id == machine_id)
            count_query = count_query.where(AlertRecord.machine_id == machine_id)

        if severity is not None:
            query = query.where(AlertRecord.severity == severity.upper().strip())
            count_query = count_query.where(AlertRecord.severity == severity.upper().strip())

        if alert_status is not None:
            query = query.where(AlertRecord.status == alert_status.upper().strip())
            count_query = count_query.where(AlertRecord.status == alert_status.upper().strip())

        if acknowledged is True:
            query = query.where(AlertRecord.status.in_(["ACKNOWLEDGED", "RESOLVED"]))
            count_query = count_query.where(AlertRecord.status.in_(["ACKNOWLEDGED", "RESOLVED"]))
        elif acknowledged is False:
            query = query.where(AlertRecord.status == "OPEN")
            count_query = count_query.where(AlertRecord.status == "OPEN")

        if before is not None:
            query = query.where(AlertRecord.triggered_at <= before)
            count_query = count_query.where(AlertRecord.triggered_at <= before)

        if after is not None:
            query = query.where(AlertRecord.triggered_at >= after)
            count_query = count_query.where(AlertRecord.triggered_at >= after)

        total = db.execute(count_query).scalar_one()

        records = (
            db.execute(query.order_by(AlertRecord.triggered_at.desc()).limit(limit).offset(offset))
            .scalars()
            .all()
        )

        items = [
            AlertDTO(
                id=r.id,
                machine_id=r.machine_id,
                alert_type=r.alert_type,
                severity=r.severity,
                status=r.status,
                message=r.message,
                trigger_conditions=r.trigger_conditions,
                top_factors=r.top_factors,
                triggered_at=r.triggered_at,
                acknowledged_at=r.acknowledged_at,
                resolved_at=r.resolved_at,
                resolved_by=r.resolved_by,
            )
            for r in records
        ]

        return AlertListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def get_machine_alerts(
        db: Session,
        machine_id: str,
        severity: str | None = None,
        alert_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AlertListResponse:
        """Query bounded alerts for a single machine."""
        machine_exists = db.execute(
            select(MachineRecord.machine_id).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if machine_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        return AlertService.get_alerts(
            db=db,
            machine_id=machine_id,
            severity=severity,
            alert_status=alert_status,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def get_alert_by_id(db: Session, alert_id: int) -> AlertDTO:
        """Retrieve a single alert by sequence ID."""
        alert = db.execute(
            select(AlertRecord).where(AlertRecord.id == alert_id)
        ).scalar_one_or_none()

        if alert is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert '{alert_id}' not found.",
            )

        return AlertDTO(
            id=alert.id,
            machine_id=alert.machine_id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            status=alert.status,
            message=alert.message,
            trigger_conditions=alert.trigger_conditions,
            top_factors=alert.top_factors,
            triggered_at=alert.triggered_at,
            acknowledged_at=alert.acknowledged_at,
            resolved_at=alert.resolved_at,
            resolved_by=alert.resolved_by,
        )

    @staticmethod
    def acknowledge_alert(
        db: Session,
        alert_id: int,
        resolved_by: str | None = None,
        notes: str | None = None,
        new_status: str = "ACKNOWLEDGED",
    ) -> AlertDTO:
        """Update an alert's lifecycle status to ACKNOWLEDGED or RESOLVED."""
        alert = db.execute(
            select(AlertRecord).where(AlertRecord.id == alert_id)
        ).scalar_one_or_none()

        if alert is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert '{alert_id}' not found.",
            )

        now = datetime.now(UTC)
        norm_status = new_status.upper().strip()

        if norm_status not in ("ACKNOWLEDGED", "RESOLVED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid alert status '{new_status}'. Status must be 'ACKNOWLEDGED' or 'RESOLVED'.",
            )

        if alert.status == "RESOLVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Alert '{alert_id}' is already RESOLVED and cannot be transitioned to '{norm_status}'.",
            )

        if norm_status == "RESOLVED":
            alert.status = "RESOLVED"
            alert.resolved_at = now
            if resolved_by:
                alert.resolved_by = resolved_by
            if alert.acknowledged_at is None:
                alert.acknowledged_at = now
        else:
            alert.status = "ACKNOWLEDGED"
            alert.acknowledged_at = now
            if resolved_by:
                alert.resolved_by = resolved_by

        db.commit()
        db.refresh(alert)

        return AlertDTO(
            id=alert.id,
            machine_id=alert.machine_id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            status=alert.status,
            message=alert.message,
            trigger_conditions=alert.trigger_conditions,
            top_factors=alert.top_factors,
            triggered_at=alert.triggered_at,
            acknowledged_at=alert.acknowledged_at,
            resolved_at=alert.resolved_at,
            resolved_by=alert.resolved_by,
        )

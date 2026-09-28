"""Maintenance service for querying maintenance records and history."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models.machine import MachineRecord
from api.app.models.maintenance import MaintenanceRecord
from api.app.schemas.maintenance import MaintenanceDTO, MaintenanceListResponse


class MaintenanceService:
    """Service layer for querying maintenance logs and work orders."""

    @staticmethod
    def get_maintenance_events(
        db: Session,
        machine_id: str,
        event_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> MaintenanceListResponse:
        """Query bounded maintenance history for a specific machine."""
        machine_exists = db.execute(
            select(MachineRecord.machine_id).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if machine_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        query = select(MaintenanceRecord).where(MaintenanceRecord.machine_id == machine_id)
        count_query = select(func.count(MaintenanceRecord.id)).where(
            MaintenanceRecord.machine_id == machine_id
        )

        if event_status is not None:
            query = query.where(MaintenanceRecord.status == event_status.upper().strip())
            count_query = count_query.where(
                MaintenanceRecord.status == event_status.upper().strip()
            )

        total = db.execute(count_query).scalar_one()

        records = (
            db.execute(
                query.order_by(MaintenanceRecord.created_at.desc()).limit(limit).offset(offset)
            )
            .scalars()
            .all()
        )

        items = [
            MaintenanceDTO(
                id=r.id,
                machine_id=r.machine_id,
                event_type=r.event_type,
                description=r.description,
                status=r.status,
                technician=r.technician,
                started_at=r.started_at,
                completed_at=r.completed_at,
                created_at=r.created_at,
            )
            for r in records
        ]

        return MaintenanceListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

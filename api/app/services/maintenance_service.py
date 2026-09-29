"""Maintenance service for querying maintenance records and history."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models.alert import AlertRecord
from api.app.models.machine import MachineRecord
from api.app.models.maintenance import MaintenanceRecord
from api.app.schemas.maintenance import (
    MaintenanceCreateRequest,
    MaintenanceDTO,
    MaintenanceListResponse,
    MaintenanceUpdateRequest,
)

VALID_EVENT_TYPES = {"INSPECTION", "PART_REPLACEMENT", "OVERHAUL", "LUBRICATION", "CALIBRATION"}
VALID_STATUSES = {"SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"}


class MaintenanceService:
    """Service layer for querying and updating maintenance logs and work orders."""

    @staticmethod
    def _to_dto(r: MaintenanceRecord) -> MaintenanceDTO:
        return MaintenanceDTO(
            id=r.id,
            machine_id=r.machine_id,
            alert_id=r.alert_id,
            event_type=r.event_type,
            description=r.description,
            status=r.status,
            technician=r.technician,
            started_at=r.started_at,
            completed_at=r.completed_at,
            created_at=r.created_at,
        )

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
            norm_status = event_status.upper().strip()
            query = query.where(MaintenanceRecord.status == norm_status)
            count_query = count_query.where(MaintenanceRecord.status == norm_status)

        total = db.execute(count_query).scalar_one()

        records = (
            db.execute(
                query.order_by(MaintenanceRecord.created_at.desc()).limit(limit).offset(offset)
            )
            .scalars()
            .all()
        )

        items = [MaintenanceService._to_dto(r) for r in records]

        return MaintenanceListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def list_all_maintenance(
        db: Session,
        machine_id: str | None = None,
        event_status: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> MaintenanceListResponse:
        """Query bounded fleet-wide maintenance events with optional filters."""
        query = select(MaintenanceRecord)
        count_query = select(func.count(MaintenanceRecord.id))

        if machine_id is not None:
            query = query.where(MaintenanceRecord.machine_id == machine_id)
            count_query = count_query.where(MaintenanceRecord.machine_id == machine_id)

        if event_status is not None:
            norm_status = event_status.upper().strip()
            query = query.where(MaintenanceRecord.status == norm_status)
            count_query = count_query.where(MaintenanceRecord.status == norm_status)

        if event_type is not None:
            norm_type = event_type.upper().strip()
            query = query.where(MaintenanceRecord.event_type == norm_type)
            count_query = count_query.where(MaintenanceRecord.event_type == norm_type)

        total = db.execute(count_query).scalar_one()

        records = (
            db.execute(
                query.order_by(MaintenanceRecord.created_at.desc()).limit(limit).offset(offset)
            )
            .scalars()
            .all()
        )

        items = [MaintenanceService._to_dto(r) for r in records]

        return MaintenanceListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def get_maintenance_by_id(db: Session, maintenance_id: int) -> MaintenanceDTO:
        """Retrieve a single maintenance event by ID."""
        record = db.execute(
            select(MaintenanceRecord).where(MaintenanceRecord.id == maintenance_id)
        ).scalar_one_or_none()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Maintenance event '{maintenance_id}' not found.",
            )

        return MaintenanceService._to_dto(record)

    @staticmethod
    def create_maintenance_event(
        db: Session,
        machine_id: str,
        payload: MaintenanceCreateRequest,
        actor: str | None = None,
    ) -> MaintenanceDTO:
        """Create a new maintenance work order with entity and relationship validation."""
        machine_exists = db.execute(
            select(MachineRecord.machine_id).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if machine_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        event_type = payload.event_type.upper().strip()
        if event_type not in VALID_EVENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event_type '{payload.event_type}'. Must be one of {sorted(VALID_EVENT_TYPES)}.",
            )

        status_val = (payload.status or "SCHEDULED").upper().strip()
        if status_val not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{payload.status}'. Must be one of {sorted(VALID_STATUSES)}.",
            )

        if payload.alert_id is not None:
            alert = db.execute(
                select(AlertRecord).where(AlertRecord.id == payload.alert_id)
            ).scalar_one_or_none()

            if alert is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Alert '{payload.alert_id}' not found.",
                )

            if alert.machine_id != machine_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Alert '{payload.alert_id}' belongs to machine '{alert.machine_id}', not '{machine_id}'.",
                )

        record = MaintenanceRecord(
            machine_id=machine_id,
            alert_id=payload.alert_id,
            event_type=event_type,
            description=payload.description,
            status=status_val,
            technician=payload.technician or actor,
            started_at=payload.started_at,
            completed_at=payload.completed_at,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return MaintenanceService._to_dto(record)

    @staticmethod
    def update_maintenance_event(
        db: Session,
        maintenance_id: int,
        payload: MaintenanceUpdateRequest,
        actor: str | None = None,
    ) -> MaintenanceDTO:
        """Update an existing maintenance event / work order status and attributes."""
        record = db.execute(
            select(MaintenanceRecord).where(MaintenanceRecord.id == maintenance_id)
        ).scalar_one_or_none()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Maintenance event '{maintenance_id}' not found.",
            )

        if payload.status is not None:
            norm_status = payload.status.upper().strip()
            if norm_status not in VALID_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status '{payload.status}'. Must be one of {sorted(VALID_STATUSES)}.",
                )
            record.status = norm_status
            if (
                norm_status == "IN_PROGRESS"
                and record.started_at is None
                and payload.started_at is None
            ):
                record.started_at = datetime.now(UTC)
            elif (
                norm_status == "COMPLETED"
                and record.completed_at is None
                and payload.completed_at is None
            ):
                record.completed_at = datetime.now(UTC)

        if payload.description is not None:
            record.description = payload.description

        if payload.technician is not None:
            record.technician = payload.technician

        if payload.started_at is not None:
            record.started_at = payload.started_at

        if payload.completed_at is not None:
            record.completed_at = payload.completed_at

        db.commit()
        db.refresh(record)

        return MaintenanceService._to_dto(record)

"""Twin query service for accessing canonical Digital Twin state and history."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models.machine import MachineRecord
from api.app.models.twin import TwinSnapshotRecord
from api.app.schemas.twin import TwinHistoryResponse, TwinSnapshotDTO, TwinStateDTO
from api.app.twin.service import get_twin_service
from api.app.twin.snapshot import get_latest_snapshot


class TwinQueryService:
    """Service layer for querying Digital Twin state and snapshot history."""

    @staticmethod
    def get_latest_twin(db: Session, machine_id: str) -> TwinStateDTO:
        """Return the canonical real-time Digital Twin state for a machine."""
        # 1. Verify machine exists
        machine_exists = db.execute(
            select(MachineRecord.machine_id).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if machine_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        # 2. Check in-memory real-time state first
        twin_svc = get_twin_service()
        state = twin_svc.get_state(machine_id)
        if state is not None:
            d = state.to_dict()
            return TwinStateDTO(**d)

        # 3. Fall back to latest persisted snapshot
        snap = get_latest_snapshot(db, machine_id)
        if snap is not None:
            payload = dict(snap.snapshot_payload)
            return TwinStateDTO(**payload)

        # 4. Default un-streamed state for newly registered machine
        return TwinStateDTO(
            machine_id=machine_id,
            sync_status="OFFLINE",
            health_state="OFFLINE",
            operating_state="UNKNOWN",
        )

    @staticmethod
    def get_twin_history(
        db: Session,
        machine_id: str,
        limit: int = 50,
        offset: int = 0,
        before: datetime | None = None,
        after: datetime | None = None,
    ) -> TwinHistoryResponse:
        """Query bounded snapshot history for a machine."""
        machine_exists = db.execute(
            select(MachineRecord.machine_id).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if machine_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        query = select(TwinSnapshotRecord).where(TwinSnapshotRecord.machine_id == machine_id)
        count_query = select(func.count(TwinSnapshotRecord.id)).where(
            TwinSnapshotRecord.machine_id == machine_id
        )

        if before is not None:
            query = query.where(TwinSnapshotRecord.ts <= before)
            count_query = count_query.where(TwinSnapshotRecord.ts <= before)

        if after is not None:
            query = query.where(TwinSnapshotRecord.ts >= after)
            count_query = count_query.where(TwinSnapshotRecord.ts >= after)

        total = db.execute(count_query).scalar_one()

        records = (
            db.execute(query.order_by(TwinSnapshotRecord.ts.desc()).limit(limit).offset(offset))
            .scalars()
            .all()
        )

        items = [
            TwinSnapshotDTO(
                id=r.id,
                machine_id=r.machine_id,
                ts=r.ts,
                sync_status=r.sync_status,
                operating_state=r.operating_state,
                health_state=r.health_state,
                health_score=r.health_score,
                risk_band=r.risk_band,
                failure_probability=r.failure_probability,
                anomaly_flag=r.anomaly_flag,
                snapshot_payload=r.snapshot_payload,
                created_at=r.created_at,
            )
            for r in records
        ]

        return TwinHistoryResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

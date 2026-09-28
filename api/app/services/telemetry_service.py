"""Telemetry service for retrieving bounded time-series observations."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models.machine import MachineRecord
from api.app.models.telemetry import TelemetryRecord
from api.app.schemas.telemetry import TelemetryDTO, TelemetryListResponse


class TelemetryService:
    """Service layer for querying telemetry observations."""

    @staticmethod
    def get_telemetry(
        db: Session,
        machine_id: str,
        limit: int = 50,
        offset: int = 0,
        before: datetime | None = None,
        after: datetime | None = None,
        seq_min: int | None = None,
        seq_max: int | None = None,
    ) -> TelemetryListResponse:
        """Query bounded telemetry history for a specific machine."""
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
        query = select(TelemetryRecord).where(TelemetryRecord.machine_id == machine_id)
        count_query = select(func.count(TelemetryRecord.id)).where(
            TelemetryRecord.machine_id == machine_id
        )

        if before is not None:
            query = query.where(TelemetryRecord.ts <= before)
            count_query = count_query.where(TelemetryRecord.ts <= before)

        if after is not None:
            query = query.where(TelemetryRecord.ts >= after)
            count_query = count_query.where(TelemetryRecord.ts >= after)

        if seq_min is not None:
            query = query.where(TelemetryRecord.seq >= seq_min)
            count_query = count_query.where(TelemetryRecord.seq >= seq_min)

        if seq_max is not None:
            query = query.where(TelemetryRecord.seq <= seq_max)
            count_query = count_query.where(TelemetryRecord.seq <= seq_max)

        total = db.execute(count_query).scalar_one()

        records = (
            db.execute(
                query.order_by(TelemetryRecord.ts.desc(), TelemetryRecord.seq.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )

        items = [
            TelemetryDTO(
                id=r.id,
                machine_id=r.machine_id,
                seq=r.seq,
                ts=r.ts,
                provenance=r.provenance,
                fw=r.fw,
                air_temp_c=r.air_temp_c,
                process_temp_c=r.process_temp_c,
                rotational_speed_rpm=r.rotational_speed_rpm,
                torque_nm=r.torque_nm,
                vibration_mm_s=r.vibration_mm_s,
                pressure_bar=r.pressure_bar,
                current_a=r.current_a,
                voltage_v=r.voltage_v,
                tool_wear_min=r.tool_wear_min,
                operating_hours=r.operating_hours,
                quality=r.quality,
                delta_t_c=r.delta_t_c,
                power_va=r.power_va,
                trip=r.trip,
                buffered=r.buffered,
                received_at=r.received_at,
            )
            for r in records
        ]

        return TelemetryListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

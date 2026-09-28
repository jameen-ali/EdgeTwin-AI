"""Machine service for querying fleet assets and detailed statuses."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models.machine import MachineRecord
from api.app.models.prediction import PredictionRecord
from api.app.models.telemetry import TelemetryRecord
from api.app.schemas.machine import MachineDetailResponse, MachineListResponse, MachineSummary
from api.app.twin.service import get_twin_service
from api.app.twin.snapshot import get_latest_snapshot


class MachineService:
    """Business logic for machine asset queries."""

    @staticmethod
    def get_machines(
        db: Session,
        limit: int = 50,
        offset: int = 0,
        machine_status: str | None = None,
    ) -> MachineListResponse:
        """Return a bounded, paginated list of machine summaries with latest twin states."""
        query = select(MachineRecord)
        count_query = select(func.count(MachineRecord.machine_id))

        if machine_status is not None:
            query = query.where(MachineRecord.status == machine_status)
            count_query = count_query.where(MachineRecord.status == machine_status)

        total = db.execute(count_query).scalar_one()

        records = (
            db.execute(query.order_by(MachineRecord.machine_id).limit(limit).offset(offset))
            .scalars()
            .all()
        )

        twin_svc = get_twin_service()
        items: list[MachineSummary] = []

        for m in records:
            # Check in-memory twin state first (O(1))
            twin = twin_svc.get_state(m.machine_id)
            if twin is not None:
                summary = MachineSummary(
                    machine_id=m.machine_id,
                    machine_type=m.machine_type,
                    location=m.location,
                    status=m.status,
                    sync_status=twin.sync_status,
                    health_state=twin.health_state,
                    health_score=twin.health_score,
                    risk_band=twin.risk_band,
                    operating_state=twin.operating_state,
                    last_telemetry_ts=twin.last_telemetry_ts,
                    updated_at=twin.updated_at or m.updated_at,
                )
            else:
                # Fall back to latest persisted snapshot if available
                latest_snap = get_latest_snapshot(db, m.machine_id)
                if latest_snap is not None:
                    summary = MachineSummary(
                        machine_id=m.machine_id,
                        machine_type=m.machine_type,
                        location=m.location,
                        status=m.status,
                        sync_status=latest_snap.sync_status,
                        health_state=latest_snap.health_state,
                        health_score=latest_snap.health_score,
                        risk_band=latest_snap.risk_band,
                        operating_state=latest_snap.operating_state,
                        last_telemetry_ts=latest_snap.ts,
                        updated_at=latest_snap.created_at,
                    )
                else:
                    summary = MachineSummary(
                        machine_id=m.machine_id,
                        machine_type=m.machine_type,
                        location=m.location,
                        status=m.status,
                        sync_status="OFFLINE",
                        health_state="OFFLINE",
                        health_score=None,
                        risk_band=None,
                        operating_state="UNKNOWN",
                        last_telemetry_ts=None,
                        updated_at=m.updated_at,
                    )
            items.append(summary)

        return MachineListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def get_machine(db: Session, machine_id: str) -> MachineDetailResponse:
        """Return machine details along with its latest twin state, telemetry, and prediction."""
        record = db.execute(
            select(MachineRecord).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        # 1. Latest Twin state (in-memory or latest snapshot)
        twin_svc = get_twin_service()
        twin = twin_svc.get_state(machine_id)
        latest_twin_dict: dict[str, Any] | None = None
        if twin is not None:
            latest_twin_dict = twin.to_dict()
        else:
            snap = get_latest_snapshot(db, machine_id)
            if snap is not None:
                latest_twin_dict = snap.snapshot_payload

        # 2. Latest telemetry
        latest_telem = db.execute(
            select(TelemetryRecord)
            .where(TelemetryRecord.machine_id == machine_id)
            .order_by(TelemetryRecord.ts.desc())
            .limit(1)
        ).scalar_one_or_none()

        telem_dict: dict[str, Any] | None = None
        if latest_telem is not None:
            telem_dict = {
                "id": latest_telem.id,
                "seq": latest_telem.seq,
                "ts": latest_telem.ts.isoformat(),
                "provenance": latest_telem.provenance,
                "fw": latest_telem.fw,
                "signals": {
                    "air_temp_c": latest_telem.air_temp_c,
                    "process_temp_c": latest_telem.process_temp_c,
                    "rotational_speed_rpm": latest_telem.rotational_speed_rpm,
                    "torque_nm": latest_telem.torque_nm,
                    "vibration_mm_s": latest_telem.vibration_mm_s,
                    "pressure_bar": latest_telem.pressure_bar,
                    "current_a": latest_telem.current_a,
                    "voltage_v": latest_telem.voltage_v,
                    "tool_wear_min": latest_telem.tool_wear_min,
                    "operating_hours": latest_telem.operating_hours,
                },
                "delta_t_c": latest_telem.delta_t_c,
                "power_va": latest_telem.power_va,
                "trip": latest_telem.trip,
            }

        # 3. Latest prediction
        latest_pred = db.execute(
            select(PredictionRecord)
            .where(PredictionRecord.machine_id == machine_id)
            .order_by(PredictionRecord.ts.desc())
            .limit(1)
        ).scalar_one_or_none()

        pred_dict: dict[str, Any] | None = None
        if latest_pred is not None:
            pred_dict = {
                "id": latest_pred.id,
                "ts": latest_pred.ts.isoformat(),
                "failure_probability": latest_pred.failure_probability,
                "failure_prediction": latest_pred.failure_prediction,
                "risk_band": latest_pred.risk_band,
                "anomaly_score": latest_pred.anomaly_score,
                "anomaly_flag": latest_pred.anomaly_flag,
                "health_score": latest_pred.health_score,
                "health_state": latest_pred.health_state,
                "top_factors": latest_pred.top_factors,
                "model_version": latest_pred.model_version,
            }

        return MachineDetailResponse(
            machine_id=record.machine_id,
            machine_type=record.machine_type,
            location=record.location,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            latest_twin=latest_twin_dict,
            latest_telemetry=telem_dict,
            latest_prediction=pred_dict,
        )

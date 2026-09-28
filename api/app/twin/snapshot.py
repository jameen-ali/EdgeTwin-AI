"""
api/app/twin/snapshot.py — Digital Twin snapshot persistence.

Writes TwinSnapshotRecord rows to the DB and reads the latest snapshot
back for REST queries.

Design decisions:
- Snapshots are written on every LIVE inference result (≈ 1 Hz per machine)
  so the full state is recoverable from the DB.
- STALE and OFFLINE transitions also write a snapshot so state changes
  are fully auditable.
- Reading uses a single `ORDER BY ts DESC LIMIT 1` which is covered by the
  compound index `ix_twin_snapshots_machine_ts_desc` created in migration
  0001_initial_schema.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.models.twin import TwinSnapshotRecord
from api.app.twin.state import TwinState

logger = logging.getLogger(__name__)


def persist_twin_snapshot(db: Session, state: TwinState) -> TwinSnapshotRecord | None:
    """Persist a TwinState to the twin_snapshots table.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    state:
        The current TwinState to persist.

    Returns
    -------
    TwinSnapshotRecord | None
        The persisted record, or None if persistence fails (error is logged,
        not re-raised, so the caller (ingestion pipeline) never crashes).
    """
    try:
        ts = state.last_telemetry_ts or datetime.now(UTC)
        record = TwinSnapshotRecord(
            machine_id=state.machine_id,
            ts=ts,
            sync_status=state.sync_status,
            operating_state=state.operating_state,
            health_state=state.health_state,
            health_score=float(state.health_score) if state.health_score is not None else 0.0,
            risk_band=state.risk_band or "UNKNOWN",
            failure_probability=(
                float(state.failure_probability) if state.failure_probability is not None else 0.0
            ),
            anomaly_flag=bool(state.anomaly_flag) if state.anomaly_flag is not None else False,
            snapshot_payload=state.to_dict(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error(
            "Failed to persist twin snapshot",
            extra={"machine_id": state.machine_id, "error": str(exc)},
        )
        return None


def get_latest_snapshot(db: Session, machine_id: str) -> TwinSnapshotRecord | None:
    """Return the most recent TwinSnapshotRecord for a machine_id."""
    stmt = (
        select(TwinSnapshotRecord)
        .where(TwinSnapshotRecord.machine_id == machine_id)
        .order_by(TwinSnapshotRecord.ts.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_snapshot_history(
    db: Session,
    machine_id: str,
    limit: int = 100,
) -> list[TwinSnapshotRecord]:
    """Return recent snapshot history for a machine (newest first)."""
    stmt = (
        select(TwinSnapshotRecord)
        .where(TwinSnapshotRecord.machine_id == machine_id)
        .order_by(TwinSnapshotRecord.ts.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())

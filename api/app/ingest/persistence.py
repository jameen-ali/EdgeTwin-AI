"""
api/app/ingest/persistence.py — Telemetry database persistence layer.

Provides an idempotent upsert-like insert for telemetry records.  Duplicate
(machine_id, seq) pairs are detected and dropped gracefully; unknown machines
are auto-registered with minimal metadata so the system never silently discards
valid telemetry from a previously-unseen machine_id.

Architecture contract:
- This module has NO MQTT dependency (pure DB + model layer).
- Called by the message handler after successful validation + normalisation.
- Side effects: may INSERT a machine row if the machine is unknown.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.models.machine import MachineRecord
from api.app.models.telemetry import TelemetryRecord

logger = logging.getLogger(__name__)

# Provenance tag used for auto-registered machines
_AUTO_MACHINE_TYPE = "UNKNOWN"
_AUTO_MACHINE_STATUS = "ACTIVE"


def persist_telemetry(
    db: Session,
    fields: dict[str, Any],
) -> tuple[bool, str]:
    """Persist a normalised telemetry record.

    Behaviour
    ---------
    1. Ensures a machine row exists (auto-creates with type UNKNOWN if absent).
    2. Attempts INSERT of the TelemetryRecord.
    3. If UNIQUE(machine_id, seq) is violated → graceful duplicate drop.
    4. All other exceptions → rollback + re-raise.

    Parameters
    ----------
    db:
        An active SQLAlchemy Session (caller provides, caller closes).
    fields:
        Normalised field dict from :func:`~.normalizer.normalize_telemetry`.

    Returns
    -------
    (True, "persisted")  on new insertion.
    (False, "duplicate") on duplicate (machine_id, seq).
    """
    machine_id: str = fields["machine_id"]
    seq: int = fields["seq"]

    # 1. Ensure machine exists (idempotent)
    _ensure_machine(db, machine_id)

    # 2. Insert telemetry
    record = TelemetryRecord(**fields)
    db.add(record)
    try:
        db.commit()
        logger.info(
            "Telemetry persisted",
            extra={"machine_id": machine_id, "seq": seq, "event": "telemetry_persisted"},
        )
        return True, "persisted"
    except IntegrityError as exc:
        db.rollback()
        err_str = str(exc.orig) if exc.orig else str(exc)
        # The UNIQUE constraint name is 'uq_telemetry_machine_seq' on both
        # PostgreSQL and SQLite.
        if "uq_telemetry_machine_seq" in err_str or "UNIQUE constraint" in err_str:
            logger.warning(
                "Duplicate telemetry dropped",
                extra={"machine_id": machine_id, "seq": seq, "event": "duplicate_telemetry"},
            )
            return False, "duplicate"
        # Unexpected integrity error — re-raise so caller can log + alert
        raise


def _ensure_machine(db: Session, machine_id: str) -> None:
    """Auto-register machine_id if not already present.

    Architecture decision: auto-registration is allowed because:
    - The telemetry contract already validated the machine_id format.
    - Architecture.md states telemetry from any source that meets the contract
      should be ingested (FR-02).
    - Silently discarding valid telemetry from an unlisted machine is worse than
      auto-registering with type=UNKNOWN so an operator can later add metadata.
    - Memory.md records this as an explicit decision (added in S11).
    """
    stmt = select(MachineRecord).where(MachineRecord.machine_id == machine_id)
    result = db.execute(stmt).scalar_one_or_none()
    if result is not None:
        return

    logger.info(
        "Auto-registering unknown machine",
        extra={"machine_id": machine_id, "event": "machine_auto_registered"},
    )
    db.add(
        MachineRecord(
            machine_id=machine_id,
            machine_type=_AUTO_MACHINE_TYPE,
            status=_AUTO_MACHINE_STATUS,
        )
    )
    try:
        db.flush()  # flush without commit so it's part of the outer transaction
    except IntegrityError:
        db.rollback()
        # Race condition: another concurrent insert won — that's fine.
        logger.debug(
            "Machine already registered by concurrent insert",
            extra={"machine_id": machine_id},
        )

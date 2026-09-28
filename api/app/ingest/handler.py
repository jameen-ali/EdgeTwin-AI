"""
api/app/ingest/handler.py — MQTT message handler (decode → validate → normalise → persist).

This module is the integration seam between the MQTT callback layer and the
pure business-logic / persistence layers.  It must NEVER crash: all exceptions
are caught, logged, and dropped so the MQTT client loop remains healthy.

Architecture contract:
- No MQTT library imported here (dependency-free from paho side).
- Pure function `handle_message()` is unit-testable with a mock Session.
- Business logic (decode, validate, normalise, persist) is delegated to
  dedicated modules.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from api.app.ingest.normalizer import normalize_telemetry
from api.app.ingest.persistence import persist_telemetry
from simulation.contract import TelemetryValidator

logger = logging.getLogger(__name__)

# Compiled topic regex — same pattern as used in virtual_edge and contract
_TOPIC_REGEX = re.compile(r"^edgetwin/v[0-9]+/([A-Z]{3}-[0-9]{4})/telemetry$")
_STATUS_TOPIC_REGEX = re.compile(r"^edgetwin/v[0-9]+/([A-Z]{3}-[0-9]{4})/status$")

# Singleton validator (thread-safe: read-only after construction)
_validator: TelemetryValidator | None = None


def get_validator() -> TelemetryValidator:
    """Return a lazily-initialised singleton TelemetryValidator."""
    global _validator
    if _validator is None:
        _validator = TelemetryValidator()
    return _validator


def extract_machine_id_from_topic(topic: str) -> str | None:
    """Return the machine_id from an MQTT topic string, or None."""
    m = _TOPIC_REGEX.match(topic)
    return m.group(1) if m else None


def handle_message(
    topic: str,
    raw_payload: bytes,
    db: Session,
) -> dict[str, Any]:
    """Process one MQTT message end-to-end.

    Parameters
    ----------
    topic:
        MQTT topic string.
    raw_payload:
        Raw bytes from the MQTT message.
    db:
        Active SQLAlchemy Session (caller is responsible for lifecycle).

    Returns
    -------
    dict with keys:
        - "outcome": "persisted" | "duplicate" | "rejected" | "status_updated"
        - "reason":  human-readable string
        - "machine_id": str | None
        - "seq": int | None
    """
    machine_id: str | None = None
    seq: int | None = None

    try:
        # Step 0: Check for canonical status / LWT topic
        status_match = _STATUS_TOPIC_REGEX.match(topic)
        if status_match is not None:
            machine_id = status_match.group(1)
            try:
                text = raw_payload.decode("utf-8")
                payload_dict = json.loads(text)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Dropping status message: invalid JSON",
                    extra={"machine_id": machine_id, "error": str(exc), "event": "invalid_json"},
                )
                return _rejected("invalid_json", str(exc), machine_id, None)

            status_str = payload_dict.get("status") if isinstance(payload_dict, dict) else None
            if not isinstance(status_str, str):
                return _rejected(
                    "invalid_status_payload", "Missing or non-string status", machine_id, None
                )

            status_upper = status_str.upper()
            if status_upper == "OFFLINE":
                try:
                    from api.app.twin.service import get_twin_service
                    from api.app.twin.snapshot import persist_twin_snapshot

                    twin_svc = get_twin_service()
                    new_state = twin_svc.mark_offline(machine_id)
                    persist_twin_snapshot(db, new_state)
                    logger.info(
                        "Machine marked OFFLINE via MQTT LWT/status",
                        extra={"machine_id": machine_id, "event": "machine_marked_offline"},
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Failed to update twin for OFFLINE status",
                        extra={
                            "machine_id": machine_id,
                            "error": str(exc),
                            "event": "status_twin_failed",
                        },
                    )
            elif status_upper == "ONLINE":
                logger.info(
                    "Machine reported ONLINE via MQTT status",
                    extra={"machine_id": machine_id, "event": "machine_reported_online"},
                )

            return {
                "outcome": "status_updated",
                "reason": f"Machine {machine_id} status updated to {status_upper}",
                "machine_id": machine_id,
                "seq": None,
            }

        # Step 1: Validate topic shape
        machine_id = extract_machine_id_from_topic(topic)
        if machine_id is None:
            logger.warning(
                "Dropping message: topic does not match canonical pattern",
                extra={"topic": topic, "event": "invalid_topic"},
            )
            return _rejected("invalid_topic", topic, machine_id, seq)

        logger.debug(
            "MQTT message received",
            extra={"machine_id": machine_id, "topic": topic, "event": "message_received"},
        )

        # Step 2: Decode UTF-8 JSON
        try:
            text = raw_payload.decode("utf-8")
            payload_dict: dict[str, Any] = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning(
                "Dropping message: invalid JSON",
                extra={"machine_id": machine_id, "error": str(exc), "event": "invalid_json"},
            )
            return _rejected("invalid_json", str(exc), machine_id, seq)

        # Step 3: Extract seq for logging if available
        seq = payload_dict.get("seq")

        # Step 4: Validate against telemetry contract (schema + ranges)
        validator = get_validator()
        result = validator.validate(payload_dict, topic=topic)
        if not result.valid:
            logger.warning(
                "Dropping message: validation failed",
                extra={
                    "machine_id": machine_id,
                    "seq": seq,
                    "errors": result.errors[:5],  # cap to avoid log flooding
                    "event": "validation_failed",
                },
            )
            return _rejected("validation_failed", "; ".join(result.errors[:3]), machine_id, seq)

        # Validate that topic machine_id matches payload machine_id (security check)
        payload_mid = payload_dict.get("machine_id")
        if payload_mid != machine_id:
            logger.warning(
                "Dropping message: topic/payload machine_id mismatch",
                extra={
                    "topic_machine_id": machine_id,
                    "payload_machine_id": payload_mid,
                    "event": "machine_id_mismatch",
                },
            )
            return _rejected(
                "machine_id_mismatch", f"{payload_mid} != {machine_id}", machine_id, seq
            )

        # Step 5: Normalise payload into DB field dict
        fields = normalize_telemetry(payload_dict)

        # Step 6: Persist (idempotent)
        persisted, reason = persist_telemetry(db, fields)

        if persisted:
            # Step 7: Run ML inference and health engine (error-isolated)
            try:
                from sqlalchemy import select

                from api.app.inference import get_inference_service
                from api.app.models.telemetry import TelemetryRecord

                # Retrieve the persisted telemetry record ID for foreign key lineage
                stmt = (
                    select(TelemetryRecord.id)
                    .where(
                        TelemetryRecord.machine_id == machine_id,
                        TelemetryRecord.seq == seq,
                    )
                    .limit(1)
                )
                telem_id = db.execute(stmt).scalar_one_or_none()

                inference_svc = get_inference_service()
                inf_result, _pred_rec, _alert_rec = inference_svc.process_and_persist(
                    db=db,
                    payload=payload_dict,
                    telemetry_id=telem_id,
                )
            except Exception as inf_exc:  # noqa: BLE001
                # Inference failure must never crash or drop persisted telemetry
                logger.error(
                    "Inference processing failed for persisted telemetry",
                    extra={
                        "machine_id": machine_id,
                        "seq": seq,
                        "error": str(inf_exc),
                        "event": "inference_failed",
                    },
                )
                inf_result = None

            # Step 8: Update Digital Twin state and persist snapshot (error-isolated)
            if inf_result is not None:
                try:
                    from api.app.twin.service import get_twin_service
                    from api.app.twin.snapshot import persist_twin_snapshot

                    twin_svc = get_twin_service()
                    new_state = twin_svc.update_from_inference(
                        payload=payload_dict,
                        inference_result=inf_result,
                    )
                    persist_twin_snapshot(db, new_state)
                    logger.debug(
                        "Twin state updated",
                        extra={
                            "machine_id": machine_id,
                            "sync_status": new_state.sync_status,
                            "health_state": new_state.health_state,
                            "event": "twin_updated",
                        },
                    )
                except Exception as twin_exc:  # noqa: BLE001
                    logger.error(
                        "Twin update failed for persisted telemetry",
                        extra={
                            "machine_id": machine_id,
                            "seq": seq,
                            "error": str(twin_exc),
                            "event": "twin_update_failed",
                        },
                    )

            return {
                "outcome": "persisted",
                "reason": reason,
                "machine_id": machine_id,
                "seq": seq,
            }
        else:
            logger.info(
                "Duplicate telemetry dropped",
                extra={"machine_id": machine_id, "seq": seq, "event": "duplicate_telemetry"},
            )
            return {
                "outcome": "duplicate",
                "reason": reason,
                "machine_id": machine_id,
                "seq": seq,
            }

    except Exception as exc:
        # Catch-all: the MQTT loop must never crash because of one bad message
        logger.exception(
            "Unexpected error processing MQTT message",
            extra={
                "topic": topic,
                "machine_id": machine_id,
                "seq": seq,
                "error": str(exc),
                "event": "ingest_error",
            },
        )
        return _rejected("unexpected_error", str(exc), machine_id, seq)


def _rejected(
    reason_code: str,
    detail: str,
    machine_id: str | None,
    seq: int | None,
) -> dict[str, Any]:
    """Construct a standardised rejection result dict."""
    return {
        "outcome": "rejected",
        "reason": f"{reason_code}: {detail}",
        "machine_id": machine_id,
        "seq": seq,
    }

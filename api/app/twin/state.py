"""
api/app/twin/state.py — Immutable Digital Twin state dataclass.

TwinState is the single data structure that travels from the TwinService
to the WebSocket broadcaster and the DB snapshot writer.  It MUST be
JSON-serialisable so it can be sent on the wire and stored in the
snapshot_payload JSON column.

Sync FSM (from architecture.md §9):
    OFFLINE  ──► LIVE    (first valid telemetry)
    LIVE     ──► STALE   (no message for > STALE_SECONDS)
    STALE    ──► LIVE    (telemetry resumes)
    STALE    ──► OFFLINE (STALE_TO_OFFLINE_SECONDS elapsed or LWT received)
    LIVE     ──► OFFLINE (LWT received)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Sync status constants
SYNC_LIVE = "LIVE"
SYNC_STALE = "STALE"
SYNC_OFFLINE = "OFFLINE"

# Timing constants (seconds) — tuned for 1 Hz nominal publishing rate
STALE_SECONDS: float = 5.0  # 3× nominal interval (architecture.md §9 "3x interval")
STALE_TO_OFFLINE_SECONDS: float = 30.0  # 30 s of no message after going STALE → OFFLINE


@dataclass(frozen=True)
class TwinState:
    """Immutable snapshot of a machine's Digital Twin at a single instant.

    Fields follow architecture.md §9 and the twin_snapshots DB schema:
    - sync_status:     LIVE | STALE | OFFLINE
    - operating_state: RUNNING | STOPPED | STARTING | DEGRADING | TRIPPED (from edge telemetry)
    - health_state:    HEALTHY | WARNING | CRITICAL | MAINTENANCE_REQUIRED | OFFLINE
    - health_score:    float [0, 100] or None
    - risk_band:       LOW | MEDIUM | HIGH | CRITICAL | None
    - failure_probability: float [0, 1] or None
    - anomaly_flag:    bool or None
    - last_telemetry_ts: datetime of most recent telemetry (for staleness detection)
    - last_seq:        last sequence number seen (or None)
    - signals:         raw sensor readings (may be partial / None values)
    - quality:         per-sensor quality flags
    - edge:            edge diagnostics (delta_t_c, power_va, trip, buffered)
    - top_factors:     top SHAP attributions
    - recommendation:  structured recommendation dict
    - model_version:   string tag of the champion model version used
    - provenance:      SIMULATED | REPLAY | REAL
    - updated_at:      wall-clock time of this state object creation
    """

    machine_id: str
    sync_status: str  # LIVE | STALE | OFFLINE

    # Health Layer output
    health_state: str = "OFFLINE"
    health_score: float | None = None
    risk_band: str | None = None
    failure_probability: float | None = None
    anomaly_flag: bool | None = None
    anomaly_score: float | None = None

    # Operating state from edge FSM
    operating_state: str = "UNKNOWN"

    # Temporal tracking
    last_telemetry_ts: datetime | None = None
    last_seq: int | None = None
    updated_at: datetime | None = None

    # Raw telemetry fields (latest)
    signals: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, str] = field(default_factory=dict)
    edge: dict[str, Any] = field(default_factory=dict)

    # ML outputs
    top_factors: list[dict[str, Any]] | None = None
    recommendation: dict[str, Any] | None = None
    model_version: str = "unknown"

    # Metadata
    provenance: str = "SIMULATED"
    fw: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serialisable dict for wire and DB persistence."""
        return {
            "machine_id": self.machine_id,
            "sync_status": self.sync_status,
            "health_state": self.health_state,
            "health_score": self.health_score,
            "risk_band": self.risk_band,
            "failure_probability": self.failure_probability,
            "anomaly_flag": self.anomaly_flag,
            "anomaly_score": self.anomaly_score,
            "operating_state": self.operating_state,
            "last_telemetry_ts": (
                self.last_telemetry_ts.isoformat() if self.last_telemetry_ts else None
            ),
            "last_seq": self.last_seq,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "signals": self.signals,
            "quality": self.quality,
            "edge": self.edge,
            "top_factors": self.top_factors,
            "recommendation": self.recommendation,
            "model_version": self.model_version,
            "provenance": self.provenance,
            "fw": self.fw,
        }

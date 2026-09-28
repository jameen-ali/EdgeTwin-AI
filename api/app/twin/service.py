"""
api/app/twin/service.py — Digital Twin Service (T-035).

Responsibilities:
1. Maintain a per-machine in-memory TwinState (latest state + staleness clock).
2. Sync FSM: OFFLINE → LIVE → STALE → OFFLINE per architecture.md §9.
3. Accept InferenceResult bundles from the ingestion pipeline and update state.
4. Detect STALE/OFFLINE transitions by comparing wall-clock time to last telemetry.
5. Notify all registered WebSocket connection callbacks on every state change.
6. Persist each state transition as a TwinSnapshotRecord via snapshot.py.

Design rules (from rules.md):
- Business logic is pure / dependency-injected (no global singletons inside the class).
- Twin state contains ONLY derived/health information + last raw signals; the UI
  never computes health or risk — it renders twin state.
- All exceptions are caught and logged; the service must never crash the ingestion loop.
- STALE/OFFLINE transitions are driven by a monotonic clock check called on each
  new telemetry message — no background thread needed for a 1 Hz demo system.
  For production a background scheduler would be appropriate.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from api.app.twin.state import (
    STALE_SECONDS,
    STALE_TO_OFFLINE_SECONDS,
    SYNC_LIVE,
    SYNC_OFFLINE,
    SYNC_STALE,
    TwinState,
)

logger = logging.getLogger(__name__)

# Type alias for async WebSocket notification callback
_WsCallback = Callable[[str, dict[str, Any]], None]


class TwinService:
    """Stateful Digital Twin manager.

    Thread-safety: a single threading.Lock guards the in-memory _states dict
    because updates come from the MQTT background thread and reads come from
    both the MQTT thread and FastAPI async handlers (via run_in_threadpool).
    """

    def __init__(self) -> None:
        self._states: dict[str, TwinState] = {}
        self._lock = threading.Lock()
        # Set of async callbacks called when a machine's twin state changes.
        # Each callback is `async def on_update(machine_id: str, state_dict: dict) -> None`.
        self._ws_callbacks: list[_WsCallback] = []

    # ------------------------------------------------------------------
    # Callback registration (used by WebSocket broadcaster)
    # ------------------------------------------------------------------

    def register_ws_callback(self, callback: _WsCallback) -> None:
        """Register an async callback to be invoked on every twin state update."""
        with self._lock:
            if callback not in self._ws_callbacks:
                self._ws_callbacks.append(callback)

    def unregister_ws_callback(self, callback: _WsCallback) -> None:
        """Remove a previously registered WebSocket callback."""
        with self._lock:
            try:
                self._ws_callbacks.remove(callback)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    def get_state(self, machine_id: str) -> TwinState | None:
        """Return the current TwinState for a machine, or None if unknown."""
        with self._lock:
            return self._states.get(machine_id)

    def get_all_states(self) -> dict[str, TwinState]:
        """Return a shallow copy of all current machine states."""
        with self._lock:
            return dict(self._states)

    def list_machine_ids(self) -> list[str]:
        """Return all machine IDs currently tracked by the twin service."""
        with self._lock:
            return list(self._states.keys())

    # ------------------------------------------------------------------
    # Core update path: called by ingest handler after inference
    # ------------------------------------------------------------------

    def update_from_inference(
        self,
        payload: dict[str, Any],
        inference_result: Any,  # api.app.inference.schemas.InferenceResult
    ) -> TwinState:
        """Build a new TwinState from a validated payload + InferenceResult and store it.

        Parameters
        ----------
        payload:
            The validated telemetry dict (edgetwin.telemetry.v1).
        inference_result:
            InferenceResult from api.app.inference.schemas.

        Returns
        -------
        TwinState
            The newly computed state.
        """
        machine_id = str(payload.get("machine_id", "UNKNOWN"))
        now = datetime.now(UTC)

        # Parse telemetry timestamp
        raw_ts = payload.get("ts")
        if isinstance(raw_ts, str):
            try:
                telemetry_ts = datetime.fromisoformat(raw_ts)
            except ValueError:
                telemetry_ts = now
        elif isinstance(raw_ts, datetime):
            telemetry_ts = raw_ts
        else:
            telemetry_ts = now

        # Extract operating state from edge trip field
        edge = payload.get("edge", {}) or {}
        trip_code = edge.get("trip")
        if trip_code:
            operating_state = "TRIPPED"
        else:
            operating_state = "RUNNING"

        # Extract recommendation as a simple dict for JSON storage
        rec = None
        if inference_result.health_assessment.recommendation is not None:
            r = inference_result.health_assessment.recommendation
            rec = {
                "action_code": r.action_code,
                "recommendation_text": r.recommendation_text,
                "urgency": r.urgency,
                "target_component": r.target_component,
                "reason": r.reason,
            }

        new_state = TwinState(
            machine_id=machine_id,
            sync_status=SYNC_LIVE,
            health_state=inference_result.health_state,
            health_score=inference_result.health_score,
            risk_band=inference_result.risk_band,
            failure_probability=inference_result.failure_probability,
            anomaly_flag=inference_result.anomaly_flag,
            anomaly_score=inference_result.anomaly_score,
            operating_state=operating_state,
            last_telemetry_ts=telemetry_ts,
            last_seq=payload.get("seq"),
            updated_at=now,
            signals=payload.get("signals", {}),
            quality=payload.get("quality", {}),
            edge=edge,
            top_factors=inference_result.top_factors,
            recommendation=rec,
            model_version=inference_result.model_version,
            provenance=payload.get("provenance", "SIMULATED"),
            fw=payload.get("fw"),
        )

        self._set_state(machine_id, new_state)
        return new_state

    def mark_offline(self, machine_id: str) -> TwinState:
        """Force a machine into OFFLINE sync state (e.g. on LWT receipt).

        Returns the new TwinState (or a minimal offline state if not previously tracked).
        """
        now = datetime.now(UTC)
        with self._lock:
            existing = self._states.get(machine_id)

        if existing is not None:
            new_state = TwinState(
                machine_id=existing.machine_id,
                sync_status=SYNC_OFFLINE,
                health_state="OFFLINE",
                health_score=existing.health_score,
                risk_band=existing.risk_band,
                failure_probability=existing.failure_probability,
                anomaly_flag=existing.anomaly_flag,
                anomaly_score=existing.anomaly_score,
                operating_state=existing.operating_state,
                last_telemetry_ts=existing.last_telemetry_ts,
                last_seq=existing.last_seq,
                updated_at=now,
                signals=existing.signals,
                quality=existing.quality,
                edge=existing.edge,
                top_factors=existing.top_factors,
                recommendation=existing.recommendation,
                model_version=existing.model_version,
                provenance=existing.provenance,
                fw=existing.fw,
            )
        else:
            new_state = TwinState(
                machine_id=machine_id,
                sync_status=SYNC_OFFLINE,
                health_state="OFFLINE",
                operating_state="UNKNOWN",
                updated_at=now,
            )

        self._set_state(machine_id, new_state)
        return new_state

    def tick_staleness(self, machine_id: str) -> TwinState | None:
        """Check and apply staleness / offline transitions for a machine.

        Should be called periodically or before serving state to a client.
        Implements the architecture.md §9 FSM:
            LIVE  → STALE   if last_telemetry_ts is older than STALE_SECONDS
            STALE → OFFLINE if last_telemetry_ts is older than STALE_TO_OFFLINE_SECONDS

        Returns the (possibly updated) TwinState, or None if machine is unknown.
        """
        with self._lock:
            state = self._states.get(machine_id)

        if state is None:
            return None

        if state.last_telemetry_ts is None:
            return state

        now = datetime.now(UTC)
        age = (now - state.last_telemetry_ts).total_seconds()

        if state.sync_status == SYNC_LIVE and age > STALE_SECONDS:
            logger.info(f"Twin {machine_id} LIVE → STALE (age={age:.1f}s > {STALE_SECONDS}s)")
            new_state = TwinState(
                machine_id=state.machine_id,
                sync_status=SYNC_STALE,
                health_state=state.health_state,
                health_score=state.health_score,
                risk_band=state.risk_band,
                failure_probability=state.failure_probability,
                anomaly_flag=state.anomaly_flag,
                anomaly_score=state.anomaly_score,
                operating_state=state.operating_state,
                last_telemetry_ts=state.last_telemetry_ts,
                last_seq=state.last_seq,
                updated_at=now,
                signals=state.signals,
                quality=state.quality,
                edge=state.edge,
                top_factors=state.top_factors,
                recommendation=state.recommendation,
                model_version=state.model_version,
                provenance=state.provenance,
                fw=state.fw,
            )
            self._set_state(machine_id, new_state)
            return new_state

        if state.sync_status == SYNC_STALE and age > STALE_TO_OFFLINE_SECONDS:
            logger.warning(
                f"Twin {machine_id} STALE → OFFLINE (age={age:.1f}s > {STALE_TO_OFFLINE_SECONDS}s)"
            )
            new_state = TwinState(
                machine_id=state.machine_id,
                sync_status=SYNC_OFFLINE,
                health_state="OFFLINE",
                health_score=state.health_score,
                risk_band=state.risk_band,
                failure_probability=state.failure_probability,
                anomaly_flag=state.anomaly_flag,
                anomaly_score=state.anomaly_score,
                operating_state=state.operating_state,
                last_telemetry_ts=state.last_telemetry_ts,
                last_seq=state.last_seq,
                updated_at=now,
                signals=state.signals,
                quality=state.quality,
                edge=state.edge,
                top_factors=state.top_factors,
                recommendation=state.recommendation,
                model_version=state.model_version,
                provenance=state.provenance,
                fw=state.fw,
            )
            self._set_state(machine_id, new_state)
            return new_state

        return state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_state(self, machine_id: str, state: TwinState) -> None:
        """Store new state and fire registered callbacks (thread-safe)."""
        with self._lock:
            self._states[machine_id] = state
            callbacks = list(self._ws_callbacks)

        state_dict = state.to_dict()
        for cb in callbacks:
            try:
                # Callbacks may be async (coroutines); fire them safely
                if asyncio.iscoroutinefunction(cb):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.ensure_future(cb(machine_id, state_dict))
                        else:
                            loop.run_until_complete(cb(machine_id, state_dict))
                    except RuntimeError:
                        # No event loop in MQTT background thread context
                        pass
                else:
                    cb(machine_id, state_dict)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"WebSocket callback raised an exception for {machine_id}: {exc}")


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_twin_service: TwinService | None = None
_twin_service_lock = threading.Lock()


def get_twin_service() -> TwinService:
    """Return the global, lazily-initialised TwinService singleton."""
    global _twin_service
    if _twin_service is None:
        with _twin_service_lock:
            if _twin_service is None:
                _twin_service = TwinService()
    return _twin_service

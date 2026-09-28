"""
tests/api/test_twin.py — Unit tests for T-035 Digital Twin Service and T-037 WebSocket stream.

Tests cover:
- TwinState dataclass creation, to_dict round-trip
- TwinService: LIVE update, STALE transition, OFFLINE transition, LWT mark_offline
- TwinService: callback registration/deregistration, multi-machine isolation
- TwinService: sync FSM correctness (timing thresholds)
- Snapshot persistence: persist_twin_snapshot writes correct row
- ConnectionManager: connect/disconnect, broadcast filters, dead-connection cleanup
- WebSocket endpoint: /ws/live snapshot, ping/pong, /ws/live/{machine_id}
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# TwinState tests
# ---------------------------------------------------------------------------
from api.app.twin.state import (
    STALE_SECONDS,
    STALE_TO_OFFLINE_SECONDS,
    SYNC_LIVE,
    SYNC_OFFLINE,
    SYNC_STALE,
    TwinState,
)


class TestTwinState:
    def _make_state(self, **kwargs: Any) -> TwinState:
        defaults = {
            "machine_id": "MOT-1001",
            "sync_status": SYNC_LIVE,
            "health_state": "HEALTHY",
            "health_score": 85.0,
            "risk_band": "LOW",
            "failure_probability": 0.03,
            "anomaly_flag": False,
            "operating_state": "RUNNING",
            "last_telemetry_ts": datetime.now(UTC),
            "last_seq": 42,
            "updated_at": datetime.now(UTC),
            "signals": {"air_temp_c": 25.0},
            "quality": {"air_temp_c": "OK"},
            "edge": {"trip": None, "buffered": 0},
            "top_factors": [{"feature": "Tool_Wear_Min", "shap_value": 0.12}],
            "recommendation": {"action_code": "ROUTINE_INSPECTION"},
            "model_version": "edgetwin-risk:v2-champion",
            "provenance": "SIMULATED",
        }
        defaults.update(kwargs)
        return TwinState(**defaults)

    def test_creation_defaults(self) -> None:
        state = TwinState(machine_id="MOT-1001", sync_status=SYNC_OFFLINE)
        assert state.machine_id == "MOT-1001"
        assert state.sync_status == SYNC_OFFLINE
        assert state.health_state == "OFFLINE"
        assert state.health_score is None
        assert state.signals == {}

    def test_frozen_immutability(self) -> None:
        state = TwinState(machine_id="MOT-1001", sync_status=SYNC_LIVE)
        with pytest.raises((AttributeError, TypeError)):
            state.sync_status = SYNC_OFFLINE  # type: ignore[misc]

    def test_to_dict_all_keys(self) -> None:
        state = self._make_state()
        d = state.to_dict()
        required_keys = {
            "machine_id",
            "sync_status",
            "health_state",
            "health_score",
            "risk_band",
            "failure_probability",
            "anomaly_flag",
            "operating_state",
            "last_telemetry_ts",
            "last_seq",
            "updated_at",
            "signals",
            "quality",
            "edge",
            "top_factors",
            "recommendation",
            "model_version",
            "provenance",
            "fw",
        }
        assert required_keys.issubset(set(d.keys()))

    def test_to_dict_json_serialisable(self) -> None:
        state = self._make_state()
        d = state.to_dict()
        # Must not raise
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        assert decoded["machine_id"] == "MOT-1001"

    def test_to_dict_ts_as_isoformat(self) -> None:
        ts = datetime(2026, 9, 28, 10, 0, 0, tzinfo=UTC)
        state = self._make_state(last_telemetry_ts=ts)
        d = state.to_dict()
        assert "2026-09-28" in d["last_telemetry_ts"]

    def test_to_dict_none_ts(self) -> None:
        state = TwinState(machine_id="MOT-1001", sync_status=SYNC_OFFLINE)
        d = state.to_dict()
        assert d["last_telemetry_ts"] is None
        assert d["updated_at"] is None

    def test_sync_constants(self) -> None:
        assert SYNC_LIVE == "LIVE"
        assert SYNC_STALE == "STALE"
        assert SYNC_OFFLINE == "OFFLINE"
        # Stale threshold must be positive and less than offline threshold
        assert 0 < STALE_SECONDS < STALE_TO_OFFLINE_SECONDS


# ---------------------------------------------------------------------------
# TwinService tests
# ---------------------------------------------------------------------------

from api.app.twin.service import TwinService


def _make_inference_result(
    machine_id: str = "MOT-1001",
    health_state: str = "HEALTHY",
    health_score: float = 88.0,
    risk_band: str = "LOW",
    failure_probability: float = 0.04,
    anomaly_flag: bool = False,
    anomaly_score: float = 0.10,
    top_factors: list | None = None,
    model_version: str = "edgetwin-risk:v2-champion",
) -> MagicMock:
    rec = MagicMock()
    rec.machine_id = machine_id
    rec.health_state = health_state
    rec.health_score = health_score
    rec.risk_band = risk_band
    rec.failure_probability = failure_probability
    rec.anomaly_flag = anomaly_flag
    rec.anomaly_score = anomaly_score
    rec.top_factors = top_factors or []
    rec.model_version = model_version
    rec.health_assessment.recommendation = None
    return rec


def _make_payload(machine_id: str = "MOT-1001", seq: int = 1) -> dict[str, Any]:
    return {
        "machine_id": machine_id,
        "seq": seq,
        "ts": datetime.now(UTC).isoformat(),
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {"air_temp_c": 25.0, "tool_wear_min": 120.0},
        "quality": {"air_temp_c": "OK"},
        "edge": {"trip": None, "buffered": 0},
    }


class TestTwinService:
    def setup_method(self) -> None:
        self.svc = TwinService()

    # Basic state management
    def test_get_state_unknown_returns_none(self) -> None:
        assert self.svc.get_state("MOT-9999") is None

    def test_update_from_inference_creates_live_state(self) -> None:
        payload = _make_payload()
        result = _make_inference_result()
        state = self.svc.update_from_inference(payload, result)
        assert state.machine_id == "MOT-1001"
        assert state.sync_status == SYNC_LIVE
        assert state.health_state == "HEALTHY"
        assert state.health_score == 88.0

    def test_update_from_inference_stored_in_service(self) -> None:
        payload = _make_payload()
        result = _make_inference_result()
        self.svc.update_from_inference(payload, result)
        stored = self.svc.get_state("MOT-1001")
        assert stored is not None
        assert stored.sync_status == SYNC_LIVE

    def test_multiple_machines_isolated(self) -> None:
        self.svc.update_from_inference(
            _make_payload("MOT-1001"), _make_inference_result("MOT-1001")
        )
        self.svc.update_from_inference(
            _make_payload("PMP-2001"), _make_inference_result("PMP-2001", health_state="WARNING")
        )
        assert self.svc.get_state("MOT-1001").health_state == "HEALTHY"
        assert self.svc.get_state("PMP-2001").health_state == "WARNING"

    def test_list_machine_ids(self) -> None:
        self.svc.update_from_inference(_make_payload("MOT-1001"), _make_inference_result())
        self.svc.update_from_inference(
            _make_payload("PMP-2001"), _make_inference_result("PMP-2001")
        )
        ids = self.svc.list_machine_ids()
        assert "MOT-1001" in ids
        assert "PMP-2001" in ids

    def test_get_all_states_returns_copy(self) -> None:
        self.svc.update_from_inference(_make_payload(), _make_inference_result())
        all_states = self.svc.get_all_states()
        assert isinstance(all_states, dict)
        assert "MOT-1001" in all_states

    # Operating state
    def test_trip_sets_operating_state_tripped(self) -> None:
        payload = _make_payload()
        payload["edge"]["trip"] = "TRIP_OVERLOAD"
        result = _make_inference_result()
        state = self.svc.update_from_inference(payload, result)
        assert state.operating_state == "TRIPPED"

    def test_no_trip_sets_operating_state_running(self) -> None:
        payload = _make_payload()
        payload["edge"]["trip"] = None
        result = _make_inference_result()
        state = self.svc.update_from_inference(payload, result)
        assert state.operating_state == "RUNNING"

    # mark_offline
    def test_mark_offline_unknown_machine(self) -> None:
        state = self.svc.mark_offline("MOT-9999")
        assert state.machine_id == "MOT-9999"
        assert state.sync_status == SYNC_OFFLINE
        assert state.health_state == "OFFLINE"

    def test_mark_offline_known_machine(self) -> None:
        self.svc.update_from_inference(_make_payload(), _make_inference_result())
        state = self.svc.mark_offline("MOT-1001")
        assert state.sync_status == SYNC_OFFLINE
        assert state.health_state == "OFFLINE"
        # Preserves prior ML outputs
        assert state.health_score == 88.0

    # Staleness FSM
    def test_tick_unknown_machine_returns_none(self) -> None:
        assert self.svc.tick_staleness("UNKNOWN-9999") is None

    def test_tick_live_to_stale_transition(self) -> None:
        payload = _make_payload()
        result = _make_inference_result()
        self.svc.update_from_inference(payload, result)

        # Wind back the last_telemetry_ts to simulate staleness
        old_state = self.svc.get_state("MOT-1001")
        stale_ts = datetime.now(UTC) - timedelta(seconds=STALE_SECONDS + 1)
        # Inject stale state by direct _states manipulation
        from api.app.twin.state import TwinState as _TS

        stale_state = _TS(
            machine_id=old_state.machine_id,
            sync_status=SYNC_LIVE,
            last_telemetry_ts=stale_ts,
            health_state=old_state.health_state,
            health_score=old_state.health_score,
        )
        with self.svc._lock:
            self.svc._states["MOT-1001"] = stale_state

        new_state = self.svc.tick_staleness("MOT-1001")
        assert new_state is not None
        assert new_state.sync_status == SYNC_STALE

    def test_tick_stale_to_offline_transition(self) -> None:
        from api.app.twin.state import TwinState as _TS

        offline_ts = datetime.now(UTC) - timedelta(seconds=STALE_TO_OFFLINE_SECONDS + 1)
        stale_state = _TS(
            machine_id="MOT-1001",
            sync_status=SYNC_STALE,
            last_telemetry_ts=offline_ts,
            health_state="WARNING",
            health_score=60.0,
        )
        with self.svc._lock:
            self.svc._states["MOT-1001"] = stale_state

        new_state = self.svc.tick_staleness("MOT-1001")
        assert new_state is not None
        assert new_state.sync_status == SYNC_OFFLINE
        assert new_state.health_state == "OFFLINE"

    def test_tick_live_fresh_no_transition(self) -> None:
        payload = _make_payload()
        result = _make_inference_result()
        self.svc.update_from_inference(payload, result)
        state = self.svc.tick_staleness("MOT-1001")
        assert state is not None
        assert state.sync_status == SYNC_LIVE

    # Callbacks
    def test_callback_called_on_state_update(self) -> None:
        called_with: list[tuple] = []

        def cb(mid: str, sd: dict) -> None:
            called_with.append((mid, sd))

        self.svc.register_ws_callback(cb)
        self.svc.update_from_inference(_make_payload(), _make_inference_result())
        assert len(called_with) == 1
        assert called_with[0][0] == "MOT-1001"
        assert called_with[0][1]["machine_id"] == "MOT-1001"

    def test_callback_deregistered(self) -> None:
        called: list[int] = []

        def cb(mid: str, sd: dict) -> None:
            called.append(1)

        self.svc.register_ws_callback(cb)
        self.svc.unregister_ws_callback(cb)
        self.svc.update_from_inference(_make_payload(), _make_inference_result())
        assert len(called) == 0

    def test_duplicate_callback_not_doubled(self) -> None:
        called: list[int] = []

        def cb(mid: str, sd: dict) -> None:
            called.append(1)

        self.svc.register_ws_callback(cb)
        self.svc.register_ws_callback(cb)  # duplicate
        self.svc.update_from_inference(_make_payload(), _make_inference_result())
        assert len(called) == 1  # fired only once

    def test_faulty_callback_does_not_crash_service(self) -> None:
        def bad_cb(mid: str, sd: dict) -> None:
            raise RuntimeError("intentional error")

        self.svc.register_ws_callback(bad_cb)
        # Must not raise
        self.svc.update_from_inference(_make_payload(), _make_inference_result())
        # State should still be updated
        assert self.svc.get_state("MOT-1001") is not None

    # Recommendation serialisation
    def test_recommendation_serialised_as_dict(self) -> None:
        result = _make_inference_result()
        rec_mock = MagicMock()
        rec_mock.action_code = "REPLACE_TOOL"
        rec_mock.recommendation_text = "Replace cutting tool immediately."
        rec_mock.urgency = "HIGH"
        rec_mock.target_component = "Tool"
        rec_mock.reason = "Wear limit exceeded"
        result.health_assessment.recommendation = rec_mock

        state = self.svc.update_from_inference(_make_payload(), result)
        assert state.recommendation is not None
        assert state.recommendation["action_code"] == "REPLACE_TOOL"
        assert state.recommendation["urgency"] == "HIGH"


# ---------------------------------------------------------------------------
# Snapshot persistence tests (SQLite in-memory)
# ---------------------------------------------------------------------------

from api.app.twin.snapshot import get_latest_snapshot, get_snapshot_history, persist_twin_snapshot


@pytest.fixture()
def sqlite_session():
    """Provide an in-memory SQLite session for snapshot persistence tests.

    Enables PRAGMA foreign_keys = ON so that FK violations are caught the
    same way they would be in PostgreSQL.
    """
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    from api.app.db.base import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # Enforce FK constraints in SQLite (disabled by default)
    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _conn_record):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _make_twin_state(
    machine_id: str = "MOT-1001",
    sync_status: str = SYNC_LIVE,
    health_state: str = "HEALTHY",
    health_score: float = 90.0,
) -> TwinState:
    return TwinState(
        machine_id=machine_id,
        sync_status=sync_status,
        health_state=health_state,
        health_score=health_score,
        risk_band="LOW",
        failure_probability=0.03,
        anomaly_flag=False,
        operating_state="RUNNING",
        last_telemetry_ts=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        signals={"air_temp_c": 25.0},
        quality={"air_temp_c": "OK"},
        edge={"trip": None},
        model_version="edgetwin-risk:v2-champion",
        provenance="SIMULATED",
    )


class TestSnapshotPersistence:
    def test_persist_snapshot_creates_record(self, sqlite_session) -> None:
        # Need a machine row first
        from api.app.models.machine import MachineRecord

        sqlite_session.add(MachineRecord(machine_id="MOT-1001", machine_type="Motor"))
        sqlite_session.commit()

        state = _make_twin_state()
        record = persist_twin_snapshot(sqlite_session, state)
        assert record is not None
        assert record.id is not None
        assert record.machine_id == "MOT-1001"
        assert record.sync_status == SYNC_LIVE
        assert record.health_state == "HEALTHY"
        assert record.health_score == pytest.approx(90.0)

    def test_get_latest_snapshot(self, sqlite_session) -> None:
        from api.app.models.machine import MachineRecord

        sqlite_session.add(MachineRecord(machine_id="MOT-1001", machine_type="Motor"))
        sqlite_session.commit()

        persist_twin_snapshot(sqlite_session, _make_twin_state(health_score=80.0))
        persist_twin_snapshot(sqlite_session, _make_twin_state(health_score=70.0))

        latest = get_latest_snapshot(sqlite_session, "MOT-1001")
        assert latest is not None
        # Latest score should be 70 (written second)
        assert latest.health_score == pytest.approx(70.0)

    def test_get_latest_snapshot_none_if_no_records(self, sqlite_session) -> None:
        result = get_latest_snapshot(sqlite_session, "MOT-9999")
        assert result is None

    def test_get_snapshot_history_ordered(self, sqlite_session) -> None:
        from api.app.models.machine import MachineRecord

        sqlite_session.add(MachineRecord(machine_id="MOT-1001", machine_type="Motor"))
        sqlite_session.commit()

        for score in [90.0, 80.0, 70.0]:
            persist_twin_snapshot(sqlite_session, _make_twin_state(health_score=score))

        history = get_snapshot_history(sqlite_session, "MOT-1001", limit=10)
        assert len(history) == 3

    def test_snapshot_payload_contains_full_state(self, sqlite_session) -> None:
        from api.app.models.machine import MachineRecord

        sqlite_session.add(MachineRecord(machine_id="MOT-1001", machine_type="Motor"))
        sqlite_session.commit()

        state = _make_twin_state()
        record = persist_twin_snapshot(sqlite_session, state)
        payload = record.snapshot_payload
        assert payload["machine_id"] == "MOT-1001"
        assert payload["sync_status"] == SYNC_LIVE
        assert "signals" in payload

    def test_persist_handles_failure_gracefully(self, sqlite_session) -> None:
        # Snapshot for non-existent machine — FK violation — should return None, not raise
        state = _make_twin_state(machine_id="GHOST-9999")
        result = persist_twin_snapshot(sqlite_session, state)
        assert result is None


# ---------------------------------------------------------------------------
# ConnectionManager tests
# ---------------------------------------------------------------------------

from api.app.ws.broadcaster import ConnectionManager


class TestConnectionManager:
    """All async tests are wrapped with asyncio.run() — pytest-asyncio is not installed."""

    def setup_method(self) -> None:
        self.mgr = ConnectionManager()

    def _make_ws(self) -> AsyncMock:
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    def test_connect_increments_count(self) -> None:
        async def _run():
            ws = self._make_ws()
            await self.mgr.connect(ws, machine_id="MOT-1001")
            assert self.mgr.active_count == 1

        asyncio.run(_run())

    def test_disconnect_decrements_count(self) -> None:
        async def _run():
            ws = self._make_ws()
            await self.mgr.connect(ws)
            self.mgr.disconnect(ws)
            assert self.mgr.active_count == 0

        asyncio.run(_run())

    def test_disconnect_unknown_ws_safe(self) -> None:
        ws = self._make_ws()
        self.mgr.disconnect(ws)  # Must not raise

    def test_broadcast_sends_to_matching_machine(self) -> None:
        async def _run():
            ws1 = self._make_ws()
            ws2 = self._make_ws()
            await self.mgr.connect(ws1, machine_id="MOT-1001")
            await self.mgr.connect(ws2, machine_id="PMP-2001")
            await self.mgr.broadcast_twin_update("MOT-1001", {"machine_id": "MOT-1001"})
            ws1.send_text.assert_awaited_once()
            ws2.send_text.assert_not_awaited()

        asyncio.run(_run())

    def test_broadcast_sends_to_all_when_filter_none(self) -> None:
        async def _run():
            ws1 = self._make_ws()
            ws2 = self._make_ws()
            await self.mgr.connect(ws1, machine_id=None)
            await self.mgr.connect(ws2, machine_id="PMP-2001")
            await self.mgr.broadcast_twin_update("MOT-1001", {"machine_id": "MOT-1001"})
            ws1.send_text.assert_awaited_once()
            ws2.send_text.assert_not_awaited()

        asyncio.run(_run())

    def test_broadcast_removes_dead_connections(self) -> None:
        async def _run():
            ws_dead = self._make_ws()
            ws_dead.send_text.side_effect = RuntimeError("connection closed")
            await self.mgr.connect(ws_dead, machine_id=None)
            await self.mgr.broadcast_twin_update("MOT-1001", {"machine_id": "MOT-1001"})
            assert self.mgr.active_count == 0

        asyncio.run(_run())

    def test_broadcast_message_json_format(self) -> None:
        async def _run():
            ws = self._make_ws()
            await self.mgr.connect(ws, machine_id=None)
            state = {"machine_id": "MOT-1001", "sync_status": "LIVE"}
            await self.mgr.broadcast_twin_update("MOT-1001", state)
            sent_text = ws.send_text.call_args[0][0]
            msg = json.loads(sent_text)
            assert msg["event"] == "twin_update"
            assert msg["data"]["machine_id"] == "MOT-1001"

        asyncio.run(_run())

    def test_broadcast_no_connections_is_noop(self) -> None:
        async def _run():
            await self.mgr.broadcast_twin_update("MOT-1001", {"machine_id": "MOT-1001"})

        asyncio.run(_run())  # Must not raise

    def test_multiple_updates_accumulated(self) -> None:
        async def _run():
            ws = self._make_ws()
            await self.mgr.connect(ws, machine_id=None)
            for i in range(3):
                await self.mgr.broadcast_twin_update("MOT-1001", {"seq": i})
            assert ws.send_text.await_count == 3

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# WebSocket endpoint tests
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient

from api.app.main import app


@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client


class TestWebSocketEndpoint:
    def test_ws_live_connects_and_receives_snapshot(self, test_client: TestClient) -> None:
        with test_client.websocket_connect("/ws/live") as ws:
            data = ws.receive_json()
            assert data["event"] == "snapshot"
            assert isinstance(data["data"], list)

    def test_ws_live_ping_pong(self, test_client: TestClient) -> None:
        with test_client.websocket_connect("/ws/live") as ws:
            # Drain the initial snapshot
            ws.receive_json()
            ws.send_text("ping")
            resp = ws.receive_json()
            assert resp["event"] == "pong"

    def test_ws_live_machine_connects(self, test_client: TestClient) -> None:
        with test_client.websocket_connect("/ws/live/MOT-1001") as ws:
            data = ws.receive_json()
            assert data["event"] == "snapshot"
            # data may be None (machine not yet tracked) or a dict
            assert data["data"] is None or isinstance(data["data"], dict)

    def test_ws_live_machine_ping_pong(self, test_client: TestClient) -> None:
        with test_client.websocket_connect("/ws/live/MOT-1001") as ws:
            ws.receive_json()
            ws.send_text("ping")
            resp = ws.receive_json()
            assert resp["event"] == "pong"

    def test_ws_connection_manager_increments(self, test_client: TestClient) -> None:
        from api.app.ws.broadcaster import get_connection_manager

        mgr = get_connection_manager()
        before = mgr.active_count
        with test_client.websocket_connect("/ws/live"):
            assert mgr.active_count == before + 1
        # After disconnect count returns
        assert mgr.active_count == before

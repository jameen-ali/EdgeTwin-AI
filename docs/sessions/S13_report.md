# S13 Session Report — Digital Twin Service + WebSocket Real-Time Synchronization (T-035 + T-037)

**EdgeTwin AI — AI-Powered Predictive Maintenance using Digital Twins and Edge Intelligence**
- **Date:** 2026-09-28
- **Session:** S13 (T-035 Digital Twin Service + T-037 WebSocket Stream)
- **Branch:** `feat/T-035-T-037-digital-twin-websocket`
- **Base Commit:** S12 baseline (`feat(inference): add inference service and health engine L1-L6`)

---

## 1. Executive Summary

Session S13 implemented the real-time Digital Twin layer and WebSocket streaming synchronization for EdgeTwin AI:
1. **T-035 (Digital Twin Service):**
   - **Immutable State Model (`api/app/twin/state.py`):** Created frozen `TwinState` dataclass encapsulating machine health, operating state (from edge trip signals), failure probability, anomaly flags, SHAP top factors, recommendations, and telemetry metadata.
   - **Sync FSM:** Implemented the 3-state synchronization Finite State Machine per architecture specification §9 (`LIVE` → `STALE` after 5s silence → `OFFLINE` after 30s silence or explicit MQTT LWT).
   - **State Manager (`api/app/twin/service.py`):** Thread-safe `TwinService` maintaining per-machine state in memory, handling inference updates, staleness evaluation, LWT disconnects, and subscriber notifications.
   - **Snapshot Persistence (`api/app/twin/snapshot.py`):** Transactionally persists `TwinSnapshotRecord` to the database on every state update/transition with complete error isolation.
   - **Ingestion Pipeline Wiring (`api/app/ingest/handler.py`):** Integrated Step 8 into `handle_message()`, seamlessly updating the Digital Twin and writing snapshot rows immediately after inference.
2. **T-037 (WebSocket Stream):**
   - **Connection Manager (`api/app/ws/broadcaster.py`):** Async multi-client connection manager supporting broadcast fan-out, per-machine topic subscriptions, dead connection pruning, and graceful error handling.
   - **Live Streaming Endpoints (`api/app/ws/router.py`):** Exposed `/ws/live` (all machines) and `/ws/live/{machine_id}` (machine-specific subscription) WebSocket routes. Sends immediate snapshot upon client connect, pushes `twin_update` events on state transitions, and responds to ping/pong keepalives.
   - **Application Lifespan Wiring (`api/app/main.py`):** Configured FastAPI lifespan to wire the WebSocket broadcast callback into `TwinService` on startup and cleanly unregister on shutdown.
3. **Verification:** Added 46 comprehensive unit and integration tests across `tests/api/test_twin.py`. Full project test suite: **484 passed, 1 skipped** (offline MQTT integration test).

---

## 2. Implemented Architecture & Modules

### 2.1 Package Structure (`api/app/twin/` and `api/app/ws/`)
- `api/app/twin/state.py`: `TwinState` immutable dataclass, constants (`SYNC_LIVE`, `SYNC_STALE`, `SYNC_OFFLINE`, `STALE_SECONDS = 5.0`, `STALE_TO_OFFLINE_SECONDS = 30.0`), and JSON-serialisation `to_dict()`.
- `api/app/twin/service.py`: `TwinService` managing in-memory state dictionary, thread lock synchronization, state transition callbacks, staleness clock ticks, and singleton accessor `get_twin_service()`.
- `api/app/twin/snapshot.py`: Snapshot persistence utilities (`persist_twin_snapshot`, `get_latest_snapshot`, `get_snapshot_history`) interacting with `TwinSnapshotRecord`.
- `api/app/twin/__init__.py`: Package exports for twin state and service.
- `api/app/ws/broadcaster.py`: `ConnectionManager` managing active WebSockets, subscription filters, thread-safe iteration, and dead connection pruning.
- `api/app/ws/router.py`: FastAPI WebSocket routes `/ws/live` and `/ws/live/{machine_id}` with immediate snapshot push and ping/pong echo.
- `api/app/ws/__init__.py`: Package exports for WebSocket broadcaster and router.

### 2.2 Integration Points
- **MQTT Ingestion Handler (`api/app/ingest/handler.py`):** Step 8 triggers `TwinService.update_from_inference()` and `persist_twin_snapshot()` within a dedicated `try/except` boundary. Twin failures never block or invalidate persisted telemetry.
- **FastAPI Lifespan (`api/app/main.py`):** Registers async broadcaster callback with `TwinService` during application startup, binds `ConnectionManager` and `TwinService` to `app.state`, mounts `ws_router`, and cleanly deregisters on shutdown.

---

## 3. Data Flow

```text
MQTT Broker
    │ (edgetwin/telemetry/{machine_id})
    ▼
MQTTIngestionClient (Thread)
    │
    ▼
handle_message() [api/app/ingest/handler.py]
    ├─ Step 1-6: Validation & Telemetry Persistence (S11)
    ├─ Step 7:   Inference & Health Engine L1-L6 (S12)
    │            └─ outputs InferenceResult
    └─ Step 8:   Digital Twin Update (S13)
                 │
                 ├─► TwinService.update_from_inference()
                 │     ├─ Updates in-memory TwinState (LIVE)
                 │     └─ Fires registered callbacks
                 │          │
                 │          ▼
                 │     ConnectionManager.broadcast_twin_update()
                 │          │
                 │          ├─► /ws/live (all connected dashboard clients)
                 │          └─► /ws/live/{machine_id} (single machine subscribers)
                 │
                 └─► persist_twin_snapshot()
                       └─ Writes TwinSnapshotRecord to PostgreSQL / SQLite
```

---

## 4. Test Suite & Verification Results

- **New Tests (`tests/api/test_twin.py`):** 46 tests covering:
  - `TwinState` dataclass immutability, default fields, serialization, and JSON compliance.
  - `TwinService` live state creation, multi-machine isolation, and state retrieval.
  - Operating state derivation (`RUNNING` vs `TRIPPED` based on edge payload trip code).
  - Sync FSM transitions (`LIVE` → `STALE` → `OFFLINE` based on elapsed time).
  - Explicit `mark_offline()` handling (e.g. for MQTT LWT triggers).
  - WebSocket callback registration, deregistration, duplicate suppression, and exception containment.
  - Database snapshot persistence (`persist_twin_snapshot`), latest query, and history queries with foreign key enforcement.
  - `ConnectionManager` connect, disconnect, machine_id filtering, broadcast JSON format, and dead connection removal.
  - Live FastAPI WebSocket endpoints (`/ws/live` and `/ws/live/{machine_id}`) verifying initial snapshot delivery, ping/pong echo, and connection counting.
- **Full Test Suite:** **484 passed, 1 skipped** (offline MQTT integration test).
- **Static Analysis & Quality Checks:**
  - `ruff check .`: Clean (0 errors).
  - `ruff format --check api/app/twin api/app/ws tests/api/test_twin.py api/app/ingest/handler.py api/app/main.py`: Clean (10 files formatted).

---

## 5. Scope Compliance & Guardrails

- [x] Implemented ONLY T-035 (Digital Twin Service) and T-037 (WebSocket Stream).
- [x] Did NOT implement REST API v1 endpoints (deferred to S14 / T-036).
- [x] Did NOT implement JWT authentication / RBAC (deferred to S15 / T-038).
- [x] Did NOT touch frontend / dashboard code.
- [x] Did NOT redesign firmware or ML models.
- [x] No git push executed.

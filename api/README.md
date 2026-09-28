# EdgeTwin AI Backend API & Database Service

The `api/` directory contains the FastAPI backend and database persistence foundation for the EdgeTwin AI predictive maintenance platform.

---

## 1. Architecture & Package Structure

```
api/
├── alembic.ini                   # Alembic database migration configuration
├── migrations/                   # Alembic migration scripts
│   ├── env.py                    # Migration runtime environment
│   ├── script.py.mako            # Revision template
│   └── versions/
│       └── 0001_initial_schema.py # Initial DDL migration for all 8 entities
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entrypoint & lifespan
│   ├── config.py                 # Environment-driven settings (pydantic-settings)
│   ├── logging.py                # Structured logging configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py               # SQLAlchemy 2.0 DeclarativeBase
│   │   └── session.py            # Engine, sessionmaker, get_db, connection check
│   ├── models/                   # SQLAlchemy 2.0 domain models
│   │   ├── __init__.py
│   │   ├── machine.py            # Machine fleet asset metadata
│   │   ├── telemetry.py          # Raw telemetry records (edgetwin.telemetry.v1)
│   │   ├── prediction.py         # ML predictions & health assessments
│   │   ├── twin.py               # ISO 23247 Digital Twin state snapshots
│   │   ├── alert.py              # System and machine alarms
│   │   ├── feedback.py           # Technician feedback (CONFIRMED/FALSE_ALARM)
│   │   ├── maintenance.py        # Maintenance actions and overhaul logs
│   │   └── model_version.py      # MLflow registry version lineage
│   ├── schemas/                  # Pydantic v2 validation & response models
│   │   ├── __init__.py
│   │   ├── common.py             # RFC 7807 problem details error schema
│   │   └── health.py             # /health and /ready response schemas
│   └── routes/                   # API endpoint routers
│       ├── __init__.py
│       └── health.py             # Liveness (/health) and Readiness (/ready)
└── README.md
```

---

## 2. Database Choice & Schema

- **Selected Engine:** **PostgreSQL 16** (production / local Docker Compose) and **SQLite** (lightweight local testing/CI).
- **ORM / Migrations:** **SQLAlchemy 2.0** (`Mapped[...]`, `mapped_column(...)`) and **Alembic**.
- **Entities & Tables:**
  1. `machines`: Fleet assets identified by `machine_id` (e.g. `MOT-1001`).
  2. `telemetry`: Raw time-series telemetry with 10 nullable sensor channels, `quality` JSON, `edge` diagnostics, and unique constraint on `(machine_id, seq)`.
  3. `predictions`: ML inference outputs (`failure_probability`, `risk_band`, `anomaly_score`, `health_score`, `top_factors` SHAP JSON, `model_version`).
  4. `twin_snapshots`: Periodic full state objects aligned with ISO 23247.
  5. `alerts`: Layer 5 alarms (`INFO`, `WARNING`, `CRITICAL`) with lifecycle state.
  6. `feedback`: Engineer ground truth labels (`CONFIRMED`, `FALSE_ALARM`).
  7. `maintenance_events`: Logs of inspections and component overhauls.
  8. `model_versions`: Mirror of MLflow model registry and promotion status.

---

## 3. Local Development & Startup Commands

### Start Backing Services (PostgreSQL & Mosquitto)
```bash
docker compose up postgres mosquitto -d
```

### Run Database Migrations
```bash
# Upgrade database to head revision
alembic -c api/alembic.ini upgrade head

# Rollback one revision
alembic -c api/alembic.ini downgrade -1
```

### Start FastAPI Application Locally
```bash
uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Execute Test Suite
```bash
# Run all backend API and database tests
pytest tests/api/ -v
```

---

## 4. API Endpoints (S10 Baseline)

| Endpoint | Method | Response | Description |
|---|---|---|---|
| `/health` | `GET` | `HealthResponse` (200) | Liveness probe indicating backend process is alive. |
| `/ready` | `GET` | `ReadyResponse` (200 / 503) | Readiness probe verifying active database connection. |
| `/api/v1/health` | `GET` | `HealthResponse` (200) | Versioned prefix alias for liveness. |
| `/api/v1/ready` | `GET` | `ReadyResponse` (200 / 503) | Versioned prefix alias for readiness. |

---

## 5. Security & Error Handling

- **No Hardcoded Credentials:** Configuration is loaded strictly from environment variables via Pydantic Settings.
- **CORS Allow-List:** Restrictive CORS configuration driven by `CORS_ORIGINS`.
- **RFC 7807 Problem Details:** All validation errors (422), HTTP exceptions (4xx), and internal errors (500) return standard `application/problem+json` envelopes.

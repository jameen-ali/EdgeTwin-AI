# EdgeTwin AI — Predictive Maintenance Platform

> **AI-Powered Predictive Maintenance for Industry 4.0**
> Real-time machine health monitoring, anomaly detection, and automated maintenance workflows.

---

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended)
- **Node.js 18+** (frontend)
- **Python 3.10+** (backend)
- **PostgreSQL 15+** (if running without Docker)

### 1. Start Infrastructure

```bash
docker-compose up -d
```

### 2. Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at **http://localhost:5173**

---

## 🔐 Demo User Credentials

All demo accounts use the same password: **`EdgeTwin@2026`**

| # | Role                    | Email                        | Password         |
|---|-------------------------|------------------------------|------------------|
| 1 | Machine Operator        | `operator@edgetwin.ai`       | `EdgeTwin@2026`  |
| 2 | Maintenance Manager     | `manager@edgetwin.ai`        | `EdgeTwin@2026`  |
| 3 | Maintenance Technician  | `technician@edgetwin.ai`     | `EdgeTwin@2026`  |
| 4 | Production Manager      | `production@edgetwin.ai`     | `EdgeTwin@2026`  |
| 5 | Factory Owner           | `owner@edgetwin.ai`          | `EdgeTwin@2026`  |
| 6 | Admin                   | `admin@edgetwin.ai`          | `EdgeTwin@2026`  |

### Auto-Seeding

Demo users are **automatically created on first startup** when `DEBUG=true` (default). The seeder checks if the `users` table is empty — if so, it inserts all 6 demo users with bcrypt-hashed passwords.

**To re-seed** (e.g., after a database reset):
```bash
# Truncate users and re-run
python backend/app/seeds/seed_users.py
```

**To regenerate SQL + credentials files**:
```bash
python backend/app/seeds/generate_credentials.py
```

---

## 📁 Project Structure

```
TATA/
├── backend/                 # FastAPI backend (Python)
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints
│   │   ├── core/            # Config, database, security
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── seeds/           # Database seeding (demo users, machines)
│   │   ├── services/        # Business logic
│   │   ├── middleware/       # Custom middleware
│   │   ├── websocket/       # WebSocket handlers
│   │   ├── workers/         # Celery background tasks
│   │   └── main.py          # FastAPI app entrypoint
│   ├── migrations/          # Alembic migrations
│   └── requirements.txt
├── frontend/                # React + Vite frontend
├── docker/                  # Docker configurations
├── iot/                     # IoT simulator / connectors
├── ml/                      # ML models (RUL, anomaly detection)
└── docker-compose.yml
```

---

## 🛠️ Tech Stack

| Layer       | Technology                                    |
|-------------|-----------------------------------------------|
| Frontend    | React, TypeScript, Vite, Three.js             |
| Backend     | FastAPI, SQLAlchemy, Pydantic                  |
| Database    | PostgreSQL, TimescaleDB, Redis                 |
| ML          | scikit-learn, XGBoost, ONNX Runtime            |
| Infra       | Docker, Celery, MinIO (S3), WebSockets         |

---

## 📡 API Docs

When the backend is running:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

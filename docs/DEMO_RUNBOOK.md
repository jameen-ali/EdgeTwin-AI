# EdgeTwin AI — Demo Runbook

> **For:** College evaluation / hackathon / final year project demo  
> **Duration:** 5–10 minutes for a focused walkthrough; 2–3 minutes for the quick version  
> **Audience:** Evaluators, panel members, fellow students

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Docker Desktop | Running | `docker info` → no error |
| Internet connection | — | For any cloud broker path |
| Modern browser | Chrome/Edge/Firefox | — |

> ⚠️ If Docker is unavailable, see **Fallback Procedure** at the end.

---

## 1. Start Docker Desktop

1. Open **Docker Desktop** from Start menu / Applications
2. Wait for the whale icon in the system tray to turn green (daemon ready)
3. Verify: `docker info` — should print server version

---

## 2. Start the Docker Compose Stack

```bash
cd EdgeTwin-AI
cp .env.example .env       # only needed on first run
docker compose up --build -d
```

First build takes 2–4 minutes. Subsequent starts take < 30 seconds.

Expected output:
```
✔ Container edgetwin-ai-postgres-1    Healthy
✔ Container edgetwin-ai-mosquitto-1   Healthy
✔ Container edgetwin-ai-api-1         Healthy
✔ Container edgetwin-ai-frontend-1    Healthy
```

---

## 3. Verify All Services

```bash
docker compose ps
```

All 4 containers should show status `running (healthy)`.

Quick health check:
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "database": "connected", ...}
```

---

## 4. Open the Dashboard

Open in browser: **http://localhost:3000**

The login page appears.

---

## 5. Login

| Role | Username | Password |
|---|---|---|
| **Admin** (recommended for demo) | `admin` | `admin_password` |
| Maintenance Engineer | `engineer` | `engineer_password` |
| Operator | `operator` | `operator_password` |

> ⚠️ These are demo credentials from `.env`. Change them in `.env` before any shared deployment.

Login → you land on the **Fleet Dashboard**.

---

## 6. Fleet Dashboard Overview

Point out:
- **6 machine cards** — different machine types (Motor, Compressor, CNC, Pump, Conveyor)
- Each card shows: health state badge, risk band, failure probability, last-seen timestamp
- All machines start in **HEALTHY / LOW** state

> Say: *"This is the fleet-level view. Each card represents a Digital Twin — a live JSON
> state object that gets updated every second as telemetry arrives from the edge device."*

---

## 7. Select a Machine

Click **MOT-1001** (or any machine).

Point out on Machine Detail page:
- **Live telemetry gauges** — updating in real time (air temp, process temp, RPM, torque, vibration...)
- **Digital Twin panel** — sync status LIVE, health score, risk probability
- **Top contributing factors** — SHAP bar chart showing which features drive the current risk score
- **No active alerts** (machine is healthy)

> Say: *"Every telemetry message triggers ML inference — XGBoost risk classification,
> Platt-calibrated probability, Isolation Forest anomaly score, and TreeSHAP attributions —
> all in about 50 ms."*

---

## 8. Show Live Telemetry

Let the gauges update for 10–15 seconds.

Point out:
- Values change on each tick (1 Hz simulated)
- Timestamps update
- Digital Twin sync status shows LIVE
- Health score stays near 100

---

## 9. Navigate to Digital Twin Panel

Click the **Digital Twin** tab on the machine detail page.

Point out:
- 2D machine schematic with signals bound to twin state
- Each sensor channel shows value + quality flag (OK / LIMIT_WARN / etc.)
- Sync status indicator (LIVE / STALE / OFFLINE)
- Health state and risk band displayed prominently

---

## 10. Trigger Healthy Scenario (Baseline)

Go to: **Scenarios** page (sidebar)

1. Select machine: MOT-1001
2. Select scenario: **Healthy Nominal Operation**
3. Click **Run Scenario**

Observe: Dashboard stays HEALTHY, probability stays LOW, no alerts generated.

> Say: *"This is the baseline — zero false alarms in steady state. The model was trained
> to avoid noise-induced alerts."*

---

## 11. Trigger a Failure Scenario

On the Scenarios page:

1. Select machine: MOT-1001
2. Select scenario: **Heat Dissipation Failure**
3. Click **Run Scenario**

Now switch back to **Machine Detail → MOT-1001** and watch:

- Temperature gauges rise
- ΔT (Process_T − Air_T) increases
- Failure probability climbs: 0.04 → 0.15 → **0.89 (CRITICAL)**
- Risk band badge changes: LOW → HIGH → **CRITICAL**
- Health score drops: 99 → 70 → **35**
- Health state changes to **CRITICAL**

> Say: *"The ML model detects the rising temperature delta in about 18 seconds —
> that's 18 ticks. This matches the T-070 benchmark result."*

---

## 12. Show SHAP Prediction Explanation

On the machine detail page, click **Predictions** tab.

- Click the most recent prediction row
- The **SHAP bar chart** shows top contributing features
- Expect: `Delta_T_C` and `Air_Temperature_C` at the top for heat dissipation

> Say: *"The system uses TreeSHAP to explain *why* the model fired — not just that it fired.
> This is critical for a maintenance engineer to trust and act on the alert."*

---

## 13. Show the Alert

Go to: **Alerts** page (sidebar)

- A new **CRITICAL** alert appears: "Heat dissipation failure risk detected on MOT-1001"
- Fields: machine, scenario, severity, triggered timestamp, status: OPEN

> Say: *"The six-layer health engine converts the ML prediction into an alert with severity
> and deduplicated lifecycle management."*

---

## 14. Acknowledge the Alert

Click the alert row → **Acknowledge**

- Status changes: OPEN → ACKNOWLEDGED
- Timestamp of acknowledgment recorded

> Say: *"Engineers acknowledge alerts before investigation, preventing duplicate notifications."*

---

## 15. Create a Maintenance Work Order

Go to: **Maintenance** page → **New Work Order**

Fill in:
- Machine: MOT-1001
- Description: Inspect heat exchanger — elevated ΔT detected
- Priority: High
- Link to alert: (select the heat dissipation alert)

Click **Create**.

> Say: *"The maintenance workflow creates a traceable work order linked to the alert and
> machine. When completed, the machine can return to HEALTHY state."*

---

## 16. Submit Engineer Feedback

Go back to **Alerts** → select the heat dissipation alert → **Submit Feedback**

- Select: **Confirmed failure** (not a false alarm)
- Click Submit

> Say: *"Confirmed and rejected feedback is stored as labelled data. When enough feedback
> accumulates, it feeds into the retraining pipeline to improve the model over time."*

---

## 17. Show History & Analytics

Go to: **History** page

- Select machine: MOT-1001
- Set time range: Last 30 minutes
- See: prediction probability timeline, health score chart, telemetry trends

> Say: *"Full time-series history is stored in PostgreSQL. Engineers can query any
> machine's complete sensor and prediction history."*

---

## 18. Show MLOps Page

Go to: **MLOps** page

Point out:
- **Current champion model** — version, algorithm, PR-AUC, Recall
- **Model versions** — challenger comparison
- **Drift status** — PSI/KS drift metrics vs training reference
- **Retraining history** — when retraining was triggered, gate result

> Say: *"The model doesn't just get deployed once. The system monitors for data drift,
> triggers retraining when conditions are met, and gates promotion using held-out metrics."*

---

## 19. Show Drift Monitoring

On the MLOps page, click **Drift** tab.

- PSI (Population Stability Index) per feature
- KS test results
- Drift flag status (GREEN/YELLOW/RED)

> Say: *"PSI and KS tests compare live telemetry distributions against the training reference.
> When drift is detected, the system flags it as a potential retraining trigger."*

---

## 20. Show Model Governance

On the MLOps page, show:
- Current champion alias → `edgetwin-risk@champion`
- Champion was promoted by meeting the gate: Recall ≥ 0.85 AND Precision ≥ 0.70
- Rollback available: one command restores previous champion

> Say: *"This is gated promotion — the challenger must beat the champion on the frozen test set
> before it becomes the new champion. Rollback is always one command away."*

---

## 21. Scenario Control — Show More Scenarios

On the Scenarios page, optionally demonstrate:
- **Power Failure + Safety Trip** — edge safety trip fires immediately at step 30
- **Sensor Dropout** — graceful quality degradation, no false CRITICAL alert
- **Machine Offline + LWT** — twin transitions to OFFLINE state

---

## 22. Recovery / Cleanup

To stop a running scenario: **Scenarios → Stop Scenario**

The machine will return to healthy telemetry within a few seconds.

To shut down the stack:
```bash
docker compose down
```

Persistent data (PostgreSQL volume) survives shutdown. Use `docker compose down -v` to
also remove volumes (resets all data — use with caution during demos).

---

## 23. Fallback Procedure (If Docker / Wokwi Is Unavailable)

### Docker not running

```bash
# Start Docker Desktop, wait for daemon
docker compose up -d           # try again
```

If Docker Desktop won't start:
1. Open Task Manager → check Docker processes
2. Restart Docker Desktop from Start menu

### API not healthy

```bash
docker compose logs api --tail=50    # check for migration errors
docker compose restart api
```

### Frontend not loading

```bash
docker compose logs frontend --tail=20
# If 502 Bad Gateway: API may not be ready yet
docker compose restart frontend
```

### No live telemetry (gauges frozen)

The virtual edge starts automatically on API startup. Check:
```bash
docker compose logs api | findstr "virtual_edge"
```

### Database migration failure

```bash
docker compose exec api alembic -c api/alembic.ini upgrade head
```

### Complete offline demo (no Docker at all)

Run backend in-process + frontend dev server:

```bash
# Terminal 1: start Mosquitto
mosquitto -c mosquitto/mosquitto.conf

# Terminal 2: start API
cp .env.example .env
alembic -c api/alembic.ini upgrade head
uvicorn api.app.main:app --reload

# Terminal 3: start frontend
cd dashboard && npm run dev

# Open: http://localhost:5173
```

---

*EdgeTwin AI Demo Runbook — S30 — 2026-09-30*

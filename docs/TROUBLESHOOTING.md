# EdgeTwin AI — Troubleshooting Guide

Common issues and solutions for development, demo, and evaluation environments.

---

## Docker Desktop Not Running

**Symptom:** `docker compose up` fails with "Cannot connect to the Docker daemon".

**Fix:**
1. Open Docker Desktop application
2. Wait for the system tray icon to turn green
3. Retry: `docker compose up -d`

**Check:**
```bash
docker info   # should print server information without errors
```

---

## PostgreSQL Container Unhealthy

**Symptom:** `docker compose ps` shows `postgres` as `unhealthy`.

**Fixes:**

Check logs:
```bash
docker compose logs postgres --tail=50
```

Common causes:
- Port 5432 already in use by local PostgreSQL installation
  - Fix: `docker compose down && docker compose up -d` after stopping local PG
  - Or: change port mapping in `docker-compose.yml` to `5433:5432`
- Data volume corruption:
  - Fix: `docker compose down -v && docker compose up -d` (WARNING: deletes all data)

Check health manually:
```bash
docker compose exec postgres pg_isready -U edgetwin -d edgetwin
```

---

## Mosquitto / MQTT Broker Unavailable

**Symptom:** API logs show "Connection refused" to localhost:1883. No telemetry arriving.

**Fixes:**

Check container:
```bash
docker compose logs mosquitto --tail=30
docker compose restart mosquitto
```

Check config:
```bash
cat mosquitto/mosquitto.conf
# Should have: listener 1883, allow_anonymous true (dev config)
```

Test connectivity:
```bash
docker compose exec mosquitto nc -z localhost 1883 && echo "MQTT OK"
```

---

## API Container Unhealthy

**Symptom:** `api` shows `unhealthy` in `docker compose ps`.

**Fixes:**

Check logs:
```bash
docker compose logs api --tail=100
```

Common causes:
1. **Migration failure** — database not ready yet:
   ```bash
   docker compose exec api alembic -c api/alembic.ini upgrade head
   docker compose restart api
   ```
2. **Missing environment variables** — check `.env` file has all required values from `.env.example`
3. **Port 8000 already in use**:
   ```bash
   netstat -ano | findstr :8000   # Windows
   # Kill the process or change port in docker-compose.yml
   ```
4. **MLflow artifact not found**:
   ```bash
   python scripts/ml_smoke_test.py   # verify artifacts exist
   ```

Health check:
```bash
curl http://localhost:8000/health
```

---

## Frontend / Dashboard Unavailable

**Symptom:** http://localhost:3000 returns 502 Bad Gateway or connection refused.

**Fixes:**

Check container:
```bash
docker compose logs frontend --tail=30
docker compose restart frontend
```

Common causes:
1. **API not healthy yet** — frontend depends on API health:
   ```bash
   docker compose ps   # wait for api to be healthy first
   ```
2. **Port 3000 in use**:
   ```bash
   netstat -ano | findstr :3000   # Windows
   ```
3. **CORS error in browser console** — check `CORS_ORIGINS` in `.env` includes `http://localhost:3000`

---

## Database Migration Failure

**Symptom:** API logs show `alembic.util.exc.CommandError` or `sqlalchemy` errors.

**Fix:**

Run migration manually:
```bash
docker compose exec api alembic -c api/alembic.ini upgrade head
```

Check migration status:
```bash
docker compose exec api alembic -c api/alembic.ini current
docker compose exec api alembic -c api/alembic.ini history
```

If migrations are stuck in a bad state:
```bash
docker compose exec api alembic -c api/alembic.ini downgrade base
docker compose exec api alembic -c api/alembic.ini upgrade head
```

---

## MQTT Connection Issue (No Telemetry Arriving)

**Symptom:** Telemetry gauges on dashboard frozen; API logs show no ingestion.

**Check:**
```bash
docker compose logs api | findstr "mqtt"
docker compose logs api | findstr "ingest"
```

**Fixes:**
1. Restart the API (which restarts the MQTT consumer):
   ```bash
   docker compose restart api
   ```
2. Verify Mosquitto is accepting connections:
   ```bash
   docker compose exec mosquitto nc -z localhost 1883
   ```
3. Check `MQTT_BROKER_URL` in `.env` matches the Mosquitto service name (`mosquitto`)

---

## WebSocket Not Updating (Dashboard Frozen)

**Symptom:** Machine detail page doesn't update in real time; gauges are static.

**Check browser console:** F12 → Console — look for WebSocket errors.

**Fixes:**
1. Check Nginx WebSocket proxy config:
   ```bash
   docker compose exec frontend nginx -t   # test nginx config
   ```
2. The WebSocket endpoint is `ws://localhost:3000/ws/live` (proxied through Nginx).
   If browser shows WebSocket error, verify Nginx config has:
   ```nginx
   proxy_http_version 1.1;
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade";
   ```
3. Hard-refresh the browser (Ctrl+Shift+R)
4. Try incognito window to rule out browser extension issues

---

## Frontend Build Failure

**Symptom:** `npm run build` or `docker compose up --build` fails at frontend step.

**Fix:**
```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
npm run build
```

Common causes:
- Node.js version mismatch (requires Node 20+):
  ```bash
  node --version   # should be >= 20
  ```
- TypeScript error (genuine type issue):
  ```bash
  cd dashboard && npx tsc --noEmit   # see specific error
  ```

---

## Wokwi Simulation Unavailable

**Symptom:** `wokwi-cli` not found, or `WOKWI_CLI_TOKEN` not set. CI job reports notice.

**This is expected behavior** on environments without a Wokwi subscription.

**What still works without Wokwi:**
- Virtual Python edge (`simulation/virtual_edge.py`) — used by default
- Native C++ firmware unit tests (g++ harness)
- All 8 scenario simulations via the virtual edge

**If you have a Wokwi token:**
```bash
export WOKWI_CLI_TOKEN=your_token_here
# Add to GitHub repository secrets as WOKWI_CLI_TOKEN for CI
```

---

## Missing ML Model Artifact

**Symptom:** API fails to start with `FileNotFoundError` on `.joblib` artifact.
Or `python scripts/ml_smoke_test.py` fails with artifact not found.

**Fix:**
```bash
python scripts/ml_smoke_test.py   # diagnose which artifact is missing
```

The artifacts should be committed in `artifacts/`:
```
artifacts/calibrated_classifier_sigmoid.joblib
artifacts/champion_features.json
artifacts/anomaly_isolation_forest.joblib
artifacts/anomaly_ref_params.json
artifacts/training_reference_stats.json
```

If missing (e.g., after fresh clone without LFS):
```bash
dvc pull   # restore DVC-tracked artifacts
```

If DVC remote is not configured:
```bash
python ml/models/train.py   # re-run training to regenerate artifacts
```

---

## Stale or Missing Environment Variables

**Symptom:** API startup error about missing `SECRET_KEY`, `DATABASE_URL`, or other env vars.

**Fix:**
```bash
cp .env.example .env
# Edit .env — fill in values as needed
```

Required variables (see `.env.example`):
```
DATABASE_URL=postgresql://edgetwin:edgetwin_password@localhost:5432/edgetwin
POSTGRES_USER=edgetwin
POSTGRES_PASSWORD=edgetwin_password
POSTGRES_DB=edgetwin
MQTT_BROKER_URL=mqtt://mosquitto:1883
MQTT_USERNAME=
MQTT_PASSWORD=
JWT_SECRET_KEY=change_me_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

> ⚠️ `.env` is gitignored. Never commit real secrets. `.env.example` must have no real values.

---

## Backend Tests Failing

**Run tests with verbose output:**
```bash
pytest -v --tb=short tests/
```

**Common failures:**

| Symptom | Fix |
|---|---|
| Import errors | `pip install -e .` (missing dependency) |
| Database errors in tests | Tests use in-memory SQLite; check `tests/conftest.py` |
| ML artifact not found | Run `python scripts/ml_smoke_test.py` to diagnose |
| Async test timeout | Increase `asyncio_mode` timeout in `pyproject.toml` |

---

## Frontend Tests Failing

```bash
cd dashboard
npm test -- --run
```

Common failures:
- `Cannot find module` → `npm install`
- Type errors → `npx tsc --noEmit` for details
- Mock not working → check `tests/setup.ts` for global test configuration

---

## Native Firmware Tests Failing to Compile

```bash
g++ -std=c++17 -O2 -Iedge -Itests/edge -Itests/edge/arduino_compat \
    tests/edge/test_native_edge.cpp edge/process_model.cpp \
    edge/ring_buffer.cpp edge/command.cpp edge/telemetry.cpp \
    -o test_native_edge_bin
./test_native_edge_bin
```

> Note: Do NOT include `edge/sensors.cpp` — it depends on `DHTesp.h` (Arduino-only library).
> The CI build deliberately excludes it.

If `g++` is not found:
- Windows: install MinGW-w64 (`ucrt64` package) or Git for Windows (includes g++)
- Linux/macOS: `sudo apt install g++` or `brew install gcc`

---

## AI4I 2020 Dataset Not Found

**Symptom:** `scripts/benchmark_t071.py` fails with "CSV not found".

**Fix:**
```bash
python scripts/download_ai4i.py
```

This downloads the AI4I 2020 CSV from the UCI ML Repository to `data/raw/ai4i2020.csv`.
The CSV is gitignored (per `data/raw/*.csv` rule).

---

## Port Conflicts Summary

| Service | Default Port | Change in |
|---|---|---|
| Frontend | 3000 | `docker-compose.yml` ports section |
| Backend API | 8000 | `docker-compose.yml` ports section |
| PostgreSQL | 5432 | `docker-compose.yml` ports section |
| Mosquitto MQTT | 1883 | `docker-compose.yml` ports section |
| Frontend dev server | 5173 | `dashboard/vite.config.ts` |

---

*EdgeTwin AI Troubleshooting Guide — S30 — 2026-09-30*

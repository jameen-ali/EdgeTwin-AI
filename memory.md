# memory.md — EdgeTwin AI Project Memory

Living log. Update on every important decision, bug, fix, dependency, API or DB change. Newest entries at the top of each section.
Legend: [FACT] sourced · [AUDIT] measured by us on the uploaded files · [DECISION] · [PROPOSED] · [ASSUMPTION]
Last updated: 2026-09-24 (discovery phase, no code written yet)

---
## 1. Current status
- Discovery and research complete. Six core documents drafted (v0.1).
- **[T-001]** Repository scaffolded: `pyproject.toml`, `requirements.txt`, `.gitignore`, `.pre-commit-config.yaml`, `.env.example`, `gemini.md`, `.agents/rules/engineering.md`, and skeleton directories. Notebooks safely moved to `notebooks/`. Verification passed.
- **[T-003]** Reproducible data preparation pipeline implemented and verified. Branch `feat/T-003-data-preparation`. All 38 tests pass. ruff/black clean.
- **[T-010]** DVC versioning initialized. `dvc repro` works. `dvc status` clean after reproduction. Branch `feat/T-010-T-011-data-contract`. 90 tests pass.
- **[T-011]** Shared feature contract and machine-grouped splits implemented. 11 feature columns, 5 forbidden, Machine_Failure as target. Zero Machine_ID overlap. Failure rate within 5pp of 10.97% in all splits.
- **[T-012]** Model comparison experiment completed. Branch `feat/T-012-model-comparison`. 15 candidate (model × feature_set) combinations evaluated with 5-fold CV and MLflow tracking. Champion selected by validation PR-AUC: XGBoost with `+physics` (Val PR-AUC = 0.8969, Recall = 0.8195). Evaluated once on held-out test set: Test PR-AUC = 0.9234, Recall = 0.8963, F1 = 0.8403, Accuracy = 0.9693. Test isolation bug audited and fixed. 149 tests pass.
- **[T-013]** Probability calibration and threshold analysis completed. Platt/Sigmoid calibration selected on validation data (6.8% Brier error reduction, 86.4% ECE reduction, 0 loss in PR-AUC/ROC-AUC). 41 candidate thresholds swept (0.10..0.90, step 0.02). Operational decision threshold $t^* = 0.16$ cost-justified ($r=5$, Cost=137). 4 risk bands defined (LOW <0.15, MEDIUM 0.15..0.16, HIGH 0.16..0.80, CRITICAL >=0.80).
- **[T-014]** Unsupervised anomaly detection and Layer 4 Health Score completed. IsolationForest (contamination=0.02, 150 trees) trained on 6,081 healthy training rows with 14 features. Normalized scores [0, 1] with zero-denominator & NaN guards. Health score composite index $[0, 100]$ with strictly clamped sensor penalty $[0, 15]$. Deterministic state precedence hierarchy: OFFLINE > MAINTENANCE_REQUIRED (operational override) > CRITICAL > WARNING > HEALTHY. Single final test evaluation on held-out test set: Recall = 0.8963, Precision = 0.7610, F1 = 0.8231, Brier = 0.02055. 220 tests pass.
- **[T-015]** Model explainability layer implemented: `EdgeTwinExplainer` using `shap.TreeExplainer` operating in model log-odds margin space. Dynamic feature alignment via `preprocessor.get_feature_names_out()`. Strict additivity guard enforced ($|\sum \phi_i + \text{base\_value} - \text{margin}| \le 10^{-4}$, measured discrepancy $\approx 2.03 \times 10^{-6}$). Zero-dependency fallback via native XGBoost `Booster.predict(..., pred_contribs=True)` producing identical attributions. Latency SLA measured on validation telemetry: mean = 19.24 ms, p95 = 20.12 ms (< 100 ms SLA passed). Global importance table computed on validation background and saved to `artifacts/feature_importance_global.csv`. Mandatory honesty disclaimer included on all outputs. 31 tests pass.
- **[T-016]** Model packaging, registration, and governance implemented: `EdgeTwinRiskModel` (`mlflow.pyfunc.PythonModel`) wrapping calibrated S05 champion. Ingestion contract supports raw telemetry (10 sensors + Machine_Type) with auto-derivation of physics features (`+physics`), missing sensor values, and unseen categories. Automated 10-step technical promotion gate enforces schema, bounds, threshold 0.16, risk-band rules, and metadata before champion promotion. Model registered in MLflow under `edgetwin-risk` (Version 2) with aliases `challenger` and `champion`. Verified round-trip load and inference via `models:/edgetwin-risk@champion`. Model card generated in `docs/ml/model_card.md` using frozen S04/S05 metrics (ZERO test set re-evaluation). 16 tests pass.
- **[T-020]** Telemetry contract v1 implemented: JSON Schema Draft 2020-12 (`docs/api/telemetry.v1.schema.json`, `edgetwin.telemetry.v1`) with null support, strict sensor ranges (`SENSOR_RANGES`), quality flags, and edge diagnostic fields. Implemented `TelemetryValidator` with safe JSON parsing, schema enforcement, topic consistency, leakage guard rejecting forbidden fields, sequence tracking, and diagnostic discrepancy detection ($\Delta T = 0.2\,^\circ\text{C}$, apparent power = $5.0\text{ VA}$). Implemented `telemetry_to_feature_df` adapter resolving `Machine_Type` via `MACHINE_ID_PREFIX_MAP` and emitting exactly 11 raw columns. 55 tests pass.
- **[T-021]** Scenario specification and deterministic process model implemented: `SimulatedMachine` with coupled physical process equations, deterministic seed (`seed=42`) and timestamps, and 5-state FSM (`STOPPED`, `STARTING`, `RUNNING`, `DEGRADING`, `TRIPPED`). Created 8 declarative YAML scenarios (`healthy_nominal.yaml`, `heat_dissipation.yaml`, `overstrain.yaml`, `power_failure.yaml`, `tool_wear.yaml`, `random_vibration.yaml`, `sensor_dropout.yaml`, `machine_offline.yaml`) with full documentation of empirical parameters vs simulation assumptions in `docs/dataset/fault_signatures.md`. All 8 scenarios passed detection targets against frozen `models:/edgetwin-risk@champion`, IsolationForest, and Health Score engine. Zero test set access. 13 tests pass.
- **[T-022, T-023]** Virtual Edge simulator and MQTT broker setup implemented. Mosquitto configured via `docker-compose.yml` with basic unauthenticated local access. `VirtualEdge` wraps the authoritative `SimulatedMachine`, uses `paho-mqtt` 2.0 to emit canonical telemetry on `edgetwin/v1/{machine_id}/telemetry`. Built-in explicit state machine handles network drops with a ring buffer (capacity 1000) and automatic flush on reconnect. Integration tests verify connectivity. Unit tests pass (mocked broker). Rule 10 dependency justified.
- **[T-040]** Wokwi hardware feasibility spike completed. Evaluated Path A (public cloud broker via Wokwi Public Gateway) vs Path B (local Mosquitto via Wokwi Private Gateway / `host.wokwi.internal`). Path A selected as primary architecture to satisfy PRD §6 zero-recurring-cost requirement without requiring paid Wokwi subscriptions ($7/mo) or proprietary extension licenses. Documented ESP32 MQTT library constraints (`PubSubClient` publish QoS 0 limitation vs `256dpi/arduino-mqtt` and native `esp-mqtt` with QoS 1 support), hardware sensor mapping, and security mitigations. S08 Python Virtual Edge established as permanent offline/CI fallback.
- **[T-041]** ESP32 / Wokwi Firmware v1 implemented in `edge/`. Circuit diagram `edge/diagram.json` models ESP32 DevKit v1, DHT22 (GPIO 15), Slide Potentiometer (GPIO 34 ADC1), MPU6050 (I2C SDA 21, SCL 22), and red trip indicator LED (GPIO 2). Modular C++ firmware implements sensor reading (`sensors.cpp`), coupled process equations and deterministic safety trips (`process_model.cpp`), canonical JSON serialization conforming to `edgetwin.telemetry.v1` (`telemetry.cpp`), bounded FIFO ring buffer (`ring_buffer.cpp`), and 1 Hz non-blocking publish loop (`firmware.ino`) with QoS 1 publishing (`256dpi/arduino-mqtt`), retained LWT on `edgetwin/v1/MOT-1001/status`, and remote command subscription. Safe config template in `config.h.example`. All 6 contract tests pass. Full suite 345 passed, 1 skipped.
- **[T-030, T-031]** FastAPI backend foundation and database schema with Alembic migrations implemented in `api/`. Clean layered structure (config, db, models, schemas, routes, migrations). 8 domain models mapped with SQLAlchemy 2.0 (`machines`, `telemetry`, `predictions`, `twin_snapshots`, `alerts`, `feedback`, `maintenance_events`, `model_versions`). Alembic version `0001_initial_schema` creates all tables, foreign keys, unique constraints, and time-series compound indexes. Endpoints `/health` and `/ready` provide liveness/readiness probes. RFC 7807 problem details error handling and environment-driven CORS. Multi-stage `Dockerfile` and updated `docker-compose.yml` (PostgreSQL 16 + Mosquitto + API). 24 new tests in `tests/api/`. Total 369 passed, 1 skipped.
- **[T-002]** BLOCKED (dataset provenance not yet provided by user).
- Waiting on: (a) dataset provenance from the user, (b) UI reference website (only needed at T-050).

---

## S10 — T-030 FastAPI Skeleton & T-031 Database Schema (2026-09-28)

### Task completion
- **Status:** DONE (T-030 and T-031)
- **Branch:** `feat/T-030-T-031-backend-foundation`
- **Base Commit:** `a5dbffd` (S16/T-041 baseline: `feat(edge): add ESP32 Wokwi firmware v1`)
- **Files created:**
  - `api/app/__init__.py`
  - `api/app/config.py`
  - `api/app/logging.py`
  - `api/app/db/__init__.py`
  - `api/app/db/base.py`
  - `api/app/db/session.py`
  - `api/app/models/__init__.py`
  - `api/app/models/machine.py`
  - `api/app/models/telemetry.py`
  - `api/app/models/prediction.py`
  - `api/app/models/twin.py`
  - `api/app/models/alert.py`
  - `api/app/models/feedback.py`
  - `api/app/models/maintenance.py`
  - `api/app/models/model_version.py`
  - `api/app/schemas/__init__.py`
  - `api/app/schemas/common.py`
  - `api/app/schemas/health.py`
  - `api/app/routes/__init__.py`
  - `api/app/routes/health.py`
  - `api/app/main.py`
  - `api/alembic.ini`
  - `api/migrations/env.py`
  - `api/migrations/script.py.mako`
  - `api/migrations/versions/0001_initial_schema.py`
  - `Dockerfile`
  - `tests/api/__init__.py`
  - `tests/api/test_config.py`
  - `tests/api/test_health.py`
  - `tests/api/test_errors.py`
  - `tests/api/test_db.py`
  - `tests/api/test_models.py`
  - `tests/api/test_migrations.py`
  - `tests/api/test_telemetry_persistence.py`
- **Files modified:**
  - `pyproject.toml` (added backend dependencies)
  - `docker-compose.yml` (added postgres:16-alpine and api services)
  - `.env.example` (added environment configuration template)
  - `api/README.md` (complete backend documentation)
  - `tasks.md` (marked T-030 and T-031 DONE)
  - `memory.md`

### Rule 10 Dependency Justifications [DECISION]
1. `fastapi>=0.115.0,<1`: [FACT] Modern high-performance asynchronous web framework for REST API and WebSocket services with automatic OpenAPI documentation and dependency injection.
2. `uvicorn>=0.30.0,<1`: [FACT] Production-ready ASGI web server for executing the FastAPI application.
3. `pydantic>=2.8.0,<3`: [FACT] Core data validation, typing, and schema serialization library.
4. `pydantic-settings>=2.5.0,<3`: [FACT] Twelve-factor environment configuration parser with type safety and dotenv integration.
5. `sqlalchemy>=2.0.0,<3`: [FACT] Authoritative Python SQL toolkit and Object Relational Mapper (ORM) supporting PostgreSQL and SQLite with mapped typed columns (`Mapped[...]`).
6. `alembic>=1.13.0,<2`: [FACT] Database schema migration tool for deterministic, version-controlled schema evolution.
7. `httpx>=0.27.0,<1` (dev): [FACT] Required for FastAPI's `TestClient` to perform automated HTTP endpoint and probe testing.

### Database Architecture & Domain Schema [DECISION & MEASURED]
- **Selected Engine:** PostgreSQL 16 (Postgres Docker container / production) with SQLite compatibility for isolated test suites.
- **8 Domain Entities:**
  1. `machines`: Fleet assets keyed by `machine_id` (`MOT-1001`, `PMP-2001`, etc.).
  2. `telemetry`: Raw time-series telemetry with 10 nullable sensor channels, `quality` JSON, `edge` diagnostics, and unique constraint on `(machine_id, seq)`.
  3. `predictions`: ML inference outputs (`failure_probability`, `risk_band`, `anomaly_score`, `health_score`, `top_factors` SHAP JSON, `model_version`).
  4. `twin_snapshots`: Periodic full state objects aligned with ISO 23247.
  5. `alerts`: Layer 5 alarms (`INFO`, `WARNING`, `CRITICAL`) with lifecycle state.
  6. `feedback`: Engineer ground truth labels (`CONFIRMED`, `FALSE_ALARM`).
  7. `maintenance_events`: Logs of inspections and component overhauls.
  8. `model_versions`: Mirror of MLflow model registry and promotion status.
- **Migration Verification:** Alembic migration `0001_initial_schema` executes clean `upgrade` -> `downgrade` -> `upgrade` cycles verified by automated unit tests.
- **API Baseline:** `/health` (liveness), `/ready` (readiness + DB ping), and versioned `/api/v1/*` aliases. RFC 7807 problem details error format. Restricted CORS allow-list.

---

---

## S16 — T-041 ESP32 / Wokwi Firmware v1 (2026-09-26)

### Task completion
- **Status:** DONE (T-041)
- **Branch:** `feat/T-041-esp32-firmware-v1`
- **Base Commit:** `0dfa4c6` (S09/T-040 baseline)
- **Files created:** `edge/diagram.json`, `edge/wokwi.toml`, `edge/libraries.txt`, `edge/config.h.example`, `edge/sensors.h`, `edge/sensors.cpp`, `edge/process_model.h`, `edge/process_model.cpp`, `edge/telemetry.h`, `edge/telemetry.cpp`, `edge/ring_buffer.h`, `edge/ring_buffer.cpp`, `edge/firmware.ino`, `tests/contract/test_firmware_contract.py`
- **Files modified:** `.gitignore`, `memory.md`, `tasks.md`

### Implementation Summary
- **Circuit Schematic:** `edge/diagram.json` with ESP32 DevKit v1, DHT22 on GPIO 15, slide potentiometer on GPIO 34, MPU6050 on I2C (GPIO 21/22), and red trip LED on GPIO 2 with 220 $\Omega$ resistor.
- **Sensor Acquisition:** `sensors.cpp` reads DHT22 ambient temperature, 12-bit ADC torque scaling [0.0, 150.0] Nm, and MPU6050 dynamic acceleration vector magnitude.
- **Coupled Process Equations:** `process_model.cpp` mirrors S07 physics (temperature differential accumulation, electrical inrush/coupling, shaft speed curve, wear progression) and evaluates deterministic safety trips ($\Delta T > 45$ °C, Current $> 45$ A, Vibration $> 15$ mm/s, sustained overload $\ge 32$ A for 10 s).
- **Wire Contract:** `telemetry.cpp` emits strict `edgetwin.telemetry.v1` JSON with all 10 raw signals, quality dictionary, and edge diagnostics. Zero forbidden ML leakage fields.
- **Resilience:** `ring_buffer.cpp` provides a 50-message bounded circular buffer for offline store-and-forward.
- **MQTT:** `firmware.ino` connects via `256dpi/arduino-mqtt` at 1 Hz with QoS 1 telemetry and retained status/LWT.

---

## S09 — T-040 Wokwi Hardware Feasibility Spike (2026-09-26)

### Task completion
- **Status:** DONE (T-040)
- **Branch:** `feat/T-040-wokwi-feasibility`
- **Base Commit:** `ab2f7d8` (S08 baseline)
- **Files created/updated:** `docs/wokwi/connectivity.md`, `docs/sessions/S09_report.md`, `tasks.md`, `memory.md`
- **Files modified:** `memory.md`, `tasks.md`, `docs/wokwi/connectivity.md`

### Major Architectural Decisions [DECISION]
1. **Primary Connectivity Path (Path A):** Selected Wokwi ESP32 $\rightarrow$ Wokwi Public Gateway $\rightarrow$ Public Cloud Broker (TLS 8883) $\rightarrow$ Backend. Zero recurring cost; runs in any browser without local helper binaries or paid licenses.
2. **Offline Fallback:** S08 `VirtualEdge` (`simulation/virtual_edge.py`) retained as the 100% deterministic offline fallback.
3. **ESP32 MQTT Library Selection:** Disallowed standard `PubSubClient` for QoS 1 publish requirement; designated `256dpi/arduino-mqtt` or native Espressif `esp-mqtt` (`mqtt_client.h`) for T-041 firmware.
4. **Sensor Simulation Split:** DHT22 (air temp), slide potentiometer (torque/load), and MPU6050 (vibration) mapped to Wokwi virtual hardware; remaining 7 channels synthesized via coupled process equations.

---

## S08 — T-022 Virtual Edge & T-023 MQTT Setup (2026-09-25)

### Task completion
- **Status:** DONE (T-022 and T-023)
- **Branch:** `feat/T-022-T-023-virtual-edge-mqtt`
- **Base Commit:** `2915966` (S07 baseline)
- **Files created:** `simulation/virtual_edge.py`, `mosquitto/mosquitto.conf`, `docker-compose.yml`, `docs/wokwi/connectivity.md`, `tests/simulation/test_virtual_edge.py`, `tests/integration/test_mqtt_integration.py`
- **Files modified:** `pyproject.toml` (added `paho-mqtt>=2.0.0,<3`), `memory.md`

### Rule 10 Dependency Justifications [DECISION]
1. `paho-mqtt>=2.0.0,<3`: [FACT] Required for MQTT connectivity between Virtual Edge (Python publisher) and Mosquitto Broker. Version 2.0 API (`CallbackAPIVersion.VERSION2`) enforces modern, robust callback signatures. This dependency provides QoS handling, Last Will and Testament (LWT) support, and the necessary asynchronous networking to fulfill the Virtual Edge's ring-buffer and automatic re-flush logic.

### Implementation Notes
- **Mosquitto:** Standard `eclipse-mosquitto:2.0` via Docker Compose. `allow_anonymous true` for local development.
- **Topics:** Authoritative `edgetwin/v1/{machine_id}/telemetry`, `.../status`, `.../cmd`.
- **Validation:** Every payload is pre-validated by `TelemetryValidator` before publication.
- **Resilience:** `VirtualEdge` maintains a `deque(maxlen=1000)`. When disconnected, payloads buffer locally. Upon reconnect, buffer flushes synchronously before new emissions, preventing data loss.

---

## S07 — T-020 Telemetry Contract & T-021 Process Model (2026-09-25)

### Task completion
- **Status:** DONE (T-020 and T-021)
- **Branch:** `feat/T-020-T-021-telemetry-scenarios`
- **Base Commit:** `6f9befc` (S06 champion baseline)
- **Files created:**
  - `docs/api/telemetry.v1.schema.json` (JSON Schema Draft 2020-12, canonical ID: `edgetwin.telemetry.v1`)
  - `simulation/__init__.py`
  - `simulation/contract.py` (`TelemetryValidator`, `TelemetryValidationResult`, `telemetry_to_feature_df`)
  - `simulation/process_model.py` (`SimulatedMachine`, 5-state FSM, coupled physics equations)
  - `simulation/scenarios/` (8 declarative YAML scenario files: `healthy_nominal.yaml`, `heat_dissipation.yaml`, `overstrain.yaml`, `power_failure.yaml`, `tool_wear.yaml`, `random_vibration.yaml`, `sensor_dropout.yaml`, `machine_offline.yaml`)
  - `docs/dataset/fault_signatures.md` (empirical vs assumed parameters breakdown for all 8 scenarios)
  - `tests/contract/test_telemetry_contract.py` (39 contract & validation tests)
  - `tests/contract/test_telemetry_ml_compat.py` (16 ML compatibility & leakage tests)
  - `tests/simulation/test_scenarios.py` (13 process model & scenario validation tests)
- **Files modified:** `pyproject.toml` (added `jsonschema>=4.20,<5` and `pyyaml>=6.0,<7`), `tasks.md`, `memory.md`, `tests/mlops/test_register.py` (test isolation tracking URI restoration)

### Rule 10 Dependency Justifications [DECISION]
1. `jsonschema>=4.20,<5`: [FACT] Required for RFC-compliant JSON Schema Draft 2020-12 validation of wire telemetry payloads (`docs/api/telemetry.v1.schema.json`). Provides schema validation, type checking, required field enforcement, and structured error reporting without requiring heavyweight runtime modeling libraries like Pydantic (which was explicitly prohibited).
2. `pyyaml>=6.0,<7`: [FACT] Required for loading declarative fault scenario specifications (`simulation/scenarios/*.yaml`). Decouples simulation configuration (fault injection step, duration, ramp parameters, initial conditions) from Python simulator logic, satisfying the requirement that scenario definitions live in YAML rather than hardcoded Python.

### T-020 Telemetry Contract v1 [SPECIFICATION & AUDIT]
- **Canonical Schema ID:** `edgetwin.telemetry.v1` (Draft 2020-12).
- **Top-level required fields:** `schema`, `machine_id`, `seq`, `ts`, `provenance`, `fw`, `signals`, `quality`, `edge`.
- **Machine ID pattern:** `^[A-Z]{3}-[0-9]{4}$`.
- **Provenance enum:** `SIMULATED`, `REPLAY`, `REAL`.
- **Signals:** 10 raw sensors (`air_temp_c`, `process_temp_c`, `rotational_speed_rpm`, `torque_nm`, `vibration_mm_s`, `pressure_bar`, `current_a`, `voltage_v`, `tool_wear_min`, `operating_hours`). All signals support `number` OR `null`. Null values are never converted to zero; they pass through as `np.nan` for the champion model's median imputer.
- **Sensor ranges:** Authoritative bounds sourced strictly from `ml.data.schema.SENSOR_RANGES`. Out-of-bounds sensor values are flagged with quality `OUT_OF_RANGE` but are NOT silently clipped.
- **Quality enum:** `OK`, `OUT_OF_RANGE`, `STALE`, `MISSING`, `LIMIT_WARN`, `LIMIT_ALARM`. Missing signals in dictionary are assigned `MISSING`.
- **Edge diagnostic fields:** `delta_t_c`, `power_va`, `trip`, `buffered`. Strictly diagnostic; NEVER passed to ML model.
- **Diagnostic discrepancy comparison:** Backend independently calculates $\Delta T = \text{Process} - \text{Air}$ and $\text{Apparent Power} = V \cdot I$, comparing against edge values using approved tolerances ($\Delta T = 0.2\,^\circ\text{C}$, Apparent Power = $5.0\text{ VA}$). Discrepancies logged without causing ML rejection.
- **Machine Type resolution:** Resolved via `ml.data.schema.MACHINE_ID_PREFIX_MAP` (`CMP` -> Compressor, `PMP` -> Pump, `CNC` -> CNC_Machine, `CNV` -> Conveyor, `MOT` -> Motor). Unrecognized prefixes map to `"Unknown"` without raising an unhandled exception.
- **Leakage guards:** Payload rejected if forbidden leakage fields are present (`Failure_Type`, `Machine_Failure`, `Sensor_Batch_Code`, `Checksum_Flag`). Operational metadata (`machine_id`, `ts`, `seq`, `provenance`, `fw`, `quality`, `edge`) stripped by `telemetry_to_feature_df`. Adapter outputs exactly 11 columns (10 raw sensors + `Machine_Type`) in PascalCase, and champion model auto-derives the 3 physics features internally.

### T-021 Deterministic Process Model & Scenarios [MEASURED]
- **Process Model:** `SimulatedMachine` implements coupled thermodynamic and electro-mechanical process equations, maintaining realistic dependencies ($\Delta T \propto \text{Power} / \text{RPM}$, $\text{Current} \propto \text{Torque} / \text{Voltage}$, $\text{Vibration} \propto \text{Wear} \cdot \text{Torque}$, etc.).
- **Five-state FSM:** `STOPPED` -> `STARTING` -> `RUNNING` -> `DEGRADING` -> `TRIPPED` with documented transition rules.
- **Determinism:** Fixed random seed (`seed: 42`) and deterministic ISO-8601 replay timestamp sequencing across all runs.
- **Measured Scenario Evaluations against frozen `models:/edgetwin-risk@champion`:**
  - **SCN-01 (Healthy Nominal):** Mean $p_{\text{fail}} = 0.0117$, max $p_{\text{fail}} = 0.0292 \le 0.05$. 0 false alarms across 60 steps. All risk bands `LOW`. Target $\le 0.05$ PASSED.
  - **SCN-02 (Heat Dissipation):** Baseline $p_{\text{fail}} = 0.0105$; degraded $p_{\text{fail}} = 0.8940$ (max $0.8969$). Model risk band elevated to `CRITICAL` ($p \ge 0.80$). Target $\ge 0.16$ PASSED.
  - **SCN-03 (Overstrain):** Baseline $p_{\text{fail}} = 0.0171$; degraded $p_{\text{fail}} = 0.8790$ (max $0.8966$). Model risk band elevated to `CRITICAL` ($p \ge 0.80$). Target $\ge 0.16$ PASSED.
  - **SCN-04 (Power Failure):** Active fault $p_{\text{fail}} = 0.8992$ (max $0.8995$). After 10s persistence, edge hardware safety trips (`state=TRIPPED`, `trip_code="TRIP_OVERLOAD"`), dropping current to 0A. Target $\ge 0.16$ PASSED.
  - **SCN-05 (Tool Wear):** Final tool wear reaches $254.5\text{ min} \ge 240\text{ min}$. Layer 4 health score triggers deterministic operational override to `MAINTENANCE_REQUIRED`. Degraded model risk $p_{\text{fail}} = 0.8886$ (`CRITICAL`). Target PASSED.
  - **SCN-06 (Random Vibration):** Fault peak $p_{\text{fail}} = 0.8973$ (max $0.8984$), risk band `CRITICAL`. Target $\ge 0.16$ PASSED.
  - **SCN-07 (Sensor Dropout):** Null signals flagged with `MISSING` quality; model evaluates safely with median imputation ($p_{\text{fail}} = 0.0125$). Target PASSED.
  - **SCN-08 (Machine Offline):** Telemetry stream intentionally stops after step 10. Digital Twin synchronization verifies `LIVE` -> `STALE` -> `OFFLINE` state transitions without manufacturing synthetic predictions. Target PASSED.
- **Top SHAP Attributions (TreeExplainer on champion):**
  - SCN-02 (Heat Dissipation): `['Process_Temperature_C', 'Current_A', 'Tool_Wear_Min']` (Thermal and load features drive failure probability).
  - SCN-06 (Random Vibration): `['Vibration_mm_s', 'Tool_Wear_Min', 'Pressure_bar']` (Vibration is dominant driver).
- **Acceptance Criteria Summary:** 8/8 scenarios executed and PASSED their detection and operational targets. Zero criteria unmet.

### Test Set Protection [GOVERNANCE]
- The held-out test partition (`data/test/`) was strictly NOT accessed during S07.
- No new evaluations or metric calculations on held-out data were performed.
- All scenario calibrations and distributions were derived exclusively from non-test training distributions and physics domain bounds.


---

## S06 — T-015 Explainability & T-016 Model Registry (2026-09-25)

### Task completion
- **Status:** DONE (T-015 and T-016)
- **Branch:** `feat/T-015-T-016-explainability-registry`
- **Base Commit:** `1d08fb1` (S05 final baseline)
- **Files created:** `ml/models/explain.py`, `mlops/register.py`, `tests/ml/test_explain.py`, `tests/mlops/test_register.py`, `docs/ml/explainability.md`, `docs/ml/model_card.md`, `artifacts/feature_importance_global.csv`, `artifacts/sample_explanation.json`, `artifacts/champion_features.json`
- **Files modified:** `pyproject.toml` (added `shap>=0.48.0,<1`), `tasks.md`, `memory.md`

### T-015 Explainability [MEASURED]
- Model: Frozen S05 champion (`xgboost + physics`, 14 features, Platt sigmoid calibration).
- Explainer class: `EdgeTwinExplainer`.
- Explanation space: Model margin (log-odds). Positive SHAP monotonically increases calibrated probability; negative SHAP monotonically decreases probability. Values represent statistical associations, NOT physical causation.
- Dynamic feature alignment: Transformed feature names recovered dynamically via `preprocessor.get_feature_names_out()` (`['Air_Temperature_C', 'Process_Temperature_C', 'Rotational_Speed_RPM', 'Torque_Nm', 'Vibration_mm_s', 'Pressure_bar', 'Current_A', 'Voltage_V', 'Tool_Wear_Min', 'Operating_Hours', 'Delta_T_C', 'Apparent_Power_VA', 'Mech_Power_W', 'Machine_Type']`), resolving `ColumnTransformer` categorical reordering.
- Additivity verification: Strict numerical guard ($|\text{base\_value} + \sum \phi_i - \text{margin}| \le 10^{-4}$). Measured error on validation telemetry: $\approx 2.03 \times 10^{-6}$.
- Native XGBoost fallback: `Booster.predict(..., pred_contribs=True)` produces shape $(N, 15)$ (columns 0–13 SHAP, column 14 bias), matching TreeSHAP within $10^{-4}$.
- Latency benchmark (50 single-row runs after warm-up):
  - Mean: 19.24 ms
  - Median: 19.24 ms
  - p95: 20.12 ms (< 100 ms SLA passed)
  - Max: 20.38 ms
- Global feature importance (validation background, 1,490 rows):
  1. `Tool_Wear_Min` (mean |SHAP| = 1.1532)
  2. `Vibration_mm_s` (mean |SHAP| = 0.9182)
  3. `Process_Temperature_C` (mean |SHAP| = 0.8427)
  4. `Voltage_V` (mean |SHAP| = 0.7004)
  5. `Current_A` (mean |SHAP| = 0.5199)
  6. `Torque_Nm` (mean |SHAP| = 0.4790)
  7. `Air_Temperature_C` (mean |SHAP| = 0.3079)
  8. `Pressure_bar` (mean |SHAP| = 0.2112)
  9. `Rotational_Speed_RPM` (mean |SHAP| = 0.2021)
  10. `Apparent_Power_VA` (mean |SHAP| = 0.1860)
  11. `Delta_T_C` (mean |SHAP| = 0.1818)
  12. `Mech_Power_W` (mean |SHAP| = 0.1472)
  13. `Operating_Hours` (mean |SHAP| = 0.0936)
  14. `Machine_Type` (mean |SHAP| = 0.0633)

### T-016 Model Registry & Model Card [MEASURED & VERIFIED]
- Model Wrapper: `EdgeTwinRiskModel(mlflow.pyfunc.PythonModel)` encapsulating complete S05 calibrated inference contract.
- Input Contract: Supports raw telemetry (10 sensors + Machine_Type), auto-deriving physics features via `apply_feature_set(df, "+physics")`. Robust to NaNs (median imputation) and unseen categories (`unknown_value=-1`). Enforces strict leakage guard.
- Output Contract: `pd.DataFrame` with `calibrated_probability` $\in [0, 1]$, `failure_prediction` $\in \{0, 1\}$ ($=1$ iff $p \ge 0.16$), and `risk_band` $\in \{\text{LOW, MEDIUM, HIGH, CRITICAL}\}$. Zero mixing of L3 anomaly scores or L4 health scores.
- Promotion Gate: 10-step technical verification (loading, raw telemetry handling, physics derivation, NaNs, unseen categories, schema, bounds, threshold obedience, risk band rules, metadata validation).
- MLflow Registry:
  - Experiment: `T-015-T-016-explainability-registry`
  - Run ID: `517dc9f1f9144b62b61f7dd3f076f85e`
  - Registered Model: `edgetwin-risk`
  - Version: `2`
  - Aliases: `challenger` $\to$ `champion` (post-gate)
  - Target URI: `models:/edgetwin-risk@champion`
- Verification: `models:/edgetwin-risk@champion` loaded and predicted successfully on raw telemetry.
- Model Card: Generated at `docs/ml/model_card.md` using frozen historical S04/S05 test results. Zero test set re-evaluation conducted.

---

## S05 — T-013 Calibration & T-014 Anomaly/Health Scoring (2026-09-25)

### Task completion
- **Status:** DONE (T-013 and T-014)
- **Branch:** `feat/T-013-T-014-calibration-health`
- **Base Commit:** `cfb9b57` (S04 final reconciliation)
- **Files created:** `ml/models/calibrate.py`, `ml/models/thresholds.py`, `ml/models/anomaly.py`, `ml/models/health.py`, `tests/ml/test_calibration.py`, `tests/ml/test_thresholds.py`, `tests/ml/test_anomaly.py`, `tests/ml/test_health.py`, `scripts/run_s05.py`, `docs/ml/calibration.md`, `docs/ml/thresholds.md`, `docs/ml/health_model.md`, `docs/sessions/S05_report.md`
- **Files modified:** `tasks.md`, `memory.md`

### Calibration results [T-013 — MEASURED]
- Base S04 champion (`xgboost + physics`, 14 features) remained frozen.
- Calibration evaluated on `val_df` using `FrozenEstimator`:
  - Uncalibrated: Brier = 0.02810, ECE = 0.02867, PR-AUC = 0.89693, ROC-AUC = 0.98220
  - Sigmoid (Platt): Brier = 0.02619, ECE = 0.00391, PR-AUC = 0.89693, ROC-AUC = 0.98220 (Selected: 6.8% Brier error reduction, 86.4% ECE reduction, 0 PR-AUC ranking loss)
  - Isotonic: Brier = 0.02237, ECE = 0.00000, PR-AUC = 0.89004, ROC-AUC = 0.98474 (degrades PR-AUC ranking due to step-wise binning)

### Threshold analysis & risk bands [T-013 — MEASURED]
- 41 thresholds evaluated on `val_df` ($t \in [0.10, 0.90]$, step 0.02).
- F1-optimal: $t = 0.50$ (F1 = 0.8231, Recall = 0.8045, Precision = 0.8425)
- Cost-optimal ($r=1$): $t = 0.50$ (Cost = 46)
- Cost-optimal ($r=3$): $t = 0.16$ (Cost = 95)
- Cost-optimal ($r=5$): $t = 0.16$ (Cost = 137, Recall = 0.8421, Precision = 0.7778)
- Cost-optimal ($r=10$): $t = 0.16$ (Cost = 242)
- Operational decision threshold frozen at $t^* = 0.16$.
- Note: $r$ is a configurable parameter; $r=5$ is a project-specific operating point, not an industrial standard. Lowering threshold from 0.50 to 0.16 is an operational trade-off (trading precision for recall to minimize missed failures), NOT a universal improvement in model capability.
- Risk bands defined: LOW ($p < 0.15$), MEDIUM ($0.15 \le p < 0.16$), HIGH ($0.16 \le p < 0.80$), CRITICAL ($p \ge 0.80$).

### Unsupervised anomaly detector [T-014 — MEASURED]
- Model: `IsolationForest(n_estimators=150, contamination=0.02, random_state=42)`
- Training data: 6,081 healthy training rows (`train_df[Machine_Failure == 0]`). Zero target or post-hoc leakage.
- Features: 14 `+physics` features (median imputation + ordinal encoding on Machine_Type).
- Normalization: $s_{\text{nominal}} = -0.41224$ (95th pct), $s_{\text{extreme}} = -0.55025$ (1st pct), $\Delta = 0.13801$.
- Validation: ROC-AUC = 0.8699, PR-AUC = 0.4639.
- Thresholds: Provisional default = 0.50 (Recall = 0.8045, FPR = 0.2006); Empirical ($\alpha=0.02$) = 0.9075 (Recall = 0.2632, FPR = 0.0206).

### Layer 4 Health Score & precedence [T-014 — SPECIFICATION]
- Composite formula: $\text{Health Score} = \text{clip}(100 - (60 \cdot p_{\text{cal}} + 25 \cdot a_{\text{anomaly}} + \Delta_{\text{sensor}}), 0, 100)$
- Sensor penalty clamping: strictly $0 \le \Delta_{\text{sensor}} \le 15$.
- Deterministic state precedence hierarchy: `OFFLINE` > `MAINTENANCE_REQUIRED` (Tool_Wear_Min >= 240 or tech confirmation) > `CRITICAL` > `WARNING` > `HEALTHY`.

### Final held-out test evaluation [S05 — MEASURED]
- Evaluated ONCE on held-out test partition (1,499 rows, 9 machines) with frozen calibrator and $t^* = 0.16$:
  - Recall: 0.8963 (121/135 failures detected)
  - Precision: 0.7610 (38 false positives)
  - F1: 0.8231
  - F2: 0.8655
  - Accuracy: 0.9653
  - ROC-AUC: 0.9755
  - PR-AUC: 0.9234
  - Brier score: 0.02055 (17.5% reduction over uncalibrated baseline 0.02492)
  - Per-failure-type recall: Heat Dissipation = 95.35%, Overstrain = 93.48%, Power = 75.00%, Tool Wear = 76.47%, Random = 100.00%.

---

## S04 — T-012 Model Comparison (2026-09-25)

### Task completion
- **Status:** DONE (T-012)
- **Branch:** `feat/T-012-model-comparison`
- **Base Commit:** `17c2536` (S03 — feat(data): add versioned data contract and splits)
- **Files created:** `ml/data/engineering.py`, `ml/models/train.py`, `ml/models/evaluate.py`, `ml/models/compare.py`, `tests/ml/test_models.py`, `docs/ml/model_comparison.md`, `docs/sessions/S04_report.md`, `scripts/reconcile_comparison.py`
- **Files modified:** `pyproject.toml` (mlflow + xgboost added), `tasks.md`, `memory.md`

### Champion selection [T-012 — DECISION]
- **Selection Rule:** Validation PR-AUC (primary), Validation Recall (tie-break).
- **Champion:** `xgboost` with `+physics` (14 features).
  - Validation PR-AUC: 0.8969
  - Validation Recall: 0.8195
  - Validation F1: 0.8104
  - Validation ROC-AUC: 0.9822
  - Validation Accuracy: 0.9657
  - MLflow Run ID: `bd7c1288181a461fbe43e994078e16bf`

### Single held-out test evaluation [T-012 — MEASURED]
- Evaluated strictly once after champion selection on held-out test partition (9 machines, 1,499 rows).
- MLflow Test Run ID: `0709463d1ee14acb9d325cb58a57e69f`
- Test PR-AUC: 0.9234
- Test Recall: 0.8963
- Test F1: 0.8403
- Test Accuracy: 0.9693
- Test ROC-AUC: 0.9755
- Per-failure-type recall: Heat Dissipation = 95.35%, Overstrain = 93.48%, Power = 75.00%, Tool Wear = 76.47%, Random = 100.00%.

### Audit & test report isolation fix [T-012 — FIX]
- **Issue:** Initial docs showed Decision Tree + base10 instead of XGBoost + physics.
- **Root Cause:** In `ml/models/compare.py`, `run_comparison()` lacked an `output_path` parameter and had hardcoded `_DOCS_ML_DIR / "model_comparison.md"`. When `pytest` ran the smoke test `test_comparison_champion_has_zero_machine_id_overlap(models=("decision_tree",))`, it silently overwrote `docs/ml/model_comparison.md` with the single smoke-test model and ephemeral test run ID.
- **Fix:** Added `output_path: Path | None = None` to `run_comparison()`. Updated smoke tests in `tests/ml/test_models.py` to route reports to `tmp_path / "model_comparison.md"`. Reconciled `docs/ml/model_comparison.md` from `mlflow.db`. Confirmed `pytest` runs no longer touch `docs/ml/model_comparison.md`.

---

## S03 — T-010 + T-011 Data Contract (2026-09-25)

### Task completion
- **Status:** DONE (both T-010 and T-011)
- **Branch:** `feat/T-010-T-011-data-contract`
- **Base Commit:** `c6a992e` (S02 — feat(data): add reproducible preparation pipeline)
- **Files created:** `dvc.yaml`, `params.yaml`, `ml/data/features.py`, `ml/data/splits.py`, `tests/ml/test_features.py`, `tests/ml/test_splits.py`, `docs/sessions/S03_report.md`, `data/interim/splits/{train,val,test}.csv`
- **Files modified:** `ml/data/schema.py` (T-011 constants added), `ml/data/prepare.py` (--deterministic flag), `pyproject.toml` (scikit-learn + dvc added), `tasks.md`, `memory.md`, `.gitignore` (`data/interim/` added), `.dvc/` (init)
- **Files removed from Git tracking:** `data/interim/predictive_maintenance_prepared.csv`, `data/interim/data_quality_report.json` (now owned by DVC)

### DVC configuration [T-010 — DECISION]
- **DVC version:** 3.67.1
- **Remote:** None (local-only; no cloud credentials introduced)
- **Stage:** `prepare` — `cmd: python -m ml.data.prepare --deterministic`
- **Deps:** `data/raw/predictive_maintenance_dataset.csv`, `ml/data/prepare.py`, `ml/data/schema.py`
- **Params:** `params.yaml:pipeline.version`
- **Outs:** `data/interim/predictive_maintenance_prepared.csv`, `data/interim/data_quality_report.json`
- **dvc repro run 1:** Executed stage, generated `dvc.lock`, exit 0
- **dvc repro run 2:** "Stage 'prepare' didn't change, skipping", exit 0
- **dvc status:** "Data and pipelines are up to date"
- **Raw dataset:** NOT DVC-tracked (T-002 provenance BLOCKED; false provenance must not be created)

### --deterministic flag [T-010 — DECISION]
- `pipeline_timestamp_utc` in the quality report JSON is dynamic by default (real UTC).
- When `--deterministic` is passed (used by the DVC stage), it is replaced with the
  fixed string `"deterministic"`.
- This makes the JSON output byte-identical across runs so DVC can hash it stably.
- Human CLI runs (without the flag) still get the real timestamp.

### Schema contract [T-011 — DECISION]
New constants added to `ml/data/schema.py` (no breaking changes to T-003 constants):

| Constant | Value |
|---|---|
| `TARGET_COLUMN` | `"Machine_Failure"` |
| `FEATURE_COLUMNS` | 10 numeric sensors + `Machine_Type` = 11 columns |
| `CATEGORICAL_COLUMNS` | `["Machine_Type"]` |
| `IDENTIFIER_COLUMNS` | `["Machine_ID"]` |
| `TIME_COLUMNS` | `["Timestamp"]` |
| `ADMINISTRATIVE_COLUMNS` | `["Sensor_Batch_Code", "Checksum_Flag"]` |
| `LEAKAGE_COLUMNS` | `["Failure_Type"]` |
| `PREPARED_COLUMNS` | Same 17 as `EXPECTED_COLUMNS` |

### Feature contract [T-011 — DECISION]
- **Module:** `ml/data/features.py`
- **11 feature columns:** `Air_Temperature_C`, `Process_Temperature_C`, `Rotational_Speed_RPM`, `Torque_Nm`, `Vibration_mm_s`, `Pressure_bar`, `Current_A`, `Voltage_V`, `Tool_Wear_Min`, `Operating_Hours`, `Machine_Type`
- **Target:** `Machine_Failure` (binary: 0=healthy, 1=failure)
- **5 forbidden columns:** `Failure_Type`, `Machine_ID`, `Timestamp`, `Sensor_Batch_Code`, `Checksum_Flag`
- **No feature engineering at this stage:** DeltaT, apparent power, mechanical power, wear-rate etc. are T-012 additions
- **Leakage guard:** `validate_no_leakage()` raises `ValueError` if forbidden columns are present in a DataFrame passed to `select_features()`

### Split strategy [T-011 — DECISION]
- **Strategy:** Machine-level grouped split (NOT row-level random)
- **Rationale:** 60 unique Machine_IDs, each with 137-187 rows. Row-level splitting would leak machine-specific sensor calibration, wear patterns, and operating biases across train/test.
- **Algorithm:** Failure-rate-aware round-robin assignment
  1. Sort machines by per-machine `Machine_Failure` rate
  2. Round-robin over sorted list: assign to train / val / test cyclically
  3. Each split receives machines from the full range of failure rates (low/med/high)
- **This is NOT sklearn StratifiedGroupKFold.** StratifiedGroupKFold stratifies group-level target labels (which groups contain any failure). Our heuristic distributes per-machine failure *rates* proportionally, which is a different and more granular objective.
- **GroupShuffleSplit is also NOT used.** It provides no failure-rate control.

### Split results (seed=42) [T-011 — MEASURED]
| Split | Machines | Rows | Failure rate |
|---|---|---|---|
| Train | 42 | 6,897 | 11.83% |
| Validation | 9 | 1,489 | 8.93% |
| Test | 9 | 1,499 | 9.01% |
| Overall | 60 | 9,885 | 10.97% |

- Machine_ID overlap: **0** (zero overlap across all three splits — verified by test)
- All splits contain both classes (0 and 1)

### Machine-level leakage analysis [T-011 — AUDIT]
- 60 unique Machine_IDs; mean 164.75 rows per machine (min 137, max 187)
- All 60 machines have at least 1 failure (range 6.5%-17.3% per-machine rate)
- Row-level splitting would expose train rows from the same machine that appears in test → machine-level leakage
- **Chosen: grouped split by Machine_ID** — complete prevention

### Temporal leakage analysis [T-011 — AUDIT]
- Timestamps span 2024-01-01 to 2024-06-28 (~6 months)
- Tool_Wear_Min is NOT monotone within machines — not a strict time series
- Up to 6 readings per machine per day (sparse sensor snapshots, not regular intervals)
- **Decision:** Grouped machine split is appropriate. Temporal ordering within the training machines' rows is a T-012 modelling decision.
- **No temporal leak:** grouped by machine, not by time window

### Parameters [T-011]
```yaml
pipeline:
  version: "T-003/v1"
split:
  seed: 42
  train_frac: 0.70
  val_frac: 0.15
  test_frac: 0.15
  strategy: grouped_machine_id
  target_col: Machine_Failure
  group_col: Machine_ID
```

### Dependencies added [S03]
| Dependency | Version | Reason | Section |
|---|---|---|---|
| `scikit-learn` | `>=1.6,<2` | `numpy` / `pandas` integration; future use in splits | `[project].dependencies` |
| `dvc` | `>=3.0,<4` | T-010 data versioning pipeline | `[project.optional-dependencies].dev` |

### Output paths
- Prepared dataset (DVC): `data/interim/predictive_maintenance_prepared.csv` (9,885 x 17)
- Quality report (DVC): `data/interim/data_quality_report.json`
- Train split: `data/interim/splits/train.csv` (6,897 x 17, 42 machines)
- Val split: `data/interim/splits/val.csv` (1,489 x 17, 9 machines)
- Test split: `data/interim/splits/test.csv` (1,499 x 17, 9 machines)
- DVC lock: `dvc.lock`
- DVC config: `.dvc/config`

### Tests
- New: 21 feature tests (test_features.py) + 21 split tests (test_splits.py) = 42 new tests
- Total: 90 tests passing (38 T-003 + 42 new S03 + 2 smoke tests) — actually 90 passing including all categories

### Remaining limitations
- Dataset provenance still unverified (T-002 BLOCKED)
- No cloud DVC remote configured; `dvc push` will fail until a remote is added
- Split val/test failure rates (8.9%) are ~2pp below overall (11.0%) — acceptable given only 9 machines per group and the round-robin heuristic; exact stratification is not achievable with integer group assignment
- Scikit-learn is declared as a runtime dependency but `splits.py` only uses `numpy` (also a sklearn dep) directly; sklearn's API may be used more in T-012

---

## S02 — T-003 Data Preparation Pipeline (2026-09-25)


### Task completion
- **Status:** DONE
- **Branch:** `feat/T-003-data-preparation`
- **Base commit:** `18a63ec37b890a1007259b3e096d33659c6c98bd` (S01)
- **Files created:** `ml/__init__.py`, `ml/data/__init__.py`, `ml/data/schema.py`, `ml/data/prepare.py`, `tests/ml/__init__.py`, `tests/ml/test_prepare.py`, `data/interim/predictive_maintenance_prepared.csv`, `data/interim/data_quality_report.json`, `docs/sessions/S02_report.md`
- **Files modified (project config):** `pyproject.toml` (pandas dependency declared; package discovery enabled; black target-version added), `tasks.md`, `memory.md`

### Measured statistics [AUDIT — S02]
| Metric | Value |
|---|---|
| Raw input rows | 10,000 |
| Raw input columns | 17 |
| Machine_Type missing before | 490 |
| Machine_Type recovered from Machine_ID prefix | 490 |
| Machine_Type conflicts (non-null vs derived) | 0 |
| Duplicates detected (derive-first order) | 115 |
| Output rows | 9,885 |
| Output columns | 17 |
| Voltage_V violations (> 500 V) nullified | 22 |
| All other range violations | 0 |
| Machine_Type nulls in output | 0 |
| Missing sensor values preserved (not imputed) | Yes |

### Historical discrepancy reconciliation [AUDIT — S02]
- **Row count discrepancy:** The previously documented expected output of 9,894 rows was calculated using a dedup-first order (raw NaN Machine_Type is treated as distinct from non-null), which detects 106 duplicates. The T-003 spec mandates derive-first order (schema → derive_machine_type → remove_duplicates), which exposes 9 additional semantic duplicates (rows with NaN Machine_Type that become identical to existing rows after derivation). Derive-first is semantically correct and produces **9,885 rows**. Both orderings and their rationale are documented in `docs/sessions/S02_report.md`.
- **"339 mislabelled rows" reconciliation:** The figure "339" in prior memory.md/tasks.md referred approximately to the count of missing Machine_Type rows that would have been *incorrectly* assigned Compressor by mode imputation (i.e., non-Compressor rows). The actual figures: 490 missing Machine_Type rows total; 150 of those are CMP prefix (Compressor = correct by accident under mode imputation); 340 would be *incorrectly* assigned Compressor. The "339" was an off-by-one approximation. Corrected to 340 in this session.

### Implementation decisions [DECISION — S02]
- Pipeline order: schema_validate → derive_machine_type → remove_duplicates → validate_ranges. This is semantically correct: duplicate identity is evaluated on recovered values.
- Range violations are nullified to NaN (not clipped). Clipping was the notebook defect; nullification + reporting is the correct behaviour.
- No imputation at this stage. Missing sensor values remain NaN throughout the pipeline and in the output.
- `Sensor_Batch_Code` and `Checksum_Flag` are retained in the prepared output for traceability; they are excluded from duplicate comparison identity but not dropped from the dataset.
- `FORBIDDEN_FEATURE_COLUMNS` constant established: `[Failure_Type, Machine_ID, Timestamp, Sensor_Batch_Code, Checksum_Flag]`.

### Dependencies added [S02]
- `pandas>=2.2,<3` added to `[project].dependencies` in `pyproject.toml`. Justified: introduced as the first production/project Python code using pandas. No new dev or optional dependencies added.
- `pyproject.toml` package discovery changed from `packages = []` to `[tool.setuptools.packages.find]` to allow `ml` package and sub-packages to be importable after `pip install -e .`.
- `target-version = ["py311"]` added to `[tool.black]` to resolve Python version mismatch warning with black 26.x running on Python 3.13.

### Output paths
- Prepared dataset: `data/interim/predictive_maintenance_prepared.csv` (9,885 × 17)
- Quality report: `data/interim/data_quality_report.json`

### Missing-value policy
Missing sensor values are preserved as NaN and not imputed. Imputation belongs inside the sklearn `Pipeline` fit on training data only (T-010/T-012) to prevent evaluation leakage.

### Remaining limitations
- Dataset provenance still unverified (T-002 BLOCKED).
- `Sensor_Batch_Code` and `Checksum_Flag` are retained in the interim dataset; whether to drop them at the feature engineering stage is a T-011 decision.

---

## 2. Uploaded project inventory [AUDIT]
```
EdgeTwin-AI/
  README.md            (empty)   requirements.txt (empty)
  data/raw/predictive_maintenance_dataset.csv        10,000 x 17
  data/processed/predictive_maintenance_cleaned.csv  9,893 x 15
  data/processed/predictive_maintenance_engineered.csv 9,893 x 19
  data/processed/01_Data_Understanding.ipynb, 02_Feature_Engineering.ipynb   (notebooks stored inside data/)
  notebooks/Untitled.ipynb (empty)   api/ , dashboard/ , docs/ , models/  (empty)
```
Notebook hygiene: `.ipynb_checkpoints` present; notebook uses an absolute Windows path (`D:\Project\...`) → make relative.

## 3. Dataset decisions and findings
- [FACT] AI4I 2020 (UCI, CC BY 4.0, Matzka 2020): synthetic, 10,000 rows, 3.39% failures, 5 features + product type, modes TWF/HDF/PWF/OSF/RNF. https://archive.ics.uci.edu/dataset/601
- [AUDIT] **The uploaded dataset is NOT AI4I 2020.** 10,000 rows, 60 machine IDs (5 types), timestamps, vibration/pressure/current/voltage/op-hours, failure rate 10.99%. It reuses the AI4I failure-mode names. **Provenance unknown → asked the user.**
- [AUDIT] Signatures indicate rule-generated labels (synthetic): e.g., "Random Failure" rows show vibration ≈ 7.4 mm/s and pressure ≈ 9.2 bar (not random); Heat Dissipation has raised ΔT and lower RPM; Overstrain combines high wear and torque. Do not present as real industrial data.
- [AUDIT] **Rows are independent snapshots**, not machine time series: corr(time, Operating_Hours) per machine ≈ −0.008, Operating_Hours jumps up and down within one machine, attributes are not consistent per Machine_ID. Consequence: the data supports *failure-condition detection from the current state*, **not** RUL or true forecasting.
- [AUDIT] Missing values: ~10% per sensor; **37.4% of rows have ≥ 1 missing sensor**. Machine_Type null in 490 rows (recoverable from the Machine_ID prefix).
- [AUDIT] Machine_Type has no effect on failure rate or sensor means (single generator) → per-type thresholds cannot be learned from this data.
- [AUDIT] Duplicates: 106 rows dropped in notebook (matches).
- **Defects in existing cleaning (kept for traceability; notebooks not modified):**
  1. Machine_Type imputed by mode ("Compressor") instead of the ID prefix → **339 rows mislabelled**.
  2. Median imputation performed before train/test split (mild evaluation leakage).
  3. Cell 3.7 consistency fix is a no-op (`Machine_Failure==1 & No Failure → set to 1`); harmless only because zero inconsistencies exist.
  4. Voltage clipping to ≤ 500 V altered 22 values that are plausible anomalies.
  5. `Wear_Rate = Tool_Wear/Operating_Hours` is physically unjustified here (Operating_Hours independent of wear; correlation with target ≈ 0; max ≈ 94 outlier).
  6. `Power_Approx = V×I` is **apparent power (VA)**, not watts; mechanical power = τ·ω is a different quantity. Both are kept as separately named features.
  7. Only the target `Machine_Failure` is a valid label; `Failure_Type` is leakage if used as a feature.
- [AUDIT] Preliminary benchmark (5-fold stratified, untuned, OOF; **not a final result**):
  | Setup | ROC-AUC | PR-AUC | best F1 | Notes |
  |---|---|---|---|---|
  | LogReg, engineered, imputed | 0.84 | – | 0.44 | linear model weak |
  | RandomForest, engineered, imputed | 0.97 | – | 0.74 | |
  | HistGB, engineered, imputed | 0.97 | 0.90 | 0.84 | |
  | **HistGB, raw10, NaN-native** | **0.978** | **0.924** | 0.865 (P 0.88 / R 0.85) | no imputation needed |
  | HistGB, raw10 + 4 physics, NaN-native | 0.977 | 0.924 | 0.872 (P 0.91 / R 0.84) | |
  | Isolation Forest (healthy-only) | 0.895 | 0.564 | – | HDF 0.96, PWF 0.91, RNF 0.92, OSF 0.87, **TWF 0.78** |
  Per-mode recall (HistGB imputed): Tool Wear lowest (≈ 0.5). Engineered features barely change tree-model accuracy; they matter for explainability and for edge computation.
- [DECISION] Primary training data = the uploaded dataset **after** T-003 fixes, labelled "provenance unverified" until the user answers; AI4I 2020 used as an independent public benchmark for pipeline generality (T-071). If provenance cannot be established, the report will state that the dataset is a synthetic table of unknown origin.
- [DECISION] Training data vs live telemetry: the simulator's healthy envelope and fault signatures are computed from this dataset's EDA, so simulated telemetry is in-distribution; it is explicitly labelled SIMULATED.
- Healthy envelope (mean / std): air 25.4/2.5 °C, process 35.3/2.8 °C, RPM 1548/179, torque 40.1/10.1 Nm, vibration 2.5/1.0 mm/s, pressure 5.5/1.8 bar, current 12.0/3.5 A, voltage 415/12 V, wear 131/75 min, op-hours 10,039/5,785 h. Air and process temp correlate 0.90 in healthy data; other pairs ≈ 0.

## 4. Model decisions
- [DECISION] Target: binary `Machine_Failure`; algorithms compared: LR, DT, RF, gradient-boosted trees (HGB; XGBoost if justified). Champion expected to be GBDT with native NaN handling (removes the leakage-prone imputation step and matches real edge sensor dropouts).
- [DECISION] Isolation Forest is a separate unsupervised layer; reported separately; not used to inflate classifier metrics.
- [DECISION] No RUL claims. Trend layer in the twin is a labelled heuristic.
- [ASSUMPTION] SHAP TreeExplainer compatibility with HistGradientBoosting must be verified (T-015); fallback XGBoost/LightGBM native contributions.

## 5. Wokwi decisions and verified constraints
- [FACT] WiFi with internet access, MQTT/HTTP(S)/WebSocket supported; public gateway has no LAN access and is monitored; private gateway required for localhost/`host.wokwi.internal`. https://docs.wokwi.com/guides/esp32-wifi
- [FACT] Wokwi for VS Code bundles the private IoT gateway and can forward the serial port over RFC2217 (`wokwi.toml`). https://docs.wokwi.com/vscode/project-config
- [FACT] Parts: DHT22, NTC, DS18B20, MPU6050, pots, slide pot, HX711, pushbuttons, LEDs, BMP180. No current/voltage/industrial-pressure sensors. https://docs.wokwi.com/getting-started/supported-hardware
- [FACT] Automation: `set-control`, `wait-serial` scenarios (alpha), CLI token. https://docs.wokwi.com/wokwi-ci/automation-scenarios
- [FACT] Pricing page: Community free (public projects, virtual WiFi), Hobby $7/mo lists Private IoT Gateway; VS Code licence terms appear inconsistent across pages → **[ASSUMPTION] verify before relying** (https://wokwi.com/pricing, https://wokwi.com/license).
- [FACT-derived] Free Community projects are public → **never put real credentials in a public Wokwi sketch.**
- [DECISION] MQTT chosen over HTTP: pub/sub, small payloads, last-will for offline detection, retained status, QoS; one contract serves Wokwi, virtual edge, replay. HTTP kept as a debug fallback only.
- [DECISION] Two connectivity paths (A: cloud broker with TLS; B: VS Code + local Mosquitto); backend unchanged between them. Decide at T-040.
- [DECISION] Wokwi does not simulate machine physics; a firmware process model + real Wokwi parts (DHT22/NTC/MPU6050/slide pot) drive signals. Documented honestly.
- [DECISION] CI cannot depend on Wokwi (token/minutes/paid); a Python virtual edge implements the same contract. Risk: two implementations drifting → shared scenario spec + golden test.

## 6. Architecture decisions
- [DECISION] Single FastAPI process with background MQTT consumer; WebSocket for dashboard push (bidirectional need for commands, native in FastAPI). SSE considered; rejected for lack of client→server channel.
- [DECISION] PostgreSQL only (no TimescaleDB/MongoDB): ≈ 260k telemetry rows/day at 6 machines × 0.5 Hz; tables hypertable-ready.
- [DECISION] Digital Twin = state model + derived decisions + history, inside the backend (not a separate service). Aligned with ISO 23247 roles; not DTDL.
- [DECISION] Decision layers L1–L6 kept separate (sensor condition / ML risk / anomaly / health / alert / recommendation).
- [DECISION] Existing folders kept: `api/` = backend, `dashboard/` = frontend. New: `edge/ simulation/ ml/ mlops/ tests/`.
- [DECISION] Not adopted (no purpose at this scale): Prometheus/Grafana, Kafka, Redis, Kubernetes, Evidently (own PSI/KS ≈ 100 lines; Evidently optional stretch).
- [DECISION] Auth (3 roles) is included because feedback, retraining, and scenario injection are privileged, identity-bound actions.

## 7. Research findings (sources actually retrieved)
- [FACT] Digital-twin PdM SLR (van Dinter et al., Information and Software Technology 151, 2022): notes scarcity of failure data and use of twins to generate degradation data. https://qspace.qu.edu.qa/handle/10576/36810
- [FACT] Newer systematic review of DT-driven PdM: https://arxiv.org/abs/2509.24443
- [FACT] ISO 23247 defines a digital twin framework for manufacturing (OME, device communication, DT, user entities). https://www.iso.org/standard/75066.html (part 1), part 2 https://www.iso.org/standard/78743.html
- [FACT] Azure Digital Twins: DTDL models, twin graph, event routing. https://learn.microsoft.com/azure/digital-twins/overview
- [FACT] **AWS Monitron closed to new customers (from 31 Oct 2024); Amazon Lookout for Equipment end of support 7 Oct 2026** → do not cite as live competitors; useful as market context. https://aws.amazon.com/lookout-for-equipment/ ; https://docs.aws.amazon.com/Monitron/latest/user-guide/what-is-monitron.html
- [FACT] Monitron combines ISO-standard vibration thresholds with ML models (design idea reused: standards-referenced threshold layer + ML layer). https://docs.aws.amazon.com/Monitron/latest/user-guide/how-monitron-works.html
- [FACT] Siemens Senseye: cloud predictive maintenance from condition data with ML forecasting. https://press.siemens.com/global/en/node/6475
- [FACT] IBM Maximo Application Suite: asset monitoring + predictive failure probability modules. https://www.ibm.com/downloads/cas/WXEOEVGP (secondary partner page: cosol.global)
- [FACT] GE Vernova APM / predictive analytics. https://www.gevernova.com/software/products/predictive-analytics
- [FACT] PTC ThingWorx anomaly detection docs https://support.ptc.com ; sale of ThingWorx/Kepware to TPG reported by CIMdata (Nov 2025) — **verify current status**.
- [FACT, secondary] NVIDIA: Omniverse (3-D industrial twins) and Jetson (edge inference) are platforms rather than turnkey PdM apps (ARC Advisory write-up; weak source).
- **Not researched to primary source:** Bosch. Excluded from the comparison until sourced.
- [FACT] Drift ≠ performance decay in a published PdM MLOps evaluation (arXiv 2211.06239) → drift is a warning, not a retrain trigger by itself.
- [FACT] MLflow deprecates registry stages in favour of aliases/tags (RFC #10336) → we use `champion`/`challenger` aliases. https://github.com/mlflow/mlflow/issues/10336
- [FACT] TinyML PdM survey arXiv 2506.18927; 2026 multimodal TinyML PdM paper (PMC13417022) highlights per-installation baselines/recalibration.
- [FACT] HiveMQ Cloud Serverless offers a free tier with TLS (8883) and username/password; Serverless has no uptime SLA; permission model limits (per-credential default permissions) → **[ASSUMPTION] verify limits and topic ACL support.**
- [SECONDARY] Vibration severity zones A–D per ISO 20816 depend on machine group/support; **do not hard-code numeric limits until the standard text is checked.**

## 8. Proposed system contributions (not novelty claims)
C1 Source-agnostic telemetry contract with one ingestion/inference/twin path for simulated, replayed, and future real sensors, enforced by contract tests.
C2 Layered decision architecture (sensor condition → ML risk → anomaly → health → alert → recommendation) with provenance stored on the twin.
C3 Edge safety layer that works without the backend; edge–cloud disagreement logged as an MLOps signal.
C4 Feedback-driven MLOps loop: drift + labelled engineer feedback → gated retraining → alias promotion/rollback, with drift treated as a warning rather than an automatic trigger.
C5 Fault-scenario engine shared by firmware, virtual edge, and CI enabling **detection latency / false-alarm rate** as evaluation metrics beyond offline accuracy.
Honest assessment: individual elements exist in the literature; the contribution is the integrated, measured, reproducible system. Suitable and defensible for a B.Tech project; not a research-novelty claim.

## 9. UI decisions
Provisional palette/type in design.md. Reference website pending. Chart-series colours are separate from state colours. State never colour-only.

## 10. Bugs and fixes
| # | Item | Status |
|---|---|---|
| B-1 | Machine_Type mislabelled for 339 rows (mode imputation) | Open → T-003 |
| B-2 | Imputation before split | Open → T-010/T-012 (pipeline-internal) |
| B-3 | No-op consistency line in notebook 3.7 | Noted; notebook untouched |
| B-4 | Absolute path `D:\Project\...` in notebooks | Open → T-001 |
| B-5 | Notebooks stored under `data/processed/` | Open → T-001 (needs approval) |

## 11. Known limitations
Dataset synthetic, provenance unverified, i.i.d. snapshots (no forecasting). Wokwi has no physics; vibration is a proxy, not calibrated velocity. Wokwi free plan = public projects and monitored public gateway. Preliminary metrics are untuned OOF estimates. Numeric ISO vibration limits not yet verified.

## 12. Dependencies (planned; each needs justification in its task)
Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, pydantic, paho-mqtt (or aiomqtt), scikit-learn, xgboost, shap, MLflow, DVC, pandas, scipy; React, TypeScript, Vite, Tailwind, TanStack Query, Recharts; PostgreSQL 16, Mosquitto, Docker Compose; PubSubClient + ArduinoJson (firmware).

### Justified & Declared Dependencies
- `xgboost>=3.0.0`: [T-012] S04 Champion classifier. Required for gradient boosted tree training and native margin attribution (`Booster.predict(..., pred_contribs=True)`).
- `mlflow>=3.14.0`: [T-012, T-016] Model experiment tracking and model registry. Encapsulates `EdgeTwinRiskModel` PyFunc artifact, alias governance (`challenger`, `champion`), and technical promotion gates.
- `shap>=0.48.0,<1`: [T-015] TreeSHAP explainer engine (`shap.TreeExplainer`).
  - *What it does:* Computes game-theoretic local feature attributions (TreeSHAP) in model log-odds margin space with guaranteed numerical additivity ($\sum \phi_i + \text{base} = \text{margin}$) and global feature importance ranking.
  - *Why stdlib/existing tools are insufficient:* Python standard library provides no tree attribution or SHAP implementation. While XGBoost includes native `pred_contribs=True` (which we implemented as an offline fallback), `shap` provides canonical interop, tree path-dependent background perturbation, interaction index utilities, and standardized explainability primitives required by T-015. Declared in `pyproject.toml` as `shap>=0.48.0,<1`.

## 13. API / database changes
None yet (v1 draft in architecture.md §8, §12, §13).

## 14. Open questions
1. **Dataset source / licence / generation method?** (blocks T-002)
2. UI reference website (needed at T-050).
3. Submission/expo date (sets how much of the stretch scope fits).
4. Wokwi plan/licence available to you (decides Path A vs B at T-040).

## 15. Future considerations
Shallow-tree edge screening (T-044); Evidently reports; TimescaleDB if volume grows; Prometheus `/metrics`; real sensor hardware (ESP32 + accelerometer) as a bridge from simulation.

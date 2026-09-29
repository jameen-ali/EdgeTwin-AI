# tasks.md — EdgeTwin AI Task Roadmap

Status values: `TODO` · `IN PROGRESS` · `BLOCKED` · `DONE`. Only **one task IN PROGRESS at a time.** A task is DONE only when acceptance criteria pass and tests are green (rules.md §G).
Detail level: Phases 0–3 are fully specified now. Later phases are listed compactly and are expanded to the full template **before** each task starts (workflow: research → requirements → … → implement).

Full template per task: **ID · Goal · Files · Depends · Implementation · Acceptance · Tests · Status**

---
## PHASE 0 — Foundation and data trust

### T-001 Repository hygiene and structure
- **Goal:** Clean, reproducible repo skeleton without touching existing work.
- **Files:** `.gitignore`, `README.md` (currently empty), `requirements.txt` (currently empty), `pyproject.toml`, `.env.example`, `.pre-commit-config.yaml`, new empty dirs `edge/ simulation/ ml/ mlops/ tests/`. Move (with approval) the two notebooks from `data/processed/` to `notebooks/`.
- **Depends:** none.
- **Implementation:** ignore `.ipynb_checkpoints/`, `.env`, `__pycache__`, `mlruns/`, large artefacts; pin Python version; ruff + black config; README with project one-liner and status table (all features "not started").
- **Acceptance:** fresh clone → `pip install -e .[dev]` works; `ruff` and `pytest` (0 tests) run; no notebook or data file altered except moved.
- **Tests:** CI-less smoke: `pytest --collect-only` exits 0.
- **Status:** DONE

### T-002 Dataset provenance and data card
- **Goal:** Establish where `predictive_maintenance_dataset.csv` came from and what it legitimately supports.
- **Files:** `docs/dataset/data_card.md`, `docs/dataset/audit.md`.
- **Depends:** **user input: source, licence, generation method** (BLOCKING for public release of the data).
- **Implementation:** record source/licence/date; document the audit findings in memory.md (synthetic-looking, i.i.d. snapshots, 37% rows with ≥ 1 missing sensor, no per-machine time structure, Machine_Type not predictive); add AI4I 2020 (UCI, CC BY 4.0) as the credible public benchmark with citation.
- **Acceptance:** data card states provenance, licence, known limits; if provenance unverifiable, the card says so and the report labels the dataset "provenance unverified".
- **Tests:** none (document); link check.
- **Status:** BLOCKED (waiting on user)

### T-003 Fix the data pipeline defects found in the audit
- **Goal:** Replace notebook-only cleaning with a tested script that does not corrupt data or leak.
- **Files:** `ml/data/prepare.py`, `ml/data/schema.py`, `tests/ml/test_prepare.py`; notebooks untouched (kept as EDA record).
- **Depends:** T-001.
- **Implementation:** (1) derive `Machine_Type` from `Machine_ID` prefix (490 missing values recovered; 340 of those would have been incorrectly set to Compressor by mode imputation; 0 non-null conflicts); (2) drop exact duplicates ignoring `Sensor_Batch_Code/Checksum_Flag` — derive-first order exposes 115 total duplicates (106 raw + 9 semantic) → 9,885 output rows; (3) **no imputation** at this stage — NaN preserved; (4) range checks flag/nullify impossible values instead of clipping (22 Voltage_V > 500 V nullified); (5) write `data/interim/` with a JSON quality report; (6) forbidden-column list constant `FORBIDDEN_FEATURE_COLUMNS`.
- **Acceptance:** output row count 9,885 (measured; historical 9,894 was dedup-first order — documented in S02 report); zero Machine_Type mismatches vs ID prefix; NaN preserved; report lists every modified value count.
- **Tests:** 36 unit tests + 2 existing smoke tests = 38 total passing; T1 prefix mapping, T2 recovery, T3 conflict detection, T4 dedup semantics, T5 NaN preserved, T6 range nullify, T7 no imputation, T8 regression on raw dataset.
- **Status:** DONE

### T-004 Research documents from verified sources
- **Goal:** Convert the discovery report into `docs/research/` (literature, competitors, gap, novelty, dataset comparison).
- **Files:** `docs/research/*.md`.
- **Depends:** none (report exists).
- **Implementation:** keep [FACT]/[DECISION]/[PROPOSED]/[ASSUMPTION] labels; open items to verify: Bosch offering, ISO 20816-3 zone limits (need the standard text), Wokwi VS Code licence terms, HiveMQ free-tier limits.
- **Acceptance:** every claim has a URL or is labelled ASSUMPTION; no invented citations.
- **Tests:** link checker in CI (later).
- **Status:** TODO

---
## PHASE 1 — Machine learning (built on your notebooks)

### T-010 Reproducible data stage (DVC) + schema validation
- **Goal:** `dvc repro` rebuilds interim/processed data from raw.
- **Files:** `dvc.yaml`, `params.yaml`, `ml/data/*`, `.dvc/`.
- **Depends:** T-003.
- **Implementation:** DVC 3.67.1 initialized; single `prepare` stage invokes `python -m ml.data.prepare --deterministic`; deps: raw CSV + prepare.py + schema.py; outs: prepared CSV + quality report JSON. `--deterministic` flag added to prepare.py to suppress live UTC timestamp in JSON output so DVC output hashes are stable. Local-only DVC (no cloud remote). Raw dataset is NOT DVC-tracked (T-002 provenance BLOCKED). `data/interim/` files removed from Git tracking; `.gitignore` updated.
- **Acceptance:** `dvc repro` exits 0; second `dvc repro` shows 'Stage prepare didn\'t change, skipping'; `dvc status` shows 'Data and pipelines are up to date'. Prepared CSV: 9,885 × 17 (deterministic).
- **Tests:** Full 90-test suite passes with T-010 behavior preserved.
- **Status:** DONE

### T-011 Shared feature module
- **Goal:** One feature function used by training and the backend.
- **Files:** `ml/data/features.py`, `ml/data/splits.py`, `tests/ml/test_features.py`, `tests/ml/test_splits.py`.
- **Depends:** T-003.
- **Implementation:** `ml/data/schema.py` extended with T-011 constants: `TARGET_COLUMN`, `FEATURE_COLUMNS` (10 numeric + Machine_Type = 11), `CATEGORICAL_COLUMNS`, `IDENTIFIER_COLUMNS`, `TIME_COLUMNS`, `ADMINISTRATIVE_COLUMNS`, `LEAKAGE_COLUMNS`, `PREPARED_COLUMNS`. `ml/data/features.py` provides `get_feature_columns()`, `get_target_column()`, `get_forbidden_columns()`, `select_features()`, `select_target()`, `validate_no_leakage()`. `ml/data/splits.py` implements machine-level grouped split (42/9/9 machines = ~70/15/15%) with failure-rate-aware round-robin assignment; seed=42; zero Machine_ID overlap guaranteed. No feature engineering (DeltaT, VA, etc.) at this stage.
- **Acceptance:** 11 feature columns, 5 forbidden, Machine_Failure as target; zero Machine_ID overlap in splits; failure rate within 5pp of 10.97% overall in each split.
- **Tests:** 21 feature tests + 21 split tests = 42 new tests; total 90 passing.
- **Status:** DONE

### T-012 Model comparison experiment
- **Goal:** Justified model selection.
- **Files:** `ml/data/engineering.py`, `ml/models/train.py`, `ml/models/evaluate.py`, `ml/models/compare.py`, `docs/ml/model_comparison.md`, `tests/ml/test_models.py`.
- **Depends:** T-010, T-011.
- **Implementation:** Evaluated 5 candidate model types (Logistic Regression, Decision Tree, Random Forest, HistGradientBoosting, XGBoost) across 3 feature configurations (`base10`, `+physics`, `+wear_rate`) with 5-fold cross-validation and MLflow tracking. Preprocessing fitted strictly on training data (median imputation, ordinal encoding with unseen category guard, standard scaling for linear models only). Selection criterion: Validation PR-AUC (primary) and Validation Recall (tie-break). Champion: `xgboost` with `+physics` (14 features; Val PR-AUC = 0.8969, Val Recall = 0.8195). Single final evaluation on held-out test set: Test PR-AUC = 0.9234, Recall = 0.8963, F1 = 0.8403, Accuracy = 0.9693, ROC-AUC = 0.9755. Per-failure-type recall reported (Tool Wear = 76.47%).
- **Acceptance:** Complete 15-model comparison table in `docs/ml/model_comparison.md`; champion chosen by validation PR-AUC; single held-out test evaluation after selection; MLflow runs tracked; zero leakage verified.
- **Tests:** 59 unit and integration tests in `tests/ml/test_models.py` (total 149 tests passing across repository); seed determinism; metric sanity; leakage guards; test report isolation.
- **Status:** DONE

### T-013 Calibration, threshold, and risk bands
- **Goal:** Probability that means something plus a defensible threshold.
- **Files:** `ml/models/calibrate.py`, `ml/models/thresholds.py`, `docs/ml/calibration.md`, `docs/ml/thresholds.md`.
- **Depends:** T-012.
- **Implementation:** Evaluated uncalibrated vs. sigmoid (Platt) vs. isotonic calibration on `val_df` using `FrozenEstimator` to keep S04 champion frozen. Sigmoid selected: validation Brier score reduced from 0.02810 to 0.02619 (6.8% reduction), ECE reduced from 0.02867 to 0.00391 (86.4% reduction), zero degradation in PR-AUC (0.8969) or ROC-AUC (0.9822). Threshold sweep (0.10..0.90, step 0.02) evaluated 41 points on validation data across cost ratios r=1, 3, 5, 10. Selected operational threshold $t^* = 0.16$ based on $r=5$ cost-sensitive optimization (Cost=137, Recall=0.8421, Precision=0.7778 on val). Defined 4 system risk bands: LOW (<0.15), MEDIUM (0.15..0.16), HIGH (0.16..0.80), CRITICAL (>=0.80).
- **Acceptance:** Reliability curve and Brier score reported; operational threshold cost-justified; bands documented as project-specific operational recommendations.
- **Tests:** 18 unit and integration tests in `tests/ml/test_calibration.py`, 18 in `tests/ml/test_thresholds.py`.
- **Status:** DONE

### T-014 Anomaly detector and health score definition
- **Goal:** Separate unsupervised anomaly detection and a documented health score.
- **Files:** `ml/models/anomaly.py`, `ml/models/health.py`, `docs/ml/health_model.md`.
- **Depends:** T-012.
- **Implementation:** Isolation Forest (n_estimators=150, contamination=0.02, random_state=42) trained strictly on 6,081 healthy training observations (`train_df[Machine_Failure == 0]`) with 14 `+physics` features. Normalization to [0, 1] using healthy training reference percentiles (s_nominal=95th, s_extreme=1st) with robust guards against zero denominators and NaNs. Validation: ROC-AUC = 0.8699, PR-AUC = 0.4639. Empirical validation threshold (alpha=0.02) = 0.9075, provisional default = 0.50. Layer 4 Health Score composite formula: $100 - (60 \cdot p_{\text{cal}} + 25 \cdot a_{\text{anomaly}} + \Delta_{\text{sensor}})$ with strictly clamped sensor penalty $0 \le \Delta_{\text{sensor}} \le 15$. Deterministic state precedence hierarchy implemented: `OFFLINE` > `MAINTENANCE_REQUIRED` (operational override: Tool_Wear_Min >= 240 or tech confirmation) > `CRITICAL` > `WARNING` > `HEALTHY`.
- **Acceptance:** Anomaly metrics reported separately from classifier metrics; fusion table unit-tested; state precedence strictly verified.
- **Tests:** 17 unit and integration tests in `tests/ml/test_anomaly.py`, 18 in `tests/ml/test_health.py`.
- **Status:** DONE

### T-015 Explainability
- **Goal:** Top contributing features per prediction in model log-odds margin space.
- **Files:** `ml/models/explain.py`, `docs/ml/explainability.md`, `tests/ml/test_explain.py`.
- **Depends:** T-012, T-013.
- **Implementation:** Implemented `EdgeTwinExplainer` supporting both `Pipeline` and `CalibratedClassifierCV`. Uses `shap.TreeExplainer(classifier, feature_perturbation="tree_path_dependent")` operating in XGBoost margin/log-odds space. Clarified Platt scaling monotonic relation (positive SHAP monotonically increases failure probability, negative SHAP decreases probability). Feature names recovered dynamically via `preprocessor.get_feature_names_out()` to guarantee 1-to-1 alignment with transformed matrix. Verified strict numerical additivity ($|\sum \phi_i + \text{base\_value} - \text{margin}| \le 10^{-4}$, measured $\approx 2.03 \times 10^{-6}$) with loud `ValueError` on discrepancy. Built-in zero-dependency fallback via native XGBoost `Booster.predict(..., pred_contribs=True)` producing identical contributions. Computed global feature importance ranking on validation background (`artifacts/feature_importance_global.csv`). Enforced mandatory disclaimer: *"Statistical association with failure condition in model log-odds margin space; not causal."*
- **Acceptance:** Measured p95 single-sample explanation latency is 20.12 ms (< 100 ms SLA passed with 79.9% margin); additivity error $\approx 2.03 \times 10^{-6} \le 10^{-4}$; all 6 forbidden leakage columns rejected.
- **Tests:** 31 tests in `tests/ml/test_explain.py` covering initialization, leakage rejection, feature alignment, local payload structure, top-k sorting, direction semantics, additivity guards, native fallback equivalence, global ranking, and latency SLA.
- **Status:** DONE

### T-016 Registry and model card
- **Goal:** Versioned, loadable champion encapsulated in a production PyFunc wrapper with technical promotion gate.
- **Files:** `mlops/register.py`, `docs/ml/model_card.md`, `tests/mlops/test_register.py`.
- **Depends:** T-013–T-015.
- **Implementation:** Created `EdgeTwinRiskModel` (`mlflow.pyfunc.PythonModel`) wrapping the frozen S05 calibrated champion pipeline. Encapsulates full inference contract: accepts raw telemetry (10 sensors + `Machine_Type`) and auto-derives physics features (`+physics`) via `apply_feature_set`; handles missing sensor values (median imputation) and unseen machine categories; enforces leakage guards; evaluates operational threshold $t^* = 0.16$; assigns operational risk bands (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). Implemented automated 10-step technical promotion gate verifying artifact loading, schema, bounds, threshold obedience, risk-band rules, and metadata before alias promotion. Registered model `edgetwin-risk` in MLflow, assigning `challenger` alias then promoting to `champion` upon passing gate. Generated comprehensive `docs/ml/model_card.md` using historical frozen S04/S05 metrics (ZERO test set re-evaluation).
- **Acceptance:** Successfully registered `edgetwin-risk` (Version 2) in `sqlite:///mlflow.db`; loadable via `models:/edgetwin-risk@champion`; verified round-trip inference on raw telemetry.
- **Tests:** 16 tests in `tests/mlops/test_register.py` covering raw telemetry handling, physics auto-generation, NaN handling, unseen category handling, leakage rejection, output schema, threshold consistency, promotion gate success/rejection, and MLflow lifecycle.
- **Status:** DONE

---
## PHASE 2 — Contract and simulation

### T-020 Telemetry contract v1
- **Goal:** Single source of truth for wire messages and bridge to ML inference.
- **Files:** `docs/api/telemetry.v1.schema.json`, `simulation/contract.py`, `tests/contract/test_telemetry_contract.py`, `tests/contract/test_telemetry_ml_compat.py`.
- **Depends:** T-001.
- **Implementation:** Draft 2020-12 JSON Schema (`edgetwin.telemetry.v1`) with nulls supported for missing sensors, `provenance` enum, `seq`, ISO-8601 UTC `ts`, sensor range validation against authoritative `SENSOR_RANGES`, quality flags (`OK`, `OUT_OF_RANGE`, `STALE`, `MISSING`, `LIMIT_WARN`, `LIMIT_ALARM`), and edge diagnostic fields (`delta_t_c`, `power_va`, `trip`, `buffered`). Implemented `TelemetryValidator` with safe/non-crashing JSON parsing, schema enforcement, MQTT topic-payload machine ID consistency, missing-value quality marking, strict leakage guard rejecting forbidden fields (`Failure_Type`, `Machine_Failure`, `Sensor_Batch_Code`, `Checksum_Flag`), sequence tracking, and diagnostic comparison against backend calculations with approved tolerances ($\Delta T = 0.2\,^\circ\text{C}$, Apparent Power = $5.0\text{ VA}$). Implemented `telemetry_to_feature_df` adapter resolving `Machine_Type` via `MACHINE_ID_PREFIX_MAP` (fallback "Unknown") and producing exactly 11 columns (10 raw sensors + `Machine_Type`) so champion model auto-derives physics features without caller computation.
- **Acceptance:** 55 tests passing across `test_telemetry_contract.py` (39 tests) and `test_telemetry_ml_compat.py` (16 tests); verified round-trip inference with frozen `models:/edgetwin-risk@champion`, leakage absence, and diagnostic isolation.
- **Status:** DONE

### T-021 Scenario spec and process model
- **Goal:** Reproducible fault scenarios derived from empirical data and coupled physics process model.
- **Files:** `simulation/scenarios/*.yaml` (8 scenarios), `simulation/process_model.py`, `docs/dataset/fault_signatures.md`, `tests/simulation/test_scenarios.py`.
- **Depends:** T-003, T-020.
- **Implementation:** Coupled physical process equations in `SimulatedMachine` maintaining real-world thermodynamic and electro-mechanical relationships between temperature, current, voltage, power, torque, RPM, vibration, pressure, tool wear, and operating hours; deterministic seed (`seed=42`) and replay timestamps; five-state finite state machine (`STOPPED`, `STARTING`, `RUNNING`, `DEGRADING`, `TRIPPED`). Documented empirical parameters versus simulation assumptions in `docs/dataset/fault_signatures.md` across 8 scenarios (SCN-01 to SCN-08). Evaluated scenarios through frozen `models:/edgetwin-risk@champion`, IsolationForest anomaly detector, and Layer 4 Health Score engine.
- **Acceptance:** SCN-01 healthy nominal mean $p_{\text{fail}} = 0.0117$, max $p_{\text{fail}} = 0.0292 \le 0.05$ (PASSED); SCN-02 heat dissipation degraded $p_{\text{fail}} = 0.8940 \ge 0.16$ (PASSED, top SHAP factors: `Process_Temperature_C`, `Current_A`, `Tool_Wear_Min`); SCN-03 overstrain degraded $p_{\text{fail}} = 0.8790 \ge 0.16$ (PASSED); SCN-04 power failure active fault $p_{\text{fail}} = 0.8992 \ge 0.16$ before safety trip and post-trip `TRIP_OVERLOAD` (PASSED); SCN-05 tool wear $\ge 240$ min triggers `MAINTENANCE_REQUIRED` health state and late $p_{\text{fail}} = 0.8886$ (PASSED); SCN-06 random vibration fault $p_{\text{fail}} = 0.8973 \ge 0.16$ (PASSED, top SHAP factor: `Vibration_mm_s`); SCN-07 sensor dropout handled without crash (PASSED); SCN-08 machine offline halts telemetry after step 10 (PASSED). 13 tests passing in `tests/simulation/test_scenarios.py`.
- **Status:** DONE

### T-022 Virtual edge (Python)
- **Goal:** Firmware-equivalent publisher for CI and for development without Wokwi.
- **Files:** `simulation/virtual_edge.py`, `tests/simulation/test_virtual_edge.py`.
- **Depends:** T-020, T-021.
- **Implementation:** `VirtualEdge` wraps `SimulatedMachine`, uses `paho-mqtt` 2.0 (`CallbackAPIVersion.VERSION2`) to publish canonical telemetry on `edgetwin/v1/{machine_id}/telemetry` (QoS 1) with pre-publish validation. Retained status and LWT on `edgetwin/v1/{machine_id}/status`. Built-in explicit state machine handles network drops with a ring buffer (capacity 1000) and automatic flush on reconnect.
- **Acceptance:** publishes valid v1 messages at configurable rate; ring buffer stores messages during disconnection and flushes on reconnect; LWT configured.
- **Tests:** 4 unit tests in `tests/simulation/test_virtual_edge.py`; live integration test in `tests/integration/test_mqtt_integration.py`.
- **Status:** DONE

### T-023 Broker and connectivity setup
- **Goal:** MQTT works for both Wokwi paths.
- **Files:** `docker-compose.yml`, `mosquitto/mosquitto.conf`, `docs/wokwi/connectivity.md`.
- **Depends:** T-001.
- **Implementation:** Mosquitto 2.0 container configured in `docker-compose.yml` on port 1883; `mosquitto/mosquitto.conf` for local development; `docs/wokwi/connectivity.md` documenting canonical topics and connectivity paths.
- **Acceptance:** `docker-compose.yml` broker service; anonymous local dev access; canonical topics documented.
- **Tests:** `tests/integration/test_mqtt_integration.py`.
- **Status:** DONE

---
## PHASE 3 — Wokwi and edge (feasibility first)

| ID | Goal | Depends | Acceptance (short) | Status |
|---|---|---|---|---|
| T-040 | **Feasibility spike:** Determine technically viable Wokwi connectivity path (Path A vs Path B) and ESP32 library/sensor feasibility | T-023 | Path A selected (zero recurring cost); library constraints analyzed; decision documented in memory.md | DONE |
| T-041 | Firmware v1: DHT22 + NTC + MPU6050 + slide pot + process model → contract v1 | T-040, T-021 | valid telemetry at 1 Hz; modular C++ edge architecture; diagram.json; contract tests pass | DONE |
| T-042 | Firmware v2: validation, ΔT/VA/RMS, safety trips + LED, ring buffer, LWT, `cmd` subscribe | T-041 | trip fires with backend down; buffered messages flush on reconnect; command validation; status/LWT | DONE |
| T-043 | Wokwi ↔ backend integration checklist (manual) + optional Wokwi CI scenario if a token/plan allows | T-042, T-032 | documented repeatable procedure; CI runner; E2E integration verified | DONE |
| T-044 | *(stretch)* shallow-tree edge screening, disagreement metric | T-016, T-042 | tree ≤ 4 KB; agreement with cloud reported | TODO (stretch) |

### T-043 Wokwi ↔ backend integration & CI verification
- **Goal:** Repeatable manual checklist and automated simulation runner verifying edge-to-backend pipeline, plus secret-safe GitHub Actions CI.
- **Files:** `docs/wokwi/integration_guide.md`, `simulation/wokwi_runner.py`, `.github/workflows/ci.yml`, `tests/simulation/test_wokwi_runner.py`, `tests/integration/test_edge_e2e_pipeline.py`.
- **Depends:** T-042, T-032.
- **Implementation:** Documented 10-stage integration checklist for Path A (Cloud HiveMQ TLS 8883) and Path B (Local Mosquitto 1883). Automated simulation runner (`simulation/wokwi_runner.py`) detecting host toolchains, running native firmware tests via host g++, reporting missing Wokwi prerequisites without fabricating execution, and verifying E2E telemetry ingestion into DB and Digital Twin. Multi-stage GitHub Actions CI (`.github/workflows/ci.yml`) covering linting, native C++ firmware tests, pytest suite, and secret-safe Wokwi action.
- **Acceptance:** 10-stage integration procedure documented; native C++ firmware tests pass; E2E edge-to-backend integration tests pass; Wokwi runner returns deterministic status; CI pipeline defined without hardcoded secrets.
- **Tests:** 6 tests in `tests/simulation/test_wokwi_runner.py`, 7 tests in `tests/integration/test_edge_e2e_pipeline.py`.
- **Status:** DONE


---
## PHASE 4 — Backend (compact; expanded before start)
| ID | Goal | Depends | Acceptance (short) | Status |
|---|---|---|---|---|
| T-030 | FastAPI skeleton, settings, structured logging, `/health`, `/ready`, Dockerfile | T-001 | container serves `/health` and `/ready`, RFC 7807 error format, CORS | DONE |
| T-031 | DB schema + Alembic migrations (architecture.md §12) | T-030 | 8 domain tables migrated up/down cleanly with indices & constraints | DONE |
| T-032 | MQTT ingest + validation + persistence + reconnect | T-020, T-023, T-031 | bad payloads rejected with reason, none crash the consumer | DONE |
| T-033 | Inference service (load champion, shared features, explain) | T-016, T-011 | p95 inference < 50 ms | DONE |
| T-034 | Health engine L1–L6 with hysteresis + recommendations | T-014 | full decision table unit-tested | DONE |
| T-035 | Digital Twin service (state, sync FSM, snapshots) | T-034 | twin updates < 500 ms after ingest; STALE/OFFLINE work | DONE |
| T-036 | REST API v1 + OpenAPI | T-035 | contract tests pass | DONE |
| T-037 | WebSocket live stream | T-035 | multi-client fan-out test | DONE |
| T-038 | JWT auth + 3 roles, command endpoint guard | T-036 | role matrix tested | DONE |

## PHASE 5 — Frontend (starts after design reference is received)
| ID | Goal | Depends | Status |
|---|---|---|---|
| T-050 | Design tokens + component kit from `design.md` (+ reference analysis) | design reference | DONE |
| T-051 | App shell, routing, API client, WS hook | T-036, T-037 | DONE |
| T-052 | Fleet dashboard | T-051 | DONE |
| T-053 | Machine detail + live monitoring | T-051 | DONE |
| T-054 | Digital Twin view (SVG schematic) | T-053 | DONE |
| T-055 | Predictions + explanations panel | T-053 | DONE |
| T-056 | Alerts + maintenance workflow + feedback | T-055 | DONE |
| T-057 | History and analytics | T-053 | DONE |
| T-058 | Model / MLOps page + scenario control | T-060 | DONE |

### T-050 Design Tokens & Component Kit
- **Goal:** Synthesize design references (Browser Use, Deepgram, LaunchDarkly) into an original, dark-first industrial AI control room design system and reusable component kit.
- **Files:** `dashboard/src/index.css`, `dashboard/src/components/common/Button.tsx`, `IconButton.tsx`, `Card.tsx`, `StatusBadge.tsx`, `HealthBadge.tsx`, `Metric.tsx`, `MetricGrid.tsx`, `DataTable.tsx`, `Input.tsx`, `Select.tsx`, `Modal.tsx`, `Toast.tsx`, `LoadingState.tsx`, `EmptyState.tsx`, `ErrorState.tsx`, `ConnectionIndicator.tsx`, `LiveIndicator.tsx`, `RoleGate.tsx`.
- **Depends:** Design references (Browser Use, Deepgram, LaunchDarkly), `design.md`.
- **Implementation:** Defined comprehensive design tokens (canvas `#0B0B0C`, surfaces `#101014` / `#18181B`, cyan accent `#149AFB`, operational green `#13EF95`, warning orange `#FE750E`, danger red `#EF4444`, slate maintenance `#8C9AC4`). Enforced sharp action controls (4px radius) vs rounded content cards (8-16px) tension. Implemented non-color-only status badges with geometric shapes (●, ▲, ■, ◆, ○) and accessible text labels. Built 17 reusable UI components.
- **Acceptance:** Component kit unit tests pass; all tokens contrast-checked; zero generic templates; responsive and accessible.
- **Tests:** `dashboard/tests/components.test.tsx` (9 tests), `dashboard/tests/rbac.test.ts` (7 tests).
- **Status:** DONE

### T-051 App Shell, Routing, Typed API Client & WebSocket Live Stream
- **Goal:** Implement persistent industrial application shell, routing, authentication state, RBAC utilities, typed API client with RFC 7807 error parsing, and live twin WebSocket client.
- **Files:** `dashboard/src/components/layout/AppShell.tsx`, `Sidebar.tsx`, `TopHeader.tsx`, `PageHeader.tsx`, `dashboard/src/api/client.ts`, `dashboard/src/api/websocket.ts`, `dashboard/src/context/AuthContext.tsx`, `dashboard/src/hooks/useAuth.ts`, `dashboard/src/hooks/useTwinWebSocket.ts`, `dashboard/src/utils/rbac.ts`, `dashboard/src/App.tsx`, `dashboard/src/pages/*.tsx`.
- **Depends:** T-036, T-037.
- **Implementation:** Created persistent navigation shell with responsive drawer. Implemented `AuthProvider` with token persistence, profile fetching, auto-logout on 401, and `ProtectedRoute`. Built typed API client handling RFC 7807 problem details across all status codes. Developed auto-reconnecting `TwinWebSocketClient` with keepalive ping/pong frames. Implemented route shells for all primary platform views (`/dashboard`, `/machines`, `/alerts`, `/maintenance`, `/scenarios`, `/mlops`, `/settings`, `/login`, `*`). Enforced data honesty with truthful empty states when backend has no active telemetry.
- **Acceptance:** Full auth lifecycle tested; protected routes redirect cleanly; API client parses RFC 7807; WebSocket manages connection states; Vitest suite and Vite production build pass.
- **Tests:** `dashboard/tests/auth.test.tsx` (4 tests), `dashboard/tests/apiClient.test.ts` (4 tests), `dashboard/tests/websocket.test.ts` (3 tests).
- **Status:** DONE

### T-052 Fleet Dashboard
- **Goal:** Production-grade operational fleet overview integrating real backend REST APIs, live twin WebSocket streaming (1 Hz), operational KPI cards, status filtering, multi-field search, risk-based sorting, high-density table and card views, active incident triage ticker with RBAC acknowledgment, and truthful empty states.
- **Files:** `dashboard/src/pages/DashboardPage.tsx`, `dashboard/src/api/client.ts`, `dashboard/src/types/machine.ts`, `dashboard/src/types/alert.ts`, `dashboard/src/utils/formatters.ts`, `dashboard/src/components/common/HealthBadge.tsx`, `dashboard/src/components/common/StatusBadge.tsx`, `dashboard/tests/dashboard.test.tsx`.
- **Depends:** T-051.
- **Implementation:** Built fleet overview landing page (`/dashboard`). Integrated `useTwinWebSocket` passing JWT authentication token, merging real-time twin state changes (health scores, failure probabilities, operating/connectivity states, timestamps) reactively into the machine fleet. Implemented 4 operational KPI metrics (Total Machines, Active Running, Fleet Health, Active Alarms) with status lines and contextual deltas. Provided 5 status filter tabs (All, Attention Needed, Healthy, Tripped, Offline), real-time search (by Machine ID, Type, Location), and sort controls (Risk, Health Index, ID). Added dual-view toggle between high-density technical `DataTable` and responsive visual asset cards with mini health meters and calibrated risk highlights ($t^* = 0.16$). Integrated active alert incident triage panel with role-gated acknowledgment (`RoleGate` + `api.alerts.acknowledge`) and floating feedback toasts. Harmonized client list API responses to handle both flat arrays and `{ items, total }` paginated envelopes. Enforced truthful empty and error states.
- **Acceptance:** Full fleet lifecycle tested; live WebSocket twin updates merge at 1 Hz; table and card view toggles functional; active incident acknowledgment verified; Vitest suite (37 passed across 6 test suites) and Vite production build pass cleanly.
- **Tests:** `dashboard/tests/dashboard.test.tsx` (10 tests).
- **Status:** DONE

### T-053 Machine Detail & Live Telemetry Monitoring
- **Goal:** Comprehensive per-machine operational view at `/machines/:id` displaying machine identity, canonical Digital Twin state, calibrated ML failure risk ($t^* = 0.16$), priority operational sensor readings, historical telemetry, zero-dependency SVG time-series charts, and 1 Hz live WebSocket streaming.
- **Files:** `dashboard/src/pages/MachineDetailPage.tsx`, `dashboard/src/components/machine/MachineHeader.tsx`, `dashboard/src/components/machine/MachineStatusSummary.tsx`, `dashboard/src/components/machine/TelemetryMetricGrid.tsx`, `dashboard/src/components/machine/TelemetryChart.tsx`, `dashboard/src/components/machine/RawTelemetryTable.tsx`, `dashboard/src/api/client.ts`, `dashboard/src/types/machine.ts`, `dashboard/src/App.tsx`, `dashboard/src/pages/MachinesPage.tsx`, `dashboard/src/pages/DashboardPage.tsx`, `dashboard/tests/machineDetail.test.tsx`.
- **Depends:** T-051.
- **Implementation:** Created operational machine view at `/machines/:id`. Designed `MachineHeader` featuring "← Fleet" back-navigation, machine ID, equipment type, plant location, `StatusBadge`, `HealthBadge`, and connection status. Built `MachineStatusSummary` presenting backend-authoritative health score, calibrated failure probability $p_{fail}$, risk band, operating state, connection state, last packet sequence, and model version. Implemented `TelemetryMetricGrid` prioritizing core operational signals (process temp, vibration RMS, speed RPM, torque, current) and secondary signals (pressure, voltage, tool wear, operating hours), strictly preserving null sensor values as `—` (never converted to 0). Engineered zero-dependency pure React + SVG `TelemetryChart` with dynamic domain scaling, horizontal gridlines, threshold indicators, hover crosshair & tooltip card, and pulsing live update dots. Integrated machine-specific WebSocket stream `/ws/live/{machine_id}` appending live points into a bounded 100-sample buffer without page reloads. Provided dual-view toggle between multi-signal charts and raw observations `DataTable`. Handled 404 Machine Not Found with clear return navigation, network error retry states, and truthful empty states when no history exists. Connected fleet table rows and cards to navigate to `/machines/:id`.
- **Acceptance:** All 12 session test requirements satisfied (route rendering, machine loading, 404 handling, twin state, current telemetry, historical telemetry, truthful null handling, live WebSocket updates, live telemetry metrics, connection states, empty history, back-to-fleet navigation); Vitest suite passes (49 tests across 7 test files); backend regression passes (588 passed, 1 skipped); TypeScript and Vite production build pass cleanly.
- **Tests:** `dashboard/tests/machineDetail.test.tsx` (12 tests).
- **Status:** DONE

### T-054 Digital Twin Visualization
- **Goal:** Implement an operationally informative, accessible SVG schematic representing the machine Digital Twin, communicating machine identity, equipment type, operating state (RUNNING with rotational pulse, STOPPED, STARTING, DEGRADING, TRIPPED with interlock banner), live connectivity (LIVE/STALE/OFFLINE), circular conic health gauge, and spatial sensor overlays mapped with real telemetry and quality indicators.
- **Files:** `dashboard/src/components/machine/DigitalTwinView.tsx`, `dashboard/src/pages/MachineDetailPage.tsx`, `dashboard/tests/digitalTwinPredictions.test.tsx`.
- **Depends:** T-053.
- **Implementation:** Engineered pure React + SVG industrial induction motor schematic featuring cooling fins, fan cowl, terminal junction box, drive shaft keyway, and rotor center core. Dynamic visual state treatments: active rotational indicator when `RUNNING`, controlled startup pulse when `STARTING`, warning accent glow when `DEGRADING`, and safety trip interlock banner when `TRIPPED`. Integrated high-contrast circular conic health gauge directly from backend `health_score` (never recalculated). Positioned spatial sensor callout cards displaying core operational signals (process temp, vibration RMS, speed RPM, torque, current, pressure, tool wear) with correct engineering units and backend quality tags (`LIMIT_WARN`, `LIMIT_ALARM`, `OUT_OF_RANGE`). Encapsulated accessible labeling via `role="img"` container with comprehensive `aria-label`. Wired live WebSocket updates seamlessly at 1 Hz via `/ws/live/{machine_id}` without full page reloads.
- **Acceptance:** All 8 task test requirements passed (machine identity, operating state, health score/badge, current sensors with quality flags, live WebSocket updates, LIVE/STALE/OFFLINE, RUNNING/STOPPED/TRIPPED states, accessible labeling); Vitest suite passes cleanly; zero 3D/Three.js bloat.
- **Tests:** `dashboard/tests/digitalTwinPredictions.test.tsx` (tests 1–8).
- **Status:** DONE

### T-055 Predictions & Explanations Panel
- **Goal:** Implement a dedicated AI predictive assessment and model explainability panel presenting calibrated failure probability ($p_{fail}$), operational risk bands (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), project decision threshold ($t^* = 0.16$), unsupervised anomaly detection score & flag (Isolation Forest), model version (`v1.2-xgb`), prediction timestamp, horizontal TreeSHAP feature attributions in model margin space, honest non-causal disclaimer, and backend system maintenance recommendations.
- **Files:** `dashboard/src/components/machine/PredictionPanel.tsx`, `dashboard/src/components/machine/FeatureContributions.tsx`, `dashboard/src/components/machine/RecommendationPanel.tsx`, `dashboard/src/types/prediction.ts`, `dashboard/src/api/client.ts`, `dashboard/src/pages/MachineDetailPage.tsx`, `dashboard/tests/digitalTwinPredictions.test.tsx`.
- **Depends:** T-053.
- **Implementation:** Built `PredictionPanel` unifying supervised risk metrics, anomaly detection, governance timing, explainability, and operational recommendations. Extracted backend `failure_probability` and operational risk band with semantic badge treatments. Highlighted project operating threshold $t^* = 0.16$. Rendered unsupervised anomaly score and `ANOMALY DETECTED` vs `NOMINAL` status. Built `FeatureContributions` rendering proportional horizontal TreeSHAP margin attribution bars distinguishing positive risk-increasing contributions (`+0.310`, red/danger) from negative risk-reducing contributions (`-0.050`, green/success), alongside explicit raw feature values (`Value: 8.20 mm/s`) to avoid confusing values with contributions. Embedded mandatory scientific non-causal disclaimer. Created `RecommendationPanel` displaying backend action codes (`INSPECT_BEARING`), priority badges, target component, and engineering reasoning. Implemented non-destructive prediction fetching fallback via `api.machines.getPredictions(id, { limit: 1 })`, ensuring prediction API failures never break the machine page and ordinary telemetry packets never trigger redundant explanation requests.
- **Acceptance:** All 14 task test requirements passed (calibrated probability, risk band, decision threshold $t^* = 0.16$, anomaly state, model version, feature contributions, positive/negative direction distinction, value vs contribution separation, non-causal disclaimer, recommendation rendering, empty state handling, explanation API error resilience, live prediction updates, duplicate request prevention); Vitest suite passes cleanly (71 total tests); backend regression passes (588 passed, 1 skipped).
- **Tests:** `dashboard/tests/digitalTwinPredictions.test.tsx` (tests 9–22).
- **Status:** DONE

### T-056 Alerts + Maintenance Workflow & Feedback
- **Goal:** Implement end-to-end operational workflow connecting AI risk alerts, human acknowledgment, incident triage, maintenance event/work-order creation & updates, and operator feedback persistence with ground-truth evaluation, avoiding duplicate submissions, and integrating across Fleet Dashboard, Machine Detail, and dedicated Alerts & Maintenance pages.
- **Files:** `api/app/models/alert.py`, `api/app/models/maintenance.py`, `api/app/schemas/maintenance.py`, `api/app/schemas/feedback.py`, `api/app/services/alert_service.py`, `api/app/services/maintenance_service.py`, `api/app/services/feedback_service.py`, `api/app/routes/maintenance.py`, `api/app/routes/alerts.py`, `api/app/routes/machines.py`, `api/migrations/versions/0003_add_alert_id_to_maintenance.py`, `dashboard/src/types/maintenance.ts`, `dashboard/src/types/feedback.ts`, `dashboard/src/types/alert.ts`, `dashboard/src/api/client.ts`, `dashboard/src/components/alerts/AlertDetailModal.tsx`, `dashboard/src/components/maintenance/CreateWorkOrderModal.tsx`, `dashboard/src/components/maintenance/UpdateWorkOrderModal.tsx`, `dashboard/src/components/feedback/OperatorFeedbackModal.tsx`, `dashboard/src/pages/AlertsPage.tsx`, `dashboard/src/pages/MaintenancePage.tsx`, `dashboard/src/pages/MachineDetailPage.tsx`, `dashboard/tests/alertsWorkflow.test.tsx`, `tests/api/test_alerts_maintenance_feedback.py`.
- **Depends:** T-054, T-055.
- **Implementation:** Added `alert_id` foreign key with SQLite support to `maintenance_events` model and Alembic migration `0003_add_alert_id_to_maintenance.py`. Implemented `MaintenanceService` with listing, detail, creation (validating machine and linked alert existence and consistency), and lifecycle updates (`PLANNED` -> `IN_PROGRESS` -> `COMPLETED`/`CANCELLED` with automated timestamping). Enhanced `AlertService` with single alert lookup and strict transition rules (cannot re-open `RESOLVED` alerts). Enhanced `FeedbackService` with duplicate submission detection (raises `409 Conflict` on duplicate machine/alert feedback) and machine feedback querying. Added dedicated REST endpoints under `/api/v1/maintenance` and extended `/api/v1/alerts` and `/api/v1/machines`. Built comprehensive frontend operational components: `AlertDetailModal` for incident triage, `CreateWorkOrderModal` with AI recommendation prefill, `UpdateWorkOrderModal` for technician workflow progression, and `OperatorFeedbackModal` with ground-truth evaluation and non-retraining disclaimer. Connected workflows into `/alerts`, `/maintenance`, and `/machines/:id` (Operational Activity section). Role-gated actions to `ADMIN` and `MAINTENANCE_ENGINEER` while allowing `OPERATOR` feedback submission and viewing.
- **Acceptance:** Full operational lifecycle verified; alert acknowledgment and resolution persisted in database; maintenance work orders created from alerts and AI recommendations; operator feedback recorded with ground-truth verification and duplicate rejection; RBAC enforced at API and UI levels; 14 new backend unit/integration tests pass; 11 new frontend integration tests pass; all 82 frontend tests and all 230 API tests pass.
- **Tests:** `dashboard/tests/alertsWorkflow.test.tsx` (11 tests), `tests/api/test_alerts_maintenance_feedback.py` (14 tests).
- **Status:** DONE

### T-057 History and Analytics View
- **Goal:** Implement a dedicated operational historical analytics experience at `/history` enabling operators and reliability engineers to analyze machine telemetry, composite health index trends, sensor observations, persisted ML model assessments, incident alert timelines, maintenance work order progression, and fleet-wide health/risk distribution retrospectively across bounded time windows (1h, 6h, 24h, 7d, 30d).
- **Files:** `api/app/schemas/history.py`, `api/app/services/history_service.py`, `api/app/routes/history.py`, `api/app/main.py`, `api/app/routes/__init__.py`, `dashboard/src/types/history.ts`, `dashboard/src/api/client.ts`, `dashboard/src/components/history/HistoricalHealthChart.tsx`, `dashboard/src/components/history/HistoricalSensorChart.tsx`, `dashboard/src/components/history/HistoricalPredictionTimeline.tsx`, `dashboard/src/components/history/HistoricalEventTimeline.tsx`, `dashboard/src/components/history/FleetAnalyticsSection.tsx`, `dashboard/src/pages/HistoryPage.tsx`, `dashboard/src/App.tsx`, `dashboard/src/components/layout/Sidebar.tsx`, `tests/api/test_history.py`, `dashboard/tests/historyAnalytics.test.tsx`.
- **Depends:** T-053, T-055, T-056.
- **Implementation:**
  - Built backend `HistoryService` querying existing database models (`TelemetryRecord`, `PredictionRecord`, `AlertRecord`, `MaintenanceEventRecord`, `MachineRecord`) without duplicating storage.
  - Formulated defensible duration calculations for time-in-warning and time-in-critical without unwarranted continuous extrapolation over sparse observations (`MAX_SAMPLE_GAP_SECONDS = 300`).
  - Implemented configurable downsampling for high-density telemetry across historical horizons (1h/6h raw up to 1000 points, 24h 60s bins, 7d 15m bins, 30d 1h bins) and surfaced downsampling metadata (`is_downsampled`, `downsample_interval_s`).
  - Normalized all datetimes strictly to timezone-aware UTC (`ensure_utc`), supporting ISO 8601 formatting and explicit query boundary checks (`to_ts >= from_ts`).
  - Added authenticated REST endpoints under `/api/v1/history`: `GET /machines/{machine_id}` and `GET /fleet` with comprehensive Pydantic validation schemas. Enforced read-only RBAC accessible to all authenticated operational roles (`OPERATOR`, `MAINTENANCE_ENGINEER`, `ADMIN`).
  - Built frontend `/history` route with Scope selector (Fleet Overview or specific machine) and Horizon selector (1h, 6h, 24h, 7d, 30d).
  - Implemented pure React + SVG `HistoricalHealthChart` featuring threshold guidelines (>=80 Healthy, 60-79 Warning, <60 Critical), area gradients, interactive crosshairs, and hover tooltips.
  - Implemented pure React + SVG `HistoricalSensorChart` supporting interactive switching across 8 telemetry sensors (Process Temp, Vibration RMS, Speed RPM, Torque, Pressure, Current, Voltage, Tool Wear) with dynamic scaling, min/avg/max KPIs, and downsample status badge.
  - Built `HistoricalPredictionTimeline` presenting persisted ML inference records ($p_{fail}$, risk bands, anomaly status, TreeSHAP margin factors, model version) with honest empty states when no predictions exist.
  - Built `HistoricalEventTimeline` with tabbed views for incident alerts (supporting status filters: All, Open, Acknowledged, Resolved) and maintenance work orders.
  - Implemented `FleetAnalyticsSection` featuring fleet health/risk distribution meters, fleet summary KPI cards, and machine retrospective triage table with direct drilldown.
- **Acceptance:** Full historical retrieval verified; defensible durations calculated correctly; downsampling prevents browser memory exhaustion; timezone-aware UTC consistency maintained; truthful empty states rendered; RBAC permissions verified; 15 new backend tests in `tests/api/test_history.py` pass; 10 new frontend integration tests in `dashboard/tests/historyAnalytics.test.tsx` pass; all 707 backend tests and 118 frontend tests pass; TypeScript and Vite production build pass cleanly; all ML models, calibrations, thresholds ($t^*=0.160$), and held-out test data strictly preserved.
- **Tests:** `tests/api/test_history.py` (15 tests), `dashboard/tests/historyAnalytics.test.tsx` (10 tests).
- **Status:** DONE

### T-058 Model / MLOps Page + Scenario-Control UI
- **Goal:** Build a controlled demonstration and simulation Scenario Control layer integrated directly into the MLOps dashboard (`/mlops`) and standalone scenarios page (`/scenarios`), allowing authorized operators (`ADMIN`, `MAINTENANCE_ENGINEER`) to trigger canonical machine/telemetry fault scenarios (`SCN-01` to `SCN-08`) under strict backend command-guard authorization without free-form telemetry injection or ML model modifications.
- **Files:** `dashboard/src/components/mlops/ScenarioControlPanel.tsx`, `dashboard/src/pages/MLOpsPage.tsx`, `dashboard/src/pages/ScenariosPage.tsx`, `dashboard/src/api/client.ts`, `dashboard/src/types/scenario.ts`, `dashboard/tests/scenarioControl.test.tsx`.
- **Depends:** T-060, T-061, T-021.
- **Implementation:**
  - Preserved intact all S23 drift monitoring (PSI, KS, feedback accuracy) and S24 model lifecycle & governance (MLflow model registry, champion/challenger comparison, promotion gate, rollback, audit trail) on `/mlops`.
  - Added 3rd sub-tab "Scenario Control" to `/mlops` and unified standalone `/scenarios` view using `ScenarioControlPanel`.
  - Dynamically loads fleet machines via `api.machines.list()` and 8 backend canonical simulation scenarios (`SCN-01` Healthy Nominal through `SCN-08` Machine Offline) via `api.scenarios.list()`.
  - Built comprehensive Scenario Preview card detailing target asset, scenario ID, failure mechanism, command safety guard ("Preset Enforced — No Arbitrary Injection"), estimated duration, current machine operating state, and RBAC authorization requirement.
  - Implemented two-step modal confirmation workflow for dispatching scenarios to prevent accidental double-clicks or accidental triggering via dropdown selection changes.
  - Provided quick "Select Baseline (SCN-01)" action button to rapidly reset machine to nominal healthy operation.
  - Enforced strict client and backend RBAC: `RoleGate` restricts dispatch mutation to `ADMIN` and `MAINTENANCE_ENGINEER`; unauthorized `OPERATOR` users are provided with read-only observation mode with disabled buttons.
  - Surfaced backend RFC 7807 problem details (403 Forbidden, 404 Machine Not Found, 409/422 Unsafe parameter) gracefully within confirmation modal and toast notifications.
  - Tracked recent session command acknowledgments in an audit table displaying Command ID, target machine, scenario code, status (`ACCEPTED`), authorizing user, timestamp, and server acknowledgment message.
- **Acceptance:** All 20 task test requirements satisfied; 11 new Vitest unit and integration tests passing; full frontend suite (108 tests across 12 files) passing; TypeScript `tsc --noEmit` and Vite production build passing cleanly; all backend scenario command-guard tests (7 passed) passing; zero modification to ML models, calibration, threshold ($t^*=0.160$), drift logic, or test data.
- **Tests:** `dashboard/tests/scenarioControl.test.tsx` (11 tests), `tests/api/test_auth.py` (`TestCommandGuardAndScenarios`, 7 tests).
- **Status:** DONE

## PHASE 6 — MLOps
| ID | Goal | Depends | Status |
|---|---|---|---|
| T-060 | Drift monitor (PSI/KS) vs training reference + feedback-based performance tracking | T-035 | DONE |
| T-061 | Retrain pipeline, champion/challenger gate, promotion, rollback | T-060, T-016 | DONE |
| T-062 | GitHub Actions CI (lint, unit, contract, ML smoke, image build) | T-001 | DONE |
| T-063 | Full `docker compose` stack | T-030 | DONE |

### T-060 Drift Monitor (PSI/KS) vs Training Reference + Feedback-based Performance Tracking
- **Goal:** Implement production-oriented MLOps monitoring comparing current operational telemetry against authorized training baseline distributions using Population Stability Index (PSI) and two-sample Kolmogorov-Smirnov (KS) tests, alongside ground-truth model performance tracking (running precision, recall, false-alarm rate) derived from persisted operator feedback records, with an operational MLOps dashboard at `/mlops`.
- **Files:** `mlops/drift.py`, `mlops/feedback_metrics.py`, `artifacts/training_reference_stats.json`, `api/app/schemas/mlops.py`, `api/app/schemas/feedback.py`, `api/app/services/mlops_service.py`, `api/app/routes/mlops.py`, `api/app/main.py`, `dashboard/src/types/mlops.ts`, `dashboard/src/api/client.ts`, `dashboard/src/pages/MLOpsPage.tsx`, `tests/mlops/test_drift.py`, `tests/mlops/test_feedback_metrics.py`, `tests/api/test_mlops_api.py`, `dashboard/tests/mlopsPage.test.tsx`.
- **Depends:** T-035, T-056.
- **Implementation:**
  - Engineered core statistical drift engine in `mlops/drift.py`: 13 continuous features + 1 categorical (`Machine_Type`).
  - Implemented stable quantile-based reference decile binning with $[-\infty, +\infty]$ bounds, zero-frequency $\epsilon = 10^{-4}$ smoothing, and missing value exclusion.
  - Implemented categorical PSI comparing class proportions with `__OTHER__` unseen category handling.
  - Implemented continuous two-sample Kolmogorov-Smirnov test (`scipy.stats.ks_2samp`) exposing test statistic $D$ and $p$-value; explicitly excluded categorical `Machine_Type` from KS (returns `None` / N/A).
  - Enforced small-sample sufficiency guard ($n < 30 \implies \text{INSUFFICIENT\_DATA}$) to prevent manufactured drift conclusions.
  - Defined operational heuristic thresholds: PSI $<0.10$ STABLE, $[0.10, 0.25)$ WATCH, $\ge 0.25$ DRIFT; KS $p < 0.05$ and $D \ge 0.15 \implies \text{DRIFT}$.
  - Computed and serialized immutable baseline reference statistics from `data/interim/splits/train.csv` (version `v1.0-train-split`, 42 machines, 6,897 samples). Held-out test set `data/test/` strictly untouched.
  - Developed `mlops/feedback_metrics.py`: extracts operator feedback records (`CONFIRMED`, `FALSE_ALARM`, `INCONCLUSIVE`). Correctly excludes `INCONCLUSIVE` from binary precision and recall denominators.
  - Computes running precision ($TP / (TP + FP)$), recall estimate ($TP / (TP + FN)$), and operational false-alarm rate ($FP / \text{Total}$). Explicitly avoids confusing $1 - \text{precision}$ with false-alarm rate.
  - Required minimum 5 evaluated labels before reporting performance metrics, otherwise displaying `INSUFFICIENT_DATA` (never fabricating 0%).
  - Added authenticated backend REST endpoints under `/api/v1/mlops`: `GET /overview`, `GET /drift`, `GET /performance`. Enforced RBAC (read access for all authenticated roles).
  - Enhanced dashboard at `/mlops`: model governance strip (champion `v1.2-xgb`, reference `v1.0-train-split`, cutoff $t^*=0.160$), 4 KPI metric cards, active drift alert banner, status-tabbed and searchable feature drift `DataTable`, feedback status breakdown with visual distribution meter, and data science governance disclaimer.
- **Acceptance:** Reference baseline generated exclusively from training split without test contamination; PSI and KS detectors deterministic with edge case handling; operator feedback evaluated truthfully; all ML invariants (XGBoost, calibration, cutoff, health formula, Isolation Forest, TreeSHAP) frozen with zero automatic retraining or promotion; 13 drift tests, 6 feedback tests, 6 API tests, 10 frontend tests pass cleanly; full 271 backend tests and 92 frontend tests pass.
- **Tests:** `tests/mlops/test_drift.py` (13 tests), `tests/mlops/test_feedback_metrics.py` (6 tests), `tests/api/test_mlops_api.py` (6 tests), `dashboard/tests/mlopsPage.test.tsx` (10 tests).
- **Status:** DONE

### T-061 Retrain Pipeline, Champion/Challenger Gate, Promotion, Rollback
- **Goal:** Implement a fully governed retraining pipeline, champion/challenger technical comparison gate, explicit promotion workflow, safe rollback mechanism, and immutable audit logging, accompanied by REST API endpoints and a dedicated frontend Model Lifecycle & Governance dashboard at `/mlops`.
- **Files:** `mlops/retrain.py`, `mlops/promote.py`, `api/app/schemas/retrain.py`, `api/app/services/retrain_service.py`, `api/app/routes/retrain.py`, `api/app/main.py`, `api/app/routes/__init__.py`, `dashboard/src/types/mlops.ts`, `dashboard/src/api/client.ts`, `dashboard/src/components/mlops/ModelLifecyclePanel.tsx`, `dashboard/src/components/mlops/PromotionGateCard.tsx`, `dashboard/src/components/mlops/RetrainJobModal.tsx`, `dashboard/src/components/mlops/RollbackModal.tsx`, `dashboard/src/pages/MLOpsPage.tsx`, `tests/mlops/test_retrain.py`, `tests/mlops/test_promote.py`, `tests/api/test_retrain_api.py`, `dashboard/tests/modelLifecycle.test.tsx`.
- **Depends:** T-060, T-016.
- **Implementation:**
  - Implemented `mlops/retrain.py`: Assembles retraining dataset from authorized `train.csv` (6,897 rows, 42 machines) and `val.csv` (1,619 rows, 9 machines) with SHA-256 integrity verification. Strict test-quarantine guard (`_assert_no_test_set_access`) rejects any access to `data/test/` or test machine IDs. Trains challenger XGBoost model under frozen hyperparameter and feature contracts (14 features: 10 raw sensors + `Machine_Type` + 3 physics). Fits Platt/Sigmoid calibration on `val.csv`. Evaluates metrics strictly at frozen cutoff $t^* = 0.160$. Logs run and registers model with alias `challenger` in MLflow Model Registry.
  - Implemented `mlops/promote.py`: 6 hard promotion gates: (1) recall protection ($\text{val\_recall} \ge \text{champ} - 0.05$), (2) precision floor ($\ge 0.10$), (3) feature contract ($n=14$), (4) calibration contract (`sigmoid`), (5) threshold contract ($t^* = 0.160$), and (6) technical inference gate (schema, bounds, threshold, risk bands). Computes soft PR-AUC delta for decision support.
  - Implemented explicit administrative promotion re-assigning `champion` alias in MLflow registry. Implemented safe rollback re-assigning `champion` alias to a designated existing version with mandatory justification.
  - Implemented append-only tamper-evident audit log in `artifacts/retrain_audit.jsonl` recording all retrain, promotion, and rollback events with actors, timestamps, and metrics.
  - Added authenticated REST endpoints under `/api/v1/mlops`: `POST /retrain` (Admin), `GET /gate` (Admin/Engineer), `POST /promote` (Admin), `POST /rollback` (Admin), `GET /registry` (Admin/Engineer), `GET /audit-log` (Admin).
  - Enhanced frontend dashboard at `/mlops` with a dual-tab architecture: "Drift & Observability" (T-060) and "Model Lifecycle & Governance" (T-061). Implemented `ModelLifecyclePanel`, `PromotionGateCard`, `RetrainJobModal`, and `RollbackModal`.
- **Acceptance:** Full test set quarantine enforced; frozen feature and threshold contracts preserved; recall protection prevents performance regressions; explicit human promotion required; append-only audit trail verified; 65 new backend tests pass; 5 new frontend integration tests pass; full test suites and production builds pass cleanly.
- **Tests:** `tests/mlops/test_retrain.py` (26 tests), `tests/mlops/test_promote.py` (16 tests), `tests/api/test_retrain_api.py` (23 tests), `dashboard/tests/modelLifecycle.test.tsx` (5 tests).
- **Status:** DONE

### T-062 GitHub Actions CI (Lint, Unit, Contract, ML Smoke, Image Build)
- **Goal:** Build a robust, reproducible, and fast-failing GitHub Actions CI pipeline in `.github/workflows/ci.yml` that validates code quality, native C++ firmware, operational ML invariants, frontend TypeScript/Vitest/Vite build, full backend test suites, and Docker container builds on every relevant push and pull request.
- **Files:** `.github/workflows/ci.yml`, `tests/ml/test_ml_smoke.py`, `scripts/ml_smoke_test.py`, `tests/test_smoke.py`.
- **Depends:** T-001, T-016, T-030, T-050.
- **Implementation:**
  - Designed multi-job GitHub Actions workflow triggered on pull requests and pushes to `main` and `feat/**` with concurrency group cancellation.
  - Implemented `backend-quality` job running `ruff check .` and `black --check .` under Python 3.11.
  - Retained `firmware-native` compiling native C++ edge harness (`g++ -std=c++17`) and running unit tests.
  - Created dedicated deterministic `ml-smoke` job executing `tests/ml/test_ml_smoke.py` and `scripts/ml_smoke_test.py`: validates model artifact paths, 14-feature contract, operational decision threshold ($t^* = 0.160$), risk band mappings, and model inference without accessing held-out test data (`data/test/`).
  - Implemented `frontend-quality` job under Node 20: runs `npm ci` (with package-lock caching), TypeScript compilation (`npm run lint`), Vitest test suite (`npm test -- --run`), and Vite production bundle build (`npm run build`).
  - Implemented `backend-tests` job running the comprehensive Pytest suite and automated simulation runner.
  - Implemented `docker-build` job validating `docker compose config` and building multi-container images (`edgetwin-api:ci` and `edgetwin-frontend:ci`) via Buildx without publishing.
  - Preserved `wokwi-simulation` for cloud-based Wokwi execution with graceful fallback notice if `WOKWI_CLI_TOKEN` is unset.
  - Enforced zero `continue-on-error: true` flags to prevent hiding real regressions.
- **Acceptance:** All 7 workflow jobs configured; ML smoke test executes deterministically in < 2 seconds; zero access to held-out test data; frontend tests (118 passed) and backend tests (707 passed) pass cleanly; ruff and black formatting checks 100% clean.
- **Tests:** `tests/ml/test_ml_smoke.py` (6 tests), `tests/test_smoke.py` (2 tests), `scripts/ml_smoke_test.py`.
- **Status:** DONE

### T-063 Full Docker Compose Stack
- **Goal:** Create a reproducible, multi-container Docker Compose deployment stack connecting Frontend, Backend API, PostgreSQL 16, Eclipse Mosquitto MQTT broker, and ML inference services with automated migrations, robust healthchecks, non-root container security, and reverse proxy routing.
- **Files:** `docker-compose.yml`, `Dockerfile`, `dashboard/Dockerfile`, `dashboard/nginx.conf`, `dashboard/.dockerignore`, `.dockerignore`, `scripts/docker-entrypoint.sh`, `.env.example`, `README.md`.
- **Depends:** T-030, T-031, T-032, T-050.
- **Implementation:**
  - Upgraded root `Dockerfile` for `api`: multi-stage Python 3.11-slim container installing dependencies, copying application modules, operational artifacts (`artifacts/`), and scripts; runs as non-root user (`edgetwin`); healthcheck via `curl -f http://localhost:8000/health`.
  - Created `scripts/docker-entrypoint.sh`: automatically applies Alembic migrations (`alembic -c api/alembic.ini upgrade head`) against the live PostgreSQL database before launching Uvicorn.
  - Created multi-stage `dashboard/Dockerfile` and `dashboard/nginx.conf`: builds production React SPA with Node 20 alpine, serves static bundle via Nginx 1.25 alpine with gzip compression and security headers, and proxies `/api/` and `/ws/` live WebSocket streams to the backend container.
  - Configured `docker-compose.yml` defining 4 orchestrated services:
    1. `postgres` (PostgreSQL 16-alpine with named volume `postgres_data` and `pg_isready` healthcheck).
    2. `mosquitto` (Eclipse Mosquitto 2.0 with TCP port 1883 and socket availability healthcheck).
    3. `api` (FastAPI backend depending on healthy postgres and mosquitto, port 8000).
    4. `frontend` (React + Nginx reverse proxy depending on healthy api, port 3000 mapped to container 80).
  - Created root `.dockerignore` excluding `.git`, `node_modules`, test caches, and held-out test data (`data/test/`) while preserving required ML model artifacts.
  - Updated `.env.example` with documented environment variables for local Docker Compose while preserving empty secret keys for test assertions.
  - Documented complete quick start, endpoints, development credentials, and stop commands in `README.md`.
- **Acceptance:** `docker compose config` validates cleanly without obsolete syntax; startup sequence governed by healthchecks rather than brittle sleep commands; non-root user security enforced; automated Alembic migration verifies cleanly; zero secrets committed; no architectural regressions.
- **Tests:** `docker compose config`, `tests/test_smoke.py`.
- **Status:** DONE


## PHASE 7 — Verification and demo
| ID | Goal | Depends | Status |
|---|---|---|---|
| T-070 | End-to-end test (virtual edge → alert) + **detection-latency / false-alarm benchmark** per scenario | T-035, T-022 | TODO |
| T-071 | Second-dataset (AI4I 2020) pipeline run | T-012 | TODO |
| T-072 | Demo script (2–3 min), seed data, offline fallback recording | T-070 | TODO |
| T-073 | Final docs, README, evaluation report, limitations | all | TODO |

## Suggested order
T-001 → T-003 → (T-002 when user answers) → T-010/T-011 → T-012 → T-013–T-016 → T-020 → T-040 (early risk check!) → T-021/T-022 → T-030–T-037 → T-041/T-042 → T-050… → T-060/T-061 → T-070 → T-072.
The Wokwi spike (T-040) is scheduled early on purpose: it is the largest external dependency.

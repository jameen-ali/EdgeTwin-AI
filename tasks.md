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
| T-054 | Digital Twin view (SVG schematic) | T-053 | TODO |
| T-055 | Predictions + explanations panel | T-053 | TODO |
| T-056 | Alerts + maintenance workflow + feedback | T-055 | TODO |
| T-057 | History and analytics | T-053 | TODO |
| T-058 | Model / MLOps page + scenario control | T-060 | TODO |

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

## PHASE 6 — MLOps
| ID | Goal | Depends | Status |
|---|---|---|---|
| T-060 | Drift monitor (PSI/KS) vs training reference + feedback-based performance tracking | T-035 | TODO |
| T-061 | Retrain pipeline, champion/challenger gate, promotion, rollback | T-060, T-016 | TODO |
| T-062 | GitHub Actions CI (lint, unit, contract, ML smoke, image build) | T-001 | TODO |
| T-063 | Full `docker compose` stack | T-030 | TODO |

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

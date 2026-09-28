# S12 Session Report — Inference Service + Health Engine (T-033 + T-034)

**EdgeTwin AI — AI-Powered Predictive Maintenance using Digital Twins and Edge Intelligence**
- **Date:** 2026-09-28
- **Session:** S12 (T-033 Inference Service + T-034 Health Engine Layers 1–6)
- **Branch:** `feat/T-034-inference-health`
- **Base Commit:** `a6f8f4f` (S11 baseline: `feat(ingest): add mqtt telemetry ingestion and persistence`)

---

## 1. Executive Summary

Session S12 implemented the ML Inference Service and the 6-Layer Machine Health Engine for EdgeTwin AI:
1. **T-033 (Inference Service):** Loads the champion calibrated XGBoost risk model (`models:/edgetwin-risk@champion`), unsupervised Isolation Forest anomaly detector, and `EdgeTwinExplainer` (SHAP attributions in model log-odds margin space). Connects raw wire telemetry via `telemetry_to_feature_df` with automatic `+physics` feature derivations.
2. **T-034 (Health Engine Layers 1–6):** Full implementation of the multi-layer decision architecture:
   - **Layer 1 (Sensor Condition):** Evaluates sensor quality flags, detects out-of-range & missing readings, computes clamped sensor quality penalty $\Delta_{\text{sensor}} \in [0, 15]$.
   - **Layer 2 (Supervised Failure Risk):** Calibrated positive failure probability $p_{\text{cal}} \in [0, 1]$, binary prediction at cost-optimal threshold $t^* = 0.16$, and operational risk bands (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
   - **Layer 3 (Unsupervised Anomaly Detection):** Normalized anomaly score $a_{\text{anomaly}} \in [0, 1]$ and anomaly flag.
   - **Layer 4 (Composite Machine Health Score):** Deterministic index $\text{Health Score} = \text{clip}(100 - (60 \cdot p_{\text{cal}} + 25 \cdot a_{\text{anomaly}} + \Delta_{\text{sensor}}), 0.0, 100.0)$ and strict deterministic state precedence hierarchy (`OFFLINE` > `MAINTENANCE_REQUIRED` > `CRITICAL` > `WARNING` > `HEALTHY`).
   - **Layer 5 (Alert Severity & Hysteresis):** Assigns alert severity (`CRITICAL`, `WARNING`, `INFO`, `None`) with machine state tracking to prevent alert flapping.
   - **Layer 6 (Actionable Maintenance Recommendations):** Maps top SHAP contributing features, tool wear status, and hardware trips to domain-grounded action codes (`ACT_EMERGENCY_INSPECT`, `ACT_REPLACE_TOOL`, `ACT_INSPECT_COOLING`, `ACT_CHECK_ELECTRICAL`, `ACT_CHECK_MECHANICAL_OVERLOAD`, `ACT_INSPECT_BEARINGS_VIBRATION`, `ACT_CHECK_PRESSURE_SEALS`, `ACT_CALIBRATE_SENSORS`, `ACT_DIAGNOSTIC_AUDIT`, `ACT_ROUTINE_MONITOR`, `ACT_CHECK_CONNECTIVITY`).
3. **Lineage & Persistence:** Persists `PredictionRecord` into the database linked to `TelemetryRecord` with foreign keys and model version metadata; persists `AlertRecord` on WARNING/CRITICAL conditions with duplicate suppression.
4. **End-to-End Pipeline Integration:** Integrated inference seamlessly into `api/app/ingest/handler.py` so that MQTT messages trigger telemetry persistence followed immediately by inference and prediction persistence without crashing or blocking ingestion.
5. **Verification:** Added 30 comprehensive unit and integration tests across `tests/api/test_health_engine.py` and `tests/api/test_inference.py`. Full project test suite: **438 passed, 1 skipped** (offline MQTT integration test).

---

## 2. Implemented Architecture & Modules

### 2.1 Package Structure (`api/app/inference/`)
- `api/app/inference/schemas.py`: Dataclasses for `InferenceResult`, `HealthAssessment`, and `Recommendation`.
- `api/app/inference/engine.py`: `ModelEngine` singleton managing model loading (MLflow champion with fallback to local joblib artifacts), feature validation, leakage prevention, and SHAP explainer initialization.
- `api/app/inference/recommendations.py`: Layer 6 recommendation matrix mapping physical fault signatures and SHAP feature rankings to specific maintenance actions and urgency levels.
- `api/app/inference/health_engine.py`: Multi-layer HealthEngine evaluating Layers 1 through 6 with deterministic precedence hierarchy and per-machine hysteresis tracking.
- `api/app/inference/persistence.py`: Database persistence module writing `PredictionRecord` and `AlertRecord` with transaction isolation and rollback guards.
- `api/app/inference/service.py`: `InferenceService` orchestrator providing `run_inference()` and `process_and_persist()`.
- `api/app/inference/__init__.py`: Package entry point exporting high-level interfaces.

### 2.2 Ingestion Integration (`api/app/ingest/handler.py`)
- Step 7 added to `handle_message()`: Executes `InferenceService.process_and_persist()` upon successful telemetry persistence.
- Isolated with exception handling: Inference errors are logged with structured context and never drop or invalidate persisted telemetry.

---

## 3. Decision Layers Verified

| Layer | Question Answered | Source / Model | Output | Verified In |
|---|---|---|---|---|
| **L1 Sensor Condition** | Can I trust each reading? | Telemetry quality + bounds | Per-channel status, `out_of_range_count`, `missing_count`, $\Delta_{\text{sensor}} \in [0, 15]$ | `test_health_engine.py` |
| **L2 ML Risk** | How likely is a failure condition? | Calibrated XGBoost ($t^* = 0.16$) | $p_{\text{cal}} \in [0, 1]$, `failure_prediction` (0/1), `risk_band` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) | `test_inference.py` |
| **L3 Anomaly** | Is this unlike nominal healthy operation? | Isolation Forest (healthy-only) | $a_{\text{anomaly}} \in [0, 1]$, `anomaly_flag` | `test_inference.py` |
| **L4 Machine Health** | Overall machine operating state | Composite index + precedence | `health_score` $[0, 100]$, `health_state` (`HEALTHY`, `WARNING`, `CRITICAL`, `MAINTENANCE_REQUIRED`, `OFFLINE`) | `test_health_engine.py` |
| **L5 Alert Severity** | Who must be notified, how urgently | Hysteresis rules + state | `alert_severity` (`CRITICAL`, `WARNING`, `INFO`, `None`), `alert_type`, trigger conditions | `test_health_engine.py` |
| **L6 Recommendation** | What action should be taken | Domain decision matrix | `action_code`, `recommendation_text`, `urgency`, `target_component` | `test_health_engine.py` |

---

## 4. Test Suite & Verification Results

- **New Tests:** 30 unit and integration tests covering:
  - Layer 1 sensor quality penalties and clamping.
  - Layer 2 risk predictions and operational risk bands.
  - Layer 3 anomaly scores and flags.
  - Layer 4 health score arithmetic and 5-state deterministic precedence hierarchy.
  - Layer 5 alert severities, trigger conditions, and hysteresis transitions.
  - Layer 6 recommendations and domain action codes.
  - Model leakage rejection (`validate_no_leakage`).
  - Prediction and Alert database persistence.
  - End-to-end MQTT ingest -> Telemetry persistence -> Inference -> Prediction persistence.
- **Full Test Suite:** **438 passed, 1 skipped** (offline MQTT integration test).
- **Static Analysis:**
  - `ruff check .`: Clean (0 errors).
  - `black --check .`: Clean (0 files reformatted).
  - `git diff --check`: Clean (0 whitespace/conflict errors).

---

## 5. Scope Compliance & Guardrails

- [x] Implemented ONLY T-033 and T-034.
- [x] No Digital Twin service implemented (deferred to T-035).
- [x] No REST API endpoints beyond health/readiness implemented (deferred to T-036).
- [x] No WebSockets, JWT authentication, or frontend code touched.
- [x] No modifications to trained model weights or held-out test data.
- [x] No git push executed.

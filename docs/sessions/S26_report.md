# Session S26 Report: T-057 — History and Analytics View

**Date:** 2026-09-29  
**Session:** S26  
**Task:** T-057 — History and Analytics View  
**Model:** Gemini High  
**Branch:** `feat/T-057-history-analytics`  
**Base Commit:** `4fed863` (`feat(frontend): add mlops scenario control ui`)  

---

## 1. Executive Summary

Session S26 implemented the operational historical analysis layer of EdgeTwin AI, delivering a dedicated, high-density retrospective investigation experience at route `/history`. 

Reliability engineers and operators can now perform deep-dive retrospectives across bounded time horizons (1 hour, 6 hours, 24 hours, 7 days, 30 days) to answer key operational questions:
1. **What happened to a machine over time?** Comprehensive timeline integrating health, sensors, predictions, alerts, and maintenance.
2. **How did its health change?** Pure React + SVG continuous health score trend line with operational threshold bands ($\ge 80$ Healthy, $60\text{--}79$ Warning, $<60$ Critical).
3. **How did temperature/vibration/load change?** Interactive sensor telemetry charts for 8 operational parameters with dynamic scaling and downsample indicators.
4. **When did alerts occur?** Incident timeline with status filtering (All, Open, Acknowledged, Resolved) and severity badges.
5. **What maintenance happened?** Work order progression timeline tracking lifecycle states (`PLANNED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`).
6. **What predictions/risk states occurred?** Persisted machine learning inference history displaying failure probability ($p_{fail}$), risk band, anomaly status, model version, and TreeSHAP attribution factors.
7. **How does a machine compare with fleet-level behavior?** Fleet-wide historical overview with asset health distribution meters, failure-risk distribution meters, and machine operational retrospective triage table with one-click drilldowns.

All ML models, calibration layers, operating decision thresholds ($t^* = 0.160$), drift reference baselines, and held-out test data (`data/test/`) remain strictly frozen and untouched.

---

## 2. Git State & Branching

- **Base Commit:** `4fed863` (`feat(frontend): add mlops scenario control ui`)
- **Active Branch:** `feat/T-057-history-analytics`
- **Working Tree:** Clean, no untracked or dangling changes prior to commit.

---

## 3. Discovered & Reused Data Sources

Rather than duplicating telemetry storage or fabricating synthetic records, the implementation queries the existing SQLAlchemy 2.0 ORM models and backend services:
- `api/app/models/telemetry.py` (`TelemetryRecord`): High-frequency sensor observations (process/air temperatures, vibration RMS, rotational speed, torque, pressure, current, voltage, tool wear).
- `api/app/models/prediction.py` (`PredictionRecord`): Persisted model inference outputs (calibrated $p_{fail}$, binary classification, risk band, anomaly score/flag, TreeSHAP top factors, model version).
- `api/app/models/alert.py` (`AlertRecord`): Incident alerts, trigger severities, acknowledgment timestamps, and resolution states.
- `api/app/models/maintenance.py` (`MaintenanceEventRecord`): Work orders, lifecycle states, linked alert IDs, assigned technicians, and completion timestamps.
- `api/app/models/machine.py` (`MachineRecord`): Asset inventory, equipment types, plant locations, and operating states.
- `api/app/models/twin_state.py` (`TwinSnapshotRecord`): Canonical twin state and composite health score records.

---

## 4. Architecture & Implementation

### 4.1 Backend Services & Endpoints (`api/app/`)

1. **Pydantic Schemas (`api/app/schemas/history.py`):**
   - `MachineHistoryResponse`: Standardized payload containing machine metadata, requested window, UTC bounding timestamps, summary statistics, health trend points, sensor trend points, persisted predictions, alert items, maintenance items, and downsample metadata.
   - `FleetHistoryResponse`: Fleet-level asset counts, average health score, health distribution (Healthy, Warning, Critical, Offline), failure-risk distribution (Low, Medium, High, Critical), per-machine alert counts, and machine retrospective summaries.
   - Strict validation schemas for query parameters (`TimeWindowEnum`: `1h`, `6h`, `24h`, `7d`, `30d`, optional `from_ts` and `to_ts` ISO datetimes with `to_ts >= from_ts`).

2. **History Service (`api/app/services/history_service.py`):**
   - **Timezone Normalization:** Enforces UTC normalization (`ensure_utc`) on all query bounds and database records to prevent offset-naive/aware arithmetic discrepancies.
   - **Defensible Duration Calculation:** Computes `time_in_warning_s` and `time_in_critical_s` by evaluating gaps between consecutive telemetry/health observations. Imposes a strict maximum sample gap guard (`MAX_SAMPLE_GAP_SECONDS = 300`) to prevent unwarranted continuous extrapolation across sparse data or offline periods.
   - **Multi-Horizon Downsampling:** Downsamples 1 Hz telemetry into discrete time bins:
     - `1h`: Raw points (up to 1,000 points).
     - `6h`: Raw points (up to 1,000 points).
     - `24h`: 60-second time bins.
     - `7d`: 15-minute time bins.
     - `30d`: 1-hour time bins.
   - Aggregates continuous numeric sensor values via arithmetic means within each time bin. Emits downsampling metadata (`is_downsampled: bool`, `downsample_interval_s: int | None`) to the consumer.

3. **REST Endpoints (`api/app/routes/history.py`):**
   - `GET /api/v1/history/machines/{machine_id}`: Retrieves comprehensive machine history.
   - `GET /api/v1/history/fleet`: Retrieves fleet-level aggregation and asset distributions.
   - Enforces read-only RBAC via `get_current_user` allowing access to all authenticated roles (`OPERATOR`, `MAINTENANCE_ENGINEER`, `ADMIN`).

### 4.2 Frontend Architecture (`dashboard/src/`)

1. **Dedicated Route & Navigation:**
   - Route `/history` registered in `dashboard/src/App.tsx` within `ProtectedRoute`.
   - Sidebar item added in `dashboard/src/components/layout/Sidebar.tsx` with Lucide `History` icon.
   - URL query parameter synchronization (`machine_id`, `window`) enabling bookmarking and deep linking.

2. **Pure React + SVG Visualizations:**
   - `HistoricalHealthChart.tsx`: Zero-dependency SVG time-series chart rendering composite health scores $[0, 100]$. Features horizontal operational threshold lines ($\ge 80$ Healthy, $60\text{--}79$ Warning, $<60$ Critical), vertical crosshair on cursor hover, and dynamic metadata tooltip card displaying UTC timestamp, health score, operating state, and failure probability.
   - `HistoricalSensorChart.tsx`: Zero-dependency SVG telemetry chart supporting interactive metric switching across 8 sensors:
     - Process Temperature (°C)
     - Ambient Air Temperature (°C)
     - Vibration RMS (mm/s)
     - Rotational Speed (RPM)
     - Torque (Nm)
     - Pressure (bar)
     - Current (A)
     - Voltage (V)
     - Tool Wear (min)
     Features dynamic min/max domain scaling with safety padding, Min/Avg/Max summary KPIs, and downsample status badges.

3. **Retrospective Timelines:**
   - `HistoricalPredictionTimeline.tsx`: Renders persisted model predictions table ($p_{fail}$, risk band badges, Isolation Forest anomaly status, model version `v1.2-xgb`, and top TreeSHAP factor chips). Truthful empty state displayed when no prediction records exist.
   - `HistoricalEventTimeline.tsx`: Dual-tab container rendering:
     - Incident Alerts Timeline with interactive status filter pills (`All`, `Open`, `Acknowledged`, `Resolved`) and severity badges.
     - Maintenance Work Orders Timeline detailing work order IDs, components, actions, assigned technicians, lifecycle state badges, and completion timestamps.

4. **Fleet Analytics Section (`FleetAnalyticsSection.tsx`):**
   - Summary KPI cards: Total Fleet Assets, Active Running, Fleet Avg Health, Total Window Incidents, and Completed Maintenance.
   - Fleet Health Distribution bar meter (Healthy / Warning / Critical / Offline).
   - Calibrated Failure-Risk Distribution bar meter (Low / Medium / High / Critical at $t^* = 0.160$).
   - Machine Operational Performance Retrospective table ranking assets by risk and alert volume with one-click drilldown into machine-specific history.

---

## 5. Verification & Testing

### 5.1 Backend Testing (`pytest`)
- Created `tests/api/test_history.py` containing 15 comprehensive unit and integration tests:
  1. `test_get_machine_history_unauthenticated_401`
  2. `test_get_machine_history_operator_authorized_200`
  3. `test_get_machine_history_unknown_machine_404`
  4. `test_get_machine_history_empty_range_truthful_empty`
  5. `test_get_machine_history_downsampling_enforced`
  6. `test_get_machine_history_defensible_durations`
  7. `test_get_fleet_history_200`
  8. `test_get_fleet_history_invalid_window_422`
  9. `test_get_history_no_mutation_side_effects`
  10. `test_get_machine_history_explicit_bounds`
  11. `test_get_machine_history_invalid_bounds_order_422`
  12. `test_get_machine_history_predictions_content`
  13. `test_get_machine_history_alerts_and_maintenance_content`
  14. `test_history_openapi_docs`
- **Full Backend Regression Suite:**
  ```text
  =========== 707 passed, 1 skipped, 8 warnings in 270.42s ============
  ```

### 5.2 Frontend Testing (`vitest`)
- Created `dashboard/tests/historyAnalytics.test.tsx` containing 10 integration test cases:
  1. Renders page header and scope/horizon selector controls.
  2. Renders fleet overview by default with KPI distribution cards.
  3. Switches to machine scope and renders machine history panels.
  4. Switches time window horizon and triggers reload.
  5. Allows switching sensor metrics in sensor chart.
  6. Filters incident alerts by status in event timeline.
  7. Switches to maintenance tab in event timeline.
  8. Drills down from fleet machine table into specific machine history.
  9. Renders error state when API fails with retry option.
  10. Renders truthful empty states when a machine has no history recorded.
- **Full Frontend Regression Suite:**
  ```text
  Test Files  13 passed (13)
  Tests       118 passed (118)
  Duration    9.73s
  ```

### 5.3 Static Analysis, Formatting & Build
- **TypeScript:** `npm run lint` (`tsc --noEmit`) passes with 0 errors.
- **Production Build:** `npm run build` succeeds cleanly in 2.75s (`dist/assets/index-hp_hMGhb.js`: 471.73 kB, gzip 112.02 kB).
- **Ruff Check:** `ruff check` passes with 0 errors ("All checks passed!").
- **Black Check:** `black --check api/ tests/api/` passes with 101 files unchanged.
- **Git Diff Check:** `git diff --check` passes with zero trailing whitespace or merge marker issues.

---

## 6. Security, RBAC & Invariant Audits

| Security / Invariant Criterion | Status | Verification Detail |
|---|---|---|
| **No ML Model Modification** | VERIFIED | No changes to XGBoost models, calibration, feature contracts, or thresholds ($t^* = 0.160$). |
| **No Test Set Contamination** | VERIFIED | `data/test/` and `artifacts/training_reference_stats.json` strictly untouched. |
| **No Synthetic Data Generation** | VERIFIED | Only existing persisted records are queried; no fake historical data seeded. |
| **Read-Only API RBAC** | VERIFIED | Endpoints reject unauthenticated requests (401); read access granted to `OPERATOR`, `MAINTENANCE_ENGINEER`, `ADMIN`. |
| **Zero Side-Effect Guarantees** | VERIFIED | History endpoints execute read-only queries with zero mutations. Verified by test `test_get_history_no_mutation_side_effects`. |
| **No Credential Exposure** | VERIFIED | Responses contain zero passwords, JWT secrets, or sensitive audit metadata. |
| **Defensible Durations** | VERIFIED | Time in warning/critical capped at sample boundaries; gaps $>300$ s excluded. |
| **Client Resource Protection** | VERIFIED | Downsampling strategy prevents memory exhaustion on large time horizons. |

---

## 7. Known Limitations

1. **Downsampling Interpolation:** Downsampling utilizes bucketed arithmetic means. In long horizons (e.g. 30 days with 1-hour bins), extreme momentary sensor spikes lasting < 10 seconds will be smoothed. Event records (alerts and maintenance) remain fully unaggregated and discrete.
2. **Intermittent Telemetry Observations:** If an edge device was disconnected or offline, the calculated time in warning/critical accurately halts during the communication gap rather than assuming the machine remained in degraded state continuously.
3. **Persisted Predictions Availability:** Predictions are only available for time intervals where model inference was actively executed and persisted by the backend inference worker.

---

## 8. Next Recommended Session

- **Session S27 / Task T-062:** GitHub Actions CI pipeline (lint, unit, contract, ML smoke, container image build) or **Task T-070:** End-to-end integration and detection-latency / false-alarm benchmark testing.

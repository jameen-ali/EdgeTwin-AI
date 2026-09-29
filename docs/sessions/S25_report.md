# Session S25 Completion Report: MLOps Page & Scenario-Control UI (T-058)

**Session:** S25  
**Task:** T-058 — MLOps Page and Scenario-Control UI  
**Branch:** `feat/T-058-mlops-scenario-ui`  
**Base Commit:** `4ec3305` (`docs(sessions): add S24 completion report and task tracking`)  
**Date:** 2026-09-29  

---

## 1. Executive Summary

In Session S25, we implemented **Task T-058**, establishing a governed demonstration and simulation Scenario Control layer integrated into both the central MLOps experience (`/mlops`) and the dedicated simulation console (`/scenarios`).

This layer connects industrial operators and reliability engineers to the authoritative backend scenario injection engine (`api/app/routes/scenarios.py`) without introducing any arbitrary parameter injection, without compromising safety interlocks, and while preserving 100% of the S23 statistical drift monitoring and S24 governed model retraining/promotion lifecycle intact.

---

## 2. Existing Backend Scenario Infrastructure Discovered

Prior to writing frontend code, repository discovery confirmed that canonical physical scenarios and injection endpoints were already designed, implemented, and tested in earlier sessions:
- **Specification:** Defined in `simulation/scenarios/*.yaml` and coupled in `simulation/process_model.py` (T-021).
- **Backend Route:** Mounted in `api/app/routes/scenarios.py` under the prefix `/api/v1/scenarios`:
  - `GET /api/v1/scenarios`: Returns an inventory of authorized canonical fault scenarios (`CANONICAL_SCENARIOS`) with names, descriptions, and target failure modes. Accessible to all authenticated users.
  - `POST /api/v1/scenarios/inject`: Validates target asset existence in `machines` database, executes command safety checks against arbitrary code execution (rejects forbidden keys such as `eval`, `exec`, `system`, `subprocess`), generates an authoritative audit log via `log_security_event`, and dispatches the command with an HTTP `202 Accepted` response. Restricted strictly to `PRIVILEGED_MAINTENANCE_ROLES` (`ADMIN`, `MAINTENANCE_ENGINEER`).

---

## 3. Supported Scenarios

Only the 8 canonical simulation scenarios officially supported by the backend are exposed:

| Scenario Code | Canonical Preset Name | Target Failure Mode / Effect | Duration (est.) | Category | Severity |
|---|---|---|---|---|---|
| **SCN-01** | Healthy Nominal | None (Nominal Baseline) | 300s (5.0m) | Healthy | `INFO` |
| **SCN-02** | Heat Dissipation Failure | Heat Dissipation Failure (HDF) — Thermal runaway, $\Delta T < 8.6^\circ\text{C}$ | 180s (3.0m) | Thermal | `CRITICAL` |
| **SCN-03** | Overstrain Overload | Overstrain Failure (OSF) — High torque $\times$ tool wear overload | 150s (2.5m) | Mechanical | `CRITICAL` |
| **SCN-04** | Power Failure Overload | Power Failure (PWF) — Electric torque $\times$ rotational speed power trip | 120s (2.0m) | Electrical | `CRITICAL` |
| **SCN-05** | Tool Wear Degradation | Tool Wear Failure (TWF) — Cumulative mechanical wear $\ge 240\text{ min}$ | 240s (4.0m) | Mechanical | `WARNING` |
| **SCN-06** | Random Vibration Spike | Random Failures (RNF) — High vibration pulse without explicit thermal shift | 90s (1.5m) | Dynamic | `WARNING` |
| **SCN-07** | Sensor Dropout Fault | Sensor Hardware Dropout — Nulls in sensor readings exercising NaN handling | 120s (2.0m) | Instrumentation | `INFO` |
| **SCN-08** | Machine Offline | Connectivity Drop — Halts telemetry stream exercising offline LWT | 180s (3.0m) | Network | `INFO` |

*Safety Invariant:* Free-form parameter injection is strictly prohibited. Presets are hardcoded to backend canonical definitions; arbitrary numerical inputs for temperature, vibration, RPM, torque, or current are prevented by design.

---

## 4. Scenario Control UI & Components Implemented

### Component Architecture
1. **`ScenarioControlPanel.tsx` (`dashboard/src/components/mlops/ScenarioControlPanel.tsx`):**
   - **Simulation Boundary Disclaimer:** Top banner distinguishing simulation controls from real physical machine operations and clarifying that synthetic faults do NOT retrain or alter production ML weights.
   - **Machine Selector:** Dynamically queries `api.machines.list({ limit: 100 })`. Displays machine ID, machine equipment type, and current operating state. Gracefully handles loading, empty fleets, and network errors.
   - **Scenario Preset Selector:** Populated dynamically via `api.scenarios.list()`.
   - **Scenario Preview Card:** Displays scenario badge, formal name, descriptive failure mechanism, current machine operating state (`StatusBadge`), target failure mode, command safety guard badge ("Preset Enforced — No Arbitrary Injection"), estimated duration, selected asset, and RBAC authorization status.
   - **Two-Step Confirmation Modal:** For all scenario injections, users must review target asset, scenario code, and expected physical effects before confirming. Disables submission during in-flight requests and handles backend RFC 7807 problem details in-modal.
   - **Quick Baseline Action:** "Select Baseline (SCN-01)" button enables rapid 1-click selection of healthy baseline conditions without hunting through menus.
   - **Session Command Acknowledgments Table:** In-memory session audit trail recording all accepted simulation commands with Command ID, target machine, scenario code, dispatch status (`ACCEPTED`), authorizing user, timestamp, and server confirmation message.

2. **Integration into `/mlops` (`dashboard/src/pages/MLOpsPage.tsx`):**
   - Added a 3rd top-level sub-tab:
     - **Tab 1:** `Drift & Performance Monitoring` (S23 PSI/KS drift, feature drift table, operator feedback metrics)
     - **Tab 2:** `Model Lifecycle & Governance` (S24 MLflow model registry, champion/challenger comparison, promotion gate, retrain/rollback workflows, audit log)
     - **Tab 3:** `Scenario Control` (S25 demonstration fault injection & simulation control)
   - Preserves all URL state and existing component lifecycles cleanly.

3. **Unified Standalone `/scenarios` Page (`dashboard/src/pages/ScenariosPage.tsx`):**
   - Standardized the standalone route to render `ScenarioControlPanel`, avoiding redundant code and ensuring identical safety guards across both access points.

---

## 5. Security & RBAC Enforcement

- **Role Gating:**
  - `ADMIN` & `MAINTENANCE_ENGINEER`: Fully authorized to dispatch scenarios and restore baselines.
  - `OPERATOR`: Rendered in read-only observation mode. Primary action button is replaced with disabled fallback `<Button disabled>Inject Scenario (Unauthorized)</Button>` accompanied by an amber alert banner explaining role requirements.
- **Backend Authoritative Authorization:**
  - Client-side checks are strictly UX conveniences. The backend endpoint `/api/v1/scenarios/inject` enforces `require_roles(PRIVILEGED_MAINTENANCE_ROLES)` and returns HTTP `403 Forbidden` if an unauthorized JWT token attempts mutation.
- **RFC 7807 Error Handling:**
  - 401 Unauthorized: Triggers session timeout / logout.
  - 403 Forbidden: Surfaced as inline danger alert inside modal.
  - 404 Machine Not Found: Informs operator if target asset has been decommissioned.
  - 422 Unsafe parameter / Invalid scenario: Surfaced cleanly without component crash.

---

## 6. Verification & Quality Gates

### A. Frontend Unit & Integration Tests (Vitest)
A dedicated test suite was created in `dashboard/tests/scenarioControl.test.tsx` containing 11 tests:
1. `renders 3 MLOps navigation tabs and switches to Scenario Control` — PASS
2. `loads available machines and supported scenario presets into selectors` — PASS
3. `updates preview card when selecting different machine and scenario presets` — PASS
4. `prevents unauthorized OPERATOR users from dispatching scenarios` — PASS
5. `opens confirmation modal and allows cancel without making API request` — PASS
6. `dispatches scenario on confirmation and adds to session command acknowledgment log` — PASS
7. `handles backend 403 Forbidden error gracefully inside confirmation modal` — PASS
8. `handles empty fleet state gracefully` — PASS
9. `handles API loading failure with retry button` — PASS
10. `quick Select Baseline (SCN-01) action button switches scenario selection` — PASS
11. `renders dedicated /scenarios route properly with ScenarioControlPanel` — PASS

**Full Frontend Vitest Suite:**
```text
Test Files  12 passed (12)
Tests       108 passed (108)
Duration    19.21s
```

### B. TypeScript Compilation & Linting
```text
npm run lint (tsc --noEmit) -> 0 errors, exit code 0
npm run build (tsc && vite build) -> Built in 5.07s, exit code 0
```

### C. Backend Scenario Tests (pytest)
Executed `pytest -v tests/api/test_auth.py -k TestCommandGuardAndScenarios`:
```text
test_list_scenarios_authenticated                       PASSED [ 14%]
test_inject_scenario_admin_success                      PASSED [ 28%]
test_inject_scenario_engineer_success                   PASSED [ 42%]
test_inject_scenario_operator_forbidden_403             PASSED [ 57%]
test_inject_scenario_invalid_machine_404                PASSED [ 71%]
test_inject_scenario_invalid_scenario_id_422            PASSED [ 85%]
test_inject_scenario_arbitrary_code_command_rejected_422 PASSED [100%]
================ 7 passed, 29 deselected in 39.18s ================
```

---

## 7. Preservation of Strict Invariants

1. **ML Model Logic:** XGBoost champion architecture, 14-feature contract, Platt/Sigmoid probability calibration, and operational threshold $t^* = 0.160$ remain completely untouched.
2. **Health Engine & Anomaly Detector:** Unsupervised Isolation Forest, composite Health Score formula, and deterministic state precedence hierarchy remain 100% frozen.
3. **Drift & Model Governance:** S23 PSI/KS statistical reference distributions and S24 retraining/promotion gate code were not altered.
4. **Held-out Test Data:** `data/test/` directory and `artifacts/training_reference_stats.json` were strictly untouched (0 modifications).

---

## 8. Files Changed

| File | Status | Description |
|---|---|---|
| `dashboard/src/components/mlops/ScenarioControlPanel.tsx` | Created | Full scenario control, preview, modal, safety guards, and session history |
| `dashboard/tests/scenarioControl.test.tsx` | Created | 11 unit/integration tests for Scenario Control UI & RBAC |
| `dashboard/src/types/scenario.ts` | Modified | Added `duration_s` to `ScenarioSummary` and typed `ScenarioInjectResponse` |
| `dashboard/src/api/client.ts` | Modified | Added `api.scenarios.inject` and harmonized `api.scenarios.list` |
| `dashboard/src/pages/MLOpsPage.tsx` | Modified | Added 3rd sub-tab "Scenario Control" rendering `ScenarioControlPanel` |
| `dashboard/src/pages/ScenariosPage.tsx` | Modified | Updated standalone `/scenarios` view to render `ScenarioControlPanel` |
| `tasks.md` | Modified | Marked T-056 and T-058 as DONE and added T-058 detailed task section |
| `memory.md` | Modified | Added S25 completion entries in Section 1 and detailed session log |
| `docs/sessions/S25_report.md` | Created | Comprehensive S25 session report |

---

## 9. Next Recommended Session

- **Session:** S26  
- **Recommended Task:** **T-057 — History and Analytics View** (or proceed to Phase 7 verification & demo preparation **T-070** / **T-072**).
- **Focus:** Complete operational telemetry history filtering, aggregated fleet analytics, and long-term health trends.

# prd.md — EdgeTwin AI Product Requirements

Status: **v0.1 DRAFT (discovery phase)** · Owner: Mohamed Jameen Ali M R (24AD0173) · Institution: Chennai Institute of Technology
Legend: **[FACT]** verified from a source · **[DECISION]** our design choice · **[PROPOSED]** proposed system contribution · **[ASSUMPTION]** unverified, must be checked

---

## 1. Project overview
EdgeTwin AI is a predictive-maintenance platform that connects a simulated industrial machine (Wokwi/ESP32) to an edge layer, a telemetry pipeline, ML risk prediction, a Digital Twin state model, a maintenance-decision layer, a live dashboard, and an MLOps lifecycle. The point of the project is the **connected, measurable system**, not a model plus a dashboard.

## 2. Problem statement
Unplanned machine downtime is costly, and threshold-only alarms are either late or noisy. Many student/academic PdM projects stop at offline model accuracy, so they never show how a prediction becomes a maintenance decision, how the model is governed after deployment, or how the system behaves when sensors fail or data drifts. EdgeTwin AI addresses the full path from sensor reading to maintenance action to model improvement.

## 3. Target users and personas
| Persona | Goal | Needs |
|---|---|---|
| **Operator** (shop-floor) | Know if a machine is safe to run right now | Fleet status at a glance, clear state, plain-language alert |
| **Maintenance Engineer** | Decide what to inspect and when | Risk, contributing factors, trend, history, recommendation, ability to confirm/reject an alert |
| **Admin / ML Owner** | Keep the system trustworthy | Model version, metrics, drift, retraining, user management |
| **Evaluator / Judge** (demo audience) | Understand the system in 2–3 min | One story: normal → fault injected → prediction → twin → alert → action |

## 4. Product goals
G1 Working end-to-end pipeline Wokwi → dashboard. G2 Health and risk that are explainable and separated into distinct layers. G3 A Digital Twin that is a state model, not a picture. G4 Demonstrable MLOps (tracking, registry, drift, gated retraining). G5 Reproducible, tested, documented. G6 Honest evaluation with stated limits.

## 5. Functional requirements
| ID | Requirement |
|---|---|
| FR-01 | Register and list machines (id, type, location, sensor set, thresholds profile). |
| FR-02 | Ingest telemetry over MQTT from any source that meets the telemetry contract (Wokwi, virtual edge, dataset replay). |
| FR-03 | Validate every message (schema, ranges, units, staleness, duplicates); reject or flag with a reason; never crash on bad input. |
| FR-04 | Compute features (shared code for training and serving). |
| FR-05 | Produce failure-risk probability, anomaly score, and health score per reading window, each stored with model version. |
| FR-06 | Maintain a Digital Twin state per machine (see §9) that updates on each telemetry message and exposes sync status (LIVE / STALE / OFFLINE). |
| FR-07 | Explain each elevated-risk prediction with top contributing features (statistical association, not causation). |
| FR-08 | Generate alerts with severity, dedupe/hysteresis, and lifecycle (open → acknowledged → resolved). |
| FR-09 | Produce maintenance recommendations from a documented rule layer; label them "system recommendations". |
| FR-10 | Show live telemetry, history, prediction history, alert history, maintenance events per machine. |
| FR-11 | Multi-machine fleet view (≥ 5 machines). |
| FR-12 | Model/MLOps page: current model version, metrics, comparison, drift status, retraining history. |
| FR-13 | Feedback: engineers mark alerts as confirmed / false alarm; stored as labelled data. |
| FR-14 | Scenario control: inject a named fault scenario into a simulated machine from the dashboard (Admin/Engineer). |
| FR-15 | Role-based access (Admin, Maintenance Engineer, Operator). |

## 6. Non-functional requirements
- **Latency [DECISION target]:** p95 sensor-change → dashboard update ≤ 2 s on a local deployment (measured, not assumed).
- **Reliability:** backend survives malformed payloads, broker reconnects, and DB restarts; edge buffers when backend is unreachable (bounded ring buffer).
- **Reproducibility:** any reported metric reproducible from a git commit + data hash + seed.
- **Security:** no secrets in git; TLS + auth on MQTT; input validation; role checks server-side.
- **Testability:** every decision layer is a pure function with unit tests.
- **Cost:** must be runnable at zero recurring cost (see Wokwi options in architecture.md).
- **Honesty:** UI and docs label simulated data and non-standard thresholds.

## 7. Core features
Fleet overview · Machine detail with live signals · Digital Twin panel · Risk + explanation · Alerts & maintenance workflow · History/analytics · Model & MLOps page · Scenario injection · Edge safety trips visible independently of the cloud.

## 8. Machine-learning requirements
- ML-1 Supervised **failure-condition risk** classifier (binary `Machine_Failure`), compared across ≥ 4 algorithm families; class imbalance handled; metrics: Precision, Recall, F1, PR-AUC, ROC-AUC, confusion matrix (not accuracy alone).
- ML-2 Must accept missing sensor values natively (37% of raw rows have ≥ 1 missing sensor [FACT from our audit]); no imputation fitted on test data.
- ML-3 Probability calibration and an explicit, cost-justified decision threshold.
- ML-4 Unsupervised anomaly detector trained on healthy data only, evaluated separately from ML-1.
- ML-5 Explainability via SHAP or a documented fallback; explanations exposed via API.
- ML-6 `Failure_Type` and other post-outcome columns are **never** model inputs (leakage guard test).
- ML-7 Honest scope: the training data are independent snapshots, so the model detects *failure conditions in the current state*; forecasting is provided only by the twin's trend layer and is labelled a heuristic, not RUL.
- ML-8 A second public benchmark (AI4I 2020) is run through the same pipeline to demonstrate pipeline generality.

## 9. Digital Twin requirements
State object per machine: `machine_id, type, operating_state, signals{air_temp, process_temp, delta_t, rpm, torque, vibration, pressure, current, voltage, power, tool_wear, op_hours}, sensor_quality{per signal}, edge_flags, health{score, state}, risk{probability, band, model_version}, anomaly{score, flag}, top_factors[], recommendation, maintenance_status, sync{status, last_update, staleness_s}, provenance{source: SIMULATED|REPLAY|REAL}`.
Twin must update on each valid message, mark STALE after 3× expected interval, OFFLINE on MQTT last-will or timeout, keep append-only snapshots, and never invent values for missing sensors. Aligned conceptually with ISO 23247 roles (see architecture.md).

## 10. Edge requirements
ESP32 firmware (Wokwi) performs: sensor read, range/plausibility validation, derived features (ΔT, apparent power, windowed vibration RMS), deterministic **safety limit trips** independent of the cloud, bounded store-and-forward buffer, MQTT publish with last-will, command subscribe (scenario/mode). Optional stretch: shallow-tree edge screening.

## 11. MLOps requirements
Data versioning (DVC), experiment tracking and model registry with aliases (MLflow), containerised services, CI (lint, tests, contract test, ML smoke), live drift monitoring (PSI/KS) vs training reference, feedback-labelled performance tracking, gated retraining with champion/challenger promotion and rollback, structured logging, model card.

## 12. Dashboard requirements
Pages: Dashboard, Machines, Live Monitoring, Digital Twin, Predictions, Alerts, Maintenance, Analytics, Model/MLOps, Settings. Original industrial visual identity (design.md). Every value shows unit and freshness; simulated data is visibly labelled.

## 13. Success criteria (measurable)
1. Live demo of the full loop (normal → injected fault → alert → recommendation) runs unattended for ≥ 10 min.
2. p95 end-to-end latency ≤ 2 s (local) measured by test.
3. Held-out failure-class **recall ≥ 0.85 at precision ≥ 0.70** **[TARGET — preliminary OOF results ≈ 0.85 recall / 0.88 precision; must be re-validated on a clean hold-out]**.
4. Per-scenario **detection latency** and **false-alarm rate** reported for ≥ 4 fault scenarios.
5. One full retraining cycle demonstrated: drift flag → retrain → gate → promote → rollback.
6. All FR marked DONE only with passing tests; README lets a stranger run the stack.

## 14. Out of scope
Real plant integration (OPC UA/PLC), true RUL prognostics, 3D CAD twin, physics-based FEM simulation, Kubernetes/cloud scaling, multi-tenant SaaS, mobile app, computer-vision inspection, claiming safety-standard compliance.

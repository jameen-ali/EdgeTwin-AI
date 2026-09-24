# memory.md — EdgeTwin AI Project Memory

Living log. Update on every important decision, bug, fix, dependency, API or DB change. Newest entries at the top of each section.
Legend: [FACT] sourced · [AUDIT] measured by us on the uploaded files · [DECISION] · [PROPOSED] · [ASSUMPTION]
Last updated: 2026-09-24 (discovery phase, no code written yet)

---
## 1. Current status
Discovery and research complete. Six core documents drafted (v0.1). **No implementation started.** Waiting on: (a) dataset provenance from the user, (b) UI reference website (only needed at T-050).

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
Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, pydantic, paho-mqtt (or aiomqtt), scikit-learn, (xgboost optional), shap (verify), MLflow, DVC, pandas, scipy; React, TypeScript, Vite, Tailwind, TanStack Query, Recharts; PostgreSQL 16, Mosquitto, Docker Compose; PubSubClient + ArduinoJson (firmware).

## 13. API / database changes
None yet (v1 draft in architecture.md §8, §12, §13).

## 14. Open questions
1. **Dataset source / licence / generation method?** (blocks T-002)
2. UI reference website (needed at T-050).
3. Submission/expo date (sets how much of the stretch scope fits).
4. Wokwi plan/licence available to you (decides Path A vs B at T-040).

## 15. Future considerations
Shallow-tree edge screening (T-044); Evidently reports; TimescaleDB if volume grows; Prometheus `/metrics`; real sensor hardware (ESP32 + accelerometer) as a bridge from simulation.

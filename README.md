# EdgeTwin AI

> **AI-Powered Predictive Maintenance Platform Combining IoT Edge Intelligence, Machine Learning, Digital Twins, Real-Time Monitoring, and MLOps**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto_2.0-660066?style=flat&logo=eclipse-mosquitto&logoColor=white)](https://mosquitto.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-3.0+-EB5424?style=flat)](https://xgboost.readthedocs.io/)
[![MLflow](https://img.shields.io/badge/MLflow-3.0+-0194E2?style=flat&logo=mlflow&logoColor=white)](https://mlflow.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![ESP32](https://img.shields.io/badge/ESP32-C%2B%2B17-E7352C?style=flat&logo=espressif&logoColor=white)](https://www.espressif.com/)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat&logo=githubactions&logoColor=white)](https://github.com/features/actions)

---

## Visual Showcase

<!-- IMAGE: HERO_OVERVIEW -->
<!-- Replace with your GitHub-hosted image URL -->
![EdgeTwin AI — Project Overview](IMAGE_URL_HERE)

<!-- IMAGE: ARCHITECTURE_DIAGRAM -->
<!-- Replace with your GitHub-hosted image URL -->
![EdgeTwin AI — End-to-End Architecture](IMAGE_URL_HERE)

<!-- IMAGE: DIGITAL_TWIN_MONITORING -->
<!-- Replace with your GitHub-hosted image URL -->
![EdgeTwin AI — Digital Twin Monitoring](IMAGE_URL_HERE)

<!-- IMAGE: MLOPS_LIFECYCLE -->
<!-- Replace with your GitHub-hosted image URL -->
![EdgeTwin AI — MLOps Lifecycle](IMAGE_URL_HERE)

---

## Project Overview

Unplanned equipment downtime is one of the single most expensive operational liabilities in modern industrial manufacturing. Traditional industrial monitoring architectures rely heavily on static threshold-based alarms. In practice, static thresholds suffer from two fatal operational flaws:
1. **Lateness**: They trigger only after irreversible physical wear or catastrophic failure has already begun.
2. **Alert Fatigue**: They generate excessive false positives under transient dynamic loads, causing operators to disregard warning indicators.

While academic predictive maintenance (PdM) research frequently achieves strong offline classification scores on curated datasets, real-world industrial deployments must solve a fundamentally broader engineering challenge: **how a raw sensor reading reliably traverses edge hardware, network brokers, ingestion pipelines, machine learning models, explainability engines, digital twins, alert workflows, and human feedback loops back into governed MLOps lifecycle management.**

**EdgeTwin AI** is a production-oriented predictive maintenance platform that bridges this gap. Industrial machines continuously stream multi-modal telemetry across critical physical parameters:
- **Temperature** (Ambient and Process temperatures)
- **Vibration** (High-frequency RMS velocity)
- **Rotational Speed** (RPM)
- **Torque** (Load moment in Nm)
- **Pressure** (Hydraulic / pneumatic system pressure)
- **Current** (Motor phase current)
- **Voltage** (Line supply voltage)
- **Tool Wear** (Cumulative operational wear minutes)

EdgeTwin AI processes this telemetry through an integrated, closed-loop pipeline:

```text
Physical / Simulated Machine
  └──> ESP32 Edge Device (Autonomous Safety Trips & Local Validation)
        └──> MQTT Transport (Canonical Topics, Schema Validation, QoS, LWT)
              └──> FastAPI Ingestion (Deduplication, Range Validation, Quality Scoring)
                    └──> PostgreSQL Persistence (Atomic Storage & Temporal Indexing)
                          └──> Physics Feature Engineering (Derived Thermal & Power Metrics)
                                ├──> ML Inference (Calibrated XGBoost Failure Probability)
                                ├──> Anomaly Detection (Unsupervised Isolation Forest)
                                └──> Explainability Engine (TreeSHAP Model Attribution)
                                      └──> Health Evaluation Engine (6-Layer Decision Fusion)
                                            └──> Digital Twin Synchronization (ISO 23247 Aligned)
                                                  ├──> Alerts & Maintenance Work Orders
                                                  ├──> Real-Time WebSocket Push
                                                  └──> React Operator Dashboard
                                                        └──> Human Feedback & Drift Monitoring
                                                              └──> Governed MLOps Retraining Loop
```

---

## Project Highlights

- **Real-Time MQTT Telemetry Ingestion**: Asynchronous message consumption over canonical topics (`edgetwin/v1/{machine_id}/telemetry`), supporting strict JSON schema validation, deduplication, and Last Will and Testament (LWT) disconnect detection.
- **ESP32 Edge Intelligence**: C++17 firmware featuring deterministic, edge-autonomous safety trip logic (thermal runaway, over-current, severe vibration, sustained stall) and circular ring buffering for resilient store-and-forward operation during network loss.
- **Telemetry Validation & Quality Scoring**: Granular signal quality tagging (`OK`, `OUT_OF_RANGE`, `STALE`, `MISSING`, `LIMIT_WARN`, `LIMIT_ALARM`) preventing corrupted sensor readings from poisoning inference pipelines.
- **Calibrated XGBoost Failure Prediction**: Gradient boosted classification evaluated on 14 production features (including physics-derived attributes) calibrated via Platt/Sigmoid scaling with a frozen optimal decision threshold ($t^* = 0.160$).
- **Isolation Forest Anomaly Detection**: Unsupervised out-of-distribution detector trained exclusively on verified healthy machine runs, outputting normalized $[0, 1]$ anomaly scores alongside supervised risk probabilities.
- **TreeSHAP Explainability**: On-demand feature attribution computing exact marginal contributions for every inference event, providing transparent model-attribution insights into primary failure drivers.
- **6-Layer Health Scoring Engine**: Hierarchical decision fusion uniting sensor validity, ML risk probabilities, anomaly flags, operational thresholds, and active maintenance status into a deterministic 0–100 health index.
- **Digital Twin Synchronization**: ISO 23247 aligned live virtual representation with real-time sync state tracking (`LIVE`, `STALE`, `OFFLINE`), coupled with append-only database snapshots for full auditability.
- **Sub-100ms End-to-End Latency**: Measured average pipeline processing latency of **60.71 ms** (from edge ingest through ML inference, health scoring, and twin propagation).
- **Incident & Maintenance Workflow**: Complete alert lifecycle management (Active, Acknowledged, Resolved) directly coupled with maintenance work orders and human operator feedback tracking.
- **Production MLOps Governance**: Continuous Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) drift monitoring, automated DVC-tracked retraining pipelines, 6-gate champion/challenger validation, and instant model rollback.
- **Interactive Scenario Simulation**: Eight built-in canonical industrial fault injection scenarios enabling realistic testing and live demonstration of failure cascades.
- **Cloud-Native & Containerized**: Fully orchestrated via Docker Compose with role-based access control (RBAC), JWT authentication, non-root security profiles, and automated GitHub Actions CI.

---

## System Architecture

The EdgeTwin AI architecture is intentionally designed as a cohesive, high-performance modular system. Telemetry flows asynchronously from edge devices over MQTT into FastAPI, where streaming inference and digital twin state updates occur before being broadcast to connected clients via WebSockets.

### Architectural Layers

1. **Edge & Sensing Layer**: Physical machinery or simulated devices running ESP32 firmware (C++17) or virtual Python edge runners. Sensors measure thermal, mechanical, and electrical parameters at 1 Hz, execute autonomous safety trips locally, and buffer telemetry during network outages.
2. **Transport & Broker Layer**: Eclipse Mosquitto MQTT broker managing bidirectional pub/sub messaging. Canonical topics partition telemetry, status (retained messages and LWT), and remote command dispatch.
3. **Ingestion & Persistence Layer**: FastAPI asynchronous consumer decodes, validates, and quality-tags incoming packets, persisting raw records directly to PostgreSQL 16 with compound indexing on `(machine_id, ts DESC)`.
4. **Intelligence & Decision Engine**: A shared feature engineering module feeds normalized vectors into calibrated XGBoost, Isolation Forest, and TreeSHAP models. The 6-layer health engine evaluates machine health and triggers alerts.
5. **Digital Twin Service**: Maintains in-memory and persistent temporal state models for every monitored asset. Updates are broadcast via WebSockets to operator dashboards in under 5 ms.
6. **Operations & Frontend Layer**: Modern React 18 / TypeScript single-page application providing fleet overview, machine detail, live digital twin schematics, risk timelines, SHAP visualizations, and work order tracking.
7. **MLOps Governance Layer**: MLflow tracking and model registry managing versioned model artifacts, monitoring data and prediction drift, evaluating challenger models against a 6-gate promotion policy, and supporting one-click rollback.

---

## Core Workflow

```text
 1. Telemetry Generation   --> Edge sensors record 10 physical and electrical channels at 1 Hz
 2. Edge Processing        --> ESP32 validates ranges, checks safety trips, and buffers data
 3. MQTT Transport         --> Packets published to edgetwin/v1/{machine_id}/telemetry with LWT
 4. Ingestion & Validation --> FastAPI consumes payload, validates schema, and checks staleness
 5. Persistence            --> Telemetry record and per-signal quality flags stored in PostgreSQL
 6. Feature Engineering    --> Shared module derives Delta_T_C, Mech_Power_W, and Apparent_Power_VA
 7. ML Inference           --> Calibrated XGBoost predicts failure probability (p_fail)
 8. Anomaly Detection      --> Isolation Forest computes unsupervised out-of-distribution score
 9. Health Evaluation      --> 6-layer engine calculates composite health score (0–100) and state
10. Twin Synchronization   --> Digital Twin updates live state, evaluates sync status, logs snapshot
11. Alerts & Work Orders   --> Breaches trigger deduplicated alerts and draft maintenance orders
12. Dashboard Streaming    --> State updates pushed via WebSocket to React frontend in real time
13. Human Feedback         --> Maintenance engineers confirm issues or flag false alarms
14. MLOps Monitoring       --> System tracks PSI/KS drift, triggers retraining, and enforces gates
```

---

## AI / ML Pipeline

The predictive maintenance engine utilizes a multi-model architecture combining supervised failure risk classification, unsupervised anomaly detection, and exact feature attribution.

```text
Incoming Sensor Telemetry (10 Raw Signals)
  │
  ├──> Feature Engineering Pipeline
  │     ├── Delta_T_C          = Process_Temperature_C - Air_Temperature_C
  │     ├── Mech_Power_W       = Torque_Nm × Rotational_Speed_RPM × (2π / 60)
  │     └── Apparent_Power_VA  = Current_A × Voltage_V
  │
  ├──> Supervised Risk Model (XGBoost Classifier)
  │     ├── Native handling of missing values
  │     ├── Platt / Sigmoid Post-Hoc Calibration
  │     └── Decision Threshold: t* = 0.160
  │           ├── LOW RISK:      p_fail < 0.15
  │           ├── MEDIUM RISK:   0.15 ≤ p_fail < 0.16
  │           ├── HIGH RISK:     0.16 ≤ p_fail < 0.80
  │           └── CRITICAL RISK: p_fail ≥ 0.80
  │
  ├──> Unsupervised Anomaly Model (Isolation Forest)
  │     ├── Fitted exclusively on verified healthy operation baseline
  │     └── Normalized Anomaly Score ∈ [0.0, 1.0] (Threshold = 0.50)
  │
  └──> Explainability Engine (TreeSHAP)
        └── Model-attribution insights identifying top contributing risk factors
```

### Feature Engineering & Leakage Protection
The production feature vector consists of **14 contract features**:
- **Raw Sensor Signals**: `Air_Temperature_C`, `Process_Temperature_C`, `Rotational_Speed_RPM`, `Torque_Nm`, `Vibration_mm_s`, `Pressure_bar`, `Current_A`, `Voltage_V`, `Tool_Wear_Min`, `Operating_Hours`
- **Categorical Asset Metadata**: `Machine_Type` (One-hot / ordinal encoded)
- **Physics-Derived Attributes**:
  - **$\Delta T$ (Thermal Gradient)**: $\Delta T = T_{\text{process}} - T_{\text{air}}$
  - **Mechanical Power Output**: $P_{\text{mech}} = \tau \times \omega = \text{Torque} \times \left(\text{RPM} \times \frac{2\pi}{60}\right)$
  - **Electrical Apparent Power**: $S = V_{\text{line}} \times I_{\text{phase}}$

> **Leakage Guard**: Target labels (`Failure`), fault categories (`Failure_Type`), asset identifiers (`Machine_ID`), temporal indices (`Timestamp`), and transmission artifacts (`Checksum_Flag`, `Sensor_Batch_Code`) are strictly excluded from feature vectors. This invariant is enforced by automated test suites.

### Probability Calibration & Threshold Optimization
Raw gradient-boosted decision trees output uncalibrated scores that can distort risk calculations. EdgeTwin AI applies **Platt / Sigmoid calibration** fitted on cross-validation folds to ensure well-calibrated failure probabilities $p_{\text{fail}}$ reflecting empirical failure risk.

An optimal decision threshold of **$t^* = 0.160$** was selected during validation to maximize $F_1$ score and optimize the precision-recall trade-off against severe class imbalance (10.99% failure prevalence).

### Model Explainability via TreeSHAP
For every high-risk prediction, EdgeTwin AI executes TreeSHAP to calculate exact feature attributions.

> **Methodological Note on Explainability**: TreeSHAP provides **model-attribution insights** into the features contributing to a prediction. SHAP attributions reflect how individual feature values shifted the model's log-odds relative to the base value; they represent associative model contributions rather than verified physical causality.

### 6-Layer Health Decision Engine
The health engine unifies multi-model inference and operational constraints:

| Layer | Responsibility | Output / Values |
|---|---|---|
| **L1: Sensor Condition** | Validates physical plausibility, range limits, and staleness | `OK`, `OUT_OF_RANGE`, `STALE`, `MISSING`, `LIMIT_WARN`, `LIMIT_ALARM` |
| **L2: ML Failure Risk** | Evaluates calibrated failure probability | $p_{\text{fail}} \in [0, 1]$, Risk Band (`LOW`, `MED`, `HIGH`, `CRITICAL`) |
| **L3: Anomaly Detection** | Detects novel or out-of-distribution operating patterns | Normalized score $\in [0, 1]$, Boolean anomaly flag |
| **L4: Machine Health** | Computes composite health score with hysteresis dampening | Score: $0 \text{--} 100$; State: `HEALTHY`, `WARNING`, `CRITICAL`, `MAINTENANCE_REQUIRED`, `OFFLINE` |
| **L5: Alert Lifecycle** | Evaluates threshold persistence and prevents alert spam | `INFO`, `WARNING`, `CRITICAL` alerts with state tracking |
| **L6: Recommendations** | Selects actionable maintenance protocols from rules | Prescriptive action code and operator instructions |

---

## Digital Twin

The Digital Twin in EdgeTwin AI serves as an active, synchronized software representation of the monitored physical asset, structured in alignment with **ISO 23247 (Digital Twin Manufacturing Framework)**.

```json
{
  "machine_id": "MOT-1001",
  "sync": {
    "status": "LIVE",
    "last_update": "2026-09-30T10:15:30.120Z",
    "staleness_s": 1.02
  },
  "operating_state": "RUNNING",
  "signals": {
    "air_temp_c": 26.2,
    "process_temp_c": 44.8,
    "rpm": 1495.0,
    "torque_nm": 42.1,
    "vibration_mms": 0.32,
    "pressure_bar": 5.1,
    "current_a": 8.4,
    "voltage_v": 230.1,
    "tool_wear_min": 142.0
  },
  "quality": {
    "vibration_mms": "OK",
    "temperature": "OK",
    "pressure": "LIMIT_WARN"
  },
  "health": {
    "score": 91.4,
    "state": "HEALTHY"
  },
  "risk": {
    "probability": 0.018,
    "band": "LOW",
    "model_version": "edgetwin-champion-v2"
  },
  "anomaly": {
    "score": 0.08,
    "flag": false
  },
  "top_factors": [
    { "feature": "Torque_Nm", "shap_value": 0.12 },
    { "feature": "Delta_T_C", "shap_value": 0.08 }
  ],
  "recommendation": "Nominal operation. Continue scheduled monitoring.",
  "provenance": "SIMULATED"
}
```

### State Synchronization Lifecycle
- **`LIVE`**: Active telemetry received within $3 \times$ expected sampling period ($< 3\text{ s}$).
- **`STALE`**: Telemetry heartbeat delayed between 3 s and 10 s; frontend flags telemetry unreliability.
- **`OFFLINE`**: Inactive for $> 10\text{ s}$ or MQTT Last Will and Testament received; twin enters safe offline state.

---

## MLOps Lifecycle

EdgeTwin AI incorporates a closed-loop MLOps architecture ensuring machine learning models remain accurate, monitored, and safely manageable post-deployment.

```text
Production Telemetry & Feedback
  │
  ├──> Drift Monitoring (Scheduled or On-Demand)
  │     ├── Population Stability Index (PSI) vs. Reference Stats
  │     └── Kolmogorov-Smirnov (KS) Two-Sample Distribution Tests
  │
  ├──> Automated Retraining Pipeline (mlops/retrain.py)
  │     ├── Ingestion of verified human feedback labels
  │     ├── Stratified DVC dataset split generation
  │     └── Candidate model hyperparameter optimization
  │
  ├──> Model Registry (MLflow Registry)
  │     ├── Artifact logging: weights, calibration curves, SHAP explainers
  │     └── Alias assignment: challenger
  │
  ├──> Governed 6-Gate Promotion Policy (mlops/promote.py)
  │     ├── Gate 1 (Recall Protection): val_recall ≥ champion_val_recall - 0.05
  │     ├── Gate 2 (Precision Floor): val_precision ≥ 0.10
  │     ├── Gate 3 (Feature Contract): n_features == 14
  │     ├── Gate 4 (Calibration Contract): calibration_method == "sigmoid"
  │     ├── Gate 5 (Threshold Contract): operational_threshold == 0.160
  │     ├── Gate 6 (Technical Inference Gate): Schema, bounds, risk bands valid
  │     └── Governance: Evaluated on val_df; requires explicit Admin approval
  │
  └──> Safe Production Rollback
        └── Instant one-command alias reversion to previous known-good model
```

### Drift Detection & Model Governance
- **Statistical Drift Analysis**: Features are continuously evaluated against `artifacts/training_reference_stats.json` using **Population Stability Index (PSI)** and **Kolmogorov-Smirnov (KS)** tests. PSI values $> 0.25$ raise automated drift notifications.
- **Human-in-the-Loop Feedback**: Maintenance engineers record feedback on predictions (Confirmed Failure, False Alarm, Maintenance Completed) through the dashboard. Labeled records feed directly into future training splits.
- **Six-Gate Promotion Policy**:
  1. **Recall Protection**: Candidate validation recall must remain within allowed degradation relative to champion (`val_recall >= champion_val_recall - 0.05`).
  2. **Precision Minimum**: Candidate validation precision must satisfy the hard floor (`val_precision >= 0.10`).
  3. **Feature Contract**: Candidate must consume the exact 14-feature production contract (`n_features == 14`).
  4. **Calibration Contract**: Calibration method must be Sigmoid (`calibration_method == "sigmoid"`).
  5. **Threshold Contract**: Decision threshold must remain fixed at $t^* = 0.160$.
  6. **Technical Inference Gate**: Schema compatibility, prediction bounds, and risk band assignment must pass validation on sample inference.
- **Administrative Governance**: Comparison is evaluated strictly against the validation split (`val_df`); the held-out test set is quarantined. Promotion requires **explicit administrator approval**; there is no unverified automatic production promotion.
- **Instant Rollback**: If an active model exhibits unexpected real-world degradation, administrators can instantly roll back to the preceding champion artifact via the UI or CLI (`python -m mlops.promote rollback`).

---

## Technology Stack

| Layer / Domain | Technology | Purpose in Project |
|---|---|---|
| **Edge Device** | ESP32 (Xtensa Dual-Core) | Physical / simulated microcontroller executing sensor sampling and safety trips |
| **Edge Framework** | Arduino / Native C++17 | Bounded ring buffer, sensor drivers, and deterministic trip logic |
| **Simulation** | Python 3.11 / Wokwi | Physics-based virtual edge and hardware-in-the-loop simulation |
| **Message Broker** | Eclipse Mosquitto 2.0 | High-performance MQTT message transport (v3.1.1) |
| **Backend Framework** | FastAPI 0.115+ | Asynchronous REST API, WebSocket streaming, and background ingest worker |
| **Data Validation** | Pydantic 2.8+ | Schema validation, request decoding, and settings management |
| **Relational Database** | PostgreSQL 16 | Persistent storage for telemetry, predictions, alerts, twins, and audit logs |
| **Database ORM** | SQLAlchemy 2.0+ / Alembic 1.13+ | Async ORM mappings and database schema migrations |
| **Supervised ML** | XGBoost 3.0+ | Extreme Gradient Boosting classifier for failure probability prediction |
| **Unsupervised ML** | scikit-learn 1.6.1 | Isolation Forest anomaly detection and Platt/Sigmoid calibration |
| **Explainability** | SHAP (TreeSHAP) 0.48+ | Exact game-theoretic feature attribution for tree ensembles |
| **Experiment Tracking** | MLflow 3.0+ | Model registry, experiment versioning, and artifact repository |
| **Data Versioning** | DVC 3.0+ | Immutable data tracking and reproducible ML pipeline stages |
| **Frontend Framework** | React 18.3 | Reactive single-page user interface |
| **Language (Frontend)** | TypeScript 5.5 | Type-safe client-side application logic |
| **Build Tool** | Vite 5.4 | Fast frontend development and production bundling |
| **Styling** | Tailwind CSS | Modern dark-mode industrial UI design system |
| **Visualization** | Recharts 2.12+ / Lucide React | Interactive telemetry charts, risk timelines, and industrial icons |
| **Containerization** | Docker & Docker Compose | Multi-container reproducible deployment orchestration |
| **Web Server** | Nginx Alpine | Static frontend hosting and reverse proxying |
| **CI / CD** | GitHub Actions | 7-job automated quality, testing, and container build pipeline |

---

## Repository Structure

```text
EdgeTwin-AI/
├── .github/
│   └── workflows/
│       └── ci.yml               # 7-job GitHub Actions CI/CD pipeline
├── api/                         # FastAPI backend service
│   ├── alembic.ini              # Database migration configuration
│   ├── Dockerfile               # Backend container specification
│   ├── migrations/              # Alembic schema version migration scripts
│   └── app/
│       ├── main.py              # Application entrypoint & lifespan management
│       ├── config.py            # Environment configuration via Pydantic
│       ├── db/                  # Database engine session & base models
│       ├── models/              # SQLAlchemy ORM database models
│       ├── schemas/             # Pydantic schemas & telemetry contracts
│       ├── ingest/              # MQTT consumer, validation, and normalization
│       ├── inference/           # ML engine, health scoring, and TreeSHAP
│       ├── twin/                # Digital Twin service & snapshot management
│       ├── services/            # Alert, maintenance, feedback, and MLOps services
│       ├── security/            # JWT authentication & server-side RBAC
│       ├── ws/                  # WebSocket broadcaster & client tracking
│       └── routes/              # REST API route endpoints
├── dashboard/                   # React + TypeScript frontend application
│   ├── Dockerfile               # Frontend container specification
│   ├── nginx.conf               # Nginx reverse proxy configuration
│   ├── package.json             # Frontend dependencies & scripts
│   ├── vite.config.ts           # Vite build configuration
│   └── src/
│       ├── App.tsx              # Application root & route definitions
│       ├── main.tsx             # DOM mount & context provider initialization
│       ├── api/                 # REST API client & WebSocket subscription hook
│       ├── components/          # Reusable UI components & navigation
│       ├── pages/               # Dashboard views (Fleet, Machine, Twin, MLOps, etc.)
│       └── types/               # TypeScript interface definitions
├── edge/                        # ESP32 firmware source (C++17)
│   ├── firmware.ino             # Main Arduino/ESP32 sketch
│   ├── process_model.cpp/.h     # Local physics model & safety trip evaluation
│   ├── telemetry.cpp/.h         # MQTT formatting & JSON serialization
│   ├── ring_buffer.cpp/.h       # Bounded FIFO circular buffer for offline resilience
│   ├── sensors.cpp/.h           # Sensor hardware abstraction drivers
│   └── command.cpp/.h           # Remote command parser & reset handlers
├── simulation/                  # Simulation & virtual edge environment
│   ├── virtual_edge.py          # Python virtual edge runner (CI / dev)
│   ├── process_model.py         # Shared physics simulation engine
│   ├── wokwi_runner.py          # Wokwi CLI hardware-in-the-loop bridge
│   └── scenarios/               # 8 canonical YAML fault injection scenarios
├── ml/                          # Machine learning training pipeline
│   ├── data/                    # Dataset preparation, feature engineering & splits
│   └── models/                  # Training, calibration, evaluation & anomaly scripts
├── mlops/                       # MLOps operational scripts
│   ├── drift.py                 # Statistical drift detection (PSI / KS)
│   ├── retrain.py               # Retraining pipeline orchestrator
│   ├── promote.py               # Champion/challenger gate & rollback runner
│   └── register.py              # MLflow model registration utility
├── scripts/                     # Operational & benchmark utilities
│   ├── benchmark_t070.py        # T-070 end-to-end system benchmark harness
│   ├── benchmark_t071.py        # T-071 AI4I 2020 external validation harness
│   ├── ml_smoke_test.py         # Production ML artifact smoke test
│   └── download_ai4i.py         # AI4I public dataset downloader
├── artifacts/                   # Serialized production models & reference data
│   ├── calibrated_classifier_sigmoid.joblib
│   ├── champion_features.json
│   ├── anomaly_isolation_forest.joblib
│   ├── anomaly_ref_params.json
│   ├── training_reference_stats.json
│   ├── t070_benchmark_results.json
│   └── t071_ai4i_results.json
├── mosquitto/                   # MQTT broker configuration
│   └── mosquitto.conf           # Mosquitto listener & security rules
├── tests/                       # Automated test suites (Pytest, Vitest, C++)
│   ├── api/                     # Backend API & WebSocket tests
│   ├── contract/                # Telemetry JSON schema contract validation
│   ├── ml/                      # ML pipeline, leakage guards & invariant tests
│   ├── mlops/                   # MLOps drift & promotion tests
│   ├── edge/                    # Native C++ firmware test harness
│   ├── integration/             # End-to-end integration & scenario tests
│   └── simulation/              # Virtual edge & process model tests
├── docs/                        # Public system documentation
│   ├── FINAL_EVALUATION_REPORT.md # Comprehensive final evaluation report
│   ├── DEMO_RUNBOOK.md          # Step-by-step evaluator demonstration guide
│   └── TROUBLESHOOTING.md       # Production troubleshooting runbook
├── .env.example                 # Environment configuration template
├── docker-compose.yml           # Full-stack Docker multi-container definition
├── pyproject.toml               # Python project configuration & dependencies
└── README.md                    # Project documentation
```

---

## Quick Start

### Option A: Docker Compose Deployment (Recommended)

The entire EdgeTwin AI platform (PostgreSQL, Mosquitto, FastAPI Backend, and React Frontend) can be initialized via Docker Compose.

#### 1. Clone the Repository
```bash
git clone https://github.com/jameen-ali/EdgeTwin-AI.git
cd EdgeTwin-AI
```

#### 2. Configure Environment Variables
```bash
cp .env.example .env
```
*(The default `.env.example` file contains preconfigured development credentials suitable for local evaluation).*

#### 3. Build and Launch Containers
```bash
docker compose up --build -d
```

#### 4. Verify Service Health
```bash
docker compose ps
```
All four containers (`edgetwin-postgres`, `edgetwin-mosquitto`, `edgetwin-api`, and `edgetwin-frontend`) should indicate `running (healthy)`.

Check API health directly:
```bash
curl http://localhost:8000/health
```

#### 5. Open the Dashboard
Navigate to **`http://localhost:3000`** in your browser.

**Development / Demo Credentials**:
The initial administrator account is automatically bootstrapped at startup from `ADMIN_USERNAME` and `ADMIN_PASSWORD` defined in `.env` (template defaults: `admin` / `change-admin-password-in-production`):

| Role | Username | Password (from `.env`) | Access Scope |
|---|---|---|---|
| **Administrator** | `admin` | `change-admin-password-in-production` | Full system access, scenario injection, MLOps retraining & promotion |

> [!NOTE]
> Additional accounts (e.g., Maintenance Engineer, Operator) can be provisioned through the administrative dashboard. Never expose default demo credentials on untrusted public networks.

---

### Option B: Local Development Setup

#### Prerequisites
- **Python 3.11+**
- **Node.js 20+** and **npm**
- **PostgreSQL 16**
- **Eclipse Mosquitto MQTT Broker**
- **g++ with C++17 support** (for native firmware verification)

#### 1. Backend & Python Environment
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install dependencies in editable mode with development tools
pip install -e .[dev]

# Set up environment variables
cp .env.example .env

# Apply database migrations
alembic -c api/alembic.ini upgrade head

# Start background API server
uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Development Server
```bash
cd dashboard
npm install
npm run dev
```
Access the development frontend at **`http://localhost:5173`**.

#### 3. Launching Virtual Telemetry
To simulate active edge machines transmitting live MQTT telemetry:
```bash
python simulation/virtual_edge.py --machine-id MOT-1001 --rate 1.0
```

---

## Configuration

All configuration is managed declaratively through `.env`, validated at startup via Pydantic Settings.

| Variable Category | Key | Description / Default | Production Recommendation |
|---|---|---|---|
| **Environment** | `ENVIRONMENT` | `development` / `production` | Set to `production` |
| **API Server** | `API_HOST`, `API_PORT` | `0.0.0.0`, `8000` | Bind behind reverse proxy |
| **CORS** | `CORS_ORIGINS` | `["http://localhost:3000", ...]` | Restrict strictly to authorized frontend domains |
| **Database** | `DATABASE_URL` | `postgresql+psycopg2://edgetwin:...` | Use managed PostgreSQL instance with TLS |
| **Broker** | `MQTT_HOST`, `MQTT_PORT` | `localhost`, `1883` | Enable MQTTS (port 8883) with mutual TLS |
| **Broker Auth** | `MQTT_USERNAME`, `MQTT_PASSWORD` | Optional / dev-open | Enforce strong per-device credentials |
| **Tracking** | `MLFLOW_TRACKING_URI` | `sqlite:///mlflow.db` | Connect to central MLflow tracking server |
| **Security** | `JWT_SECRET_KEY` | Development placeholder | Generate cryptographically random 256-bit key |
| **Security** | `JWT_ALGORITHM` | `HS256` | Keep `HS256` or use asymmetric `RS256` |
| **Default Admin** | `ADMIN_PASSWORD` | `change-admin-password-in-production` | Rotate immediately before external exposure |

> [!WARNING]
> Never commit `.env` or production credentials to source control. `.env.example` contains only non-sensitive development defaults.

---

## Testing

EdgeTwin AI enforces rigorous testing across every layer of the architecture. The automated test suite contains **839 verified passing tests** spanning Python backend logic, TypeScript frontend components, native C++ firmware, and ML invariants.

| Test Layer | Framework / Harness | Command | Verified Count | Status |
|---|---|---|:---:|:---:|
| **Backend Unit, API, Contract & Integration** | Pytest / AnyIO | `pytest -v` | **702** | PASS |
| **Frontend Unit & UI** | Vitest / Testing Library | `cd dashboard && npm test -- --run` | **118** | PASS |
| **Native Edge Firmware** | g++ (C++17) Harness | Native compiled binary | **13** | PASS |
| **ML Operational Smoke** | Standalone Pytest runner | `python scripts/ml_smoke_test.py` | **6** | PASS |
| **Total Verified Passing Tests** | — | — | **839** | **ALL PASS** |

> Note: The 34 tests for the external AI4I 2020 integration suite (`tests/integration/test_t071_ai4i.py`) execute within the 702 backend pytest count.

### Executing Tests Locally

```bash
# 1. Run Python Backend & Integration Tests
pytest -v

# 2. Run Frontend Tests
cd dashboard && npm test -- --run && cd ..

# 3. Verify ML Invariants & Artifact Integrity
python scripts/ml_smoke_test.py

# 4. Compile & Execute Native Firmware C++ Tests
g++ -std=c++17 -O2 -Iedge -Itests/edge -Itests/edge/arduino_compat \
    tests/edge/test_native_edge.cpp edge/process_model.cpp \
    edge/ring_buffer.cpp edge/command.cpp edge/telemetry.cpp \
    -o test_native_edge && ./test_native_edge
```

---

## Evaluation & Results

The system has undergone two distinct, rigorous evaluation benchmarks: an **Internal Production Benchmark (T-070)** and an **External Public Dataset Generalization Study (T-071)**.

### 1. EdgeTwin Held-Out Production Evaluation (T-012)
Evaluated once on the frozen, stratified held-out test split (1,977 samples; 10.99% failure prevalence):

| Metric | Target (PRD §13) | Achieved Value | Status |
|---|:---:|:---:|:---:|
| **PR-AUC** | — | **0.9234** | Exceeded |
| **ROC-AUC** | $\ge 0.900$ | **0.9755** | Exceeded |
| **Recall (at $t^* = 0.160$)** | $\ge 0.850$ | **0.8963** | Exceeded |
| **Precision (at $t^* = 0.160$)** | $\ge 0.700$ | **0.7908** | Exceeded |
| **$F_1$ Score** | — | **0.8403** | Exceeded |
| **Overall Accuracy** | — | **0.9693** | Exceeded |
| **False Alarm Rate** | $\le 0.050$ | **< 0.020** | Exceeded |

---

### 2. T-070: End-to-End Live System Benchmark
Executed across all **8 canonical fault scenarios** using 740 telemetry messages to evaluate real-time performance and system latency:

| Scenario ID | Injected Fault Condition | Detection Lag | Mean Inf Latency | Final Twin State | Result |
|---|---|:---:|:---:|---|:---:|
| **SCN-01** | Healthy Nominal Operation | N/A (No Trip) | 49.78 ms | `HEALTHY` / `LOW` | **PASS** |
| **SCN-02** | Heat Dissipation Failure (HDF) | 18 ticks | 49.27 ms | `CRITICAL` / `CRITICAL` | **PASS** |
| **SCN-03** | Overstrain Failure (OSF) | 29 ticks | 51.12 ms | `CRITICAL` / `CRITICAL` | **PASS** |
| **SCN-04** | Power Failure (PWF) + Safety Trip | 0 ticks (Instant) | 47.32 ms | `CRITICAL` / `LOW` (Trip) | **PASS** |
| **SCN-05** | Tool Wear Failure (TWF) | 41 ticks | 46.97 ms | `MAINTENANCE_REQUIRED` | **PASS** |
| **SCN-06** | Random Vibration Cluster | 0 ticks (Instant) | 49.97 ms | `CRITICAL` / `CRITICAL` | **PASS** |
| **SCN-07** | Sensor Dropout & Imputation | 0 ticks | 49.37 ms | `HEALTHY` / `LOW` | **PASS** |
| **SCN-08** | Machine Disconnect & MQTT LWT | 0 ticks (Instant) | 52.69 ms | `OFFLINE` | **PASS** |

#### Latency Measurements Across Full Pipeline:
- **Telemetry Ingestion & Quality Tagging**: Mean = **11.15 ms** (Min = 6.61 ms, Max = 40.99 ms)
- **ML Inference (XGBoost + IF + TreeSHAP)**: Mean = **49.56 ms** (Min = 46.97 ms, Max = 52.69 ms)
- **Digital Twin State & WebSocket Broadcast**: Mean = **3.04 ms** (Min = 2.68 ms, Max = 4.54 ms)
- **Total Pipeline Latency**: Mean = **60.71 ms** (Max = 90.77 ms)
- **Scenario Detection Rate**: **100.0%** (8/8 scenarios detected)
- **Steady-State False Alarm Rate**: **0.0%**

---

### 3. T-071: AI4I 2020 External Dataset Validation

To assess model generalization and pipeline adaptability, the frozen production pipeline was evaluated against the public **AI4I 2020 Predictive Maintenance Dataset** (UCI Machine Learning Repository, 10,000 samples) without any model retraining:

| Metric | AI4I 2020 External Study | EdgeTwin Held-Out Test Set | Context & Interpretation |
|---|:---:|:---:|---|
| **ROC-AUC** | **0.7520** | 0.9755 | Demonstrates meaningful rank-order discrimination on unseen data |
| **PR-AUC** | **0.2854** | 0.9234 | Precision-recall area reflecting distribution shift |
| **Recall (at $t^* = 0.160$)** | **0.0413** | 0.8963 | Conservative detection due to lower base rate & missing features |
| **Precision (at $t^* = 0.160$)** | **0.9333** | 0.7908 | High confidence when positive classification triggers |
| **$F_1$ Score** | **0.0791** | 0.8403 | Harmonic mean reflecting operational trade-off |
| **False Alarm Rate** | **0.0001** | < 0.020 | Negligible false positive triggering on external records |
| **Brier Score** | **0.0318** | — | Well-calibrated probabilistic output |

> [!NOTE]
> **Factual Analysis of Cross-Domain Performance**:
> The lower recall on AI4I 2020 is directly explained by two structural domain discrepancies:
> 1. **Feature Absence (43% Missing)**: AI4I lacks 6 of EdgeTwin's 14 production features (`Vibration_mm_s`, `Pressure_bar`, `Current_A`, `Voltage_V`, `Operating_Hours`, and `Apparent_Power_VA`). These were median-imputed, blunting failure signatures.
> 2. **Base-Rate Mismatch (3× Shift)**: The AI4I dataset has an empirical failure rate of **3.39%**, compared to EdgeTwin's **10.99%**. Evaluating with a frozen threshold ($t^* = 0.160$) calibrated for an 11% prior creates an intentionally conservative operating posture. Power Failure (11.6% detection) and Overstrain (8.2% detection) yielded the highest sensitivity because both are driven by Torque and RPM — features directly present in AI4I.

---

## Limitations

In the interest of engineering transparency and academic integrity, the following limitations are documented:

1. **Training Data Provenance (T-002 BLOCKED)**: The initial EdgeTwin training dataset is synthetic data whose original generation parameters are unverified. A formal provenance audit and replacement with physical sensor recordings are required prior to industrial production use.
2. **Cross-Domain Feature Incompleteness**: When deployed against external telemetry schemas lacking electrical and vibration instrumentation (as shown in AI4I 2020), model recall degrades significantly.
3. **Fixed Threshold Sensitivity**: The decision threshold $t^* = 0.160$ is optimized specifically for machines with a ~11% failure rate. Deployments in environments with significantly different baseline failure rates require threshold recalibration.
4. **Local Windows Docker Runtime**: Docker Compose container configuration is verified in automated Linux CI environments; local execution on Windows requires Docker Desktop to be actively running.
5. **Wokwi Cloud CI Token**: Hardware-in-the-loop cloud emulation via Wokwi requires a `WOKWI_CLI_TOKEN`. In environments where this token is absent, hardware logic verification gracefully falls back to native C++ unit testing.
6. **Manual Model Promotion Gate**: While drift monitoring and retraining pipelines are automated, production model promotion intentionally requires manual administrative approval.
7. **Internal Work Order Management**: Maintenance workflows are tracked within EdgeTwin AI; native connectors to enterprise CMMS suites (e.g., SAP PM, IBM Maximo) are not implemented.
8. **Time-Series Downsampling**: Long-range temporal analytics queries downsample historical readings to maintain low query latency on standard PostgreSQL tables.

---

## Security

EdgeTwin AI implements defense-in-depth principles across all components:

- **Credential Hygiene**: Production secrets, database credentials, and cryptographic keys must never be committed to git. `.env.example` supplies sanitized placeholders only.
- **Server-Side RBAC**: Role-based access control is enforced at the route dependency layer in FastAPI. Client-side gating in React is purely for user experience.
- **Authentication**: Stateless JSON Web Tokens (JWT) signed with HMAC-SHA256, featuring configurable token lifetimes. Passwords hashed using `bcrypt` with salt rounds.
- **Container Isolation**: Docker images run as non-root service users (`UID 1000`), do not mount the host Docker socket, and disallow privileged execution.
- **Input Validation**: Strict schema enforcement via Pydantic v2 and JSON Schema v1 prevents injection attacks and structural malformations.
- **Rate Limiting**: Rate limits protect authentication endpoints and scenario command injection APIs.

---

## Documentation

Comprehensive project documentation is available in the repository:

- **[Final Evaluation Report](docs/FINAL_EVALUATION_REPORT.md)**: Exhaustive technical evaluation covering PRD compliance, machine learning methodology, T-070 system benchmarks, and T-071 cross-domain validation.
- **[Demo Runbook](docs/DEMO_RUNBOOK.md)**: Step-by-step evaluator script for live demonstrations, fault scenario walkthroughs, and UI navigation.
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**: Resolution procedures for Docker, database, broker, migration, and runtime issues.

---

## Roadmap

The following future improvements are identified based on the final system evaluation:

- [ ] **Provenance Audit (T-002)**: Complete provenance verification of training datasets and collect empirical sensor traces.
- [ ] **Physical Sensor Integration**: Validate ESP32 firmware against physical motors equipped with I2C/SPI accelerometer (MPU6050) and thermal sensors.
- [ ] **Remaining Useful Life (RUL) Prognostics**: Integrate deep sequence models (LSTM / Transformer) to predict remaining operating hours alongside failure probability.
- [ ] **TimescaleDB Scaling**: Transition time-series telemetry tables to TimescaleDB hypertables for multi-million row retention.
- [ ] **Industrial Protocol Ingestion**: Develop an OPC-UA / Modbus TCP connector bridge for direct integration into PLC networks.
- [ ] **Enterprise CMMS Integration**: Bidirectional synchronization with enterprise asset management platforms (SAP PM, IBM Maximo).
- [ ] **Evidently AI Drift Dashboard**: Deepen MLOps monitoring with interactive drift visualization reports.

---

## Author & Project Information

**EdgeTwin AI**  
*AI-Powered Predictive Maintenance using Digital Twins and Edge Intelligence*  
Machine Learning Operations (MLOps) — Student Project  

- **Author**: Mohamed Jameen Ali M R  
- **Register Number**: 24AD0173  
- **Institution**: Chennai Institute of Technology  

---

## License & Academic Use

This project is developed as an academic capstone and research platform in Machine Learning Operations (MLOps) at Chennai Institute of Technology. Licensing terms for public distribution are pending institutional release.

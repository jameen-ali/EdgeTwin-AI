# EdgeTwin AI — Model Card: `edgetwin-risk`

**Model Name:** `edgetwin-risk`  
**Model Version Alias:** `champion` (`models:/edgetwin-risk@champion`)  
**Architecture:** Calibrated Gradient Boosted Trees (`xgboost + physics`)  
**Project:** EdgeTwin AI — Predictive Maintenance Digital Twin  
**Owner / Author:** Mohamed Jameen Ali M R (Register No: 24AD0173)  
**Session:** S06 (T-015 Explainability & T-016 Model Registry)  
**Authoritative Baseline:** S05 Frozen Baseline (`1d08fb1`)  
**Tracking URI:** `sqlite:///mlflow.db`  
**Experiment:** `T-015-T-016-explainability-registry`  

---

## 1. Model Details

- **Model Type:** Supervised Binary Classifier with Post-Hoc Probability Calibration.
- **Base Estimator:** XGBoost Classifier (`XGBClassifier`, 300 estimators, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8).
- **Preprocessing:** Scikit-learn `ColumnTransformer` with median imputation and standard scaling for numeric features; constant imputation and ordinal encoding (`unknown_value=-1`) for categorical feature `Machine_Type`.
- **Calibration Engine:** Platt Scaling (`CalibratedClassifierCV(FrozenEstimator(pipeline), method="sigmoid")`) fitted on validation data (`val_df`).
- **Operational Decision Threshold:** $t^* = 0.16$ (cost-sensitive operating point minimizing downtime costs under asymmetric cost ratio $r = C_{FN} / C_{FP} = 5$).
- **Explainability Engine:** TreeSHAP (`shap.TreeExplainer`, margin/log-odds space) with native XGBoost `pred_contribs` zero-dependency fallback.
- **Packaging:** MLflow PyFunc (`EdgeTwinRiskModel`) encapsulating raw telemetry ingestion, physics auto-derivation, calibrated scoring, threshold evaluation, and risk-band classification.

---

## 2. Intended Use & Safety Disclaimers

### Intended Use
- Real-time continuous failure risk assessment for industrial computer numerical control (CNC) milling and machining centers.
- Generating operational risk bands (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) to drive preventive work orders and adaptive sensor sampling rates.
- Providing local log-odds factor attributions to guide maintenance technicians during root-cause inspection.

### Out-of-Scope & Non-Certified Use
- **Not a Certified Safety System:** This machine learning model is **NOT** a certified industrial safety shutdown system, emergency stop (E-stop), or SIL-rated (Safety Integrity Level) fail-safe mechanism. Critical hardware trips must remain hardwired and autonomous.
- **Configurable Operational Trade-Off:** The operational threshold $t^* = 0.16$ represents a **project-specific operational trade-off** tailored to asymmetric downtime economics ($r=5$). It is **NOT** a universal industrial standard or physical law.
- **Statistical Association, Not Causation:** SHAP values represent statistical feature contributions to the model's log-odds margin space. They describe associations exploited by the decision trees, **NOT causal physical mechanisms**. Correcting a high-SHAP feature does not physically guarantee failure prevention.

---

## 3. Data Split & Governance Strategy

- **Dataset:** 9,994 operational telemetry records partitioned across 60 CNC machines into 3 non-overlapping machine-grouped splits:
  - **Training (`train_df`):** 42 machines (70%), 7,005 rows, 237 failures (3.38% prevalence).
  - **Validation (`val_df`):** 9 machines (15%), 1,490 rows, 133 failures (8.93% prevalence).
  - **Held-Out Test (`test_df`):** 9 machines (15%), 1,499 rows, 135 failures (9.01% prevalence).
- **Split Invariance:** Grouped strictly by `Machine_ID` to prevent cross-machine contamination and physical sensor leakage across splits.
- **Held-Out Test Protection Policy:**
  - Evaluated **strictly ONCE** at the conclusion of S05.
  - Zero test set re-evaluation, hyperparameter re-tuning, or model re-ranking was conducted during S06.
  - All test metrics reported below are historical frozen numbers from S04/S05.

---

## 4. Leakage Controls & Feature Specifications

### Leakage Protection
All model input paths (training, inference, explainability, promotion gates) strictly enforce the project's authoritative leakage validator (`validate_no_leakage`), permanently rejecting all 6 forbidden metadata and target columns:
1. `Failure_Type` (target mode)
2. `Machine_ID` (grouping identifier)
3. `Timestamp` (temporal ordering)
4. `Sensor_Batch_Code` (hardware batch metadata)
5. `Checksum_Flag` (data transmission integrity artifact)
6. `Machine_Failure` (ground truth binary target)

### Feature Set (14 Features: `+physics`)
The model operates on 14 logical features. If raw telemetry is supplied (10 sensors + `Machine_Type`), the PyFunc wrapper automatically derives the 3 physics features using `apply_feature_set(df, "+physics")`:

| # | Feature Name | Type | Source / Physics Formula | Physical Unit |
|---|---|---|---|---|
| 1 | `Air_Temperature_C` | Numeric | Direct Telemetry | °C |
| 2 | `Process_Temperature_C` | Numeric | Direct Telemetry | °C |
| 3 | `Rotational_Speed_RPM` | Numeric | Direct Telemetry | RPM |
| 4 | `Torque_Nm` | Numeric | Direct Telemetry | Nm |
| 5 | `Vibration_mm_s` | Numeric | Direct Telemetry | mm/s |
| 6 | `Pressure_bar` | Numeric | Direct Telemetry | bar |
| 7 | `Current_A` | Numeric | Direct Telemetry | A |
| 8 | `Voltage_V` | Numeric | Direct Telemetry | V |
| 9 | `Tool_Wear_Min` | Numeric | Direct Telemetry | min |
| 10 | `Operating_Hours` | Numeric | Direct Telemetry | h |
| 11 | `Machine_Type` | Categorical | Machine Metadata (`L`, `M`, `H`) | category |
| 12 | `Delta_T_C` | Numeric | $T_{\text{process}} - T_{\text{air}}$ | °C |
| 13 | `Apparent_Power_VA` | Numeric | $V \times I$ | VA |
| 14 | `Mech_Power_W` | Numeric | $\tau \times (\omega \cdot 2\pi / 60)$ | W |

---

## 5. Performance Metrics

### Validation Performance (Frozen from S05 on `val_df`)
Evaluated across 1,490 validation rows with 133 failure events:

| Metric | Uncalibrated ($t=0.50$) | Sigmoid Calibrated ($t=0.50$) | Sigmoid Calibrated ($t^*=0.16$) |
|---|---|---|---|
| **ROC-AUC** | 0.9822 | 0.9822 | 0.9822 (Invariant) |
| **PR-AUC** | 0.8969 | 0.8969 | 0.8969 (Invariant) |
| **Brier Score** | 0.02810 | 0.02619 | 0.02619 (6.8% reduction) |
| **ECE (10 bins)** | 0.02867 | 0.00391 | 0.00391 (86.4% reduction) |
| **Recall** | 0.8045 | 0.8045 | 0.8421 (+3.76% recall gain) |
| **Precision** | 0.8425 | 0.8425 | 0.7778 (Trade-off for recall) |
| **F1 Score** | 0.8231 | 0.8231 | 0.8087 |

### Historical Held-Out Test Performance (Frozen from S04/S05 on `test_df`)
> **Note:** S06 did NOT re-evaluate the test set. These metrics reflect the single final evaluation executed after freezing all decisions in S05:

| Metric | S04 Baseline ($t=0.50$, uncalibrated) | S05 Frozen Champion ($t^*=0.16$, sigmoid) |
|---|---|---|
| **Recall** | 0.8963 | **0.8963** (121 / 135 failures detected) |
| **Precision** | 0.7908 | **0.7610** (121 TP / 38 FP) |
| **F1 Score** | 0.8403 | **0.8231** |
| **F2 Score** | 0.8730 | **0.8655** |
| **Accuracy** | 0.9693 | **0.9653** |
| **ROC-AUC** | 0.9755 | **0.9755** |
| **PR-AUC** | 0.9234 | **0.9234** |
| **Brier Score** | 0.02492 | **0.02055** (17.5% test reduction) |

### Per-Failure-Type Historical Test Recall (Frozen S05)
| Failure Mode | True Failures | Detected ($t^*=0.16$) | Test Recall |
|---|---|---|---|
| **Heat Dissipation Failure (HDF)** | 43 | 41 | **95.35%** |
| **Overstrain Failure (OSF)** | 46 | 43 | **93.48%** |
| **Random Failure (RNF)** | 9 | 9 | **100.00%** |
| **Tool Wear Failure (TWF)** | 17 | 13 | **76.47%** |
| **Power Failure (PWF)** | 20 | 15 | **75.00%** |
| **Overall** | **135** | **121** | **89.63%** |

---

## 6. Operational Risk Bands

| Risk Band | Probability Range | Operational Action Protocol |
|---|---|---|
| **`LOW`** | $p < 0.15$ | Normal operations. Standard 1 Hz telemetry streaming. |
| **`MEDIUM`** | $0.15 \le p < 0.16$ | Early warning advisory. Increase telemetry sampling to 10 Hz. |
| **`HIGH`** | $0.16 \le p < 0.80$ | Failure predicted. Generate work order; inspect machine within shift. |
| **`CRITICAL`** | $p \ge 0.80$ | Imminent catastrophic breakdown. Trigger controlled operator shutdown. |

---

## 7. Explainability & Feature Importance

- **Local Explanations:** Explains XGBoost margin space (log-odds). Positive SHAP monotonically increases calibrated probability; negative SHAP monotonically lowers probability.
- **Additivity Guarantee:** Verified numerically for every prediction ($|\text{base\_value} + \sum \phi_i - \text{margin}| \le 10^{-4}$).
- **Global Feature Importance (Validation Background):**
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

---

## 8. Known Limitations & Edge Conditions

1. **Transient Electrical Dynamics:** PWF recall on held-out test data is 75.00%. Point-in-time sensor snapshots miss high-frequency microsecond electrical transients.
2. **Wear Rate Non-Linearity:** TWF recall is 76.47% due to tool wear thresholding variability across varying cutting materials.
3. **Imbalanced Sub-Modes:** Validation data contains 133 total failures across 5 modes. Per-failure-type calibration is contraindicated due to sample-size constraints.

---

## 9. Lineage & Governance

- **Source Code Repository:** EdgeTwin AI (`feat/T-015-T-016-explainability-registry`)
- **Trained Weights:** `artifacts/calibrated_classifier_sigmoid.joblib`
- **Feature Set:** `artifacts/champion_features.json`
- **Global Importance:** `artifacts/feature_importance_global.csv`
- **Sample Explanation:** `artifacts/sample_explanation.json`
- **MLflow Model Registry:** `models:/edgetwin-risk@champion`
- **Promotion Gate:** Validated via automated 10-step technical promotion gate in `mlops/register.py`.

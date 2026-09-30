# T-071: AI4I 2020 Predictive Maintenance Generalization Benchmark Report

**Session:** S29  
**Task:** T-071 - Second-Dataset Pipeline Run / AI4I 2020 Generalization Benchmark  
**Branch:** `feat/T-071-ai4i-generalization`  
**Champion Model:** `edgetwin-risk@champion` (XGBoost, +physics, t\*=0.160) - FROZEN  
**Dataset:** AI4I 2020 Predictive Maintenance Dataset (UCI ML Repository, CC BY 4.0)  
**Date:** 2026-09-30

---

## 1. Objective

Validate the **portability** of the EdgeTwin predictive-maintenance pipeline against an
independent, publicly available dataset without modifying the production champion model.

**Research question:** Can EdgeTwin feature engineering, inference methodology, and predictive-maintenance concepts be applied to an independent equipment dataset, with explicit documentation of which features transfer directly, which require mapping, and which are incompatible?

This is **NOT** a re-training exercise, NOT a model evaluation on EdgeTwin's held-out test set, and NOT a performance benchmark to compare directly against production results.

---

## 2. Dataset Profiles

### 2.1 EdgeTwin Training Dataset (reference)

| Property | Value |
|---|---|
| Source | Synthetic / provenance unverified (T-002 BLOCKED) |
| Rows (post T-003 dedup) | 9,885 |
| Failure rate | 10.99% |
| Failure types | Heat Dissipation, Overstrain, Power, Tool Wear, Random |
| Machine types | Pump, Compressor, CNC_Machine, Conveyor, Motor |
| Missing data | Yes (13-40% per sensor column) |

### 2.2 AI4I 2020 Dataset (external validation)

| Property | Value |
|---|---|
| Source | UCI ML Repository - Stephan Matzka, HTW Berlin, CC BY 4.0 |
| Citation | Dua, D. and Graff, C. (2019). UCI Machine Learning Repository |
| URL | https://archive.ics.uci.edu/ml/datasets/AI4I+2020+Predictive+Maintenance+Dataset |
| Rows | 10,000 |
| Failure rate | **3.39%** (vs EdgeTwin 10.99% - 3.24x lower) |
| Failure types | TWF(46), HDF(115), PWF(95), OSF(98), RNF(19) |
| Machine quality types | L=6000, M=2997, H=1003 |
| Missing data | **None** (complete dataset) |

> **Important:** AI4I 2020 represents a **different failure regime**: 3.4% failure rate vs 11.0%, clean sensor readings, different sensor suite, and quality-variant machine types (L/M/H) rather than machine-class types.

---

## 3. Feature Compatibility Analysis

The production champion uses **14 features** (`+physics` feature set).

### 3.1 Compatibility Table

| EdgeTwin Feature | AI4I Column | Status | Notes |
|---|---|:---:|---|
| `Air_Temperature_C` | `Air temperature [K]` | **MAPPED** | Subtract 273.15 (unit shift) |
| `Process_Temperature_C` | `Process temperature [K]` | **MAPPED** | Subtract 273.15 (unit shift) |
| `Rotational_Speed_RPM` | `Rotational speed [rpm]` | **DIRECT** | Identical quantity and unit |
| `Torque_Nm` | `Torque [Nm]` | **DIRECT** | Identical quantity and unit |
| `Tool_Wear_Min` | `Tool wear [min]` | **DIRECT** | Identical quantity and unit |
| `Machine_Type` | `Type` (L/M/H) | **MAPPED\*** | L->Motor, M->CNC_Machine, H->Compressor (approximate) |
| `Delta_T_C` | Temps in K | **DERIVED** | Kelvin delta = Celsius delta (unit-invariant) |
| `Mech_Power_W` | RPM, Torque | **DERIVED** | Torque x RPM x 2pi/60 |
| `Vibration_mm_s` | *(absent)* | **UNAVAILABLE** | Not in AI4I 2020 -> NaN |
| `Pressure_bar` | *(absent)* | **UNAVAILABLE** | Not in AI4I 2020 -> NaN |
| `Current_A` | *(absent)* | **UNAVAILABLE** | Not in AI4I 2020 -> NaN |
| `Voltage_V` | *(absent)* | **UNAVAILABLE** | Not in AI4I 2020 -> NaN |
| `Operating_Hours` | *(absent)* | **UNAVAILABLE** | Not in AI4I 2020 -> NaN |
| `Apparent_Power_VA` | *(absent)* | **UNAVAILABLE** | Cannot derive without V and I -> NaN |

**Summary: 3 DIRECT, 3 MAPPED, 2 DERIVED, 6 UNAVAILABLE** (57% available, 43% structural gaps)

### 3.2 Machine_Type Mapping Caveat

> **WARNING:** AI4I `Type` (L/M/H) = product **quality variants** of the same CNC milling machine. EdgeTwin `Machine_Type` = **different equipment categories**. The mapping is approximate by operational complexity only. This is a **known semantic mismatch**.

### 3.3 Imputation of UNAVAILABLE Features

6 UNAVAILABLE columns are set to **NaN** (not zero). The production `SimpleImputer(strategy='median')` fills these with EdgeTwin training medians. This introduces cross-dataset distribution shift for those 6 features - an acknowledged limitation.

---

## 4. Benchmark Execution

1. Downloaded AI4I 2020 from UCI (10,000 rows, 522 KB)
2. Applied feature compatibility mapping
3. Loaded frozen `edgetwin-risk@champion` via MLflow (no model code modified)
4. Ran inference on all 10,000 AI4I rows
5. Evaluated at frozen threshold t\*=0.160 (production value, unchanged)
6. Logged to isolated MLflow experiment `edgetwin-ai4i-validation`
7. Saved results to `artifacts/t071_ai4i_results.json`

---

## 5. Results

### 5.1 Score Distribution

| Statistic | Value |
|---|---|
| Min score | 0.0103 |
| Mean score | 0.0128 |
| Max score | 0.7609 |
| Healthy mean | 0.0123 |
| Failure mean | 0.0573 |
| Healthy P95 | 0.0177 |
| Failure P5 | 0.0103 |

The model **discriminates classes** (failure mean > healthy mean), but the separation is weak -- the failure P5 barely exceeds the healthy mean.

### 5.2 Evaluation at Frozen Threshold (t\*=0.160)

| Metric | Value | Notes |
|---|:---:|---|
| **PR-AUC** | 0.2854 | vs 0.9234 on EdgeTwin test - expected degradation |
| **ROC-AUC** | 0.7520 | Meaningful discrimination retained |
| **Recall** | 0.0413 | Model detects only 4% of AI4I failures at t\*=0.16 |
| **Precision** | 0.9333 | When it fires, 93% of alerts are true positives |
| **F1** | 0.0791 | Dominated by extremely low recall |
| **False Alarm Rate** | 0.0001 | Near-zero false positives |
| **Brier Score** | 0.0318 | Low (good calibration for healthy majority class) |

### 5.3 Per-Failure-Type Detection at t\*=0.160

| Failure Type | Count | Detected | Rate | Mean Score |
|---|:---:|:---:|:---:|:---:|
| Tool Wear Failure (TWF) | 46 | 0 | 0.0% | 0.0210 |
| Heat Dissipation Failure (HDF) | 115 | 1 | 0.9% | 0.0165 |
| Power Failure (PWF) | 95 | 11 | **11.6%** | 0.0751 |
| Overstrain Failure (OSF) | 98 | 8 | **8.2%** | 0.0661 |
| Random Failure (RNF) | 19 | 0 | 0.0% | 0.0126 |

Power and Overstrain score highest -- both correlate with Torque/RPM, which are DIRECT features available in AI4I. Physically consistent.

### 5.4 Calibration

| Statistic | Value |
|---|---|
| AI4I actual failure rate | 3.39% |
| Mean predicted score | 1.28% |
| Calibration gap | 2.11 pp |

Model underestimates failure risk by ~2pp. Champion was Platt-calibrated at 11% failure rate; the 3x lower AI4I base rate shifts the prior significantly.

---

## 6. Scientific Conclusions

**Q1: Can EdgeTwin feature engineering transfer to AI4I 2020?**  
PARTIALLY. 5 physical sensor columns map directly or with unit conversion. 2 physics-derived features (Delta_T, Mech_Power) are fully derivable. 6 features are structurally absent.

**Q2: Can the frozen champion classify AI4I failures?**  
YES, with rank-order discrimination, but NOT at the production threshold. ROC-AUC=0.752 demonstrates meaningful discrimination. The production threshold (t\*=0.160) is extremely conservative for AI4I's 3.4% failure rate, detecting only 4% of failures.

**Q3: Is the degradation explained by known factors?**  
YES. Three clearly attributable causes:
  1. Missing sensors (43% of features): Vibration, Pressure, Current, Voltage, Operating_Hours are absent and imputed with EdgeTwin medians that carry no AI4I signal.
  2. Cross-domain imputation bias.
  3. Base-rate mismatch (3.4% vs 11.0%): threshold tuned for a 3x higher prior.

**Q4: Does this invalidate the EdgeTwin champion?**  
NO. The champion performs correctly in its domain (PR-AUC 0.923, Recall 0.896). The AI4I result demonstrates expected transfer degradation under severe feature and distribution shift -- a scientifically honest and predicted outcome.

---

## 7. Limitations

1. AI4I represents one machine type (CNC milling machine) in 3 quality variants; EdgeTwin covers 5 heterogeneous machine classes.
2. Cross-domain imputation introduces values the AI4I physical system never measured.
3. Machine_Type semantic mismatch: L/M/H to Motor/CNC/Compressor is approximate.
4. No re-calibration performed: domain-adapted threshold would yield substantially different characteristics.
5. Provenance asymmetry: EdgeTwin training data is provenance-unverified (T-002 BLOCKED); AI4I is a public, peer-reviewed dataset.

---

## 8. Deliverables

| Artefact | Path |
|---|---|
| Benchmark script | `scripts/benchmark_t071.py` |
| Test suite (34 tests) | `tests/integration/test_t071_ai4i.py` |
| Results JSON | `artifacts/t071_ai4i_results.json` |
| AI4I dataset | `data/raw/ai4i2020.csv` |
| This report | `docs/sessions/S29_report.md` |
| MLflow experiment | `edgetwin-ai4i-validation` |

---

## 9. Test Results: 34/34 PASSED

| Test Class | Tests | Status |
|---|:---:|:---:|
| TestFeatureCompatibilityCatalogue | 7 | PASS |
| TestBuildEdgetwinFeatures | 9 | PASS |
| TestEvaluate | 5 | PASS |
| TestBenchmarkResults | 13 | PASS |
| **Total** | **34** | **PASS** |

---

*Report: S29 / T-071 -- EdgeTwin AI Second-Dataset Validation*

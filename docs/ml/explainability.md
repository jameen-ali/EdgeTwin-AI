# EdgeTwin AI — Explainability Specification & Verification (T-015)

**Module:** `ml/models/explain.py`  
**Class:** `EdgeTwinExplainer`  
**Primary Engine:** TreeSHAP (`shap.TreeExplainer`)  
**Fallback Engine:** Native XGBoost (`Booster.predict(..., pred_contribs=True)`)  
**Author:** Mohamed Jameen Ali M R (Register No: 24AD0173)  
**Session:** S06 Phase 2  
**Baseline Model:** S05 Frozen Champion (`xgboost + physics`, 14 features, Platt sigmoid calibration)  

---

## 1. Core Architectural Principles

### 1.1 Explanation Space: Model Margin / Log-Odds
TreeSHAP explains the model's **raw margin (log-odds) space**, where additive feature attribution mathematically holds:

$$\text{margin}(x) = \text{base\_value} + \sum_{i=1}^{14} \phi_i(x)$$

> **CRITICAL RULE:** SHAP values are **NOT** additive percentage points of failure probability. They represent additive contributions to the uncalibrated tree ensemble margin.

### 1.2 Monotonic Connection with Platt Scaling (Sigmoid Calibration)
The calibrated probability $p_{\text{cal}}(x)$ is computed via a monotonic logistic sigmoid transformation of the margin:

$$p_{\text{cal}}(x) = \sigma(A \cdot \text{margin}(x) + B) = \frac{1}{1 + e^{-(A \cdot \text{margin}(x) + B)}}$$

Because $A > 0$ (Platt scaling slope), the sigmoid mapping is **strictly monotonically increasing**:
- $\phi_i > 0$ $\implies$ increases model margin $\implies$ **monotonically increases calibrated failure probability**
- $\phi_i < 0$ $\implies$ decreases model margin $\implies$ **monotonically decreases calibrated failure probability**
- $\phi_i \approx 0$ $\implies$ neutral contribution to risk

### 1.3 Statistical Association, Not Causation
All explanation payloads include the mandatory disclaimer:
> *"Statistical association with failure condition in model log-odds margin space; not causal."*

SHAP values quantify how features shift the model's prediction across the training distribution. They describe statistical patterns detected by the decision trees, **NOT causal physical mechanisms**. Modifying a high-SHAP feature (e.g., reducing rotational speed) does not physically guarantee prevention of mechanical failure.

---

## 2. Dynamic Feature Alignment & Leakage Protection

### 2.1 Positional Reordering in `ColumnTransformer`
Scikit-learn's `ColumnTransformer` partitions inputs into numeric transformers first, followed by categorical transformers. Consequently, `Machine_Type` (index 10 in the logical 14-feature input) is placed at index 13 in the transformed representation.

To prevent silent feature misalignment:
- Positional indexing is strictly forbidden.
- Transformed feature column names are dynamically and deterministically recovered via `preprocessor.get_feature_names_out()`.
- Transformed feature names map 1-to-1 with the 14 columns of the SHAP contribution matrix.

### 2.2 Leakage Protection
Every explanation input (`explain_instance`, `explain_prediction`, `explain_global`, `benchmark_latency`) must pass the project's authoritative leakage validator (`validate_no_leakage`), rejecting all 6 forbidden columns:
- `Failure_Type`
- `Machine_ID`
- `Timestamp`
- `Sensor_Batch_Code`
- `Checksum_Flag`
- `Machine_Failure`

---

## 3. Strict Additivity Guard

For every local explanation call, `EdgeTwinExplainer` computes:
$$\Delta_{\text{additivity}} = \left| \left( \text{base\_value} + \sum_{i=1}^{14} \phi_i \right) - \text{model\_margin} \right|$$

- **Tolerance:** $\epsilon = 10^{-4}$ ($1\times 10^{-4}$).
- **Measured Discrepancy:** $\approx 2.03 \times 10^{-6}$ (comfortably within tolerance).
- **Enforcement:** If $\Delta_{\text{additivity}} > 10^{-4}$, the explainer immediately raises a loud `ValueError`, halting prediction and preventing corrupted explanations from reaching edge telemetry logs.

---

## 4. Native XGBoost Zero-Dependency Fallback

If `shap` is unavailable or `shap.TreeExplainer` raises an unexpected runtime exception, `EdgeTwinExplainer` transparently falls back to native XGBoost:

```python
booster = self.classifier.get_booster()
dmat = xgb.DMatrix(X_trans)
contribs = booster.predict(dmat, pred_contribs=True)
shap_vals = contribs[:, :-1]
base_val = float(contribs[0, -1])
```

- **Output Shape:** `(N, 15)` where columns 0–13 are feature SHAP values and column 14 is the bias / base value.
- **Verification:** Verified numerically in `tests/ml/test_explain.py::TestNativeFallback` to produce identical results ($\Delta < 10^{-4}$) to `shap.TreeExplainer`.

---

## 5. Measured Latency Benchmark (SLA Verification)

### Benchmark Protocol
- Single warm-up explanation call (un-timed).
- 50 consecutive single-row explanation calls on validation telemetry.
- Timing measured via `time.perf_counter()`.
- Required SLA: $p95 < 100\text{ ms}$.

### Measured Performance
| Metric | Measured Value | SLA Target | Status |
|---|---|---|---|
| **Mean Latency** | **19.24 ms** | — | — |
| **Median Latency** | **19.24 ms** | — | — |
| **p95 Latency** | **20.12 ms** | **< 100.0 ms** | **PASSED** (79.9% margin) |
| **Max Latency** | **20.38 ms** | — | — |

The measured p95 latency of ~20 ms easily satisfies the 100 ms edge responsiveness SLA.

---

## 6. Global Feature Importance (Validation Background)

Computed via mean absolute SHAP values across all 1,490 validation rows (`X_val_eng`, zero test data accessed):

| Rank | Feature Name | Mean Absolute SHAP ($\overline{|\phi|}$) | Mean Signed SHAP ($\overline{\phi}$) | Directional Impact |
|---|---|---|---|---|
| 1 | `Tool_Wear_Min` | **1.1532** | -0.7236 | Strong risk differentiator |
| 2 | `Vibration_mm_s` | **0.9182** | -0.6127 | Strong risk differentiator |
| 3 | `Process_Temperature_C` | **0.8427** | -0.5113 | High thermal indicator |
| 4 | `Voltage_V` | **0.7004** | -0.5674 | Electrical stability indicator |
| 5 | `Current_A` | **0.5199** | -0.3515 | Electrical load indicator |
| 6 | `Torque_Nm` | **0.4790** | -0.2968 | Mechanical load indicator |
| 7 | `Air_Temperature_C` | **0.3079** | -0.1956 | Environmental baseline |
| 8 | `Pressure_bar` | **0.2112** | -0.1447 | Hydraulic / pneumatic status |
| 9 | `Rotational_Speed_RPM` | **0.2021** | -0.1241 | Kinematic operating point |
| 10 | `Apparent_Power_VA` | **0.1860** | -0.0533 | Combined physics power |
| 11 | `Delta_T_C` | **0.1818** | -0.1166 | Thermal differential |
| 12 | `Mech_Power_W` | **0.1472** | -0.1009 | Mechanical power output |
| 13 | `Operating_Hours` | **0.0936** | -0.0754 | Machine lifecycle age |
| 14 | `Machine_Type` | **0.0633** | +0.0223 | Machine structural variant |

---

## 7. Local Explanation Schema & Sample

Invoking `explain_prediction(X, top_k=5)` produces an API-friendly structure:

```json
{
  "base_value": 0.386633,
  "model_margin": -6.072550,
  "calibrated_probability": 0.010208,
  "top_factors": [
    {
      "feature_name": "Tool_Wear_Min",
      "feature_value": 165.2,
      "shap_value": -1.059785,
      "abs_magnitude": 1.059785,
      "direction": "lowers risk"
    },
    {
      "feature_name": "Vibration_mm_s",
      "feature_value": 1.12,
      "shap_value": -0.842103,
      "abs_magnitude": 0.842103,
      "direction": "lowers risk"
    }
  ],
  "additivity_verified": true,
  "additivity_discrepancy": 2.031e-06,
  "disclaimer": "Statistical association with failure condition in model log-odds margin space; not causal."
}
```

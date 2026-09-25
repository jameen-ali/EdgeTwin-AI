# T-014 Anomaly Detection & L4 Health Score Specification

## 1. Unsupervised Anomaly Detection

- **Model:** `IsolationForest(n_estimators=150, contamination=0.02, random_state=42)`
- **Training Population:** 6,081 healthy training observations (`train_df[Machine_Failure == 0]`).
- **Features:** 14 `+physics` columns (median imputation + ordinal encoding on Machine_Type).
- **Forbidden Columns Excluded:** `Machine_Failure`, `Failure_Type`, `Machine_ID`, `Timestamp`, `Sensor_Batch_Code`, `Checksum_Flag`.

### Anomaly Score Semantics & Normalization
- Bounded strictly in $[0.0, 1.0]$.
- Direction: **0.0 = completely nominal / healthy**, **1.0 = highly anomalous**.
- Reference points: $s_{\text{nominal}} = -0.41224$, $s_{\text{extreme}} = -0.55025$ ($\Delta = 0.13801$).
- Safeguarded against zero denominators, constant distributions, and NaNs (fallback: 0.50).

### Validation Performance
- **Validation ROC-AUC:** 0.8699
- **Validation PR-AUC:** 0.4639
- **Provisional Threshold (0.50):** Recall = 0.8045, FPR = 0.2006
- **Empirical Threshold (0.9075):** Recall = 0.2632, FPR = 0.0206

## 2. Layer 4 Health Score Architecture

The Health Score is an explainable, linear composite index in $[0, 100]$:

$$\text{Health Score} = \text{clip}\left(100 - (\Delta_{\text{risk}} + \Delta_{\text{anomaly}} + \Delta_{\text{sensor}}), 0.0, 100.0\right)$$

Where:
- **$\Delta_{\text{risk}} = 60.0 \times p_{\text{cal}}$:** Up to 60 points deducted based on calibrated failure probability.
- **$\Delta_{\text{anomaly}} = 25.0 \times a_{\text{anomaly}}$:** Up to 25 points deducted based on physical telemetry outlier score.
- **$\Delta_{\text{sensor}} = \min(15.0, \max(0.0, 5 \cdot N_{\text{out\_of\_range}} + 5 \cdot N_{\text{missing}}))$:** Strictly capped at 15 points maximum.

## 3. Health State Precedence Hierarchy

Deterministic precedence resolved in descending order:

1. **`OFFLINE`:** Telemetry loss, staleness > $3\times$ sampling interval, or broker disconnection. Output: `health_score = None`, `state = OFFLINE`.
2. **`MAINTENANCE_REQUIRED`:** Operational rule override: `Tool_Wear_Min >= 240.0` min OR technician work-order confirmation.
3. **`CRITICAL`:** $\text{Health Score} < 50.0$ OR $p_{\text{cal}} \ge 0.80$ OR edge hardware safety trip.
4. **`WARNING`:** $50.0 \le \text{Health Score} < 80.0$ OR $p_{\text{cal}} \ge 0.15$ OR $a_{\text{anomaly}} \ge 0.50$ OR $\Delta_{\text{sensor}} > 0$ OR $\ge 3$ missing sensors.
5. **`HEALTHY`:** $\text{Health Score} \ge 80.0$, $p_{\text{cal}} < 0.15$, $a_{\text{anomaly}} < 0.50$, and all sensors valid.

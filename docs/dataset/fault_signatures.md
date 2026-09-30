# fault_signatures.md — EdgeTwin AI Empirical Fault Signatures & Simulation Mapping

**Version:** 1.0 (S07 / T-021)  
**Status:** Authoritative Reference for Simulation and Synthetic Replay  
**Author:** EdgeTwin AI Engineering Team  

---

## 1. Overview & Methodological Distinction

The scenarios implemented in EdgeTwin AI (`simulation/scenarios/*.yaml`) are grounded in the empirical distributions and failure signatures discovered during exploratory data analysis (EDA) of the primary prepared dataset (`data/interim/predictive_maintenance_prepared.csv`).

To comply with **Rule 1** and **Rule 3** of the EdgeTwin AI Engineering Rulebook:
- **[EMPIRICAL]** designates values, distributions, correlations, and cluster centroids directly measured from the non-test training/validation partitions of the historical dataset.
- **[ASSUMPTION]** designates engineering choices, dynamic rates of change, noise models, and duration specifications required to simulate time-series behavior from static snapshot data.

---

## 2. Empirical Baseline Envelope (Healthy Operation)

### 2.1 Distributional Parameters
From the 6,081 non-failure training rows (`Machine_Failure == 0`):

| Sensor Measurement | Empirical Mean [EMPIRICAL] | Empirical Std [EMPIRICAL] | Authoritative Range [EMPIRICAL] | Unit |
|---|---|---|---|---|
| `Air_Temperature_C` | 25.4 | 2.5 | [0.0, 60.0] | °C |
| `Process_Temperature_C` | 35.3 | 2.8 | [0.0, 80.0] | °C |
| `Rotational_Speed_RPM` | 1548.0 | 179.0 | [0.0, 5000.0] | RPM |
| `Torque_Nm` | 40.1 | 10.1 | [0.0, 150.0] | N·m |
| `Vibration_mm_s` | 2.5 | 1.0 | [0.0, 20.0] | mm/s RMS |
| `Pressure_bar` | 5.5 | 1.8 | [0.0, 20.0] | bar |
| `Current_A` | 12.0 | 3.5 | [0.0, 50.0] | A |
| `Voltage_V` | 415.0 | 12.0 | [300.0, 500.0] | V |
| `Tool_Wear_Min` | 131.0 | 75.0 | [0.0, 300.0] | min |
| `Operating_Hours` | 10039.0 | 5785.0 | [0.0, 25000.0] | h |

### 2.2 Physical Coupling [EMPIRICAL & ASSUMPTION]
- **Thermal Tracking [EMPIRICAL]:** In healthy data, $T_{\text{air}}$ and $T_{\text{process}}$ correlate at $\rho = 0.90$. The nominal thermal differential is $\Delta T = T_{\text{process}} - T_{\text{air}} \approx 9.9^\circ\text{C}$.
- **Apparent Electrical Power [EMPIRICAL]:** $S = V \times I \approx 415\text{ V} \times 12\text{ A} \approx 4980\text{ VA}$.
- **Mechanical Shaft Power [EMPIRICAL]:** $P_{\text{mech}} = \tau \times \left(\omega \times \frac{2\pi}{60}\right) \approx 40.1 \times (1548 \times 0.10472) \approx 6500\text{ W}$.
- **Sensor Noise Model [ASSUMPTION]:** Additive zero-mean Gaussian white noise $\mathcal{N}(0, \sigma^2)$ is applied to steady-state operational points.

---

## 3. Fault Scenario Signatures

---

### SCN-01: Healthy Nominal Operation
* **Scenario ID:** `SCN-01-HEALTHY`
* **Target Failure Mode:** None (Normal operation).
* **Empirical Grounding [EMPIRICAL]:** Centered exactly at the empirical healthy means of the 6,081 non-failure training samples.
* **Simulated Trajectory [ASSUMPTION]:** Stationary operation with stochastic noise; tool wear accumulates at $0.1$ min/step; operating hours advance by $1\text{ s}$/step.
* **Feature Relationships [EMPIRICAL]:** Air and process temperatures track closely ($\Delta T \approx 9.9^\circ\text{C}$); torque and speed remain within the nominal mechanical power envelope.
* **Target ML Behavior:** Calibrated risk $p_{\text{fail}} < 0.15$ (`LOW` risk); anomaly score $a_{\text{anomaly}} < 0.35$; health score $\ge 85$ (`HEALTHY`).

---

### SCN-02: Heat Dissipation Failure (HDF)
* **Scenario ID:** `SCN-02-HEAT-DISSIPATION`
* **Target Failure Mode:** Heat Dissipation Failure.
* **Empirical Grounding [EMPIRICAL]:** In the training dataset, HDF instances exhibit elevated process temperatures ($> 60^\circ\text{C}$) and/or large temperature differentials ($\Delta T = T_{\text{process}} - T_{\text{air}} > 15^\circ\text{C}$ to $40^\circ\text{C}$), frequently accompanied by drive shaft speed droop under thermal friction.
* **Simulated Trajectory [ASSUMPTION]:** Linear degradation ramp over $60\text{ s}$:
  * $T_{\text{process}}$ climbs from $35.3^\circ\text{C} \to 68.0^\circ\text{C}$ ($+0.54^\circ\text{C}$/step).
  * $T_{\text{air}}$ climbs slightly from $25.4^\circ\text{C} \to 28.0^\circ\text{C}$.
  * $\Delta T$ expands from $9.9^\circ\text{C} \to 40.0^\circ\text{C}$.
  * Rotational speed droops from $1548 \to 1320$ RPM.
* **Feature Relationships [EMPIRICAL]:** Directly targets the calibrated champion model's derived feature `Delta_T_C` and raw `Process_Temperature_C`.
* **Target ML Behavior:** Calibrated risk $p_{\text{fail}}$ crosses $0.16$ and reaches $\ge 0.80$ (`CRITICAL`); top SHAP factor is `Process_Temperature_C` or `Delta_T_C`.

---

### SCN-03: Overstrain Failure (OSF)
* **Scenario ID:** `SCN-03-OVERSTRAIN`
* **Target Failure Mode:** Overstrain Failure.
* **Empirical Grounding [EMPIRICAL]:** In the training dataset, OSF instances result from the non-linear interaction between drive torque and tool wear. The empirical product $\tau \times \text{Tool\_Wear}$ exceeds $11,000$ to $12,000$ N·m·min (typical torque $\approx 65$–$80$ N·m with tool wear $> 200$ min).
* **Simulated Trajectory [ASSUMPTION]:**
  * Baseline tool wear pre-loaded at $215$ min.
  * Mechanical binding ramp over $40\text{ s}$: Torque ramps from $40.1 \to 75.0$ N·m ($+0.87$ N·m/step).
  * Motor current increases from $12.0 \to 22.0$ A to overcome load resistance.
  * Mechanical power $P_{\text{mech}}$ surges $> 11.5\text{ kW}$.
* **Feature Relationships [EMPIRICAL]:** Reproduces high $\text{Torque\_Nm}$, elevated $\text{Current\_A}$, high $\text{Tool\_Wear\_Min}$, and derived $\text{Mech\_Power\_W}$.
* **Target ML Behavior:** Calibrated risk $p_{\text{fail}}$ exceeds $0.16$ and reaches $\ge 0.85$ (`CRITICAL`); top SHAP factors include `Tool_Wear_Min`, `Torque_Nm`, and `Mech_Power_W`.

---

### SCN-04: Power Failure (PWF)
* **Scenario ID:** `SCN-04-POWER-FAILURE`
* **Target Failure Mode:** Power Failure.
* **Empirical Grounding [EMPIRICAL]:** In the training dataset, PWF instances are characterized by extreme electrical anomalies where apparent power $S = V \times I$ deviates drastically from the nominal $5000\text{ VA}$ envelope, caused by voltage sags/surges or phase overcurrent ($I > 25$ A or $V < 340$ V).
* **Simulated Trajectory [ASSUMPTION]:**
  * Instantaneous step change at $t=30\text{ s}$:
  * Current surges from $12.0 \to 32.0$ A.
  * Voltage sags from $415.0 \to 330.0$ V.
  * Resulting apparent power: $S = 330 \times 32 = 10,560\text{ VA}$ ($> 2\times$ nominal).
* **Feature Relationships [EMPIRICAL]:** Directly exercises `Voltage_V`, `Current_A`, and derived `Apparent_Power_VA`.
* **Target ML Behavior:** Calibrated risk $p_{\text{fail}} \ge 0.75$; edge safety trip `TRIP_OVERLOAD` activated.

---

### SCN-05: Tool Wear Failure (TWF) & Operational Override
* **Scenario ID:** `SCN-05-TOOL-WEAR`
* **Target Failure Mode:** Tool Wear Failure.
* **Empirical Grounding [EMPIRICAL]:** TWF rows in the training data exhibit tool wear exceeding $200$–$250$ min, accompanied by increased cutting friction and elevated high-frequency vibration ($> 3.5$ mm/s).
* **Simulated Trajectory [ASSUMPTION]:**
  * Pre-accumulated tool wear starting at $225$ min.
  * Accelerated wear progression at $0.25$ min/step ($225 \to 255$ min).
  * Vibration increases gradually from $2.5 \to 4.6$ mm/s.
* **Operational Override [T-014 Specification]:** When `Tool_Wear_Min >= 240` (reached at step 60), the health scoring engine forces machine state into `MAINTENANCE_REQUIRED` regardless of classifier probability.
* **Target ML Behavior:** Calibrated risk $p_{\text{fail}} \ge 0.16$; Digital Twin state transitions to `MAINTENANCE_REQUIRED`.

---

### SCN-06: Sudden High-Vibration / "Random" Failure (RNF)
* **Scenario ID:** `SCN-06-RANDOM-VIBRATION`
* **Target Failure Mode:** Random Failure.
* **Empirical Grounding [EMPIRICAL]:** A critical finding of our dataset exploratory analysis is that rows labelled "Random Failure" in this dataset are rule-generated synthetic clusters rather than physically stochastic anomalies: they systematically exhibit vibration velocity clustered around $7.4$ mm/s and fluid pressure clustered around $9.2$ bar.
* **Simulated Trajectory [ASSUMPTION]:** Instantaneous step change at $t=30\text{ s}$:
  * Vibration jumps from $2.5 \to 7.4$ mm/s.
  * Pressure jumps from $5.5 \to 9.2$ bar.
* **Feature Relationships [EMPIRICAL]:** Directly matches the empirical cluster centers of the dataset's RNF rows.
* **Target ML Behavior:** Calibrated risk $p_{\text{fail}} \ge 0.90$ (`CRITICAL`), consistent with the 100% recall observed in S05 test evaluation; immediate alarm.

---

### SCN-07: Sensor Dropout / Degradation
* **Scenario ID:** `SCN-07-SENSOR-DROPOUT`
* **Target Failure Mode:** None (Sensor telemetry fault).
* **Empirical Grounding [EMPIRICAL]:** In the raw dataset, $37.4\%$ of rows contain $\ge 1$ missing sensor reading.
* **Simulated Trajectory [ASSUMPTION]:**
  * Intermittent `null` sensor readings for `vibration_mm_s` ($t \in [20, 50]$) and `pressure_bar` ($t \in [35, 65]$).
* **Target ML Behavior:** The champion model's internal median imputer handles `null` values without throwing exceptions; predictions remain in `LOW` band under healthy underlying operation; sensor quality flagged `MISSING`; health score penalized by $\Delta_{\text{sensor}}$.

---

### SCN-08: Communication Loss / Machine Offline
* **Scenario ID:** `SCN-08-OFFLINE`
* **Target Failure Mode:** Telemetry transport loss.
* **Empirical Grounding [EMPIRICAL]:** Conforms to the Digital Twin FSM in `architecture.md` §9.
* **Simulated Trajectory [ASSUMPTION]:** Telemetry stream halts completely at $t=10\text{ s}$.
* **Target Behavior:** No ML predictions manufactured during silence; Digital Twin sync FSM transitions `LIVE` $\to$ `STALE` (after $3\times$ interval) $\to$ `OFFLINE` (after timeout); health engine overrides state to `OFFLINE`.

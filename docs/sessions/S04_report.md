# S04 Session Report

## 1. Session Information

- **Session:** S04
- **Model:** Claude Sonnet / Gemini 3.7 Flash
- **Task:** T-012 — Model Comparison with MLflow Experiment Tracking
- **Branch:** `feat/T-012-model-comparison`
- **Base Commit:** `17c2536` (S03 — feat(data): add versioned data contract and splits)
- **Author:** Mohamed Jameen Ali M R (Register No: 24AD0173)

---

## 2. Pre-Implementation Audit & Repository State

### Repository state
| Item | State |
|---|---|
| Base commit | `17c2536` ✓ |
| Branch | `feat/T-012-model-comparison` |
| Working tree | Clean at start of S04 |
| DVC pipeline | `dvc repro` verified functional; `data/interim/predictive_maintenance_prepared.csv` ready (9,885 rows x 17 cols) |
| Feature contract | S03 shared contract: 10 numeric sensors + Machine_Type = 11 base features (`TARGET_COLUMN = "Machine_Failure"`) |
| Split contract | Grouped Machine_ID split: 42 train / 9 val / 9 test machines (zero machine overlap) |

---

## 3. Candidate Models & Feature Sets

### Candidate models
1. **Logistic Regression:** baseline linear classifier with `StandardScaler` + `SimpleImputer(strategy='median')` + `class_weight='balanced'`.
2. **Decision Tree:** non-linear tree baseline (`max_depth=6`, `min_samples_leaf=5`, `class_weight='balanced'`).
3. **Random Forest:** ensemble bagged trees (`n_estimators=200`, `max_depth=10`, `min_samples_leaf=3`, `class_weight='balanced'`).
4. **HistGradientBoosting:** gradient-boosted trees with native NaN support (`max_iter=200`, `learning_rate=0.05`, `class_weight='balanced'`).
5. **XGBoost:** gradient-boosted trees with `scale_pos_weight` dynamically computed from train set positive ratio (`n_estimators=300`, `learning_rate=0.05`, `max_depth=6`).

### Feature sets
- **`base10` (11 features):** 10 raw sensors (`Air_Temperature_C`, `Process_Temperature_C`, `Rotational_Speed_RPM`, `Torque_Nm`, `Vibration_mm_s`, `Pressure_bar`, `Current_A`, `Voltage_V`, `Tool_Wear_Min`, `Operating_Hours`) + `Machine_Type`.
- **`+physics` (14 features):** `base10` + 3 physics-derived columns:
  - `Delta_T_C = Process_Temperature_C - Air_Temperature_C` (thermal dissipation differential)
  - `Apparent_Power_VA = Voltage_V * Current_A` (electrical apparent power)
  - `Mech_Power_W = Torque_Nm * (Rotational_Speed_RPM * 2 * pi / 60)` (mechanical shaft power)
- **`+wear_rate` (15 features):** `+physics` + `Wear_Rate = Tool_Wear_Min / Operating_Hours` (safely guarded against zero/NaN division).

### Leakage and safety verification
- All physics derivations are pure arithmetic on existing sensors — zero information from target (`Machine_Failure`) or administrative columns (`Failure_Type`, `Timestamp`, `Machine_ID`).
- Feature transformations are applied after data splitting — zero partition leakage.
- Missing values handled via `SimpleImputer(strategy='median')` fitted exclusively on training data.
- Categorical `Machine_Type` encoded via `OrdinalEncoder` fitted on training data with `handle_unknown='use_encoded_value', unknown_value=-1`.

---

## 4. Complete Candidate Validation Results (T-012 Experiment)

Selection rule:
- **Primary:** Validation PR-AUC (handles the ~10.97% class imbalance without false optimism)
- **Tie-break:** Validation Recall

| Model | Feature Set | n_features | Val Accuracy | Val Precision | Val Recall | Val F1 | Val ROC-AUC | Val PR-AUC | MLflow Run ID |
|---|---|---|---|---|---|---|---|---|---|
| **xgboost ★** | **+physics** | **14** | **0.9657** | **0.8015** | **0.8195** | **0.8104** | **0.9822** | **0.8969** | `bd7c1288181a461fbe43e994078e16bf` |
| xgboost | base10 | 11 | 0.9671 | 0.7958 | 0.8496 | 0.8218 | 0.9809 | 0.8967 | `c2a55bd1c43042ce880b87cf861c0c61` |
| xgboost | +wear_rate | 15 | 0.9617 | 0.7714 | 0.8120 | 0.7912 | 0.9805 | 0.8957 | `3eb65fda892949b0a9e425f2f4073abe` |
| hist_gradient_boosting | base10 | 11 | 0.9631 | 0.7910 | 0.7970 | 0.7940 | 0.9771 | 0.8875 | `e6793ef024dc4234a16e91aafb1a1880` |
| hist_gradient_boosting | +physics | 14 | 0.9657 | 0.8060 | 0.8120 | 0.8090 | 0.9779 | 0.8870 | `597ab4b262e549828b71d8dfd19116f6` |
| hist_gradient_boosting | +wear_rate | 15 | 0.9651 | 0.8045 | 0.8045 | 0.8045 | 0.9757 | 0.8806 | `6e5270e900784f3489a1795334b09a80` |
| random_forest | +physics | 14 | 0.9657 | 0.8534 | 0.7444 | 0.7952 | 0.9751 | 0.8702 | `a07d1a4783f94add89057e20eccde2a2` |
| random_forest | base10 | 11 | 0.9624 | 0.8348 | 0.7218 | 0.7742 | 0.9781 | 0.8681 | `58f14778edb1464c9cd2316e651d9b3a` |
| random_forest | +wear_rate | 15 | 0.9651 | 0.8462 | 0.7444 | 0.7920 | 0.9778 | 0.8599 | `05692fc2a7ce4cd796f0bf7e96fe7ad8` |
| logistic_regression | +wear_rate | 15 | 0.7931 | 0.2739 | 0.7970 | 0.4077 | 0.8830 | 0.5928 | `9babf1e5461645d58e92ed4401fa40e4` |
| logistic_regression | base10 | 11 | 0.7945 | 0.2753 | 0.7970 | 0.4093 | 0.8842 | 0.5911 | `6e6575a91215465384c0ae2f72b20bd9` |
| logistic_regression | +physics | 14 | 0.7952 | 0.2760 | 0.7970 | 0.4101 | 0.8832 | 0.5904 | `41707005a6714682b0bc5fde36bbf3ed` |
| decision_tree | +wear_rate | 15 | 0.9483 | 0.6892 | 0.7669 | 0.7260 | 0.8665 | 0.5494 | `5ae9a9a2f18849068bd8314fba32229d` |
| decision_tree | +physics | 14 | 0.9469 | 0.6824 | 0.7594 | 0.7189 | 0.8624 | 0.5397 | `fbdb78d28014476fae6004cc31f453ab` |
| decision_tree | base10 | 11 | 0.9429 | 0.6622 | 0.7368 | 0.6975 | 0.8500 | 0.5114 | `112d5adbc52c4be3bcc63c71ee5d61aa` |

★ = Selected Champion

---

## 5. Champion Details & Held-Out Test Evaluation

### Champion profile
- **Model:** `xgboost`
- **Feature Set:** `+physics` (14 features)
- **Validation PR-AUC:** 0.8969
- **Validation Recall:** 0.8195
- **Validation ROC-AUC:** 0.9822
- **Validation F1:** 0.8104
- **MLflow Run ID:** `bd7c1288181a461fbe43e994078e16bf`

### Single held-out test evaluation
Evaluated strictly **once** after champion selection on the held-out test partition (9 machines, 1,499 rows, zero overlap with train/val).
- **MLflow Test Run ID:** `0709463d1ee14acb9d325cb58a57e69f`

| Test Metric | Value |
|---|---|
| `test_accuracy` | 0.9693 |
| `test_precision` | 0.7908 |
| `test_recall` | 0.8963 |
| `test_f1` | 0.8403 |
| `test_roc_auc` | 0.9755 |
| `test_pr_auc` | 0.9234 |

### Test confusion matrix
| | Predicted No Failure | Predicted Failure | Total |
|---|---|---|---|
| **Actual No Failure** | 1,332 (TN) | 32 (FP) | 1,364 |
| **Actual Failure** | 14 (FN) | 121 (TP) | 135 |
| **Total** | 1,346 | 153 | 1,499 |

### Per-failure-type recall on test set
| Failure Type | Total in Test | Failures | Detected (TP) | Recall |
|---|---|---|---|---|
| Heat Dissipation Failure | 43 | 43 | 41 | 95.35% |
| Overstrain Failure | 46 | 46 | 43 | 93.48% |
| Power Failure | 20 | 20 | 15 | 75.00% |
| Tool Wear Failure | 17 | 17 | 13 | 76.47% |
| Random Failure | 9 | 9 | 9 | 100.00% |
| No Failure | 1,364 | 0 | 0 | 0.00% |

> Note: Tool Wear Failure was historically the weakest failure mode in earlier exploration (~58%). The `+physics` XGBoost model detected 13 of 17 tool wear failures (76.47% recall) at default 0.50 threshold without threshold optimization.

---

## 6. Audit & Root Cause Analysis: Champion Selection Inconsistency

### Discrepancy observed
In the initial completion summary, the champion was reported as `xgboost + physics` (Val PR-AUC = 0.8969, Test PR-AUC = 0.9234), but `docs/ml/model_comparison.md` displayed `decision_tree + base10` (Val PR-AUC = 0.5114, Test PR-AUC = 0.6601).

### Root cause identified
1. The full experiment `python -m ml.models.compare` ran cleanly and logged all 15 candidate runs and the champion test run to `mlflow.db`. It selected `xgboost + physics` as champion and wrote the complete table to `docs/ml/model_comparison.md`.
2. Subsequently, `python -m pytest` was executed to run the full test suite.
3. In `tests/ml/test_models.py`, the smoke test `test_comparison_champion_has_zero_machine_id_overlap` called `run_comparison(models=("decision_tree",), feature_sets=(FEATURE_SET_BASE,), ...)`.
4. While the test isolated MLflow tracking by passing an ephemeral `tmp_path / 'mlflow.db'` tracking URI, `run_comparison()` in `ml/models/compare.py` lacked an `output_path` parameter and had hardcoded:
   ```python
   comparison_path = _DOCS_ML_DIR / "model_comparison.md"
   write_comparison_table(all_results, champion, test_result, comparison_path)
   ```
5. As a result, the test execution overwrote the production artifact `docs/ml/model_comparison.md` with only the single model from the smoke test (`decision_tree`), along with its ephemeral test run ID (`50c6294411bc4677afac86f5f4baf380`).

### Corrective action implemented
1. **Added `output_path` parameter to `run_comparison()`**: Callers can now redirect report generation to any path. If not provided, it defaults to `docs/ml/model_comparison.md`.
2. **Updated smoke tests in `tests/ml/test_models.py`**: Both `test_comparison_smoke_no_cv` and `test_comparison_champion_has_zero_machine_id_overlap` now pass `output_path=tmp_path / "model_comparison.md"`, ensuring test executions never touch or mutate repository documentation.
3. **Reconciled `docs/ml/model_comparison.md`**: Restored the complete 15-candidate comparison table from the authoritative `mlflow.db` experiment records.
4. **Verified regression immunity**: Re-ran the complete 149-test suite; confirmed that `docs/ml/model_comparison.md` remained 100% byte-consistent and untouched after full test execution.

---

## 7. Verification & Deliverables

- **Unit tests:** 149 passed (`pytest`)
- **Linting:** 0 errors (`ruff check .`)
- **Formatting:** 100% compliant (`black --check .`)
- **All requirements met:**
  - Standardized feature engineering module (`ml/data/engineering.py`)
  - Pipeline creation with median imputation, ordinal encoding, and scaling rules (`ml/models/train.py`)
  - Evaluation module with full metric set + CM + per-failure recall (`ml/models/evaluate.py`)
  - Comparison orchestrator with MLflow tracking (`ml/models/compare.py`)
  - Test suite with 59 tests for T-012 (`tests/ml/test_models.py`)
  - Authoritative comparison report (`docs/ml/model_comparison.md`)
  - S04 session report (`docs/sessions/S04_report.md`)

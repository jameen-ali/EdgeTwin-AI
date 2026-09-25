# memory.md — EdgeTwin AI Project Memory

Living log. Update on every important decision, bug, fix, dependency, API or DB change. Newest entries at the top of each section.
Legend: [FACT] sourced · [AUDIT] measured by us on the uploaded files · [DECISION] · [PROPOSED] · [ASSUMPTION]
Last updated: 2026-09-24 (discovery phase, no code written yet)

---
## 1. Current status
- Discovery and research complete. Six core documents drafted (v0.1).
- **[T-001]** Repository scaffolded: `pyproject.toml`, `requirements.txt`, `.gitignore`, `.pre-commit-config.yaml`, `.env.example`, `gemini.md`, `.agents/rules/engineering.md`, and skeleton directories. Notebooks safely moved to `notebooks/`. Verification passed.
- **[T-003]** Reproducible data preparation pipeline implemented and verified. Branch `feat/T-003-data-preparation`. All 38 tests pass. ruff/black clean.
- **[T-010]** DVC versioning initialized. `dvc repro` works. `dvc status` clean after reproduction. Branch `feat/T-010-T-011-data-contract`. 90 tests pass.
- **[T-011]** Shared feature contract and machine-grouped splits implemented. 11 feature columns, 5 forbidden, Machine_Failure as target. Zero Machine_ID overlap. Failure rate within 5pp of 10.97% in all splits.
- **[T-012]** Model comparison experiment completed. Branch `feat/T-012-model-comparison`. 15 candidate (model × feature_set) combinations evaluated with 5-fold CV and MLflow tracking. Champion selected by validation PR-AUC: XGBoost with `+physics` (Val PR-AUC = 0.8969, Recall = 0.8195). Evaluated once on held-out test set: Test PR-AUC = 0.9234, Recall = 0.8963, F1 = 0.8403, Accuracy = 0.9693. Test isolation bug audited and fixed. 149 tests pass.
- **[T-013]** Probability calibration and threshold analysis completed. Platt/Sigmoid calibration selected on validation data (6.8% Brier error reduction, 86.4% ECE reduction, 0 loss in PR-AUC/ROC-AUC). 41 candidate thresholds swept (0.10..0.90, step 0.02). Operational decision threshold $t^* = 0.16$ cost-justified ($r=5$, Cost=137). 4 risk bands defined (LOW <0.15, MEDIUM 0.15..0.16, HIGH 0.16..0.80, CRITICAL >=0.80).
- **[T-014]** Unsupervised anomaly detection and Layer 4 Health Score completed. IsolationForest (contamination=0.02, 150 trees) trained on 6,081 healthy training rows with 14 features. Normalized scores [0, 1] with zero-denominator & NaN guards. Health score composite index $[0, 100]$ with strictly clamped sensor penalty $[0, 15]$. Deterministic state precedence hierarchy: OFFLINE > MAINTENANCE_REQUIRED (operational override) > CRITICAL > WARNING > HEALTHY. Single final test evaluation on held-out test set: Recall = 0.8963, Precision = 0.7610, F1 = 0.8231, Brier = 0.02055. 220 tests pass.
- **[T-002]** BLOCKED (dataset provenance not yet provided by user).
- Waiting on: (a) dataset provenance from the user, (b) UI reference website (only needed at T-050).

---

## S05 — T-013 Calibration & T-014 Anomaly/Health Scoring (2026-09-25)

### Task completion
- **Status:** DONE (T-013 and T-014)
- **Branch:** `feat/T-013-T-014-calibration-health`
- **Base Commit:** `cfb9b57` (S04 final reconciliation)
- **Files created:** `ml/models/calibrate.py`, `ml/models/thresholds.py`, `ml/models/anomaly.py`, `ml/models/health.py`, `tests/ml/test_calibration.py`, `tests/ml/test_thresholds.py`, `tests/ml/test_anomaly.py`, `tests/ml/test_health.py`, `scripts/run_s05.py`, `docs/ml/calibration.md`, `docs/ml/thresholds.md`, `docs/ml/health_model.md`, `docs/sessions/S05_report.md`
- **Files modified:** `tasks.md`, `memory.md`

### Calibration results [T-013 — MEASURED]
- Base S04 champion (`xgboost + physics`, 14 features) remained frozen.
- Calibration evaluated on `val_df` using `FrozenEstimator`:
  - Uncalibrated: Brier = 0.02810, ECE = 0.02867, PR-AUC = 0.89693, ROC-AUC = 0.98220
  - Sigmoid (Platt): Brier = 0.02619, ECE = 0.00391, PR-AUC = 0.89693, ROC-AUC = 0.98220 (Selected: 6.8% Brier error reduction, 86.4% ECE reduction, 0 PR-AUC ranking loss)
  - Isotonic: Brier = 0.02237, ECE = 0.00000, PR-AUC = 0.89004, ROC-AUC = 0.98474 (degrades PR-AUC ranking due to step-wise binning)

### Threshold analysis & risk bands [T-013 — MEASURED]
- 41 thresholds evaluated on `val_df` ($t \in [0.10, 0.90]$, step 0.02).
- F1-optimal: $t = 0.50$ (F1 = 0.8231, Recall = 0.8045, Precision = 0.8425)
- Cost-optimal ($r=1$): $t = 0.50$ (Cost = 46)
- Cost-optimal ($r=3$): $t = 0.16$ (Cost = 95)
- Cost-optimal ($r=5$): $t = 0.16$ (Cost = 137, Recall = 0.8421, Precision = 0.7778)
- Cost-optimal ($r=10$): $t = 0.16$ (Cost = 242)
- Operational decision threshold frozen at $t^* = 0.16$.
- Risk bands defined: LOW ($p < 0.15$), MEDIUM ($0.15 \le p < 0.16$), HIGH ($0.16 \le p < 0.80$), CRITICAL ($p \ge 0.80$).

### Unsupervised anomaly detector [T-014 — MEASURED]
- Model: `IsolationForest(n_estimators=150, contamination=0.02, random_state=42)`
- Training data: 6,081 healthy training rows (`train_df[Machine_Failure == 0]`). Zero target or post-hoc leakage.
- Features: 14 `+physics` features (median imputation + ordinal encoding on Machine_Type).
- Normalization: $s_{\text{nominal}} = -0.41224$ (95th pct), $s_{\text{extreme}} = -0.55025$ (1st pct), $\Delta = 0.13801$.
- Validation: ROC-AUC = 0.8699, PR-AUC = 0.4639.
- Thresholds: Provisional default = 0.50 (Recall = 0.8045, FPR = 0.2006); Empirical ($\alpha=0.02$) = 0.9075 (Recall = 0.2632, FPR = 0.0206).

### Layer 4 Health Score & precedence [T-014 — SPECIFICATION]
- Composite formula: $\text{Health Score} = \text{clip}(100 - (60 \cdot p_{\text{cal}} + 25 \cdot a_{\text{anomaly}} + \Delta_{\text{sensor}}), 0, 100)$
- Sensor penalty clamping: strictly $0 \le \Delta_{\text{sensor}} \le 15$.
- Deterministic state precedence hierarchy: `OFFLINE` > `MAINTENANCE_REQUIRED` (Tool_Wear_Min >= 240 or tech confirmation) > `CRITICAL` > `WARNING` > `HEALTHY`.

### Final held-out test evaluation [S05 — MEASURED]
- Evaluated ONCE on held-out test partition (1,499 rows, 9 machines) with frozen calibrator and $t^* = 0.16$:
  - Recall: 0.8963 (121/135 failures detected)
  - Precision: 0.7610 (38 false positives)
  - F1: 0.8231
  - F2: 0.8655
  - Accuracy: 0.9653
  - ROC-AUC: 0.9755
  - PR-AUC: 0.9234
  - Brier score: 0.02055 (17.5% reduction over uncalibrated baseline 0.02492)
  - Per-failure-type recall: Heat Dissipation = 95.35%, Overstrain = 93.48%, Power = 75.00%, Tool Wear = 76.47%, Random = 100.00%.

---

## S04 — T-012 Model Comparison (2026-09-25)

### Task completion
- **Status:** DONE (T-012)
- **Branch:** `feat/T-012-model-comparison`
- **Base Commit:** `17c2536` (S03 — feat(data): add versioned data contract and splits)
- **Files created:** `ml/data/engineering.py`, `ml/models/train.py`, `ml/models/evaluate.py`, `ml/models/compare.py`, `tests/ml/test_models.py`, `docs/ml/model_comparison.md`, `docs/sessions/S04_report.md`, `scripts/reconcile_comparison.py`
- **Files modified:** `pyproject.toml` (mlflow + xgboost added), `tasks.md`, `memory.md`

### Champion selection [T-012 — DECISION]
- **Selection Rule:** Validation PR-AUC (primary), Validation Recall (tie-break).
- **Champion:** `xgboost` with `+physics` (14 features).
  - Validation PR-AUC: 0.8969
  - Validation Recall: 0.8195
  - Validation F1: 0.8104
  - Validation ROC-AUC: 0.9822
  - Validation Accuracy: 0.9657
  - MLflow Run ID: `bd7c1288181a461fbe43e994078e16bf`

### Single held-out test evaluation [T-012 — MEASURED]
- Evaluated strictly once after champion selection on held-out test partition (9 machines, 1,499 rows).
- MLflow Test Run ID: `0709463d1ee14acb9d325cb58a57e69f`
- Test PR-AUC: 0.9234
- Test Recall: 0.8963
- Test F1: 0.8403
- Test Accuracy: 0.9693
- Test ROC-AUC: 0.9755
- Per-failure-type recall: Heat Dissipation = 95.35%, Overstrain = 93.48%, Power = 75.00%, Tool Wear = 76.47%, Random = 100.00%.

### Audit & test report isolation fix [T-012 — FIX]
- **Issue:** Initial docs showed Decision Tree + base10 instead of XGBoost + physics.
- **Root Cause:** In `ml/models/compare.py`, `run_comparison()` lacked an `output_path` parameter and had hardcoded `_DOCS_ML_DIR / "model_comparison.md"`. When `pytest` ran the smoke test `test_comparison_champion_has_zero_machine_id_overlap(models=("decision_tree",))`, it silently overwrote `docs/ml/model_comparison.md` with the single smoke-test model and ephemeral test run ID.
- **Fix:** Added `output_path: Path | None = None` to `run_comparison()`. Updated smoke tests in `tests/ml/test_models.py` to route reports to `tmp_path / "model_comparison.md"`. Reconciled `docs/ml/model_comparison.md` from `mlflow.db`. Confirmed `pytest` runs no longer touch `docs/ml/model_comparison.md`.

---

## S03 — T-010 + T-011 Data Contract (2026-09-25)

### Task completion
- **Status:** DONE (both T-010 and T-011)
- **Branch:** `feat/T-010-T-011-data-contract`
- **Base Commit:** `c6a992e` (S02 — feat(data): add reproducible preparation pipeline)
- **Files created:** `dvc.yaml`, `params.yaml`, `ml/data/features.py`, `ml/data/splits.py`, `tests/ml/test_features.py`, `tests/ml/test_splits.py`, `docs/sessions/S03_report.md`, `data/interim/splits/{train,val,test}.csv`
- **Files modified:** `ml/data/schema.py` (T-011 constants added), `ml/data/prepare.py` (--deterministic flag), `pyproject.toml` (scikit-learn + dvc added), `tasks.md`, `memory.md`, `.gitignore` (`data/interim/` added), `.dvc/` (init)
- **Files removed from Git tracking:** `data/interim/predictive_maintenance_prepared.csv`, `data/interim/data_quality_report.json` (now owned by DVC)

### DVC configuration [T-010 — DECISION]
- **DVC version:** 3.67.1
- **Remote:** None (local-only; no cloud credentials introduced)
- **Stage:** `prepare` — `cmd: python -m ml.data.prepare --deterministic`
- **Deps:** `data/raw/predictive_maintenance_dataset.csv`, `ml/data/prepare.py`, `ml/data/schema.py`
- **Params:** `params.yaml:pipeline.version`
- **Outs:** `data/interim/predictive_maintenance_prepared.csv`, `data/interim/data_quality_report.json`
- **dvc repro run 1:** Executed stage, generated `dvc.lock`, exit 0
- **dvc repro run 2:** "Stage 'prepare' didn't change, skipping", exit 0
- **dvc status:** "Data and pipelines are up to date"
- **Raw dataset:** NOT DVC-tracked (T-002 provenance BLOCKED; false provenance must not be created)

### --deterministic flag [T-010 — DECISION]
- `pipeline_timestamp_utc` in the quality report JSON is dynamic by default (real UTC).
- When `--deterministic` is passed (used by the DVC stage), it is replaced with the
  fixed string `"deterministic"`.
- This makes the JSON output byte-identical across runs so DVC can hash it stably.
- Human CLI runs (without the flag) still get the real timestamp.

### Schema contract [T-011 — DECISION]
New constants added to `ml/data/schema.py` (no breaking changes to T-003 constants):

| Constant | Value |
|---|---|
| `TARGET_COLUMN` | `"Machine_Failure"` |
| `FEATURE_COLUMNS` | 10 numeric sensors + `Machine_Type` = 11 columns |
| `CATEGORICAL_COLUMNS` | `["Machine_Type"]` |
| `IDENTIFIER_COLUMNS` | `["Machine_ID"]` |
| `TIME_COLUMNS` | `["Timestamp"]` |
| `ADMINISTRATIVE_COLUMNS` | `["Sensor_Batch_Code", "Checksum_Flag"]` |
| `LEAKAGE_COLUMNS` | `["Failure_Type"]` |
| `PREPARED_COLUMNS` | Same 17 as `EXPECTED_COLUMNS` |

### Feature contract [T-011 — DECISION]
- **Module:** `ml/data/features.py`
- **11 feature columns:** `Air_Temperature_C`, `Process_Temperature_C`, `Rotational_Speed_RPM`, `Torque_Nm`, `Vibration_mm_s`, `Pressure_bar`, `Current_A`, `Voltage_V`, `Tool_Wear_Min`, `Operating_Hours`, `Machine_Type`
- **Target:** `Machine_Failure` (binary: 0=healthy, 1=failure)
- **5 forbidden columns:** `Failure_Type`, `Machine_ID`, `Timestamp`, `Sensor_Batch_Code`, `Checksum_Flag`
- **No feature engineering at this stage:** DeltaT, apparent power, mechanical power, wear-rate etc. are T-012 additions
- **Leakage guard:** `validate_no_leakage()` raises `ValueError` if forbidden columns are present in a DataFrame passed to `select_features()`

### Split strategy [T-011 — DECISION]
- **Strategy:** Machine-level grouped split (NOT row-level random)
- **Rationale:** 60 unique Machine_IDs, each with 137-187 rows. Row-level splitting would leak machine-specific sensor calibration, wear patterns, and operating biases across train/test.
- **Algorithm:** Failure-rate-aware round-robin assignment
  1. Sort machines by per-machine `Machine_Failure` rate
  2. Round-robin over sorted list: assign to train / val / test cyclically
  3. Each split receives machines from the full range of failure rates (low/med/high)
- **This is NOT sklearn StratifiedGroupKFold.** StratifiedGroupKFold stratifies group-level target labels (which groups contain any failure). Our heuristic distributes per-machine failure *rates* proportionally, which is a different and more granular objective.
- **GroupShuffleSplit is also NOT used.** It provides no failure-rate control.

### Split results (seed=42) [T-011 — MEASURED]
| Split | Machines | Rows | Failure rate |
|---|---|---|---|
| Train | 42 | 6,897 | 11.83% |
| Validation | 9 | 1,489 | 8.93% |
| Test | 9 | 1,499 | 9.01% |
| Overall | 60 | 9,885 | 10.97% |

- Machine_ID overlap: **0** (zero overlap across all three splits — verified by test)
- All splits contain both classes (0 and 1)

### Machine-level leakage analysis [T-011 — AUDIT]
- 60 unique Machine_IDs; mean 164.75 rows per machine (min 137, max 187)
- All 60 machines have at least 1 failure (range 6.5%-17.3% per-machine rate)
- Row-level splitting would expose train rows from the same machine that appears in test → machine-level leakage
- **Chosen: grouped split by Machine_ID** — complete prevention

### Temporal leakage analysis [T-011 — AUDIT]
- Timestamps span 2024-01-01 to 2024-06-28 (~6 months)
- Tool_Wear_Min is NOT monotone within machines — not a strict time series
- Up to 6 readings per machine per day (sparse sensor snapshots, not regular intervals)
- **Decision:** Grouped machine split is appropriate. Temporal ordering within the training machines' rows is a T-012 modelling decision.
- **No temporal leak:** grouped by machine, not by time window

### Parameters [T-011]
```yaml
pipeline:
  version: "T-003/v1"
split:
  seed: 42
  train_frac: 0.70
  val_frac: 0.15
  test_frac: 0.15
  strategy: grouped_machine_id
  target_col: Machine_Failure
  group_col: Machine_ID
```

### Dependencies added [S03]
| Dependency | Version | Reason | Section |
|---|---|---|---|
| `scikit-learn` | `>=1.6,<2` | `numpy` / `pandas` integration; future use in splits | `[project].dependencies` |
| `dvc` | `>=3.0,<4` | T-010 data versioning pipeline | `[project.optional-dependencies].dev` |

### Output paths
- Prepared dataset (DVC): `data/interim/predictive_maintenance_prepared.csv` (9,885 x 17)
- Quality report (DVC): `data/interim/data_quality_report.json`
- Train split: `data/interim/splits/train.csv` (6,897 x 17, 42 machines)
- Val split: `data/interim/splits/val.csv` (1,489 x 17, 9 machines)
- Test split: `data/interim/splits/test.csv` (1,499 x 17, 9 machines)
- DVC lock: `dvc.lock`
- DVC config: `.dvc/config`

### Tests
- New: 21 feature tests (test_features.py) + 21 split tests (test_splits.py) = 42 new tests
- Total: 90 tests passing (38 T-003 + 42 new S03 + 2 smoke tests) — actually 90 passing including all categories

### Remaining limitations
- Dataset provenance still unverified (T-002 BLOCKED)
- No cloud DVC remote configured; `dvc push` will fail until a remote is added
- Split val/test failure rates (8.9%) are ~2pp below overall (11.0%) — acceptable given only 9 machines per group and the round-robin heuristic; exact stratification is not achievable with integer group assignment
- Scikit-learn is declared as a runtime dependency but `splits.py` only uses `numpy` (also a sklearn dep) directly; sklearn's API may be used more in T-012

---

## S02 — T-003 Data Preparation Pipeline (2026-09-25)


### Task completion
- **Status:** DONE
- **Branch:** `feat/T-003-data-preparation`
- **Base commit:** `18a63ec37b890a1007259b3e096d33659c6c98bd` (S01)
- **Files created:** `ml/__init__.py`, `ml/data/__init__.py`, `ml/data/schema.py`, `ml/data/prepare.py`, `tests/ml/__init__.py`, `tests/ml/test_prepare.py`, `data/interim/predictive_maintenance_prepared.csv`, `data/interim/data_quality_report.json`, `docs/sessions/S02_report.md`
- **Files modified (project config):** `pyproject.toml` (pandas dependency declared; package discovery enabled; black target-version added), `tasks.md`, `memory.md`

### Measured statistics [AUDIT — S02]
| Metric | Value |
|---|---|
| Raw input rows | 10,000 |
| Raw input columns | 17 |
| Machine_Type missing before | 490 |
| Machine_Type recovered from Machine_ID prefix | 490 |
| Machine_Type conflicts (non-null vs derived) | 0 |
| Duplicates detected (derive-first order) | 115 |
| Output rows | 9,885 |
| Output columns | 17 |
| Voltage_V violations (> 500 V) nullified | 22 |
| All other range violations | 0 |
| Machine_Type nulls in output | 0 |
| Missing sensor values preserved (not imputed) | Yes |

### Historical discrepancy reconciliation [AUDIT — S02]
- **Row count discrepancy:** The previously documented expected output of 9,894 rows was calculated using a dedup-first order (raw NaN Machine_Type is treated as distinct from non-null), which detects 106 duplicates. The T-003 spec mandates derive-first order (schema → derive_machine_type → remove_duplicates), which exposes 9 additional semantic duplicates (rows with NaN Machine_Type that become identical to existing rows after derivation). Derive-first is semantically correct and produces **9,885 rows**. Both orderings and their rationale are documented in `docs/sessions/S02_report.md`.
- **"339 mislabelled rows" reconciliation:** The figure "339" in prior memory.md/tasks.md referred approximately to the count of missing Machine_Type rows that would have been *incorrectly* assigned Compressor by mode imputation (i.e., non-Compressor rows). The actual figures: 490 missing Machine_Type rows total; 150 of those are CMP prefix (Compressor = correct by accident under mode imputation); 340 would be *incorrectly* assigned Compressor. The "339" was an off-by-one approximation. Corrected to 340 in this session.

### Implementation decisions [DECISION — S02]
- Pipeline order: schema_validate → derive_machine_type → remove_duplicates → validate_ranges. This is semantically correct: duplicate identity is evaluated on recovered values.
- Range violations are nullified to NaN (not clipped). Clipping was the notebook defect; nullification + reporting is the correct behaviour.
- No imputation at this stage. Missing sensor values remain NaN throughout the pipeline and in the output.
- `Sensor_Batch_Code` and `Checksum_Flag` are retained in the prepared output for traceability; they are excluded from duplicate comparison identity but not dropped from the dataset.
- `FORBIDDEN_FEATURE_COLUMNS` constant established: `[Failure_Type, Machine_ID, Timestamp, Sensor_Batch_Code, Checksum_Flag]`.

### Dependencies added [S02]
- `pandas>=2.2,<3` added to `[project].dependencies` in `pyproject.toml`. Justified: introduced as the first production/project Python code using pandas. No new dev or optional dependencies added.
- `pyproject.toml` package discovery changed from `packages = []` to `[tool.setuptools.packages.find]` to allow `ml` package and sub-packages to be importable after `pip install -e .`.
- `target-version = ["py311"]` added to `[tool.black]` to resolve Python version mismatch warning with black 26.x running on Python 3.13.

### Output paths
- Prepared dataset: `data/interim/predictive_maintenance_prepared.csv` (9,885 × 17)
- Quality report: `data/interim/data_quality_report.json`

### Missing-value policy
Missing sensor values are preserved as NaN and not imputed. Imputation belongs inside the sklearn `Pipeline` fit on training data only (T-010/T-012) to prevent evaluation leakage.

### Remaining limitations
- Dataset provenance still unverified (T-002 BLOCKED).
- `Sensor_Batch_Code` and `Checksum_Flag` are retained in the interim dataset; whether to drop them at the feature engineering stage is a T-011 decision.

---

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

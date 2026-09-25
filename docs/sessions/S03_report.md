# S03 Session Report

## 1. Session Information

- **Session:** S03
- **Model:** Claude Sonnet 4.6 (Thinking)
- **Tasks:** T-010 (DVC Data Versioning), T-011 (Schema Contract + Feature Module + Splits)
- **Branch:** `feat/T-010-T-011-data-contract`
- **Base Commit:** `c6a992e` (S02 — feat(data): add reproducible preparation pipeline)
- **Final Commit:** (see Section 7)

---

## 2. Pre-Implementation Audit

### Repository state

| Item | State |
|---|---|
| Branch | `feat/T-003-data-preparation` |
| Working tree | CLEAN |
| S02 commit | `c6a992e` ✓ |
| DVC installed | NOT INSTALLED |
| DVC files | None (no `.dvc/`, `dvc.yaml`, `params.yaml`) |
| `ml/data/features.py` | Does not exist |
| `ml/data/splits.py` | Does not exist |
| scikit-learn | 1.6.1 installed (not declared) |

### Dataset state (measured)

| Metric | Value |
|---|---|
| Prepared rows | 9,885 |
| Prepared columns | 17 |
| Unique Machine_IDs | 60 |
| Rows per machine | 137–187 (mean 164.75) |
| `Machine_Failure` = 1 | 1,084 (10.97%) |
| `Machine_Failure` = 0 | 8,801 (89.03%) |
| Timestamp range | 2024-01-01 to 2024-06-28 |
| All machines have ≥1 failure | Yes (60/60) |

### Existing T-003 state

- `ml/data/prepare.py` — fully functional pipeline
- `ml/data/schema.py` — schema constants including `FORBIDDEN_FEATURE_COLUMNS`
- 38 tests passing
- Prepared dataset: `data/interim/predictive_maintenance_prepared.csv` (committed to Git in S02)

### Existing DVC state

None. DVC not installed.

---

## 3. T-010 Implementation

### DVC configuration

- **DVC version:** 3.67.1
- **Remote:** None (local-only)
- **Initialized:** `dvc init` → created `.dvc/`, `.dvc/config`, `.dvcignore`

### DVC stage

```yaml
stages:
  prepare:
    cmd: python -m ml.data.prepare --deterministic
    deps:
      - data/raw/predictive_maintenance_dataset.csv
      - ml/data/prepare.py
      - ml/data/schema.py
    params:
      - params.yaml:
          - pipeline.version
    outs:
      - data/interim/predictive_maintenance_prepared.csv
      - data/interim/data_quality_report.json
```

**Design decisions:**

1. **`--deterministic` flag:** The quality report JSON contains `pipeline_timestamp_utc` which changes each run. Added `--deterministic` CLI flag to `prepare.py` that replaces the live timestamp with `"deterministic"`. The DVC stage uses this flag so JSON output is byte-identical across runs. Human CLI runs (without flag) still get real timestamps.

2. **Raw dataset NOT DVC-tracked:** T-002 dataset provenance is BLOCKED. Tracking the raw dataset under DVC would imply verified provenance that does not exist. The raw dataset is a dependency (immutable input) but not a DVC output.

3. **`data/interim/` removed from Git:** The prepared CSV and quality report were previously committed in S02. They were removed from Git tracking (`git rm --cached`) and `.gitignore` was updated so DVC owns them exclusively.

### Dependencies

- `dvc>=3.0,<4` added to `[project.optional-dependencies].dev` in `pyproject.toml`
- `scikit-learn>=1.6,<2` added to `[project].dependencies` (runtime; used by splits.py)

### Reproduction result

**Run 1:**
```
Running stage 'prepare':
> python -m ml.data.prepare --deterministic
[T-003] Loading raw data from: ...
=== EdgeTwin AI - Data Preparation Summary ===
  Source rows      : 10000  ...  Output rows    : 9885
  Schema valid: True
Generating lock file 'dvc.lock'
```
Exit: 0

**Run 2:**
```
Stage 'prepare' didn't change, skipping
Data and pipelines are up to date.
```
Exit: 0 — idempotent ✓

### Dataset tracking result

```
$ dvc status
Data and pipelines are up to date.
```

---

## 4. T-011 Implementation

### Schema (`ml/data/schema.py` additions)

New constants added — no T-003 constants modified:

| Constant | Value |
|---|---|
| `TARGET_COLUMN` | `"Machine_Failure"` |
| `FEATURE_COLUMNS` | 11 columns (below) |
| `CATEGORICAL_COLUMNS` | `["Machine_Type"]` |
| `IDENTIFIER_COLUMNS` | `["Machine_ID"]` |
| `TIME_COLUMNS` | `["Timestamp"]` |
| `ADMINISTRATIVE_COLUMNS` | `["Sensor_Batch_Code", "Checksum_Flag"]` |
| `LEAKAGE_COLUMNS` | `["Failure_Type"]` |
| `PREPARED_COLUMNS` | 17 (alias of `EXPECTED_COLUMNS`) |

### Feature contract (`ml/data/features.py`)

**11 feature columns:**
`Air_Temperature_C`, `Process_Temperature_C`, `Rotational_Speed_RPM`, `Torque_Nm`, `Vibration_mm_s`, `Pressure_bar`, `Current_A`, `Voltage_V`, `Tool_Wear_Min`, `Operating_Hours`, `Machine_Type`

**Public API:**

| Function | Description |
|---|---|
| `get_feature_columns()` | Returns copy of FEATURE_COLUMNS list |
| `get_target_column()` | Returns `"Machine_Failure"` |
| `get_forbidden_columns()` | Returns copy of FORBIDDEN_FEATURE_COLUMNS list |
| `select_features(df)` | Extracts feature cols; raises on leakage or missing cols |
| `select_target(df)` | Extracts Machine_Failure Series |
| `validate_no_leakage(df, context)` | Raises ValueError if forbidden col present |

### Target

`Machine_Failure` — binary integer (0=healthy, 1=failure).
- Verified from prepared dataset: values are {0, 1} only
- Failure rate: 10.97% (imbalanced; class weighting or resampling at T-012)

### Forbidden columns

`["Failure_Type", "Machine_ID", "Timestamp", "Sensor_Batch_Code", "Checksum_Flag"]`

All 5 are retained in the prepared dataset for traceability but excluded at feature selection time by the leakage guard.

### Split strategy

**Machine-level grouped split** — NOT row-level random, NOT `GroupShuffleSplit`, NOT `StratifiedGroupKFold`.

**Algorithm:** Failure-rate-aware round-robin assignment:
1. Compute per-machine `Machine_Failure` rate
2. Sort machines ascending by rate (tie-broken with seed-controlled noise)
3. Round-robin assignment over sorted list: train → val → test → train → ...
4. Result: each split receives machines from the full range of per-machine failure rates

**Why not sklearn's grouped split tools:**
- `GroupShuffleSplit`: does not control target distribution at all
- `StratifiedGroupKFold`: stratifies on whether each group (machine) is in the positive class — but since ALL 60 machines have failures, every group is "positive", making this stratification meaningless

### Split ratios

70% train / 15% validation / 15% test (as per S03 prompt default, not specified in project docs)

### Random seed

`42` — stored in `params.yaml` under `split.seed`

### Machine-level leakage analysis

| Metric | Value |
|---|---|
| Unique Machine_IDs | 60 |
| Rows per machine (min/max) | 137 / 187 |
| All machines have ≥1 failure | Yes |
| Machine_ID overlap in splits | 0 (verified by test) |

**Conclusion:** Row-level splitting leaks machine-specific sensor calibration, individual wear curves, and operating regime biases. Machine-level grouped split completely prevents this.

### Temporal leakage analysis

| Metric | Value |
|---|---|
| Timestamp range | 2024-01-01 to 2024-06-28 (~6 months) |
| Timestamp unique | 9,584 / 9,885 |
| Tool_Wear_Min monotone within machine | NO |
| Max readings per machine per day | 6 |

**Conclusion:** Data is sparse panel snapshots, not a strict time series. Tool_Wear_Min is not monotone, indicating readings are not always sequential. Grouped machine split is appropriate. Temporal structure within training rows is a T-012 modelling concern (e.g., whether to engineer lag features).

---

## 5. Tests

### New test files

**`tests/ml/test_features.py`** — 21 tests across 5 classes:
- `TestGetFeatureColumns`: 7 tests (count, membership, forbidden exclusion, target exclusion, list copy)
- `TestGetTargetColumn`: 2 tests
- `TestGetForbiddenColumns`: 7 tests (5 specific columns + count + list copy)
- `TestSelectFeatures`: 5 tests (correct columns, missing col, leakage guard, copy semantics)
- `TestSelectTarget`: 3 tests
- `TestValidateNoLeakage`: 4 tests
- `TestRegressionOnPreparedDataset`: 3 tests

**`tests/ml/test_splits.py`** — 21 tests across 7 classes:
- `TestBasicSplitProperties`: 4 tests (non-empty, size approximation, no overlap, full coverage)
- `TestDeterminism`: 3 tests (same seed, different seed, arbitrary seed)
- `TestTargetProperties`: 3 tests (target present, both classes, failure rate preserved)
- `TestSaveLoadRoundtrip`: 2 tests
- `TestErrorHandling`: 3 tests (missing group col, missing target col, invalid fractions)
- `TestFeatureColumnsInSplits`: 1 test
- `TestRegressionOnPreparedDataset`: 5 tests (real data: sizes, overlap, determinism, failure rate, save/load)

### pytest result

```
$ python -m pytest -q
....................................................................[  80%]
..................                                                   [100%]
90 passed in 3.43s
```

All 90 tests pass. 38 T-003 tests + 42 new S03 tests + 2 smoke tests = 90.

---

## 6. Static Checks

### ruff check

```
$ python -m ruff check .
All checks passed!
```
Exit: 0

### black --check

```
$ python -m black --check .
All done! ✨ 🍰 ✨
6 files would be left unchanged.
```
Exit: 0

---

## 7. DVC Verification

```
$ dvc repro
Running stage 'prepare':
> python -m ml.data.prepare --deterministic
... (pipeline output)
Generating lock file 'dvc.lock'
Updating lock file 'dvc.lock'
Exit: 0

$ dvc repro
Stage 'prepare' didn't change, skipping
Data and pipelines are up to date.
Exit: 0

$ dvc status
Data and pipelines are up to date.
Exit: 0
```

---

## 8. Data Integrity

| Check | Result |
|---|---|
| Raw CSV unchanged | ✓ PASS (hash verified) |
| Notebooks unchanged | ✓ PASS |
| T-003 behavior preserved | ✓ PASS (38 T-003 tests still pass) |
| Historical processed CSVs unchanged | ✓ PASS |
| No secrets in tracked files | ✓ PASS |
| No cloud credentials introduced | ✓ PASS |
| Prepared CSV deterministic | ✓ PASS (dvc repro idempotent) |
| Machine_ID overlap in splits | 0 ✓ |

---

## 9. Deviations

1. **`data/interim/` removed from Git** — This was necessary because the prepared CSV was committed in S02, but DVC cannot track files already tracked by Git. Files removed with `git rm --cached`; `.gitignore` updated. The data is not lost (DVC reproduces it on demand). The S02 commit still references these files in its tree, but the current working tree transfers ownership to DVC.

2. **Scikit-learn declared but not used directly in S03 code** — `splits.py` uses `numpy` directly (not sklearn's split classes). Scikit-learn is declared as a runtime dependency in anticipation of T-012 which will use sklearn pipelines, estimators, and cross-validation. This is a forward declaration consistent with the project architecture.

---

## 10. Problems / Surprises

1. **Prepared CSV already Git-tracked (from S02):** `dvc repro` failed with "output is already tracked by SCM (e.g. Git)". Fixed by `git rm --cached` on the two interim files and updating `.gitignore`. This is expected when transitioning from Git-only to DVC-managed artifacts.

2. **`pipeline_timestamp_utc` DVC instability:** Without the `--deterministic` flag, every `dvc repro` run would produce a different `data_quality_report.json` hash because the UTC timestamp changes. Fixed by adding `--deterministic` to the DVC stage command.

3. **Quality JSON removal from S02 Git history:** The S02 commit (`c6a992e`) still contains `data/interim/data_quality_report.json` in its tree. On the S03 branch, it is no longer tracked by Git (DVC-owned). This is correct DVC workflow; S02's commit is unmodified.

---

## 11. Dependencies Added

| Dependency | Version | Reason | Section in `pyproject.toml` |
|---|---|---|---|
| `scikit-learn` | `>=1.6,<2` | Runtime ML dependency; forward-declared for T-012 | `[project].dependencies` |
| `dvc` | `>=3.0,<4` | T-010 data versioning pipeline tool | `[project.optional-dependencies].dev` |

---

## 12. Open Questions

1. **DVC remote:** No cloud remote configured. `dvc push` will fail until a remote is set up (S26 CI/CD session). For now, the DVC cache is local only.

2. **Split failure rate imbalance:** Val (8.93%) and Test (9.01%) failure rates are ~2pp below the overall 10.97%. With only 9 machines per group, exact balance is not achievable. For T-012 model evaluation, this is acceptable; the test set still contains 135 failure rows.

3. **`Sensor_Batch_Code` / `Checksum_Flag` in splits:** These administrative columns are retained in the split DataFrames. The feature contract excludes them from `select_features()`. If they are needed for traceability in downstream tasks, they are accessible.

4. **T-002 provenance:** Still BLOCKED. The DVC pipeline dependency on the raw dataset is declared but the raw dataset's source, licence, and generation method remain unverified.

---

## 13. Recommended S04 Scope

> Do not implement S04 — this is a recommendation only.

**T-012 (Model Comparison)** is the natural next step. Before starting:

1. The feature contract is ready: `ml/data/features.py` provides `select_features(df)` and `select_target(df)`.
2. The split is ready: `ml/data/splits.py` with `split_dataset(df, seed=42)`.
3. **Training input:** Call `select_features()` on the training split's feature-only DataFrame (after removing forbidden cols). No imputation is included — the champion GBDT model should use native NaN handling.
4. **Leakage guard test is required by T-012:** A test that fails if a forbidden column is in the feature set.
5. **No feature engineering yet:** T-012 will introduce the physics-derived features (DeltaT, apparent power, etc.) and ablate them against the base feature set.
6. **MLflow:** Will be introduced at T-012 for experiment tracking. The pyproject.toml will need `mlflow` added.
7. **Class imbalance:** 10.97% positive rate. Use `class_weight='balanced'` in sklearn estimators or `scale_pos_weight` in XGBoost. Do not oversample/undersample before T-012.

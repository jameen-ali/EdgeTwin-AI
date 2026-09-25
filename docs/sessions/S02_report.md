# S02 Session Report

## 1. Session Information

- **Session:** S02
- **Model:** Claude Sonnet 4.6 (Thinking)
- **Task:** T-003 — Fix the Data Pipeline Defects Found in the Data Audit
- **Branch:** `feat/T-003-data-preparation`
- **Base Commit:** `18a63ec37b890a1007259b3e096d33659c6c98bd` (S01 — chore(repo): scaffold EdgeTwin project)
- **Final Commit:** (see end of report)

---

## 2. Pre-Implementation Audit

All values independently measured from the raw dataset before any implementation.

| Metric | Value |
|---|---|
| Raw row count | 10,000 |
| Raw column count | 17 |
| Missing `Machine_Type` | 490 |
| Prefix-derived corrections possible | 490 (all missing rows have valid prefixes) |
| Conflicting non-null `Machine_Type` (vs prefix) | 0 |
| Would be incorrectly Compressor under mode imputation | 340 |
| Duplicate rows — dedup-first order (raw NaN preserved) | 106 → 9,894 output |
| Duplicate rows — derive-first order (spec-mandated) | 115 → 9,885 output |
| Existing processed CSV row count | 9,893 (historical; 15 cols) |
| `Voltage_V` violations (> 500 V) | 22 |
| All other sensor range violations | 0 |

---

## 3. Task Status

**DONE**

All 16 acceptance criteria (A1–A16) are met:

| AC | Criterion | Met? |
|---|---|---|
| A1 | Reproducible Python preparation script exists | ✓ |
| A2 | Raw dataset remains immutable (hash verified) | ✓ |
| A3 | Machine_Type derived from Machine_ID prefix, not mode | ✓ |
| A4 | Duplicate detection ignores Sensor_Batch_Code/Checksum_Flag | ✓ |
| A5 | Missing sensor values remain NaN | ✓ |
| A6 | Range violations detected, documented, not clipped | ✓ |
| A7 | Prepared data written to data/interim/ | ✓ |
| A8 | Quality report records every modification category | ✓ |
| A9 | Forbidden feature columns explicitly defined | ✓ |
| A10 | Unit and regression tests pass (36 + 2 = 38 total) | ✓ |
| A11 | Two pipeline runs produce deterministic output (SHA-256 verified) | ✓ |
| A12 | `ruff check` passes | ✓ |
| A13 | `black --check` passes | ✓ |
| A14 | `pytest` passes (38/38) | ✓ |
| A15 | `tasks.md` and `memory.md` updated | ✓ |
| A16 | S02 report exists | ✓ |

---

## 4. Implementation

### Files created

| File | Purpose |
|---|---|
| `ml/__init__.py` | Package marker |
| `ml/data/__init__.py` | Package marker |
| `ml/data/schema.py` | Schema constants, range bounds, prefix map, `FORBIDDEN_FEATURE_COLUMNS`, `validate_schema()` |
| `ml/data/prepare.py` | Full preparation pipeline: `load_raw_data`, `derive_machine_type`, `remove_duplicates`, `validate_ranges`, `build_quality_report`, `save_outputs`, `prepare_dataset`, `main` (CLI) |
| `tests/ml/__init__.py` | Package marker |
| `tests/ml/test_prepare.py` | 36 unit tests across 8 test classes (T1–T8) |

### Files modified

| File | Change |
|---|---|
| `pyproject.toml` | Added `pandas>=2.2,<3` runtime dependency; switched to `[tool.setuptools.packages.find]` auto-discovery; added `target-version = ["py311"]` to `[tool.black]` |
| `tasks.md` | T-003 status set to DONE with measured evidence |
| `memory.md` | S02 entry added with all statistics and decisions |

### Files generated (pipeline output)

| File | Description |
|---|---|
| `data/interim/predictive_maintenance_prepared.csv` | Prepared dataset (9,885 × 17) |
| `data/interim/data_quality_report.json` | Machine-readable quality report |

### Files intentionally untouched

- `data/raw/predictive_maintenance_dataset.csv` — immutable raw dataset (SHA-256 verified before and after pipeline run)
- `notebooks/01_Data_Understanding.ipynb` — historical EDA record
- `notebooks/02_Feature_Engineering.ipynb` — historical EDA record
- `data/processed/predictive_maintenance_cleaned.csv` — historical artifact
- `data/processed/predictive_maintenance_engineered.csv` — historical artifact
- `rules.md`, `prd.md`, `architecture.md`, `design.md` — core documents (read-only)

---

## 5. Data Transformation Summary

```
Input rows              : 10,000
Machine_Type recovered  :    490  (all missing; 340 would have been wrong via mode)
Machine_Type conflicts  :      0  (all non-null values consistent with prefix)
Duplicates removed      :    115  (106 raw + 9 semantic after derivation)
Output rows             :  9,885
Voltage_V nullified     :     22  (values > 500 V; not clipped)
Other range violations  :      0
Missing sensor values   : preserved as NaN throughout (no imputation)
```

### Missing value counts (before → after)

| Column | Before | After | Notes |
|---|---|---|---|
| Air_Temperature_C | 806 | 806 | preserved |
| Process_Temperature_C | 135 | 135 | preserved |
| Rotational_Speed_RPM | 1,024 | 1,024 | preserved |
| Torque_Nm | 130 | 130 | preserved |
| Vibration_mm_s | 413 | 413 | preserved |
| Pressure_bar | 749 | 748 | 1 fewer after dedup |
| Current_A | 97 | 97 | preserved |
| Voltage_V | 676 | 698 | +22 from nullification of OOB values |
| Tool_Wear_Min | 271 | 271 | preserved |
| Operating_Hours | 213 | 213 | preserved |

---

## 6. Tests

### Test classes and individual tests (36 tests)

| Class | Test | Status |
|---|---|---|
| T1 TestPrefixMapping | `test_all_five_prefixes_in_map[CMP-Compressor]` | PASS |
| T1 TestPrefixMapping | `test_all_five_prefixes_in_map[PMP-Pump]` | PASS |
| T1 TestPrefixMapping | `test_all_five_prefixes_in_map[CNC-CNC_Machine]` | PASS |
| T1 TestPrefixMapping | `test_all_five_prefixes_in_map[CNV-Conveyor]` | PASS |
| T1 TestPrefixMapping | `test_all_five_prefixes_in_map[MOT-Motor]` | PASS |
| T1 TestPrefixMapping | `test_map_has_exactly_five_entries` | PASS |
| T2 TestMissingMachineTypeRecovery | `test_null_machine_type_filled_from_id` | PASS |
| T2 TestMissingMachineTypeRecovery | `test_report_counts_recovered` | PASS |
| T2 TestMissingMachineTypeRecovery | `test_non_null_machine_type_preserved_when_consistent` | PASS |
| T3 TestConflictingMachineTypeDetection | `test_conflict_detected_and_reported` | PASS |
| T3 TestConflictingMachineTypeDetection | `test_conflict_value_overridden_with_derived` | PASS |
| T3 TestConflictingMachineTypeDetection | `test_zero_conflicts_in_consistent_data` | PASS |
| T4 TestDuplicateRemoval | `test_rows_differing_only_in_batch_code_removed` | PASS |
| T4 TestDuplicateRemoval | `test_rows_differing_only_in_checksum_removed` | PASS |
| T4 TestDuplicateRemoval | `test_rows_differing_in_sensor_value_kept` | PASS |
| T4 TestDuplicateRemoval | `test_ignore_columns_defined_correctly` | PASS |
| T4 TestDuplicateRemoval | `test_first_occurrence_kept` | PASS |
| T5 TestMissingValuesPreserved | `test_nan_sensor_preserved_through_derive` | PASS |
| T5 TestMissingValuesPreserved | `test_nan_sensor_preserved_through_dedup` | PASS |
| T5 TestMissingValuesPreserved | `test_nan_within_range_not_touched_by_range_validator` | PASS |
| T5 TestMissingValuesPreserved | `test_multiple_nan_columns_preserved` | PASS |
| T6 TestRangeViolation | `test_voltage_above_500_detected` | PASS |
| T6 TestRangeViolation | `test_voltage_above_500_nullified_not_clipped` | PASS |
| T6 TestRangeViolation | `test_valid_voltage_at_boundary_not_flagged` | PASS |
| T6 TestRangeViolation | `test_total_violation_count_reported` | PASS |
| T6 TestRangeViolation | `test_range_bounds_present_in_report` | PASS |
| T7 TestNoImputationPerformed | `test_pipeline_does_not_fill_nan_with_mean_or_median` | PASS |
| T7 TestNoImputationPerformed | `test_pipeline_does_not_fill_nan_with_zero` | PASS |
| T7 TestNoImputationPerformed | `test_pipeline_does_not_forward_fill` | PASS |
| T8 TestRegressionOnRawDataset | `test_output_row_count` | PASS |
| T8 TestRegressionOnRawDataset | `test_machine_type_fully_recovered` | PASS |
| T8 TestRegressionOnRawDataset | `test_voltage_violations_nullified` | PASS |
| T8 TestRegressionOnRawDataset | `test_no_other_range_violations` | PASS |
| T8 TestRegressionOnRawDataset | `test_no_machine_type_null_in_output` | PASS |
| T8 TestRegressionOnRawDataset | `test_raw_dataset_unchanged` | PASS |
| T8 TestRegressionOnRawDataset | `test_pipeline_deterministic` | PASS |
| (S01) test_project_folders_exist | — | PASS |
| (S01) test_env_example_secrets_empty | — | PASS |

**pytest -q result:**
```
......................................                                   [100%]
38 passed in 2.64s
```

---

## 7. Static Verification

### ruff check

```
$ python -m ruff check .
All checks passed!
```
Exit code: 0

### black --check

```
$ python -m black --check .
All done! ✨ 🍰 ✨
4 files would be left unchanged.
```
Exit code: 0

---

## 8. Determinism Verification

The pipeline was run twice on the same raw input:

```
Run 1 SHA-256 of predictive_maintenance_prepared.csv:
  643b2410bfe621fb058c66ca3e2b2014cb008131df99f4bb4511cbcb4399b9d3

Run 2 SHA-256 of predictive_maintenance_prepared.csv:
  643b2410bfe621fb058c66ca3e2b2014cb008131df99f4bb4511cbcb4399b9d3

DETERMINISM: PASS
```

Both runs produce byte-identical CSV output. The JSON quality report contains a `pipeline_timestamp_utc` field which is intentionally dynamic metadata; the data content is deterministic.

---

## 9. Data Integrity

| Check | Result |
|---|---|
| Raw CSV unchanged (SHA-256 before = after pipeline) | ✓ PASS |
| Notebooks unchanged | ✓ PASS (hashes verified) |
| Existing processed CSVs unchanged | ✓ PASS (hashes verified) |
| No secrets in source code | ✓ PASS |
| No absolute Windows paths in source code | ✓ PASS |
| Machine_Type nulls in output | 0 |
| Voltage_V out-of-range values nullified (not clipped) | 22 |
| Missing sensor values preserved as NaN | ✓ PASS |

---

## 10. Historical Audit Reconciliation

### Row count: 9,894 vs 9,885

The previously documented value of **9,894** was computed using a **dedup-first** approach:
- Duplicates detected on raw data (Machine_Type NaN treated as distinct from non-null): **106**
- 10,000 − 106 = **9,894**

The T-003 spec mandates **derive-first** order (schema → derive_machine_type → remove_duplicates). Under this order:
- 490 missing Machine_Type values are filled from Machine_ID prefix.
- 9 rows that previously had `Machine_Type=NaN` now become semantically identical to existing rows with the derived type and identical sensor values → detected as additional duplicates.
- Total duplicates removed: **106 + 9 = 115**
- 10,000 − 115 = **9,885** (the implemented, measured result)

The derive-first order is semantically correct because duplicate identity should be evaluated on recovered (meaningful) column values, not raw incomplete data.

### Machine_Type "339 mislabelled" vs "340"

The figure **"339"** in prior memory.md/tasks.md was an off-by-one approximation. The correct measured values:
- 490 rows with missing Machine_Type
- 150 of those have CMP prefix → Compressor (mode imputation accidentally correct)
- **340** would have been incorrectly assigned Compressor by mode imputation

Corrected to **340** in this session.

### Existing processed CSV: 9,893 vs raw minus duplicates

The historical processed CSV has **9,893 rows** (not 9,894 or 9,885). This is a separate notebook artifact from before S01. It is not modified in T-003. Its row count is not required to match the new pipeline output.

---

## 11. Dependencies

| Dependency | Version | Reason | Declared in |
|---|---|---|---|
| `pandas` | `>=2.2,<3` | First production Python code using pandas | `pyproject.toml` `[project].dependencies` |

No other dependencies were added.

Also:
- `[tool.setuptools.packages.find]` enabled (was `packages = []`) — package discovery, not a new dependency.
- `target-version = ["py311"]` added to `[tool.black]` — formatting config, not a dependency.

---

## 12. Deviations

None. Implementation follows the approved Phase 1 plan exactly.

---

## 13. Problems / Surprises

1. **Windows cp1252 encoding:** The CLI summary used Unicode em-dash and arrow characters (`—`, `→`) which caused `UnicodeEncodeError` on the Windows cp1252 terminal. Fixed by replacing with ASCII equivalents.

2. **Single-row DataFrame None vs float nan:** When constructing single-row DataFrames from dicts with `None` for float columns, pandas keeps `dtype=object`, so `.loc[0, col]` returns Python `None` rather than `float('nan')`. `math.isnan(None)` raises `TypeError`. Fixed by introducing a `_is_missing()` helper in the test file that handles both representations. This is a known pandas behaviour and is documented in the test file.

3. **Package discovery was disabled:** `pyproject.toml` had `packages = []`, which prevented `ml` from being importable after `pip install -e .`. Fixed by switching to `[tool.setuptools.packages.find]`.

4. **Black version target mismatch:** black 26.x defaulted to Python 3.15 target syntax on a Python 3.13 runtime, causing `black --check` to fail with a safety-check warning. Fixed by adding `target-version = ["py311"]` to `[tool.black]`.

---

## 14. Open Questions

1. **Dataset provenance / T-002:** The raw dataset's source, licence, and generation method remain unknown. T-002 is BLOCKED pending user input. The prepared dataset is labelled "provenance unverified" throughout.

2. **Sensor_Batch_Code / Checksum_Flag retention:** These administrative columns are retained in the interim prepared dataset. Whether they should be dropped before feature engineering is a T-011 decision.

---

## 15. Recommended S03 Scope

> Do not implement S03 — this is a recommendation only.

**T-010** (Reproducible data stage with DVC + schema validation + train/val/test split) is the natural next step. Before starting:

1. Consider whether DVC requires any environment setup or authentication for the local remote.
2. Decide on train/val/test split proportions and stratification column (`Machine_Failure`).
3. Confirm `params.yaml` design (split seed, sizes, schema version).
4. The prepared dataset at `data/interim/predictive_maintenance_prepared.csv` (9,885 × 17) is the correct input for T-010.
5. `ml/data/schema.py` constants (`FORBIDDEN_FEATURE_COLUMNS`, `SENSOR_RANGES`, etc.) should be imported by T-010's DVC stage rather than redefined.

Alternatively, **T-004** (Research documents) can be completed independently and in parallel with T-010 setup since it has no code dependencies.

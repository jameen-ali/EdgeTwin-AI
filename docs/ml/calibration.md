# T-013 Probability Calibration

> Calibration evaluates whether predicted probabilities represent true empirical failure rates.
> Protocol: Evaluated on `val_df` using `FrozenEstimator(pipeline)` to protect the frozen S04 champion model.

## Calibration Comparison on Validation Set

| Method | Brier Score | ECE | PR-AUC | ROC-AUC | Status |
|---|---|---|---|---|---|
| `uncalibrated` | 0.02810 | 0.02867 | 0.89693 | 0.98220 | Evaluated |
| `sigmoid` | 0.02619 | 0.00391 | 0.89693 | 0.98220 | ★ Selected |
| `isotonic` | 0.02237 | 0.00000 | 0.89004 | 0.98474 | Evaluated |

## Method Selection Rationale

- **Selected Production Method:** `sigmoid`
- **Brier Score Reduction:** Sigmoid calibration (Platt scaling) reduces the validation Brier score from 0.02810 to 0.02619 (~6.8% error reduction) while preserving ranking discrimination (PR-AUC: 0.8969).
- **Isotonic Behavior:** Isotonic regression reduces Brier score further (0.02237) but slightly degrades PR-AUC ranking (0.8900) due to step-wise binning on 133 minority validation events.
- **Decision:** Sigmoid calibration selected as the robust, monotonic parametric calibration function.

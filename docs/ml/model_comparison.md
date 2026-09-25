# T-012 Model Comparison

> Selection criterion: Validation PR-AUC (primary), Recall (tie-break).
> Test evaluation performed once on the held-out test partition after champion selection.

## Validation Results

| Model | Feature Set | n_feat | Val Accuracy | Val Precision | Val Recall | Val F1 | Val ROC-AUC | Val PR-AUC |
|---|---|---|---|---|---|---|---|---|
| xgboost ★ | +physics | 14 | 0.9657 | 0.8015 | 0.8195 | 0.8104 | 0.9822 | 0.8969 |
| xgboost | base10 | 11 | 0.9671 | 0.7958 | 0.8496 | 0.8218 | 0.9809 | 0.8967 |
| xgboost | +wear_rate | 15 | 0.9617 | 0.7714 | 0.8120 | 0.7912 | 0.9805 | 0.8957 |
| hist_gradient_boosting | base10 | 11 | 0.9631 | 0.7910 | 0.7970 | 0.7940 | 0.9771 | 0.8875 |
| hist_gradient_boosting | +physics | 14 | 0.9657 | 0.8060 | 0.8120 | 0.8090 | 0.9779 | 0.8870 |
| hist_gradient_boosting | +wear_rate | 15 | 0.9651 | 0.8045 | 0.8045 | 0.8045 | 0.9757 | 0.8806 |
| random_forest | +physics | 14 | 0.9657 | 0.8534 | 0.7444 | 0.7952 | 0.9751 | 0.8702 |
| random_forest | base10 | 11 | 0.9624 | 0.8348 | 0.7218 | 0.7742 | 0.9781 | 0.8681 |
| random_forest | +wear_rate | 15 | 0.9651 | 0.8462 | 0.7444 | 0.7920 | 0.9778 | 0.8599 |
| logistic_regression | +wear_rate | 15 | 0.7931 | 0.2739 | 0.7970 | 0.4077 | 0.8830 | 0.5928 |
| logistic_regression | base10 | 11 | 0.7945 | 0.2753 | 0.7970 | 0.4093 | 0.8842 | 0.5911 |
| logistic_regression | +physics | 14 | 0.7952 | 0.2760 | 0.7970 | 0.4101 | 0.8832 | 0.5904 |
| decision_tree | +wear_rate | 15 | 0.9483 | 0.6892 | 0.7669 | 0.7260 | 0.8665 | 0.5494 |
| decision_tree | +physics | 14 | 0.9469 | 0.6824 | 0.7594 | 0.7189 | 0.8624 | 0.5397 |
| decision_tree | base10 | 11 | 0.9429 | 0.6622 | 0.7368 | 0.6975 | 0.8500 | 0.5114 |

★ = Selected champion

## Champion Details

- **Model:** xgboost
- **Feature set:** +physics
- **n_features:** 14
- **Val PR-AUC:** 0.8969
- **Val Recall:** 0.8195
- **MLflow run id:** bd7c1288181a461fbe43e994078e16bf

## Final Test Results (champion only)

| Metric | Value |
|---|---|
| test_accuracy | 0.9693 |
| test_precision | 0.7908 |
| test_recall | 0.8963 |
| test_f1 | 0.8403 |
| test_roc_auc | 0.9755 |
| test_pr_auc | 0.9234 |

## Per-Failure-Type Recall on Test Set

| Failure Type | Count | Failures | Detected | Recall |
|---|---|---|---|---|
| Heat Dissipation Failure | 43 | 43 | 41 | 0.9535 |
| No Failure | 1364 | 0 | 0 | 0.0000 |
| Overstrain Failure | 46 | 46 | 43 | 0.9348 |
| Power Failure | 20 | 20 | 15 | 0.7500 |
| Random Failure | 9 | 9 | 9 | 1.0000 |
| Tool Wear Failure | 17 | 17 | 13 | 0.7647 |

## Champion Test Confusion Matrix

| | Predicted No Failure | Predicted Failure |
|---|---|---|
| **Actual No Failure** | 1332 (TN) | 32 (FP) |
| **Actual Failure** | 14 (FN) | 121 (TP) |

## Notes

- Target class imbalance: ~10.97% positive (Machine_Failure == 1).
- Split: grouped by Machine_ID (42 train / 9 val / 9 test machines).
- Preprocessing fitted on training data only.
- No threshold optimization performed (belongs to T-013).
- XGBoost scale_pos_weight computed from actual training label ratio.
- Tool Wear Failure is the historically weakest sub-class; see per-failure-type recall.

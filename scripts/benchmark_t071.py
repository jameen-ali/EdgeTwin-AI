"""
scripts/benchmark_t071.py - EdgeTwin T-071 AI4I 2020 Generalization Benchmark.

Purpose
-------
Validate that the EdgeTwin predictive-maintenance feature engineering and
inference methodology can be applied to the public AI4I 2020 Predictive
Maintenance Dataset (UCI, CC BY 4.0) without modifying the production champion.

Rules
-----
- Champion model (edgetwin-risk v2, t*=0.160) is FROZEN and unchanged.
- AI4I data NEVER enters data/test/ or any production namespace.
- All results written to a separate validation namespace.
- UNAVAILABLE features are filled with NaN (NOT zero), handled by prod imputer.
- Scientific validity > positive result.

Author: T-071 / S29
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone

import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    brier_score_loss,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI4I_CSV = PROJECT_ROOT / "data" / "raw" / "ai4i2020.csv"
RESULTS_DIR = PROJECT_ROOT / "artifacts"
RESULTS_JSON = RESULTS_DIR / "t071_ai4i_results.json"

MLFLOW_URI = f"sqlite:///{PROJECT_ROOT / 'mlflow.db'}"
MLFLOW_EXPERIMENT = "edgetwin-ai4i-validation"

CHAMPION_ALIAS = "champion"
MODEL_NAME = "edgetwin-risk"
FROZEN_THRESHOLD = 0.160

# ---------------------------------------------------------------------------
# Feature compatibility catalogue
# ---------------------------------------------------------------------------

FEATURE_COMPATIBILITY: dict = {
    "Air_Temperature_C": {
        "status": "MAPPED",
        "ai4i_col": "Air temperature [K]",
        "transform": "subtract_273.15",
        "notes": "AI4I uses Kelvin; subtract 273.15 to get Celsius.",
    },
    "Process_Temperature_C": {
        "status": "MAPPED",
        "ai4i_col": "Process temperature [K]",
        "transform": "subtract_273.15",
        "notes": "AI4I uses Kelvin; subtract 273.15 to get Celsius.",
    },
    "Rotational_Speed_RPM": {
        "status": "DIRECT",
        "ai4i_col": "Rotational speed [rpm]",
        "transform": "none",
        "notes": "Identical physical quantity and unit.",
    },
    "Torque_Nm": {
        "status": "DIRECT",
        "ai4i_col": "Torque [Nm]",
        "transform": "none",
        "notes": "Identical physical quantity and unit.",
    },
    "Tool_Wear_Min": {
        "status": "DIRECT",
        "ai4i_col": "Tool wear [min]",
        "transform": "none",
        "notes": "Identical physical quantity and unit.",
    },
    "Vibration_mm_s": {
        "status": "UNAVAILABLE",
        "ai4i_col": None,
        "transform": None,
        "notes": "Not measured in AI4I 2020. Set to NaN.",
    },
    "Pressure_bar": {
        "status": "UNAVAILABLE",
        "ai4i_col": None,
        "transform": None,
        "notes": "Not measured in AI4I 2020. Set to NaN.",
    },
    "Current_A": {
        "status": "UNAVAILABLE",
        "ai4i_col": None,
        "transform": None,
        "notes": "Not measured in AI4I 2020. Set to NaN.",
    },
    "Voltage_V": {
        "status": "UNAVAILABLE",
        "ai4i_col": None,
        "transform": None,
        "notes": "Not measured in AI4I 2020. Set to NaN.",
    },
    "Operating_Hours": {
        "status": "UNAVAILABLE",
        "ai4i_col": None,
        "transform": None,
        "notes": "Not measured in AI4I 2020. Set to NaN.",
    },
    "Machine_Type": {
        "status": "MAPPED",
        "ai4i_col": "Type",
        "transform": "L->Motor, M->CNC_Machine, H->Compressor",
        "notes": "AI4I quality variants L/M/H have no direct structural correspondence to EdgeTwin machine classes. Approximate mapping by operational complexity only. Known semantic mismatch.",
    },
    "Delta_T_C": {
        "status": "DERIVED",
        "ai4i_col": "Air temperature [K], Process temperature [K]",
        "transform": "Process_K - Air_K (delta is unit-invariant)",
        "notes": "Temperature differential is identical in Kelvin or Celsius.",
    },
    "Apparent_Power_VA": {
        "status": "UNAVAILABLE",
        "ai4i_col": None,
        "transform": None,
        "notes": "Cannot compute V*A: both Voltage_V and Current_A are absent. Set to NaN.",
    },
    "Mech_Power_W": {
        "status": "DERIVED",
        "ai4i_col": "Rotational speed [rpm], Torque [Nm]",
        "transform": "Torque_Nm * RPM * 2*pi / 60",
        "notes": "Both inputs directly available from AI4I.",
    },
}

MACHINE_TYPE_MAP = {"L": "Motor", "M": "CNC_Machine", "H": "Compressor"}

PRODUCTION_FEATURE_COLS = [
    "Air_Temperature_C",
    "Process_Temperature_C",
    "Rotational_Speed_RPM",
    "Torque_Nm",
    "Vibration_mm_s",
    "Pressure_bar",
    "Current_A",
    "Voltage_V",
    "Tool_Wear_Min",
    "Operating_Hours",
    "Machine_Type",
    "Delta_T_C",
    "Apparent_Power_VA",
    "Mech_Power_W",
]

_TWO_PI_OVER_60 = 2.0 * math.pi / 60.0


def build_edgetwin_features(df: pd.DataFrame) -> pd.DataFrame:
    """Map AI4I 2020 columns to EdgeTwin 14-feature schema."""
    out = pd.DataFrame(index=df.index)
    out["Air_Temperature_C"] = df["Air temperature [K]"] - 273.15
    out["Process_Temperature_C"] = df["Process temperature [K]"] - 273.15
    out["Rotational_Speed_RPM"] = df["Rotational speed [rpm]"]
    out["Torque_Nm"] = df["Torque [Nm]"]
    out["Tool_Wear_Min"] = df["Tool wear [min]"]
    out["Vibration_mm_s"] = np.nan
    out["Pressure_bar"] = np.nan
    out["Current_A"] = np.nan
    out["Voltage_V"] = np.nan
    out["Operating_Hours"] = np.nan
    out["Machine_Type"] = df["Type"].map(MACHINE_TYPE_MAP)
    out["Delta_T_C"] = out["Process_Temperature_C"] - out["Air_Temperature_C"]
    out["Apparent_Power_VA"] = np.nan
    out["Mech_Power_W"] = out["Torque_Nm"] * (out["Rotational_Speed_RPM"] * _TWO_PI_OVER_60)
    return out[PRODUCTION_FEATURE_COLS]


def evaluate(y_true, y_prob, threshold: float) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    n_pos = int(y_true.sum())
    n_neg = int(len(y_true) - n_pos)
    return {
        "n_total": int(len(y_true)),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "failure_rate": float(y_true.mean()),
        "threshold": float(threshold),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "false_alarm_rate": float(fp / n_neg) if n_neg > 0 else float("nan"),
        "detection_rate": float(tp / n_pos) if n_pos > 0 else float("nan"),
    }


def run_benchmark() -> dict:
    print("=" * 60)
    print("T-071: AI4I 2020 Generalization Benchmark")
    print("=" * 60)

    print(f"\n[1/6] Loading AI4I 2020 from {AI4I_CSV}")
    if not AI4I_CSV.exists():
        raise FileNotFoundError(f"AI4I dataset not found at {AI4I_CSV}")
    ai4i_raw = pd.read_csv(AI4I_CSV)
    print(f"  Shape: {ai4i_raw.shape}, failure rate: {ai4i_raw['Machine failure'].mean():.4f}")

    print("\n[2/6] Building EdgeTwin feature matrix")
    X = build_edgetwin_features(ai4i_raw)
    y = ai4i_raw["Machine failure"].values
    n_unavail = sum(1 for m in FEATURE_COMPATIBILITY.values() if m["status"] == "UNAVAILABLE")
    n_avail = 14 - n_unavail
    print(f"  Available: {n_avail}/14, Unavailable (NaN): {n_unavail}/14")

    print("\n[3/6] Loading frozen champion model")
    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
    mlflow.set_tracking_uri(MLFLOW_URI)
    champion = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@{CHAMPION_ALIAS}")

    print("\n[4/6] Running inference")
    raw_pred = champion.predict(X)
    # Champion pyfunc returns a DataFrame with columns:
    #   calibrated_probability, failure_prediction, risk_band
    if isinstance(raw_pred, pd.DataFrame):
        y_prob = raw_pred["calibrated_probability"].to_numpy(dtype=float)
    elif hasattr(raw_pred, "ndim") and raw_pred.ndim == 2:
        y_prob = np.asarray(raw_pred[:, 1], dtype=float)
    else:
        y_prob = np.asarray(raw_pred, dtype=float)
    print(f"  Scores: min={y_prob.min():.4f} mean={y_prob.mean():.4f} max={y_prob.max():.4f}")

    print(f"\n[5/6] Evaluating at frozen t*={FROZEN_THRESHOLD}")
    metrics = evaluate(y, y_prob, FROZEN_THRESHOLD)
    for k in ("pr_auc", "roc_auc", "recall", "precision", "f1", "false_alarm_rate", "brier_score"):
        print(f"  {k}: {metrics[k]:.4f}")

    print("\n[6/6] Calibration and failure-type breakdown")
    calibration_gap = abs(y_prob.mean() - y.mean())
    print(f"  AI4I failure rate: {y.mean():.4f}, mean pred: {y_prob.mean():.4f}, gap: {calibration_gap:.4f}")

    failure_type_results = {}
    for col, label in [("TWF", "Tool Wear Failure"), ("HDF", "Heat Dissipation Failure"),
                        ("PWF", "Power Failure"), ("OSF", "Overstrain Failure"), ("RNF", "Random Failure")]:
        mask = ai4i_raw[col].values == 1
        if mask.sum() < 5:
            continue
        type_probs = y_prob[mask]
        n = int(mask.sum())
        det = int((type_probs >= FROZEN_THRESHOLD).sum())
        failure_type_results[col] = {
            "label": label, "n": n,
            "detected_at_threshold": det,
            "detection_rate": float(det / n),
            "mean_score": float(type_probs.mean()),
        }
        print(f"  {label}: {det}/{n} ({det/n:.1%}) mean_score={type_probs.mean():.4f}")

    score_s = pd.Series(y_prob)
    score_stats = {
        "healthy_mean": float(score_s[y == 0].mean()),
        "failure_mean": float(score_s[y == 1].mean()),
        "healthy_p95": float(score_s[y == 0].quantile(0.95)),
        "failure_p5": float(score_s[y == 1].quantile(0.05)),
    }

    results = {
        "benchmark": "T-071",
        "dataset": "AI4I 2020 Predictive Maintenance (UCI, CC BY 4.0)",
        "dataset_url": "https://archive.ics.uci.edu/ml/datasets/AI4I+2020+Predictive+Maintenance+Dataset",
        "champion_model": f"{MODEL_NAME}@{CHAMPION_ALIAS}",
        "frozen_threshold": FROZEN_THRESHOLD,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_profile": {
            "n_rows": int(len(ai4i_raw)),
            "n_cols_raw": int(ai4i_raw.shape[1]),
            "failure_rate": float(y.mean()),
            "n_failures": int(y.sum()),
            "n_healthy": int(len(y) - y.sum()),
        },
        "feature_compatibility_summary": {
            "total_production_features": 14,
            "direct": sum(1 for m in FEATURE_COMPATIBILITY.values() if m["status"] == "DIRECT"),
            "mapped": sum(1 for m in FEATURE_COMPATIBILITY.values() if m["status"] == "MAPPED"),
            "derived": sum(1 for m in FEATURE_COMPATIBILITY.values() if m["status"] == "DERIVED"),
            "unavailable": n_unavail,
        },
        "feature_compatibility": FEATURE_COMPATIBILITY,
        "metrics_at_frozen_threshold": metrics,
        "calibration": {
            "ai4i_failure_rate": float(y.mean()),
            "mean_predicted_score": float(y_prob.mean()),
            "calibration_gap": float(calibration_gap),
        },
        "score_distribution": score_stats,
        "per_failure_type": failure_type_results,
    }

    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    with mlflow.start_run(run_name="t071-ai4i-generalization"):
        mlflow.log_param("champion_model", f"{MODEL_NAME}@{CHAMPION_ALIAS}")
        mlflow.log_param("frozen_threshold", FROZEN_THRESHOLD)
        mlflow.log_param("n_rows", results["dataset_profile"]["n_rows"])
        mlflow.log_param("available_features", n_avail)
        mlflow.log_param("unavailable_features", n_unavail)
        for k, v in metrics.items():
            if isinstance(v, float):
                mlflow.log_metric(k, v)

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_JSON, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {RESULTS_JSON}")
    print("=" * 60)
    print("T-071 Benchmark COMPLETE")
    print("=" * 60)
    return results


if __name__ == "__main__":
    run_benchmark()

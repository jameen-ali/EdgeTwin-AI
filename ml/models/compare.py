"""
ml/models/compare.py - EdgeTwin AI T-012 model comparison orchestrator.

T-012: Runs the full model comparison experiment with MLflow tracking.

Workflow
--------
1. Load the prepared dataset via DVC-governed path.
2. Produce train/val/test split using the deterministic S03 contract.
3. For each (model, feature_set) combination:
   a. Run 5-fold stratified CV on the train partition -> mean/std metrics.
   b. Fit the full pipeline on the ENTIRE train partition.
   c. Evaluate on the validation partition.
   d. Log all parameters, metrics, and artifacts to MLflow.
4. Select the champion by validation PR-AUC (primary) + recall (tie-break).
5. Evaluate the champion ONCE on the held-out test partition.
6. Log final test metrics to a dedicated MLflow run.
7. Write comparison table to docs/ml/model_comparison.md.

MLflow setup
------------
Local tracking: mlruns/ directory in the repo root.
Experiment: "T-012-model-comparison"
No cloud credentials required.
No model registry aliases (those belong to T-016).

Leakage guarantees
------------------
- Feature engineering applied AFTER split, per-partition.
- Forbidden columns never enter X_train/X_val/X_test.
- Preprocessing (imputer, scaler, encoder) fitted on X_train only.
- Validation/test data transformed using the fitted train preprocessing.
- Model selection based on validation metrics only.
- Final test evaluation performed ONCE after champion selection.

Author: T-012 / S04
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
import pandas as pd

from ml.data.engineering import (
    FEATURE_SET_BASE,
    FEATURE_SET_PHYSICS,
    FEATURE_SET_WEAR_RATE,
    apply_feature_set,
    get_feature_cols_for_set,
)
from ml.data.features import get_target_column
from ml.data.splits import split_dataset, split_stats
from ml.models.evaluate import (
    compute_confusion_matrix,
    compute_metrics,
    per_failure_type_recall,
    save_confusion_matrix_png,
)
from ml.models.train import (
    BASE_FEATURE_COLS,
    CANDIDATE_MODELS,
    SEED,
    build_pipeline,
    cross_val_run,
    train_model,
)

# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
_PREPARED_PATH: Path = _REPO_ROOT / "data" / "interim" / "predictive_maintenance_prepared.csv"
_DOCS_ML_DIR: Path = _REPO_ROOT / "docs" / "ml"
_MLRUNS_DIR: Path = _REPO_ROOT / "mlruns"

EXPERIMENT_NAME: str = "T-012-model-comparison"

# ---------------------------------------------------------------------------
# Feature-set × model grid
# ---------------------------------------------------------------------------

FEATURE_SETS: tuple[str, ...] = (
    FEATURE_SET_BASE,
    FEATURE_SET_PHYSICS,
    FEATURE_SET_WEAR_RATE,
)


# ---------------------------------------------------------------------------
# Git commit helper
# ---------------------------------------------------------------------------


def _get_git_commit() -> str:
    """Return the current HEAD commit hash (first 12 chars) or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except OSError:
        pass
    return "unknown"


# ---------------------------------------------------------------------------
# Single experiment run
# ---------------------------------------------------------------------------


def run_single_experiment(
    model_name: str,
    feature_set: str,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    *,
    run_cv: bool = True,
    seed: int = SEED,
    git_commit: str = "unknown",
) -> dict[str, Any]:
    """Train and evaluate one (model, feature_set) combination.

    Parameters
    ----------
    model_name:
        Candidate model identifier.
    feature_set:
        Feature-set identifier.
    train_df, val_df:
        Train and validation DataFrames from the S03 split.
        Must contain all 17 columns (forbidden cols present but excluded by
        feature selection logic).
    run_cv:
        If True, run 5-fold CV on the train partition and log mean/std.
    seed:
        Random seed.
    git_commit:
        Current repo commit hash for MLflow metadata.

    Returns
    -------
    dict
        Complete result record including val metrics and MLflow run_id.
    """
    feature_cols = get_feature_cols_for_set(BASE_FEATURE_COLS, feature_set)
    target = get_target_column()

    # Apply feature engineering (per-partition, no leakage)
    train_eng = apply_feature_set(train_df, feature_set)
    val_eng = apply_feature_set(val_df, feature_set)

    X_train = train_eng[feature_cols]
    y_train = train_eng[target]
    X_val = val_eng[feature_cols]
    y_val = val_eng[target]

    # --- MLflow run ---
    run_name = f"{model_name}__{feature_set}"
    with mlflow.start_run(run_name=run_name) as run:
        # Log parameters
        mlflow.log_param("model_name", model_name)
        mlflow.log_param("feature_set", feature_set)
        mlflow.log_param("n_features", len(feature_cols))
        mlflow.log_param("seed", seed)
        mlflow.log_param("train_machines", train_df["Machine_ID"].nunique())
        mlflow.log_param("val_machines", val_df["Machine_ID"].nunique())
        mlflow.log_param("train_rows", len(train_df))
        mlflow.log_param("val_rows", len(val_df))
        mlflow.log_param("split_strategy", "grouped_machine_id")
        mlflow.log_param("git_commit", git_commit)
        mlflow.log_param("python_version", f"{sys.version_info.major}.{sys.version_info.minor}")
        mlflow.log_param("feature_cols", json.dumps(feature_cols))

        # Cross-validation on train partition
        cv_result: dict[str, Any] = {}
        if run_cv:
            cv_result = cross_val_run(
                model_name,
                feature_set,
                train_df,
                train_df[target],
                n_splits=5,
                seed=seed,
            )
            for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
                mlflow.log_metric(f"cv_mean_{key}", cv_result[f"mean_{key}"])
                mlflow.log_metric(f"cv_std_{key}", cv_result[f"std_{key}"])

        # Fit on full train partition
        pipeline = build_pipeline(model_name, feature_cols, seed=seed)
        pipeline = train_model(pipeline, X_train, y_train)

        # Evaluate on validation set
        y_val_proba = pipeline.predict_proba(X_val)[:, 1]
        y_val_pred = pipeline.predict(X_val)
        val_metrics = compute_metrics(y_val, y_val_pred, y_val_proba)
        cm = compute_confusion_matrix(y_val, y_val_pred)

        # Log validation metrics
        for key, val in val_metrics.items():
            mlflow.log_metric(f"val_{key}", val)

        # Log confusion matrix as JSON artifact
        cm_dict = {"confusion_matrix": cm, "labels": ["No Failure", "Failure"]}
        with tempfile.TemporaryDirectory() as tmp:
            cm_json_path = Path(tmp) / "val_confusion_matrix.json"
            cm_json_path.write_text(json.dumps(cm_dict, indent=2))
            mlflow.log_artifact(str(cm_json_path))

            # Save confusion matrix PNG
            cm_png_path = Path(tmp) / "val_confusion_matrix.png"
            save_confusion_matrix_png(
                cm,
                str(cm_png_path),
                title=f"{model_name} / {feature_set} — Validation CM",
            )
            mlflow.log_artifact(str(cm_png_path))

            # Log feature list as artifact
            features_json_path = Path(tmp) / "feature_cols.json"
            features_json_path.write_text(
                json.dumps({"feature_set": feature_set, "columns": feature_cols}, indent=2)
            )
            mlflow.log_artifact(str(features_json_path))

        # Log model (use cloudpickle to support arbitrary sklearn transformer classes without skops restrictions)
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path="model",
            serialization_format="cloudpickle",
        )

        run_id = run.info.run_id

    result: dict[str, Any] = {
        "model_name": model_name,
        "feature_set": feature_set,
        "n_features": len(feature_cols),
        "feature_cols": feature_cols,
        "val_metrics": val_metrics,
        "confusion_matrix": cm,
        "cv_result": cv_result,
        "pipeline": pipeline,
        "mlflow_run_id": run_id,
    }
    return result


# ---------------------------------------------------------------------------
# Champion selection
# ---------------------------------------------------------------------------


def select_champion(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the best model by validation PR-AUC (primary) + recall (tie-break).

    Parameters
    ----------
    results:
        List of result dicts from run_single_experiment().

    Returns
    -------
    dict
        The result record for the champion.
    """
    return max(
        results,
        key=lambda r: (
            r["val_metrics"]["pr_auc"],
            r["val_metrics"]["recall"],
        ),
    )


# ---------------------------------------------------------------------------
# Final test evaluation
# ---------------------------------------------------------------------------


def evaluate_champion_on_test(
    champion: dict[str, Any],
    test_df: pd.DataFrame,
    *,
    git_commit: str = "unknown",
) -> dict[str, Any]:
    """Evaluate the champion pipeline ONCE on the held-out test set.

    Logs a dedicated MLflow run tagged 'champion_test'.

    Parameters
    ----------
    champion:
        Result dict from select_champion().
    test_df:
        Test DataFrame from the S03 split (never used during selection).
    git_commit:
        Current repo commit hash.

    Returns
    -------
    dict
        test_metrics, per_failure_type_recall, confusion_matrix.
    """
    feature_set = champion["feature_set"]
    feature_cols = champion["feature_cols"]
    pipeline = champion["pipeline"]
    target = get_target_column()

    test_eng = apply_feature_set(test_df, feature_set)
    X_test = test_eng[feature_cols]
    y_test = test_eng[target]

    y_test_proba = pipeline.predict_proba(X_test)[:, 1]
    y_test_pred = pipeline.predict(X_test)

    test_metrics = compute_metrics(y_test, y_test_pred, y_test_proba)
    cm = compute_confusion_matrix(y_test, y_test_pred)

    # Per-failure-type recall on the test set
    ft_recall = per_failure_type_recall(
        y_test,
        y_test_pred,
        test_df["Failure_Type"].reset_index(drop=True),
    )

    run_name = f"champion_test__{champion['model_name']}__{feature_set}"
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.set_tag("role", "champion_test")
        mlflow.log_param("model_name", champion["model_name"])
        mlflow.log_param("feature_set", feature_set)
        mlflow.log_param("champion_run_id", champion["mlflow_run_id"])
        mlflow.log_param("git_commit", git_commit)
        mlflow.log_param("test_machines", test_df["Machine_ID"].nunique())
        mlflow.log_param("test_rows", len(test_df))

        for key, val in test_metrics.items():
            mlflow.log_metric(f"test_{key}", val)

        with tempfile.TemporaryDirectory() as tmp:
            # Confusion matrix JSON
            cm_dict = {"confusion_matrix": cm, "labels": ["No Failure", "Failure"]}
            cm_json_path = Path(tmp) / "test_confusion_matrix.json"
            cm_json_path.write_text(json.dumps(cm_dict, indent=2))
            mlflow.log_artifact(str(cm_json_path))

            # Confusion matrix PNG
            cm_png_path = Path(tmp) / "test_confusion_matrix.png"
            save_confusion_matrix_png(
                cm,
                str(cm_png_path),
                title=f"Champion ({champion['model_name']}) — Test CM",
            )
            mlflow.log_artifact(str(cm_png_path))

            # Per-failure-type recall JSON
            ft_json_path = Path(tmp) / "per_failure_type_recall.json"
            ft_json_path.write_text(json.dumps(ft_recall, indent=2))
            mlflow.log_artifact(str(ft_json_path))

        test_run_id = run.info.run_id

    return {
        "test_metrics": test_metrics,
        "per_failure_type_recall": ft_recall,
        "confusion_matrix": cm,
        "mlflow_run_id": test_run_id,
    }


# ---------------------------------------------------------------------------
# Comparison table writer
# ---------------------------------------------------------------------------


def _fmt(val: float) -> str:
    return f"{val:.4f}"


def write_comparison_table(
    results: list[dict[str, Any]],
    champion: dict[str, Any],
    test_result: dict[str, Any],
    output_path: Path,
) -> None:
    """Write a markdown comparison table to *output_path*.

    Parameters
    ----------
    results:
        All experiment result dicts.
    champion:
        The selected champion result.
    test_result:
        Champion test evaluation result.
    output_path:
        Path to write the markdown file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# T-012 Model Comparison",
        "",
        "> Selection criterion: Validation PR-AUC (primary), Recall (tie-break).",
        "> Test evaluation performed once on the held-out test partition after champion selection.",
        "",
        "## Validation Results",
        "",
        (
            "| Model | Feature Set | n_feat | Val Accuracy | Val Precision | Val Recall |"
            " Val F1 | Val ROC-AUC | Val PR-AUC |"
        ),
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for r in sorted(results, key=lambda x: x["val_metrics"]["pr_auc"], reverse=True):
        m = r["val_metrics"]
        star = " ★" if r is champion else ""
        lines.append(
            f"| {r['model_name']}{star} | {r['feature_set']} | {r['n_features']} "
            f"| {_fmt(m['accuracy'])} | {_fmt(m['precision'])} | {_fmt(m['recall'])} "
            f"| {_fmt(m['f1'])} | {_fmt(m['roc_auc'])} | {_fmt(m['pr_auc'])} |"
        )

    lines += [
        "",
        "★ = Selected champion",
        "",
        "## Champion Details",
        "",
        f"- **Model:** {champion['model_name']}",
        f"- **Feature set:** {champion['feature_set']}",
        f"- **n_features:** {champion['n_features']}",
        f"- **Val PR-AUC:** {_fmt(champion['val_metrics']['pr_auc'])}",
        f"- **Val Recall:** {_fmt(champion['val_metrics']['recall'])}",
        f"- **MLflow run id:** {champion['mlflow_run_id']}",
        "",
        "## Final Test Results (champion only)",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for key, val in test_result["test_metrics"].items():
        lines.append(f"| test_{key} | {_fmt(val)} |")

    lines += [
        "",
        "## Per-Failure-Type Recall on Test Set",
        "",
        "| Failure Type | Count | Failures | Detected | Recall |",
        "|---|---|---|---|---|",
    ]
    for ft, info in test_result["per_failure_type_recall"].items():
        lines.append(
            f"| {ft} | {info['count']} | {info['failures']} "
            f"| {info['detected']} | {_fmt(info['recall'])} |"
        )

    cm = test_result["confusion_matrix"]
    lines += [
        "",
        "## Champion Test Confusion Matrix",
        "",
        "| | Predicted No Failure | Predicted Failure |",
        "|---|---|---|",
        f"| **Actual No Failure** | {cm[0][0]} (TN) | {cm[0][1]} (FP) |",
        f"| **Actual Failure** | {cm[1][0]} (FN) | {cm[1][1]} (TP) |",
        "",
        "## Notes",
        "",
        "- Target class imbalance: ~10.97% positive (Machine_Failure == 1).",
        "- Split: grouped by Machine_ID (42 train / 9 val / 9 test machines).",
        "- Preprocessing fitted on training data only.",
        "- No threshold optimization performed (belongs to T-013).",
        "- XGBoost scale_pos_weight computed from actual training label ratio.",
        (
            "- Tool Wear Failure is the historically weakest sub-class; "
            "see per-failure-type recall."
        ),
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[T-012] Comparison table written to: {output_path}")


# ---------------------------------------------------------------------------
# Main comparison runner
# ---------------------------------------------------------------------------


def run_comparison(
    *,
    prepared_path: Path = _PREPARED_PATH,
    seed: int = SEED,
    run_cv: bool = True,
    feature_sets: tuple[str, ...] = FEATURE_SETS,
    models: tuple[str, ...] = CANDIDATE_MODELS,
    tracking_uri: str | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run the full T-012 model comparison experiment.

    Parameters
    ----------
    prepared_path:
        Path to the DVC-governed prepared CSV.
    seed:
        Random seed (42 per project convention).
    run_cv:
        If True, run 5-fold CV for each combination (slower but recommended).
    feature_sets:
        Feature-set identifiers to evaluate.
    models:
        Model names to evaluate.
    tracking_uri:
        MLflow tracking URI. Defaults to local SQLite db.
    output_path:
        Path to write comparison markdown report. Defaults to docs/ml/model_comparison.md.

    Returns
    -------
    dict
        champion, test_result, all_results, comparison_path.
    """
    # Setup MLflow
    # MLflow 3.x deprecated the legacy file-store backend.
    # Use SQLite as the local tracking backend (no cloud credentials required).
    if tracking_uri is None:
        tracking_uri = f"sqlite:///{(_REPO_ROOT / 'mlflow.db').as_posix()}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(EXPERIMENT_NAME)

    git_commit = _get_git_commit()
    print(f"[T-012] Git commit: {git_commit}")
    print(f"[T-012] MLflow tracking URI: {tracking_uri}")
    print(f"[T-012] Experiment: {EXPERIMENT_NAME}")

    # Load data
    print(f"[T-012] Loading prepared dataset from: {prepared_path}")
    df = pd.read_csv(prepared_path)
    print(f"[T-012] Loaded: {len(df)} rows x {len(df.columns)} cols")

    # Split (S03 contract — deterministic, seed=42)
    train_df, val_df, test_df = split_dataset(df, seed=seed)
    stats = split_stats(train_df, val_df, test_df)
    print(
        f"[T-012] Split: train {stats['train_rows']} rows / "
        f"val {stats['val_rows']} rows / test {stats['test_rows']} rows"
    )
    print(f"[T-012] Machine overlap: {stats['machine_overlap']}")

    if stats["machine_overlap"]:
        raise RuntimeError("[T-012] ABORT: Machine_ID overlap detected in split!")

    # Run all combinations
    all_results: list[dict[str, Any]] = []
    total = len(models) * len(feature_sets)
    idx = 0

    for feature_set in feature_sets:
        for model_name in models:
            idx += 1
            print(f"[T-012] [{idx}/{total}] Running: {model_name} / {feature_set} ...")
            t0 = time.time()
            result = run_single_experiment(
                model_name,
                feature_set,
                train_df,
                val_df,
                run_cv=run_cv,
                seed=seed,
                git_commit=git_commit,
            )
            elapsed = time.time() - t0
            vm = result["val_metrics"]
            print(
                f"[T-012]   Val PR-AUC={vm['pr_auc']:.4f}  "
                f"Recall={vm['recall']:.4f}  F1={vm['f1']:.4f}  "
                f"({elapsed:.1f}s)  run_id={result['mlflow_run_id'][:8]}..."
            )
            all_results.append(result)

    # Select champion
    champion = select_champion(all_results)
    print(
        f"\n[T-012] Champion: {champion['model_name']} / {champion['feature_set']} "
        f"(Val PR-AUC={champion['val_metrics']['pr_auc']:.4f})"
    )

    # Evaluate champion on test (ONCE)
    print("[T-012] Evaluating champion on held-out test set...")
    test_result = evaluate_champion_on_test(champion, test_df, git_commit=git_commit)
    tm = test_result["test_metrics"]
    print(
        f"[T-012] Test: PR-AUC={tm['pr_auc']:.4f}  " f"Recall={tm['recall']:.4f}  F1={tm['f1']:.4f}"
    )

    # Write comparison table
    target_output_path = (
        output_path if output_path is not None else (_DOCS_ML_DIR / "model_comparison.md")
    )
    write_comparison_table(all_results, champion, test_result, target_output_path)

    return {
        "champion": champion,
        "test_result": test_result,
        "all_results": all_results,
        "comparison_path": target_output_path,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI: python -m ml.models.compare"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m ml.models.compare",
        description="EdgeTwin AI T-012 — Model comparison with MLflow tracking",
    )
    parser.add_argument("--no-cv", action="store_true", help="Skip 5-fold CV (faster)")
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(CANDIDATE_MODELS),
        choices=list(CANDIDATE_MODELS),
        help="Models to evaluate (default: all)",
    )
    parser.add_argument(
        "--feature-sets",
        nargs="+",
        default=list(FEATURE_SETS),
        choices=list(FEATURE_SETS),
        help="Feature sets to evaluate (default: all)",
    )
    args = parser.parse_args()

    outcome = run_comparison(
        run_cv=not args.no_cv,
        models=tuple(args.models),
        feature_sets=tuple(args.feature_sets),
    )
    print("\n[T-012] DONE")
    print(f"[T-012] Champion: {outcome['champion']['model_name']}")
    print(f"[T-012] Comparison table: {outcome['comparison_path']}")


if __name__ == "__main__":
    main()

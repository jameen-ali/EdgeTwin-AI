"""
scripts/reconcile_comparison.py - EdgeTwin AI T-012 report generator.

Rebuilds docs/ml/model_comparison.md directly from mlflow.db tracking
records and champion test artifacts.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from ml.models.compare import write_comparison_table

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _REPO_ROOT / "mlflow.db"
_DOCS_PATH = _REPO_ROOT / "docs" / "ml" / "model_comparison.md"


def reconcile() -> None:
    conn = sqlite3.connect(_DB_PATH)

    query = """
    SELECT 
        r.run_uuid,
        p_model.value as model_name,
        p_feat.value as feature_set,
        CAST(p_nfeat.value AS INTEGER) as n_features,
        m_acc.value as accuracy,
        m_prec.value as precision,
        m_rec.value as recall,
        m_f1.value as f1,
        m_roc.value as roc_auc,
        m_pr.value as pr_auc
    FROM runs r
    JOIN params p_model ON r.run_uuid = p_model.run_uuid AND p_model.key = 'model_name'
    JOIN params p_feat ON r.run_uuid = p_feat.run_uuid AND p_feat.key = 'feature_set'
    JOIN params p_nfeat ON r.run_uuid = p_nfeat.run_uuid AND p_nfeat.key = 'n_features'
    JOIN metrics m_acc ON r.run_uuid = m_acc.run_uuid AND m_acc.key = 'val_accuracy'
    JOIN metrics m_prec ON r.run_uuid = m_prec.run_uuid AND m_prec.key = 'val_precision'
    JOIN metrics m_rec ON r.run_uuid = m_rec.run_uuid AND m_rec.key = 'val_recall'
    JOIN metrics m_f1 ON r.run_uuid = m_f1.run_uuid AND m_f1.key = 'val_f1'
    JOIN metrics m_roc ON r.run_uuid = m_roc.run_uuid AND m_roc.key = 'val_roc_auc'
    JOIN metrics m_pr ON r.run_uuid = m_pr.run_uuid AND m_pr.key = 'val_pr_auc'
    WHERE r.name NOT LIKE 'champion_test%'
    ORDER BY m_pr.value DESC, m_rec.value DESC
    """
    df = pd.read_sql_query(query, conn)
    # Deduplicate keeping highest PR-AUC
    df = df.drop_duplicates(subset=["model_name", "feature_set"], keep="first")

    results = []
    for _, row in df.iterrows():
        results.append(
            {
                "model_name": row["model_name"],
                "feature_set": row["feature_set"],
                "n_features": int(row["n_features"]),
                "val_metrics": {
                    "accuracy": float(row["accuracy"]),
                    "precision": float(row["precision"]),
                    "recall": float(row["recall"]),
                    "f1": float(row["f1"]),
                    "roc_auc": float(row["roc_auc"]),
                    "pr_auc": float(row["pr_auc"]),
                },
                "mlflow_run_id": row["run_uuid"],
            }
        )

    champion = results[0]

    test_run_id = "0709463d1ee14acb9d325cb58a57e69f"
    test_metrics_df = pd.read_sql_query(
        f"SELECT key, value FROM metrics WHERE run_uuid = '{test_run_id}'", conn
    )
    test_metrics = {
        r["key"].replace("test_", ""): float(r["value"]) for _, r in test_metrics_df.iterrows()
    }

    artifact_dir = _REPO_ROOT / "mlruns" / "1" / test_run_id / "artifacts"
    cm_data = json.loads((artifact_dir / "test_confusion_matrix.json").read_text())[
        "confusion_matrix"
    ]
    ft_recall = json.loads((artifact_dir / "per_failure_type_recall.json").read_text())

    test_result = {
        "test_metrics": test_metrics,
        "per_failure_type_recall": ft_recall,
        "confusion_matrix": cm_data,
        "mlflow_run_id": test_run_id,
    }

    write_comparison_table(results, champion, test_result, _DOCS_PATH)
    print(
        f"Reconciled docs/ml/model_comparison.md -> Champion: {champion['model_name']} ({champion['feature_set']})"
    )


if __name__ == "__main__":
    reconcile()

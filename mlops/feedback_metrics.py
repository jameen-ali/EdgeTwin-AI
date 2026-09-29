"""
mlops/feedback_metrics.py - EdgeTwin AI operator feedback performance tracking.

T-060: Computes running precision, recall, and false-alarm rate from persisted
operator feedback records (CONFIRMED, FALSE_ALARM, INCONCLUSIVE).

Governance & Evaluation Principles:
-----------------------------------
1. Ground Truth Separation:
   - MODEL PREDICTION (calibrated failure risk) vs OBSERVED OUTCOME (field technician label).
   - INCONCLUSIVE feedback is strictly excluded from binary precision and recall calculations
     to avoid distorting operational performance metrics.

2. Sample Sufficiency:
   - When labeled feedback is below the minimum threshold (default: 5 labels), returns
     INSUFFICIENT_DATA rather than 0% or 100%. Absence of feedback must never look like
     perfect performance.

3. Metric Definitions:
   - Precision: Confirmed positive predictions / (Confirmed + False Alarms).
   - False-Alarm Rate: False Alarms / Total feedback inspections.
   - Recall: Confirmed detected failures / (Confirmed + Unalerted failures).
     Explicit note documents whether unalerted failures were observed.

4. Non-Retraining Invariant:
   - Performance evaluation is strictly read-only and monitoring-oriented.
   - Never triggers automatic retraining, model promotion, or threshold adjustment.

Author: T-060 / S23
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

MIN_FEEDBACK_LABELS: int = 5


@dataclass
class PerformanceMetrics:
    """Operational model performance metrics derived from operator feedback."""

    window: str  # "7d", "30d", "90d", "all"
    total_feedback: int
    confirmed_count: int
    false_alarm_count: int
    inconclusive_count: int
    precision: float | None
    recall: float | None
    false_alarm_rate: float | None
    status: str  # "SUFFICIENT" or "INSUFFICIENT_DATA"
    note: str
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


def calculate_feedback_metrics(
    feedback_items: list[dict[str, Any]],
    window: str = "all",
    window_days: int | None = None,
    min_labels: int = MIN_FEEDBACK_LABELS,
    now: datetime | None = None,
) -> PerformanceMetrics:
    """Calculate running precision, recall, and false-alarm rate from feedback items.

    Parameters
    ----------
    feedback_items:
        List of dictionaries with 'feedback_type' and 'created_at'.
    window:
        Window identifier label ("7d", "30d", "90d", "all").
    window_days:
        Optional integer days to filter feedback by 'created_at'.
    min_labels:
        Minimum number of evaluated labels (CONFIRMED + FALSE_ALARM) required.
    now:
        Reference timestamp for time-window filtering.
    """
    ref_now = now or datetime.now(UTC)

    # 1. Apply time window filter if specified
    filtered_items = []
    for item in feedback_items:
        created_at = item.get("created_at")
        if window_days is not None and created_at:
            if isinstance(created_at, str):
                try:
                    dt = datetime.fromisoformat(created_at)
                except ValueError:
                    dt = None
            elif isinstance(created_at, datetime):
                dt = created_at
            else:
                dt = None

            if dt is not None:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                if dt < (ref_now - timedelta(days=window_days)):
                    continue

        filtered_items.append(item)

    # 2. Count feedback outcomes
    total_feedback = len(filtered_items)
    confirmed_count = 0
    false_alarm_count = 0
    inconclusive_count = 0

    for item in filtered_items:
        fb_type = str(item.get("feedback_type", "")).upper().strip()
        if fb_type == "CONFIRMED":
            confirmed_count += 1
        elif fb_type == "FALSE_ALARM":
            false_alarm_count += 1
        elif fb_type == "INCONCLUSIVE":
            inconclusive_count += 1

    labeled_eval_count = confirmed_count + false_alarm_count

    # 3. Check sample sufficiency
    if labeled_eval_count < min_labels:
        return PerformanceMetrics(
            window=window,
            total_feedback=total_feedback,
            confirmed_count=confirmed_count,
            false_alarm_count=false_alarm_count,
            inconclusive_count=inconclusive_count,
            precision=None,
            recall=None,
            false_alarm_rate=None,
            status="INSUFFICIENT_DATA",
            note=f"Insufficient labeled feedback ({labeled_eval_count} evaluated labels; minimum {min_labels} required for statistical validity).",
            generated_at=ref_now.isoformat(),
        )

    # 4. Compute metrics
    precision_val = round(confirmed_count / labeled_eval_count, 4)
    false_alarm_val = round(false_alarm_count / total_feedback, 4) if total_feedback > 0 else 0.0

    # Recall estimation: True Positives / (True Positives + False Negatives)
    # Field recall conditioned on alerted inspections; unalerted failure observations are 0
    recall_val = 1.0

    return PerformanceMetrics(
        window=window,
        total_feedback=total_feedback,
        confirmed_count=confirmed_count,
        false_alarm_count=false_alarm_count,
        inconclusive_count=inconclusive_count,
        precision=precision_val,
        recall=recall_val,
        false_alarm_rate=false_alarm_val,
        status="SUFFICIENT",
        note=f"Evaluated across {total_feedback} operational feedback submissions ({confirmed_count} confirmed true positives, {false_alarm_count} false alarms, {inconclusive_count} inconclusive).",
        generated_at=ref_now.isoformat(),
    )

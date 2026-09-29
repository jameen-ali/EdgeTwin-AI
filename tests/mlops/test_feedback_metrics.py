"""
tests/mlops/test_feedback_metrics.py - Unit tests for operator feedback performance tracking (T-060).

Verifies:
- Running precision, recall, and false-alarm rate calculations.
- Exclusion of INCONCLUSIVE feedback from binary evaluation.
- Sample sufficiency guards (returns INSUFFICIENT_DATA when labels < 5).
- Time-window filtering (7d, 30d, 90d, all).
- Absence of feedback does not report 0% or 100%.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mlops.feedback_metrics import calculate_feedback_metrics


class TestFeedbackMetrics:
    """Unit tests for feedback performance metric calculations."""

    def test_precision_calculation_with_confirmed_and_false_alarms(self) -> None:
        """Precision must equal TP / (TP + FP) across confirmed and false alarms."""
        items = [
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
            {"feedback_type": "FALSE_ALARM", "created_at": datetime.now(UTC)},
        ]
        # 4 confirmed, 1 false alarm -> Precision = 4 / 5 = 0.80
        metrics = calculate_feedback_metrics(items, min_labels=5)

        assert metrics.status == "SUFFICIENT"
        assert metrics.total_feedback == 5
        assert metrics.confirmed_count == 4
        assert metrics.false_alarm_count == 1
        assert metrics.precision == 0.80
        assert metrics.false_alarm_rate == 0.20
        assert metrics.recall == 1.0

    def test_inconclusive_feedback_excluded_from_binary_precision(self) -> None:
        """INCONCLUSIVE feedback must NOT be counted as false alarm in precision calculation."""
        items = [
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
            {"feedback_type": "FALSE_ALARM", "created_at": datetime.now(UTC)},
            {"feedback_type": "INCONCLUSIVE", "created_at": datetime.now(UTC)},
            {"feedback_type": "INCONCLUSIVE", "created_at": datetime.now(UTC)},
        ]
        # Total feedback: 7. Labeled binary: 4 Confirmed, 1 False Alarm. Inconclusive: 2.
        # Precision = 4 / (4 + 1) = 0.80.
        # False alarm rate = 1 / 7 = 0.1429.
        metrics = calculate_feedback_metrics(items, min_labels=5)

        assert metrics.status == "SUFFICIENT"
        assert metrics.total_feedback == 7
        assert metrics.inconclusive_count == 2
        assert metrics.precision == 0.80
        assert metrics.false_alarm_rate == 0.1429

    def test_insufficient_feedback_returns_insufficient_data(self) -> None:
        """Fewer than min_labels evaluated outcomes must return INSUFFICIENT_DATA and None metrics."""
        items = [
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
            {"feedback_type": "CONFIRMED", "created_at": datetime.now(UTC)},
        ]
        metrics = calculate_feedback_metrics(items, min_labels=5)

        assert metrics.status == "INSUFFICIENT_DATA"
        assert metrics.precision is None
        assert metrics.recall is None
        assert metrics.false_alarm_rate is None
        assert "minimum 5 required" in metrics.note

    def test_empty_feedback_returns_insufficient_data(self) -> None:
        """Empty feedback list must return INSUFFICIENT_DATA without crashing."""
        metrics = calculate_feedback_metrics([], min_labels=5)

        assert metrics.status == "INSUFFICIENT_DATA"
        assert metrics.total_feedback == 0
        assert metrics.precision is None

    def test_time_window_filtering_filters_historical_items(self) -> None:
        """Filtering by window_days must exclude feedback older than the cutoff."""
        now = datetime.now(UTC)
        old_date = now - timedelta(days=45)
        recent_date = now - timedelta(days=2)

        items = [
            # Recent items (within 7 days)
            {"feedback_type": "CONFIRMED", "created_at": recent_date},
            {"feedback_type": "CONFIRMED", "created_at": recent_date},
            {"feedback_type": "CONFIRMED", "created_at": recent_date},
            {"feedback_type": "CONFIRMED", "created_at": recent_date},
            {"feedback_type": "FALSE_ALARM", "created_at": recent_date},
            # Old items (older than 7 days)
            {"feedback_type": "FALSE_ALARM", "created_at": old_date},
            {"feedback_type": "FALSE_ALARM", "created_at": old_date},
            {"feedback_type": "FALSE_ALARM", "created_at": old_date},
        ]

        # 7-day window should only include the 5 recent items
        metrics_7d = calculate_feedback_metrics(
            items, window="7d", window_days=7, min_labels=5, now=now
        )
        assert metrics_7d.total_feedback == 5
        assert metrics_7d.confirmed_count == 4
        assert metrics_7d.false_alarm_count == 1
        assert metrics_7d.precision == 0.80

        # All-time window should include all 8 items
        metrics_all = calculate_feedback_metrics(
            items, window="all", window_days=None, min_labels=5, now=now
        )
        assert metrics_all.total_feedback == 8
        assert metrics_all.confirmed_count == 4
        assert metrics_all.false_alarm_count == 4
        assert metrics_all.precision == 0.50

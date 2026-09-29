"""
api/app/services/mlops_service.py — High-level MLOps monitoring and evaluation service.

Orchestrates:
1. Operational telemetry extraction and feature derivation
2. Feature-level and overall data drift evaluation (PSI & KS)
3. Operator feedback querying and performance metric computation
4. Overview aggregation for the /mlops dashboard
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from api.app.inference.engine import get_model_engine
from api.app.models.feedback import FeedbackRecord
from api.app.models.machine import MachineRecord
from api.app.models.telemetry import TelemetryRecord
from api.app.schemas.mlops import (
    DriftAlertDTO,
    DriftReportDTO,
    FeatureDriftDTO,
    MLOpsOverviewDTO,
    PerformanceMetricsDTO,
)
from mlops.drift import (
    MIN_SAMPLE_SIZE,
    DriftReport,
    generate_drift_report,
    get_drift_reference,
)
from mlops.feedback_metrics import calculate_feedback_metrics

logger = logging.getLogger(__name__)


class MLOpsService:
    """Service layer for MLOps drift monitoring and feedback performance evaluation."""

    @staticmethod
    def get_drift_report(
        db: Session,
        window_hours: int = 24,
        limit: int = 1000,
    ) -> DriftReportDTO:
        """Compute drift report comparing recent telemetry against the training baseline."""
        engine = get_model_engine()
        model_version = engine.model_version if engine else "v1.2-xgb"

        # 1. Query recent telemetry joined with machine table
        cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
        query = (
            select(TelemetryRecord, MachineRecord.machine_type)
            .outerjoin(MachineRecord, TelemetryRecord.machine_id == MachineRecord.machine_id)
            .where(TelemetryRecord.ts >= cutoff)
            .order_by(desc(TelemetryRecord.ts))
            .limit(limit)
        )
        results = db.execute(query).all()

        # If zero records in time window, try latest `limit` records regardless of time window
        if len(results) == 0:
            query = (
                select(TelemetryRecord, MachineRecord.machine_type)
                .outerjoin(MachineRecord, TelemetryRecord.machine_id == MachineRecord.machine_id)
                .order_by(desc(TelemetryRecord.ts))
                .limit(limit)
            )
            results = db.execute(query).all()

        current_n = len(results)
        window_desc = f"Latest {current_n} observations (rolling {window_hours}h)"

        # 2. Insufficient data guard
        if current_n < MIN_SAMPLE_SIZE:
            empty_df = pd.DataFrame()
            report: DriftReport = generate_drift_report(
                empty_df,
                reference=get_drift_reference(),
                model_version=model_version,
                window_description=window_desc,
                min_sample_size=MIN_SAMPLE_SIZE,
            )
            # Override current_sample_count to accurately reflect database rows
            report.current_sample_count = current_n
            return DriftReportDTO(**report.to_dict())

        # 3. Build DataFrame matching feature contract
        data_rows = []
        for tel, m_type in results:
            data_rows.append(
                {
                    "Air_Temperature_C": tel.air_temp_c,
                    "Process_Temperature_C": tel.process_temp_c,
                    "Rotational_Speed_RPM": tel.rotational_speed_rpm,
                    "Torque_Nm": tel.torque_nm,
                    "Vibration_mm_s": tel.vibration_mm_s,
                    "Pressure_bar": tel.pressure_bar,
                    "Current_A": tel.current_a,
                    "Voltage_V": tel.voltage_v,
                    "Tool_Wear_Min": tel.tool_wear_min,
                    "Operating_Hours": tel.operating_hours,
                    "Machine_Type": m_type or "Unknown",
                }
            )

        current_df = pd.DataFrame(data_rows)

        # 4. Generate multi-feature drift report
        report = generate_drift_report(
            current_df,
            reference=get_drift_reference(),
            model_version=model_version,
            window_description=window_desc,
            min_sample_size=MIN_SAMPLE_SIZE,
        )

        return DriftReportDTO(
            model_version=report.model_version,
            reference_version=report.reference_version,
            overall_status=report.overall_status.value,
            reference_sample_count=report.reference_sample_count,
            current_sample_count=report.current_sample_count,
            window_description=report.window_description,
            generated_at=report.generated_at,
            features=[FeatureDriftDTO(**f.to_dict()) for f in report.feature_results],
            drift_alerts=[DriftAlertDTO(**a.to_dict()) for a in report.drift_alerts],
            drifting_features_count=report.drifting_features_count,
            watch_features_count=report.watch_features_count,
            stable_features_count=report.stable_features_count,
        )

    @staticmethod
    def get_performance_metrics(
        db: Session,
        window: str = "all",
        window_days: int | None = None,
    ) -> PerformanceMetricsDTO:
        """Query feedback records and calculate running precision, recall, and false alarm rate."""
        query = select(FeedbackRecord).order_by(desc(FeedbackRecord.created_at))
        records = db.execute(query).scalars().all()

        items = [
            {
                "feedback_type": r.feedback_type,
                "created_at": r.created_at,
            }
            for r in records
        ]

        metrics = calculate_feedback_metrics(
            items,
            window=window,
            window_days=window_days,
        )

        return PerformanceMetricsDTO(**metrics.to_dict())

    @classmethod
    def get_overview(
        cls,
        db: Session,
        window_hours: int = 24,
        window_days: int | None = None,
    ) -> MLOpsOverviewDTO:
        """Generate unified MLOps overview encompassing drift, performance, and registry info."""
        engine = get_model_engine()
        model_version = engine.model_version if engine else "v1.2-xgb"
        threshold = engine.operational_threshold if engine else 0.16

        drift_report = cls.get_drift_report(db, window_hours=window_hours)
        performance = cls.get_performance_metrics(
            db, window="all" if window_days is None else f"{window_days}d", window_days=window_days
        )

        return MLOpsOverviewDTO(
            model_name="edgetwin-risk",
            model_version=model_version,
            registered_alias="champion",
            operational_threshold=threshold,
            drift=drift_report,
            performance=performance,
            last_evaluated_at=datetime.now(UTC).isoformat(),
        )

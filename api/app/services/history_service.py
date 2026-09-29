"""History and operational analytics service layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import ClassVar

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models.alert import AlertRecord
from api.app.models.machine import MachineRecord
from api.app.models.maintenance import MaintenanceRecord
from api.app.models.prediction import PredictionRecord
from api.app.models.telemetry import TelemetryRecord
from api.app.models.twin import TwinSnapshotRecord
from api.app.schemas.history import (
    FleetAlertCount,
    FleetHealthDistribution,
    FleetHistoryResponse,
    FleetMachineSummary,
    FleetRiskDistribution,
    HistoricalAlertItem,
    HistoricalHealthPoint,
    HistoricalMaintenanceItem,
    HistoricalPredictionPoint,
    HistoricalSensorPoint,
    MachineHistoryResponse,
    MachineHistorySummary,
)
from api.app.services.twin_query_service import TwinQueryService

MAX_SAMPLE_GAP_SECONDS = 300  # Max gap of 5 minutes between samples to count continuous duration


def ensure_utc(dt: datetime) -> datetime:
    """Normalize datetime to UTC timezone-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class HistoryService:
    """Service for querying, aggregating, and downsampling historical operational data."""

    WINDOW_MAP: ClassVar[dict[str, timedelta]] = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    @classmethod
    def parse_window(
        cls,
        window: str = "24h",
        before: datetime | None = None,
        after: datetime | None = None,
    ) -> tuple[datetime, datetime]:
        """Resolve start and end UTC timestamps from time window or explicit bounds."""
        now = datetime.now(UTC)

        if after is not None and before is not None:
            after = ensure_utc(after)
            before = ensure_utc(before)
            if after >= before:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="'after' timestamp must be strictly earlier than 'before' timestamp.",
                )
            return after, before

        if window not in cls.WINDOW_MAP:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid time window '{window}'. Allowed values: {', '.join(cls.WINDOW_MAP.keys())}.",
            )

        delta = cls.WINDOW_MAP[window]
        to_ts = ensure_utc(before) if before is not None else now
        from_ts = ensure_utc(after) if after is not None else (to_ts - delta)

        return from_ts, to_ts

    @classmethod
    def get_machine_history(
        cls,
        db: Session,
        machine_id: str,
        window: str = "24h",
        before: datetime | None = None,
        after: datetime | None = None,
        max_points: int = 120,
    ) -> MachineHistoryResponse:
        """Query bounded historical telemetry, health trends, predictions, and events."""
        # 1. Verify machine exists
        machine = db.execute(
            select(MachineRecord).where(MachineRecord.machine_id == machine_id)
        ).scalar_one_or_none()

        if machine is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine '{machine_id}' not found.",
            )

        from_ts, to_ts = cls.parse_window(window=window, before=before, after=after)

        # 2. Query alerts in window
        alert_records = (
            db.execute(
                select(AlertRecord)
                .where(
                    AlertRecord.machine_id == machine_id,
                    AlertRecord.triggered_at >= from_ts,
                    AlertRecord.triggered_at <= to_ts,
                )
                .order_by(AlertRecord.triggered_at.desc())
            )
            .scalars()
            .all()
        )

        alerts = [
            HistoricalAlertItem(
                id=a.id,
                alert_type=a.alert_type,
                severity=a.severity,
                status=a.status,
                message=a.message,
                triggered_at=ensure_utc(a.triggered_at),
                acknowledged_at=ensure_utc(a.acknowledged_at) if a.acknowledged_at else None,
                resolved_at=ensure_utc(a.resolved_at) if a.resolved_at else None,
                resolved_by=a.resolved_by,
            )
            for a in alert_records
        ]

        # 3. Query maintenance in window
        maint_records = (
            db.execute(
                select(MaintenanceRecord)
                .where(
                    MaintenanceRecord.machine_id == machine_id,
                    MaintenanceRecord.created_at >= from_ts,
                    MaintenanceRecord.created_at <= to_ts,
                )
                .order_by(MaintenanceRecord.created_at.desc())
            )
            .scalars()
            .all()
        )

        maintenance = [
            HistoricalMaintenanceItem(
                id=m.id,
                alert_id=m.alert_id,
                event_type=m.event_type,
                description=m.description,
                status=m.status,
                technician=m.technician,
                started_at=ensure_utc(m.started_at) if m.started_at else None,
                completed_at=ensure_utc(m.completed_at) if m.completed_at else None,
                created_at=ensure_utc(m.created_at),
            )
            for m in maint_records
        ]

        # 4. Query predictions in window
        pred_records = (
            db.execute(
                select(PredictionRecord)
                .where(
                    PredictionRecord.machine_id == machine_id,
                    PredictionRecord.ts >= from_ts,
                    PredictionRecord.ts <= to_ts,
                )
                .order_by(PredictionRecord.ts.desc())
                .limit(100)
            )
            .scalars()
            .all()
        )

        predictions = [
            HistoricalPredictionPoint(
                id=p.id,
                ts=ensure_utc(p.ts),
                failure_probability=p.failure_probability,
                failure_prediction=p.failure_prediction,
                risk_band=p.risk_band,
                anomaly_score=p.anomaly_score,
                anomaly_flag=p.anomaly_flag,
                model_version=p.model_version,
                top_factors=p.top_factors,
            )
            for p in pred_records
        ]

        # 5. Query twin snapshots in window (for health trend)
        snapshot_records = (
            db.execute(
                select(TwinSnapshotRecord)
                .where(
                    TwinSnapshotRecord.machine_id == machine_id,
                    TwinSnapshotRecord.ts >= from_ts,
                    TwinSnapshotRecord.ts <= to_ts,
                )
                .order_by(TwinSnapshotRecord.ts.asc())
            )
            .scalars()
            .all()
        )

        # 6. Query telemetry in window
        telemetry_records = (
            db.execute(
                select(TelemetryRecord)
                .where(
                    TelemetryRecord.machine_id == machine_id,
                    TelemetryRecord.ts >= from_ts,
                    TelemetryRecord.ts <= to_ts,
                )
                .order_by(TelemetryRecord.ts.asc())
            )
            .scalars()
            .all()
        )

        # Fallback for health points: if snapshots exist, use them. If not, check predictions.
        raw_health_points: list[HistoricalHealthPoint] = []
        if snapshot_records:
            raw_health_points = [
                HistoricalHealthPoint(
                    ts=ensure_utc(s.ts),
                    health_score=round(s.health_score, 1),
                    health_state=s.health_state,
                    operating_state=s.operating_state,
                    failure_probability=round(s.failure_probability, 4),
                )
                for s in snapshot_records
            ]
        elif pred_records:
            raw_health_points = [
                HistoricalHealthPoint(
                    ts=ensure_utc(p.ts),
                    health_score=round(p.health_score if p.health_score is not None else 100.0, 1),
                    health_state=p.health_state or "HEALTHY",
                    operating_state=machine.status or "UNKNOWN",
                    failure_probability=round(p.failure_probability, 4),
                )
                for p in reversed(pred_records)
            ]

        # Raw sensor points from telemetry
        raw_sensor_points = [
            HistoricalSensorPoint(
                ts=ensure_utc(t.ts),
                process_temp_c=t.process_temp_c,
                air_temp_c=t.air_temp_c,
                rotational_speed_rpm=t.rotational_speed_rpm,
                torque_nm=t.torque_nm,
                vibration_mm_s=t.vibration_mm_s,
                pressure_bar=t.pressure_bar,
                current_a=t.current_a,
                voltage_v=t.voltage_v,
                power_va=t.power_va,
                tool_wear_min=t.tool_wear_min,
            )
            for t in telemetry_records
        ]

        # 7. Summary metrics calculation
        health_scores = [h.health_score for h in raw_health_points]
        avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else None
        min_health = round(min(health_scores), 1) if health_scores else None
        max_health = round(max(health_scores), 1) if health_scores else None

        fail_probs = [
            h.failure_probability for h in raw_health_points if h.failure_probability is not None
        ]
        avg_fail_prob = round(sum(fail_probs) / len(fail_probs), 4) if fail_probs else None

        # Defensible duration in WARNING / CRITICAL
        time_warning_s = 0
        time_critical_s = 0
        if len(raw_health_points) > 1:
            for i in range(len(raw_health_points) - 1):
                p_cur = raw_health_points[i]
                p_next = raw_health_points[i + 1]
                gap = (p_next.ts - p_cur.ts).total_seconds()
                if 0 < gap <= MAX_SAMPLE_GAP_SECONDS:
                    gap_int = int(gap)
                    if p_cur.health_state == "WARNING" or (60.0 <= p_cur.health_score < 80.0):
                        time_warning_s += gap_int
                    elif p_cur.health_state == "CRITICAL" or (p_cur.health_score < 60.0):
                        time_critical_s += gap_int

        resolved_alerts = sum(1 for a in alerts if a.status == "RESOLVED")

        summary = MachineHistorySummary(
            avg_health_score=avg_health,
            min_health_score=min_health,
            max_health_score=max_health,
            time_in_warning_s=time_warning_s,
            time_in_critical_s=time_critical_s,
            alert_count=len(alerts),
            resolved_alert_count=resolved_alerts,
            maintenance_count=len(maintenance),
            avg_failure_probability=avg_fail_prob,
            sample_count=len(telemetry_records) or len(raw_health_points),
        )

        # 8. Downsampling for charts if point counts exceed max_points
        is_downsampled = False
        downsample_interval_s: int | None = None

        health_trend = raw_health_points
        sensor_trend = raw_sensor_points

        total_sensor_pts = len(raw_sensor_points)
        if total_sensor_pts > max_points:
            is_downsampled = True
            window_duration = max(1, (to_ts - from_ts).total_seconds())
            bucket_duration = window_duration / max_points
            downsample_interval_s = max(1, int(bucket_duration))
            sensor_trend = cls._downsample_sensors(raw_sensor_points, from_ts, to_ts, max_points)

        total_health_pts = len(raw_health_points)
        if total_health_pts > max_points:
            is_downsampled = True
            health_trend = cls._downsample_health(raw_health_points, from_ts, to_ts, max_points)

        # Retrieve current operating state
        try:
            latest_twin = TwinQueryService.get_latest_twin(db, machine_id)
            current_state = latest_twin.operating_state or machine.status or "UNKNOWN"
        except Exception:  # noqa: BLE001
            current_state = machine.status or "UNKNOWN"

        return MachineHistoryResponse(
            machine_id=machine_id,
            machine_type=machine.machine_type,
            current_operating_state=current_state,
            window=window,
            from_ts=from_ts,
            to_ts=to_ts,
            summary=summary,
            health_trend=health_trend,
            sensor_trend=sensor_trend,
            prediction_history=predictions,
            alerts=alerts,
            maintenance=maintenance,
            is_downsampled=is_downsampled,
            downsample_interval_s=downsample_interval_s,
        )

    @classmethod
    def get_fleet_history(
        cls,
        db: Session,
        window: str = "24h",
        before: datetime | None = None,
        after: datetime | None = None,
    ) -> FleetHistoryResponse:
        """Compute aggregated fleet-level operational performance and triage indicators."""
        from_ts, to_ts = cls.parse_window(window=window, before=before, after=after)

        machines = (
            db.execute(select(MachineRecord).order_by(MachineRecord.machine_id)).scalars().all()
        )
        total_machines = len(machines)

        healthy_cnt = 0
        warning_cnt = 0
        critical_cnt = 0
        offline_cnt = 0

        low_risk_cnt = 0
        med_risk_cnt = 0
        high_risk_cnt = 0
        crit_risk_cnt = 0

        health_scores: list[float] = []
        alerts_by_machine: list[FleetAlertCount] = []
        machine_summaries: list[FleetMachineSummary] = []

        for m in machines:
            try:
                twin = TwinQueryService.get_latest_twin(db, m.machine_id)
                h_score = twin.health_score
                h_state = twin.health_state or "OFFLINE"
                r_band = twin.risk_band or "LOW"
                op_state = twin.operating_state or m.status or "UNKNOWN"
                fail_prob = twin.failure_probability
            except Exception:  # noqa: BLE001
                h_score = None
                h_state = "OFFLINE"
                r_band = "LOW"
                op_state = m.status or "UNKNOWN"
                fail_prob = None

            # Query machine alert counts in window
            total_machine_alerts = db.execute(
                select(func.count(AlertRecord.id)).where(
                    AlertRecord.machine_id == m.machine_id,
                    AlertRecord.triggered_at >= from_ts,
                    AlertRecord.triggered_at <= to_ts,
                )
            ).scalar_one()

            crit_alerts = db.execute(
                select(func.count(AlertRecord.id)).where(
                    AlertRecord.machine_id == m.machine_id,
                    AlertRecord.severity == "CRITICAL",
                    AlertRecord.triggered_at >= from_ts,
                    AlertRecord.triggered_at <= to_ts,
                )
            ).scalar_one()

            # Query maintenance count in window
            maint_count = db.execute(
                select(func.count(MaintenanceRecord.id)).where(
                    MaintenanceRecord.machine_id == m.machine_id,
                    MaintenanceRecord.created_at >= from_ts,
                    MaintenanceRecord.created_at <= to_ts,
                )
            ).scalar_one()

            # Tally alert frequency if machine had any alerts
            alerts_by_machine.append(
                FleetAlertCount(
                    machine_id=m.machine_id,
                    alert_count=total_machine_alerts,
                    critical_count=crit_alerts,
                )
            )

            # Health classification
            if h_score is not None:
                health_scores.append(h_score)
                if h_score >= 80.0:
                    healthy_cnt += 1
                elif h_score >= 60.0:
                    warning_cnt += 1
                else:
                    critical_cnt += 1
            else:
                offline_cnt += 1

            # Risk classification
            if r_band == "CRITICAL":
                crit_risk_cnt += 1
            elif r_band == "HIGH":
                high_risk_cnt += 1
            elif r_band == "MEDIUM":
                med_risk_cnt += 1
            else:
                low_risk_cnt += 1

            machine_summaries.append(
                FleetMachineSummary(
                    machine_id=m.machine_id,
                    machine_type=m.machine_type,
                    location=m.location,
                    operating_state=op_state,
                    health_state=h_state,
                    health_score=round(h_score, 1) if h_score is not None else None,
                    failure_probability=round(fail_prob, 4) if fail_prob is not None else None,
                    alert_count=total_machine_alerts,
                    maintenance_count=maint_count,
                )
            )

        # Sort alert frequency by total alerts descending
        alerts_by_machine.sort(key=lambda x: (x.alert_count, x.critical_count), reverse=True)

        avg_fleet_health = (
            round(sum(health_scores) / len(health_scores), 1) if health_scores else None
        )

        return FleetHistoryResponse(
            window=window,
            from_ts=from_ts,
            to_ts=to_ts,
            total_machines=total_machines,
            avg_fleet_health=avg_fleet_health,
            health_distribution=FleetHealthDistribution(
                healthy=healthy_cnt,
                warning=warning_cnt,
                critical=critical_cnt,
                offline=offline_cnt,
            ),
            risk_distribution=FleetRiskDistribution(
                low=low_risk_cnt,
                medium=med_risk_cnt,
                high=high_risk_cnt,
                critical=crit_risk_cnt,
            ),
            alerts_by_machine=alerts_by_machine,
            machine_summaries=machine_summaries,
        )

    @classmethod
    def _downsample_sensors(
        cls,
        points: list[HistoricalSensorPoint],
        from_ts: datetime,
        to_ts: datetime,
        num_buckets: int,
    ) -> list[HistoricalSensorPoint]:
        """Aggregate dense sensor observations into equal-interval average bins."""
        if not points or num_buckets <= 0:
            return []

        from_ts = ensure_utc(from_ts)
        to_ts = ensure_utc(to_ts)
        window_span = (to_ts - from_ts).total_seconds()
        bucket_span = window_span / num_buckets

        buckets: list[list[HistoricalSensorPoint]] = [[] for _ in range(num_buckets)]

        for pt in points:
            offset = (ensure_utc(pt.ts) - from_ts).total_seconds()
            idx = int(offset / bucket_span)
            if idx < 0:
                idx = 0
            elif idx >= num_buckets:
                idx = num_buckets - 1
            buckets[idx].append(pt)

        def _calc_avg(pts: list[HistoricalSensorPoint], attr: str) -> float | None:
            vals = [getattr(p, attr) for p in pts if getattr(p, attr) is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        downsampled: list[HistoricalSensorPoint] = []
        for i, b_points in enumerate(buckets):
            if not b_points:
                continue

            # Bucket timestamp is representative midpoint or average of point timestamps
            mid_sec = from_ts.timestamp() + (i + 0.5) * bucket_span
            b_ts = datetime.fromtimestamp(mid_sec, tz=UTC)

            downsampled.append(
                HistoricalSensorPoint(
                    ts=b_ts,
                    process_temp_c=_calc_avg(b_points, "process_temp_c"),
                    air_temp_c=_calc_avg(b_points, "air_temp_c"),
                    rotational_speed_rpm=_calc_avg(b_points, "rotational_speed_rpm"),
                    torque_nm=_calc_avg(b_points, "torque_nm"),
                    vibration_mm_s=_calc_avg(b_points, "vibration_mm_s"),
                    pressure_bar=_calc_avg(b_points, "pressure_bar"),
                    current_a=_calc_avg(b_points, "current_a"),
                    voltage_v=_calc_avg(b_points, "voltage_v"),
                    power_va=_calc_avg(b_points, "power_va"),
                    tool_wear_min=_calc_avg(b_points, "tool_wear_min"),
                )
            )

        return downsampled

    @classmethod
    def _downsample_health(
        cls,
        points: list[HistoricalHealthPoint],
        from_ts: datetime,
        to_ts: datetime,
        num_buckets: int,
    ) -> list[HistoricalHealthPoint]:
        """Aggregate dense health snapshots into equal-interval average bins."""
        if not points or num_buckets <= 0:
            return []

        from_ts = ensure_utc(from_ts)
        to_ts = ensure_utc(to_ts)
        window_span = (to_ts - from_ts).total_seconds()
        bucket_span = window_span / num_buckets

        buckets: list[list[HistoricalHealthPoint]] = [[] for _ in range(num_buckets)]

        for pt in points:
            offset = (ensure_utc(pt.ts) - from_ts).total_seconds()
            idx = int(offset / bucket_span)
            if idx < 0:
                idx = 0
            elif idx >= num_buckets:
                idx = num_buckets - 1
            buckets[idx].append(pt)

        downsampled: list[HistoricalHealthPoint] = []
        for i, b_points in enumerate(buckets):
            if not b_points:
                continue

            mid_sec = from_ts.timestamp() + (i + 0.5) * bucket_span
            b_ts = datetime.fromtimestamp(mid_sec, tz=UTC)

            h_vals = [p.health_score for p in b_points]
            avg_h = round(sum(h_vals) / len(h_vals), 1)

            p_vals = [p.failure_probability for p in b_points if p.failure_probability is not None]
            avg_p = round(sum(p_vals) / len(p_vals), 4) if p_vals else None

            # Representative state is worst observed in bucket
            has_crit = any(p.health_state == "CRITICAL" or p.health_score < 60 for p in b_points)
            has_warn = any(p.health_state == "WARNING" or p.health_score < 80 for p in b_points)
            rep_health_state = "CRITICAL" if has_crit else ("WARNING" if has_warn else "HEALTHY")

            rep_op_state = b_points[-1].operating_state

            downsampled.append(
                HistoricalHealthPoint(
                    ts=b_ts,
                    health_score=avg_h,
                    health_state=rep_health_state,
                    operating_state=rep_op_state,
                    failure_probability=avg_p,
                )
            )

        return downsampled

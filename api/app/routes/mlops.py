"""
api/app/routes/mlops.py — REST API endpoints for MLOps drift monitoring and feedback analysis.

Protected by JWT bearer authentication.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.user import UserRecord
from api.app.schemas.mlops import (
    DriftReportDTO,
    MLOpsOverviewDTO,
    PerformanceMetricsDTO,
)
from api.app.security.deps import get_current_user
from api.app.services.mlops_service import MLOpsService

router = APIRouter(prefix="/mlops", tags=["MLOps"])


@router.get(
    "/overview",
    response_model=MLOpsOverviewDTO,
    summary="Get unified MLOps overview",
    description="Returns champion model registry metadata, overall drift status, feature drift report, and operator feedback metrics.",
)
def get_mlops_overview(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    window_hours: int = Query(24, ge=1, le=720, description="Rolling hours for telemetry window"),
    window_days: int | None = Query(
        None, ge=1, le=365, description="Days for feedback window (None = all)"
    ),
) -> MLOpsOverviewDTO:
    """Retrieve full MLOps monitoring overview."""
    return MLOpsService.get_overview(db, window_hours=window_hours, window_days=window_days)


@router.get(
    "/drift",
    response_model=DriftReportDTO,
    summary="Get feature & data drift report",
    description="Evaluates PSI and KS statistics across all 14 monitored features against the frozen training baseline.",
)
def get_drift_report(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    window_hours: int = Query(24, ge=1, le=720, description="Rolling hours for telemetry window"),
    limit: int = Query(1000, ge=10, le=10000, description="Maximum telemetry records to evaluate"),
) -> DriftReportDTO:
    """Retrieve feature-level and overall data drift report."""
    return MLOpsService.get_drift_report(db, window_hours=window_hours, limit=limit)


@router.get(
    "/performance",
    response_model=PerformanceMetricsDTO,
    summary="Get feedback performance metrics",
    description="Computes running precision, recall, and false-alarm rate derived from field operator feedback.",
)
def get_performance_metrics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    window: str = Query("all", description="Window label: 7d, 30d, 90d, all"),
    window_days: int | None = Query(
        None, ge=1, le=365, description="Filter feedback within last N days"
    ),
) -> PerformanceMetricsDTO:
    """Retrieve operator feedback performance metrics."""
    return MLOpsService.get_performance_metrics(db, window=window, window_days=window_days)

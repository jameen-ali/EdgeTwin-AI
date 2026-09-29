"""Pydantic schemas for MLOps drift monitoring and feedback performance analysis."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FeatureDriftDTO(BaseModel):
    """Drift metrics and status for a single monitored feature."""

    feature_name: str = Field(..., description="Monitored feature column name")
    feature_type: str = Field(..., description="Feature type: numeric or categorical")
    reference_count: int = Field(
        ..., description="Number of observations in reference training baseline"
    )
    current_count: int = Field(
        ..., description="Number of valid observations in current operational window"
    )
    psi: float | None = Field(None, description="Population Stability Index (PSI)")
    ks_statistic: float | None = Field(
        None, description="Kolmogorov-Smirnov two-sample statistic D"
    )
    ks_p_value: float | None = Field(None, description="Kolmogorov-Smirnov two-sample p-value")
    missing_reference_pct: float = Field(
        ..., description="Missing data percentage in reference baseline"
    )
    missing_current_pct: float = Field(
        ..., description="Missing data percentage in current operational data"
    )
    status: str = Field(
        ..., description="Operational status: STABLE, WATCH, DRIFT, INSUFFICIENT_DATA"
    )
    message: str = Field(..., description="Diagnostic summary description")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional statistical details"
    )

    model_config = ConfigDict(from_attributes=True)


class DriftAlertDTO(BaseModel):
    """Operational alert emitted when feature drift exceeds watch/drift thresholds."""

    feature_name: str = Field(..., description="Drifting feature name")
    severity: str = Field(..., description="Alert severity: WARNING or CRITICAL")
    metric: str = Field(..., description="Triggering metric: PSI, KS, or DATA_QUALITY")
    value: float = Field(..., description="Measured metric value")
    threshold: float = Field(..., description="Exceeded threshold")
    message: str = Field(..., description="Alert narrative")
    recommendation: str = Field(
        ..., description="Recommended engineering or MLOps inspection action"
    )

    model_config = ConfigDict(from_attributes=True)


class DriftReportDTO(BaseModel):
    """Aggregated feature drift report."""

    model_version: str = Field(..., description="Champion model version tag")
    reference_version: str = Field(..., description="Training reference baseline identifier")
    overall_status: str = Field(
        ..., description="Aggregated drift status: STABLE, WATCH, DRIFT, INSUFFICIENT_DATA"
    )
    reference_sample_count: int = Field(..., description="Total reference training observations")
    current_sample_count: int = Field(..., description="Total operational observations evaluated")
    window_description: str = Field(
        ..., description="Description of the evaluated telemetry window"
    )
    generated_at: str = Field(..., description="UTC timestamp of drift assessment")
    features: list[FeatureDriftDTO] = Field(..., description="Per-feature drift results")
    drift_alerts: list[DriftAlertDTO] = Field(
        default_factory=list, description="Model and data drift alerts"
    )
    drifting_features_count: int = Field(0, description="Count of features in DRIFT state")
    watch_features_count: int = Field(0, description="Count of features in WATCH state")
    stable_features_count: int = Field(0, description="Count of features in STABLE state")

    model_config = ConfigDict(from_attributes=True)


class PerformanceMetricsDTO(BaseModel):
    """Operator feedback performance metrics and ground-truth validation."""

    window: str = Field(..., description="Time window evaluated: 7d, 30d, 90d, all")
    total_feedback: int = Field(..., description="Total feedback submissions in window")
    confirmed_count: int = Field(..., description="Confirmed true positive failure count")
    false_alarm_count: int = Field(..., description="False alarm count")
    inconclusive_count: int = Field(..., description="Inconclusive feedback count")
    precision: float | None = Field(None, description="Running precision (TP / (TP + FP))")
    recall: float | None = Field(None, description="Running recall estimate (TP / (TP + FN))")
    false_alarm_rate: float | None = Field(None, description="Operational false alarm rate")
    status: str = Field(..., description="SUFFICIENT or INSUFFICIENT_DATA")
    note: str = Field(..., description="Evaluation narrative and sample size caveats")
    generated_at: str = Field(..., description="Evaluation timestamp")

    model_config = ConfigDict(from_attributes=True)


class MLOpsOverviewDTO(BaseModel):
    """Top-level MLOps monitoring overview."""

    model_name: str = Field(..., description="Registered model name")
    model_version: str = Field(..., description="Champion model version tag")
    registered_alias: str = Field(..., description="Model alias (e.g. champion)")
    operational_threshold: float = Field(..., description="Operational decision cutoff t*")
    drift: DriftReportDTO = Field(..., description="Feature drift assessment")
    performance: PerformanceMetricsDTO = Field(
        ..., description="Feedback-based performance metrics"
    )
    last_evaluated_at: str = Field(..., description="Evaluation timestamp")

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

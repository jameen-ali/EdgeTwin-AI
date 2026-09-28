"""
api/app/inference/schemas.py — Typed schemas and data structures for ML inference and health assessment.

Defines the contracts for:
- Layer 1 Sensor Condition
- Layer 2 ML Risk
- Layer 3 Anomaly Detection
- Layer 4 Machine Health
- Layer 5 Alert Severity
- Layer 6 Recommendations
- Complete unified InferenceResult and HealthAssessment payloads
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Recommendation:
    """Actionable maintenance recommendation (Layer 6)."""

    action_code: str
    recommendation_text: str
    urgency: str  # ROUTINE, LOW, MEDIUM, HIGH, IMMEDIATE
    target_component: str
    reason: str


@dataclass
class HealthAssessment:
    """Comprehensive multi-layer health evaluation (Layers 1-6)."""

    # Layer 1: Sensor Condition
    out_of_range_count: int
    missing_count: int
    sensor_penalty: float  # Clamped [0.0, 15.0]
    sensor_status: dict[str, str] = field(default_factory=dict)
    is_degraded: bool = False

    # Layer 2: Supervised Failure Risk
    failure_probability: float | None = None
    failure_prediction: int | None = None  # 0 or 1 at t* = 0.16
    risk_band: str | None = None  # LOW, MEDIUM, HIGH, CRITICAL

    # Layer 3: Unsupervised Anomaly Detection
    anomaly_score: float | None = None  # Normalized [0.0, 1.0]
    anomaly_flag: bool | None = None

    # Layer 4: Composite Machine Health
    health_score: float | None = None  # [0.0, 100.0]
    health_state: str = "OFFLINE"  # HEALTHY, WARNING, CRITICAL, MAINTENANCE_REQUIRED, OFFLINE
    delta_risk: float | None = None
    delta_anomaly: float | None = None

    # Layer 5: Alert Severity
    alert_severity: str | None = None  # None, INFO, WARNING, CRITICAL
    alert_type: str | None = None
    trigger_conditions: dict[str, Any] = field(default_factory=dict)

    # Layer 6: Recommendation
    recommendation: Recommendation | None = None


@dataclass
class InferenceResult:
    """Complete inference and health evaluation bundle for a telemetry observation."""

    machine_id: str
    ts: datetime
    telemetry_id: int | None

    # Layer 2: Risk
    failure_probability: float
    failure_prediction: int
    risk_band: str

    # Layer 3: Anomaly
    anomaly_score: float | None
    anomaly_flag: bool | None

    # Layer 4: Health
    health_score: float | None
    health_state: str

    # Layer 5: Explainability (SHAP)
    top_factors: list[dict[str, Any]] | None
    all_factors: list[dict[str, Any]] | None
    model_margin: float | None
    base_value: float | None
    additivity_verified: bool
    disclaimer: str

    # Health & Alert Context
    health_assessment: HealthAssessment
    model_version: str
    inference_latency_ms: float

"""Prediction database entity storing ML inference and health assessments."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    desc,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base

if TYPE_CHECKING:
    from api.app.models.machine import MachineRecord
    from api.app.models.telemetry import TelemetryRecord


class PredictionRecord(Base):
    """Prediction entity storing outputs produced by the ML inference service and health engine."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    machine_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("machines.machine_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telemetry_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("telemetry.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Layer 2: Supervised Failure Risk
    failure_probability: Mapped[float] = mapped_column(Float, nullable=False)
    failure_prediction: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 or 1
    risk_band: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # LOW, MEDIUM, HIGH, CRITICAL

    # Layer 3: Unsupervised Anomaly Detection
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Layer 4: Composite Machine Health
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    health_state: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Layer 5: Explainability (Top contributing SHAP factors)
    top_factors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    # Governance & Lineage
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    inference_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    machine: Mapped["MachineRecord"] = relationship("MachineRecord", back_populates="predictions")
    telemetry: Mapped["TelemetryRecord"] = relationship(
        "TelemetryRecord", back_populates="predictions"
    )

    __table_args__ = (Index("ix_predictions_machine_ts_desc", "machine_id", desc("ts")),)

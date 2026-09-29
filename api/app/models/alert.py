"""Alert entity model for system and machine alarms."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base

if TYPE_CHECKING:
    from api.app.models.feedback import FeedbackRecord
    from api.app.models.machine import MachineRecord
    from api.app.models.maintenance import MaintenanceRecord


class AlertRecord(Base):
    """Alert record raised by the Layer 5 alert engine or edge safety trips."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    machine_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("machines.machine_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # INFO, WARNING, CRITICAL
    status: Mapped[str] = mapped_column(
        String(16), default="OPEN", nullable=False
    )  # OPEN, ACKNOWLEDGED, RESOLVED
    message: Mapped[str] = mapped_column(String(255), nullable=False)

    trigger_conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    top_factors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relationships
    machine: Mapped["MachineRecord"] = relationship("MachineRecord", back_populates="alerts")
    feedbacks: Mapped[list["FeedbackRecord"]] = relationship(
        "FeedbackRecord", back_populates="alert", cascade="all, delete-orphan"
    )
    maintenance_events: Mapped[list["MaintenanceRecord"]] = relationship(
        "MaintenanceRecord", back_populates="alert"
    )

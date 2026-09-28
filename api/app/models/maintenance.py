"""Maintenance event entity model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base

if TYPE_CHECKING:
    from api.app.models.machine import MachineRecord


class MaintenanceRecord(Base):
    """Maintenance event entity for logging actions, inspections, and component overhauls."""

    __tablename__ = "maintenance_events"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    machine_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("machines.machine_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # INSPECTION, PART_REPLACEMENT, OVERHAUL, LUBRICATION, CALIBRATION
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="SCHEDULED", nullable=False
    )  # SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
    technician: Mapped[str | None] = mapped_column(String(128), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    machine: Mapped["MachineRecord"] = relationship(
        "MachineRecord", back_populates="maintenance_events"
    )

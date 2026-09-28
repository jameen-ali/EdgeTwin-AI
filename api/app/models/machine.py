"""Machine entity model representing physical and virtual assets."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base

if TYPE_CHECKING:
    from api.app.models.alert import AlertRecord
    from api.app.models.feedback import FeedbackRecord
    from api.app.models.maintenance import MaintenanceRecord
    from api.app.models.prediction import PredictionRecord
    from api.app.models.telemetry import TelemetryRecord
    from api.app.models.twin import TwinSnapshotRecord


class MachineRecord(Base):
    """Machine entity representing monitored equipment in the factory fleet."""

    __tablename__ = "machines"

    machine_id: Mapped[str] = mapped_column(String(32), primary_key=True, index=True)
    machine_type: Mapped[str] = mapped_column(String(64), nullable=False)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="OFFLINE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    telemetry_records: Mapped[list["TelemetryRecord"]] = relationship(
        "TelemetryRecord", back_populates="machine", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["PredictionRecord"]] = relationship(
        "PredictionRecord", back_populates="machine", cascade="all, delete-orphan"
    )
    twin_snapshots: Mapped[list["TwinSnapshotRecord"]] = relationship(
        "TwinSnapshotRecord", back_populates="machine", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["AlertRecord"]] = relationship(
        "AlertRecord", back_populates="machine", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["FeedbackRecord"]] = relationship(
        "FeedbackRecord", back_populates="machine", cascade="all, delete-orphan"
    )
    maintenance_events: Mapped[list["MaintenanceRecord"]] = relationship(
        "MaintenanceRecord", back_populates="machine", cascade="all, delete-orphan"
    )

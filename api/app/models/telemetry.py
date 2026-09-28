"""Telemetry database entity storing raw edge observations."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base

if TYPE_CHECKING:
    from api.app.models.machine import MachineRecord
    from api.app.models.prediction import PredictionRecord


class TelemetryRecord(Base):
    """Raw telemetry record received from edge or virtual devices conforming to edgetwin.telemetry.v1."""

    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    machine_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("machines.machine_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    provenance: Mapped[str] = mapped_column(String(16), nullable=False)  # SIMULATED, REPLAY, REAL
    fw: Mapped[str] = mapped_column(String(32), nullable=False)

    # 10 Raw Sensor Signals (nullable to support missing sensor values natively)
    air_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    process_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    rotational_speed_rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    torque_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    vibration_mm_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_bar: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    voltage_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_wear_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    operating_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Sensor Quality Assessment Flags
    quality: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Edge-Computed Diagnostics
    delta_t_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_va: Mapped[float | None] = mapped_column(Float, nullable=True)
    trip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    buffered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Complete raw payload for full auditability
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Ingestion metadata
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    machine: Mapped["MachineRecord"] = relationship(
        "MachineRecord", back_populates="telemetry_records"
    )
    predictions: Mapped[list["PredictionRecord"]] = relationship(
        "PredictionRecord", back_populates="telemetry", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("machine_id", "seq", name="uq_telemetry_machine_seq"),
        Index("ix_telemetry_machine_ts_desc", "machine_id", desc("ts")),
    )

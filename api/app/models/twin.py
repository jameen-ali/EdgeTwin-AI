"""Digital Twin state snapshot entity."""

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


class TwinSnapshotRecord(Base):
    """Digital Twin periodic state snapshot entity reflecting complete state history."""

    __tablename__ = "twin_snapshots"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    machine_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("machines.machine_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Sync and operational state
    sync_status: Mapped[str] = mapped_column(String(16), nullable=False)  # LIVE, STALE, OFFLINE
    operating_state: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # STOPPED, STARTING, RUNNING, DEGRADING, TRIPPED
    health_state: Mapped[str] = mapped_column(String(32), nullable=False)
    health_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_band: Mapped[str] = mapped_column(String(16), nullable=False)
    failure_probability: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Full structured twin state object for audit and UI replay
    snapshot_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    machine: Mapped["MachineRecord"] = relationship(
        "MachineRecord", back_populates="twin_snapshots"
    )

    __table_args__ = (Index("ix_twin_snapshots_machine_ts_desc", "machine_id", desc("ts")),)

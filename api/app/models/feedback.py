"""Engineer feedback database entity for active learning and model evaluation."""

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
    from api.app.models.alert import AlertRecord
    from api.app.models.machine import MachineRecord


class FeedbackRecord(Base):
    """Feedback entity recording engineer verification (CONFIRMED / FALSE_ALARM)."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    machine_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("machines.machine_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)  # CONFIRMED, FALSE_ALARM
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    machine: Mapped["MachineRecord"] = relationship("MachineRecord", back_populates="feedbacks")
    alert: Mapped["AlertRecord"] = relationship("AlertRecord", back_populates="feedbacks")

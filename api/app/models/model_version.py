"""Model version registry entity."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from api.app.db.base import Base


class ModelVersionRecord(Base):
    """Model version database record tracking MLflow registry synchronization and promotion status."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)  # "edgetwin-risk"
    version: Mapped[str] = mapped_column(String(32), nullable=False)  # "2"
    alias: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "champion", "challenger"
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("model_name", "version", name="uq_model_name_version"),)

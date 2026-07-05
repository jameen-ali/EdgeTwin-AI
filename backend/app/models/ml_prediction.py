import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy import Uuid as UUID
from app.core.database import Base


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    prediction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id    = Column(UUID(as_uuid=True), ForeignKey("machines.machine_id"), nullable=False, index=True)
    timestamp     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    health_score  = Column(Float, nullable=False)
    risk_level    = Column(String(20), nullable=False)
    rul_hours     = Column(Float, nullable=False)
    failure_type  = Column(String(100), nullable=True)
    confidence    = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=False)

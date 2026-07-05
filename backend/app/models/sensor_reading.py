import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy import Uuid as UUID
from app.core.database import Base


class SensorReading(Base):
    """High-frequency sensor data — ideally in TimescaleDB hypertable."""
    __tablename__ = "sensor_readings"

    reading_id  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id  = Column(UUID(as_uuid=True), ForeignKey("machines.machine_id"), nullable=False, index=True)
    timestamp   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    temperature = Column(Float, nullable=False)   # °C
    vibration   = Column(Float, nullable=False)   # mm/s
    pressure    = Column(Float, nullable=False)   # bar
    current     = Column(Float, nullable=False)   # Amperes
    rpm         = Column(Float, nullable=False)
    noise_level = Column(Float, nullable=False)   # dB

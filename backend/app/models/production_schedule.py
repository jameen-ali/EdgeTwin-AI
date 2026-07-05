from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base

class ProductionSchedule(Base):
    __tablename__ = "production_schedules"

    schedule_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    machine_id = Column(String(32), ForeignKey("machines.machine_id"), nullable=False)
    product = Column(String(100), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False) # on_track, delayed, halted, cancelled
    delay_reason = Column(String(200), nullable=True)
    units_planned = Column(Integer, default=1000)

    machine = relationship("Machine")

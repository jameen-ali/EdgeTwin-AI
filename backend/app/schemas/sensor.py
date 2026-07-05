from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class SensorReadingBase(BaseModel):
    temperature: float
    vibration: float
    pressure: float
    current: float
    rpm: float
    noise_level: float

class SensorReadingCreate(SensorReadingBase):
    machine_id: UUID
    timestamp: Optional[datetime] = None

class SensorReadingResponse(SensorReadingBase):
    reading_id: UUID
    machine_id: UUID
    timestamp: datetime

    class Config:
        from_attributes = True

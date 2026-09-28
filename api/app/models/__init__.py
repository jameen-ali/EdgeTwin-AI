"""SQLAlchemy models package exporting all database entities."""

from api.app.models.alert import AlertRecord
from api.app.models.feedback import FeedbackRecord
from api.app.models.machine import MachineRecord
from api.app.models.maintenance import MaintenanceRecord
from api.app.models.model_version import ModelVersionRecord
from api.app.models.prediction import PredictionRecord
from api.app.models.telemetry import TelemetryRecord
from api.app.models.twin import TwinSnapshotRecord
from api.app.models.user import UserRecord

__all__ = [
    "AlertRecord",
    "FeedbackRecord",
    "MachineRecord",
    "MaintenanceRecord",
    "ModelVersionRecord",
    "PredictionRecord",
    "TelemetryRecord",
    "TwinSnapshotRecord",
    "UserRecord",
]

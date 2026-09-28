"""
api/app/inference/__init__.py — EdgeTwin AI ML Inference & Health Engine package.
"""

from api.app.inference.engine import ModelEngine, get_model_engine
from api.app.inference.health_engine import HealthEngine
from api.app.inference.persistence import persist_prediction
from api.app.inference.recommendations import generate_recommendation
from api.app.inference.schemas import (
    HealthAssessment,
    InferenceResult,
    Recommendation,
)
from api.app.inference.service import InferenceService, get_inference_service

__all__ = [
    "HealthAssessment",
    "HealthEngine",
    "InferenceResult",
    "InferenceService",
    "ModelEngine",
    "Recommendation",
    "generate_recommendation",
    "get_inference_service",
    "get_model_engine",
    "persist_prediction",
]

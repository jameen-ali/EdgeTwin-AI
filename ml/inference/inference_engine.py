"""
EdgeTwin AI — ML Inference Engine
===================================
Simulates ONNX inference for machine health prediction.
In a real environment, this would load .onnx models and run inference.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
import random
import uuid

def calculate_health(temperature: float, vibration: float) -> float:
    # Baseline normal values
    normal_temp = 45.0
    normal_vib = 2.0
    
    # Simple penalty calculation
    temp_penalty = max(0, temperature - normal_temp) * 1.5
    vib_penalty = max(0, vibration - normal_vib) * 10.0
    
    health = 100.0 - temp_penalty - vib_penalty
    return max(0.0, min(100.0, health))

def predict_machine_health(machine_id: str, recent_readings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run prediction on the latest sensor readings.
    """
    if not recent_readings:
        # Default if no data
        return {
            "prediction_id": str(uuid.uuid4()),
            "machine_id": machine_id,
            "timestamp": datetime.now(timezone.utc),
            "health_score": 100.0,
            "risk_level": "low",
            "rul_hours": 2000.0,
            "failure_type": "None",
            "confidence": 0.95,
            "model_version": "v1.0.0-sim",
        }
        
    # Take the latest reading for simple simulation (could average over window)
    latest = recent_readings[0]
    temp = latest.get("temperature", 45.0)
    vib = latest.get("vibration", 2.0)
    
    health_score = calculate_health(temp, vib)
    
    # Determine risk level
    if health_score < 30:
        risk_level = "critical"
        rul = random.uniform(5, 48)
        failure_type = "Bearing Failure" if vib > 5 else "Overheating"
        confidence = random.uniform(0.85, 0.98)
    elif health_score < 60:
        risk_level = "high"
        rul = random.uniform(48, 168)
        failure_type = "Impending Component Wear"
        confidence = random.uniform(0.75, 0.85)
    elif health_score < 80:
        risk_level = "medium"
        rul = random.uniform(168, 720)
        failure_type = "Minor Degradation"
        confidence = random.uniform(0.65, 0.75)
    else:
        risk_level = "low"
        rul = random.uniform(720, 2000)
        failure_type = "None"
        confidence = random.uniform(0.9, 0.99)
        
    return {
        "prediction_id": str(uuid.uuid4()),
        "machine_id": machine_id,
        "timestamp": datetime.now(timezone.utc),
        "health_score": round(health_score, 1),
        "risk_level": risk_level,
        "rul_hours": round(rul, 1),
        "failure_type": failure_type,
        "confidence": round(confidence, 2),
        "model_version": "v1.0.0-sim",
    }

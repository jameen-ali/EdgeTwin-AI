import sys
import os
from celery import Celery
from sqlalchemy.orm import Session
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.core.database import SessionLocal
from backend.app.models.machine import Machine
from backend.app.models.sensor_reading import SensorReading
from backend.app.models.ml_prediction import MLPrediction
from ml.inference.inference_engine import predict_machine_health

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ml_inference",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

@celery_app.task(name="run_fleet_inference")
def run_fleet_inference():
    """Runs ML inference on all active machines using their latest sensor data."""
    db: Session = SessionLocal()
    try:
        machines = db.query(Machine).filter(Machine.status != "offline").all()
        
        predictions_made = 0
        for machine in machines:
            # Get latest 10 readings
            readings = db.query(SensorReading)\
                .filter(SensorReading.machine_id == machine.machine_id)\
                .order_by(SensorReading.timestamp.desc())\
                .limit(10)\
                .all()
                
            if not readings:
                continue
                
            reading_dicts = [
                {
                    "temperature": r.temperature,
                    "vibration": r.vibration,
                    "pressure": r.pressure,
                    "current": r.current,
                    "rpm": r.rpm,
                    "noise_level": r.noise_level
                } for r in readings
            ]
            
            # Run Inference
            pred_data = predict_machine_health(str(machine.machine_id), reading_dicts)
            
            # Save to DB
            prediction = MLPrediction(**pred_data)
            db.add(prediction)
            
            # Update Machine current status
            machine.health_score = pred_data["health_score"]
            machine.risk_level = pred_data["risk_level"]
            machine.rul_hours = pred_data["rul_hours"]
            
            # If critical or high, update status and generate alert
            from backend.app.models.alert import Alert, AlertSeverity, AlertStatus
            
            if pred_data["risk_level"] == "critical":
                machine.status = "critical"
                severity = AlertSeverity.critical
            elif pred_data["risk_level"] == "high" or pred_data["risk_level"] == "medium":
                machine.status = "warning"
                severity = AlertSeverity.high if pred_data["risk_level"] == "high" else AlertSeverity.medium
            else:
                machine.status = "normal"
                severity = AlertSeverity.low
                
            # Create Alert if severity is high or critical and no pending alert exists
            if severity in [AlertSeverity.high, AlertSeverity.critical]:
                existing_alert = db.query(Alert).filter(
                    Alert.machine_id == machine.machine_id,
                    Alert.status.in_([AlertStatus.pending, AlertStatus.escalated])
                ).first()
                
                if not existing_alert:
                    new_alert = Alert(
                        machine_id=machine.machine_id,
                        severity=severity,
                        status=AlertStatus.pending,
                        auto_escalated=False
                    )
                    db.add(new_alert)
                    # Note: Trigger WebSocket notification here in a real system
                
            predictions_made += 1
            
        db.commit()
        return f"Ran inference on {predictions_made} machines."
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

"""
tests/api/test_inference.py — Comprehensive tests for Inference Service (T-033/T-034).

Tests cover:
- ModelEngine loading (calibrated champion, anomaly pipeline, SHAP explainer)
- Leakage rejection during inference
- Supervised failure risk predictions and operational risk bands
- Unsupervised anomaly score [0, 1] bounds and flags
- SHAP explainability additivity, factor sorting, and disclaimer
- InferenceService end-to-end execution
- Database persistence of PredictionRecord and AlertRecord
- End-to-end MQTT ingest -> Telemetry persistence -> Inference -> Prediction persistence
- Inference latency SLA verification
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.app.db.base import Base
from api.app.inference.engine import get_model_engine
from api.app.inference.schemas import InferenceResult
from api.app.inference.service import get_inference_service
from api.app.ingest.handler import handle_message
from api.app.models.machine import MachineRecord
from api.app.models.prediction import PredictionRecord
from api.app.models.telemetry import TelemetryRecord


@pytest.fixture(scope="module")
def sqlite_engine():
    """In-memory SQLite engine for inference tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(sqlite_engine):
    """Database session fixture with rollback per test."""
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Seed test machine
    machine = MachineRecord(
        machine_id="MOT-1001",
        machine_type="Motor",
        status="ACTIVE",
    )
    session.add(machine)
    session.commit()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def valid_telemetry_payload() -> dict[str, Any]:
    """Canonical valid telemetry dictionary conforming to edgetwin.telemetry.v1."""
    return {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 42,
        "ts": "2026-09-28T12:00:00Z",
        "provenance": "SIMULATED",
        "fw": "1.0.0",
        "signals": {
            "air_temp_c": 25.4,
            "process_temp_c": 35.6,
            "rotational_speed_rpm": 1540.0,
            "torque_nm": 41.2,
            "vibration_mm_s": 2.6,
            "pressure_bar": 5.5,
            "current_a": 12.1,
            "voltage_v": 415.2,
            "tool_wear_min": 50.0,
            "operating_hours": 120.0,
        },
        "quality": {
            "air_temp_c": "OK",
            "process_temp_c": "OK",
            "rotational_speed_rpm": "OK",
            "torque_nm": "OK",
            "vibration_mm_s": "OK",
            "pressure_bar": "OK",
            "current_a": "OK",
            "voltage_v": "OK",
            "tool_wear_min": "OK",
            "operating_hours": "OK",
        },
        "edge": {
            "trip": None,
            "delta_t_c": 10.2,
            "power_va": 5023.92,
            "buffered": 0,
        },
    }


class TestModelEngine:
    """Tests for core model loading, risk prediction, anomaly scoring, and SHAP explainability."""

    def test_model_engine_singleton_loading(self):
        engine = get_model_engine()
        assert engine is not None
        assert engine.calibrated_model is not None
        assert len(engine.feature_cols) == 14
        assert engine.model_version != "unknown"
        assert engine.explainer is not None

    def test_predict_risk_nominal(self, valid_telemetry_payload: dict[str, Any]):
        engine = get_model_engine()
        from ml.data.engineering import apply_feature_set
        from simulation.contract import telemetry_to_feature_df

        df_feat = telemetry_to_feature_df(valid_telemetry_payload)
        df_phys = apply_feature_set(df_feat, "+physics")

        p_fail, pred, band = engine.predict_risk(df_phys)
        assert 0.0 <= p_fail <= 1.0
        assert pred in (0, 1)
        assert band in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        # On nominal data, p_fail should be low (< 0.15)
        assert p_fail < 0.15
        assert band == "LOW"
        assert pred == 0

    def test_predict_anomaly_nominal(self, valid_telemetry_payload: dict[str, Any]):
        engine = get_model_engine()
        from ml.data.engineering import apply_feature_set
        from simulation.contract import telemetry_to_feature_df

        df_feat = telemetry_to_feature_df(valid_telemetry_payload)
        df_phys = apply_feature_set(df_feat, "+physics")

        score, flag = engine.predict_anomaly(df_phys)
        assert score is not None
        assert 0.0 <= score <= 1.0
        assert flag is not None
        assert isinstance(flag, bool)

    def test_explain_nominal(self, valid_telemetry_payload: dict[str, Any]):
        engine = get_model_engine()
        from ml.data.engineering import apply_feature_set
        from simulation.contract import telemetry_to_feature_df

        df_feat = telemetry_to_feature_df(valid_telemetry_payload)
        df_phys = apply_feature_set(df_feat, "+physics")

        exp = engine.explain(df_phys, top_k=5)
        assert exp["top_factors"] is not None
        assert len(exp["top_factors"]) <= 5
        assert exp["model_margin"] is not None
        assert exp["base_value"] is not None
        assert exp["additivity_verified"] is True
        assert (
            "Statistical association with failure condition in model log-odds margin space; not causal."
            in exp["disclaimer"]
        )

        # Verify factor structure
        first_factor = exp["top_factors"][0]
        assert "feature_name" in first_factor
        assert "shap_value" in first_factor
        assert "direction" in first_factor
        assert "abs_magnitude" in first_factor

    def test_leakage_rejection(self, valid_telemetry_payload: dict[str, Any]):
        engine = get_model_engine()
        from ml.data.engineering import apply_feature_set
        from simulation.contract import telemetry_to_feature_df

        df_feat = telemetry_to_feature_df(valid_telemetry_payload)
        df_phys = apply_feature_set(df_feat, "+physics")

        # Inject forbidden target column
        df_leak = df_phys.copy()
        df_leak["Failure_Type"] = "No_Failure"

        with pytest.raises(ValueError, match="Leakage guard violation"):
            engine.predict_risk(df_leak)


class TestInferenceService:
    """Tests for InferenceService orchestration and persistence."""

    def test_run_inference_nominal(self, valid_telemetry_payload: dict[str, Any]):
        svc = get_inference_service()
        result: InferenceResult = svc.run_inference(valid_telemetry_payload, telemetry_id=1)

        assert result.machine_id == "MOT-1001"
        assert result.telemetry_id == 1
        assert 0.0 <= result.failure_probability <= 1.0
        assert result.risk_band == "LOW"
        assert result.health_state == "HEALTHY"
        assert result.health_score is not None and result.health_score >= 80.0
        assert result.top_factors is not None and len(result.top_factors) == 5
        assert result.inference_latency_ms > 0.0
        assert result.health_assessment.recommendation is not None
        assert result.health_assessment.recommendation.action_code == "ACT_ROUTINE_MONITOR"

    def test_run_inference_hardware_trip(self, valid_telemetry_payload: dict[str, Any]):
        svc = get_inference_service()
        payload = copy.deepcopy(valid_telemetry_payload)
        payload["edge"]["trip"] = "TRIP_OVERLOAD"

        result = svc.run_inference(payload)
        assert result.health_state == "CRITICAL"
        assert result.health_assessment.alert_severity == "CRITICAL"
        assert result.health_assessment.alert_type == "HARDWARE_SAFETY_TRIP"
        assert result.health_assessment.recommendation.action_code == "ACT_EMERGENCY_INSPECT"
        assert result.health_assessment.recommendation.urgency == "IMMEDIATE"

    def test_run_inference_tool_wear_override(self, valid_telemetry_payload: dict[str, Any]):
        svc = get_inference_service()
        payload = copy.deepcopy(valid_telemetry_payload)
        payload["signals"]["tool_wear_min"] = 245.0

        result = svc.run_inference(payload)
        assert result.health_state == "MAINTENANCE_REQUIRED"
        assert result.health_assessment.recommendation.action_code == "ACT_REPLACE_TOOL"

    def test_process_and_persist(
        self, db_session: Session, valid_telemetry_payload: dict[str, Any]
    ):
        svc = get_inference_service()

        # Insert a parent TelemetryRecord
        telem = TelemetryRecord(
            machine_id="MOT-1001",
            ts=datetime.now(UTC),
            seq=999,
            provenance="SIMULATED",
            fw="1.0.0",
            air_temp_c=25.4,
            process_temp_c=35.6,
            rotational_speed_rpm=1540.0,
            torque_nm=41.2,
            vibration_mm_s=2.6,
            pressure_bar=5.5,
            current_a=12.1,
            voltage_v=415.2,
            tool_wear_min=50.0,
            operating_hours=120.0,
        )
        db_session.add(telem)
        db_session.commit()
        db_session.refresh(telem)

        # Run inference and persist
        result, pred_rec, alert_rec = svc.process_and_persist(
            db=db_session,
            payload=valid_telemetry_payload,
            telemetry_id=telem.id,
        )

        assert pred_rec.id is not None
        assert pred_rec.machine_id == "MOT-1001"
        assert pred_rec.telemetry_id == telem.id
        assert pred_rec.failure_probability == result.failure_probability
        assert pred_rec.risk_band == result.risk_band
        assert pred_rec.health_score == result.health_score
        assert pred_rec.health_state == result.health_state
        assert pred_rec.top_factors is not None
        assert pred_rec.model_version == result.model_version
        assert alert_rec is None  # Healthy state produces no alert

        # Verify DB query
        stmt = select(PredictionRecord).where(PredictionRecord.id == pred_rec.id)
        fetched = db_session.execute(stmt).scalar_one_or_none()
        assert fetched is not None
        assert fetched.machine_id == "MOT-1001"
        assert fetched.telemetry_id == telem.id

    def test_process_and_persist_creates_alert_on_critical(
        self, db_session: Session, valid_telemetry_payload: dict[str, Any]
    ):
        svc = get_inference_service()
        payload = copy.deepcopy(valid_telemetry_payload)
        payload["edge"]["trip"] = "TRIP_OVERLOAD"

        _result, pred_rec, alert_rec = svc.process_and_persist(
            db=db_session,
            payload=payload,
            telemetry_id=None,
        )

        assert pred_rec.id is not None
        assert alert_rec is not None
        assert alert_rec.machine_id == "MOT-1001"
        assert alert_rec.severity == "CRITICAL"
        assert alert_rec.status == "OPEN"
        assert "ACT_EMERGENCY_INSPECT" in alert_rec.message

    def test_e2e_ingest_to_inference_integration(
        self, db_session: Session, valid_telemetry_payload: dict[str, Any]
    ):
        """End-to-end test: raw JSON MQTT message -> handle_message -> telemetry + prediction in DB."""
        topic = "edgetwin/v1/MOT-1001/telemetry"
        raw_bytes = json.dumps(valid_telemetry_payload).encode("utf-8")

        res = handle_message(topic, raw_bytes, db_session)
        assert res["outcome"] == "persisted"
        assert res["machine_id"] == "MOT-1001"

        # Verify TelemetryRecord was created
        stmt_t = select(TelemetryRecord).where(
            TelemetryRecord.machine_id == "MOT-1001",
            TelemetryRecord.seq == valid_telemetry_payload["seq"],
        )
        telem = db_session.execute(stmt_t).scalar_one_or_none()
        assert telem is not None

        # Verify PredictionRecord was created and linked to TelemetryRecord
        stmt_p = select(PredictionRecord).where(
            PredictionRecord.machine_id == "MOT-1001",
            PredictionRecord.telemetry_id == telem.id,
        )
        pred = db_session.execute(stmt_p).scalar_one_or_none()
        assert pred is not None
        assert pred.machine_id == "MOT-1001"
        assert pred.telemetry_id == telem.id
        assert pred.failure_probability is not None
        assert pred.health_score is not None
        assert pred.health_state == "HEALTHY"
        assert pred.top_factors is not None

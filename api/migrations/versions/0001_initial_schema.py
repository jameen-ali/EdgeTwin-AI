"""Initial database schema migration for EdgeTwin AI.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Machines table
    op.create_table(
        "machines",
        sa.Column("machine_id", sa.String(length=32), nullable=False),
        sa.Column("machine_type", sa.String(length=64), nullable=False),
        sa.Column("location", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="OFFLINE", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("machine_id"),
    )
    op.create_index("ix_machines_machine_id", "machines", ["machine_id"], unique=False)

    # 2. Telemetry table
    op.create_table(
        "telemetry",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("machine_id", sa.String(length=32), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.String(length=16), nullable=False),
        sa.Column("fw", sa.String(length=32), nullable=False),
        sa.Column("air_temp_c", sa.Float(), nullable=True),
        sa.Column("process_temp_c", sa.Float(), nullable=True),
        sa.Column("rotational_speed_rpm", sa.Float(), nullable=True),
        sa.Column("torque_nm", sa.Float(), nullable=True),
        sa.Column("vibration_mm_s", sa.Float(), nullable=True),
        sa.Column("pressure_bar", sa.Float(), nullable=True),
        sa.Column("current_a", sa.Float(), nullable=True),
        sa.Column("voltage_v", sa.Float(), nullable=True),
        sa.Column("tool_wear_min", sa.Float(), nullable=True),
        sa.Column("operating_hours", sa.Float(), nullable=True),
        sa.Column("quality", sa.JSON(), nullable=True),
        sa.Column("delta_t_c", sa.Float(), nullable=True),
        sa.Column("power_va", sa.Float(), nullable=True),
        sa.Column("trip", sa.String(length=64), nullable=True),
        sa.Column("buffered", sa.Integer(), server_default="0", nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.machine_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("machine_id", "seq", name="uq_telemetry_machine_seq"),
    )
    op.create_index("ix_telemetry_machine_id", "telemetry", ["machine_id"], unique=False)
    op.create_index("ix_telemetry_ts", "telemetry", ["ts"], unique=False)
    op.create_index("ix_telemetry_received_at", "telemetry", ["received_at"], unique=False)
    op.create_index(
        "ix_telemetry_machine_ts_desc",
        "telemetry",
        ["machine_id", sa.text("ts DESC")],
        unique=False,
    )

    # 3. Predictions table
    op.create_table(
        "predictions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("machine_id", sa.String(length=32), nullable=False),
        sa.Column("telemetry_id", sa.BigInteger(), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_probability", sa.Float(), nullable=False),
        sa.Column("failure_prediction", sa.Integer(), nullable=False),
        sa.Column("risk_band", sa.String(length=16), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("anomaly_flag", sa.Boolean(), nullable=True),
        sa.Column("health_score", sa.Float(), nullable=True),
        sa.Column("health_state", sa.String(length=32), nullable=True),
        sa.Column("top_factors", sa.JSON(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("inference_latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.machine_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["telemetry_id"], ["telemetry.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_machine_id", "predictions", ["machine_id"], unique=False)
    op.create_index("ix_predictions_telemetry_id", "predictions", ["telemetry_id"], unique=False)
    op.create_index("ix_predictions_ts", "predictions", ["ts"], unique=False)
    op.create_index(
        "ix_predictions_machine_ts_desc",
        "predictions",
        ["machine_id", sa.text("ts DESC")],
        unique=False,
    )

    # 4. Twin Snapshots table
    op.create_table(
        "twin_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("machine_id", sa.String(length=32), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_status", sa.String(length=16), nullable=False),
        sa.Column("operating_state", sa.String(length=32), nullable=False),
        sa.Column("health_state", sa.String(length=32), nullable=False),
        sa.Column("health_score", sa.Float(), nullable=False),
        sa.Column("risk_band", sa.String(length=16), nullable=False),
        sa.Column("failure_probability", sa.Float(), nullable=False),
        sa.Column("anomaly_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("snapshot_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.machine_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_twin_snapshots_machine_id", "twin_snapshots", ["machine_id"], unique=False)
    op.create_index("ix_twin_snapshots_ts", "twin_snapshots", ["ts"], unique=False)
    op.create_index(
        "ix_twin_snapshots_machine_ts_desc",
        "twin_snapshots",
        ["machine_id", sa.text("ts DESC")],
        unique=False,
    )

    # 5. Alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("machine_id", sa.String(length=32), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="OPEN", nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("trigger_conditions", sa.JSON(), nullable=True),
        sa.Column("top_factors", sa.JSON(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.machine_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_machine_id", "alerts", ["machine_id"], unique=False)
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"], unique=False)

    # 6. Feedback table
    op.create_table(
        "feedback",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("machine_id", sa.String(length=32), nullable=False),
        sa.Column("alert_id", sa.BigInteger(), nullable=True),
        sa.Column("feedback_type", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.machine_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_machine_id", "feedback", ["machine_id"], unique=False)
    op.create_index("ix_feedback_alert_id", "feedback", ["alert_id"], unique=False)

    # 7. Maintenance Events table
    op.create_table(
        "maintenance_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("machine_id", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="SCHEDULED", nullable=False),
        sa.Column("technician", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.machine_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maintenance_events_machine_id", "maintenance_events", ["machine_id"], unique=False
    )

    # 8. Model Versions table
    op.create_table(
        "model_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("alias", sa.String(length=32), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_name", "version", name="uq_model_name_version"),
    )


def downgrade() -> None:
    op.drop_table("model_versions")
    op.drop_table("maintenance_events")
    op.drop_table("feedback")
    op.drop_table("alerts")
    op.drop_table("twin_snapshots")
    op.drop_table("predictions")
    op.drop_table("telemetry")
    op.drop_table("machines")

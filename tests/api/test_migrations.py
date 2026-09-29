"""Tests for Alembic migration execution."""

import os
import tempfile

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_and_downgrade():
    """Verify Alembic migration creates all 8 tables and rolls back cleanly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "alembic_test.db")
        db_url = f"sqlite:///{db_path}"

        alembic_cfg = Config("api/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # 1. Run upgrade to head
        command.upgrade(alembic_cfg, "head")

        # 2. Inspect created database tables
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        expected_tables = {
            "machines",
            "telemetry",
            "predictions",
            "twin_snapshots",
            "alerts",
            "feedback",
            "maintenance_events",
            "model_versions",
            "users",
            "alembic_version",
        }
        assert expected_tables.issubset(tables)

        # 3. Check columns and indexes on telemetry and users table
        columns = {c["name"] for c in inspector.get_columns("telemetry")}
        assert "air_temp_c" in columns
        assert "vibration_mm_s" in columns
        assert "quality" in columns
        assert "delta_t_c" in columns
        assert "buffered" in columns

        user_columns = {c["name"] for c in inspector.get_columns("users")}
        assert "username" in user_columns
        assert "password_hash" in user_columns
        assert "role" in user_columns
        assert "is_active" in user_columns

        maint_columns = {c["name"] for c in inspector.get_columns("maintenance_events")}
        assert "alert_id" in maint_columns
        assert "event_type" in maint_columns
        assert "status" in maint_columns

        # 4. Run downgrade to base
        command.downgrade(alembic_cfg, "base")

        # 5. Verify tables dropped
        inspector_after = inspect(engine)
        tables_after = set(inspector_after.get_table_names())
        assert len(tables_after - {"alembic_version"}) == 0

        # 6. Re-upgrade to ensure idempotency
        command.upgrade(alembic_cfg, "head")
        tables_final = set(inspect(engine).get_table_names())
        assert expected_tables.issubset(tables_final)
        engine.dispose()

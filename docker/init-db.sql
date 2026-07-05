-- EdgeTwin AI — Database Initialization
-- Runs once when Docker Compose PostgreSQL container starts

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable pgcrypto for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- TimescaleDB hypertable for sensor_readings will be created
-- after tables are initialized via Alembic/SQLAlchemy create_all:
-- SELECT create_hypertable('sensor_readings', 'timestamp', if_not_exists => TRUE);

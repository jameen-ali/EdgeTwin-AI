# Multi-stage Dockerfile for EdgeTwin AI FastAPI Backend
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install -e .

# Copy application source code
COPY api/ ./api/
COPY docs/ ./docs/
COPY simulation/ ./simulation/
COPY ml/ ./ml/
COPY mlops/ ./mlops/

# Expose API port
EXPOSE 8000

# Default entrypoint runs uvicorn server
CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

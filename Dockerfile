# Multi-stage production-ready Dockerfile for EdgeTwin AI FastAPI Backend (T-063)
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
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -e .

# Copy application source code, operational artifacts, and scripts
COPY api/ ./api/
COPY docs/ ./docs/
COPY simulation/ ./simulation/
COPY ml/ ./ml/
COPY mlops/ ./mlops/
COPY artifacts/ ./artifacts/
COPY scripts/ ./scripts/

# Ensure scripts are executable
RUN chmod +x scripts/docker-entrypoint.sh

# Run as non-root user for security (Section 18)
RUN useradd -m -u 1000 edgetwin && \
    chown -R edgetwin:edgetwin /app
USER edgetwin

# Expose API port
EXPOSE 8000

# Container healthcheck using backend /health probe
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default entrypoint runs migrations and starts uvicorn
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]

"""Logging configuration and setup for EdgeTwin AI."""

import logging
import sys

from api.app.config import get_settings

# Sensitive field names to avoid logging in plain text
REDACTED_KEYS = {"password", "secret", "token", "key", "authorization", "credential"}


def setup_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    log_format = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(log_level)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if not settings.DB_ECHO else logging.INFO
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the standard name."""
    return logging.getLogger(name)

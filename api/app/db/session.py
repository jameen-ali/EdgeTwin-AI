"""Database engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from api.app.config import get_settings
from api.app.logging import get_logger

logger = get_logger(__name__)


def create_db_engine(db_url: str | None = None) -> Engine:
    """Create SQLAlchemy engine based on configuration."""
    settings = get_settings()
    url = db_url or settings.DATABASE_URL

    connect_args = {}
    engine_kwargs = {
        "echo": settings.DB_ECHO,
        "future": True,
    }

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        engine_kwargs["connect_args"] = connect_args
    else:
        engine_kwargs.update(
            {
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
                "pool_pre_ping": True,
            }
        )

    return create_engine(url, **engine_kwargs)


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection(db_engine: Engine | None = None) -> tuple[bool, str | None]:
    """Verify active database connectivity with a lightweight ping query."""
    eng = db_engine or engine
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except (SQLAlchemyError, OSError) as e:
        err_msg = str(e)
        logger.warning(f"Database connectivity check failed: {err_msg}")
        return False, err_msg

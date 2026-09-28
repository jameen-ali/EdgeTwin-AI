"""Tests for database engine creation, session management, and connectivity checks."""

import os
import tempfile

from sqlalchemy import text

from api.app.db.session import check_db_connection, create_db_engine, get_db


def test_create_sqlite_engine():
    """Verify engine creation with SQLite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite:///{db_path}"
        engine = create_db_engine(db_url)
        ok, err = check_db_connection(engine)
        assert ok is True
        assert err is None
        engine.dispose()


def test_check_db_connection_failure():
    """Verify check_db_connection properly reports failures."""
    # Invalid host and port that will immediately fail
    engine = create_db_engine("postgresql+psycopg2://invalid:invalid@127.0.0.1:59999/invalid")
    ok, err = check_db_connection(engine)
    assert ok is False
    assert err is not None


def test_get_db_session_lifecycle():
    """Verify get_db dependency yields a valid session and closes it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite:///{db_path}"
        engine = create_db_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE test_table (id INTEGER PRIMARY KEY)"))
            conn.commit()

        from sqlalchemy.orm import sessionmaker

        TestSessionLocal = sessionmaker(bind=engine)

        from unittest.mock import patch

        with patch("api.app.db.session.SessionLocal", TestSessionLocal):
            gen = get_db()
            session = next(gen)
            assert session is not None
            res = session.execute(text("SELECT 1")).scalar()
            assert res == 1

            try:
                next(gen)
            except StopIteration:
                pass
        engine.dispose()

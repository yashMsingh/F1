"""Shared pytest fixtures for database and schema tests."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
import app.db.models  # noqa: F401

project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")


def _is_postgres_reachable(url: str) -> bool:
    """Check if the configured PostgreSQL database is accessible."""
    try:
        eng = create_engine(url, connect_args={"connect_timeout": 2})
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def db_url() -> str:
    """Determine the active database URL (PostgreSQL if reachable, otherwise temporary SQLite)."""
    env_url = os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@localhost:5432/f1_race_intelligence")
    if _is_postgres_reachable(env_url):
        return env_url
    
    # Fallback to local SQLite file for testing
    temp_dir = tempfile.mkdtemp()
    sqlite_path = Path(temp_dir) / "test_f1.db"
    return f"sqlite:///{sqlite_path}"


@pytest.fixture(scope="session")
def engine(db_url):
    """Create a test database engine with foreign key enforcement."""
    eng = create_engine(db_url, echo=False)

    if db_url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # Create tables
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="function")
def migration_db_url() -> str:
    """Provide a completely isolated fresh DB URL for migration lifecycle tests."""
    temp_dir = tempfile.mkdtemp()
    sqlite_path = Path(temp_dir) / "migration_test_f1.db"
    return f"sqlite:///{sqlite_path}"


@pytest.fixture(scope="function")
def alembic_config(migration_db_url) -> Config:
    """Provide Alembic Config pointing to alembic.ini and the fresh migration DB."""
    ini_path = project_root / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", migration_db_url)
    return cfg


@pytest.fixture(scope="function")
def session(engine) -> Generator[Session, None, None]:
    """Provide a database session wrapped in a transaction with automatic rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    db_sess = SessionLocal()

    yield db_sess

    db_sess.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()

"""Shared pytest fixtures for database and schema tests."""

import os
import tempfile
from pathlib import Path
from typing import Generator, Optional

import pytest
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
import app.db.models  # noqa: F401

project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")

# Files designated as integration tests requiring live PostgreSQL database
INTEGRATION_FILES = {
    "test_longitudinal_analytics.py",
    "test_longitudinal_ten_rounds.py",
    "test_longitudinal_fifteen_rounds.py",
    "test_longitudinal_integration.py",
}


def pytest_configure(config):
    """Register custom markers for test categorization."""
    config.addinivalue_line("markers", "integration: integration tests requiring live PostgreSQL database")
    config.addinivalue_line("markers", "unit: isolated unit tests using SQLite")


def pytest_collection_modifyitems(config, items):
    """Automatically tag tests as integration or unit based on file name or explicit markers."""
    for item in items:
        fspath = getattr(item, "path", None) or Path(item.fspath)
        if fspath.name in INTEGRATION_FILES or item.get_closest_marker("integration"):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)


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
def sqlite_db_url() -> str:
    """Isolated temporary SQLite database file for unit tests."""
    temp_dir = tempfile.mkdtemp()
    sqlite_path = Path(temp_dir) / "test_f1.db"
    return f"sqlite:///{sqlite_path}"


@pytest.fixture(scope="session")
def postgres_db_url() -> str:
    """PostgreSQL database URL from environment or default local config."""
    return os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@localhost:5432/f1_race_intelligence")


@pytest.fixture(scope="session")
def db_url(sqlite_db_url) -> str:
    """Default database URL for unit testing (isolated SQLite)."""
    return sqlite_db_url


@pytest.fixture(scope="session")
def engine(sqlite_db_url) -> Engine:
    """Create isolated SQLite engine for unit tests with foreign key enforcement and pre-created schema."""
    eng = create_engine(sqlite_db_url, echo=False)

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Pre-create all schema tables in isolated SQLite database
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="session")
def postgres_engine(postgres_db_url) -> Optional[Engine]:
    """Create PostgreSQL engine for integration tests if database is reachable, else None."""
    if _is_postgres_reachable(postgres_db_url):
        return create_engine(postgres_db_url, echo=False)
    return None


@pytest.fixture(scope="function")
def sqlite_session(engine) -> Generator[Session, None, None]:
    """Provide an isolated unit-test database session with automatic transaction rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    db_sess = SessionLocal()

    try:
        yield db_sess
    finally:
        db_sess.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def postgres_session(postgres_engine) -> Generator[Session, None, None]:
    """Provide a PostgreSQL database session for integration tests wrapped in a transaction with automatic rollback."""
    if postgres_engine is None:
        pytest.skip("Integration test requires reachable PostgreSQL database")

    connection = postgres_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    db_sess = SessionLocal()

    try:
        yield db_sess
    finally:
        db_sess.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def session(request, engine, postgres_engine) -> Generator[Session, None, None]:
    """Provide a database session.

    Routes to:
    - PostgreSQL session for tests marked with 'integration' or in longitudinal suites.
    - Isolated SQLite session for unit tests.
    Both sessions use transaction rollback to ensure zero side-effects or test cross-contamination.
    """
    is_integration = request.node.get_closest_marker("integration") is not None
    active_engine = postgres_engine if is_integration else engine

    if is_integration and active_engine is None:
        pytest.skip("Integration test requires reachable PostgreSQL database")

    connection = active_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    db_sess = SessionLocal()

    try:
        yield db_sess
    finally:
        db_sess.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


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

"""Database session and engine configuration.

Reads DATABASE_URL from environment variables (or .env file via python-dotenv).
Never hardcodes credentials.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env from project root if it exists
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")


def get_database_url() -> str:
    """Return the database URL from environment, or raise if missing."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Copy .env.example to .env and configure your database."
        )
    return url


def get_engine(echo: bool = False):
    """Create a SQLAlchemy engine from the configured DATABASE_URL."""
    return create_engine(get_database_url(), echo=echo)


def get_session_factory(engine=None):
    """Create a sessionmaker bound to the given (or default) engine."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)

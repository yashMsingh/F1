"""Dependency injection for FastAPI routes."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import get_session_factory


def get_db() -> Generator[Session, None, None]:
    """Provide a database session per request, ensuring cleanup."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

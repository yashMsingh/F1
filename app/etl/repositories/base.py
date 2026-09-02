"""F1 Race Intelligence — Base repository class and value comparison helpers."""

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session


def values_equal(a: Any, b: Any) -> bool:
    """Compare two field values for semantic equality to detect real mutations.

    Handles:
      - None vs None (equal)
      - Decimal vs int / Decimal / float with numeric equivalency (e.g. 26.00 == 26)
      - Strings, dates, times, ints
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False

    # Handle numeric comparisons between Decimal, float, int
    if isinstance(a, (Decimal, int, float)) and isinstance(b, (Decimal, int, float)):
        try:
            return Decimal(str(a)) == Decimal(str(b))
        except (InvalidOperation, ValueError):
            return a == b

    return a == b


class BaseRepository:
    """Abstract base repository providing common session operations."""

    def __init__(self, session: Session):
        self.session = session

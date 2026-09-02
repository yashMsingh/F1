"""F1 Race Intelligence — Parsing layer exceptions."""

from typing import Optional

from app.f1.exceptions import F1APIError


class F1ParsingError(F1APIError):
    """Base exception for all parsing and transformation errors."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[str] = None):
        super().__init__(message)
        self.field = field
        self.value = value


class F1ValidationError(F1ParsingError):
    """Raised when a parsed value fails domain validation rules."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[str] = None):
        super().__init__(message, field=field, value=value)


class F1TimeParsingError(F1ParsingError):
    """Raised when a time/duration string cannot be parsed to milliseconds."""

    def __init__(self, message: str, raw_value: Optional[str] = None):
        super().__init__(message, field="time", value=raw_value)
        self.raw_value = raw_value


class F1StructureError(F1ParsingError):
    """Raised when an expected response structure (table, key) is missing."""

    def __init__(self, message: str, expected_key: Optional[str] = None):
        super().__init__(message, field=expected_key)
        self.expected_key = expected_key

"""F1 Race Intelligence — ETL and persistence layer exceptions."""

from typing import Optional

from app.f1.exceptions import F1APIError


class F1ETLError(F1APIError):
    """Base exception for all ETL and persistence errors."""

    def __init__(
        self,
        message: str,
        entity_type: Optional[str] = None,
        record_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.entity_type = entity_type
        self.record_id = record_id


class F1PersistenceError(F1ETLError):
    """Raised when a database flush, insert, or update operation fails."""

    def __init__(
        self,
        message: str,
        entity_type: Optional[str] = None,
        record_id: Optional[str] = None,
    ):
        super().__init__(message, entity_type=entity_type, record_id=record_id)


class F1DependencyError(F1PersistenceError):
    """Raised when a required parent entity (foreign key target) does not exist."""

    def __init__(
        self,
        message: str,
        entity_type: Optional[str] = None,
        missing_entity: Optional[str] = None,
        missing_id: Optional[str] = None,
    ):
        super().__init__(message, entity_type=entity_type, record_id=missing_id)
        self.missing_entity = missing_entity
        self.missing_id = missing_id


class F1TransactionError(F1ETLError):
    """Raised when an explicit transaction boundary encounters an unrecoverable failure."""

    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message)
        self.operation = operation

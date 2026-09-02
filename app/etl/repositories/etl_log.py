"""F1 Race Intelligence — EtlLog repository."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.db.models.etl_log import EtlLog
from app.etl.repositories.base import BaseRepository
from app.etl.types import IngestionStats, IngestionStatus


def _utcnow() -> datetime:
    """Return naive UTC timestamp consistent with SQLAlchemy DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EtlLogRepository(BaseRepository):
    """Repository managing ETL run audit logging."""

    def get_by_id(self, log_id: int) -> Optional[EtlLog]:
        """Retrieve an EtlLog record by its primary key ID."""
        return self.session.get(EtlLog, log_id)

    def start_run(
        self,
        source: str,
        entity_type: str,
        season_year: Optional[int] = None,
        round_num: Optional[int] = None,
        endpoint: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> EtlLog:
        """Create and flush an initial EtlLog record with RUNNING status."""
        entry = EtlLog(
            source=source,
            entity_type=entity_type,
            season_year=season_year,
            round=round_num,
            endpoint=endpoint,
            source_url=source_url,
            status=IngestionStatus.RUNNING.value,
            records_processed=0,
            records_inserted=0,
            records_updated=0,
            records_skipped=0,
            started_at=_utcnow(),
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def complete_run(
        self,
        log_id: int,
        stats: IngestionStats,
        status: IngestionStatus = IngestionStatus.SUCCESS,
        error_message: Optional[str] = None,
    ) -> EtlLog:
        """Update an existing EtlLog entry with completion metrics and final status."""
        entry = self.get_by_id(log_id)
        if entry is None:
            raise ValueError(f"EtlLog with ID {log_id} not found.")

        entry.status = status.value
        entry.records_processed = stats.records_processed
        entry.records_inserted = stats.records_inserted
        entry.records_updated = stats.records_updated
        entry.records_skipped = stats.records_skipped
        entry.error_message = error_message
        entry.completed_at = _utcnow()
        self.session.flush()
        return entry

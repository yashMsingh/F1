"""F1 Race Intelligence — ETL result types and operational statistics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IngestionStatus(str, Enum):
    """Lifecycle status states for an ETL ingestion run."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(slots=True)
class IngestionStats:
    """Operational statistics tracking record counts for an ingestion operation."""

    entity_type: str = ""
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0

    def merge(self, other: IngestionStats) -> IngestionStats:
        """Combine counts from another IngestionStats instance into a new instance."""
        entities = [e for e in [self.entity_type, other.entity_type] if e]
        merged_entity = ",".join(entities) if entities else "composite"
        return IngestionStats(
            entity_type=merged_entity,
            records_processed=self.records_processed + other.records_processed,
            records_inserted=self.records_inserted + other.records_inserted,
            records_updated=self.records_updated + other.records_updated,
            records_skipped=self.records_skipped + other.records_skipped,
            records_failed=self.records_failed + other.records_failed,
        )


@dataclass(slots=True)
class IngestionResult:
    """Overall outcome of an ETL service operation including run metadata."""

    status: IngestionStatus
    stats: IngestionStats = field(default_factory=IngestionStats)
    error_message: Optional[str] = None
    log_id: Optional[int] = None
    season_year: Optional[int] = None
    round: Optional[int] = None

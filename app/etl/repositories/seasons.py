"""F1 Race Intelligence — Season repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.season import Season
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedSeason


class SeasonRepository(BaseRepository):
    """Repository managing Season entities."""

    def get_by_year(self, year: int) -> Optional[Season]:
        """Retrieve a Season by its primary key year."""
        stmt = select(Season).where(Season.season_year == year)
        return self.session.scalars(stmt).first()

    def upsert(self, item: ParsedSeason) -> tuple[Season, str]:
        """Idempotently insert or update a single Season record."""
        existing = self.get_by_year(item.year)
        if existing is None:
            season = Season(season_year=item.year, url=item.url)
            self.session.add(season)
            return season, "inserted"

        # Check for mutation in mutable fields
        if not values_equal(existing.url, item.url):
            existing.url = item.url
            return existing, "updated"

        return existing, "skipped"

    def upsert_many(self, items: Sequence[ParsedSeason]) -> IngestionStats:
        """Idempotently persist a batch of ParsedSeason records."""
        stats = IngestionStats(entity_type="seasons", records_processed=len(items))
        for item in items:
            _, action = self.upsert(item)
            if action == "inserted":
                stats.records_inserted += 1
            elif action == "updated":
                stats.records_updated += 1
            elif action == "skipped":
                stats.records_skipped += 1
        return stats

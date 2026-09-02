"""F1 Race Intelligence — Constructor repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.constructor import Constructor
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedConstructor


class ConstructorRepository(BaseRepository):
    """Repository managing Constructor entities."""

    def get_by_slug(self, constructor_id: str) -> Optional[Constructor]:
        """Look up a constructor by its unique Jolpica API slug."""
        stmt = select(Constructor).where(Constructor.constructor_id == constructor_id)
        return self.session.scalars(stmt).first()

    def get_by_id(self, internal_id: int) -> Optional[Constructor]:
        """Look up a constructor by its surrogate integer primary key."""
        return self.session.get(Constructor, internal_id)

    def upsert(self, item: ParsedConstructor) -> tuple[Constructor, str]:
        """Idempotently insert or update a single Constructor record."""
        existing = self.get_by_slug(item.constructor_id)
        if existing is None:
            constructor = Constructor(
                constructor_id=item.constructor_id,
                name=item.name,
                nationality=item.nationality,
                url=item.url,
            )
            self.session.add(constructor)
            return constructor, "inserted"

        # Check for mutations
        updated = False
        if not values_equal(existing.name, item.name):
            existing.name = item.name
            updated = True
        if not values_equal(existing.nationality, item.nationality):
            existing.nationality = item.nationality
            updated = True
        if not values_equal(existing.url, item.url):
            existing.url = item.url
            updated = True

        return existing, ("updated" if updated else "skipped")

    def upsert_many(self, items: Sequence[ParsedConstructor]) -> IngestionStats:
        """Idempotently persist a batch of ParsedConstructor records."""
        stats = IngestionStats(entity_type="constructors", records_processed=len(items))
        for item in items:
            _, action = self.upsert(item)
            if action == "inserted":
                stats.records_inserted += 1
            elif action == "updated":
                stats.records_updated += 1
            elif action == "skipped":
                stats.records_skipped += 1
        return stats

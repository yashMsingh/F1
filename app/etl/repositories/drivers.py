"""F1 Race Intelligence — Driver repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.driver import Driver
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedDriver


class DriverRepository(BaseRepository):
    """Repository managing Driver entities."""

    def get_by_slug(self, driver_id: str) -> Optional[Driver]:
        """Look up a driver by their unique Jolpica API slug."""
        stmt = select(Driver).where(Driver.driver_id == driver_id)
        return self.session.scalars(stmt).first()

    def get_by_id(self, internal_id: int) -> Optional[Driver]:
        """Look up a driver by their surrogate integer primary key."""
        return self.session.get(Driver, internal_id)

    def upsert(self, item: ParsedDriver) -> tuple[Driver, str]:
        """Idempotently insert or update a single Driver record."""
        existing = self.get_by_slug(item.driver_id)
        if existing is None:
            driver = Driver(
                driver_id=item.driver_id,
                permanent_number=item.permanent_number,
                code=item.code,
                given_name=item.given_name,
                family_name=item.family_name,
                date_of_birth=item.date_of_birth,
                nationality=item.nationality,
                url=item.url,
            )
            self.session.add(driver)
            return driver, "inserted"

        # Check for mutations
        updated = False
        if not values_equal(existing.given_name, item.given_name):
            existing.given_name = item.given_name
            updated = True
        if not values_equal(existing.family_name, item.family_name):
            existing.family_name = item.family_name
            updated = True
        if not values_equal(existing.permanent_number, item.permanent_number):
            existing.permanent_number = item.permanent_number
            updated = True
        if not values_equal(existing.code, item.code):
            existing.code = item.code
            updated = True
        if not values_equal(existing.date_of_birth, item.date_of_birth):
            existing.date_of_birth = item.date_of_birth
            updated = True
        if not values_equal(existing.nationality, item.nationality):
            existing.nationality = item.nationality
            updated = True
        if not values_equal(existing.url, item.url):
            existing.url = item.url
            updated = True

        return existing, ("updated" if updated else "skipped")

    def upsert_many(self, items: Sequence[ParsedDriver]) -> IngestionStats:
        """Idempotently persist a batch of ParsedDriver records."""
        stats = IngestionStats(entity_type="drivers", records_processed=len(items))
        for item in items:
            _, action = self.upsert(item)
            if action == "inserted":
                stats.records_inserted += 1
            elif action == "updated":
                stats.records_updated += 1
            elif action == "skipped":
                stats.records_skipped += 1
        return stats

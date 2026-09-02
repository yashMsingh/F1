"""F1 Race Intelligence — DriverStanding repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.driver import Driver
from app.db.models.driver_standing import DriverStanding
from app.db.models.season import Season
from app.etl.exceptions import F1DependencyError
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedDriverStanding


class DriverStandingRepository(BaseRepository):
    """Repository managing DriverStanding entities."""

    def get_by_key(self, season_year: int, round_num: int, driver_id: int) -> Optional[DriverStanding]:
        """Look up a standing by unique composite key (season_year, round, driver_id)."""
        stmt = select(DriverStanding).where(
            DriverStanding.season_year == season_year,
            DriverStanding.round == round_num,
            DriverStanding.driver_id == driver_id,
        )
        return self.session.scalars(stmt).first()

    def _resolve_driver_id(self, slug: str) -> int:
        stmt = select(Driver.id).where(Driver.driver_id == slug)
        driver_id = self.session.scalars(stmt).first()
        if driver_id is None:
            raise F1DependencyError(
                f"Driver slug '{slug}' not found in database.",
                entity_type="driver_standings",
                missing_entity="drivers",
                missing_id=slug,
            )
        return driver_id

    def _verify_season(self, year: int) -> None:
        stmt = select(Season.season_year).where(Season.season_year == year)
        if self.session.scalars(stmt).first() is None:
            raise F1DependencyError(
                f"Season '{year}' not found in database for driver standings.",
                entity_type="driver_standings",
                missing_entity="seasons",
                missing_id=str(year),
            )

    def upsert(
        self,
        item: ParsedDriverStanding,
        driver_cache: Optional[dict[str, int]] = None,
    ) -> tuple[DriverStanding, str]:
        """Idempotently insert or update a single DriverStanding record."""
        self._verify_season(item.season)

        if driver_cache is not None and item.driver_id in driver_cache:
            d_id = driver_cache[item.driver_id]
        else:
            d_id = self._resolve_driver_id(item.driver_id)
            if driver_cache is not None:
                driver_cache[item.driver_id] = d_id

        existing = self.get_by_key(item.season, item.round, d_id)
        if existing is None:
            standing = DriverStanding(
                season_year=item.season,
                round=item.round,
                driver_id=d_id,
                position=item.position,
                points=item.points,
                wins=item.wins,
            )
            self.session.add(standing)
            return standing, "inserted"

        # Check for mutations
        updated = False
        if not values_equal(existing.position, item.position):
            existing.position = item.position
            updated = True
        if not values_equal(existing.points, item.points):
            existing.points = item.points
            updated = True
        if not values_equal(existing.wins, item.wins):
            existing.wins = item.wins
            updated = True

        return existing, ("updated" if updated else "skipped")

    def upsert_many(self, items: Sequence[ParsedDriverStanding]) -> IngestionStats:
        """Idempotently persist a batch of ParsedDriverStanding records."""
        stats = IngestionStats(entity_type="driver_standings", records_processed=len(items))
        driver_cache: dict[str, int] = {}
        for item in items:
            _, action = self.upsert(item, driver_cache=driver_cache)
            if action == "inserted":
                stats.records_inserted += 1
            elif action == "updated":
                stats.records_updated += 1
            elif action == "skipped":
                stats.records_skipped += 1
        return stats

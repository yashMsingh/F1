"""F1 Race Intelligence — LapTime repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.driver import Driver
from app.db.models.lap_time import LapTime
from app.db.models.race import Race
from app.etl.exceptions import F1DependencyError
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedLapTime


class LapTimeRepository(BaseRepository):
    """Repository managing LapTime entities."""

    def get_by_key(self, race_id: int, driver_id: int, lap_number: int) -> Optional[LapTime]:
        """Look up a lap time by its composite key (race_id, driver_id, lap_number)."""
        stmt = select(LapTime).where(
            LapTime.race_id == race_id,
            LapTime.driver_id == driver_id,
            LapTime.lap_number == lap_number,
        )
        return self.session.scalars(stmt).first()

    def _resolve_race_id(self, season: int, round_num: int) -> int:
        stmt = select(Race.id).where(Race.season_year == season, Race.round == round_num)
        race_id = self.session.scalars(stmt).first()
        if race_id is None:
            raise F1DependencyError(
                f"Race not found for season {season}, round {round_num}.",
                entity_type="lap_times",
                missing_entity="races",
                missing_id=f"{season}/{round_num}",
            )
        return race_id

    def _resolve_driver_id(self, slug: str) -> int:
        stmt = select(Driver.id).where(Driver.driver_id == slug)
        driver_id = self.session.scalars(stmt).first()
        if driver_id is None:
            raise F1DependencyError(
                f"Driver slug '{slug}' not found in database.",
                entity_type="lap_times",
                missing_entity="drivers",
                missing_id=slug,
            )
        return driver_id

    def upsert(
        self,
        item: ParsedLapTime,
        race_id: Optional[int] = None,
        driver_cache: Optional[dict[str, int]] = None,
    ) -> tuple[LapTime, str]:
        """Idempotently insert or update a single LapTime record."""
        r_id = race_id if race_id is not None else self._resolve_race_id(item.season, item.round)

        if driver_cache is not None and item.driver_id in driver_cache:
            d_id = driver_cache[item.driver_id]
        else:
            d_id = self._resolve_driver_id(item.driver_id)
            if driver_cache is not None:
                driver_cache[item.driver_id] = d_id

        existing = self.get_by_key(r_id, d_id, item.lap_number)
        if existing is None:
            lap_time = LapTime(
                race_id=r_id,
                driver_id=d_id,
                lap_number=item.lap_number,
                position=item.position,
                time=item.time or "",
                time_millis=item.time_millis,
            )
            self.session.add(lap_time)
            return lap_time, "inserted"

        # Check for mutations
        updated = False
        if not values_equal(existing.position, item.position):
            existing.position = item.position
            updated = True
        if item.time and not values_equal(existing.time, item.time):
            existing.time = item.time
            updated = True
        if not values_equal(existing.time_millis, item.time_millis):
            existing.time_millis = item.time_millis
            updated = True

        return existing, ("updated" if updated else "skipped")

    def upsert_many(self, items: Sequence[ParsedLapTime]) -> IngestionStats:
        """Idempotently persist a batch of ParsedLapTime records."""
        stats = IngestionStats(entity_type="lap_times", records_processed=len(items))
        if not items:
            return stats

        driver_cache: dict[str, int] = {}
        first = items[0]
        same_event = all(i.season == first.season and i.round == first.round for i in items)
        common_race_id = self._resolve_race_id(first.season, first.round) if same_event else None

        for item in items:
            race_id = common_race_id if common_race_id is not None else None
            _, action = self.upsert(item, race_id=race_id, driver_cache=driver_cache)
            if action == "inserted":
                stats.records_inserted += 1
            elif action == "updated":
                stats.records_updated += 1
            elif action == "skipped":
                stats.records_skipped += 1
        return stats

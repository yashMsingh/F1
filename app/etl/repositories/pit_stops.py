"""F1 Race Intelligence — PitStop repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.driver import Driver
from app.db.models.pit_stop import PitStop
from app.db.models.race import Race
from app.etl.exceptions import F1DependencyError
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedPitStop


class PitStopRepository(BaseRepository):
    """Repository managing PitStop entities."""

    def get_by_key(self, race_id: int, driver_id: int, stop_number: int) -> Optional[PitStop]:
        """Look up a pit stop by its composite key (race_id, driver_id, stop_number)."""
        stmt = select(PitStop).where(
            PitStop.race_id == race_id,
            PitStop.driver_id == driver_id,
            PitStop.stop_number == stop_number,
        )
        return self.session.scalars(stmt).first()

    def _resolve_race_id(self, season: int, round_num: int) -> int:
        stmt = select(Race.id).where(Race.season_year == season, Race.round == round_num)
        race_id = self.session.scalars(stmt).first()
        if race_id is None:
            raise F1DependencyError(
                f"Race not found for season {season}, round {round_num}.",
                entity_type="pit_stops",
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
                entity_type="pit_stops",
                missing_entity="drivers",
                missing_id=slug,
            )
        return driver_id

    def upsert(
        self,
        item: ParsedPitStop,
        race_id: Optional[int] = None,
        driver_cache: Optional[dict[str, int]] = None,
    ) -> tuple[PitStop, str]:
        """Idempotently insert or update a single PitStop record."""
        r_id = race_id if race_id is not None else self._resolve_race_id(item.season, item.round)

        if driver_cache is not None and item.driver_id in driver_cache:
            d_id = driver_cache[item.driver_id]
        else:
            d_id = self._resolve_driver_id(item.driver_id)
            if driver_cache is not None:
                driver_cache[item.driver_id] = d_id

        existing = self.get_by_key(r_id, d_id, item.stop_number)
        if existing is None:
            pit_stop = PitStop(
                race_id=r_id,
                driver_id=d_id,
                stop_number=item.stop_number,
                lap=item.lap,
                time_of_day=item.time_of_day,
                duration_text=item.duration_text,
                duration_millis=item.duration_millis,
            )
            self.session.add(pit_stop)
            return pit_stop, "inserted"

        # Check for mutations
        updated = False
        if not values_equal(existing.lap, item.lap):
            existing.lap = item.lap
            updated = True
        if not values_equal(existing.time_of_day, item.time_of_day):
            existing.time_of_day = item.time_of_day
            updated = True
        if not values_equal(existing.duration_text, item.duration_text):
            existing.duration_text = item.duration_text
            updated = True
        if not values_equal(existing.duration_millis, item.duration_millis):
            existing.duration_millis = item.duration_millis
            updated = True

        return existing, ("updated" if updated else "skipped")

    def upsert_many(self, items: Sequence[ParsedPitStop]) -> IngestionStats:
        """Idempotently persist a batch of ParsedPitStop records."""
        stats = IngestionStats(entity_type="pit_stops", records_processed=len(items))
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

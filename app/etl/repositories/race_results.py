"""F1 Race Intelligence — RaceResult repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.race import Race
from app.db.models.race_result import RaceResult
from app.etl.exceptions import F1DependencyError
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedRaceResult


class RaceResultRepository(BaseRepository):
    """Repository managing RaceResult entities with dependency resolution and caching."""

    def get_by_race_and_driver(self, race_id: int, driver_id: int) -> Optional[RaceResult]:
        """Look up a race result by its unique composite key (race_id, driver_id)."""
        stmt = select(RaceResult).where(
            RaceResult.race_id == race_id,
            RaceResult.driver_id == driver_id,
        )
        return self.session.scalars(stmt).first()

    def _resolve_race_id(self, season: int, round_num: int) -> int:
        stmt = select(Race.id).where(Race.season_year == season, Race.round == round_num)
        race_id = self.session.scalars(stmt).first()
        if race_id is None:
            raise F1DependencyError(
                f"Race not found for season {season}, round {round_num}.",
                entity_type="race_results",
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
                entity_type="race_results",
                missing_entity="drivers",
                missing_id=slug,
            )
        return driver_id

    def _resolve_constructor_id(self, slug: str) -> int:
        stmt = select(Constructor.id).where(Constructor.constructor_id == slug)
        constructor_id = self.session.scalars(stmt).first()
        if constructor_id is None:
            raise F1DependencyError(
                f"Constructor slug '{slug}' not found in database.",
                entity_type="race_results",
                missing_entity="constructors",
                missing_id=slug,
            )
        return constructor_id

    def upsert(
        self,
        item: ParsedRaceResult,
        race_id: Optional[int] = None,
        driver_cache: Optional[dict[str, int]] = None,
        constructor_cache: Optional[dict[str, int]] = None,
    ) -> tuple[RaceResult, str]:
        """Idempotently insert or update a single RaceResult record."""
        # Resolve foreign keys
        r_id = race_id if race_id is not None else self._resolve_race_id(item.season, item.round)

        if driver_cache is not None and item.driver_id in driver_cache:
            d_id = driver_cache[item.driver_id]
        else:
            d_id = self._resolve_driver_id(item.driver_id)
            if driver_cache is not None:
                driver_cache[item.driver_id] = d_id

        if constructor_cache is not None and item.constructor_id in constructor_cache:
            c_id = constructor_cache[item.constructor_id]
        else:
            c_id = self._resolve_constructor_id(item.constructor_id)
            if constructor_cache is not None:
                constructor_cache[item.constructor_id] = c_id

        existing = self.get_by_race_and_driver(r_id, d_id)
        if existing is None:
            result = RaceResult(
                race_id=r_id,
                driver_id=d_id,
                constructor_id=c_id,
                car_number=item.car_number,
                grid_position=item.grid_position,
                source_position=item.source_position,
                position_text=item.position_text,
                points=item.points,
                laps_completed=item.laps_completed,
                status=item.status,
                time_millis=item.time_millis,
                time_text=item.time_text,
                fastest_lap_rank=item.fastest_lap_rank,
                fastest_lap_number=item.fastest_lap_number,
                fastest_lap_time=item.fastest_lap_time,
                fastest_lap_time_millis=item.fastest_lap_time_millis,
            )
            self.session.add(result)
            return result, "inserted"

        # Check for mutations
        updated = False
        if existing.constructor_id != c_id:
            existing.constructor_id = c_id
            updated = True
        if not values_equal(existing.car_number, item.car_number):
            existing.car_number = item.car_number
            updated = True
        if not values_equal(existing.grid_position, item.grid_position):
            existing.grid_position = item.grid_position
            updated = True
        if not values_equal(existing.source_position, item.source_position):
            existing.source_position = item.source_position
            updated = True
        if not values_equal(existing.position_text, item.position_text):
            existing.position_text = item.position_text
            updated = True
        if not values_equal(existing.points, item.points):
            existing.points = item.points
            updated = True
        if not values_equal(existing.laps_completed, item.laps_completed):
            existing.laps_completed = item.laps_completed
            updated = True
        if not values_equal(existing.status, item.status):
            existing.status = item.status
            updated = True
        if not values_equal(existing.time_millis, item.time_millis):
            existing.time_millis = item.time_millis
            updated = True
        if not values_equal(existing.time_text, item.time_text):
            existing.time_text = item.time_text
            updated = True
        if not values_equal(existing.fastest_lap_rank, item.fastest_lap_rank):
            existing.fastest_lap_rank = item.fastest_lap_rank
            updated = True
        if not values_equal(existing.fastest_lap_number, item.fastest_lap_number):
            existing.fastest_lap_number = item.fastest_lap_number
            updated = True
        if not values_equal(existing.fastest_lap_time, item.fastest_lap_time):
            existing.fastest_lap_time = item.fastest_lap_time
            updated = True
        if not values_equal(existing.fastest_lap_time_millis, item.fastest_lap_time_millis):
            existing.fastest_lap_time_millis = item.fastest_lap_time_millis
            updated = True

        return existing, ("updated" if updated else "skipped")

    def upsert_many(self, items: Sequence[ParsedRaceResult]) -> IngestionStats:
        """Idempotently persist a batch of ParsedRaceResult records."""
        stats = IngestionStats(entity_type="race_results", records_processed=len(items))
        if not items:
            return stats

        driver_cache: dict[str, int] = {}
        constructor_cache: dict[str, int] = {}

        # Resolve race_id once if all results are from the same event
        first = items[0]
        same_event = all(i.season == first.season and i.round == first.round for i in items)
        common_race_id = self._resolve_race_id(first.season, first.round) if same_event else None

        for item in items:
            race_id = common_race_id if common_race_id is not None else None
            _, action = self.upsert(
                item,
                race_id=race_id,
                driver_cache=driver_cache,
                constructor_cache=constructor_cache,
            )
            if action == "inserted":
                stats.records_inserted += 1
            elif action == "updated":
                stats.records_updated += 1
            elif action == "skipped":
                stats.records_skipped += 1
        return stats

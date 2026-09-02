"""F1 Race Intelligence — QualifyingResult repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.qualifying_result import QualifyingResult
from app.db.models.race import Race
from app.etl.exceptions import F1DependencyError
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedQualifyingResult


class QualifyingResultRepository(BaseRepository):
    """Repository managing QualifyingResult entities."""

    def get_by_race_and_driver(self, race_id: int, driver_id: int) -> Optional[QualifyingResult]:
        """Look up a qualifying result by composite key (race_id, driver_id)."""
        stmt = select(QualifyingResult).where(
            QualifyingResult.race_id == race_id,
            QualifyingResult.driver_id == driver_id,
        )
        return self.session.scalars(stmt).first()

    def _resolve_race_id(self, season: int, round_num: int) -> int:
        stmt = select(Race.id).where(Race.season_year == season, Race.round == round_num)
        race_id = self.session.scalars(stmt).first()
        if race_id is None:
            raise F1DependencyError(
                f"Race not found for season {season}, round {round_num}.",
                entity_type="qualifying_results",
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
                entity_type="qualifying_results",
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
                entity_type="qualifying_results",
                missing_entity="constructors",
                missing_id=slug,
            )
        return constructor_id

    def upsert(
        self,
        item: ParsedQualifyingResult,
        race_id: Optional[int] = None,
        driver_cache: Optional[dict[str, int]] = None,
        constructor_cache: Optional[dict[str, int]] = None,
    ) -> tuple[QualifyingResult, str]:
        """Idempotently insert or update a single QualifyingResult record."""
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
            result = QualifyingResult(
                race_id=r_id,
                driver_id=d_id,
                constructor_id=c_id,
                car_number=item.car_number,
                position=item.position,
                q1_time=item.q1_time,
                q1_time_millis=item.q1_time_millis,
                q2_time=item.q2_time,
                q2_time_millis=item.q2_time_millis,
                q3_time=item.q3_time,
                q3_time_millis=item.q3_time_millis,
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
        if not values_equal(existing.position, item.position):
            existing.position = item.position
            updated = True
        if not values_equal(existing.q1_time, item.q1_time):
            existing.q1_time = item.q1_time
            updated = True
        if not values_equal(existing.q1_time_millis, item.q1_time_millis):
            existing.q1_time_millis = item.q1_time_millis
            updated = True
        if not values_equal(existing.q2_time, item.q2_time):
            existing.q2_time = item.q2_time
            updated = True
        if not values_equal(existing.q2_time_millis, item.q2_time_millis):
            existing.q2_time_millis = item.q2_time_millis
            updated = True
        if not values_equal(existing.q3_time, item.q3_time):
            existing.q3_time = item.q3_time
            updated = True
        if not values_equal(existing.q3_time_millis, item.q3_time_millis):
            existing.q3_time_millis = item.q3_time_millis
            updated = True

        return existing, ("updated" if updated else "skipped")

    def upsert_many(self, items: Sequence[ParsedQualifyingResult]) -> IngestionStats:
        """Idempotently persist a batch of ParsedQualifyingResult records."""
        stats = IngestionStats(entity_type="qualifying_results", records_processed=len(items))
        if not items:
            return stats

        driver_cache: dict[str, int] = {}
        constructor_cache: dict[str, int] = {}

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

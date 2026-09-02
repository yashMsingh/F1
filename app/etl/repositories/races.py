"""F1 Race Intelligence — Race repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.circuit import Circuit
from app.db.models.race import Race
from app.db.models.season import Season
from app.etl.exceptions import F1DependencyError
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedRace


class RaceRepository(BaseRepository):
    """Repository managing Race entities with foreign-key dependency resolution."""

    def get_by_season_round(self, season_year: int, round_number: int) -> Optional[Race]:
        """Look up a race by its natural unique key (season_year, round)."""
        stmt = select(Race).where(
            Race.season_year == season_year,
            Race.round == round_number,
        )
        return self.session.scalars(stmt).first()

    def get_by_id(self, internal_id: int) -> Optional[Race]:
        """Look up a race by its surrogate integer primary key."""
        return self.session.get(Race, internal_id)

    def _resolve_dependencies(self, item: ParsedRace) -> int:
        """Resolve circuit slug to internal integer circuit_id and verify season exists."""
        # Verify season exists
        season_stmt = select(Season).where(Season.season_year == item.season)
        if self.session.scalars(season_stmt).first() is None:
            raise F1DependencyError(
                f"Season '{item.season}' does not exist for race round {item.round}.",
                entity_type="races",
                missing_entity="seasons",
                missing_id=str(item.season),
            )

        # Resolve circuit slug to integer PK
        circuit_stmt = select(Circuit.id).where(Circuit.circuit_id == item.circuit_id)
        circuit_pk = self.session.scalars(circuit_stmt).first()
        if circuit_pk is None:
            raise F1DependencyError(
                f"Circuit '{item.circuit_id}' does not exist for race '{item.race_name}'.",
                entity_type="races",
                missing_entity="circuits",
                missing_id=item.circuit_id,
            )
        return circuit_pk

    def upsert(self, item: ParsedRace) -> tuple[Race, str]:
        """Idempotently insert or update a single Race record."""
        circuit_pk = self._resolve_dependencies(item)
        existing = self.get_by_season_round(item.season, item.round)

        if existing is None:
            race = Race(
                season_year=item.season,
                round=item.round,
                race_name=item.race_name,
                circuit_id=circuit_pk,
                race_date=item.race_date,
                race_time=item.race_time,
                url=item.url,
            )
            self.session.add(race)
            return race, "inserted"

        # Check for mutations
        updated = False
        if not values_equal(existing.race_name, item.race_name):
            existing.race_name = item.race_name
            updated = True
        if existing.circuit_id != circuit_pk:
            existing.circuit_id = circuit_pk
            updated = True
        if not values_equal(existing.race_date, item.race_date):
            existing.race_date = item.race_date
            updated = True
        if not values_equal(existing.race_time, item.race_time):
            existing.race_time = item.race_time
            updated = True
        if not values_equal(existing.url, item.url):
            existing.url = item.url
            updated = True

        return existing, ("updated" if updated else "skipped")

    def upsert_many(self, items: Sequence[ParsedRace]) -> IngestionStats:
        """Idempotently persist a batch of ParsedRace records."""
        stats = IngestionStats(entity_type="races", records_processed=len(items))
        for item in items:
            _, action = self.upsert(item)
            if action == "inserted":
                stats.records_inserted += 1
            elif action == "updated":
                stats.records_updated += 1
            elif action == "skipped":
                stats.records_skipped += 1
        return stats

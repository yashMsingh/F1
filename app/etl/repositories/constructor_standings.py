"""F1 Race Intelligence — ConstructorStanding repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.constructor import Constructor
from app.db.models.constructor_standing import ConstructorStanding
from app.db.models.season import Season
from app.etl.exceptions import F1DependencyError
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedConstructorStanding


class ConstructorStandingRepository(BaseRepository):
    """Repository managing ConstructorStanding entities."""

    def get_by_key(self, season_year: int, round_num: int, constructor_id: int) -> Optional[ConstructorStanding]:
        """Look up a standing by unique composite key (season_year, round, constructor_id)."""
        stmt = select(ConstructorStanding).where(
            ConstructorStanding.season_year == season_year,
            ConstructorStanding.round == round_num,
            ConstructorStanding.constructor_id == constructor_id,
        )
        return self.session.scalars(stmt).first()

    def _resolve_constructor_id(self, slug: str) -> int:
        stmt = select(Constructor.id).where(Constructor.constructor_id == slug)
        constructor_id = self.session.scalars(stmt).first()
        if constructor_id is None:
            raise F1DependencyError(
                f"Constructor slug '{slug}' not found in database.",
                entity_type="constructor_standings",
                missing_entity="constructors",
                missing_id=slug,
            )
        return constructor_id

    def _verify_season(self, year: int) -> None:
        stmt = select(Season.season_year).where(Season.season_year == year)
        if self.session.scalars(stmt).first() is None:
            raise F1DependencyError(
                f"Season '{year}' not found in database for constructor standings.",
                entity_type="constructor_standings",
                missing_entity="seasons",
                missing_id=str(year),
            )

    def upsert(
        self,
        item: ParsedConstructorStanding,
        constructor_cache: Optional[dict[str, int]] = None,
    ) -> tuple[ConstructorStanding, str]:
        """Idempotently insert or update a single ConstructorStanding record."""
        self._verify_season(item.season)

        if constructor_cache is not None and item.constructor_id in constructor_cache:
            c_id = constructor_cache[item.constructor_id]
        else:
            c_id = self._resolve_constructor_id(item.constructor_id)
            if constructor_cache is not None:
                constructor_cache[item.constructor_id] = c_id

        existing = self.get_by_key(item.season, item.round, c_id)
        if existing is None:
            standing = ConstructorStanding(
                season_year=item.season,
                round=item.round,
                constructor_id=c_id,
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

    def upsert_many(self, items: Sequence[ParsedConstructorStanding]) -> IngestionStats:
        """Idempotently persist a batch of ParsedConstructorStanding records."""
        stats = IngestionStats(entity_type="constructor_standings", records_processed=len(items))
        constructor_cache: dict[str, int] = {}
        for item in items:
            _, action = self.upsert(item, constructor_cache=constructor_cache)
            if action == "inserted":
                stats.records_inserted += 1
            elif action == "updated":
                stats.records_updated += 1
            elif action == "skipped":
                stats.records_skipped += 1
        return stats

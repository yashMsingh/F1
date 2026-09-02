"""F1 Race Intelligence — Circuit repository."""

from typing import Optional, Sequence

from sqlalchemy import select

from app.db.models.circuit import Circuit
from app.etl.repositories.base import BaseRepository, values_equal
from app.etl.types import IngestionStats
from app.f1.parsing.models import ParsedCircuit


class CircuitRepository(BaseRepository):
    """Repository managing Circuit entities."""

    def get_by_slug(self, circuit_id: str) -> Optional[Circuit]:
        """Look up a circuit by its unique Jolpica API slug."""
        stmt = select(Circuit).where(Circuit.circuit_id == circuit_id)
        return self.session.scalars(stmt).first()

    def get_by_id(self, internal_id: int) -> Optional[Circuit]:
        """Look up a circuit by its surrogate integer primary key."""
        return self.session.get(Circuit, internal_id)

    def upsert(self, item: ParsedCircuit) -> tuple[Circuit, str]:
        """Idempotently insert or update a single Circuit record."""
        existing = self.get_by_slug(item.circuit_id)
        if existing is None:
            circuit = Circuit(
                circuit_id=item.circuit_id,
                circuit_name=item.circuit_name,
                locality=item.locality,
                country=item.country,
                latitude=item.latitude,
                longitude=item.longitude,
                url=item.url,
            )
            self.session.add(circuit)
            return circuit, "inserted"

        # Check for mutations
        updated = False
        if not values_equal(existing.circuit_name, item.circuit_name):
            existing.circuit_name = item.circuit_name
            updated = True
        if not values_equal(existing.locality, item.locality):
            existing.locality = item.locality
            updated = True
        if not values_equal(existing.country, item.country):
            existing.country = item.country
            updated = True
        if not values_equal(existing.latitude, item.latitude):
            existing.latitude = item.latitude
            updated = True
        if not values_equal(existing.longitude, item.longitude):
            existing.longitude = item.longitude
            updated = True
        if not values_equal(existing.url, item.url):
            existing.url = item.url
            updated = True

        return existing, ("updated" if updated else "skipped")

    def upsert_many(self, items: Sequence[ParsedCircuit]) -> IngestionStats:
        """Idempotently persist a batch of ParsedCircuit records."""
        stats = IngestionStats(entity_type="circuits", records_processed=len(items))
        for item in items:
            _, action = self.upsert(item)
            if action == "inserted":
                stats.records_inserted += 1
            elif action == "updated":
                stats.records_updated += 1
            elif action == "skipped":
                stats.records_skipped += 1
        return stats

"""F1 Race Intelligence — ETL Orchestration Service.

Coordinates transactional persistence of parsed domain records into PostgreSQL/SQLAlchemy
models while enforcing dependency-aware ordering, idempotency, and ETL run logging.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence

from sqlalchemy.orm import Session

from app.etl.exceptions import F1ETLError
from app.etl.repositories import (
    CircuitRepository,
    ConstructorRepository,
    ConstructorStandingRepository,
    DriverRepository,
    DriverStandingRepository,
    EtlLogRepository,
    LapTimeRepository,
    PitStopRepository,
    QualifyingResultRepository,
    RaceRepository,
    RaceResultRepository,
    SeasonRepository,
    SprintResultRepository,
)
from app.etl.types import IngestionResult, IngestionStats, IngestionStatus
from app.f1.parsing.models import (
    ParsedCircuit,
    ParsedConstructor,
    ParsedConstructorStanding,
    ParsedDriver,
    ParsedDriverStanding,
    ParsedLapTime,
    ParsedPitStop,
    ParsedQualifyingResult,
    ParsedRace,
    ParsedRaceResult,
    ParsedSeason,
    ParsedSprintResult,
)

logger = logging.getLogger(__name__)


class ETLService:
    """High-level transactional service orchestrating F1 data persistence."""

    def __init__(self, session: Session, auto_commit: bool = False):
        """Initialize the ETL service with a database session.

        Args:
            session: Active SQLAlchemy session.
            auto_commit: If True, commits session upon successful completion of an operation.
                         If False (default for tests), flushes only and leaves transaction control
                         to the outer context.
        """
        self.session = session
        self.auto_commit = auto_commit

        # Initialize repositories
        self.season_repo = SeasonRepository(session)
        self.circuit_repo = CircuitRepository(session)
        self.constructor_repo = ConstructorRepository(session)
        self.driver_repo = DriverRepository(session)
        self.race_repo = RaceRepository(session)
        self.race_result_repo = RaceResultRepository(session)
        self.qualifying_result_repo = QualifyingResultRepository(session)
        self.sprint_result_repo = SprintResultRepository(session)
        self.pit_stop_repo = PitStopRepository(session)
        self.lap_time_repo = LapTimeRepository(session)
        self.driver_standing_repo = DriverStandingRepository(session)
        self.constructor_standing_repo = ConstructorStandingRepository(session)
        self.etl_log_repo = EtlLogRepository(session)

    def _execute_ingestion(
        self,
        entity_type: str,
        operation_fn: Callable[[], IngestionStats],
        season_year: Optional[int] = None,
        round_num: Optional[int] = None,
        endpoint: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> IngestionResult:
        """Execute an ingestion callable inside an audited transaction boundary."""
        log_entry = self.etl_log_repo.start_run(
            source="jolpica",
            entity_type=entity_type,
            season_year=season_year,
            round_num=round_num,
            endpoint=endpoint,
            source_url=source_url,
        )
        log_id = log_entry.id

        try:
            stats = operation_fn()
            self.session.flush()

            self.etl_log_repo.complete_run(
                log_id=log_id,
                stats=stats,
                status=IngestionStatus.SUCCESS,
            )
            if self.auto_commit:
                self.session.commit()

            return IngestionResult(
                status=IngestionStatus.SUCCESS,
                stats=stats,
                log_id=log_id,
                season_year=season_year,
                round=round_num,
            )

        except Exception as exc:
            logger.error("ETL operation '%s' failed: %s", entity_type, exc, exc_info=True)
            self.session.rollback()

            # Record failure in an isolated flush
            try:
                fail_log = self.etl_log_repo.start_run(
                    source="jolpica",
                    entity_type=entity_type,
                    season_year=season_year,
                    round_num=round_num,
                    endpoint=endpoint,
                    source_url=source_url,
                )
                self.etl_log_repo.complete_run(
                    log_id=fail_log.id,
                    stats=IngestionStats(entity_type=entity_type, records_failed=1),
                    status=IngestionStatus.FAILED,
                    error_message=str(exc),
                )
                if self.auto_commit:
                    self.session.commit()
            except Exception as log_exc:
                logger.warning("Could not record failed EtlLog: %s", log_exc)

            raise exc

    # ── Single-Entity Ingestion Methods ──────────────────────────────────────

    def ingest_seasons(
        self,
        items: Sequence[ParsedSeason],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist seasons."""
        return self._execute_ingestion(
            entity_type="seasons",
            operation_fn=lambda: self.season_repo.upsert_many(items),
            endpoint=endpoint,
        )

    def ingest_circuits(
        self,
        items: Sequence[ParsedCircuit],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist circuits."""
        return self._execute_ingestion(
            entity_type="circuits",
            operation_fn=lambda: self.circuit_repo.upsert_many(items),
            endpoint=endpoint,
        )

    def ingest_constructors(
        self,
        items: Sequence[ParsedConstructor],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist constructors."""
        return self._execute_ingestion(
            entity_type="constructors",
            operation_fn=lambda: self.constructor_repo.upsert_many(items),
            endpoint=endpoint,
        )

    def ingest_drivers(
        self,
        items: Sequence[ParsedDriver],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist drivers."""
        return self._execute_ingestion(
            entity_type="drivers",
            operation_fn=lambda: self.driver_repo.upsert_many(items),
            endpoint=endpoint,
        )

    def ingest_races(
        self,
        items: Sequence[ParsedRace],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist races schedule."""
        season = items[0].season if items else None
        return self._execute_ingestion(
            entity_type="races",
            operation_fn=lambda: self.race_repo.upsert_many(items),
            season_year=season,
            endpoint=endpoint,
        )

    def ingest_race_results(
        self,
        items: Sequence[ParsedRaceResult],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist race results."""
        season = items[0].season if items else None
        round_num = items[0].round if items else None
        return self._execute_ingestion(
            entity_type="race_results",
            operation_fn=lambda: self.race_result_repo.upsert_many(items),
            season_year=season,
            round_num=round_num,
            endpoint=endpoint,
        )

    def ingest_qualifying_results(
        self,
        items: Sequence[ParsedQualifyingResult],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist qualifying session results."""
        season = items[0].season if items else None
        round_num = items[0].round if items else None
        return self._execute_ingestion(
            entity_type="qualifying_results",
            operation_fn=lambda: self.qualifying_result_repo.upsert_many(items),
            season_year=season,
            round_num=round_num,
            endpoint=endpoint,
        )

    def ingest_sprint_results(
        self,
        items: Sequence[ParsedSprintResult],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist sprint race results."""
        season = items[0].season if items else None
        round_num = items[0].round if items else None
        return self._execute_ingestion(
            entity_type="sprint_results",
            operation_fn=lambda: self.sprint_result_repo.upsert_many(items),
            season_year=season,
            round_num=round_num,
            endpoint=endpoint,
        )

    def ingest_pit_stops(
        self,
        items: Sequence[ParsedPitStop],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist pit stop records."""
        season = items[0].season if items else None
        round_num = items[0].round if items else None
        return self._execute_ingestion(
            entity_type="pit_stops",
            operation_fn=lambda: self.pit_stop_repo.upsert_many(items),
            season_year=season,
            round_num=round_num,
            endpoint=endpoint,
        )

    def ingest_lap_times(
        self,
        items: Sequence[ParsedLapTime],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist lap timing records."""
        season = items[0].season if items else None
        round_num = items[0].round if items else None
        return self._execute_ingestion(
            entity_type="lap_times",
            operation_fn=lambda: self.lap_time_repo.upsert_many(items),
            season_year=season,
            round_num=round_num,
            endpoint=endpoint,
        )

    def ingest_driver_standings(
        self,
        items: Sequence[ParsedDriverStanding],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist driver championship standings."""
        season = items[0].season if items else None
        round_num = items[0].round if items else None
        return self._execute_ingestion(
            entity_type="driver_standings",
            operation_fn=lambda: self.driver_standing_repo.upsert_many(items),
            season_year=season,
            round_num=round_num,
            endpoint=endpoint,
        )

    def ingest_constructor_standings(
        self,
        items: Sequence[ParsedConstructorStanding],
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist constructor championship standings."""
        season = items[0].season if items else None
        round_num = items[0].round if items else None
        return self._execute_ingestion(
            entity_type="constructor_standings",
            operation_fn=lambda: self.constructor_standing_repo.upsert_many(items),
            season_year=season,
            round_num=round_num,
            endpoint=endpoint,
        )

    # ── Orchestrated Multi-Entity Ingestion ──────────────────────────────────

    def ingest_race_weekend(
        self,
        season: ParsedSeason,
        circuits: Sequence[ParsedCircuit],
        constructors: Sequence[ParsedConstructor],
        drivers: Sequence[ParsedDriver],
        races: Sequence[ParsedRace],
        race_results: Sequence[ParsedRaceResult] = (),
        qualifying_results: Sequence[ParsedQualifyingResult] = (),
        sprint_results: Sequence[ParsedSprintResult] = (),
        pit_stops: Sequence[ParsedPitStop] = (),
        lap_times: Sequence[ParsedLapTime] = (),
        driver_standings: Sequence[ParsedDriverStanding] = (),
        constructor_standings: Sequence[ParsedConstructorStanding] = (),
        endpoint: Optional[str] = None,
    ) -> IngestionResult:
        """Persist an entire Grand Prix race weekend in strict dependency-safe order.

        Order:
          1. Season
          2. Circuits
          3. Constructors & Drivers
          4. Races
          5. Race Results, Qualifying Results, Sprint Results, Pit Stops, Lap Times
          6. Standings
        """
        def _operation() -> IngestionStats:
            total_stats = IngestionStats(entity_type="race_weekend")

            # 1. Season
            _, s_action = self.season_repo.upsert(season)
            s_stats = IngestionStats(entity_type="seasons", records_processed=1)
            if s_action == "inserted":
                s_stats.records_inserted = 1
            elif s_action == "updated":
                s_stats.records_updated = 1
            else:
                s_stats.records_skipped = 1
            total_stats = total_stats.merge(s_stats)

            # 2. Circuits
            c_stats = self.circuit_repo.upsert_many(circuits)
            total_stats = total_stats.merge(c_stats)

            # 3. Constructors & Drivers
            con_stats = self.constructor_repo.upsert_many(constructors)
            d_stats = self.driver_repo.upsert_many(drivers)
            total_stats = total_stats.merge(con_stats).merge(d_stats)

            # 4. Races
            r_stats = self.race_repo.upsert_many(races)
            total_stats = total_stats.merge(r_stats)

            # 5. Session results and telemetry
            if race_results:
                rr_stats = self.race_result_repo.upsert_many(race_results)
                total_stats = total_stats.merge(rr_stats)

            if qualifying_results:
                qr_stats = self.qualifying_result_repo.upsert_many(qualifying_results)
                total_stats = total_stats.merge(qr_stats)

            if sprint_results:
                sr_stats = self.sprint_result_repo.upsert_many(sprint_results)
                total_stats = total_stats.merge(sr_stats)

            if pit_stops:
                ps_stats = self.pit_stop_repo.upsert_many(pit_stops)
                total_stats = total_stats.merge(ps_stats)

            if lap_times:
                lt_stats = self.lap_time_repo.upsert_many(lap_times)
                total_stats = total_stats.merge(lt_stats)

            # 6. Standings
            if driver_standings:
                ds_stats = self.driver_standing_repo.upsert_many(driver_standings)
                total_stats = total_stats.merge(ds_stats)

            if constructor_standings:
                cs_stats = self.constructor_standing_repo.upsert_many(constructor_standings)
                total_stats = total_stats.merge(cs_stats)

            total_stats.entity_type = "race_weekend"
            return total_stats

        first_race = races[0] if races else None
        s_year = first_race.season if first_race else season.year
        r_num = first_race.round if first_race else None

        return self._execute_ingestion(
            entity_type="race_weekend",
            operation_fn=_operation,
            season_year=s_year,
            round_num=r_num,
            endpoint=endpoint,
        )

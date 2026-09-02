"""Integration tests for ETLService orchestration, transaction boundaries, and auditing."""

from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models.circuit import Circuit
from app.db.models.constructor import Constructor
from app.db.models.constructor_standing import ConstructorStanding
from app.db.models.driver import Driver
from app.db.models.driver_standing import DriverStanding
from app.db.models.etl_log import EtlLog
from app.db.models.lap_time import LapTime
from app.db.models.pit_stop import PitStop
from app.db.models.qualifying_result import QualifyingResult
from app.db.models.race import Race
from app.db.models.race_result import RaceResult
from app.db.models.season import Season
from app.db.models.sprint_result import SprintResult
from app.etl.exceptions import F1DependencyError
from app.etl.service import ETLService
from app.etl.types import IngestionStatus
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


@pytest.fixture
def synthetic_weekend_data():
    """Build a minimal valid synthetic race weekend covering all 12 entities."""
    season = ParsedSeason(year=2024, url="https://example.com/2024")
    circuits = [
        ParsedCircuit(
            circuit_id="bahrain",
            circuit_name="Bahrain International Circuit",
            locality="Sakhir",
            country="Bahrain",
            latitude=Decimal("26.0325"),
            longitude=Decimal("50.5106"),
        )
    ]
    constructors = [
        ParsedConstructor(constructor_id="red_bull", name="Red Bull Racing", nationality="Austrian"),
        ParsedConstructor(constructor_id="ferrari", name="Ferrari", nationality="Italian"),
    ]
    drivers = [
        ParsedDriver(driver_id="verstappen", given_name="Max", family_name="Verstappen", permanent_number=1, code="VER"),
        ParsedDriver(driver_id="leclerc", given_name="Charles", family_name="Leclerc", permanent_number=16, code="LEC"),
    ]
    races = [
        ParsedRace(
            season=2024,
            round=1,
            race_name="Bahrain Grand Prix",
            circuit_id="bahrain",
            race_date=date(2024, 3, 2),
            race_time=time(15, 0, 0),
        )
    ]
    race_results = [
        ParsedRaceResult(
            season=2024,
            round=1,
            driver_id="verstappen",
            constructor_id="red_bull",
            source_position=1,
            position_text="1",
            status="Finished",
            car_number=1,
            grid_position=1,
            laps_completed=57,
            points=Decimal("26.00"),
            time_text="1:31:44.742",
            time_millis=5504742,
            fastest_lap_rank=1,
            fastest_lap_number=39,
            fastest_lap_time="1:32.608",
            fastest_lap_time_millis=92608,
        ),
        ParsedRaceResult(
            season=2024,
            round=1,
            driver_id="leclerc",
            constructor_id="ferrari",
            source_position=2,
            position_text="2",
            status="Finished",
            car_number=16,
            grid_position=2,
            laps_completed=57,
            points=Decimal("18.00"),
            time_text="+22.457",
        ),
    ]
    qualifying_results = [
        ParsedQualifyingResult(
            season=2024,
            round=1,
            driver_id="verstappen",
            constructor_id="red_bull",
            position=1,
            car_number=1,
            q1_time="1:30.031",
            q1_time_millis=90031,
            q2_time="1:29.374",
            q2_time_millis=89374,
            q3_time="1:29.179",
            q3_time_millis=89179,
        ),
    ]
    sprint_results = [
        ParsedSprintResult(
            season=2024,
            round=1,
            driver_id="verstappen",
            constructor_id="red_bull",
            source_position=1,
            position_text="1",
            status="Finished",
            car_number=1,
            grid_position=1,
            laps_completed=19,
            points=Decimal("8.00"),
        )
    ]
    pit_stops = [
        ParsedPitStop(
            season=2024,
            round=1,
            driver_id="verstappen",
            stop_number=1,
            lap=18,
            time_of_day="15:28:30",
            duration_text="24.123",
            duration_millis=24123,
        )
    ]
    lap_times = [
        ParsedLapTime(
            season=2024,
            round=1,
            driver_id="verstappen",
            lap_number=1,
            position=1,
            time="1:36.415",
            time_millis=96415,
        )
    ]
    driver_standings = [
        ParsedDriverStanding(
            season=2024,
            round=1,
            driver_id="verstappen",
            position=1,
            points=Decimal("26.00"),
            wins=1,
        )
    ]
    constructor_standings = [
        ParsedConstructorStanding(
            season=2024,
            round=1,
            constructor_id="red_bull",
            position=1,
            points=Decimal("26.00"),
            wins=1,
        )
    ]

    return {
        "season": season,
        "circuits": circuits,
        "constructors": constructors,
        "drivers": drivers,
        "races": races,
        "race_results": race_results,
        "qualifying_results": qualifying_results,
        "sprint_results": sprint_results,
        "pit_stops": pit_stops,
        "lap_times": lap_times,
        "driver_standings": driver_standings,
        "constructor_standings": constructor_standings,
    }


class TestETLService:
    def test_full_race_weekend_ingestion_and_idempotency(self, session, synthetic_weekend_data):
        service = ETLService(session=session, auto_commit=False)

        # Run 1: Clean ingestion
        res1 = service.ingest_race_weekend(**synthetic_weekend_data, endpoint="2024/1/results")
        assert res1.status == IngestionStatus.SUCCESS
        assert res1.stats.records_inserted > 0
        assert res1.stats.records_failed == 0

        # Verify rows exist in DB
        assert session.scalar(select(Season.season_year).where(Season.season_year == 2024)) == 2024
        assert session.scalar(select(Circuit.circuit_id).where(Circuit.circuit_id == "bahrain")) == "bahrain"
        assert len(session.scalars(select(Constructor)).all()) == 2
        assert len(session.scalars(select(Driver)).all()) == 2
        assert len(session.scalars(select(Race)).all()) == 1
        assert len(session.scalars(select(RaceResult)).all()) == 2
        assert len(session.scalars(select(QualifyingResult)).all()) == 1
        assert len(session.scalars(select(SprintResult)).all()) == 1
        assert len(session.scalars(select(PitStop)).all()) == 1
        assert len(session.scalars(select(LapTime)).all()) == 1
        assert len(session.scalars(select(DriverStanding)).all()) == 1
        assert len(session.scalars(select(ConstructorStanding)).all()) == 1

        # Check ETL log for Run 1
        log1 = session.get(EtlLog, res1.log_id)
        assert log1 is not None
        assert log1.status == IngestionStatus.SUCCESS.value
        assert log1.season_year == 2024
        assert log1.round == 1
        assert log1.records_inserted == res1.stats.records_inserted

        # Run 2: Exact same payload (Idempotency)
        res2 = service.ingest_race_weekend(**synthetic_weekend_data, endpoint="2024/1/results")
        assert res2.status == IngestionStatus.SUCCESS
        assert res2.stats.records_inserted == 0
        assert res2.stats.records_skipped > 0
        assert res2.stats.records_failed == 0

        # Verify row counts remained exactly identical
        assert len(session.scalars(select(RaceResult)).all()) == 2

    def test_transaction_rollback_on_missing_dependency(self, session, synthetic_weekend_data):
        service = ETLService(session=session, auto_commit=False)

        # Corrupt data: race result references a driver not in drivers list
        corrupt_data = dict(synthetic_weekend_data)
        corrupt_data["race_results"] = [
            ParsedRaceResult(
                season=2024,
                round=1,
                driver_id="ghost_driver_not_present",
                constructor_id="red_bull",
                source_position=1,
                position_text="1",
                status="Finished",
                car_number=99,
                grid_position=1,
                laps_completed=57,
                points=Decimal("25"),
            )
        ]

        # Ingestion must raise F1DependencyError
        with pytest.raises(F1DependencyError):
            service.ingest_race_weekend(**corrupt_data)

        # Verify that the entire weekend operation was rolled back:
        # Season, circuits, races should not have persisted
        assert session.scalar(select(Season.season_year).where(Season.season_year == 2024)) is None
        assert session.scalar(select(Circuit.circuit_id).where(Circuit.circuit_id == "bahrain")) is None
        assert len(session.scalars(select(RaceResult)).all()) == 0

        # Verify that a FAILED EtlLog entry was created to document the aborted run
        failed_logs = session.scalars(select(EtlLog).where(EtlLog.status == IngestionStatus.FAILED.value)).all()
        assert len(failed_logs) == 1
        assert "ghost_driver_not_present" in str(failed_logs[0].error_message)

    def test_single_entity_ingestion_methods(self, session):
        service = ETLService(session=session, auto_commit=False)

        # Ingest seasons alone
        res = service.ingest_seasons([ParsedSeason(year=2026, url="https://example.com/2026")])
        assert res.status == IngestionStatus.SUCCESS
        assert res.stats.records_inserted == 1

        # Ingest drivers alone
        d_res = service.ingest_drivers([
            ParsedDriver(driver_id="piastri", given_name="Oscar", family_name="Piastri", code="PIA")
        ])
        assert d_res.status == IngestionStatus.SUCCESS
        assert d_res.stats.records_inserted == 1
        assert session.scalar(select(Driver.driver_id).where(Driver.driver_id == "piastri")) == "piastri"

"""Unit and integration tests for ETL entity repositories."""

from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models.circuit import Circuit
from app.db.models.constructor import Constructor
from app.db.models.constructor_standing import ConstructorStanding
from app.db.models.driver import Driver
from app.db.models.driver_standing import DriverStanding
from app.db.models.lap_time import LapTime
from app.db.models.pit_stop import PitStop
from app.db.models.qualifying_result import QualifyingResult
from app.db.models.race import Race
from app.db.models.race_result import RaceResult
from app.db.models.season import Season
from app.db.models.sprint_result import SprintResult
from app.etl.exceptions import F1DependencyError
from app.etl.repositories import (
    CircuitRepository,
    ConstructorRepository,
    ConstructorStandingRepository,
    DriverRepository,
    DriverStandingRepository,
    LapTimeRepository,
    PitStopRepository,
    QualifyingResultRepository,
    RaceRepository,
    RaceResultRepository,
    SeasonRepository,
    SprintResultRepository,
)
from app.etl.repositories.base import values_equal
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


# ── Values Equal Helper Tests ────────────────────────────────────────────────


class TestValuesEqual:
    def test_none_equality(self):
        assert values_equal(None, None) is True
        assert values_equal(None, "abc") is False
        assert values_equal("abc", None) is False

    def test_decimal_numeric_equality(self):
        assert values_equal(Decimal("25.00"), Decimal("25")) is True
        assert values_equal(Decimal("25.0"), 25) is True
        assert values_equal(25, Decimal("25.000")) is True
        assert values_equal(Decimal("25.00"), Decimal("26")) is False

    def test_string_and_date_equality(self):
        assert values_equal("Red Bull", "Red Bull") is True
        assert values_equal("Red Bull", "Ferrari") is False
        assert values_equal(date(2024, 3, 2), date(2024, 3, 2)) is True
        assert values_equal(date(2024, 3, 2), date(2024, 3, 3)) is False


# ── Season Repository Tests ──────────────────────────────────────────────────


class TestSeasonRepository:
    def test_insert_and_idempotency(self, session):
        repo = SeasonRepository(session)
        item = ParsedSeason(year=2024, url="https://example.com/2024")

        # First run: inserted
        season, action = repo.upsert(item)
        session.flush()
        assert action == "inserted"
        assert season.season_year == 2024
        assert season.url == "https://example.com/2024"

        # Second run: skipped (idempotent)
        _, action2 = repo.upsert(item)
        session.flush()
        assert action2 == "skipped"

        # Total rows in DB is exactly 1
        rows = session.scalars(select(Season).where(Season.season_year == 2024)).all()
        assert len(rows) == 1

    def test_update_mutated_field(self, session):
        repo = SeasonRepository(session)
        item = ParsedSeason(year=2025, url="https://example.com/2025-v1")
        repo.upsert(item)
        session.flush()

        # Update with new URL
        updated_item = ParsedSeason(year=2025, url="https://example.com/2025-v2")
        season, action = repo.upsert(updated_item)
        session.flush()

        assert action == "updated"
        assert season.url == "https://example.com/2025-v2"
        rows = session.scalars(select(Season).where(Season.season_year == 2025)).all()
        assert len(rows) == 1


# ── Circuit Repository Tests ─────────────────────────────────────────────────


class TestCircuitRepository:
    def test_insert_idempotency_and_update(self, session):
        repo = CircuitRepository(session)
        circuit = ParsedCircuit(
            circuit_id="bahrain",
            circuit_name="Bahrain International Circuit",
            locality="Sakhir",
            country="Bahrain",
            latitude=Decimal("26.032500"),
            longitude=Decimal("50.510600"),
            url="https://example.com/bahrain",
        )

        # 1. Insert
        _, action1 = repo.upsert(circuit)
        session.flush()
        assert action1 == "inserted"

        # 2. Duplicate skip
        _, action2 = repo.upsert(circuit)
        session.flush()
        assert action2 == "skipped"

        # 3. Update field
        mutated = ParsedCircuit(
            circuit_id="bahrain",
            circuit_name="Bahrain International Circuit (Updated)",
            locality="Sakhir",
            country="Bahrain",
            latitude=Decimal("26.032500"),
            longitude=Decimal("50.510600"),
            url="https://example.com/bahrain",
        )
        _, action3 = repo.upsert(mutated)
        session.flush()
        assert action3 == "updated"

        db_row = repo.get_by_slug("bahrain")
        assert db_row.circuit_name == "Bahrain International Circuit (Updated)"


# ── Constructor & Driver Repository Tests ────────────────────────────────────


class TestConstructorRepository:
    def test_insert_and_idempotency(self, session):
        repo = ConstructorRepository(session)
        team = ParsedConstructor(
            constructor_id="red_bull",
            name="Red Bull Racing",
            nationality="Austrian",
            url="https://example.com/redbull",
        )

        _, action1 = repo.upsert(team)
        session.flush()
        assert action1 == "inserted"

        _, action2 = repo.upsert(team)
        session.flush()
        assert action2 == "skipped"

        rows = session.scalars(select(Constructor).where(Constructor.constructor_id == "red_bull")).all()
        assert len(rows) == 1


class TestDriverRepository:
    def test_insert_and_null_preservation(self, session):
        repo = DriverRepository(session)
        # Driver with None for optional fields
        driver = ParsedDriver(
            driver_id="historical_driver",
            given_name="John",
            family_name="Doe",
            permanent_number=None,
            code=None,
            date_of_birth=None,
            nationality=None,
        )

        _, action = repo.upsert(driver)
        session.flush()
        assert action == "inserted"

        db_driver = repo.get_by_slug("historical_driver")
        assert db_driver.permanent_number is None
        assert db_driver.code is None
        assert db_driver.date_of_birth is None
        assert db_driver.nationality is None


# ── Race Repository Tests ────────────────────────────────────────────────────


class TestRaceRepository:
    def test_insert_and_idempotency(self, session):
        # Setup parents
        SeasonRepository(session).upsert(ParsedSeason(year=2024))
        CircuitRepository(session).upsert(
            ParsedCircuit(circuit_id="bahrain", circuit_name="Bahrain Circuit")
        )
        session.flush()

        repo = RaceRepository(session)
        race = ParsedRace(
            season=2024,
            round=1,
            race_name="Bahrain Grand Prix",
            circuit_id="bahrain",
            race_date=date(2024, 3, 2),
            race_time=time(15, 0, 0),
        )

        # 1. Insert
        _, action1 = repo.upsert(race)
        session.flush()
        assert action1 == "inserted"

        # 2. Duplicate skip
        _, action2 = repo.upsert(race)
        session.flush()
        assert action2 == "skipped"

        # Exact 1 row in DB
        rows = session.scalars(select(Race).where(Race.season_year == 2024, Race.round == 1)).all()
        assert len(rows) == 1

    def test_missing_parent_raises_dependency_error(self, session):
        repo = RaceRepository(session)
        race = ParsedRace(
            season=2024,
            round=1,
            race_name="Bahrain Grand Prix",
            circuit_id="nonexistent_circuit",
            race_date=date(2024, 3, 2),
        )
        with pytest.raises(F1DependencyError) as exc_info:
            repo.upsert(race)
        assert exc_info.value.missing_entity in ("seasons", "circuits")


# ── Race Results Repository Tests ───────────────────────────────────────────


class TestRaceResultRepository:
    @pytest.fixture
    def setup_parents(self, session):
        SeasonRepository(session).upsert(ParsedSeason(year=2024))
        CircuitRepository(session).upsert(ParsedCircuit(circuit_id="bahrain", circuit_name="Bahrain"))
        ConstructorRepository(session).upsert(ParsedConstructor(constructor_id="red_bull", name="Red Bull"))
        DriverRepository(session).upsert(ParsedDriver(driver_id="verstappen", given_name="Max", family_name="Verstappen"))
        RaceRepository(session).upsert(
            ParsedRace(season=2024, round=1, race_name="Bahrain GP", circuit_id="bahrain", race_date=date(2024, 3, 2))
        )
        session.flush()

    def test_insert_and_idempotency(self, session, setup_parents):
        repo = RaceResultRepository(session)
        result = ParsedRaceResult(
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
        )

        # 1. Insert
        _, action1 = repo.upsert(result)
        session.flush()
        assert action1 == "inserted"

        # 2. Duplicate skip
        _, action2 = repo.upsert(result)
        session.flush()
        assert action2 == "skipped"

        # Exactly 1 row in DB
        rows = session.scalars(select(RaceResult)).all()
        assert len(rows) == 1

    def test_update_points(self, session, setup_parents):
        repo = RaceResultRepository(session)
        result = ParsedRaceResult(
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
            points=Decimal("25.00"),
        )
        repo.upsert(result)
        session.flush()

        # Update points to 26 (e.g. fastest lap point added)
        updated_result = ParsedRaceResult(
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
        )
        r, action = repo.upsert(updated_result)
        session.flush()

        assert action == "updated"
        assert r.points == Decimal("26.00")
        assert len(session.scalars(select(RaceResult)).all()) == 1

    def test_missing_driver_raises_dependency_error(self, session, setup_parents):
        repo = RaceResultRepository(session)
        result = ParsedRaceResult(
            season=2024,
            round=1,
            driver_id="nonexistent_driver",
            constructor_id="red_bull",
            source_position=1,
            position_text="1",
            status="Finished",
            car_number=1,
            grid_position=1,
            laps_completed=57,
            points=Decimal("25.00"),
        )
        with pytest.raises(F1DependencyError) as exc_info:
            repo.upsert(result)
        assert exc_info.value.missing_entity == "drivers"


# ── Qualifying, Sprint, Pit Stop, Lap Time Repository Tests ─────────────────


class TestOtherEventRepositories:
    @pytest.fixture
    def setup_weekend(self, session):
        SeasonRepository(session).upsert(ParsedSeason(year=2024))
        CircuitRepository(session).upsert(ParsedCircuit(circuit_id="bahrain", circuit_name="Bahrain"))
        ConstructorRepository(session).upsert(ParsedConstructor(constructor_id="red_bull", name="Red Bull"))
        DriverRepository(session).upsert(ParsedDriver(driver_id="verstappen", given_name="Max", family_name="Verstappen"))
        RaceRepository(session).upsert(
            ParsedRace(season=2024, round=1, race_name="Bahrain GP", circuit_id="bahrain", race_date=date(2024, 3, 2))
        )
        session.flush()

    def test_qualifying_result_idempotency(self, session, setup_weekend):
        repo = QualifyingResultRepository(session)
        q = ParsedQualifyingResult(
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
        )
        _, a1 = repo.upsert(q)
        session.flush()
        assert a1 == "inserted"

        _, a2 = repo.upsert(q)
        session.flush()
        assert a2 == "skipped"

        rows = session.scalars(select(QualifyingResult)).all()
        assert len(rows) == 1

    def test_sprint_result_idempotency(self, session, setup_weekend):
        repo = SprintResultRepository(session)
        s = ParsedSprintResult(
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
            points=Decimal("8"),
        )
        _, a1 = repo.upsert(s)
        session.flush()
        assert a1 == "inserted"

        _, a2 = repo.upsert(s)
        session.flush()
        assert a2 == "skipped"

        rows = session.scalars(select(SprintResult)).all()
        assert len(rows) == 1

    def test_pit_stop_idempotency_and_duration_preservation(self, session, setup_weekend):
        repo = PitStopRepository(session)
        ps = ParsedPitStop(
            season=2024,
            round=1,
            driver_id="verstappen",
            stop_number=1,
            lap=15,
            time_of_day="15:25:30",
            duration_text="40:55.302",
            duration_millis=2455302,
        )
        _, a1 = repo.upsert(ps)
        session.flush()
        assert a1 == "inserted"

        _, a2 = repo.upsert(ps)
        session.flush()
        assert a2 == "skipped"

        row = session.scalars(select(PitStop)).first()
        assert row.duration_text == "40:55.302"
        assert row.duration_millis == 2455302
        assert len(session.scalars(select(PitStop)).all()) == 1

    def test_lap_time_idempotency(self, session, setup_weekend):
        repo = LapTimeRepository(session)
        lt = ParsedLapTime(
            season=2024,
            round=1,
            driver_id="verstappen",
            lap_number=1,
            position=1,
            time="1:36.415",
            time_millis=96415,
        )
        _, a1 = repo.upsert(lt)
        session.flush()
        assert a1 == "inserted"

        _, a2 = repo.upsert(lt)
        session.flush()
        assert a2 == "skipped"

        rows = session.scalars(select(LapTime)).all()
        assert len(rows) == 1


# ── Standings Repository Tests ──────────────────────────────────────────────


class TestStandingsRepositories:
    @pytest.fixture
    def setup_standings_parents(self, session):
        SeasonRepository(session).upsert(ParsedSeason(year=2024))
        DriverRepository(session).upsert(ParsedDriver(driver_id="verstappen", given_name="Max", family_name="Verstappen"))
        ConstructorRepository(session).upsert(ParsedConstructor(constructor_id="red_bull", name="Red Bull"))
        session.flush()

    def test_driver_standing_idempotency(self, session, setup_standings_parents):
        repo = DriverStandingRepository(session)
        ds = ParsedDriverStanding(
            season=2024,
            round=1,
            driver_id="verstappen",
            position=1,
            points=Decimal("26.00"),
            wins=1,
        )
        _, a1 = repo.upsert(ds)
        session.flush()
        assert a1 == "inserted"

        _, a2 = repo.upsert(ds)
        session.flush()
        assert a2 == "skipped"

        rows = session.scalars(select(DriverStanding)).all()
        assert len(rows) == 1

    def test_constructor_standing_idempotency(self, session, setup_standings_parents):
        repo = ConstructorStandingRepository(session)
        cs = ParsedConstructorStanding(
            season=2024,
            round=1,
            constructor_id="red_bull",
            position=1,
            points=Decimal("44.00"),
            wins=1,
        )
        _, a1 = repo.upsert(cs)
        session.flush()
        assert a1 == "inserted"

        _, a2 = repo.upsert(cs)
        session.flush()
        assert a2 == "skipped"

        rows = session.scalars(select(ConstructorStanding)).all()
        assert len(rows) == 1

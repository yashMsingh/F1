"""Tests for relational constraints, uniqueness rules, foreign keys, and constructor mobility."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import (
    Circuit,
    Constructor,
    Driver,
    LapTime,
    PitStop,
    Race,
    RaceResult,
    Season,
)


def _seed_basic_entities(session):
    """Helper to seed minimal parent records for testing constraints."""
    season = Season(season_year=2024, url="https://en.wikipedia.org/wiki/2024_Formula_One_World_Championship")
    circuit = Circuit(
        circuit_id="albert_park",
        circuit_name="Albert Park Grand Prix Circuit",
        locality="Melbourne",
        country="Australia",
    )
    constructor1 = Constructor(constructor_id="red_bull", name="Red Bull Racing", nationality="Austrian")
    constructor2 = Constructor(constructor_id="rb", name="RB F1 Team", nationality="Italian")
    driver = Driver(
        driver_id="lawson",
        permanent_number=30,
        code="LAW",
        given_name="Liam",
        family_name="Lawson",
        nationality="New Zealander",
    )

    session.add_all([season, circuit, constructor1, constructor2, driver])
    session.flush()

    race1 = Race(
        season_year=2024,
        round=1,
        race_name="Australian Grand Prix",
        circuit_id=circuit.id,
        race_date=date(2024, 3, 24),
    )
    race2 = Race(
        season_year=2024,
        round=2,
        race_name="Chinese Grand Prix",
        circuit_id=circuit.id,
        race_date=date(2024, 4, 7),
    )
    session.add_all([race1, race2])
    session.flush()

    return season, circuit, constructor1, constructor2, driver, race1, race2


def test_foreign_key_invalid_reference_rejected(session):
    """Test 2 — Foreign keys: Inserting a race with non-existent season/circuit is rejected."""
    invalid_race = Race(
        season_year=9999,  # Non-existent season
        round=1,
        race_name="Phantom Grand Prix",
        circuit_id=9999,  # Non-existent circuit
        race_date=date(2024, 1, 1),
    )
    session.add(invalid_race)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_race_season_round_uniqueness_rejected(session):
    """Test 3 — Race uniqueness: Duplicate season_year and round is rejected."""
    season, circuit, _, _, _, race1, _ = _seed_basic_entities(session)

    # Attempt to insert a second race in the same season with the same round=1
    duplicate_race = Race(
        season_year=season.season_year,
        round=1,  # Same round as race1
        race_name="Duplicate Australian Grand Prix",
        circuit_id=circuit.id,
        race_date=date(2024, 3, 25),
    )
    session.add(duplicate_race)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_race_result_driver_uniqueness_rejected(session):
    """Test 4 — Race result uniqueness: The same driver cannot have duplicate results in the same race."""
    _, _, constructor1, _, driver, race1, _ = _seed_basic_entities(session)

    res1 = RaceResult(
        race_id=race1.id,
        driver_id=driver.id,
        constructor_id=constructor1.id,
        position_text="1",
        points=Decimal("25.0"),
        laps_completed=58,
        status="Finished",
    )
    session.add(res1)
    session.flush()

    # Attempt to insert a second result for the same driver and race
    res2 = RaceResult(
        race_id=race1.id,
        driver_id=driver.id,
        constructor_id=constructor1.id,
        position_text="2",
        points=Decimal("18.0"),
        laps_completed=58,
        status="Finished",
    )
    session.add(res2)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_driver_constructor_mobility_across_races(session):
    """Test 5 — Constructor changes: A driver can legitimately appear with different constructors across races."""
    _, _, constructor1, constructor2, driver, race1, race2 = _seed_basic_entities(session)

    # Race 1: Liam Lawson drives for RB F1 Team
    res1 = RaceResult(
        race_id=race1.id,
        driver_id=driver.id,
        constructor_id=constructor2.id,  # RB
        position_text="9",
        points=Decimal("2.0"),
        laps_completed=58,
        status="Finished",
    )

    # Race 2: Liam Lawson is promoted to Red Bull Racing
    res2 = RaceResult(
        race_id=race2.id,
        driver_id=driver.id,
        constructor_id=constructor1.id,  # Red Bull Racing
        position_text="3",
        points=Decimal("15.0"),
        laps_completed=56,
        status="Finished",
    )

    session.add_all([res1, res2])
    session.flush()

    # Verify both records persisted successfully
    results = session.query(RaceResult).filter_by(driver_id=driver.id).order_by(RaceResult.race_id).all()
    assert len(results) == 2
    assert results[0].constructor_id == constructor2.id
    assert results[1].constructor_id == constructor1.id


def test_pit_stop_stop_number_uniqueness_rejected(session):
    """Test 6 — Pit-stop identity: The same stop number cannot be duplicated for the same driver/race."""
    _, _, _, _, driver, race1, _ = _seed_basic_entities(session)

    ps1 = PitStop(
        race_id=race1.id,
        driver_id=driver.id,
        stop_number=1,
        lap=18,
        time_of_day="15:30:00",
        duration_text="22.100",
        duration_millis=22100,
    )
    session.add(ps1)
    session.flush()

    # Duplicate stop 1 for same race and driver
    ps2 = PitStop(
        race_id=race1.id,
        driver_id=driver.id,
        stop_number=1,
        lap=35,
        time_of_day="16:00:00",
        duration_text="23.500",
        duration_millis=23500,
    )
    session.add(ps2)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_lap_time_lap_number_uniqueness_rejected(session):
    """Test 7 — Lap identity: The same lap number cannot be duplicated for the same driver/race."""
    _, _, _, _, driver, race1, _ = _seed_basic_entities(session)

    lt1 = LapTime(
        race_id=race1.id,
        driver_id=driver.id,
        lap_number=1,
        position=1,
        time="1:25.400",
        time_millis=85400,
    )
    session.add(lt1)
    session.flush()

    # Duplicate lap 1
    lt2 = LapTime(
        race_id=race1.id,
        driver_id=driver.id,
        lap_number=1,
        position=2,
        time="1:25.800",
        time_millis=85800,
    )
    session.add(lt2)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()

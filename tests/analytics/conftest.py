"""Pytest fixtures for analytics tests — seeded database session with known F1 data."""

from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db.models import (
    Circuit,
    Constructor,
    ConstructorStanding,
    Driver,
    DriverStanding,
    LapTime,
    PitStop,
    QualifyingResult,
    Race,
    RaceResult,
    Season,
)


@pytest.fixture
def bahrain_analytics_data(session: Session):
    """Seed the test database with a controlled 2024 Bahrain GP dataset.

    Contains:
    - 1 season (2024)
    - 1 circuit (Bahrain)
    - 3 constructors (Red Bull, Ferrari, Williams)
    - 6 drivers:
        - Verstappen & Perez (Red Bull)
        - Leclerc & Sainz (Ferrari)
        - Sargeant (Williams - DNF)
        - Albon (Williams - pit lane start)
    - 1 race (2024 Round 1)
    - 6 race results with various grid/finish/status/points scenarios
    - 5 qualifying results with Q1/Q2/Q3 times
    - Pit stops with non-NULL and NULL durations (testing denominator filtering)
    - Lap times with non-NULL and NULL millis (testing denominator filtering)
    - Driver standings & Constructor standings for Round 1
    """
    # 1. Season
    season = Season(season_year=2024, url="https://en.wikipedia.org/wiki/2024_Formula_One_World_Championship")
    session.add(season)

    # 2. Circuit
    circuit = Circuit(
        circuit_id="bahrain",
        circuit_name="Bahrain International Circuit",
        locality="Sakhir",
        country="Bahrain",
        latitude=Decimal("26.0325"),
        longitude=Decimal("50.5106"),
    )
    session.add(circuit)
    session.flush()

    # 3. Race
    race = Race(
        season_year=2024,
        round=1,
        race_name="Bahrain Grand Prix",
        circuit_id=circuit.id,
        race_date=date(2024, 3, 2),
        race_time=time(15, 0, 0),
    )
    session.add(race)
    session.flush()

    # 4. Constructors
    red_bull = Constructor(constructor_id="red_bull", name="Red Bull", nationality="Austrian")
    ferrari = Constructor(constructor_id="ferrari", name="Ferrari", nationality="Italian")
    williams = Constructor(constructor_id="williams", name="Williams", nationality="British")
    session.add_all([red_bull, ferrari, williams])
    session.flush()

    # 5. Drivers
    verstappen = Driver(driver_id="max_verstappen", permanent_number=33, code="VER", given_name="Max", family_name="Verstappen", nationality="Dutch")
    perez = Driver(driver_id="perez", permanent_number=11, code="PER", given_name="Sergio", family_name="Perez", nationality="Mexican")
    leclerc = Driver(driver_id="leclerc", permanent_number=16, code="LEC", given_name="Charles", family_name="Leclerc", nationality="Monegasque")
    sainz = Driver(driver_id="sainz", permanent_number=55, code="SAI", given_name="Carlos", family_name="Sainz", nationality="Spanish")
    sargeant = Driver(driver_id="sargeant", permanent_number=2, code="SAR", given_name="Logan", family_name="Sargeant", nationality="American")
    albon = Driver(driver_id="albon", permanent_number=23, code="ALB", given_name="Alexander", family_name="Albon", nationality="Thai")
    session.add_all([verstappen, perez, leclerc, sainz, sargeant, albon])
    session.flush()

    # 6. Race Results
    # - Verstappen: grid 1, finish 1 (delta 0), 26 pts, winner, fastest lap
    rr_ver = RaceResult(
        race_id=race.id, driver_id=verstappen.id, constructor_id=red_bull.id,
        car_number=1, grid_position=1, source_position=1, position_text="1",
        points=Decimal("26.0"), laps_completed=57, status="Finished",
        time_millis=5504742, time_text="1:31:44.742",
        fastest_lap_rank=1, fastest_lap_number=39, fastest_lap_time="1:32.608", fastest_lap_time_millis=92608,
    )
    # - Perez: grid 5, finish 2 (delta +3), 18 pts
    rr_per = RaceResult(
        race_id=race.id, driver_id=perez.id, constructor_id=red_bull.id,
        car_number=11, grid_position=5, source_position=2, position_text="2",
        points=Decimal("18.0"), laps_completed=57, status="Finished",
        time_millis=5527199, time_text="+22.457",
        fastest_lap_rank=4, fastest_lap_number=37, fastest_lap_time="1:34.364", fastest_lap_time_millis=94364,
    )
    # - Sainz: grid 4, finish 3 (delta +1), 15 pts
    rr_sai = RaceResult(
        race_id=race.id, driver_id=sainz.id, constructor_id=ferrari.id,
        car_number=55, grid_position=4, source_position=3, position_text="3",
        points=Decimal("15.0"), laps_completed=57, status="Finished",
        time_millis=5529852, time_text="+25.110",
        fastest_lap_rank=3, fastest_lap_number=41, fastest_lap_time="1:34.090", fastest_lap_time_millis=94090,
    )
    # - Leclerc: grid 2, finish 4 (delta -2), 12 pts
    rr_lec = RaceResult(
        race_id=race.id, driver_id=leclerc.id, constructor_id=ferrari.id,
        car_number=16, grid_position=2, source_position=4, position_text="4",
        points=Decimal("12.0"), laps_completed=57, status="Finished",
        time_millis=5544440, time_text="+39.698",
        fastest_lap_rank=5, fastest_lap_number=36, fastest_lap_time="1:34.090", fastest_lap_time_millis=94090,
    )
    # - Sargeant: DNF, grid 18, source_position None, position_text "R", 0 pts
    rr_sar = RaceResult(
        race_id=race.id, driver_id=sargeant.id, constructor_id=williams.id,
        car_number=2, grid_position=18, source_position=None, position_text="R",
        points=Decimal("0.0"), laps_completed=24, status="Engine",
        time_millis=None, time_text=None,
    )
    # - Albon: pit lane start, grid None, finish 10, position_text "10", 1 pt
    rr_alb = RaceResult(
        race_id=race.id, driver_id=albon.id, constructor_id=williams.id,
        car_number=23, grid_position=None, source_position=10, position_text="10",
        points=Decimal("1.0"), laps_completed=57, status="Finished",
        time_millis=5590000, time_text="+1:25.258",
    )
    session.add_all([rr_ver, rr_per, rr_sai, rr_lec, rr_sar, rr_alb])
    session.flush()

    # 7. Qualifying Results
    qr_ver = QualifyingResult(
        race_id=race.id, driver_id=verstappen.id, constructor_id=red_bull.id,
        car_number=1, position=1,
        q1_time="1:30.031", q1_time_millis=90031,
        q2_time="1:29.374", q2_time_millis=89374,
        q3_time="1:29.179", q3_time_millis=89179,
    )
    qr_lec = QualifyingResult(
        race_id=race.id, driver_id=leclerc.id, constructor_id=ferrari.id,
        car_number=16, position=2,
        q1_time="1:30.243", q1_time_millis=90243,
        q2_time="1:29.165", q2_time_millis=89165,
        q3_time="1:29.407", q3_time_millis=89407,
    )
    qr_sai = QualifyingResult(
        race_id=race.id, driver_id=sainz.id, constructor_id=ferrari.id,
        car_number=55, position=4,
        q1_time="1:29.909", q1_time_millis=89909,
        q2_time="1:29.573", q2_time_millis=89573,
        q3_time="1:29.507", q3_time_millis=89507,
    )
    qr_per = QualifyingResult(
        race_id=race.id, driver_id=perez.id, constructor_id=red_bull.id,
        car_number=11, position=5,
        q1_time="1:30.221", q1_time_millis=90221,
        q2_time="1:29.932", q2_time_millis=89932,
        q3_time="1:29.537", q3_time_millis=89537,
    )
    qr_sar = QualifyingResult(
        race_id=race.id, driver_id=sargeant.id, constructor_id=williams.id,
        car_number=2, position=18,
        q1_time="1:30.770", q1_time_millis=90770,
        q2_time=None, q2_time_millis=None,
        q3_time=None, q3_time_millis=None,
    )
    session.add_all([qr_ver, qr_lec, qr_sai, qr_per, qr_sar])
    session.flush()

    # 8. Pit Stops
    ps_ver1 = PitStop(race_id=race.id, driver_id=verstappen.id, stop_number=1, lap=17, time_of_day="18:31:18", duration_text="24.123", duration_millis=24123)
    ps_ver2 = PitStop(race_id=race.id, driver_id=verstappen.id, stop_number=2, lap=37, time_of_day="19:04:05", duration_text="23.856", duration_millis=23856)
    ps_per1 = PitStop(race_id=race.id, driver_id=perez.id, stop_number=1, lap=12, time_of_day="18:23:01", duration_text="24.500", duration_millis=24500)
    ps_per2 = PitStop(race_id=race.id, driver_id=perez.id, stop_number=2, lap=36, time_of_day="19:02:10", duration_text="24.200", duration_millis=24200)
    ps_lec1 = PitStop(race_id=race.id, driver_id=leclerc.id, stop_number=1, lap=11, time_of_day="18:21:40", duration_text="25.100", duration_millis=25100)
    # Stop with NULL duration (testing denominator filtering)
    ps_sai1 = PitStop(race_id=race.id, driver_id=sainz.id, stop_number=1, lap=14, time_of_day="18:26:00", duration_text=None, duration_millis=None)
    session.add_all([ps_ver1, ps_ver2, ps_per1, ps_per2, ps_lec1, ps_sai1])
    session.flush()

    # 9. Lap Times
    lt_ver1 = LapTime(race_id=race.id, driver_id=verstappen.id, lap_number=1, position=1, time="1:36.415", time_millis=96415)
    lt_ver2 = LapTime(race_id=race.id, driver_id=verstappen.id, lap_number=39, position=1, time="1:32.608", time_millis=92608)
    lt_lec1 = LapTime(race_id=race.id, driver_id=leclerc.id, lap_number=1, position=2, time="1:37.100", time_millis=97100)
    # Lap with NULL time_millis (e.g. unrecorded / out of track limits)
    lt_lec2 = LapTime(race_id=race.id, driver_id=leclerc.id, lap_number=2, position=2, time="IN PIT", time_millis=None)
    session.add_all([lt_ver1, lt_ver2, lt_lec1, lt_lec2])
    session.flush()

    # 10. Standings
    ds_ver = DriverStanding(season_year=2024, round=1, driver_id=verstappen.id, position=1, points=Decimal("26.0"), wins=1)
    ds_per = DriverStanding(season_year=2024, round=1, driver_id=perez.id, position=2, points=Decimal("18.0"), wins=0)
    ds_sai = DriverStanding(season_year=2024, round=1, driver_id=sainz.id, position=3, points=Decimal("15.0"), wins=0)
    ds_lec = DriverStanding(season_year=2024, round=1, driver_id=leclerc.id, position=4, points=Decimal("12.0"), wins=0)
    session.add_all([ds_ver, ds_per, ds_sai, ds_lec])

    cs_rb = ConstructorStanding(season_year=2024, round=1, constructor_id=red_bull.id, position=1, points=Decimal("44.0"), wins=1)
    cs_fe = ConstructorStanding(season_year=2024, round=1, constructor_id=ferrari.id, position=2, points=Decimal("27.0"), wins=0)
    session.add_all([cs_rb, cs_fe])
    session.flush()

    return {
        "season_year": 2024,
        "round": 1,
        "race": race,
        "circuit": circuit,
        "constructors": {"red_bull": red_bull, "ferrari": ferrari, "williams": williams},
        "drivers": {
            "max_verstappen": verstappen,
            "perez": perez,
            "leclerc": leclerc,
            "sainz": sainz,
            "sargeant": sargeant,
            "albon": albon,
        },
    }

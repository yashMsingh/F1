"""Test database schema structure, model declarations, and table mappings."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import inspect

from app.db.base import Base
from app.db.models import (
    Circuit,
    Constructor,
    ConstructorStanding,
    Driver,
    DriverStanding,
    EtlLog,
    LapTime,
    PitStop,
    QualifyingResult,
    Race,
    RaceResult,
    Season,
    SprintResult,
)


def test_all_tables_registered():
    """Verify that all 13 Phase 1 tables are registered in Base.metadata."""
    expected_tables = {
        "seasons",
        "circuits",
        "constructors",
        "drivers",
        "races",
        "race_results",
        "qualifying_results",
        "sprint_results",
        "pit_stops",
        "lap_times",
        "driver_standings",
        "constructor_standings",
        "etl_log",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_nullable_source_fields_driver():
    """Verify nullable fields on Driver model (permanent_number, code, date_of_birth, nationality, url)."""
    table = Base.metadata.tables["drivers"]
    assert table.c.permanent_number.nullable is True
    assert table.c.code.nullable is True
    assert table.c.date_of_birth.nullable is True
    assert table.c.nationality.nullable is True
    assert table.c.url.nullable is True
    # Non-nullable
    assert table.c.driver_id.nullable is False
    assert table.c.given_name.nullable is False
    assert table.c.family_name.nullable is False


def test_nullable_source_fields_race_result():
    """Verify nullable fields on RaceResult model (grid_position, source_position, time_millis, time_text, fastest_lap)."""
    table = Base.metadata.tables["race_results"]
    assert table.c.car_number.nullable is True
    assert table.c.grid_position.nullable is True
    assert table.c.source_position.nullable is True
    assert table.c.time_millis.nullable is True
    assert table.c.time_text.nullable is True
    assert table.c.fastest_lap_rank.nullable is True
    assert table.c.fastest_lap_number.nullable is True
    assert table.c.fastest_lap_time.nullable is True
    assert table.c.fastest_lap_time_millis.nullable is True
    # Non-nullable
    assert table.c.race_id.nullable is False
    assert table.c.driver_id.nullable is False
    assert table.c.constructor_id.nullable is False
    assert table.c.position_text.nullable is False
    assert table.c.points.nullable is False
    assert table.c.laps_completed.nullable is False
    assert table.c.status.nullable is False


def test_nullable_source_fields_qualifying_result():
    """Verify nullable fields on QualifyingResult model (Q1, Q2, Q3 raw and ms)."""
    table = Base.metadata.tables["qualifying_results"]
    assert table.c.car_number.nullable is True
    assert table.c.q1_time.nullable is True
    assert table.c.q1_time_millis.nullable is True
    assert table.c.q2_time.nullable is True
    assert table.c.q2_time_millis.nullable is True
    assert table.c.q3_time.nullable is True
    assert table.c.q3_time_millis.nullable is True
    # Non-nullable
    assert table.c.position.nullable is False


def test_pit_stop_duration_fields():
    """Verify pit stop duration supports both raw string text and parsed milliseconds."""
    table = Base.metadata.tables["pit_stops"]
    assert table.c.duration_text.nullable is True
    assert table.c.duration_millis.nullable is True
    assert table.c.time_of_day.nullable is True
    # Non-nullable
    assert table.c.race_id.nullable is False
    assert table.c.driver_id.nullable is False
    assert table.c.stop_number.nullable is False
    assert table.c.lap.nullable is False


def test_etl_log_schema_provenance():
    """Verify etl_log table supports provenance fields (source_url, endpoint, error_message)."""
    table = Base.metadata.tables["etl_log"]
    assert "source" in table.c
    assert "entity_type" in table.c
    assert "endpoint" in table.c
    assert "source_url" in table.c
    assert "season_year" in table.c
    assert "round" in table.c
    assert "status" in table.c
    assert "records_processed" in table.c
    assert "records_inserted" in table.c
    assert "records_updated" in table.c
    assert "records_skipped" in table.c
    assert "error_message" in table.c
    assert "started_at" in table.c
    assert "completed_at" in table.c

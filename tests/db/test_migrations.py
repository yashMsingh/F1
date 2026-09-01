"""Tests for Alembic migration lifecycle: upgrade head, downgrade base, upgrade head."""

from alembic import command
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_downgrade_cycle(alembic_config, migration_db_url):
    """Test 1 & 9 — Migration reproducibility: Run upgrade head -> downgrade base -> upgrade head from scratch."""
    migration_engine = create_engine(migration_db_url)

    # 1. Verify initial database is completely empty
    inspector = inspect(migration_engine)
    tables_initial = set(inspector.get_table_names())
    assert len(tables_initial) == 0, f"Expected empty database, found {tables_initial}"

    # 2. Upgrade to head
    command.upgrade(alembic_config, "head")

    inspector = inspect(migration_engine)
    tables_after_upgrade = set(inspector.get_table_names())

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
    assert expected_tables.issubset(tables_after_upgrade), (
        f"Missing tables after upgrade: {expected_tables - tables_after_upgrade}"
    )

    # 3. Downgrade to base to ensure downgrade drops all tables
    command.downgrade(alembic_config, "base")
    inspector = inspect(migration_engine)
    tables_after_downgrade = set(inspector.get_table_names())
    assert "races" not in tables_after_downgrade
    assert "drivers" not in tables_after_downgrade
    assert "race_results" not in tables_after_downgrade

    # 4. Final upgrade to verify reproducibility
    command.upgrade(alembic_config, "head")
    inspector = inspect(migration_engine)
    tables_final = set(inspector.get_table_names())
    assert expected_tables.issubset(tables_final)

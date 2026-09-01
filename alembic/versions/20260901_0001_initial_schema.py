"""Initial Phase 1 schema creation.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-01 23:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. seasons
    op.create_table(
        "seasons",
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("season_year"),
    )

    # 2. circuits
    op.create_table(
        "circuits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("circuit_id", sa.String(length=100), nullable=False),
        sa.Column("circuit_name", sa.String(length=255), nullable=False),
        sa.Column("locality", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("circuit_id"),
    )
    op.create_index("idx_circuits_circuit_id", "circuits", ["circuit_id"])

    # 3. constructors
    op.create_table(
        "constructors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("constructor_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("nationality", sa.String(length=100), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("constructor_id"),
    )
    op.create_index("idx_constructors_constructor_id", "constructors", ["constructor_id"])

    # 4. drivers
    op.create_table(
        "drivers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("driver_id", sa.String(length=100), nullable=False),
        sa.Column("permanent_number", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=3), nullable=True),
        sa.Column("given_name", sa.String(length=255), nullable=False),
        sa.Column("family_name", sa.String(length=255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("nationality", sa.String(length=100), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("driver_id"),
    )
    op.create_index("idx_drivers_driver_id", "drivers", ["driver_id"])

    # 5. races
    op.create_table(
        "races",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("race_name", sa.String(length=255), nullable=False),
        sa.Column("circuit_id", sa.Integer(), nullable=False),
        sa.Column("race_date", sa.Date(), nullable=False),
        sa.Column("race_time", sa.Time(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["circuit_id"], ["circuits.id"]),
        sa.ForeignKeyConstraint(["season_year"], ["seasons.season_year"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_year", "round", name="uq_races_season_round"),
    )
    op.create_index("idx_races_circuit", "races", ["circuit_id"])
    op.create_index("idx_races_season", "races", ["season_year"])

    # 6. race_results
    op.create_table(
        "race_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("constructor_id", sa.Integer(), nullable=False),
        sa.Column("car_number", sa.Integer(), nullable=True),
        sa.Column("grid_position", sa.Integer(), nullable=True),
        sa.Column("source_position", sa.Integer(), nullable=True),
        sa.Column("position_text", sa.String(length=10), nullable=False),
        sa.Column("points", sa.Numeric(precision=5, scale=2), server_default="0", nullable=False),
        sa.Column("laps_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("time_millis", sa.BigInteger(), nullable=True),
        sa.Column("time_text", sa.String(length=50), nullable=True),
        sa.Column("fastest_lap_rank", sa.Integer(), nullable=True),
        sa.Column("fastest_lap_number", sa.Integer(), nullable=True),
        sa.Column("fastest_lap_time", sa.String(length=20), nullable=True),
        sa.Column("fastest_lap_time_millis", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["constructor_id"], ["constructors.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["race_id"], ["races.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("race_id", "driver_id", name="uq_race_results_race_driver"),
    )
    op.create_index("idx_race_results_constructor", "race_results", ["constructor_id"])
    op.create_index("idx_race_results_driver", "race_results", ["driver_id"])
    op.create_index("idx_race_results_race", "race_results", ["race_id"])

    # 7. qualifying_results
    op.create_table(
        "qualifying_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("constructor_id", sa.Integer(), nullable=False),
        sa.Column("car_number", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("q1_time", sa.String(length=20), nullable=True),
        sa.Column("q1_time_millis", sa.Integer(), nullable=True),
        sa.Column("q2_time", sa.String(length=20), nullable=True),
        sa.Column("q2_time_millis", sa.Integer(), nullable=True),
        sa.Column("q3_time", sa.String(length=20), nullable=True),
        sa.Column("q3_time_millis", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["constructor_id"], ["constructors.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["race_id"], ["races.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("race_id", "driver_id", name="uq_qualifying_results_race_driver"),
    )
    op.create_index("idx_qualifying_driver", "qualifying_results", ["driver_id"])
    op.create_index("idx_qualifying_race", "qualifying_results", ["race_id"])

    # 8. sprint_results
    op.create_table(
        "sprint_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("constructor_id", sa.Integer(), nullable=False),
        sa.Column("car_number", sa.Integer(), nullable=True),
        sa.Column("grid_position", sa.Integer(), nullable=True),
        sa.Column("source_position", sa.Integer(), nullable=True),
        sa.Column("position_text", sa.String(length=10), nullable=False),
        sa.Column("points", sa.Numeric(precision=5, scale=2), server_default="0", nullable=False),
        sa.Column("laps_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("time_millis", sa.BigInteger(), nullable=True),
        sa.Column("time_text", sa.String(length=50), nullable=True),
        sa.Column("fastest_lap_rank", sa.Integer(), nullable=True),
        sa.Column("fastest_lap_number", sa.Integer(), nullable=True),
        sa.Column("fastest_lap_time", sa.String(length=20), nullable=True),
        sa.Column("fastest_lap_time_millis", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["constructor_id"], ["constructors.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["race_id"], ["races.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("race_id", "driver_id", name="uq_sprint_results_race_driver"),
    )
    op.create_index("idx_sprint_race", "sprint_results", ["race_id"])

    # 9. pit_stops
    op.create_table(
        "pit_stops",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("stop_number", sa.Integer(), nullable=False),
        sa.Column("lap", sa.Integer(), nullable=False),
        sa.Column("time_of_day", sa.String(length=20), nullable=True),
        sa.Column("duration_text", sa.String(length=20), nullable=True),
        sa.Column("duration_millis", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["race_id"], ["races.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("race_id", "driver_id", "stop_number", name="uq_pit_stops_race_driver_stop"),
    )
    op.create_index("idx_pit_stops_driver", "pit_stops", ["driver_id"])
    op.create_index("idx_pit_stops_race", "pit_stops", ["race_id"])

    # 10. lap_times
    op.create_table(
        "lap_times",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("lap_number", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("time", sa.String(length=20), nullable=False),
        sa.Column("time_millis", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["race_id"], ["races.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("race_id", "driver_id", "lap_number", name="uq_lap_times_race_driver_lap"),
    )
    op.create_index("idx_lap_times_driver", "lap_times", ["driver_id"])
    op.create_index("idx_lap_times_race", "lap_times", ["race_id"])
    op.create_index("idx_lap_times_race_lap", "lap_times", ["race_id", "lap_number"])

    # 11. driver_standings
    op.create_table(
        "driver_standings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("wins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["season_year"], ["seasons.season_year"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_year", "round", "driver_id", name="uq_driver_standings_season_round_driver"),
    )
    op.create_index("idx_driver_standings_season", "driver_standings", ["season_year"])

    # 12. constructor_standings
    op.create_table(
        "constructor_standings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("constructor_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("wins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["constructor_id"], ["constructors.id"]),
        sa.ForeignKeyConstraint(["season_year"], ["seasons.season_year"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_year", "round", "constructor_id", name="uq_constructor_standings_season_round_constructor"),
    )
    op.create_index("idx_constructor_standings_season", "constructor_standings", ["season_year"])

    # 13. etl_log
    op.create_table(
        "etl_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("season_year", sa.Integer(), nullable=True),
        sa.Column("round", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("records_processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("etl_log")
    op.drop_index("idx_constructor_standings_season", table_name="constructor_standings")
    op.drop_table("constructor_standings")
    op.drop_index("idx_driver_standings_season", table_name="driver_standings")
    op.drop_table("driver_standings")
    op.drop_index("idx_lap_times_race_lap", table_name="lap_times")
    op.drop_index("idx_lap_times_race", table_name="lap_times")
    op.drop_index("idx_lap_times_driver", table_name="lap_times")
    op.drop_table("lap_times")
    op.drop_index("idx_pit_stops_race", table_name="pit_stops")
    op.drop_index("idx_pit_stops_driver", table_name="pit_stops")
    op.drop_table("pit_stops")
    op.drop_index("idx_sprint_race", table_name="sprint_results")
    op.drop_table("sprint_results")
    op.drop_index("idx_qualifying_race", table_name="qualifying_results")
    op.drop_index("idx_qualifying_driver", table_name="qualifying_results")
    op.drop_table("qualifying_results")
    op.drop_index("idx_race_results_race", table_name="race_results")
    op.drop_index("idx_race_results_driver", table_name="race_results")
    op.drop_index("idx_race_results_constructor", table_name="race_results")
    op.drop_table("race_results")
    op.drop_index("idx_races_season", table_name="races")
    op.drop_index("idx_races_circuit", table_name="races")
    op.drop_table("races")
    op.drop_index("idx_drivers_driver_id", table_name="drivers")
    op.drop_table("drivers")
    op.drop_index("idx_constructors_constructor_id", table_name="constructors")
    op.drop_table("constructors")
    op.drop_index("idx_circuits_circuit_id", table_name="circuits")
    op.drop_table("circuits")
    op.drop_table("seasons")

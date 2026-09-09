"""F1 Race Intelligence — Controlled Real-Data Ingestion Script: 2024 Bahrain GP.

Usage:
    python scripts/ingest_bahrain_2024.py

This script performs the first real-world end-to-end ingestion of F1 data:
1. Connects to the database (PostgreSQL or isolated SQLite with FK enforcement).
2. Uses JolpicaClient to retrieve real 2024 Bahrain GP data.
3. Passes responses through Phase 2B.2 parsers.
4. Persists data via ETLService repositories in dependency order.
5. Performs database integrity and sanity checks.
6. Performs an idempotency test (second run verifies 0 inserts, 0 duplicates).
7. Inspects etl_log audit records.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.orm import sessionmaker

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
from app.etl.runners.bahrain_2024 import ingest_bahrain_2024
from app.etl.service import ETLService
from app.etl.types import IngestionStatus
from app.f1.client import JolpicaClient

load_dotenv(project_root / ".env")


def get_target_engine():
    """Determine database engine: PostgreSQL if accessible, else SQLite file."""
    env_url = os.environ.get("DATABASE_URL", "")
    db_type = "UNKNOWN"

    if env_url.startswith("postgresql"):
        try:
            test_eng = create_engine(env_url, connect_args={"connect_timeout": 2})
            with test_eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[DB] Connected to PostgreSQL: {env_url.split('@')[-1]}")
            return test_eng, "PostgreSQL"
        except Exception as e:
            print(f"[DB] PostgreSQL connection failed ({e}). Falling back to SQLite.")

    # SQLite fallback
    db_file = project_root / "data" / "f1_bahrain_2024.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    sqlite_url = f"sqlite:///{db_file}"
    print(f"[DB] Using SQLite file: {db_file}")

    eng = create_engine(sqlite_url, echo=False)

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng, "SQLite"


def verify_database_state(session) -> dict[str, int]:
    """Execute SQL row count queries across all 12 entities."""
    counts = {
        "seasons": session.scalar(select(func.count()).select_from(Season)),
        "circuits": session.scalar(select(func.count()).select_from(Circuit)),
        "constructors": session.scalar(select(func.count()).select_from(Constructor)),
        "drivers": session.scalar(select(func.count()).select_from(Driver)),
        "races": session.scalar(select(func.count()).select_from(Race)),
        "race_results": session.scalar(select(func.count()).select_from(RaceResult)),
        "qualifying_results": session.scalar(select(func.count()).select_from(QualifyingResult)),
        "sprint_results": session.scalar(select(func.count()).select_from(SprintResult)),
        "pit_stops": session.scalar(select(func.count()).select_from(PitStop)),
        "lap_times": session.scalar(select(func.count()).select_from(LapTime)),
        "driver_standings": session.scalar(select(func.count()).select_from(DriverStanding)),
        "constructor_standings": session.scalar(select(func.count()).select_from(ConstructorStanding)),
        "etl_logs": session.scalar(select(func.count()).select_from(EtlLog)),
    }
    return counts


def main() -> int:
    print("=" * 70)
    print("F1 Race Intelligence — Controlled Ingestion: 2024 Bahrain GP")
    print("=" * 70)

    engine, db_type = get_target_engine()
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    client = JolpicaClient()

    # ── RUN 1: First-Run Ingestion ───────────────────────────────────────────
    print("\n>>> [RUN 1] Starting initial ingestion of 2024 Bahrain GP...")
    with SessionLocal() as session:
        service = ETLService(session=session, auto_commit=True)
        res1 = ingest_bahrain_2024(client, service)

    print(f"[RUN 1 Outcome] Status: {res1.status.value}")
    print(f"  Processed: {res1.stats.records_processed}")
    print(f"  Inserted:  {res1.stats.records_inserted}")
    print(f"  Updated:   {res1.stats.records_updated}")
    print(f"  Skipped:   {res1.stats.records_skipped}")
    print(f"  Failed:    {res1.stats.records_failed}")

    if res1.status != IngestionStatus.SUCCESS:
        print(f"[ERROR] Run 1 failed: {res1.error_message}")
        return 1

    # ── VERIFICATION: Database Checks ────────────────────────────────────────
    print("\n>>> Verifying database integrity and factual accuracy...")
    with SessionLocal() as session:
        counts1 = verify_database_state(session)
        print("\n--- Row Counts in Database ---")
        for table, count in counts1.items():
            print(f"  {table:<24}: {count}")

        # Factual integrity checks
        race = session.scalars(select(Race).where(Race.season_year == 2024, Race.round == 1)).first()
        assert race is not None, "Race record not found"
        assert race.race_name == "Bahrain Grand Prix"

        winner_result = session.scalars(
            select(RaceResult).where(RaceResult.race_id == race.id, RaceResult.source_position == 1)
        ).first()
        assert winner_result is not None, "Race winner result not found"
        winner_driver = session.get(Driver, winner_result.driver_id)
        assert winner_driver is not None and winner_driver.driver_id == "max_verstappen"
        assert winner_result.points == 26, f"Expected 26 points, got {winner_result.points}"
        assert winner_result.laps_completed == 57

        pole_result = session.scalars(
            select(QualifyingResult).where(QualifyingResult.race_id == race.id, QualifyingResult.position == 1)
        ).first()
        assert pole_result is not None, "Pole position result not found"
        pole_driver = session.get(Driver, pole_result.driver_id)
        assert pole_driver is not None and pole_driver.driver_id == "max_verstappen"

        print("\n[VERIFICATION PASS] Factual checks confirmed:")
        print(f"  Winner:  {winner_driver.given_name} {winner_driver.family_name} ({winner_result.points} pts, {winner_result.laps_completed} laps)")
        print(f"  Pole:    {pole_driver.given_name} {pole_driver.family_name} (Q3: {pole_result.q3_time})")
        print(f"  Pit stops: {counts1['pit_stops']} recorded")
        print(f"  Lap times: {counts1['lap_times']} recorded")

    # ── RUN 2: Idempotency Verification ──────────────────────────────────────
    print("\n>>> [RUN 2] Running second identical ingestion (Idempotency Test)...")
    with SessionLocal() as session:
        service = ETLService(session=session, auto_commit=True)
        res2 = ingest_bahrain_2024(client, service)

    print(f"[RUN 2 Outcome] Status: {res2.status.value}")
    print(f"  Processed: {res2.stats.records_processed}")
    print(f"  Inserted:  {res2.stats.records_inserted}")
    print(f"  Updated:   {res2.stats.records_updated}")
    print(f"  Skipped:   {res2.stats.records_skipped}")
    print(f"  Failed:    {res2.stats.records_failed}")

    with SessionLocal() as session:
        counts2 = verify_database_state(session)

    # Check zero duplicates
    assert res2.stats.records_inserted == 0, f"Expected 0 inserts on Run 2, got {res2.stats.records_inserted}"
    assert res2.stats.records_skipped > 0, "Expected records to be skipped on Run 2"
    for table in counts1:
        if table != "etl_logs":
            assert counts1[table] == counts2[table], f"Table {table} row count changed from {counts1[table]} to {counts2[table]}"

    print("\n[IDEMPOTENCY PASS] Exactly 0 records inserted on second run; row counts strictly identical.")

    # ── ETL LOG VERIFICATION ─────────────────────────────────────────────────
    print("\n>>> Inspecting etl_log audit records...")
    with SessionLocal() as session:
        logs = session.scalars(select(EtlLog).order_by(EtlLog.id.desc()).limit(5)).all()
        for log in logs:
            print(f"  [Log #{log.id}] Entity: {log.entity_type:<15} Status: {log.status:<10} Processed: {log.records_processed:<5} Inserted: {log.records_inserted:<5} Skipped: {log.records_skipped:<5}")

    print("\n" + "=" * 70)
    print(f"CONTROLLED INGESTION COMPLETE: 2024 Bahrain GP successfully persisted in {db_type}!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

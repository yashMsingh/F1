"""F1 Race Intelligence — Controlled Historical Data Ingestion CLI.

Usage:
    python scripts/ingest_historical.py --season 2024 --start 1 --end 5
    python scripts/ingest_historical.py --season 2024 --start 1 --end 5 --no-laps

Ingests a contiguous slice of Grand Prix race weekends using the Phase 2B/3A
ETL pipeline into the active database (PostgreSQL or SQLite fallback).
"""

from __future__ import annotations

import argparse
import logging
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
from app.etl.runners.season_slice import ingest_season_slice
from app.etl.service import ETLService
from app.etl.types import IngestionStatus
from app.f1.client import JolpicaClient

load_dotenv(project_root / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ingest_historical")


def get_target_engine():
    """Determine database engine: PostgreSQL if accessible, else SQLite file."""
    env_url = os.environ.get("DATABASE_URL", "")

    if env_url.startswith("postgresql"):
        try:
            test_eng = create_engine(env_url, connect_args={"connect_timeout": 3})
            with test_eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[DB] Connected to PostgreSQL: {env_url.split('@')[-1]}")
            return test_eng, "PostgreSQL"
        except Exception as e:
            print(f"[DB] PostgreSQL connection failed ({e}). Falling back to SQLite.")

    # SQLite fallback
    db_file = project_root / "data" / "f1_historical.db"
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
    """Execute SQL row count queries across all 12 core entities."""
    return {
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


def main() -> int:
    parser = argparse.ArgumentParser(description="F1 Historical Race Data Ingestion")
    parser.add_argument("--season", type=int, default=2024, help="Season year (default: 2024)")
    parser.add_argument("--start", type=int, default=1, help="Starting round (default: 1)")
    parser.add_argument("--end", type=int, default=5, help="Ending round (default: 5)")
    parser.add_argument("--no-laps", action="store_true", help="Skip granular lap times for faster ingestion")
    parser.add_argument("--pace-delay", type=float, default=0.25, help="Delay in seconds between API requests (default: 0.25)")
    args = parser.parse_args()

    print("=" * 70)
    print(f"F1 Race Intelligence — Historical Ingestion: {args.season} Rounds {args.start} to {args.end}")
    print("=" * 70)

    engine, db_type = get_target_engine()
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    client = JolpicaClient()

    with SessionLocal() as session:
        service = ETLService(session=session, auto_commit=True)
        results = ingest_season_slice(
            client=client,
            service=service,
            season_year=args.season,
            start_round=args.start,
            end_round=args.end,
            include_laps=not args.no_laps,
            pace_delay_seconds=args.pace_delay,
        )

    print("\n" + "-" * 70)
    print("INGESTION ROUND SUMMARY")
    print("-" * 70)
    total_processed = sum(r.stats.records_processed for r in results)
    total_inserted = sum(r.stats.records_inserted for r in results)
    total_skipped = sum(r.stats.records_skipped for r in results)
    total_updated = sum(r.stats.records_updated for r in results)

    for i, res in enumerate(results, start=args.start):
        print(f"  Round {i:<2}: Status={res.status.value:<7} Processed={res.stats.records_processed:<5} Inserted={res.stats.records_inserted:<5} Skipped={res.stats.records_skipped:<5}")

    print(f"\nTotals: Processed={total_processed}, Inserted={total_inserted}, Skipped={total_skipped}, Updated={total_updated}")

    # Database Verification
    print("\n>>> Current Database Row Counts:")
    with SessionLocal() as session:
        counts = verify_database_state(session)
        for table, count in counts.items():
            print(f"  {table:<24}: {count}")

        # Summary of races present
        races = session.scalars(
            select(Race).where(Race.season_year == args.season).order_by(Race.round.asc())
        ).all()
        print(f"\nRaces currently in database for {args.season} ({len(races)} total):")
        for r in races:
            print(f"  Round {r.round}: {r.race_name} ({r.race_date})")

    print("\n" + "=" * 70)
    print(f"HISTORICAL INGESTION COMPLETED: {db_type}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

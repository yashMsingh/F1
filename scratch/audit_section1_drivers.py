"""
Phase 5B.0.1 Section 1: Driver Entity and Championship Eligibility Audit
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@127.0.0.1:5432/f1_race_intelligence")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("=== All 25 drivers in drivers table and their 2024 participation ===")
    rows = conn.execute(text("""
        SELECT
            d.id,
            d.driver_id,
            d.given_name || ' ' || d.family_name AS full_name,
            d.permanent_number,
            d.code,
            COUNT(DISTINCT rr.id) AS race_starts,
            COUNT(DISTINCT qr.id) AS quali_entries,
            COUNT(DISTINCT sr.id) AS sprint_entries,
            COUNT(DISTINCT ds.id) AS standings_entries,
            COALESCE(MAX(ds.position), NULL) AS latest_standing
        FROM drivers d
        LEFT JOIN race_results rr ON rr.driver_id = d.id
        LEFT JOIN qualifying_results qr ON qr.driver_id = d.id
        LEFT JOIN sprint_results sr ON sr.driver_id = d.id
        LEFT JOIN driver_standings ds ON ds.driver_id = d.id AND ds.season_year = 2024
        GROUP BY d.id, d.driver_id, d.given_name, d.family_name, d.permanent_number, d.code
        ORDER BY race_starts DESC, d.driver_id
    """)).fetchall()

    for r in rows:
        tag = ""
        if r[5] == 0:
            tag = " *** REFERENCE ENTITY (0 starts) ***"
        elif r[5] < 24:
            tag = f" *** PARTIAL SEASON ({r[5]} starts) ***"
        print(f"  {r[1]:<16} {r[2]:<25} starts={r[5]:>2} quali={r[6]:>2} sprint={r[7]:>2} standings={r[8]:>2} P{r[9] if r[9] else 'None'}{tag}")

    print("\n=== Antonelli details ===")
    ant = conn.execute(text("""
        SELECT * FROM drivers WHERE driver_id = 'antonelli'
    """)).mappings().first()
    print("Antonelli driver record:", dict(ant) if ant else "NOT FOUND")

    # Check if Antonelli appears anywhere else
    tables = ["race_results", "qualifying_results", "sprint_results", "driver_standings", "pit_stops", "lap_times"]
    for t in tables:
        cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t} WHERE driver_id = :d_id"), {"d_id": ant["id"] if ant else -1}).scalar()
        print(f"  Antonelli in {t}: {cnt}")

    # Check ETL provenance of Antonelli
    print("\n=== ETL provenance of Antonelli ===")
    etl_rows = conn.execute(text("""
        SELECT id, season_year, round, status, created_at, source_url
        FROM etl_log
        WHERE season_year = 2024
        ORDER BY id
    """)).fetchall()
    print(f"Total ETL log entries: {len(etl_rows)}")

"""Sprint round distribution check for Phase 5A documentation."""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/f1_race_intelligence")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("=== Sprint results per round ===")
    rows = conn.execute(text("""
        SELECT r.round, r.race_name, COUNT(sr.id) as sprint_count
        FROM races r
        LEFT JOIN sprint_results sr ON r.id = sr.race_id
        WHERE r.season_year = 2024
        GROUP BY r.round, r.race_name
        ORDER BY r.round
    """)).fetchall()
    for row in rows:
        flag = " *** SPRINT ***" if row[2] > 0 else ""
        print(f"  R{row[0]:02d} {row[1]:<40} sprint_results={row[2]}{flag}")

    print()
    print("=== All 13 table counts ===")
    tables = [
        "seasons","circuits","constructors","drivers","races",
        "race_results","qualifying_results","sprint_results",
        "pit_stops","lap_times","driver_standings","constructor_standings","etl_log"
    ]
    for t in tables:
        cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"  {t:<30} {cnt}")

    print()
    print("=== ETL log summary ===")
    etl = conn.execute(text("""
        SELECT status, COUNT(*) FROM etl_log GROUP BY status ORDER BY status
    """)).fetchall()
    for row in etl:
        print(f"  {row[0]}: {row[1]}")

    print()
    print("=== New drivers added in R16-24 ===")
    new_drivers = conn.execute(text("""
        SELECT d.driver_id, d.given_name, d.family_name,
               COUNT(rr.id) as race_starts
        FROM drivers d
        LEFT JOIN race_results rr ON d.driver_id = rr.driver_id
        WHERE d.driver_id IN ('lawson', 'antonelli', 'colapinto', 'doohan')
        GROUP BY d.driver_id, d.given_name, d.family_name
        ORDER BY d.driver_id
    """)).fetchall()
    for row in new_drivers:
        print(f"  {row[0]:<15} {row[1]} {row[2]:<20} starts={row[3]}")

    print()
    print("=== Bearman full-season race count ===")
    bearman = conn.execute(text("""
        SELECT r.round, r.race_name, rr.position, rr.points
        FROM race_results rr
        JOIN races r ON rr.race_id = r.id
        WHERE rr.driver_id = 'bearman' AND r.season_year = 2024
        ORDER BY r.round
    """)).fetchall()
    for row in bearman:
        print(f"  R{row[0]:02d} {row[1]:<35} P{row[2]}  pts={row[3]}")
    print(f"  Total Bearman race entries: {len(bearman)}")

print("Done.")

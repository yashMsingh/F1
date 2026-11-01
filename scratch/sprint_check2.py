"""Sprint round distribution check for Phase 5A documentation — fixed queries."""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@localhost:5432/f1_race_intelligence")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check race_results columns
    cols = conn.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'race_results' ORDER BY ordinal_position LIMIT 10
    """)).fetchall()
    print("race_results columns:", [(c[0], c[1]) for c in cols])

    print()
    print("=== New/notable drivers R16-24 ===")
    new_drivers = conn.execute(text("""
        SELECT d.driver_id, d.given_name, d.family_name,
               COUNT(rr.id) as race_starts
        FROM drivers d
        LEFT JOIN race_results rr ON d.id = rr.driver_id
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
        JOIN drivers d ON rr.driver_id = d.id
        WHERE d.driver_id = 'bearman' AND r.season_year = 2024
        ORDER BY r.round
    """)).fetchall()
    for row in bearman:
        print(f"  R{row[0]:02d} {row[1]:<35} P{row[2]}  pts={row[3]}")
    print(f"  Total Bearman entries through R24: {len(bearman)}")

    print()
    print("=== Colapinto: reference vs race driver ===")
    colapinto = conn.execute(text("""
        SELECT r.round, r.race_name, rr.position, rr.points
        FROM race_results rr
        JOIN races r ON rr.race_id = r.id
        JOIN drivers d ON rr.driver_id = d.id
        WHERE d.driver_id = 'colapinto' AND r.season_year = 2024
        ORDER BY r.round
    """)).fetchall()
    for row in colapinto:
        print(f"  R{row[0]:02d} {row[1]:<35} P{row[2]}  pts={row[3]}")
    print(f"  Total Colapinto starts: {len(colapinto)}")

print("Done.")

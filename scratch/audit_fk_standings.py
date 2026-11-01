"""FK audit for driver_standings and constructor_standings — Phase 5A audit."""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@localhost:5432/f1_race_intelligence")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Discover actual types
    for tbl in ["driver_standings", "constructor_standings"]:
        cols = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_name = '{tbl}' ORDER BY ordinal_position"
        )).fetchall()
        print(f"{tbl}: {[(c[0],c[1]) for c in cols]}")

    print()
    # driver_standings.driver_id is character varying (string), joins to drivers.driver_id (string)
    # constructor_standings.constructor_id is character varying, joins to constructors.constructor_id
    # Try integer join via drivers.id
    ds_type = conn.execute(text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name='driver_standings' AND column_name='driver_id'"
    )).scalar()
    print(f"driver_standings.driver_id type: {ds_type}")

    cs_type = conn.execute(text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name='constructor_standings' AND column_name='constructor_id'"
    )).scalar()
    print(f"constructor_standings.constructor_id type: {cs_type}")

    print()
    # Based on schema: driver_standings.driver_id is varchar (string natural key)
    # but earlier queries suggest it may be integer. Check a sample value.
    sample_ds = conn.execute(text(
        "SELECT driver_id FROM driver_standings LIMIT 3"
    )).fetchall()
    print(f"Sample driver_standings.driver_id values: {[r[0] for r in sample_ds]}")

    sample_cs = conn.execute(text(
        "SELECT constructor_id FROM constructor_standings LIMIT 3"
    )).fetchall()
    print(f"Sample constructor_standings.constructor_id values: {[r[0] for r in sample_cs]}")

    print()
    # FK check using the string key for driver_standings
    # If driver_id is string, join to drivers.driver_id (string)
    # If integer, join to drivers.id
    if ds_type == "character varying":
        q = "SELECT COUNT(*) FROM driver_standings ds WHERE NOT EXISTS (SELECT 1 FROM drivers d WHERE d.driver_id = ds.driver_id)"
    else:
        q = "SELECT COUNT(*) FROM driver_standings ds WHERE NOT EXISTS (SELECT 1 FROM drivers d WHERE d.id = ds.driver_id)"
    cnt = conn.execute(text(q)).scalar()
    print(f"driver_standings -> drivers orphans: {cnt}  {'PASS' if cnt==0 else 'FAIL'}")

    if cs_type == "character varying":
        q2 = "SELECT COUNT(*) FROM constructor_standings cs WHERE NOT EXISTS (SELECT 1 FROM constructors c WHERE c.constructor_id = cs.constructor_id)"
    else:
        q2 = "SELECT COUNT(*) FROM constructor_standings cs WHERE NOT EXISTS (SELECT 1 FROM constructors c WHERE c.id = cs.constructor_id)"
    cnt2 = conn.execute(text(q2)).scalar()
    print(f"constructor_standings -> constructors orphans: {cnt2}  {'PASS' if cnt2==0 else 'FAIL'}")

    print()
    # Round-by-round detail R16-24
    print("=== Round-by-round race/quali/sprint counts R16-24 ===")
    rows = conn.execute(text("""
        SELECT r.round, r.race_name,
               COUNT(DISTINCT rr.id) as results,
               COUNT(DISTINCT qr.id) as quali,
               COUNT(DISTINCT sr.id) as sprint
        FROM races r
        LEFT JOIN race_results rr ON r.id = rr.race_id
        LEFT JOIN qualifying_results qr ON r.id = qr.race_id
        LEFT JOIN sprint_results sr ON r.id = sr.race_id
        WHERE r.season_year = 2024 AND r.round >= 16
        GROUP BY r.round, r.race_name ORDER BY r.round
    """)).fetchall()
    for row in rows:
        print(f"  R{row[0]:02d}  {str(row[1]):<42}  results={row[2]}  quali={row[3]}  sprint={row[4]}")

    print()
    print("=== Driver standings per round R16-24 ===")
    ds_rows = conn.execute(text("""
        SELECT round, COUNT(*) as driver_count
        FROM driver_standings WHERE season_year = 2024 AND round >= 16
        GROUP BY round ORDER BY round
    """)).fetchall()
    for row in ds_rows:
        print(f"  R{row[0]:02d}  driver_standings={row[1]}")

    print()
    print("=== Constructor standings per round R16-24 ===")
    cs_rows = conn.execute(text("""
        SELECT round, COUNT(*) as constructor_count
        FROM constructor_standings WHERE season_year = 2024 AND round >= 16
        GROUP BY round ORDER BY round
    """)).fetchall()
    for row in cs_rows:
        print(f"  R{row[0]:02d}  constructor_standings={row[1]}")

print("Done.")

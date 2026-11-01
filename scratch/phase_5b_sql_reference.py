"""
Phase 5B Stage 2 — Independent Full-Season SQL Reference Calculator
Calculates all reference values directly from PostgreSQL for the 2024 full season (R1-R24).
READ-ONLY. No inserts, updates, or deletes.
"""
import os, json
from decimal import Decimal
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@localhost:5432/f1_race_intelligence")
engine = create_engine(DATABASE_URL)
results = {}

with engine.connect() as conn:

    # ─── SPRINT ROUNDS ────────────────────────────────────────────────────────
    sprint_rounds = conn.execute(text("""
        SELECT r.round FROM races r
        JOIN sprint_results sr ON sr.race_id = r.id
        WHERE r.season_year = 2024 GROUP BY r.round ORDER BY r.round
    """)).scalars().all()
    results["sprint_rounds"] = sprint_rounds
    print(f"Sprint rounds: {sprint_rounds}")

    # ─── DRIVER AGGREGATES ────────────────────────────────────────────────────
    target_drivers = [
        "max_verstappen","perez","norris","leclerc","sainz",
        "russell","hamilton","piastri","bearman","lawson","antonelli","colapinto"
    ]

    print("\n=== DRIVER AGGREGATES (Full Season R1-R24) ===")
    driver_ref = {}
    for drv_slug in target_drivers:
        row = conn.execute(text("""
            SELECT
                d.driver_id,
                d.given_name || ' ' || d.family_name AS name,
                COUNT(rr.id) AS races_entered,
                SUM(CASE WHEN rr.position_text ~ '^[0-9]+$'
                         AND LOWER(COALESCE(rr.status,'')) NOT IN ('retired','did not start','disqualified','withdrawn')
                         THEN 1 ELSE 0 END) AS races_classified,
                COUNT(rr.id) - SUM(CASE WHEN rr.position_text ~ '^[0-9]+$'
                         AND LOWER(COALESCE(rr.status,'')) NOT IN ('retired','did not start','disqualified','withdrawn')
                         THEN 1 ELSE 0 END) AS non_classified,
                COALESCE(SUM(rr.points),0) AS gp_points,
                COALESCE((
                    SELECT SUM(sr.points) FROM sprint_results sr
                    JOIN races sr_r ON sr.race_id = sr_r.id
                    WHERE sr.driver_id = d.id AND sr_r.season_year = 2024
                ), 0) AS sprint_points,
                SUM(CASE WHEN rr.source_position = 1 THEN 1 ELSE 0 END) AS wins,
                ROUND(AVG(CASE WHEN rr.position_text ~ '^[0-9]+$'
                         AND LOWER(COALESCE(rr.status,'')) NOT IN ('retired','did not start','disqualified','withdrawn')
                         THEN rr.source_position END), 2) AS avg_classified_finish,
                ROUND(AVG(CASE WHEN rr.grid_position > 0 THEN rr.grid_position END), 2) AS avg_grid
            FROM drivers d
            JOIN race_results rr ON rr.driver_id = d.id
            JOIN races r ON rr.race_id = r.id
            WHERE d.driver_id = :slug AND r.season_year = 2024
            GROUP BY d.id, d.driver_id, d.given_name, d.family_name
        """), {"slug": drv_slug}).fetchone()

        if row is None:
            print(f"  {drv_slug}: NOT FOUND")
            driver_ref[drv_slug] = None
            continue

        # Championship standing
        standing = conn.execute(text("""
            SELECT ds.position FROM driver_standings ds
            JOIN drivers d ON ds.driver_id = d.id
            WHERE d.driver_id = :slug AND ds.season_year = 2024
            ORDER BY ds.round DESC LIMIT 1
        """), {"slug": drv_slug}).scalar()

        gp = float(row[5])
        sprint = float(row[6])
        total = gp + sprint
        driver_ref[drv_slug] = {
            "name": row[1],
            "races_entered": row[2],
            "races_classified": row[3],
            "non_classified": row[4],
            "gp_points": gp,
            "sprint_points": sprint,
            "total_points": total,
            "wins": row[7],
            "avg_classified_finish": float(row[8]) if row[8] else None,
            "avg_grid": float(row[9]) if row[9] else None,
            "championship_standing": standing,
        }
        print(f"  {drv_slug:<20} starts={row[2]} classified={row[3]} nc={row[4]} gp={gp:.0f} sprint={sprint:.0f} total={total:.0f} wins={row[7]} avgF={row[8]} avgG={row[9]} P{standing}")

    results["driver_aggregates"] = driver_ref

    # ─── CONSTRUCTOR AGGREGATES ───────────────────────────────────────────────
    print("\n=== CONSTRUCTOR AGGREGATES (Full Season) ===")
    constructors = conn.execute(text("""
        SELECT constructor_id FROM constructors ORDER BY constructor_id
    """)).scalars().all()

    con_ref = {}
    for con_slug in constructors:
        row = conn.execute(text("""
            SELECT
                c.constructor_id,
                c.name,
                COUNT(DISTINCT r.id) AS races_entered,
                COUNT(rr.id) AS total_car_starts,
                COALESCE(SUM(rr.points), 0) AS gp_points,
                SUM(CASE WHEN rr.source_position = 1 THEN 1 ELSE 0 END) AS wins
            FROM constructors c
            JOIN race_results rr ON rr.constructor_id = c.id
            JOIN races r ON rr.race_id = r.id
            WHERE c.constructor_id = :slug AND r.season_year = 2024
            GROUP BY c.constructor_id, c.name
        """), {"slug": con_slug}).fetchone()

        if row is None:
            continue

        sprint_pts = conn.execute(text("""
            SELECT COALESCE(SUM(sr.points),0)
            FROM sprint_results sr
            JOIN constructors c ON sr.constructor_id = c.id
            JOIN races r ON sr.race_id = r.id
            WHERE c.constructor_id = :slug AND r.season_year = 2024
        """), {"slug": con_slug}).scalar()

        standing = conn.execute(text("""
            SELECT cs.position FROM constructor_standings cs
            JOIN constructors c ON cs.constructor_id = c.id
            WHERE c.constructor_id = :slug AND cs.season_year = 2024
            ORDER BY cs.round DESC LIMIT 1
        """), {"slug": con_slug}).scalar()

        gp = float(row[4])
        spr = float(sprint_pts)
        total = gp + spr
        con_ref[con_slug] = {
            "name": row[1],
            "races_entered": row[2],
            "gp_points": gp,
            "sprint_points": spr,
            "total_points": total,
            "wins": row[5],
            "championship_standing": standing,
        }
        print(f"  {con_slug:<20} gp={gp:.0f} sprint={spr:.0f} total={total:.0f} wins={row[5]} P{standing}")

    results["constructor_aggregates"] = con_ref

    # ─── HEAD-TO-HEAD TEAMMATE COMPARISONS ───────────────────────────────────
    print("\n=== QUALIFYING H2H (season) ===")
    # For each constructor, sum qualifying H2H rounds
    h2h_pairs = [
        ("red_bull",  "max_verstappen", "perez"),
        ("mclaren",   "norris",         "piastri"),
        ("ferrari",   "leclerc",        "sainz"),
        ("mercedes",  "hamilton",       "russell"),
        ("aston_martin", "alonso",      "stroll"),
        ("alpine",    "gasly",          "ocon"),
        ("haas",      "hulkenberg",     "kevin_magnussen"),
        ("rb",        "ricciardo",      "tsunoda"),
        ("williams",  "albon",          "colapinto"),
        ("sauber",    "bottas",         "zhou"),
    ]

    h2h_ref = {}
    for con_slug, da, db in h2h_pairs:
        # Qualifying H2H
        qh2h = conn.execute(text("""
            SELECT
                SUM(CASE WHEN qa.position < qb.position THEN 1 ELSE 0 END) AS a_ahead,
                SUM(CASE WHEN qb.position < qa.position THEN 1 ELSE 0 END) AS b_ahead,
                COUNT(*) AS comparable_rounds
            FROM races r
            JOIN constructors c ON c.constructor_id = :con_slug
            JOIN race_results rra ON rra.race_id = r.id AND rra.constructor_id = c.id
            JOIN race_results rrb ON rrb.race_id = r.id AND rrb.constructor_id = c.id
            JOIN qualifying_results qa ON qa.race_id = r.id AND qa.driver_id = rra.driver_id
            JOIN qualifying_results qb ON qb.race_id = r.id AND qb.driver_id = rrb.driver_id
            JOIN drivers da ON qa.driver_id = da.id AND da.driver_id = :da
            JOIN drivers db ON qb.driver_id = db.id AND db.driver_id = :db
            WHERE r.season_year = 2024 AND qa.position IS NOT NULL AND qb.position IS NOT NULL
        """), {"con_slug": con_slug, "da": da, "db": db}).fetchone()

        # Race H2H (both classified)
        rh2h = conn.execute(text("""
            SELECT
                SUM(CASE WHEN rra.source_position < rrb.source_position THEN 1 ELSE 0 END) AS a_ahead,
                SUM(CASE WHEN rrb.source_position < rra.source_position THEN 1 ELSE 0 END) AS b_ahead,
                COUNT(*) AS comparable_rounds
            FROM races r
            JOIN constructors c ON c.constructor_id = :con_slug
            JOIN race_results rra ON rra.race_id = r.id AND rra.constructor_id = c.id
            JOIN race_results rrb ON rrb.race_id = r.id AND rrb.constructor_id = c.id
            JOIN drivers da ON rra.driver_id = da.id AND da.driver_id = :da
            JOIN drivers db ON rrb.driver_id = db.id AND db.driver_id = :db
            WHERE r.season_year = 2024
              AND rra.position_text ~ '^[0-9]+$'
              AND LOWER(COALESCE(rra.status,'')) NOT IN ('retired','did not start','disqualified','withdrawn')
              AND rrb.position_text ~ '^[0-9]+$'
              AND LOWER(COALESCE(rrb.status,'')) NOT IN ('retired','did not start','disqualified','withdrawn')
        """), {"con_slug": con_slug, "da": da, "db": db}).fetchone()

        h2h_ref[con_slug] = {
            "driver_a": da, "driver_b": db,
            "quali_a_ahead": qh2h[0], "quali_b_ahead": qh2h[1], "quali_comparable": qh2h[2],
            "race_a_ahead": rh2h[0], "race_b_ahead": rh2h[1], "race_comparable": rh2h[2],
        }
        print(f"  {con_slug:<15} Quali: {da} {qh2h[0]}-{qh2h[1]} ({qh2h[2]} rds)  Race: {rh2h[0]}-{rh2h[1]} ({rh2h[2]} rds)")

    results["h2h"] = h2h_ref

    # ─── ROLLING PERFORMANCE (last 3 and last 5 rounds for top drivers) ───────
    print("\n=== ROLLING PERFORMANCE (last 3 and last 5 rounds) ===")
    rolling_drivers = ["max_verstappen","norris","leclerc","piastri","russell","hamilton"]
    rolling_ref = {}
    for drv_slug in rolling_drivers:
        for window in [3, 5]:
            row = conn.execute(text("""
                WITH ranked AS (
                    SELECT rr.source_position, rr.points, rr.position_text, rr.status,
                           r.round,
                           COALESCE((
                               SELECT sr.points FROM sprint_results sr
                               JOIN drivers sd ON sr.driver_id = sd.id AND sd.driver_id = :slug
                               WHERE sr.race_id = r.id
                           ),0) AS sprint_pts
                    FROM race_results rr
                    JOIN races r ON rr.race_id = r.id
                    JOIN drivers d ON rr.driver_id = d.id AND d.driver_id = :slug
                    WHERE r.season_year = 2024
                    ORDER BY r.round DESC LIMIT :w
                )
                SELECT
                    ROUND(AVG(CASE WHEN position_text ~ '^[0-9]+$'
                         AND LOWER(COALESCE(status,'')) NOT IN ('retired','did not start','disqualified','withdrawn')
                         THEN source_position END)::numeric, 2) AS avg_finish,
                    COALESCE(SUM(points),0) AS gp_points,
                    COALESCE(SUM(sprint_pts),0) AS sprint_points,
                    COALESCE(SUM(points),0) + COALESCE(SUM(sprint_pts),0) AS total_points,
                    COUNT(*) AS rounds
                FROM ranked
            """), {"slug": drv_slug, "w": window}).fetchone()
            key = f"{drv_slug}_last{window}"
            rolling_ref[key] = {
                "avg_classified_finish": float(row[0]) if row[0] else None,
                "gp_points": float(row[1]),
                "sprint_points": float(row[2]),
                "total_points": float(row[3]),
                "rounds": row[4],
            }
            print(f"  {drv_slug:<20} last{window}: avgF={row[0]} gp={row[1]:.0f} sprint={row[2]:.0f} total={row[3]:.0f}")

    results["rolling"] = rolling_ref

    # ─── POINTS RATES ─────────────────────────────────────────────────────────
    print("\n=== POINTS RATES ===")
    pts_rate_drivers = ["max_verstappen","norris","leclerc","piastri","russell","hamilton","sainz","perez"]
    pts_rates = {}
    for drv_slug in pts_rate_drivers:
        row = conn.execute(text("""
            SELECT
                COUNT(rr.id) AS starts,
                COUNT(DISTINCT r.id) AS rounds,
                COALESCE(SUM(rr.points),0) AS gp_points,
                COALESCE((
                    SELECT SUM(sr.points) FROM sprint_results sr
                    JOIN drivers sd ON sr.driver_id = sd.id AND sd.driver_id = :slug
                    JOIN races sr_r ON sr.race_id = sr_r.id WHERE sr_r.season_year = 2024
                ),0) AS sprint_points
            FROM race_results rr
            JOIN races r ON rr.race_id = r.id
            JOIN drivers d ON rr.driver_id = d.id AND d.driver_id = :slug
            WHERE r.season_year = 2024
        """), {"slug": drv_slug}).fetchone()
        starts, rounds, gp_pts, spr_pts = row[0], row[1], float(row[2]), float(row[3])
        total = gp_pts + spr_pts
        pps = round(gp_pts / starts, 2) if starts else None   # GP points per start
        ppr = round(total / rounds, 2) if rounds else None      # Total points per round
        pts_rates[drv_slug] = {
            "starts": starts, "rounds": rounds,
            "gp_points": gp_pts, "sprint_points": spr_pts, "total_points": total,
            "gp_points_per_start": pps,
            "total_points_per_round": ppr,
        }
        print(f"  {drv_slug:<20} gp_pts/start={pps}  total_pts/round={ppr}")

    results["points_rates"] = pts_rates

    # ─── SPECIAL CASES ────────────────────────────────────────────────────────
    print("\n=== SPECIAL CASES ===")

    # Bearman appearances
    bearman = conn.execute(text("""
        SELECT r.round, r.race_name, rr.source_position, rr.position_text, rr.points, rr.status,
               c.constructor_id
        FROM race_results rr JOIN races r ON rr.race_id = r.id
        JOIN drivers d ON rr.driver_id = d.id AND d.driver_id = 'bearman'
        JOIN constructors c ON rr.constructor_id = c.id
        WHERE r.season_year = 2024 ORDER BY r.round
    """)).fetchall()
    print(f"  Bearman: {len(bearman)} entries")
    for b in bearman:
        print(f"    R{b[0]:02d} {b[1]:<35} P{b[2]} pts={b[4]} status={b[5]} con={b[6]}")

    # Lawson appearances
    lawson = conn.execute(text("""
        SELECT r.round, r.race_name, rr.source_position, rr.points, c.constructor_id
        FROM race_results rr JOIN races r ON rr.race_id = r.id
        JOIN drivers d ON rr.driver_id = d.id AND d.driver_id = 'lawson'
        JOIN constructors c ON rr.constructor_id = c.id
        WHERE r.season_year = 2024 ORDER BY r.round
    """)).fetchall()
    print(f"  Lawson: {len(lawson)} entries - " + ", ".join(f"R{l[0]}(P{l[2]},{l[4]})" for l in lawson))

    # Antonelli
    ant = conn.execute(text("""
        SELECT COUNT(*) FROM race_results rr JOIN drivers d ON rr.driver_id = d.id
        JOIN races r ON rr.race_id = r.id
        WHERE d.driver_id = 'antonelli' AND r.season_year = 2024
    """)).scalar()
    print(f"  Antonelli: {ant} race starts (reference entity if 0)")

    # Colapinto
    col = conn.execute(text("""
        SELECT r.round, rr.source_position, rr.points FROM race_results rr
        JOIN drivers d ON rr.driver_id = d.id AND d.driver_id = 'colapinto'
        JOIN races r ON rr.race_id = r.id
        WHERE r.season_year = 2024 ORDER BY r.round
    """)).fetchall()
    print(f"  Colapinto: {len(col)} entries, first round={col[0][0] if col else 'N/A'}")

    # DSQ check
    dsq = conn.execute(text("""
        SELECT d.driver_id, r.round, rr.position_text, rr.status
        FROM race_results rr JOIN drivers d ON rr.driver_id = d.id
        JOIN races r ON rr.race_id = r.id
        WHERE r.season_year = 2024 AND (
            LOWER(rr.position_text) = 'dsq' OR LOWER(rr.status) ILIKE '%disqualif%'
        )
        ORDER BY r.round
    """)).fetchall()
    print(f"  DSQ results: {len(dsq)}")
    for d in dsq:
        print(f"    R{d[1]:02d} {d[0]} pos_text={d[2]} status={d[3]}")

    # DNS check
    dns = conn.execute(text("""
        SELECT d.driver_id, r.round, rr.position_text, rr.status
        FROM race_results rr JOIN drivers d ON rr.driver_id = d.id
        JOIN races r ON rr.race_id = r.id
        WHERE r.season_year = 2024 AND LOWER(rr.status) ILIKE '%did not start%'
        ORDER BY r.round
    """)).fetchall()
    print(f"  DNS results: {len(dns)}")
    for d in dns:
        print(f"    R{d[1]:02d} {d[0]} pos_text={d[2]} status={d[3]}")

    results["special_cases"] = {
        "bearman_entries": len(bearman),
        "lawson_entries": len(lawson),
        "antonelli_entries": ant,
        "colapinto_entries": len(col),
        "colapinto_first_round": col[0][0] if col else None,
        "dsq_count": len(dsq),
        "dsq_details": [(d[1], d[0], d[2], d[3]) for d in dsq],
        "dns_count": len(dns),
        "dns_details": [(d[1], d[0], d[2], d[3]) for d in dns],
    }

# Save results
import json
def default_serial(o):
    if isinstance(o, Decimal): return float(o)
    raise TypeError
with open("scratch/phase_5b_sql_reference.json", "w") as f:
    json.dump(results, f, indent=2, default=default_serial)
print("\nSaved to scratch/phase_5b_sql_reference.json")

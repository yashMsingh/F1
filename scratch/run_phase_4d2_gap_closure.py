"""Phase 4D.2 — Gap Closure Verification Script.

Covers:
1. Rolling sprint points & GP points for R13-R15 for VER, NOR, LEC, RUS
2. Round-by-round completeness audit across all 15 rounds
3. Natural-key uniqueness check on all core tables
4. Reference driver vs race vs standings participant distinction
"""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.analytics.longitudinal_driver import get_driver_trajectory
from app.statistics.longitudinal import compute_driver_form_summary

DB_URL = "postgresql://f1user:changeme@localhost:5432/f1_race_intelligence"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

def main():
    conn = engine.connect()
    session = SessionLocal()

    print("=" * 80)
    print("PHASE 4D.2 GAP CLOSURE VERIFICATION")
    print("=" * 80)

    # ── 1. ROLLING SPRINT-POINT & GP-POINT VERIFICATION (R13-R15) ─────────────
    print("\n>>> 1. ROLLING SPRINT-POINT & GP-POINT VERIFICATION (R13-R15)")
    # Check if any sprint session exists in R13-R15
    sprint_check = conn.execute(text("""
        SELECT r.round, r.race_name, count(sr.id) as sprint_row_count
        FROM races r
        LEFT JOIN sprint_results sr ON r.id = sr.race_id
        WHERE r.round BETWEEN 13 AND 15
        GROUP BY r.round, r.race_name
        ORDER BY r.round;
    """)).fetchall()
    print("Sprint sessions in R13-R15:")
    for row in sprint_check:
        print(f"  Round {row[0]} ({row[1]}): {row[2]} sprint rows")

    drivers = ["max_verstappen", "norris", "leclerc", "russell"]
    rolling_details = []

    for d_slug in drivers:
        sql_row = conn.execute(text("""
            WITH rounds_data AS (
                SELECT r.round,
                       rr.points as race_pts,
                       COALESCE(sr.points, 0.0) as sprint_pts,
                       rr.source_position,
                       CASE WHEN rr.position_text ~ '^[0-9]+$'
                             AND LOWER(rr.status) NOT IN ('retired', 'did not start', 'disqualified', 'withdrawn')
                            THEN rr.source_position ELSE NULL END as classified_finish
                FROM race_results rr
                JOIN races r ON rr.race_id = r.id
                JOIN drivers d ON rr.driver_id = d.id
                LEFT JOIN sprint_results sr ON r.id = sr.race_id AND sr.driver_id = d.id
                WHERE d.driver_id = :d_slug AND r.season_year = 2024 AND r.round BETWEEN 13 AND 15
            )
            SELECT
                SUM(race_pts) as gp_points,
                SUM(sprint_pts) as sprint_points,
                SUM(race_pts + sprint_pts) as combined_points,
                COUNT(classified_finish) as classified_finishes,
                ROUND(AVG(classified_finish), 4) as mean_classified_finish
            FROM rounds_data;
        """), {"d_slug": d_slug}).fetchone()

        # Application outputs:
        traj = get_driver_trajectory(session, 2024, d_slug, up_to_round=15)
        form_summary = compute_driver_form_summary(traj, window_size=3)
        latest_finish_win = next(
            (w for w in reversed(form_summary.rolling_windows) if w.round == 15 and w.metric_name == "finish_position"),
            None
        )
        window_items = [t for t in traj if t.round in (13, 14, 15)]
        app_gp_pts = sum(t.race_points for t in window_items)
        app_sp_pts = sum(t.sprint_points for t in window_items)
        app_comb_pts = app_gp_pts + app_sp_pts

        rec = {
            "driver": d_slug,
            "sql": {
                "gp_points": Decimal(str(sql_row[0])),
                "sprint_points": Decimal(str(sql_row[1])),
                "combined_points": Decimal(str(sql_row[2])),
                "classified_finishes": int(sql_row[3]),
                "mean_finish": float(sql_row[4]) if sql_row[4] is not None else None,
            },
            "app": {
                "gp_points": app_gp_pts,
                "sprint_points": app_sp_pts,
                "combined_points": app_comb_pts,
                "classified_finishes": latest_finish_win.valid_observations if latest_finish_win else None,
                "mean_finish": latest_finish_win.mean if latest_finish_win else None,
            }
        }
        rolling_details.append(rec)
        match = (rec["sql"] == rec["app"])
        status = "PASS" if match else "FAIL"
        print(f"[{status}] {d_slug:<15} | GP Pts: SQL={rec['sql']['gp_points']} App={rec['app']['gp_points']} | Sprint Pts: SQL={rec['sql']['sprint_points']} App={rec['app']['sprint_points']} | Comb Pts: SQL={rec['sql']['combined_points']} App={rec['app']['combined_points']} | Class Fin: SQL={rec['sql']['classified_finishes']} App={rec['app']['classified_finishes']} | Mean Fin: SQL={rec['sql']['mean_finish']} App={rec['app']['mean_finish']}")

    # ── 2. ROUND-BY-ROUND COMPLETENESS AUDIT (R1-R15) ───────────────────────────
    print("\n>>> 2. ROUND-BY-ROUND COMPLETENESS AUDIT (R1-R15)")
    completeness = conn.execute(text("""
        SELECT r.round, r.race_name,
               (SELECT count(*) FROM driver_standings ds WHERE ds.season_year = r.season_year AND ds.round = r.round) as d_stand,
               (SELECT count(*) FROM constructor_standings cs WHERE cs.season_year = r.season_year AND cs.round = r.round) as c_stand,
               (SELECT count(*) FROM race_results rr WHERE rr.race_id = r.id) as race_res,
               (SELECT count(*) FROM qualifying_results qr WHERE qr.race_id = r.id) as quali_res,
               (SELECT count(*) FROM sprint_results sr WHERE sr.race_id = r.id) as sprint_res
        FROM races r
        WHERE r.season_year = 2024
        ORDER BY r.round;
    """)).fetchall()

    print(f"{'Rnd':<3} | {'Race Name':<30} | {'D_Stand':<7} | {'C_Stand':<7} | {'Race_Res':<8} | {'Quali_Res':<9} | {'Sprint_Res':<10}")
    print("-" * 90)
    for c in completeness:
        print(f"{c[0]:<3} | {c[1]:<30} | {c[2]:<7} | {c[3]:<7} | {c[4]:<8} | {c[5]:<9} | {c[6]:<10}")

    # Inspect drivers in reference table without race participation
    print("\nDrivers in reference table with and without race participation:")
    driver_participation = conn.execute(text("""
        SELECT d.id, d.driver_id, d.code, d.given_name, d.family_name,
               count(rr.id) as race_starts,
               (SELECT count(*) FROM driver_standings ds WHERE ds.driver_id = d.id) as standings_rows
        FROM drivers d
        LEFT JOIN race_results rr ON d.id = rr.driver_id
        GROUP BY d.id, d.driver_id, d.code, d.given_name, d.family_name
        ORDER BY race_starts ASC, d.driver_id ASC;
    """)).fetchall()

    for dp in driver_participation:
        if dp[5] == 0:
            print(f"  [Reference-Only Driver] {dp[1]} ({dp[3]} {dp[4]} - {dp[2]}): race_starts={dp[5]}, standings_entries={dp[6]}")
        else:
            print(f"  [Active Racing Driver] {dp[1]} ({dp[3]} {dp[4]} - {dp[2]}): race_starts={dp[5]}, standings_entries={dp[6]}")

    # ── 3. NATURAL-KEY UNIQUENESS AUDIT ──────────────────────────────────────────
    print("\n>>> 3. NATURAL-KEY UNIQUENESS AUDIT")
    nk_checks = [
        ("races", "season_year, round", "season_year, round"),
        ("race_results", "race_id, driver_id", "race_id, driver_id"),
        ("qualifying_results", "race_id, driver_id", "race_id, driver_id"),
        ("sprint_results", "race_id, driver_id", "race_id, driver_id"),
        ("driver_standings", "season_year, round, driver_id", "season_year, round, driver_id"),
        ("constructor_standings", "season_year, round, constructor_id", "season_year, round, constructor_id"),
        ("pit_stops", "race_id, driver_id, stop_number", "race_id, driver_id, stop_number"),
        ("lap_times", "race_id, driver_id, lap_number", "race_id, driver_id, lap_number"),
    ]

    for table, nk, group_cols in nk_checks:
        dup_query = text(f"""
            SELECT {group_cols}, count(*)
            FROM {table}
            GROUP BY {group_cols}
            HAVING count(*) > 1;
        """)
        dups = conn.execute(dup_query).fetchall()
        print(f"Table '{table}' (Natural Key: {nk}) -> Duplicate Count: {len(dups)}")

if __name__ == "__main__":
    main()

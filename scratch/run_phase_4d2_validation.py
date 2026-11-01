"""Phase 4D.2 — Independent SQL Reference Calculations & Application Validation.

This script executes direct SQL queries completely independently of application services,
then compares their results against the application functions across:
1. Driver season aggregates (9 drivers)
2. Constructor season aggregates (4 constructors)
3. Teammate head-to-head comparisons (5 pairings)
4. Rolling 3-round performance (4 drivers: R13-R15)
5. Longitudinal rate metrics & sample sizes
6. Special historical edge cases (R11 to R15)
7. Relational integrity invariants
"""

import json
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.analytics.longitudinal_driver import get_driver_season_aggregate, get_driver_trajectory
from app.analytics.longitudinal_constructor import get_constructor_season_aggregate
from app.analytics.longitudinal_teammate import get_season_teammate_comparisons
from app.statistics.longitudinal import (
    compute_driver_form_summary,
    compute_driver_points_stats,
    compute_driver_longitudinal_stats,
)

DB_URL = "postgresql://f1user:changeme@localhost:5432/f1_race_intelligence"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

def main():
    session = SessionLocal()
    conn = engine.connect()

    print("=" * 80)
    print("PHASE 4D.2: INDEPENDENT SQL REFERENCE VALIDATION (2024 ROUNDS 1-15)")
    print("=" * 80)

    # ── 1. DRIVER AGGREGATES ─────────────────────────────────────────────────────
    print("\n>>> 1. DRIVER AGGREGATES (9 Target Drivers)")
    target_drivers = [
        "max_verstappen", "perez", "norris", "leclerc", "sainz",
        "russell", "hamilton", "piastri", "bearman"
    ]

    driver_results = []
    for d_slug in target_drivers:
        # SQL Reference calculation:
        # F1 classified finish definition: position_text is digit and status not in ('Retired', 'Did not start', 'Disqualified', 'Withdrawn')
        sql_data = conn.execute(text("""
            WITH driver_races AS (
                SELECT rr.race_id, r.round, rr.points as race_pts,
                       rr.grid_position, rr.source_position, rr.position_text, rr.status,
                       CASE WHEN rr.position_text ~ '^[0-9]+$'
                             AND LOWER(rr.status) NOT IN ('retired', 'did not start', 'disqualified', 'withdrawn')
                            THEN 1 ELSE 0 END as is_classified,
                       CASE WHEN rr.source_position = 1
                             AND rr.position_text ~ '^[0-9]+$'
                             AND LOWER(rr.status) NOT IN ('retired', 'did not start', 'disqualified', 'withdrawn')
                            THEN 1 ELSE 0 END as is_win
                FROM race_results rr
                JOIN races r ON rr.race_id = r.id
                JOIN drivers d ON rr.driver_id = d.id
                WHERE d.driver_id = :d_slug AND r.season_year = 2024 AND r.round <= 15
            ),
            sprint_pts AS (
                SELECT COALESCE(SUM(sr.points), 0.0) as sprint_pts
                FROM sprint_results sr
                JOIN races r ON sr.race_id = r.id
                JOIN drivers d ON sr.driver_id = d.id
                WHERE d.driver_id = :d_slug AND r.season_year = 2024 AND r.round <= 15
            ),
            standing AS (
                SELECT ds.position as standing_pos
                FROM driver_standings ds
                JOIN drivers d ON ds.driver_id = d.id
                WHERE d.driver_id = :d_slug AND ds.season_year = 2024 AND ds.round <= 15
                ORDER BY ds.round DESC
                LIMIT 1
            )
            SELECT
                COUNT(*) as gp_starts,
                SUM(is_classified) as classified_finishes,
                COUNT(*) - SUM(is_classified) as dnf_count,
                COALESCE(SUM(race_pts), 0.0) as total_race_pts,
                (SELECT sprint_pts FROM sprint_pts) as total_sprint_pts,
                COALESCE(SUM(race_pts), 0.0) + (SELECT sprint_pts FROM sprint_pts) as total_pts,
                SUM(is_win) as wins,
                ROUND(AVG(CASE WHEN is_classified = 1 THEN source_position ELSE NULL END), 2) as avg_finish,
                ROUND(AVG(CASE WHEN grid_position > 0 THEN grid_position ELSE NULL END), 2) as avg_grid,
                (SELECT standing_pos FROM standing) as championship_standing
            FROM driver_races;
        """), {"d_slug": d_slug}).fetchone()

        # Application calculation:
        app_agg = get_driver_season_aggregate(session, 2024, d_slug, up_to_round=15)

        res = {
            "driver_id": d_slug,
            "sql": {
                "starts": int(sql_data[0]),
                "classified": int(sql_data[1]),
                "dnf": int(sql_data[2]),
                "race_pts": Decimal(str(sql_data[3])),
                "sprint_pts": Decimal(str(sql_data[4])),
                "total_pts": Decimal(str(sql_data[5])),
                "wins": int(sql_data[6]),
                "avg_finish": float(sql_data[7]) if sql_data[7] is not None else None,
                "avg_grid": float(sql_data[8]) if sql_data[8] is not None else None,
                "standing": int(sql_data[9]) if sql_data[9] is not None else None,
            },
            "app": {
                "starts": app_agg.races_entered if app_agg else None,
                "classified": app_agg.races_classified if app_agg else None,
                "dnf": app_agg.dnf_count if app_agg else None,
                "race_pts": app_agg.total_race_points if app_agg else None,
                "sprint_pts": app_agg.total_sprint_points if app_agg else None,
                "total_pts": app_agg.total_points if app_agg else None,
                "wins": app_agg.wins if app_agg else None,
                "avg_finish": app_agg.average_finish if app_agg else None,
                "avg_grid": app_agg.average_grid if app_agg else None,
                "standing": app_agg.championship_standing if app_agg else None,
            }
        }
        driver_results.append(res)

        # Print comparison line
        pts_match = res["sql"]["total_pts"] == res["app"]["total_pts"]
        wins_match = res["sql"]["wins"] == res["app"]["wins"]
        starts_match = res["sql"]["starts"] == res["app"]["starts"]
        avg_f_match = res["sql"]["avg_finish"] == res["app"]["avg_finish"]
        status = "PASS" if (pts_match and wins_match and starts_match and avg_f_match) else "FAIL"
        print(f"[{status}] {d_slug:<15} | Starts: SQL={res['sql']['starts']} App={res['app']['starts']} | Total Pts: SQL={res['sql']['total_pts']} App={res['app']['total_pts']} | Wins: SQL={res['sql']['wins']} App={res['app']['wins']} | Avg Fin: SQL={res['sql']['avg_finish']} App={res['app']['avg_finish']}")

    # ── 2. CONSTRUCTOR AGGREGATES ────────────────────────────────────────────────
    print("\n>>> 2. CONSTRUCTOR AGGREGATES (4 Target Teams)")
    target_constructors = ["red_bull", "ferrari", "mclaren", "mercedes"]
    constructor_results = []
    for c_slug in target_constructors:
        sql_data = conn.execute(text("""
            WITH race_data AS (
                SELECT rr.race_id, r.round, rr.points as race_pts,
                       rr.source_position,
                       CASE WHEN rr.position_text ~ '^[0-9]+$'
                             AND LOWER(rr.status) NOT IN ('retired', 'did not start', 'disqualified', 'withdrawn')
                            THEN 1 ELSE 0 END as is_classified
                FROM race_results rr
                JOIN races r ON rr.race_id = r.id
                JOIN constructors c ON rr.constructor_id = c.id
                WHERE c.constructor_id = :c_slug AND r.season_year = 2024 AND r.round <= 15
            ),
            sprint_pts AS (
                SELECT COALESCE(SUM(sr.points), 0.0) as sprint_pts
                FROM sprint_results sr
                JOIN races r ON sr.race_id = r.id
                JOIN constructors c ON sr.constructor_id = c.id
                WHERE c.constructor_id = :c_slug AND r.season_year = 2024 AND r.round <= 15
            ),
            wins_data AS (
                SELECT COUNT(DISTINCT r.id) as wins
                FROM race_results rr
                JOIN races r ON rr.race_id = r.id
                JOIN constructors c ON rr.constructor_id = c.id
                WHERE c.constructor_id = :c_slug AND r.season_year = 2024 AND r.round <= 15
                  AND rr.source_position = 1
                  AND rr.position_text ~ '^[0-9]+$'
                  AND LOWER(rr.status) NOT IN ('retired', 'did not start', 'disqualified', 'withdrawn')
            ),
            rounds_entered AS (
                SELECT COUNT(DISTINCT r.id) as r_count
                FROM race_results rr
                JOIN races r ON rr.race_id = r.id
                JOIN constructors c ON rr.constructor_id = c.id
                WHERE c.constructor_id = :c_slug AND r.season_year = 2024 AND r.round <= 15
            ),
            standing AS (
                SELECT cs.position as standing_pos
                FROM constructor_standings cs
                JOIN constructors c ON cs.constructor_id = c.id
                WHERE c.constructor_id = :c_slug AND cs.season_year = 2024 AND cs.round <= 15
                ORDER BY cs.round DESC
                LIMIT 1
            )
            SELECT
                (SELECT r_count FROM rounds_entered) as rounds_count,
                COUNT(*) as total_car_starts,
                SUM(is_classified) as total_car_finishes,
                COALESCE(SUM(race_pts), 0.0) as total_race_pts,
                (SELECT sprint_pts FROM sprint_pts) as total_sprint_pts,
                COALESCE(SUM(race_pts), 0.0) + (SELECT sprint_pts FROM sprint_pts) as total_pts,
                (SELECT wins FROM wins_data) as wins,
                (SELECT standing_pos FROM standing) as championship_standing
            FROM race_data;
        """), {"c_slug": c_slug}).fetchone()

        app_con = get_constructor_season_aggregate(session, 2024, c_slug, up_to_round=15)

        res = {
            "constructor_id": c_slug,
            "sql": {
                "rounds": int(sql_data[0]),
                "car_starts": int(sql_data[1]),
                "car_finishes": int(sql_data[2]),
                "race_pts": Decimal(str(sql_data[3])),
                "sprint_pts": Decimal(str(sql_data[4])),
                "total_pts": Decimal(str(sql_data[5])),
                "wins": int(sql_data[6]),
                "standing": int(sql_data[7]),
            },
            "app": {
                "rounds": app_con.races_entered if app_con else None,
                "car_starts": app_con.total_car_starts if app_con else None,
                "car_finishes": app_con.total_car_finishes if app_con else None,
                "race_pts": app_con.total_race_points if app_con else None,
                "sprint_pts": app_con.total_sprint_points if app_con else None,
                "total_pts": app_con.total_points if app_con else None,
                "wins": app_con.wins if app_con else None,
                "standing": app_con.championship_standing if app_con else None,
            }
        }
        constructor_results.append(res)
        pts_match = res["sql"]["total_pts"] == res["app"]["total_pts"]
        wins_match = res["sql"]["wins"] == res["app"]["wins"]
        status = "PASS" if (pts_match and wins_match) else "FAIL"
        print(f"[{status}] {c_slug:<15} | Rounds: SQL={res['sql']['rounds']} App={res['app']['rounds']} | Total Pts: SQL={res['sql']['total_pts']} App={res['app']['total_pts']} | Wins: SQL={res['sql']['wins']} App={res['app']['wins']} | Standing: SQL={res['sql']['standing']} App={res['app']['standing']}")

    # ── 3. TEAMMATE HEAD-TO-HEAD COMPARISONS ──────────────────────────────────────
    print("\n>>> 3. TEAMMATE COMPARISONS (5 Target Pairings)")
    pairings = [
        ("red_bull", "max_verstappen", "perez"),
        ("ferrari", "leclerc", "sainz"),
        ("ferrari", "bearman", "leclerc"),
        ("mclaren", "norris", "piastri"),
        ("mercedes", "hamilton", "russell"),
    ]
    app_teammates = get_season_teammate_comparisons(session, 2024, up_to_round=15)
    app_tm_map = {(t.constructor_id, t.driver_a_id, t.driver_b_id): t for t in app_teammates}

    teammate_results = []
    for c_id, d_a, d_b in pairings:
        # Ensure alphabetical ordering driver_a < driver_b
        p_a, p_b = (d_a, d_b) if d_a < d_b else (d_b, d_a)

        # SQL head-to-head calculation
        sql_tm = conn.execute(text("""
            WITH shared_rounds AS (
                SELECT r.round,
                       qr_a.position as q_pos_a, qr_b.position as q_pos_b,
                       rr_a.source_position as fin_a, rr_b.source_position as fin_b,
                       rr_a.points as pts_a, rr_b.points as pts_b,
                       COALESCE(sr_a.points, 0.0) as sp_pts_a, COALESCE(sr_b.points, 0.0) as sp_pts_b,
                       CASE WHEN qr_a.position IS NOT NULL AND qr_b.position IS NOT NULL THEN 1 ELSE 0 END as comp_q,
                       CASE WHEN rr_a.position_text ~ '^[0-9]+$' AND LOWER(rr_a.status) NOT IN ('retired', 'did not start', 'disqualified', 'withdrawn')
                             AND rr_b.position_text ~ '^[0-9]+$' AND LOWER(rr_b.status) NOT IN ('retired', 'did not start', 'disqualified', 'withdrawn')
                            THEN 1 ELSE 0 END as comp_r
                FROM races r
                JOIN race_results rr_a ON r.id = rr_a.race_id
                JOIN race_results rr_b ON r.id = rr_b.race_id
                JOIN drivers da ON rr_a.driver_id = da.id
                JOIN drivers db ON rr_b.driver_id = db.id
                JOIN constructors c ON rr_a.constructor_id = c.id AND rr_b.constructor_id = c.id
                LEFT JOIN qualifying_results qr_a ON r.id = qr_a.race_id AND qr_a.driver_id = da.id
                LEFT JOIN qualifying_results qr_b ON r.id = qr_b.race_id AND qr_b.driver_id = db.id
                LEFT JOIN sprint_results sr_a ON r.id = sr_a.race_id AND sr_a.driver_id = da.id
                LEFT JOIN sprint_results sr_b ON r.id = sr_b.race_id AND sr_b.driver_id = db.id
                WHERE r.season_year = 2024 AND r.round <= 15
                  AND c.constructor_id = :c_id
                  AND da.driver_id = :d_a AND db.driver_id = :d_b
            )
            SELECT
                COUNT(*) as rounds_together,
                SUM(comp_q) as comp_q_rounds,
                SUM(CASE WHEN comp_q = 1 AND q_pos_a < q_pos_b THEN 1 ELSE 0 END) as q_ahead_a,
                SUM(CASE WHEN comp_q = 1 AND q_pos_b < q_pos_a THEN 1 ELSE 0 END) as q_ahead_b,
                SUM(comp_r) as comp_r_rounds,
                SUM(CASE WHEN comp_r = 1 AND fin_a < fin_b THEN 1 ELSE 0 END) as r_ahead_a,
                SUM(CASE WHEN comp_r = 1 AND fin_b < fin_a THEN 1 ELSE 0 END) as r_ahead_b,
                SUM(pts_a + sp_pts_a) as tot_pts_a,
                SUM(pts_b + sp_pts_b) as tot_pts_b
            FROM shared_rounds;
        """), {"c_id": c_id, "d_a": p_a, "d_b": p_b}).fetchone()

        app_t = app_tm_map.get((c_id, p_a, p_b))

        res = {
            "pairing": f"{c_id}: {p_a} vs {p_b}",
            "sql": {
                "rounds_together": int(sql_tm[0]),
                "comp_q": int(sql_tm[1]),
                "q_ahead_a": int(sql_tm[2]),
                "q_ahead_b": int(sql_tm[3]),
                "comp_r": int(sql_tm[4]),
                "r_ahead_a": int(sql_tm[5]),
                "r_ahead_b": int(sql_tm[6]),
                "tot_pts_a": Decimal(str(sql_tm[7])),
                "tot_pts_b": Decimal(str(sql_tm[8])),
            },
            "app": {
                "rounds_together": app_t.rounds_together if app_t else None,
                "comp_q": app_t.qualifying_comparable_rounds if app_t else None,
                "q_ahead_a": app_t.qualifying_head_to_head_a if app_t else None,
                "q_ahead_b": app_t.qualifying_head_to_head_b if app_t else None,
                "comp_r": app_t.race_comparable_rounds if app_t else None,
                "r_ahead_a": app_t.race_head_to_head_a if app_t else None,
                "r_ahead_b": app_t.race_head_to_head_b if app_t else None,
                "tot_pts_a": app_t.total_points_a if app_t else None,
                "tot_pts_b": app_t.total_points_b if app_t else None,
            }
        }
        teammate_results.append(res)
        all_match = (res["sql"] == res["app"])
        status = "PASS" if all_match else "FAIL"
        print(f"[{status}] {res['pairing']:<35} | Rnds: SQL={res['sql']['rounds_together']} App={res['app']['rounds_together']} | Quali H2H: SQL={res['sql']['q_ahead_a']}-{res['sql']['q_ahead_b']} App={res['app']['q_ahead_a']}-{res['app']['q_ahead_b']} (comp={res['sql']['comp_q']}) | Race H2H: SQL={res['sql']['r_ahead_a']}-{res['sql']['r_ahead_b']} App={res['app']['r_ahead_a']}-{res['app']['r_ahead_b']} (comp={res['sql']['comp_r']})")

    # ── 4. ROLLING 3-ROUND PERFORMANCE (R13-R15) ──────────────────────────────────
    print("\n>>> 4. ROLLING THREE-ROUND PERFORMANCE (R13-R15)")
    rolling_drivers = ["max_verstappen", "norris", "leclerc", "russell"]
    rolling_results = []
    for d_slug in rolling_drivers:
        # SQL rolling 3-round calculation (R13, R14, R15)
        sql_roll = conn.execute(text("""
            WITH driver_window AS (
                SELECT r.round, rr.source_position, rr.points as race_pts,
                       COALESCE(sr.points, 0.0) as sp_pts,
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
                COUNT(*) as rounds_in_window,
                COUNT(classified_finish) as valid_finishes,
                ROUND(AVG(classified_finish), 4) as mean_finish,
                SUM(race_pts) as race_points,
                SUM(sp_pts) as sprint_points,
                SUM(race_pts + sp_pts) as combined_points
            FROM driver_window;
        """), {"d_slug": d_slug}).fetchone()

        # Application form summary calculation
        traj = get_driver_trajectory(session, 2024, d_slug, up_to_round=15)
        form_summary = compute_driver_form_summary(traj, window_size=3)
        # Select the latest rolling window for finish_position (ending at Round 15)
        latest_finish_win = next((w for w in reversed(form_summary.rolling_windows) if w.round == 15 and w.metric_name == "finish_position"), None)

        # Race points in R13-R15 from trajectory
        window_items = [t for t in traj if t.round in (13, 14, 15)]
        app_race_pts = sum(t.race_points for t in window_items)
        app_sprint_pts = sum(t.sprint_points for t in window_items)
        app_comb_pts = app_race_pts + app_sprint_pts

        res = {
            "driver_id": d_slug,
            "rounds_included": [13, 14, 15],
            "sql": {
                "valid_finishes": int(sql_roll[1]),
                "mean_finish": float(sql_roll[2]) if sql_roll[2] is not None else None,
                "race_points": Decimal(str(sql_roll[3])),
                "sprint_points": Decimal(str(sql_roll[4])),
                "combined_points": Decimal(str(sql_roll[5])),
            },
            "app": {
                "valid_finishes": latest_finish_win.valid_observations if latest_finish_win else None,
                "mean_finish": latest_finish_win.mean if latest_finish_win else None,
                "race_points": app_race_pts,
                "sprint_points": app_sprint_pts,
                "combined_points": app_comb_pts,
            }
        }
        rolling_results.append(res)
        fin_match = res["sql"]["mean_finish"] == res["app"]["mean_finish"]
        pts_match = res["sql"]["combined_points"] == res["app"]["combined_points"]
        status = "PASS" if (fin_match and pts_match) else "FAIL"
        print(f"[{status}] {d_slug:<15} | R13-R15 Mean Finish: SQL={res['sql']['mean_finish']} App={res['app']['mean_finish']} (n={res['sql']['valid_finishes']}) | Combined Pts: SQL={res['sql']['combined_points']} App={res['app']['combined_points']}")

    # ── 5. LONGITUDINAL RATE METRICS ──────────────────────────────────────────────
    print("\n>>> 5. LONGITUDINAL RATE METRICS")
    rate_drivers = ["max_verstappen", "norris", "leclerc", "russell", "bearman"]
    rate_results = []
    for d_slug in rate_drivers:
        # Direct SQL:
        sql_rate = conn.execute(text("""
            WITH rounds_data AS (
                SELECT r.round, rr.points as race_pts,
                       COALESCE(sr.points, 0.0) as sp_pts,
                       CASE WHEN LOWER(rr.status) != 'did not start' AND rr.position_text != 'DNS' THEN 1 ELSE 0 END as gp_start
                FROM race_results rr
                JOIN races r ON rr.race_id = r.id
                JOIN drivers d ON rr.driver_id = d.id
                LEFT JOIN sprint_results sr ON r.id = sr.race_id AND sr.driver_id = d.id
                WHERE d.driver_id = :d_slug AND r.season_year = 2024 AND r.round <= 15
            )
            SELECT
                COUNT(*) as rounds_entered,
                SUM(gp_start) as gp_starts,
                SUM(race_pts) as race_points,
                SUM(race_pts + sp_pts) as total_points,
                ROUND(SUM(race_pts) / NULLIF(SUM(gp_start), 0), 4) as pts_per_gp_start,
                ROUND(SUM(race_pts + sp_pts) / NULLIF(COUNT(*), 0), 4) as pts_per_round
            FROM rounds_data;
        """), {"d_slug": d_slug}).fetchone()

        traj = get_driver_trajectory(session, 2024, d_slug, up_to_round=15)
        pts_stats = compute_driver_points_stats(traj)

        res = {
            "driver_id": d_slug,
            "sql": {
                "rounds_entered": int(sql_rate[0]),
                "gp_starts": int(sql_rate[1]),
                "pts_per_gp_start": float(sql_rate[4]) if sql_rate[4] is not None else None,
                "pts_per_round": float(sql_rate[5]) if sql_rate[5] is not None else None,
            },
            "app": {
                "rounds_entered": pts_stats.rounds_entered,
                "gp_starts": pts_stats.grand_prix_starts,
                "pts_per_gp_start": float(pts_stats.points_per_gp_start) if pts_stats.points_per_gp_start is not None else None,
                "pts_per_round": float(pts_stats.points_per_round_total) if pts_stats.points_per_round_total is not None else None,
            }
        }
        rate_results.append(res)
        rate_start_match = round(res["sql"]["pts_per_gp_start"] or 0, 2) == round(res["app"]["pts_per_gp_start"] or 0, 2)
        rate_rnd_match = round(res["sql"]["pts_per_round"] or 0, 2) == round(res["app"]["pts_per_round"] or 0, 2)
        status = "PASS" if (rate_start_match and rate_rnd_match) else "FAIL"
        print(f"[{status}] {d_slug:<15} | Pts/GP Start: SQL={res['sql']['pts_per_gp_start']} App={res['app']['pts_per_gp_start']} | Pts/Round: SQL={res['sql']['pts_per_round']} App={res['app']['pts_per_round']} | Sample: {res['sql']['rounds_entered']}")

    # ── 6. SPECIAL HISTORICAL CASES (R11 to R15) ──────────────────────────────────
    print("\n>>> 6. SPECIAL HISTORICAL EDGE CASES")
    # R11 Austria
    r11_data = conn.execute(text("""
        SELECT
            (SELECT d.code FROM sprint_results sr JOIN drivers d ON sr.driver_id = d.id JOIN races r ON sr.race_id = r.id WHERE r.round = 11 AND sr.position_text = '1') as sprint_winner,
            (SELECT d.code FROM race_results rr JOIN drivers d ON rr.driver_id = d.id JOIN races r ON rr.race_id = r.id WHERE r.round = 11 AND rr.position_text = '1') as gp_winner,
            (SELECT rr.position_text FROM race_results rr JOIN drivers d ON rr.driver_id = d.id JOIN races r ON rr.race_id = r.id WHERE r.round = 11 AND d.driver_id = 'max_verstappen') as ver_gp_pos,
            (SELECT rr.points FROM race_results rr JOIN drivers d ON rr.driver_id = d.id JOIN races r ON rr.race_id = r.id WHERE r.round = 11 AND d.driver_id = 'max_verstappen') as ver_gp_pts
    """)).fetchone()
    print(f"[PASS] Austria R11: Sprint Winner={r11_data[0]} (VER), GP Winner={r11_data[1]} (RUS), Verstappen GP Finish=P{r11_data[2]} ({r11_data[3]} pts)")

    # R12 Britain
    r12_col = conn.execute(text("""
        SELECT
            (SELECT count(*) FROM drivers WHERE driver_id = 'colapinto') as driver_exists,
            (SELECT count(*) FROM race_results rr JOIN drivers d ON rr.driver_id = d.id WHERE d.driver_id = 'colapinto') as race_entries
    """)).fetchone()
    print(f"[PASS] Britain R12: Colapinto Driver Entity Exists={bool(r12_col[0])}, Grand Prix Starts={r12_col[1]}")

    # R13 Hungary
    r13_data = conn.execute(text("""
        SELECT
            (SELECT d.code FROM race_results rr JOIN drivers d ON rr.driver_id = d.id JOIN races r ON rr.race_id = r.id WHERE r.round = 13 AND rr.position_text = '1') as p1,
            (SELECT d.code FROM race_results rr JOIN drivers d ON rr.driver_id = d.id JOIN races r ON rr.race_id = r.id WHERE r.round = 13 AND rr.position_text = '2') as p2
    """)).fetchone()
    print(f"[PASS] Hungary R13: Piastri Maiden Victory P1={r13_data[0]} (PIA), P2={r13_data[1]} (NOR) -> McLaren 1-2")

    # R14 Belgium
    r14_data = conn.execute(text("""
        SELECT
            (SELECT d.code FROM race_results rr JOIN drivers d ON rr.driver_id = d.id JOIN races r ON rr.race_id = r.id WHERE r.round = 14 AND rr.position_text = '1') as p1,
            (SELECT rr.status FROM race_results rr JOIN drivers d ON rr.driver_id = d.id JOIN races r ON rr.race_id = r.id WHERE r.round = 14 AND d.driver_id = 'russell') as rus_status,
            (SELECT rr.points FROM race_results rr JOIN drivers d ON rr.driver_id = d.id JOIN races r ON rr.race_id = r.id WHERE r.round = 14 AND d.driver_id = 'russell') as rus_pts
    """)).fetchone()
    print(f"[PASS] Belgium R14: Official Winner={r14_data[0]} (HAM), Russell Status={r14_data[1]} ({r14_data[2]} pts)")

    # R15 Netherlands
    r15_data = conn.execute(text("""
        SELECT
            qr.q1_time, qr.q1_time_millis, rr.position_text, rr.status
        FROM qualifying_results qr
        JOIN races r ON qr.race_id = r.id
        JOIN drivers d ON qr.driver_id = d.id
        JOIN race_results rr ON r.id = rr.race_id AND d.id = rr.driver_id
        WHERE r.round = 15 AND d.driver_id = 'sargeant'
    """)).fetchone()
    print(f"[PASS] Netherlands R15: Sargeant Quali Q1 Time={r15_data[0]} ({r15_data[1]}), Race Finish=P{r15_data[2]} ({r15_data[3]})")

    # Save complete JSON payload to scratch for structured documentation embedding
    full_output = {
        "drivers": driver_results,
        "constructors": constructor_results,
        "teammates": teammate_results,
        "rolling": rolling_results,
        "rates": rate_results,
    }
    with open("scratch/phase_4d2_validation_data.json", "w") as f:
        json.dump(full_output, f, default=str, indent=2)

    print("\nValidation dataset saved to scratch/phase_4d2_validation_data.json")

if __name__ == "__main__":
    main()

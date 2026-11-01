"""
Phase 5B Stage 3 — Compare SQL References with Application Outputs
Full-season 2024 (Rounds 1-24)
"""
import os, json
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.analytics.longitudinal_driver import (
    get_driver_season_aggregate,
    get_driver_trajectory,
)
from app.analytics.longitudinal_constructor import (
    get_constructor_season_aggregate,
)
from app.analytics.longitudinal_teammate import (
    get_season_teammate_comparisons,
)
from app.statistics.longitudinal import (
    compute_driver_form_summary,
    compute_driver_points_stats,
    compute_driver_longitudinal_stats,
)
from app.insights.engine import InsightEngine

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@localhost:5432/f1_race_intelligence")
engine = create_engine(DATABASE_URL)

with open("scratch/phase_5b_sql_reference.json", "r") as f:
    sql_ref = json.load(f)

discrepancies = []

def check(category, entity, metric, sql_val, app_val, tolerance=0.01):
    diff = None
    verdict = "MATCH"
    if sql_val is None and app_val is None:
        verdict = "MATCH"
    elif sql_val is None or app_val is None:
        verdict = "DISCREPANCY"
        diff = f"sql={sql_val}, app={app_val}"
    elif isinstance(sql_val, (int, float, Decimal)) and isinstance(app_val, (int, float, Decimal)):
        diff_val = abs(float(sql_val) - float(app_val))
        if diff_val > tolerance:
            verdict = "DISCREPANCY"
            diff = f"{diff_val:.4f} (sql={sql_val}, app={app_val})"
        else:
            verdict = "MATCH"
    else:
        if str(sql_val) != str(app_val):
            verdict = "DISCREPANCY"
            diff = f"sql={sql_val}, app={app_val}"
        else:
            verdict = "MATCH"
    
    res = {
        "category": category,
        "entity": entity,
        "metric": metric,
        "sql_val": sql_val,
        "app_val": app_val,
        "difference": diff,
        "verdict": verdict
    }
    discrepancies.append(res)
    if verdict == "DISCREPANCY":
        print(f"  [DISCREPANCY] {category} | {entity} | {metric}: {diff}")
    return res

with Session(engine) as session:
    print("=== 1. AUDITING DRIVER AGGREGATES ===")
    target_drivers = [
        "max_verstappen","perez","norris","leclerc","sainz",
        "russell","hamilton","piastri","bearman","lawson","antonelli","colapinto"
    ]
    for drv_slug in target_drivers:
        ref = sql_ref["driver_aggregates"].get(drv_slug)
        app_agg = get_driver_season_aggregate(session, 2024, drv_slug)
        if ref is None:
            check("Driver Aggregate", drv_slug, "existence", None, app_agg)
            continue
        if app_agg is None:
            check("Driver Aggregate", drv_slug, "existence", "exists", None)
            continue
        
        check("Driver Aggregate", drv_slug, "races_entered", ref["races_entered"], app_agg.races_entered)
        check("Driver Aggregate", drv_slug, "races_classified", ref["races_classified"], app_agg.races_classified)
        check("Driver Aggregate", drv_slug, "dnf_count", ref["non_classified"], app_agg.dnf_count)
        check("Driver Aggregate", drv_slug, "gp_points", ref["gp_points"], float(app_agg.total_race_points))
        check("Driver Aggregate", drv_slug, "sprint_points", ref["sprint_points"], float(app_agg.total_sprint_points))
        check("Driver Aggregate", drv_slug, "total_points", ref["total_points"], float(app_agg.total_points))
        check("Driver Aggregate", drv_slug, "wins", ref["wins"], app_agg.wins)
        check("Driver Aggregate", drv_slug, "avg_classified_finish", ref["avg_classified_finish"], app_agg.average_finish)
        check("Driver Aggregate", drv_slug, "avg_grid", ref["avg_grid"], app_agg.average_grid)
        check("Driver Aggregate", drv_slug, "championship_standing", ref["championship_standing"], app_agg.championship_standing)

    print("\n=== 2. AUDITING CONSTRUCTOR AGGREGATES ===")
    for con_slug, ref in sql_ref["constructor_aggregates"].items():
        app_agg = get_constructor_season_aggregate(session, 2024, con_slug)
        if app_agg is None:
            check("Constructor Aggregate", con_slug, "existence", "exists", None)
            continue
        check("Constructor Aggregate", con_slug, "gp_points", ref["gp_points"], float(app_agg.total_race_points))
        check("Constructor Aggregate", con_slug, "sprint_points", ref["sprint_points"], float(app_agg.total_sprint_points))
        check("Constructor Aggregate", con_slug, "total_points", ref["total_points"], float(app_agg.total_points))
        check("Constructor Aggregate", con_slug, "wins", ref["wins"], app_agg.wins)
        check("Constructor Aggregate", con_slug, "championship_standing", ref["championship_standing"], app_agg.championship_standing)
        contrib_sum = sum(c.total_points for c in app_agg.driver_contributions)
        check("Constructor Aggregate", con_slug, "driver_contributions_sum", float(app_agg.total_points), float(contrib_sum))

    print("\n=== 3. AUDITING TEAMMATE HEAD-TO-HEAD COMPARISONS ===")
    app_season_h2h = get_season_teammate_comparisons(session, 2024)
    app_h2h_map = {f"{p.constructor_id}:{p.driver_a_id}:{p.driver_b_id}": p for p in app_season_h2h}
    
    for con_slug, ref in sql_ref["h2h"].items():
        key = f"{con_slug}:{ref['driver_a']}:{ref['driver_b']}"
        app_p = app_h2h_map.get(key)
        if app_p is None:
            check("Teammate H2H", key, "pairing_exists", "exists", None)
            continue
        check("Teammate H2H", key, "quali_a_ahead", ref["quali_a_ahead"], app_p.qualifying_head_to_head_a)
        check("Teammate H2H", key, "quali_b_ahead", ref["quali_b_ahead"], app_p.qualifying_head_to_head_b)
        check("Teammate H2H", key, "quali_comparable", ref["quali_comparable"], app_p.qualifying_comparable_rounds)
        check("Teammate H2H", key, "race_a_ahead", ref["race_a_ahead"], app_p.race_head_to_head_a)
        check("Teammate H2H", key, "race_b_ahead", ref["race_b_ahead"], app_p.race_head_to_head_b)
        check("Teammate H2H", key, "race_comparable", ref["race_comparable"], app_p.race_comparable_rounds)

    print("\n=== 4. AUDITING ROLLING PERFORMANCE ===")
    for drv_slug in ["max_verstappen","norris","leclerc","piastri","russell","hamilton"]:
        traj = get_driver_trajectory(session, 2024, drv_slug)
        form3 = compute_driver_form_summary(traj, window_size=3)
        ref3 = sql_ref["rolling"].get(f"{drv_slug}_last3")
        if form3 and ref3:
            f_win = next((w for w in reversed(form3.rolling_windows) if w.metric_name == "finish_position"), None)
            if f_win and f_win.mean is not None:
                check("Rolling Form", drv_slug, "last3_avg_finish", ref3["avg_classified_finish"], round(f_win.mean, 2))
            pts_3 = sum(float(item.total_round_points) for item in traj[-3:])
            check("Rolling Form", drv_slug, "last3_total_points", ref3["total_points"], pts_3)

        form5 = compute_driver_form_summary(traj, window_size=5)
        ref5 = sql_ref["rolling"].get(f"{drv_slug}_last5")
        if form5 and ref5:
            f_win = next((w for w in reversed(form5.rolling_windows) if w.metric_name == "finish_position"), None)
            if f_win and f_win.mean is not None:
                check("Rolling Form", drv_slug, "last5_avg_finish", ref5["avg_classified_finish"], round(f_win.mean, 2))
            pts_5 = sum(float(item.total_round_points) for item in traj[-5:])
            check("Rolling Form", drv_slug, "last5_total_points", ref5["total_points"], pts_5)

    print("\n=== 5. AUDITING POINTS RATES ===")
    for drv_slug, ref in sql_ref["points_rates"].items():
        traj = get_driver_trajectory(session, 2024, drv_slug)
        pts_stats = compute_driver_points_stats(traj)
        check("Points Rates", drv_slug, "gp_points_per_start", ref["gp_points_per_start"], round(pts_stats.points_per_gp_start, 2))
        check("Points Rates", drv_slug, "total_points_per_round", ref["total_points_per_round"], round(pts_stats.points_per_round_total, 2))

    print("\n=== 6. AUDITING DETERMINISTIC INSIGHT GENERATION ===")
    insights = InsightEngine.evaluate_season_longitudinal_insights(session, 2024)
    print(f"Total longitudinal insights generated for 2024 full season: {len(insights)}")
    rule_counts = {}
    for ins in insights:
        rule_counts[ins.rule_id] = rule_counts.get(ins.rule_id, 0) + 1
    for rid, cnt in sorted(rule_counts.items()):
        print(f"  {rid:<45}: {cnt}")

total_checks = len(discrepancies)
matches = sum(1 for d in discrepancies if d["verdict"] == "MATCH")
disc_list = [d for d in discrepancies if d["verdict"] == "DISCREPANCY"]

print("\n=======================================================")
print(f"COMPARISON SUMMARY: {total_checks} checks performed.")
print(f"MATCH: {matches}")
print(f"DISCREPANCIES: {len(disc_list)}")
print("=======================================================")

with open("scratch/phase_5b_comparison_results.json", "w") as f:
    json.dump({
        "total_checks": total_checks,
        "matches": matches,
        "discrepancies": disc_list,
        "all_checks": discrepancies,
        "insight_rule_counts": rule_counts
    }, f, indent=2)
print("Saved to scratch/phase_5b_comparison_results.json")

"""
Phase 5B.0.1 Section 3: Points Rates Denominators Audit
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.analytics.longitudinal_driver import get_driver_trajectory
from app.statistics.longitudinal import compute_driver_points_stats

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@127.0.0.1:5432/f1_race_intelligence")
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    print(f"{'DRIVER':<18} {'STARTS':<7} {'ROUNDS_ENT':<11} {'GP_PTS':<8} {'SPR_PTS':<8} {'TOT_PTS':<8} {'PTS/GP_START':<13} {'PTS/ENT_RND':<12} {'PTS/SEASON_RND (24)':<18}")
    print("-" * 108)

    all_drivers = [
        "max_verstappen","norris","leclerc","piastri","sainz","russell","hamilton","perez",
        "alonso","gasly","hulkenberg","tsunoda","stroll","ocon","kevin_magnussen",
        "albon","ricciardo","bearman","colapinto","lawson","zhou","bottas","sargeant","doohan","antonelli"
    ]

    for drv_slug in all_drivers:
        traj = get_driver_trajectory(session, 2024, drv_slug)
        if not traj:
            print(f"{drv_slug:<18} 0       0           0.0      0.0      0.0      N/A           N/A          N/A (0 entries)")
            continue
        stats = compute_driver_points_stats(traj)
        gp_starts = stats.grand_prix_starts
        rounds_ent = stats.rounds_entered
        gp_pts = float(stats.total_race_points)
        spr_pts = float(stats.total_sprint_points)
        tot_pts = float(stats.total_championship_points)

        pps = f"{stats.points_per_gp_start:.2f}" if stats.points_per_gp_start is not None else "N/A"
        pp_ent = f"{stats.points_per_round_total:.2f}" if stats.points_per_round_total is not None else "N/A"
        pp_season = f"{(tot_pts / 24.0):.2f}"

        print(f"{drv_slug:<18} {gp_starts:<7} {rounds_ent:<11} {gp_pts:<8.1f} {spr_pts:<8.1f} {tot_pts:<8.1f} {pps:<13} {pp_ent:<12} {pp_season:<18}")

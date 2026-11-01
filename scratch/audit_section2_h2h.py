"""
Phase 5B.0.1 Section 2: Teammate H2H Event-by-Event Exclusion Audit
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@127.0.0.1:5432/f1_race_intelligence")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    for da, db, con_slug in [("max_verstappen", "perez", "red_bull"), ("hamilton", "russell", "mercedes")]:
        print(f"\n=========================================================================")
        print(f"H2H EVENT BREAKDOWN: {con_slug.upper()} ({da} vs {db})")
        print(f"=========================================================================")
        rows = conn.execute(text("""
            SELECT
                r.round,
                r.race_name,
                rra.grid_position AS grid_a,
                rra.source_position AS pos_a,
                rra.position_text AS pos_txt_a,
                rra.status AS status_a,
                rrb.grid_position AS grid_b,
                rrb.source_position AS pos_b,
                rrb.position_text AS pos_txt_b,
                rrb.status AS status_b,
                qa.position AS q_pos_a,
                qb.position AS q_pos_b
            FROM races r
            JOIN constructors c ON c.constructor_id = :con
            JOIN race_results rra ON rra.race_id = r.id AND rra.constructor_id = c.id
            JOIN race_results rrb ON rrb.race_id = r.id AND rrb.constructor_id = c.id
            JOIN drivers da ON rra.driver_id = da.id AND da.driver_id = :da
            JOIN drivers db ON rrb.driver_id = db.id AND db.driver_id = :db
            LEFT JOIN qualifying_results qa ON qa.race_id = r.id AND qa.driver_id = da.id
            LEFT JOIN qualifying_results qb ON qb.race_id = r.id AND qb.driver_id = db.id
            WHERE r.season_year = 2024
            ORDER BY r.round
        """), {"con": con_slug, "da": da, "db": db}).fetchall()

        q_comp = 0
        q_a_ahead = 0
        q_b_ahead = 0

        r_comp = 0
        r_a_ahead = 0
        r_b_ahead = 0

        excluded_race_events = []
        excluded_quali_events = []

        for row in rows:
            rnd = row[0]
            name = row[1]
            pos_a, txt_a, stat_a = row[3], row[4], (row[5] or "")
            pos_b, txt_b, stat_b = row[7], row[8], (row[9] or "")
            qp_a, qp_b = row[10], row[11]

            # Quali comparison
            if qp_a is not None and qp_b is not None:
                q_comp += 1
                if qp_a < qp_b:
                    q_a_ahead += 1
                    q_winner = da
                elif qp_b < qp_a:
                    q_b_ahead += 1
                    q_winner = db
                else:
                    q_winner = "TIE"
            else:
                excluded_quali_events.append((rnd, name, f"Missing quali: qa={qp_a}, qb={qp_b}"))
                q_winner = "EXCLUDED"

            # Race classification check
            class_a = (txt_a and txt_a.isdigit() and stat_a.lower() not in ["retired", "did not start", "disqualified", "withdrawn"])
            class_b = (txt_b and txt_b.isdigit() and stat_b.lower() not in ["retired", "did not start", "disqualified", "withdrawn"])

            if class_a and class_b:
                r_comp += 1
                if pos_a < pos_b:
                    r_a_ahead += 1
                    r_winner = da
                elif pos_b < pos_a:
                    r_b_ahead += 1
                    r_winner = db
                else:
                    r_winner = "TIE"
                print(f"  R{rnd:02d} {name:<26} Quali: P{qp_a} vs P{qp_b} ({q_winner}) | Race: P{pos_a} vs P{pos_b} ({r_winner}) [COMP]")
            else:
                reasons = []
                if not class_a:
                    reasons.append(f"{da} unclassified (txt={txt_a!r}, status={stat_a!r})")
                if not class_b:
                    reasons.append(f"{db} unclassified (txt={txt_b!r}, status={stat_b!r})")
                reason_str = "; ".join(reasons)
                excluded_race_events.append((rnd, name, reason_str))
                print(f"  R{rnd:02d} {name:<26} Quali: P{qp_a} vs P{qp_b} ({q_winner}) | Race: EXCLUDED ({reason_str})")

        print(f"\n--- {con_slug.upper()} SUMMARY ---")
        print(f"Qualifying: {da} {q_a_ahead} - {q_b_ahead} {db} ({q_comp} comparable rounds, {len(excluded_quali_events)} excluded)")
        print(f"Race:       {da} {r_a_ahead} - {r_b_ahead} {db} ({r_comp} comparable rounds, {len(excluded_race_events)} excluded)")
        print(f"\nExcluded Race Events for {con_slug}:")
        for rnd, name, reason in excluded_race_events:
            print(f"  - Round {rnd:02d} ({name}): {reason}")

"""
Phase 5B.0.1 Section 4: Detailed 33 Deterministic Insights Audit
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.insights.engine import InsightEngine

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://f1user:changeme@127.0.0.1:5432/f1_race_intelligence")
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    insights = InsightEngine.evaluate_season_longitudinal_insights(session, 2024)
    print(f"Total insights evaluated: {len(insights)}")

    for i, ins in enumerate(insights, 1):
        tr = ins.traceability
        print(f"\n--- INSIGHT {i:02d}: {ins.insight_id} ---")
        print(f"  Category:               {ins.category.value}")
        print(f"  Rule ID:                {ins.rule_id}")
        print(f"  Subject:                {ins.subject_id}")
        print(f"  Comparison Subject:     {ins.comparison_subject_id}")
        print(f"  Direction:              {ins.direction.value}")
        print(f"  Magnitude:              {ins.magnitude} {ins.unit}")
        print(f"  Evidence Strength:      {ins.evidence_strength.value}")
        print(f"  Sample Size:            {ins.sample_size}")
        print(f"  Explanation:            {ins.explanation}")
        if tr:
            print(f"  Traceability:")
            print(f"    source_metric:        {tr.source_metric}")
            print(f"    source_function:      {tr.source_function}")
            print(f"    rule_parameters:      {tr.rule_parameters}")
            print(f"    observed_value:       {tr.observed_value}")
            print(f"    min_sample_size:      {tr.minimum_sample_size}")
            print(f"    rounds_included:      {tr.rounds_included}")
            print(f"    excluded_obs:         {tr.excluded_observations}")
            print(f"    sign_convention:      {tr.sign_convention}")

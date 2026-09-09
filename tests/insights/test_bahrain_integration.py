"""Integration tests for the deterministic insight engine on the Bahrain 2024 dataset."""

from app.insights.engine import InsightEngine
from app.insights.types import Direction, EvidenceStrength, InsightCategory


class TestBahrainInsightIntegration:
    def test_evaluate_race_insights_bahrain(self, session, bahrain_analytics_data):
        insights = InsightEngine.evaluate_race_insights(
            session, season_year=2024, round_num=1
        )
        assert len(insights) > 0

        # Verify all generated insights have stable IDs and valid structure
        rule_ids = {ins.rule_id for ins in insights}
        categories = {ins.category for ins in insights}

        # Categories present
        assert InsightCategory.QUALIFYING in categories
        assert InsightCategory.POSITION_CHANGE in categories
        assert InsightCategory.TEAMMATE in categories

        # 1. Qualifying insights: Verstappen faster than Perez, Leclerc faster than Sainz
        assert "QUALIFYING_TEAMMATE_ADVANTAGE" in rule_ids
        rb_quali = next(
            i for i in insights
            if i.rule_id == "QUALIFYING_TEAMMATE_ADVANTAGE" and i.subject_id == "max_verstappen"
        )
        assert rb_quali.comparison_subject_id == "perez"
        assert rb_quali.magnitude == 358.0
        assert rb_quali.direction == Direction.FASTER
        assert rb_quali.evidence_strength == EvidenceStrength.LOW  # n=1

        # 2. Position change insights
        # Verstappen: POSITION_MAINTAINED
        ver_pos = next(i for i in insights if i.subject_id == "max_verstappen" and i.category == InsightCategory.POSITION_CHANGE)
        assert ver_pos.rule_id == "POSITION_MAINTAINED"
        assert ver_pos.direction == Direction.STABLE

        # Perez: POSITION_GAIN (+3)
        per_pos = next(i for i in insights if i.subject_id == "perez" and i.category == InsightCategory.POSITION_CHANGE)
        assert per_pos.rule_id == "POSITION_GAIN"
        assert per_pos.direction == Direction.GAINED
        assert per_pos.magnitude == 3.0

        # Leclerc: POSITION_LOSS (-2)
        lec_pos = next(i for i in insights if i.subject_id == "leclerc" and i.category == InsightCategory.POSITION_CHANGE)
        assert lec_pos.rule_id == "POSITION_LOSS"
        assert lec_pos.direction == Direction.LOST
        assert lec_pos.magnitude == 2.0

        # Sargeant (DNF) and Albon (pit lane start) must NOT have position change insights
        driver_pos_ids = {
            i.subject_id for i in insights if i.category == InsightCategory.POSITION_CHANGE
        }
        assert "sargeant" not in driver_pos_ids
        assert "albon" not in driver_pos_ids

        # 3. Teammate H2H insights
        # Red Bull: Verstappen has grid advantage (-4), finish advantage (-1), points advantage (+8)
        rb_points = next(
            i for i in insights
            if i.rule_id == "TEAMMATE_POINTS_ADVANTAGE" and i.subject_id == "max_verstappen"
        )
        assert rb_points.magnitude == 8.0
        assert rb_points.direction == Direction.HIGHER

        # 4. Multi-race / large sample rules must NOT appear on single-race data
        assert "PIT_STOP_HIGH_VARIABILITY" not in rule_ids

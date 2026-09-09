"""Unit tests for teammate head-to-head multi-dimensional insight evaluation."""

from decimal import Decimal

from app.analytics.types import TeammateComparison
from app.insights.evaluators.teammate import (
    evaluate_teammate_comparison,
)
from app.insights.types import Direction


class TestTeammateRules:
    def test_single_race_independent_dimensions(self):
        # Verstappen vs Perez:
        # grid: 1 vs 5 -> delta = -4 (Verstappen started ahead)
        # finish: 1 vs 2 -> delta = -1 (Verstappen finished ahead)
        # points: 26 vs 18 -> delta = +8 (Verstappen scored more)
        comp = TeammateComparison(
            constructor_id="red_bull",
            constructor_name="Red Bull",
            driver_a_id="max_verstappen",
            driver_a_name="Max Verstappen",
            driver_b_id="perez",
            driver_b_name="Sergio Perez",
            qualifying_delta_millis=-358,
            grid_delta=-4,
            finish_delta=-1,
            points_delta=Decimal("8.0"),
        )
        insights = evaluate_teammate_comparison(comp, season_year=2024, round_num=1)
        assert len(insights) == 3

        rule_map = {i.rule_id: i for i in insights}
        assert "TEAMMATE_GRID_ADVANTAGE" in rule_map
        assert "TEAMMATE_FINISH_ADVANTAGE" in rule_map
        assert "TEAMMATE_POINTS_ADVANTAGE" in rule_map

        grid_ins = rule_map["TEAMMATE_GRID_ADVANTAGE"]
        assert grid_ins.direction == Direction.HIGHER
        assert grid_ins.magnitude == 4.0
        assert grid_ins.subject_id == "max_verstappen"
        assert grid_ins.comparison_subject_id == "perez"

        pts_ins = rule_map["TEAMMATE_POINTS_ADVANTAGE"]
        assert pts_ins.direction == Direction.HIGHER
        assert pts_ins.magnitude == 8.0

    def test_teammate_deficit_and_missing_dimensions(self):
        # Driver A started behind (grid_delta = +2 -> no advantage insight)
        # Driver A finished behind (finish_delta = +1 -> no advantage insight)
        # Driver A scored fewer points (points_delta = -5.0 -> deficit insight)
        comp = TeammateComparison(
            constructor_id="ferrari",
            constructor_name="Ferrari",
            driver_a_id="driver_a",
            driver_a_name="Driver A",
            driver_b_id="driver_b",
            driver_b_name="Driver B",
            qualifying_delta_millis=None,
            grid_delta=2,
            finish_delta=1,
            points_delta=Decimal("-5.0"),
        )
        insights = evaluate_teammate_comparison(comp)
        assert len(insights) == 1
        ins = insights[0]
        assert ins.rule_id == "TEAMMATE_POINTS_DEFICIT"
        assert ins.direction == Direction.LOWER
        assert ins.magnitude == 5.0

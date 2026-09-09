"""Unit tests for insight engine determinism, traceability, and deduplication."""

from decimal import Decimal

from app.analytics.types import GridVsFinish
from app.insights.engine import InsightEngine
from app.insights.evaluators.position_change import (
    evaluate_single_driver_position_change,
)


class TestDeterminismAndTraceability:
    def test_determinism_identical_runs(self):
        rec = GridVsFinish("perez", "Sergio", "Perez", "Red Bull", 5, 2, 3, "Finished", Decimal("18"))
        run_1 = evaluate_single_driver_position_change(rec, season_year=2024, round_num=1)
        run_2 = evaluate_single_driver_position_change(rec, season_year=2024, round_num=1)

        assert len(run_1) == len(run_2) == 1
        ins1, ins2 = run_1[0], run_2[0]

        assert ins1.insight_id == ins2.insight_id
        assert ins1.rule_id == ins2.rule_id
        assert ins1.magnitude == ins2.magnitude
        assert ins1.direction == ins2.direction
        assert ins1.traceability == ins2.traceability

    def test_traceability_completeness(self):
        rec = GridVsFinish("perez", "Sergio", "Perez", "Red Bull", 5, 2, 3, "Finished", Decimal("18"))
        insights = evaluate_single_driver_position_change(rec, season_year=2024, round_num=1)
        ins = insights[0]
        trace = ins.traceability

        assert trace.source_metric == "position_change"
        assert trace.source_function == "get_grid_vs_finish"
        assert trace.rule_id == "POSITION_GAIN"
        assert trace.observed_value == 3
        assert trace.unit == "positions"
        assert trace.sample_size == 1
        assert trace.minimum_sample_size == 1
        assert trace.season_year == 2024
        assert trace.round_num == 1
        assert trace.driver_id == "perez"
        assert "positive means gained positions" in trace.sign_convention

    def test_deduplication(self):
        rec = GridVsFinish("perez", "Sergio", "Perez", "Red Bull", 5, 2, 3, "Finished", Decimal("18"))
        ins_list_1 = evaluate_single_driver_position_change(rec, season_year=2024, round_num=1)
        ins_list_2 = evaluate_single_driver_position_change(rec, season_year=2024, round_num=1)

        combined = ins_list_1 + ins_list_2
        assert len(combined) == 2

        deduped = InsightEngine.deduplicate(combined)
        assert len(deduped) == 1
        assert deduped[0].insight_id == ins_list_1[0].insight_id

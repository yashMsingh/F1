"""Unit tests for position change insight evaluation."""

from decimal import Decimal

from app.analytics.types import GridVsFinish
from app.insights.evaluators.position_change import (
    evaluate_multi_race_position_change,
    evaluate_single_driver_position_change,
)
from app.insights.types import Direction, EvidenceStrength
from app.statistics.types import (
    DescriptiveStats,
    PositionChangeDistribution,
    PositionChangeStats,
    QualityMetadata,
)


class TestPositionChangeRules:
    def test_single_driver_gain(self):
        # Perez: grid 5, finish 2 -> gained 3
        rec = GridVsFinish("perez", "Sergio", "Perez", "Red Bull", 5, 2, 3, "Finished", Decimal("18"))
        insights = evaluate_single_driver_position_change(rec, season_year=2024, round_num=1)
        assert len(insights) == 1
        ins = insights[0]
        assert ins.rule_id == "POSITION_GAIN"
        assert ins.direction == Direction.GAINED
        assert ins.magnitude == 3.0
        assert ins.subject_id == "perez"

    def test_single_driver_large_gain(self):
        # Driver started 18th, finished 8th -> gained 10 (>= 5 threshold)
        rec = GridVsFinish("hamilton", "Lewis", "Hamilton", "Mercedes", 18, 8, 10, "Finished", Decimal("4"))
        insights = evaluate_single_driver_position_change(rec)
        assert len(insights) == 2
        rule_ids = {i.rule_id for i in insights}
        assert rule_ids == {"POSITION_GAIN", "LARGE_POSITION_GAIN"}

        large_ins = next(i for i in insights if i.rule_id == "LARGE_POSITION_GAIN")
        assert large_ins.magnitude == 10.0
        assert large_ins.direction == Direction.GAINED

    def test_single_driver_loss(self):
        # Leclerc: grid 2, finish 4 -> lost 2 (-2)
        rec = GridVsFinish("leclerc", "Charles", "Leclerc", "Ferrari", 2, 4, -2, "Finished", Decimal("12"))
        insights = evaluate_single_driver_position_change(rec)
        assert len(insights) == 1
        ins = insights[0]
        assert ins.rule_id == "POSITION_LOSS"
        assert ins.direction == Direction.LOST
        assert ins.magnitude == 2.0  # magnitude is absolute

    def test_single_driver_maintained(self):
        # Verstappen: grid 1, finish 1 -> 0 change
        rec = GridVsFinish("max_verstappen", "Max", "Verstappen", "Red Bull", 1, 1, 0, "Finished", Decimal("26"))
        insights = evaluate_single_driver_position_change(rec)
        assert len(insights) == 1
        ins = insights[0]
        assert ins.rule_id == "POSITION_MAINTAINED"
        assert ins.direction == Direction.STABLE
        assert ins.magnitude == 0.0

    def test_missing_position_change_emits_no_insights(self):
        # DNF or pit-lane start where position_change is None
        rec_dnf = GridVsFinish("sargeant", "Logan", "Sargeant", "Williams", 18, None, None, "Engine", Decimal("0"))
        assert evaluate_single_driver_position_change(rec_dnf) == []

        rec_pit = GridVsFinish("albon", "Alex", "Albon", "Williams", None, 10, None, "Finished", Decimal("1"))
        assert evaluate_single_driver_position_change(rec_pit) == []

    def test_multi_race_position_change(self):
        stats = PositionChangeStats(
            stats=DescriptiveStats(sample_size=6, mean=2.5, median=2.0, stddev=1.2, minimum=0.0, maximum=4.0),
            distribution=PositionChangeDistribution(6, 5, 0, 1, 5/6, 0.0, 1/6),
            quality=QualityMetadata(6, 6, 0),
        )
        ins = evaluate_multi_race_position_change("perez", stats)
        assert ins is not None
        assert ins.rule_id == "POSITION_GAIN"
        assert ins.evidence_strength == EvidenceStrength.HIGH  # n=6 >= 5
        assert ins.magnitude == 2.5

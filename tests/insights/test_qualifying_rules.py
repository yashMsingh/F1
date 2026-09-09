"""Unit tests for qualifying insight evaluation."""

from app.analytics.types import TeammateQualifyingComparison
from app.insights.evaluators.qualifying import (
    evaluate_qualifying_teammate_insight,
)
from app.insights.types import Direction, EvidenceStrength
from app.statistics.types import DescriptiveStats, QualifyingDeltaStats, QualityMetadata


class TestQualifyingRules:
    def test_driver_a_faster_advantage(self):
        comp = TeammateQualifyingComparison(
            "red_bull", "Red Bull", "max_verstappen", "Max Verstappen", "perez", "Sergio Perez",
            89179, 89537, -358
        )
        ins = evaluate_qualifying_teammate_insight(comp, season_year=2024, round_num=1)
        assert ins is not None
        assert ins.rule_id == "QUALIFYING_TEAMMATE_ADVANTAGE"
        assert ins.direction == Direction.FASTER
        assert ins.magnitude == 358.0
        assert ins.unit == "milliseconds"
        assert ins.evidence_strength == EvidenceStrength.LOW  # n=1
        assert ins.subject_id == "max_verstappen"
        assert ins.comparison_subject_id == "perez"

    def test_driver_a_slower_deficit(self):
        comp = TeammateQualifyingComparison(
            "ferrari", "Ferrari", "leclerc", "Charles Leclerc", "sainz", "Carlos Sainz",
            89500, 89300, 200
        )
        ins = evaluate_qualifying_teammate_insight(comp, season_year=2024, round_num=1)
        assert ins is not None
        assert ins.rule_id == "QUALIFYING_TEAMMATE_DEFICIT"
        assert ins.direction == Direction.SLOWER
        assert ins.magnitude == 200.0

    def test_driver_equal_times(self):
        comp = TeammateQualifyingComparison(
            "mercedes", "Mercedes", "hamilton", "Lewis Hamilton", "russell", "George Russell",
            89000, 89000, 0
        )
        ins = evaluate_qualifying_teammate_insight(comp)
        assert ins is not None
        assert ins.rule_id == "QUALIFYING_TEAMMATE_EQUAL"
        assert ins.direction == Direction.EQUAL
        assert ins.magnitude == 0.0

    def test_missing_time_returns_none(self):
        comp = TeammateQualifyingComparison(
            "williams", "Williams", "albon", "Alex Albon", "sargeant", "Logan Sargeant",
            89500, None, None
        )
        ins = evaluate_qualifying_teammate_insight(comp)
        assert ins is None

    def test_with_qualifying_delta_stats(self):
        stats = QualifyingDeltaStats(
            constructor_id="ferrari",
            driver_a_id="leclerc",
            driver_b_id="sainz",
            stats=DescriptiveStats(
                sample_size=3, mean=-120.0, median=-100.0, stddev=25.0,
                minimum=-150.0, maximum=-90.0,
            ),
            quality=QualityMetadata(3, 3, 0),
        )
        ins = evaluate_qualifying_teammate_insight(stats)
        assert ins is not None
        assert ins.rule_id == "QUALIFYING_TEAMMATE_ADVANTAGE"
        assert ins.direction == Direction.FASTER
        assert ins.magnitude == 120.0
        assert ins.evidence_strength == EvidenceStrength.MODERATE  # n=3

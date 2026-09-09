"""Unit tests for race pace insight evaluation."""

from app.insights.evaluators.race_pace import (
    evaluate_fastest_recorded_lap,
    evaluate_teammate_race_pace,
)
from app.insights.types import Direction, EvidenceStrength
from app.statistics.types import DescriptiveStats, LapTimeStats, QualityMetadata


class TestRacePaceRules:
    def test_fastest_recorded_lap(self):
        ins = evaluate_fastest_recorded_lap("max_verstappen", 92608, season_year=2024, round_num=1)
        assert ins is not None
        assert ins.rule_id == "FASTEST_RECORDED_LAP"
        assert ins.direction == Direction.FASTER
        assert ins.magnitude == 92608.0
        assert ins.unit == "milliseconds"
        assert ins.evidence_strength == EvidenceStrength.LOW

    def test_fastest_recorded_lap_none(self):
        assert evaluate_fastest_recorded_lap("max_verstappen", None) is None

    def test_teammate_race_pace_advantage(self):
        stats_a = LapTimeStats(
            stats=DescriptiveStats(sample_size=50, mean=94000.0, median=93900.0, stddev=500.0, minimum=92608.0, maximum=96000.0),
            quality=QualityMetadata(50, 50, 0),
            fastest_recorded_millis=92608,
        )
        stats_b = LapTimeStats(
            stats=DescriptiveStats(sample_size=50, mean=94500.0, median=94400.0, stddev=550.0, minimum=93000.0, maximum=96500.0),
            quality=QualityMetadata(50, 50, 0),
            fastest_recorded_millis=93000,
        )
        ins = evaluate_teammate_race_pace("driver_a", "driver_b", stats_a, stats_b, constructor_id="red_bull")
        assert ins is not None
        assert ins.rule_id == "RACE_PACE_TEAMMATE_ADVANTAGE"
        assert ins.direction == Direction.FASTER
        assert ins.magnitude == 500.0
        assert ins.evidence_strength == EvidenceStrength.HIGH  # n=50 >= 5

    def test_teammate_race_pace_deficit(self):
        stats_a = LapTimeStats(
            stats=DescriptiveStats(sample_size=40, mean=95000.0, median=94900.0, stddev=400.0, minimum=93000.0, maximum=97000.0),
            quality=QualityMetadata(40, 40, 0),
            fastest_recorded_millis=93000,
        )
        stats_b = LapTimeStats(
            stats=DescriptiveStats(sample_size=40, mean=94600.0, median=94500.0, stddev=400.0, minimum=92800.0, maximum=96500.0),
            quality=QualityMetadata(40, 40, 0),
            fastest_recorded_millis=92800,
        )
        ins = evaluate_teammate_race_pace("driver_a", "driver_b", stats_a, stats_b)
        assert ins is not None
        assert ins.rule_id == "RACE_PACE_TEAMMATE_DEFICIT"
        assert ins.direction == Direction.SLOWER
        assert ins.magnitude == 400.0

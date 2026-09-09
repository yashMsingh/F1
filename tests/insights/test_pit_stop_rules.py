"""Unit tests for pit stop insight evaluation."""

from app.insights.evaluators.pit_stops import (
    evaluate_fast_pit_stop,
    evaluate_pit_stop_variability,
)
from app.insights.types import Direction, EvidenceStrength
from app.statistics.types import DescriptiveStats, PitStopStats, QualityMetadata


class TestPitStopRules:
    def test_fast_pit_stop(self):
        # 24123 ms < 25000 ms threshold
        ins = evaluate_fast_pit_stop("red_bull", 24123, season_year=2024, round_num=1)
        assert ins is not None
        assert ins.rule_id == "FAST_PIT_STOP"
        assert ins.direction == Direction.FASTER
        assert ins.magnitude == 24123.0
        assert ins.unit == "milliseconds"

    def test_slow_pit_stop_no_insight(self):
        # 26500 ms >= 25000 ms
        assert evaluate_fast_pit_stop("red_bull", 26500) is None
        assert evaluate_fast_pit_stop("red_bull", None) is None

    def test_pit_stop_high_variability_success(self):
        # stddev = 1800 ms > 1500 ms, sample_size = 4 >= 2
        stats = PitStopStats(
            stats=DescriptiveStats(sample_size=4, mean=25000.0, median=24800.0, stddev=1800.0, minimum=23500.0, maximum=27500.0),
            quality=QualityMetadata(4, 4, 0),
            fastest_duration_millis=23500,
        )
        ins = evaluate_pit_stop_variability("ferrari", stats)
        assert ins is not None
        assert ins.rule_id == "PIT_STOP_HIGH_VARIABILITY"
        assert ins.direction == Direction.HIGHER
        assert ins.magnitude == 1800.0
        assert ins.evidence_strength == EvidenceStrength.MODERATE  # n=4

    def test_pit_stop_variability_insufficient_sample(self):
        # sample_size = 1 < 2 -> MUST return None
        stats = PitStopStats(
            stats=DescriptiveStats(sample_size=1, mean=24000.0, median=24000.0, stddev=None, minimum=24000.0, maximum=24000.0),
            quality=QualityMetadata(1, 1, 0),
            fastest_duration_millis=24000,
        )
        assert evaluate_pit_stop_variability("red_bull", stats) is None

    def test_pit_stop_variability_below_threshold(self):
        # stddev = 300 ms <= 1500 ms -> returns None
        stats = PitStopStats(
            stats=DescriptiveStats(sample_size=3, mean=24000.0, median=24000.0, stddev=300.0, minimum=23700.0, maximum=24300.0),
            quality=QualityMetadata(3, 3, 0),
            fastest_duration_millis=23700,
        )
        assert evaluate_pit_stop_variability("red_bull", stats) is None

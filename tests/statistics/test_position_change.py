"""Unit tests for position change statistics and distribution."""

from decimal import Decimal

from app.analytics.types import GridVsFinish
from app.statistics.position_change import (
    compute_driver_position_change_stats,
    compute_position_change_distribution,
    compute_position_change_stats,
)


class TestPositionChangeStats:
    def test_empty_position_changes(self):
        res = compute_position_change_stats([])
        assert res.stats.sample_size == 0
        assert res.quality.total_observations == 0
        assert res.quality.valid_observations == 0
        assert res.quality.excluded_observations == 0
        assert res.distribution.positive_rate is None
        assert res.distribution.negative_rate is None
        assert res.distribution.zero_rate is None

    def test_mixed_integers_with_none(self):
        # 5 items: +3, -2, 0, +1, None (e.g. DNF)
        items = [3, -2, 0, 1, None]
        res = compute_position_change_stats(items)

        assert res.quality.total_observations == 5
        assert res.quality.valid_observations == 4
        assert res.quality.excluded_observations == 1

        assert res.stats.sample_size == 4
        assert res.stats.mean == (3 - 2 + 0 + 1) / 4.0  # 0.5
        assert res.stats.median == 0.5
        assert res.stats.minimum == -2.0
        assert res.stats.maximum == 3.0

        # Distribution: 2 positive, 1 negative, 1 zero
        dist = res.distribution
        assert dist.positive_count == 2
        assert dist.negative_count == 1
        assert dist.zero_count == 1
        # Denominator is valid_observations (4), NOT total (5)
        assert dist.positive_rate == 2 / 4.0  # 0.5
        assert dist.negative_rate == 1 / 4.0  # 0.25
        assert dist.zero_rate == 1 / 4.0      # 0.25

    def test_with_grid_vs_finish_records(self):
        records = [
            GridVsFinish("ver", "Max", "Verstappen", "Red Bull", 1, 1, 0, "Finished", Decimal("26")),
            GridVsFinish("per", "Sergio", "Perez", "Red Bull", 5, 2, 3, "Finished", Decimal("18")),
            GridVsFinish("lec", "Charles", "Leclerc", "Ferrari", 2, 4, -2, "Finished", Decimal("12")),
            GridVsFinish("alb", "Alex", "Albon", "Williams", None, 10, None, "Finished", Decimal("1")),
            GridVsFinish("sar", "Logan", "Sargeant", "Williams", 18, None, None, "Engine", Decimal("0")),
        ]
        res = compute_position_change_stats(records)

        assert res.quality.total_observations == 5
        assert res.quality.valid_observations == 3
        assert res.quality.excluded_observations == 2

        assert res.stats.sample_size == 3
        assert res.stats.minimum == -2.0
        assert res.stats.maximum == 3.0

        assert res.distribution.positive_count == 1
        assert res.distribution.negative_count == 1
        assert res.distribution.zero_count == 1
        assert res.distribution.positive_rate == 1 / 3.0

    def test_compute_driver_position_change_stats(self):
        records = [
            GridVsFinish("ver", "Max", "Verstappen", "Red Bull", 1, 1, 0, "Finished", Decimal("25")),
            GridVsFinish("lec", "Charles", "Leclerc", "Ferrari", 2, 4, -2, "Finished", Decimal("12")),
            GridVsFinish("ver", "Max", "Verstappen", "Red Bull", 2, 1, 1, "Finished", Decimal("25")),
        ]
        ver_stats = compute_driver_position_change_stats(records, "ver")
        assert ver_stats.quality.total_observations == 2
        assert ver_stats.quality.valid_observations == 2
        assert ver_stats.stats.sample_size == 2
        assert ver_stats.stats.mean == 0.5
        assert ver_stats.distribution.positive_count == 1
        assert ver_stats.distribution.zero_count == 1
        assert ver_stats.distribution.negative_count == 0

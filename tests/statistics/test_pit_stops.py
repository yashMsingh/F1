"""Unit tests for pit stop duration statistics."""

from unittest.mock import MagicMock

from app.statistics.pit_stops import compute_pit_stop_stats


class TestPitStopStats:
    def test_empty_pit_stops(self):
        res = compute_pit_stop_stats([])
        assert res.quality.total_observations == 0
        assert res.quality.valid_observations == 0
        assert res.quality.excluded_observations == 0
        assert res.stats.sample_size == 0
        assert res.fastest_duration_millis is None

    def test_pit_stops_with_missing_duration(self):
        # 3 stops: 24123 ms, 23856 ms, None (unrecorded / missing duration)
        stops = [24123, 23856, None]
        res = compute_pit_stop_stats(stops)

        assert res.quality.total_observations == 3
        assert res.quality.valid_observations == 2
        assert res.quality.excluded_observations == 1

        assert res.stats.sample_size == 2
        assert res.fastest_duration_millis == 23856
        assert res.stats.minimum == 23856.0
        assert res.stats.maximum == 24123.0
        assert res.stats.mean == (24123 + 23856) / 2.0
        assert res.stats.stddev is not None

    def test_pit_stop_objects(self):
        ps1 = MagicMock(duration_millis=22500)
        ps2 = MagicMock(duration_millis=25000)
        res = compute_pit_stop_stats([ps1, ps2])

        assert res.quality.valid_observations == 2
        assert res.fastest_duration_millis == 22500
        assert res.stats.mean == 23750.0

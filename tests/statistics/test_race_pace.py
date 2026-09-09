"""Unit tests for lap time statistics and race pace."""

from unittest.mock import MagicMock

from app.statistics.race_pace import compute_lap_time_stats


class TestLapTimeStats:
    def test_empty_laps(self):
        res = compute_lap_time_stats([])
        assert res.quality.total_observations == 0
        assert res.quality.valid_observations == 0
        assert res.quality.excluded_observations == 0
        assert res.stats.sample_size == 0
        assert res.fastest_recorded_millis is None

    def test_integer_sequence_with_none(self):
        laps = [95000, 94200, None, 94800]
        res = compute_lap_time_stats(laps)

        assert res.quality.total_observations == 4
        assert res.quality.valid_observations == 3
        assert res.quality.excluded_observations == 1

        assert res.stats.sample_size == 3
        assert res.fastest_recorded_millis == 94200
        assert res.stats.minimum == 94200.0
        assert res.stats.maximum == 95000.0
        assert res.stats.mean == (95000 + 94200 + 94800) / 3.0

    def test_duck_typed_lap_objects(self):
        lap1 = MagicMock(time_millis=92000)
        lap2 = MagicMock(time_millis=93500)
        lap3 = MagicMock(time_millis=None)  # unrecorded lap

        res = compute_lap_time_stats([lap1, lap2, lap3])
        assert res.quality.total_observations == 3
        assert res.quality.valid_observations == 2
        assert res.quality.excluded_observations == 1

        assert res.stats.sample_size == 2
        assert res.fastest_recorded_millis == 92000
        assert res.stats.mean == (92000 + 93500) / 2.0
        assert res.stats.stddev is not None

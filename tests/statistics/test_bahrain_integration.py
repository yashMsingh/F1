"""Integration tests linking Phase 2B.4 analytical outputs to Phase 2B.5 statistics.

Uses the controlled Bahrain 2024 dataset fixture to verify end-to-end evidence generation.
"""

from sqlalchemy import select

from app.analytics.constructor_analysis import get_teammate_comparison
from app.analytics.qualifying_analysis import get_teammate_qualifying_comparison
from app.analytics.race_analysis import get_grid_vs_finish
from app.db.models import LapTime, PitStop
from app.statistics.pit_stops import compute_pit_stop_stats
from app.statistics.position_change import compute_position_change_stats
from app.statistics.qualifying import compute_qualifying_delta_stats
from app.statistics.race_pace import compute_lap_time_stats
from app.statistics.teammate import compute_teammate_head_to_head_stats


class TestBahrainStatisticsIntegration:
    def test_grid_vs_finish_statistics_bahrain(self, session, bahrain_analytics_data):
        # 1. Fetch analytical facts
        records = get_grid_vs_finish(session, season_year=2024, round_num=1)
        assert len(records) == 6

        # 2. Compute statistical evidence
        stats = compute_position_change_stats(records)

        # 6 total entries: 4 classified with grid, 1 pit lane start (Albon), 1 DNF (Sargeant)
        assert stats.quality.total_observations == 6
        assert stats.quality.valid_observations == 4
        assert stats.quality.excluded_observations == 2

        # Valid changes:
        # Verstappen: 0
        # Perez: +3
        # Sainz: +1
        # Leclerc: -2
        assert stats.stats.sample_size == 4
        assert stats.stats.mean == (0 + 3 + 1 - 2) / 4.0  # 0.5
        assert stats.stats.minimum == -2.0
        assert stats.stats.maximum == 3.0
        assert stats.stats.stddev is not None

        # Distribution: 2 positive (Perez, Sainz), 1 negative (Leclerc), 1 zero (Verstappen)
        dist = stats.distribution
        assert dist.positive_count == 2
        assert dist.negative_count == 1
        assert dist.zero_count == 1
        # Denominator is valid_observations (4), NOT total (6)
        assert dist.positive_rate == 0.5
        assert dist.negative_rate == 0.25
        assert dist.zero_rate == 0.25

    def test_qualifying_delta_statistics_bahrain(self, session, bahrain_analytics_data):
        quali_comps = get_teammate_qualifying_comparison(session, season_year=2024, round_num=1)
        # Red Bull and Ferrari
        assert len(quali_comps) == 2

        stats_by_con = compute_qualifying_delta_stats(quali_comps)
        assert "red_bull" in stats_by_con
        assert "ferrari" in stats_by_con

        # For 1 race, sample_size = 1 -> stddev is strictly None
        rb = stats_by_con["red_bull"]
        assert rb.stats.sample_size == 1
        assert rb.stats.mean == -358.0
        assert rb.stats.stddev is None

    def test_pit_stop_statistics_bahrain(self, session, bahrain_analytics_data):
        race = bahrain_analytics_data["race"]
        stops = session.scalars(select(PitStop).where(PitStop.race_id == race.id)).all()
        # 6 pit stops in fixture: 5 with duration, 1 with NULL duration (Sainz stop 2)
        assert len(stops) == 6

        stats = compute_pit_stop_stats(stops)
        assert stats.quality.total_observations == 6
        assert stats.quality.valid_observations == 5
        assert stats.quality.excluded_observations == 1

        assert stats.stats.sample_size == 5
        assert stats.fastest_duration_millis == 23856
        assert stats.stats.stddev is not None

    def test_lap_time_statistics_bahrain(self, session, bahrain_analytics_data):
        race = bahrain_analytics_data["race"]
        laps = session.scalars(select(LapTime).where(LapTime.race_id == race.id)).all()
        # 4 laps in fixture: 3 with time_millis, 1 with NULL
        assert len(laps) == 4

        stats = compute_lap_time_stats(laps)
        assert stats.quality.total_observations == 4
        assert stats.quality.valid_observations == 3
        assert stats.quality.excluded_observations == 1

        assert stats.stats.sample_size == 3
        assert stats.fastest_recorded_millis == 92608
        assert stats.stats.stddev is not None

    def test_teammate_head_to_head_bahrain(self, session, bahrain_analytics_data):
        rb_comp = get_teammate_comparison(session, 2024, 1, "red_bull")
        fe_comp = get_teammate_comparison(session, 2024, 1, "ferrari")
        assert rb_comp is not None
        assert fe_comp is not None

        stats_by_con = compute_teammate_head_to_head_stats([rb_comp, fe_comp])
        assert "red_bull" in stats_by_con
        rb_h2h = stats_by_con["red_bull"]

        # One race -> sample_size = 1, stddev = None
        assert rb_h2h.qualifying_delta.sample_size == 1
        assert rb_h2h.qualifying_delta.mean == -358.0
        assert rb_h2h.qualifying_delta.stddev is None

        assert rb_h2h.points_delta.sample_size == 1
        assert rb_h2h.points_delta.mean == 8.0
        assert rb_h2h.points_delta.stddev is None

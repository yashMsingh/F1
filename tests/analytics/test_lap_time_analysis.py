"""Unit tests for lap time analysis queries."""

from app.analytics.lap_time_analysis import get_driver_lap_times


class TestLapTimeAnalysis:
    def test_get_driver_lap_times(self, session, bahrain_analytics_data):
        lap_summaries = get_driver_lap_times(session, season_year=2024, round_num=1)
        # Verstappen and Leclerc have lap times
        assert len(lap_summaries) == 2

        # Sorted by fastest_lap_millis (Verstappen fastest: 92608 ms vs Leclerc: 97100 ms)
        ver = lap_summaries[0]
        assert ver.driver_id == "max_verstappen"
        assert ver.lap_count == 2
        assert ver.fastest_lap_millis == 92608
        assert ver.avg_lap_millis == (96415 + 92608) // 2

        lec = lap_summaries[1]
        assert lec.driver_id == "leclerc"
        # Leclerc has 2 lap records in DB, but lap 2 has NULL time_millis
        assert lec.lap_count == 2
        assert lec.fastest_lap_millis == 97100
        # Average only takes into account non-NULL lap times
        assert lec.avg_lap_millis == 97100

    def test_get_driver_lap_times_empty(self, session, bahrain_analytics_data):
        lap_summaries = get_driver_lap_times(session, season_year=1999, round_num=1)
        assert lap_summaries == []

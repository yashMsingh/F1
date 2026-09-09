"""Unit tests for pit stop analysis queries."""

from app.analytics.pit_stop_analysis import (
    get_constructor_pit_stops,
    get_driver_pit_stops,
)


class TestDriverPitStops:
    def test_get_driver_pit_stops(self, session, bahrain_analytics_data):
        stops = get_driver_pit_stops(session, season_year=2024, round_num=1)
        # Verstappen (2), Perez (2), Leclerc (1), Sainz (1)
        assert len(stops) == 4

        # Sorted by stop_count desc, driver_id
        # Verstappen has 2 stops: 24123 ms and 23856 ms
        ver = next(s for s in stops if s.driver_id == "max_verstappen")
        assert ver.stop_count == 2
        assert ver.total_duration_millis == 24123 + 23856
        assert ver.fastest_stop_millis == 23856
        assert ver.avg_duration_millis == (24123 + 23856) // 2

        # Perez has 2 stops: 24500 and 24200
        per = next(s for s in stops if s.driver_id == "perez")
        assert per.stop_count == 2
        assert ver.total_duration_millis == 47979
        assert per.fastest_stop_millis == 24200
        assert per.avg_duration_millis == (24500 + 24200) // 2

        # Leclerc has 1 stop: 25100
        lec = next(s for s in stops if s.driver_id == "leclerc")
        assert lec.stop_count == 1
        assert lec.fastest_stop_millis == 25100
        assert lec.avg_duration_millis == 25100

        # Sainz has 1 stop with NULL duration (testing denominator filtering)
        sai = next(s for s in stops if s.driver_id == "sainz")
        assert sai.stop_count == 1
        assert sai.total_duration_millis is None
        assert sai.avg_duration_millis is None
        assert sai.fastest_stop_millis is None

    def test_get_driver_pit_stops_empty(self, session, bahrain_analytics_data):
        stops = get_driver_pit_stops(session, season_year=1999, round_num=1)
        assert stops == []


class TestConstructorPitStops:
    def test_get_constructor_pit_stops(self, session, bahrain_analytics_data):
        con_stops = get_constructor_pit_stops(session, season_year=2024, round_num=1)
        # Ferrari and Red Bull have pit stops
        assert len(con_stops) == 2

        # Sorted by constructor_id: ferrari, red_bull
        fe = con_stops[0]
        assert fe.constructor_id == "ferrari"
        # Leclerc has 1 stop, Sainz has 1 stop -> total 2 stops
        assert fe.total_stops == 2
        # Leclerc stop is 25100, Sainz stop is NULL -> avg is 25100, fastest is 25100
        assert fe.avg_duration_millis == 25100
        assert fe.fastest_stop_millis == 25100

        rb = con_stops[1]
        assert rb.constructor_id == "red_bull"
        # Verstappen has 2 stops, Perez has 2 stops -> total 4 stops
        assert rb.total_stops == 4
        durations = [24123, 23856, 24500, 24200]
        assert rb.fastest_stop_millis == min(durations)
        assert rb.avg_duration_millis == sum(durations) // len(durations)

    def test_get_constructor_pit_stops_empty(self, session, bahrain_analytics_data):
        con_stops = get_constructor_pit_stops(session, season_year=1999, round_num=1)
        assert con_stops == []

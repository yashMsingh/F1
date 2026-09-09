"""Unit tests for constructor analysis and teammate comparison queries."""

from decimal import Decimal

from app.analytics.constructor_analysis import get_teammate_comparison


class TestConstructorAnalysis:
    def test_get_teammate_comparison_red_bull(self, session, bahrain_analytics_data):
        comparison = get_teammate_comparison(
            session, season_year=2024, round_num=1, constructor_id="red_bull"
        )
        assert comparison is not None
        assert comparison.constructor_id == "red_bull"
        assert comparison.constructor_name == "Red Bull"

        # Alphabetical ordering: max_verstappen vs perez
        assert comparison.driver_a_id == "max_verstappen"
        assert comparison.driver_a_name == "Max Verstappen"
        assert comparison.driver_b_id == "perez"
        assert comparison.driver_b_name == "Sergio Perez"

        # Qualifying: Verstappen Q3 89179 ms, Perez Q3 89537 ms
        # delta = 89179 - 89537 = -358 ms
        assert comparison.qualifying_delta_millis == -358

        # Grid: Verstappen 1, Perez 5 -> delta = 1 - 5 = -4
        assert comparison.grid_delta == -4

        # Finish: Verstappen 1, Perez 2 -> delta = 1 - 2 = -1
        assert comparison.finish_delta == -1

        # Points: Verstappen 26, Perez 18 -> delta = 8.0
        assert comparison.points_delta == Decimal("8.0")

    def test_get_teammate_comparison_ferrari(self, session, bahrain_analytics_data):
        comparison = get_teammate_comparison(
            session, season_year=2024, round_num=1, constructor_id="ferrari"
        )
        assert comparison is not None
        assert comparison.constructor_id == "ferrari"

        # Alphabetical ordering: leclerc vs sainz
        assert comparison.driver_a_id == "leclerc"
        assert comparison.driver_b_id == "sainz"

        # Qualifying: Leclerc Q3 89407 ms, Sainz Q3 89507 ms -> delta = -100 ms
        assert comparison.qualifying_delta_millis == -100

        # Grid: Leclerc 2, Sainz 4 -> delta = 2 - 4 = -2
        assert comparison.grid_delta == -2

        # Finish: Leclerc 4, Sainz 3 -> delta = 4 - 3 = +1
        assert comparison.finish_delta == 1

        # Points: Leclerc 12, Sainz 15 -> delta = -3.0
        assert comparison.points_delta == Decimal("-3.0")

    def test_get_teammate_comparison_williams_with_dnf_and_pit_start(
        self, session, bahrain_analytics_data
    ):
        comparison = get_teammate_comparison(
            session, season_year=2024, round_num=1, constructor_id="williams"
        )
        assert comparison is not None
        # Alphabetical: albon vs sargeant
        assert comparison.driver_a_id == "albon"
        assert comparison.driver_b_id == "sargeant"

        # Albon did not participate in qualifying in our fixture data -> quali_delta is None
        assert comparison.qualifying_delta_millis is None

        # Albon grid None, Sargeant grid 18 -> grid_delta is None
        assert comparison.grid_delta is None

        # Albon finish 10, Sargeant finish None (DNF) -> finish_delta is None
        assert comparison.finish_delta is None

        # Points: Albon 1.0, Sargeant 0.0 -> delta = 1.0
        assert comparison.points_delta == Decimal("1.0")

    def test_get_teammate_comparison_nonexistent(self, session, bahrain_analytics_data):
        assert (
            get_teammate_comparison(
                session, season_year=2024, round_num=1, constructor_id="mercedes"
            )
            is None
        )
        assert (
            get_teammate_comparison(
                session, season_year=1999, round_num=1, constructor_id="red_bull"
            )
            is None
        )

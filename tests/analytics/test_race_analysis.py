"""Unit tests for race analysis queries."""

from decimal import Decimal

from app.analytics.race_analysis import (
    get_grid_vs_finish,
    get_race_overview,
    get_race_results,
)


class TestRaceOverview:
    def test_get_race_overview_success(self, session, bahrain_analytics_data):
        overview = get_race_overview(session, season_year=2024, round_num=1)
        assert overview is not None
        assert overview.season_year == 2024
        assert overview.round == 1
        assert overview.race_name == "Bahrain Grand Prix"
        assert overview.circuit_name == "Bahrain International Circuit"
        assert overview.winner_given_name == "Max"
        assert overview.winner_family_name == "Verstappen"
        assert overview.winner_constructor == "Red Bull"
        assert overview.winner_time_millis == 5504742
        assert overview.winner_time_text == "1:31:44.742"
        assert overview.classified_count == 5  # 5 classified (positions 1, 2, 3, 4, 10)
        assert overview.total_result_count == 6  # 6 total entries (including Sargeant DNF)

    def test_get_race_overview_nonexistent_race(self, session, bahrain_analytics_data):
        overview = get_race_overview(session, season_year=1999, round_num=1)
        assert overview is None


class TestGridVsFinish:
    def test_get_grid_vs_finish(self, session, bahrain_analytics_data):
        results = get_grid_vs_finish(session, season_year=2024, round_num=1)
        assert len(results) == 6

        # Check classified are sorted first by finish position
        finish_order = [r.driver_id for r in results]
        assert finish_order[:4] == ["max_verstappen", "perez", "sainz", "leclerc"]
        assert finish_order[4] == "albon"
        assert finish_order[5] == "sargeant"

        # Verstappen: grid 1, finish 1 -> delta 0
        ver = next(r for r in results if r.driver_id == "max_verstappen")
        assert ver.grid_position == 1
        assert ver.finish_position == 1
        assert ver.position_change == 0
        assert ver.points == Decimal("26.0")
        assert ver.status == "Finished"

        # Perez: grid 5, finish 2 -> delta +3 (gained 3 positions)
        per = next(r for r in results if r.driver_id == "perez")
        assert per.grid_position == 5
        assert per.finish_position == 2
        assert per.position_change == 3

        # Leclerc: grid 2, finish 4 -> delta -2 (lost 2 positions)
        lec = next(r for r in results if r.driver_id == "leclerc")
        assert lec.grid_position == 2
        assert lec.finish_position == 4
        assert lec.position_change == -2

        # Albon: pit lane start (grid None), finish 10 -> delta is None
        alb = next(r for r in results if r.driver_id == "albon")
        assert alb.grid_position is None
        assert alb.finish_position == 10
        assert alb.position_change is None

        # Sargeant: DNF (finish None), grid 18 -> delta is None
        sar = next(r for r in results if r.driver_id == "sargeant")
        assert sar.grid_position == 18
        assert sar.finish_position is None
        assert sar.position_change is None
        assert sar.status == "Engine"

    def test_get_grid_vs_finish_nonexistent_race(self, session, bahrain_analytics_data):
        results = get_grid_vs_finish(session, season_year=1999, round_num=1)
        assert results == []


class TestRaceResults:
    def test_get_all_results(self, session, bahrain_analytics_data):
        results = get_race_results(session, season_year=2024, round_num=1)
        assert len(results) == 6
        winner = results[0]
        assert winner.driver_id == "max_verstappen"
        assert winner.constructor_id == "red_bull"
        assert winner.fastest_lap_rank == 1

    def test_filter_by_driver(self, session, bahrain_analytics_data):
        results = get_race_results(session, season_year=2024, round_num=1, driver_id="leclerc")
        assert len(results) == 1
        assert results[0].driver_id == "leclerc"
        assert results[0].source_position == 4
        assert results[0].points == Decimal("12.0")

    def test_filter_by_constructor(self, session, bahrain_analytics_data):
        results = get_race_results(session, season_year=2024, round_num=1, constructor_id="red_bull")
        assert len(results) == 2
        driver_ids = {r.driver_id for r in results}
        assert driver_ids == {"max_verstappen", "perez"}

    def test_filter_nonexistent(self, session, bahrain_analytics_data):
        results = get_race_results(session, season_year=2024, round_num=1, driver_id="hamilton")
        assert results == []

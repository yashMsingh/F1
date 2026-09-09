"""Unit tests for driver race summary queries."""

from decimal import Decimal

from app.analytics.driver_summary import get_driver_race_summary


class TestDriverRaceSummary:
    def test_get_driver_race_summary_verstappen(self, session, bahrain_analytics_data):
        summary = get_driver_race_summary(
            session, season_year=2024, round_num=1, driver_id="max_verstappen"
        )
        assert summary is not None
        assert summary.driver_id == "max_verstappen"
        assert summary.given_name == "Max"
        assert summary.family_name == "Verstappen"
        assert summary.constructor_name == "Red Bull"
        assert summary.grid_position == 1
        assert summary.finish_position == 1
        assert summary.position_change == 0
        assert summary.points == Decimal("26.0")
        assert summary.laps_completed == 57
        assert summary.status == "Finished"
        # Verstappen had 2 pit stops — verify no row multiplication occurred
        assert summary.pit_stop_count == 2
        assert summary.race_time_millis == 5504742

    def test_get_driver_race_summary_perez(self, session, bahrain_analytics_data):
        summary = get_driver_race_summary(
            session, season_year=2024, round_num=1, driver_id="perez"
        )
        assert summary is not None
        assert summary.driver_id == "perez"
        assert summary.grid_position == 5
        assert summary.finish_position == 2
        assert summary.position_change == 3
        assert summary.pit_stop_count == 2

    def test_get_driver_race_summary_albon_pit_lane(self, session, bahrain_analytics_data):
        summary = get_driver_race_summary(
            session, season_year=2024, round_num=1, driver_id="albon"
        )
        assert summary is not None
        assert summary.driver_id == "albon"
        assert summary.grid_position is None
        assert summary.finish_position == 10
        assert summary.position_change is None
        assert summary.pit_stop_count == 0

    def test_get_driver_race_summary_sargeant_dnf(self, session, bahrain_analytics_data):
        summary = get_driver_race_summary(
            session, season_year=2024, round_num=1, driver_id="sargeant"
        )
        assert summary is not None
        assert summary.driver_id == "sargeant"
        assert summary.grid_position == 18
        assert summary.finish_position is None
        assert summary.position_change is None
        assert summary.status == "Engine"
        assert summary.points == Decimal("0.0")

    def test_get_driver_race_summary_nonexistent(self, session, bahrain_analytics_data):
        summary = get_driver_race_summary(
            session, season_year=2024, round_num=1, driver_id="hamilton"
        )
        assert summary is None

        summary2 = get_driver_race_summary(
            session, season_year=1999, round_num=1, driver_id="max_verstappen"
        )
        assert summary2 is None

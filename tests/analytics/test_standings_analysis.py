"""Unit tests for standings analysis queries."""

from decimal import Decimal

from app.analytics.standings_analysis import (
    get_constructor_standings,
    get_driver_standings,
)


class TestStandingsAnalysis:
    def test_get_driver_standings(self, session, bahrain_analytics_data):
        d_standings = get_driver_standings(session, season_year=2024, round_num=1)
        assert len(d_standings) == 4

        # Verify ordering by position
        positions = [d.position for d in d_standings]
        assert positions == [1, 2, 3, 4]

        # Leader: Verstappen
        p1 = d_standings[0]
        assert p1.driver_id == "max_verstappen"
        assert p1.position == 1
        assert p1.points == Decimal("26.0")
        assert p1.wins == 1

        # P2: Perez
        p2 = d_standings[1]
        assert p2.driver_id == "perez"
        assert p2.position == 2
        assert p2.points == Decimal("18.0")
        assert p2.wins == 0

    def test_get_constructor_standings(self, session, bahrain_analytics_data):
        c_standings = get_constructor_standings(session, season_year=2024, round_num=1)
        assert len(c_standings) == 2

        # P1: Red Bull
        rb = c_standings[0]
        assert rb.constructor_id == "red_bull"
        assert rb.position == 1
        assert rb.points == Decimal("44.0")
        assert rb.wins == 1

        # P2: Ferrari
        fe = c_standings[1]
        assert fe.constructor_id == "ferrari"
        assert fe.position == 2
        assert fe.points == Decimal("27.0")
        assert fe.wins == 0

    def test_get_standings_empty(self, session, bahrain_analytics_data):
        assert get_driver_standings(session, season_year=1999, round_num=1) == []
        assert get_constructor_standings(session, season_year=1999, round_num=1) == []

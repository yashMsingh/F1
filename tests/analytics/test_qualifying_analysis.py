"""Unit tests for qualifying analysis queries."""

from app.analytics.qualifying_analysis import (
    get_qualifying_order,
    get_teammate_qualifying_comparison,
)


class TestQualifyingOrder:
    def test_get_qualifying_order(self, session, bahrain_analytics_data):
        order = get_qualifying_order(session, season_year=2024, round_num=1)
        assert len(order) == 5

        # Check order by position
        positions = [q.position for q in order]
        assert positions == [1, 2, 4, 5, 18]

        # Check pole sitter (Verstappen)
        pole = order[0]
        assert pole.driver_id == "max_verstappen"
        assert pole.q1_time_millis == 90031
        assert pole.q2_time_millis == 89374
        assert pole.q3_time_millis == 89179

        # Check Q1-only eliminated driver (Sargeant)
        p18 = order[4]
        assert p18.driver_id == "sargeant"
        assert p18.q1_time_millis == 90770
        assert p18.q2_time_millis is None
        assert p18.q3_time_millis is None

    def test_get_qualifying_order_empty(self, session, bahrain_analytics_data):
        order = get_qualifying_order(session, season_year=1999, round_num=1)
        assert order == []


class TestTeammateQualifyingComparison:
    def test_teammate_qualifying_comparison(self, session, bahrain_analytics_data):
        comparisons = get_teammate_qualifying_comparison(session, season_year=2024, round_num=1)
        # Ferrari and Red Bull have ≥2 drivers in qualifying; Williams has only 1 in qualifying
        assert len(comparisons) == 2

        # Sorted by constructor_id: ferrari, red_bull
        fe = comparisons[0]
        assert fe.constructor_id == "ferrari"
        # Alphabetical by driver_id: leclerc vs sainz
        assert fe.driver_a_id == "leclerc"
        assert fe.driver_b_id == "sainz"
        # Leclerc Q3: 89407 ms, Sainz Q3: 89507 ms -> delta = 89407 - 89507 = -100 ms (Leclerc faster)
        assert fe.best_time_a_millis == 89407
        assert fe.best_time_b_millis == 89507
        assert fe.delta_millis == -100

        rb = comparisons[1]
        assert rb.constructor_id == "red_bull"
        # Alphabetical: max_verstappen vs perez
        assert rb.driver_a_id == "max_verstappen"
        assert rb.driver_b_id == "perez"
        # Verstappen Q3: 89179 ms, Perez Q3: 89537 ms -> delta = 89179 - 89537 = -358 ms
        assert rb.best_time_a_millis == 89179
        assert rb.best_time_b_millis == 89537
        assert rb.delta_millis == -358

    def test_teammate_qualifying_empty(self, session, bahrain_analytics_data):
        comparisons = get_teammate_qualifying_comparison(session, season_year=1999, round_num=1)
        assert comparisons == []

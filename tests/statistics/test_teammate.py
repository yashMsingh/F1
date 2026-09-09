"""Unit tests for teammate head-to-head multi-race statistics."""

from decimal import Decimal

from app.analytics.types import TeammateComparison
from app.statistics.teammate import (
    compute_constructor_head_to_head,
    compute_teammate_head_to_head_stats,
)


class TestTeammateHeadToHead:
    def test_single_race_comparison(self):
        comp = TeammateComparison(
            constructor_id="red_bull",
            constructor_name="Red Bull",
            driver_a_id="max_verstappen",
            driver_a_name="Max Verstappen",
            driver_b_id="perez",
            driver_b_name="Sergio Perez",
            qualifying_delta_millis=-358,
            grid_delta=-4,
            finish_delta=-1,
            points_delta=Decimal("8.0"),
        )
        res = compute_teammate_head_to_head_stats([comp])
        assert "red_bull" in res
        rb = res["red_bull"]

        assert rb.driver_a_id == "max_verstappen"
        assert rb.driver_b_id == "perez"
        assert rb.quality.total_observations == 1
        assert rb.quality.valid_observations == 1

        assert rb.qualifying_delta.sample_size == 1
        assert rb.qualifying_delta.mean == -358.0
        assert rb.qualifying_delta.stddev is None

        assert rb.grid_delta.sample_size == 1
        assert rb.grid_delta.mean == -4.0

        assert rb.finish_delta.sample_size == 1
        assert rb.finish_delta.mean == -1.0

        assert rb.points_delta.sample_size == 1
        assert rb.points_delta.mean == 8.0

    def test_multi_race_comparison_with_missing_deltas(self):
        c1 = TeammateComparison(
            "ferrari", "Ferrari", "leclerc", "Charles Leclerc", "sainz", "Carlos Sainz",
            -100, -2, 1, Decimal("-3.0")
        )
        c2 = TeammateComparison(
            "ferrari", "Ferrari", "leclerc", "Charles Leclerc", "sainz", "Carlos Sainz",
            -50, 1, -1, Decimal("10.0")
        )
        # Race 3: Sainz DNF in race -> finish_delta is None
        c3 = TeammateComparison(
            "ferrari", "Ferrari", "leclerc", "Charles Leclerc", "sainz", "Carlos Sainz",
            -150, -1, None, Decimal("18.0")
        )

        res = compute_constructor_head_to_head([c1, c2, c3], "ferrari")
        assert res is not None
        assert res.quality.total_observations == 3
        assert res.quality.valid_observations == 3

        # Qualifying: 3 valid (-100, -50, -150)
        assert res.qualifying_delta.sample_size == 3
        assert res.qualifying_delta.mean == -100.0
        assert res.qualifying_delta.stddev is not None

        # Finish: 2 valid (1, -1), 1 missing
        assert res.finish_delta.sample_size == 2
        assert res.finish_delta.mean == 0.0

        # Points: 3 valid (-3, 10, 18)
        assert res.points_delta.sample_size == 3
        assert res.points_delta.mean == 25.0 / 3.0

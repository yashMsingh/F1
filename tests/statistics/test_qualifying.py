"""Unit tests for qualifying teammate delta statistics."""

from app.analytics.types import TeammateQualifyingComparison
from app.statistics.qualifying import (
    compute_constructor_qualifying_delta,
    compute_qualifying_delta_stats,
)


class TestQualifyingDeltaStats:
    def test_single_race_comparison(self):
        # Driver A faster by 358 ms -> delta = -358
        comp = TeammateQualifyingComparison(
            constructor_id="red_bull",
            constructor_name="Red Bull",
            driver_a_id="max_verstappen",
            driver_a_name="Max Verstappen",
            driver_b_id="perez",
            driver_b_name="Sergio Perez",
            best_time_a_millis=89179,
            best_time_b_millis=89537,
            delta_millis=-358,
        )
        res = compute_qualifying_delta_stats([comp])
        assert "red_bull" in res
        rb = res["red_bull"]
        assert rb.constructor_id == "red_bull"
        assert rb.driver_a_id == "max_verstappen"
        assert rb.driver_b_id == "perez"
        assert rb.quality.total_observations == 1
        assert rb.quality.valid_observations == 1
        assert rb.quality.excluded_observations == 0
        assert rb.stats.sample_size == 1
        assert rb.stats.mean == -358.0
        assert rb.stats.stddev is None  # n = 1

    def test_multi_race_comparison_with_exclusions(self):
        comps = [
            # Race 1: driver A faster by 200 ms
            TeammateQualifyingComparison("ferrari", "Ferrari", "leclerc", "Charles Leclerc", "sainz", "Carlos Sainz", 89400, 89600, -200),
            # Race 2: driver B faster by 100 ms (delta = +100)
            TeammateQualifyingComparison("ferrari", "Ferrari", "leclerc", "Charles Leclerc", "sainz", "Carlos Sainz", 89500, 89400, 100),
            # Race 3: Sainz didn't set a time -> delta is None
            TeammateQualifyingComparison("ferrari", "Ferrari", "leclerc", "Charles Leclerc", "sainz", "Carlos Sainz", 89300, None, None),
        ]
        fe = compute_constructor_qualifying_delta(comps, "ferrari")
        assert fe is not None
        assert fe.quality.total_observations == 3
        assert fe.quality.valid_observations == 2
        assert fe.quality.excluded_observations == 1
        assert fe.stats.sample_size == 2
        assert fe.stats.mean == (-200 + 100) / 2.0  # -50.0
        assert fe.stats.minimum == -200.0
        assert fe.stats.maximum == 100.0
        assert fe.stats.stddev is not None

    def test_constructor_not_found(self):
        res = compute_constructor_qualifying_delta([], "mercedes")
        assert res is None

"""Unit tests for descriptive and consistency statistics."""

import math

from app.statistics.descriptive import (
    compute_consistency_stats,
    compute_descriptive_stats,
)


class TestDescriptiveStats:
    def test_empty_input(self):
        stats = compute_descriptive_stats([])
        assert stats.sample_size == 0
        assert stats.mean is None
        assert stats.median is None
        assert stats.stddev is None
        assert stats.minimum is None
        assert stats.maximum is None
        assert stats.q1 is None
        assert stats.q3 is None
        assert stats.iqr is None

    def test_all_none_input(self):
        stats = compute_descriptive_stats([None, None, None])
        assert stats.sample_size == 0
        assert stats.mean is None
        assert stats.stddev is None

    def test_single_observation(self):
        stats = compute_descriptive_stats([42])
        assert stats.sample_size == 1
        assert stats.mean == 42.0
        assert stats.median == 42.0
        assert stats.minimum == 42.0
        assert stats.maximum == 42.0
        assert stats.stddev is None  # n < 2 -> stddev is None
        assert stats.q1 is None
        assert stats.q3 is None
        assert stats.iqr is None

    def test_two_observations(self):
        stats = compute_descriptive_stats([10, 20])
        assert stats.sample_size == 2
        assert stats.mean == 15.0
        assert stats.median == 15.0
        assert stats.minimum == 10.0
        assert stats.maximum == 20.0
        # Bessel's correction: sqrt(((10-15)^2 + (20-15)^2) / (2-1)) = sqrt(50) = 7.0710678...
        assert math.isclose(stats.stddev, math.sqrt(50), rel_tol=1e-6)

    def test_multiple_observations_with_none_and_zeros(self):
        data = [0, None, 10, -5, None, 15]
        stats = compute_descriptive_stats(data)
        # Valid data: [-5, 0, 10, 15]
        assert stats.sample_size == 4
        assert stats.mean == 5.0
        assert stats.median == 5.0
        assert stats.minimum == -5.0
        assert stats.maximum == 15.0
        assert stats.stddev is not None
        assert stats.q1 is not None
        assert stats.q3 is not None
        assert stats.iqr == stats.q3 - stats.q1


class TestConsistencyStats:
    def test_consistency_empty(self):
        cs = compute_consistency_stats([])
        assert cs.stats.sample_size == 0
        assert cs.range is None
        assert cs.iqr is None
        assert cs.coefficient_of_variation is None

    def test_consistency_single(self):
        cs = compute_consistency_stats([10])
        assert cs.stats.sample_size == 1
        assert cs.range == 0.0
        assert cs.iqr is None
        assert cs.coefficient_of_variation is None

    def test_consistency_multiple_cv_allowed(self):
        # Naturally positive ratio scale (e.g. pit stop durations: 20s, 30s)
        cs = compute_consistency_stats([20.0, 30.0], allow_cv=True)
        assert cs.stats.sample_size == 2
        assert cs.range == 10.0
        assert cs.stats.mean == 25.0
        assert cs.coefficient_of_variation is not None
        expected_cv = cs.stats.stddev / 25.0
        assert math.isclose(cs.coefficient_of_variation, expected_cv)

    def test_cv_disallowed_by_default(self):
        # Even if data is positive, allow_cv is False by default
        cs = compute_consistency_stats([20.0, 30.0])
        assert cs.coefficient_of_variation is None

    def test_cv_disallowed_for_zero_or_negative_mean(self):
        # Position changes crossing zero
        cs = compute_consistency_stats([-2, 2], allow_cv=True)
        assert cs.stats.mean == 0.0
        assert cs.coefficient_of_variation is None

        cs2 = compute_consistency_stats([-5, -1], allow_cv=True)
        assert cs2.stats.mean < 0
        assert cs2.coefficient_of_variation is None

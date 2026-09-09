"""Descriptive and consistency statistics computation using Python standard library.

All calculations are deterministic and adhere to strict sample-size rules:
- n = 0: All metrics None, sample_size = 0
- n = 1: Single value provides mean, median, min, max; dispersion metrics are None
- n >= 2: Sample standard deviation (Bessel's correction) and quartiles computed
"""

from __future__ import annotations

import statistics
from typing import Optional, Sequence

from app.statistics.types import ConsistencyStats, DescriptiveStats


def compute_descriptive_stats(
    values: Sequence[Optional[float | int]],
) -> DescriptiveStats:
    """Compute standard descriptive statistics on a sequence of numeric values.

    None values are strictly ignored. Zeros and negative values are preserved.

    Args:
        values: Sequence of numeric values, potentially containing None.

    Returns:
        DescriptiveStats instance with sample size and computed metrics.
    """
    clean = [float(v) for v in values if v is not None]
    n = len(clean)

    if n == 0:
        return DescriptiveStats(
            sample_size=0,
            mean=None,
            median=None,
            stddev=None,
            minimum=None,
            maximum=None,
            q1=None,
            q3=None,
            iqr=None,
        )

    if n == 1:
        val = clean[0]
        return DescriptiveStats(
            sample_size=1,
            mean=val,
            median=val,
            stddev=None,
            minimum=val,
            maximum=val,
            q1=None,
            q3=None,
            iqr=None,
        )

    # n >= 2: compute mean, median, sample stddev, min, max
    mean_val = statistics.mean(clean)
    median_val = statistics.median(clean)
    stddev_val = statistics.stdev(clean)
    min_val = min(clean)
    max_val = max(clean)

    # Quantiles using standard inclusive percentile method
    try:
        q = statistics.quantiles(clean, n=4, method="inclusive")
        q1_val = q[0]
        q3_val = q[2]
        iqr_val = q3_val - q1_val
    except Exception:
        q1_val = None
        q3_val = None
        iqr_val = None

    return DescriptiveStats(
        sample_size=n,
        mean=mean_val,
        median=median_val,
        stddev=stddev_val,
        minimum=min_val,
        maximum=max_val,
        q1=q1_val,
        q3=q3_val,
        iqr=iqr_val,
    )


def compute_consistency_stats(
    values: Sequence[Optional[float | int]],
    *,
    allow_cv: bool = False,
) -> ConsistencyStats:
    """Compute dispersion and consistency statistics for a sample.

    Coefficient of Variation (CV = stddev / mean) is strictly restricted:
    - Only computed if allow_cv is True (for naturally positive, non-interval metrics).
    - Returns None if mean <= 0 or stddev is None.
    - Metrics that can cross zero (e.g. position change, deltas) must leave allow_cv=False.

    Args:
        values: Sequence of numeric values, potentially containing None.
        allow_cv: Whether the metric is strictly ratio-scale and positive.

    Returns:
        ConsistencyStats instance.
    """
    stats = compute_descriptive_stats(values)

    if stats.sample_size < 1:
        rng = None
    else:
        rng = stats.maximum - stats.minimum if stats.maximum is not None and stats.minimum is not None else None

    iqr_val = stats.iqr

    # Coefficient of Variation
    cv: Optional[float] = None
    if (
        allow_cv
        and stats.mean is not None
        and stats.mean > 0
        and stats.stddev is not None
    ):
        cv = stats.stddev / stats.mean

    return ConsistencyStats(
        stats=stats,
        range=rng,
        iqr=iqr_val,
        coefficient_of_variation=cv,
    )

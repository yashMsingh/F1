"""Statistical analysis of qualifying session deltas between teammates.

Convention:
- Delta = driver_a_best_time - driver_b_best_time (in milliseconds).
- Negative delta means driver_a was faster.
- Positive delta means driver_b was faster.
- Ordering: driver_a < driver_b alphabetically by driver_id.
- No subjective language ("better", "dominated") is used.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional, Sequence

from app.analytics.types import TeammateQualifyingComparison
from app.statistics.descriptive import compute_descriptive_stats
from app.statistics.types import QualifyingDeltaStats, QualityMetadata


def compute_qualifying_delta_stats(
    comparisons: Sequence[TeammateQualifyingComparison],
) -> dict[str, QualifyingDeltaStats]:
    """Compute qualifying delta statistics grouped by constructor.

    Args:
        comparisons: Sequence of TeammateQualifyingComparison records across races.

    Returns:
        Dict mapping constructor_id to QualifyingDeltaStats.
    """
    by_constructor: dict[str, list[TeammateQualifyingComparison]] = defaultdict(list)
    for comp in comparisons:
        by_constructor[comp.constructor_id].append(comp)

    results: dict[str, QualifyingDeltaStats] = {}
    for constructor_id, comps in by_constructor.items():
        total = len(comps)
        valid_deltas = [c.delta_millis for c in comps if c.delta_millis is not None]
        valid_count = len(valid_deltas)
        excluded_count = total - valid_count

        # Representatives for driver names from the first comparison
        driver_a = comps[0].driver_a_id
        driver_b = comps[0].driver_b_id

        stats = compute_descriptive_stats(valid_deltas)
        quality = QualityMetadata(
            total_observations=total,
            valid_observations=valid_count,
            excluded_observations=excluded_count,
        )

        results[constructor_id] = QualifyingDeltaStats(
            constructor_id=constructor_id,
            driver_a_id=driver_a,
            driver_b_id=driver_b,
            stats=stats,
            quality=quality,
        )

    return results


def compute_constructor_qualifying_delta(
    comparisons: Sequence[TeammateQualifyingComparison],
    constructor_id: str,
) -> Optional[QualifyingDeltaStats]:
    """Compute qualifying delta statistics for a single specified constructor.

    Args:
        comparisons: Multi-race comparisons.
        constructor_id: Jolpica constructor slug.

    Returns:
        QualifyingDeltaStats or None if no comparisons found for constructor.
    """
    filtered = [c for c in comparisons if c.constructor_id == constructor_id]
    if not filtered:
        return None
    res = compute_qualifying_delta_stats(filtered)
    return res.get(constructor_id)

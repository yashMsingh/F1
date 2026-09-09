"""Teammate head-to-head multi-race statistical evidence.

Rules:
- Driver ordering is strictly alphabetical by driver_id (driver_a < driver_b).
- All deltas are driver_a - driver_b.
- No composite driver scores, ratings, weights, or winner declarations.
- Separate descriptive statistics across four independent dimensions:
  qualifying delta (ms), grid delta, finish delta, points delta.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional, Sequence

from app.analytics.types import TeammateComparison
from app.statistics.descriptive import compute_descriptive_stats
from app.statistics.types import QualityMetadata, TeammateHeadToHeadStats


def compute_teammate_head_to_head_stats(
    comparisons: Sequence[TeammateComparison],
) -> dict[str, TeammateHeadToHeadStats]:
    """Compute multi-race teammate head-to-head statistics grouped by constructor.

    Args:
        comparisons: Sequence of TeammateComparison records across races.

    Returns:
        Dict mapping constructor_id to TeammateHeadToHeadStats.
    """
    by_constructor: dict[str, list[TeammateComparison]] = defaultdict(list)
    for comp in comparisons:
        by_constructor[comp.constructor_id].append(comp)

    results: dict[str, TeammateHeadToHeadStats] = {}
    for constructor_id, comps in by_constructor.items():
        total = len(comps)

        driver_a = comps[0].driver_a_id
        driver_b = comps[0].driver_b_id

        # Extract delta dimensions
        quali_deltas = [c.qualifying_delta_millis for c in comps if c.qualifying_delta_millis is not None]
        grid_deltas = [c.grid_delta for c in comps if c.grid_delta is not None]
        finish_deltas = [c.finish_delta for c in comps if c.finish_delta is not None]
        points_deltas = [float(c.points_delta) for c in comps if c.points_delta is not None]

        # Valid races are those where at least one delta dimension could be evaluated
        valid_count = sum(
            1
            for c in comps
            if (
                c.qualifying_delta_millis is not None
                or c.grid_delta is not None
                or c.finish_delta is not None
                or c.points_delta is not None
            )
        )
        excluded_count = total - valid_count

        quality = QualityMetadata(
            total_observations=total,
            valid_observations=valid_count,
            excluded_observations=excluded_count,
        )

        results[constructor_id] = TeammateHeadToHeadStats(
            constructor_id=constructor_id,
            driver_a_id=driver_a,
            driver_b_id=driver_b,
            qualifying_delta=compute_descriptive_stats(quali_deltas),
            grid_delta=compute_descriptive_stats(grid_deltas),
            finish_delta=compute_descriptive_stats(finish_deltas),
            points_delta=compute_descriptive_stats(points_deltas),
            quality=quality,
        )

    return results


def compute_constructor_head_to_head(
    comparisons: Sequence[TeammateComparison],
    constructor_id: str,
) -> Optional[TeammateHeadToHeadStats]:
    """Compute teammate head-to-head statistics for a single constructor.

    Args:
        comparisons: Multi-race comparisons.
        constructor_id: Jolpica constructor slug.

    Returns:
        TeammateHeadToHeadStats or None if no comparisons found for constructor.
    """
    filtered = [c for c in comparisons if c.constructor_id == constructor_id]
    if not filtered:
        return None
    res = compute_teammate_head_to_head_stats(filtered)
    return res.get(constructor_id)

"""Statistical analysis of starting grid to finishing position changes.

Rules:
- Missing grid (pit-lane start) or missing finish (DNF, DNS, DSQ) are excluded.
- Excluded observations are tracked in QualityMetadata and never coerced to zero.
- Denominator for positive/negative/zero rates is strictly valid_observations.
"""

from __future__ import annotations

from typing import Optional, Sequence, Union

from app.analytics.types import GridVsFinish
from app.statistics.descriptive import compute_descriptive_stats
from app.statistics.types import (
    PositionChangeDistribution,
    PositionChangeStats,
    QualityMetadata,
)


def compute_position_change_distribution(
    valid_changes: Sequence[int],
) -> PositionChangeDistribution:
    """Compute categorical distribution for a sequence of valid integer position changes.

    Args:
        valid_changes: Sequence of valid integer position changes (no None values).

    Returns:
        PositionChangeDistribution instance.
    """
    n = len(valid_changes)
    pos_count = sum(1 for x in valid_changes if x > 0)
    neg_count = sum(1 for x in valid_changes if x < 0)
    zero_count = sum(1 for x in valid_changes if x == 0)

    if n > 0:
        pos_rate = pos_count / n
        neg_rate = neg_count / n
        zero_rate = zero_count / n
    else:
        pos_rate = None
        neg_rate = None
        zero_rate = None

    return PositionChangeDistribution(
        sample_size=n,
        positive_count=pos_count,
        negative_count=neg_count,
        zero_count=zero_count,
        positive_rate=pos_rate,
        negative_rate=neg_rate,
        zero_rate=zero_rate,
    )


def compute_position_change_stats(
    items: Sequence[Union[GridVsFinish, Optional[int]]],
) -> PositionChangeStats:
    """Compute descriptive statistics and distribution for position changes.

    Accepts either a sequence of GridVsFinish records or a sequence of nullable integers.
    DNFs, pit-lane starts, or None values are tracked in QualityMetadata.excluded_observations
    and never treated as zero change.

    Args:
        items: Sequence of GridVsFinish records or nullable position change integers.

    Returns:
        PositionChangeStats instance.
    """
    total = len(items)

    valid_changes: list[int] = []
    for item in items:
        if isinstance(item, GridVsFinish):
            if item.position_change is not None:
                valid_changes.append(item.position_change)
        elif item is not None:
            valid_changes.append(int(item))

    valid_count = len(valid_changes)
    excluded_count = total - valid_count

    quality = QualityMetadata(
        total_observations=total,
        valid_observations=valid_count,
        excluded_observations=excluded_count,
    )

    stats = compute_descriptive_stats(valid_changes)
    dist = compute_position_change_distribution(valid_changes)

    return PositionChangeStats(
        stats=stats,
        distribution=dist,
        quality=quality,
    )


def compute_driver_position_change_stats(
    records: Sequence[GridVsFinish],
    driver_id: str,
) -> PositionChangeStats:
    """Filter records for a specific driver and compute position change statistics.

    Args:
        records: Multi-race sequence of GridVsFinish records.
        driver_id: Jolpica driver slug.

    Returns:
        PositionChangeStats for the specified driver.
    """
    driver_records = [r for r in records if r.driver_id == driver_id]
    return compute_position_change_stats(driver_records)

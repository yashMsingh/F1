"""Statistical analysis of pit stop durations and variability.

Rules:
- NULL durations are never treated as zero-second pit stops.
- Excluded stops are tracked in QualityMetadata.
- Duration calculations operate in integer milliseconds.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, Union

from app.db.models.pit_stop import PitStop
from app.statistics.descriptive import compute_descriptive_stats
from app.statistics.types import PitStopStats, QualityMetadata


def compute_pit_stop_stats(
    stops: Sequence[Union[PitStop, Any, Optional[int]]],
) -> PitStopStats:
    """Compute descriptive statistics and variability for pit stop durations.

    Args:
        stops: Sequence of PitStop model objects, duck-typed objects with
            duration_millis attribute, or nullable integer milliseconds.

    Returns:
        PitStopStats instance.
    """
    total = len(stops)
    valid_millis: list[int] = []

    for item in stops:
        if isinstance(item, int):
            valid_millis.append(item)
        elif hasattr(item, "duration_millis"):
            if item.duration_millis is not None:
                valid_millis.append(int(item.duration_millis))

    valid_count = len(valid_millis)
    excluded_count = total - valid_count

    quality = QualityMetadata(
        total_observations=total,
        valid_observations=valid_count,
        excluded_observations=excluded_count,
    )

    stats = compute_descriptive_stats(valid_millis)
    fastest = min(valid_millis) if valid_millis else None

    return PitStopStats(
        stats=stats,
        quality=quality,
        fastest_duration_millis=fastest,
    )

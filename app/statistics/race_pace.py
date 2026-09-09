"""Statistical analysis of lap times and race pace.

All lap time arithmetic operates on integer milliseconds.
Fastest recorded lap is distinguished from official fastest lap.
Laps with unrecorded / NULL time_millis are excluded from calculations and
tracked in QualityMetadata.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, Union

from app.db.models.lap_time import LapTime
from app.statistics.descriptive import compute_descriptive_stats
from app.statistics.types import LapTimeStats, QualityMetadata


def compute_lap_time_stats(
    laps: Sequence[Union[LapTime, Any, Optional[int]]],
) -> LapTimeStats:
    """Compute descriptive statistics on lap times in milliseconds.

    Args:
        laps: Sequence of LapTime model objects, duck-typed objects with
            time_millis attribute, or nullable integer milliseconds.

    Returns:
        LapTimeStats instance.
    """
    total = len(laps)
    valid_millis: list[int] = []

    for item in laps:
        if isinstance(item, int):
            valid_millis.append(item)
        elif hasattr(item, "time_millis"):
            if item.time_millis is not None:
                valid_millis.append(int(item.time_millis))

    valid_count = len(valid_millis)
    excluded_count = total - valid_count

    quality = QualityMetadata(
        total_observations=total,
        valid_observations=valid_count,
        excluded_observations=excluded_count,
    )

    stats = compute_descriptive_stats(valid_millis)
    fastest = min(valid_millis) if valid_millis else None

    return LapTimeStats(
        stats=stats,
        quality=quality,
        fastest_recorded_millis=fastest,
    )

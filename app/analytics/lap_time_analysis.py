"""Lap time analysis queries — per-driver aggregation.

IMPORTANT DISTINCTION:
- This module reports the fastest *recorded* lap from the lap_times table.
- The *official* fastest lap is stored in race_results.fastest_lap_rank /
  fastest_lap_time_millis. These may differ (e.g. deleted lap times).

Denominator rules:
- lap_count = total rows in lap_times for the driver (includes NULL time_millis).
- fastest_lap_millis = MIN(time_millis) WHERE time_millis IS NOT NULL.
- avg_lap_millis = integer AVG of non-NULL time_millis values.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.driver import Driver
from app.db.models.lap_time import LapTime
from app.db.models.race import Race

from app.analytics.types import LapTimeSummary

logger = logging.getLogger(__name__)


def get_driver_lap_times(
    session: Session, season_year: int, round_num: int
) -> list[LapTimeSummary]:
    """Return per-driver lap time aggregation for a race.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        List of LapTimeSummary sorted by fastest_lap_millis (fastest first,
        NULL-fastest last), empty if race not found or no lap data.
    """
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()

    if race is None:
        return []

    rows = session.execute(
        select(
            LapTime.driver_id,
            func.count(LapTime.id).label("lap_count"),
            func.min(LapTime.time_millis).label("fastest"),
            func.avg(LapTime.time_millis).label("avg_time"),
        )
        .where(LapTime.race_id == race.id)
        .group_by(LapTime.driver_id)
    ).all()

    results: list[LapTimeSummary] = []
    for row in rows:
        drv = session.get(Driver, row.driver_id)
        if drv is None:
            logger.warning("Driver id=%d not found for lap time aggregation", row.driver_id)
            continue

        fastest = int(row.fastest) if row.fastest is not None else None
        avg_time = int(row.avg_time) if row.avg_time is not None else None

        results.append(
            LapTimeSummary(
                driver_id=drv.driver_id,
                given_name=drv.given_name,
                family_name=drv.family_name,
                lap_count=row.lap_count,
                fastest_lap_millis=fastest,
                avg_lap_millis=avg_time,
            )
        )

    # Sort by fastest lap (fastest first, NULLs last)
    results.sort(key=lambda x: (x.fastest_lap_millis is None, x.fastest_lap_millis or 0))
    return results

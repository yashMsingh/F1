"""Pit stop analysis queries — per-driver and per-constructor aggregation.

Denominator rules:
- stop_count = MAX(stop_number) from all pit stop rows for the driver.
- avg_duration_millis = SUM(duration_millis) / COUNT(duration_millis)
  where duration_millis IS NOT NULL.
- fastest_stop_millis = MIN(duration_millis) where duration_millis IS NOT NULL.

Join strategy: PitStop → Driver for driver info. Constructor resolved via a
separate subquery on RaceResult to avoid row multiplication.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.pit_stop import PitStop
from app.db.models.race import Race
from app.db.models.race_result import RaceResult

from app.analytics.types import ConstructorPitStopSummary, PitStopSummary

logger = logging.getLogger(__name__)


def get_driver_pit_stops(
    session: Session, season_year: int, round_num: int
) -> list[PitStopSummary]:
    """Return per-driver pit stop aggregation for a race.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        List of PitStopSummary sorted by stop_count descending then driver_id,
        empty if race not found or no pit stop data.
    """
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()

    if race is None:
        return []

    # Aggregate pit stops per driver
    rows = session.execute(
        select(
            PitStop.driver_id,
            func.max(PitStop.stop_number).label("stop_count"),
            func.sum(PitStop.duration_millis).label("total_duration"),
            func.avg(PitStop.duration_millis).label("avg_duration"),
            func.min(PitStop.duration_millis).label("fastest_stop"),
        )
        .where(PitStop.race_id == race.id)
        .group_by(PitStop.driver_id)
    ).all()

    results: list[PitStopSummary] = []
    for row in rows:
        drv = session.get(Driver, row.driver_id)
        if drv is None:
            logger.warning("Driver id=%d not found for pit stop aggregation", row.driver_id)
            continue

        total_dur = int(row.total_duration) if row.total_duration is not None else None
        avg_dur = int(row.avg_duration) if row.avg_duration is not None else None
        fastest = int(row.fastest_stop) if row.fastest_stop is not None else None

        results.append(
            PitStopSummary(
                driver_id=drv.driver_id,
                given_name=drv.given_name,
                family_name=drv.family_name,
                stop_count=row.stop_count,
                total_duration_millis=total_dur,
                avg_duration_millis=avg_dur,
                fastest_stop_millis=fastest,
            )
        )

    results.sort(key=lambda x: (-x.stop_count, x.driver_id))
    return results


def get_constructor_pit_stops(
    session: Session, season_year: int, round_num: int
) -> list[ConstructorPitStopSummary]:
    """Return per-constructor pit stop aggregation for a race.

    Resolves constructor via RaceResult (subquery) to avoid join multiplication.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        List of ConstructorPitStopSummary sorted by constructor_id,
        empty if race not found or no pit stop data.
    """
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()

    if race is None:
        return []

    # Build a driver_id → constructor_id mapping from race_results
    rr_rows = session.execute(
        select(RaceResult.driver_id, RaceResult.constructor_id)
        .where(RaceResult.race_id == race.id)
    ).all()
    driver_to_constructor: dict[int, int] = {r.driver_id: r.constructor_id for r in rr_rows}

    # Get all pit stops for this race
    pit_stops = session.scalars(
        select(PitStop).where(PitStop.race_id == race.id)
    ).all()

    if not pit_stops:
        return []

    # Group by constructor
    by_constructor: dict[int, list[PitStop]] = defaultdict(list)
    for ps in pit_stops:
        con_id = driver_to_constructor.get(ps.driver_id)
        if con_id is not None:
            by_constructor[con_id].append(ps)
        else:
            logger.warning(
                "No constructor mapping for driver_id=%d in pit stop aggregation",
                ps.driver_id,
            )

    results: list[ConstructorPitStopSummary] = []
    for con_id, stops in by_constructor.items():
        con = session.get(Constructor, con_id)
        if con is None:
            continue

        # Count total stops as sum of max(stop_number) per driver
        driver_stops: dict[int, int] = {}
        for ps in stops:
            current_max = driver_stops.get(ps.driver_id, 0)
            driver_stops[ps.driver_id] = max(current_max, ps.stop_number)
        total_stops = sum(driver_stops.values())

        # Duration stats from non-NULL values
        durations = [ps.duration_millis for ps in stops if ps.duration_millis is not None]
        if durations:
            avg_dur = int(sum(durations) / len(durations))
            fastest = min(durations)
        else:
            avg_dur = None
            fastest = None

        results.append(
            ConstructorPitStopSummary(
                constructor_id=con.constructor_id,
                constructor_name=con.name,
                total_stops=total_stops,
                avg_duration_millis=avg_dur,
                fastest_stop_millis=fastest,
            )
        )

    results.sort(key=lambda x: x.constructor_id)
    return results

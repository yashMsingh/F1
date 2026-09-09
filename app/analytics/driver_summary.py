"""Driver race summary query — comprehensive single-driver view.

Uses separate scalar subquery for pit stop count to avoid row multiplication
from joining pit_stops with race_results.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.pit_stop import PitStop
from app.db.models.race import Race
from app.db.models.race_result import RaceResult

from app.analytics.types import DriverRaceSummary

logger = logging.getLogger(__name__)


def get_driver_race_summary(
    session: Session, season_year: int, round_num: int, driver_id: str
) -> Optional[DriverRaceSummary]:
    """Return a comprehensive single-driver race summary.

    pit_stop_count is computed via a separate scalar query on the pit_stops
    table to avoid row multiplication from a direct join.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.
        driver_id: Jolpica driver slug identifier.

    Returns:
        DriverRaceSummary or None if driver/race not found.
    """
    # Find the race
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()
    if race is None:
        return None

    # Find the driver
    drv = session.scalars(
        select(Driver).where(Driver.driver_id == driver_id)
    ).first()
    if drv is None:
        return None

    # Get race result for this driver (single row)
    row = session.execute(
        select(RaceResult, Constructor)
        .join(Constructor, RaceResult.constructor_id == Constructor.id)
        .where(RaceResult.race_id == race.id, RaceResult.driver_id == drv.id)
    ).first()

    if row is None:
        return None

    rr: RaceResult = row[0]
    con: Constructor = row[1]

    # Separate scalar subquery for pit stop count — avoids row multiplication
    pit_stop_count = session.scalar(
        select(func.count(PitStop.id))
        .where(PitStop.race_id == race.id, PitStop.driver_id == drv.id)
    ) or 0

    grid = rr.grid_position
    finish = rr.source_position
    if grid is not None and finish is not None:
        pos_change = grid - finish
    else:
        pos_change = None

    return DriverRaceSummary(
        driver_id=drv.driver_id,
        given_name=drv.given_name,
        family_name=drv.family_name,
        constructor_name=con.name,
        grid_position=grid,
        finish_position=finish,
        position_change=pos_change,
        points=rr.points,
        laps_completed=rr.laps_completed,
        status=rr.status,
        pit_stop_count=pit_stop_count,
        race_time_millis=rr.time_millis,
    )

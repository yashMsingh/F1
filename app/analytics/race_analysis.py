"""Race analysis queries — overview, grid vs finish, full results.

All queries are parameterized by (season_year, round).
Join strategy: Race → RaceResult → Driver, Constructor — single join path, no multiplicity risk.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models.circuit import Circuit
from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.race import Race
from app.db.models.race_result import RaceResult

from app.analytics.types import GridVsFinish, RaceOverview, RaceResultRow

logger = logging.getLogger(__name__)


def get_race_overview(
    session: Session, season_year: int, round_num: int
) -> Optional[RaceOverview]:
    """Return a high-level summary of a single Grand Prix.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        RaceOverview or None if the race is not found.
    """
    race = session.execute(
        select(Race, Circuit.circuit_name)
        .join(Circuit, Race.circuit_id == Circuit.id)
        .where(Race.season_year == season_year, Race.round == round_num)
    ).first()

    if race is None:
        return None

    race_obj: Race = race[0]
    circuit_name: str = race[1]

    # Count results
    results = session.scalars(
        select(RaceResult).where(RaceResult.race_id == race_obj.id)
    ).all()

    total_result_count = len(results)
    classified_count = sum(1 for r in results if r.source_position is not None)

    # Find winner (source_position == 1)
    winner_result = next((r for r in results if r.source_position == 1), None)

    winner_given_name: Optional[str] = None
    winner_family_name: Optional[str] = None
    winner_constructor: Optional[str] = None
    winner_time_millis: Optional[int] = None
    winner_time_text: Optional[str] = None

    if winner_result is not None:
        winner_driver = session.get(Driver, winner_result.driver_id)
        winner_constr = session.get(Constructor, winner_result.constructor_id)
        if winner_driver is not None:
            winner_given_name = winner_driver.given_name
            winner_family_name = winner_driver.family_name
        if winner_constr is not None:
            winner_constructor = winner_constr.name
        winner_time_millis = winner_result.time_millis
        winner_time_text = winner_result.time_text

    return RaceOverview(
        season_year=season_year,
        round=round_num,
        race_name=race_obj.race_name,
        circuit_name=circuit_name,
        race_date=race_obj.race_date,
        winner_given_name=winner_given_name,
        winner_family_name=winner_family_name,
        winner_constructor=winner_constructor,
        winner_time_millis=winner_time_millis,
        winner_time_text=winner_time_text,
        classified_count=classified_count,
        total_result_count=total_result_count,
    )


def get_grid_vs_finish(
    session: Session, season_year: int, round_num: int
) -> list[GridVsFinish]:
    """Return grid-to-finish comparisons for all drivers in a race.

    position_change = grid_position − finish_position (positive = positions gained).
    NULL if either grid_position or finish_position (source_position) is None.

    Results are ordered by source_position (classified first, NULLs last).

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        List of GridVsFinish, empty if race not found.
    """
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()

    if race is None:
        return []

    rows = session.execute(
        select(RaceResult, Driver, Constructor)
        .join(Driver, RaceResult.driver_id == Driver.id)
        .join(Constructor, RaceResult.constructor_id == Constructor.id)
        .where(RaceResult.race_id == race.id)
    ).all()

    results: list[GridVsFinish] = []
    for rr, drv, con in rows:
        grid = rr.grid_position
        finish = rr.source_position
        if grid is not None and finish is not None:
            pos_change = grid - finish
        else:
            pos_change = None

        results.append(
            GridVsFinish(
                driver_id=drv.driver_id,
                given_name=drv.given_name,
                family_name=drv.family_name,
                constructor_name=con.name,
                grid_position=grid,
                finish_position=finish,
                position_change=pos_change,
                status=rr.status,
                points=rr.points,
            )
        )

    # Sort: classified finishers first (by finish position), then unclassified
    results.sort(key=lambda x: (x.finish_position is None, x.finish_position or 0))
    return results


def get_race_results(
    session: Session,
    season_year: int,
    round_num: int,
    *,
    driver_id: Optional[str] = None,
    constructor_id: Optional[str] = None,
) -> list[RaceResultRow]:
    """Return full race results with optional driver/constructor filtering.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.
        driver_id: Optional Jolpica driver slug to filter by.
        constructor_id: Optional Jolpica constructor slug to filter by.

    Returns:
        List of RaceResultRow, empty if race not found or no matching results.
    """
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()

    if race is None:
        return []

    stmt = (
        select(RaceResult, Driver, Constructor)
        .join(Driver, RaceResult.driver_id == Driver.id)
        .join(Constructor, RaceResult.constructor_id == Constructor.id)
        .where(RaceResult.race_id == race.id)
    )

    if driver_id is not None:
        stmt = stmt.where(Driver.driver_id == driver_id)
    if constructor_id is not None:
        stmt = stmt.where(Constructor.constructor_id == constructor_id)

    rows = session.execute(stmt).all()

    results: list[RaceResultRow] = []
    for rr, drv, con in rows:
        results.append(
            RaceResultRow(
                driver_id=drv.driver_id,
                given_name=drv.given_name,
                family_name=drv.family_name,
                constructor_id=con.constructor_id,
                constructor_name=con.name,
                car_number=rr.car_number,
                grid_position=rr.grid_position,
                source_position=rr.source_position,
                position_text=rr.position_text,
                points=rr.points,
                laps_completed=rr.laps_completed,
                status=rr.status,
                time_millis=rr.time_millis,
                time_text=rr.time_text,
                fastest_lap_rank=rr.fastest_lap_rank,
                fastest_lap_number=rr.fastest_lap_number,
                fastest_lap_time=rr.fastest_lap_time,
                fastest_lap_time_millis=rr.fastest_lap_time_millis,
            )
        )

    # Sort by source_position (classified first, NULLs last)
    results.sort(key=lambda x: (x.source_position is None, x.source_position or 0))
    return results

"""Constructor / teammate comparison analysis.

Teammate identification: two drivers sharing the same constructor_id in
race_results for the given race.

Driver ordering: driver_a < driver_b by driver_id alphabetical order
(deterministic, no subjective ordering).

All deltas are driver_a_value − driver_b_value.
No "better/worse" labels — this layer provides evidence only.
Interpretation belongs to the future insight engine.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.qualifying_result import QualifyingResult
from app.db.models.race import Race
from app.db.models.race_result import RaceResult

from app.analytics.qualifying_analysis import _best_time_millis
from app.analytics.types import TeammateComparison

logger = logging.getLogger(__name__)


def get_teammate_comparison(
    session: Session,
    season_year: int,
    round_num: int,
    constructor_id: str,
) -> Optional[TeammateComparison]:
    """Return a head-to-head comparison between two teammates in a single race.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.
        constructor_id: Jolpica constructor slug.

    Returns:
        TeammateComparison or None if fewer than 2 drivers for this constructor.
    """
    # Find race and constructor
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()
    if race is None:
        return None

    con = session.scalars(
        select(Constructor).where(Constructor.constructor_id == constructor_id)
    ).first()
    if con is None:
        return None

    # Find both drivers' race results for this constructor
    rr_rows = session.execute(
        select(RaceResult, Driver)
        .join(Driver, RaceResult.driver_id == Driver.id)
        .where(RaceResult.race_id == race.id, RaceResult.constructor_id == con.id)
    ).all()

    if len(rr_rows) < 2:
        return None

    # Sort alphabetically by driver_id — deterministic ordering
    rr_rows.sort(key=lambda x: x[1].driver_id)
    rr_a, drv_a = rr_rows[0]
    rr_b, drv_b = rr_rows[1]

    # Qualifying delta (from qualifying_results)
    qr_a = session.scalars(
        select(QualifyingResult).where(
            QualifyingResult.race_id == race.id,
            QualifyingResult.driver_id == drv_a.id,
        )
    ).first()
    qr_b = session.scalars(
        select(QualifyingResult).where(
            QualifyingResult.race_id == race.id,
            QualifyingResult.driver_id == drv_b.id,
        )
    ).first()

    best_a = _best_time_millis(qr_a) if qr_a else None
    best_b = _best_time_millis(qr_b) if qr_b else None
    if best_a is not None and best_b is not None:
        quali_delta = best_a - best_b
    else:
        quali_delta = None

    # Grid delta
    if rr_a.grid_position is not None and rr_b.grid_position is not None:
        grid_delta = rr_a.grid_position - rr_b.grid_position
    else:
        grid_delta = None

    # Finish delta
    if rr_a.source_position is not None and rr_b.source_position is not None:
        finish_delta = rr_a.source_position - rr_b.source_position
    else:
        finish_delta = None

    # Points delta (always available — points default to 0)
    points_delta = rr_a.points - rr_b.points

    return TeammateComparison(
        constructor_id=con.constructor_id,
        constructor_name=con.name,
        driver_a_id=drv_a.driver_id,
        driver_a_name=f"{drv_a.given_name} {drv_a.family_name}",
        driver_b_id=drv_b.driver_id,
        driver_b_name=f"{drv_b.given_name} {drv_b.family_name}",
        qualifying_delta_millis=quali_delta,
        grid_delta=grid_delta,
        finish_delta=finish_delta,
        points_delta=points_delta,
    )

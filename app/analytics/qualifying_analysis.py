"""Qualifying analysis queries — session order and teammate comparisons.

Best-time logic: Use the deepest qualifying session reached by each driver
(Q3 if available, else Q2, else Q1). Teammate delta only computed when both
drivers have a valid best time.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.qualifying_result import QualifyingResult
from app.db.models.race import Race

from app.analytics.types import QualifyingOrder, TeammateQualifyingComparison

logger = logging.getLogger(__name__)


def _best_time_millis(qr: QualifyingResult) -> Optional[int]:
    """Return the best (deepest-session) qualifying time in milliseconds.

    Priority: Q3 > Q2 > Q1. Returns None if no valid time in any session.
    """
    if qr.q3_time_millis is not None:
        return qr.q3_time_millis
    if qr.q2_time_millis is not None:
        return qr.q2_time_millis
    if qr.q1_time_millis is not None:
        return qr.q1_time_millis
    return None


def get_qualifying_order(
    session: Session, season_year: int, round_num: int
) -> list[QualifyingOrder]:
    """Return qualifying classifications ordered by position.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        List of QualifyingOrder sorted by position, empty if race not found.
    """
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()

    if race is None:
        return []

    rows = session.execute(
        select(QualifyingResult, Driver, Constructor)
        .join(Driver, QualifyingResult.driver_id == Driver.id)
        .join(Constructor, QualifyingResult.constructor_id == Constructor.id)
        .where(QualifyingResult.race_id == race.id)
        .order_by(QualifyingResult.position)
    ).all()

    return [
        QualifyingOrder(
            driver_id=drv.driver_id,
            given_name=drv.given_name,
            family_name=drv.family_name,
            constructor_name=con.name,
            position=qr.position,
            q1_time_millis=qr.q1_time_millis,
            q2_time_millis=qr.q2_time_millis,
            q3_time_millis=qr.q3_time_millis,
        )
        for qr, drv, con in rows
    ]


def get_teammate_qualifying_comparison(
    session: Session, season_year: int, round_num: int
) -> list[TeammateQualifyingComparison]:
    """Return per-constructor teammate qualifying comparisons.

    For each constructor with two drivers in qualifying, computes the delta
    between their best qualifying times. Driver ordering is alphabetical by
    driver_id (deterministic, no subjective ordering).

    delta_millis = best_time_a − best_time_b.
    Negative delta means driver A was faster.
    None if either driver has no valid qualifying time.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        List of TeammateQualifyingComparison, one per constructor with ≥2 drivers.
    """
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()

    if race is None:
        return []

    rows = session.execute(
        select(QualifyingResult, Driver, Constructor)
        .join(Driver, QualifyingResult.driver_id == Driver.id)
        .join(Constructor, QualifyingResult.constructor_id == Constructor.id)
        .where(QualifyingResult.race_id == race.id)
    ).all()

    # Group by constructor
    by_constructor: dict[int, list[tuple[QualifyingResult, Driver, Constructor]]] = defaultdict(list)
    for qr, drv, con in rows:
        by_constructor[con.id].append((qr, drv, con))

    comparisons: list[TeammateQualifyingComparison] = []
    for con_id, entries in by_constructor.items():
        if len(entries) < 2:
            continue

        # Sort by driver_id alphabetically — deterministic ordering
        entries.sort(key=lambda x: x[1].driver_id)
        qr_a, drv_a, con_a = entries[0]
        qr_b, drv_b, _ = entries[1]

        best_a = _best_time_millis(qr_a)
        best_b = _best_time_millis(qr_b)

        if best_a is not None and best_b is not None:
            delta = best_a - best_b
        else:
            delta = None

        comparisons.append(
            TeammateQualifyingComparison(
                constructor_id=con_a.constructor_id,
                constructor_name=con_a.name,
                driver_a_id=drv_a.driver_id,
                driver_a_name=f"{drv_a.given_name} {drv_a.family_name}",
                driver_b_id=drv_b.driver_id,
                driver_b_name=f"{drv_b.given_name} {drv_b.family_name}",
                best_time_a_millis=best_a,
                best_time_b_millis=best_b,
                delta_millis=delta,
            )
        )

    # Sort output by constructor_id for deterministic ordering
    comparisons.sort(key=lambda x: x.constructor_id)
    return comparisons

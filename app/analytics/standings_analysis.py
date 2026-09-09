"""Standings analysis queries — driver and constructor championship standings.

These queries return data from the persisted standings tables.
They do NOT reconstruct standings from race results.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.constructor import Constructor
from app.db.models.constructor_standing import ConstructorStanding
from app.db.models.driver import Driver
from app.db.models.driver_standing import DriverStanding

from app.analytics.types import ConstructorStandingRow, DriverStandingRow

logger = logging.getLogger(__name__)


def get_driver_standings(
    session: Session, season_year: int, round_num: int
) -> list[DriverStandingRow]:
    """Return driver championship standings after a given round.

    Source: driver_standings table — NOT reconstructed from race results.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        List of DriverStandingRow sorted by position, empty if no data.
    """
    rows = session.execute(
        select(DriverStanding, Driver)
        .join(Driver, DriverStanding.driver_id == Driver.id)
        .where(
            DriverStanding.season_year == season_year,
            DriverStanding.round == round_num,
        )
        .order_by(DriverStanding.position)
    ).all()

    return [
        DriverStandingRow(
            driver_id=drv.driver_id,
            given_name=drv.given_name,
            family_name=drv.family_name,
            position=ds.position,
            points=ds.points,
            wins=ds.wins,
        )
        for ds, drv in rows
    ]


def get_constructor_standings(
    session: Session, season_year: int, round_num: int
) -> list[ConstructorStandingRow]:
    """Return constructor championship standings after a given round.

    Source: constructor_standings table — NOT reconstructed from race results.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        List of ConstructorStandingRow sorted by position, empty if no data.
    """
    rows = session.execute(
        select(ConstructorStanding, Constructor)
        .join(Constructor, ConstructorStanding.constructor_id == Constructor.id)
        .where(
            ConstructorStanding.season_year == season_year,
            ConstructorStanding.round == round_num,
        )
        .order_by(ConstructorStanding.position)
    ).all()

    return [
        ConstructorStandingRow(
            constructor_id=con.constructor_id,
            constructor_name=con.name,
            position=cs.position,
            points=cs.points,
            wins=cs.wins,
        )
        for cs, con in rows
    ]

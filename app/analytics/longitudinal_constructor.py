"""Longitudinal constructor analytics — trajectories, driver contributions, and aggregates.

All metrics are computed strictly from verified database records.
Sprint points are tracked distinctly from Grand Prix race points.
Multiple drivers driving for the same constructor (e.g. substitutions) are accounted for.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.types import (
    ConstructorDriverContribution,
    ConstructorSeasonAggregate,
    ConstructorTrajectoryItem,
)
from app.db.models.circuit import Circuit
from app.db.models.constructor import Constructor
from app.db.models.constructor_standing import ConstructorStanding
from app.db.models.driver import Driver
from app.db.models.race import Race
from app.db.models.race_result import RaceResult
from app.db.models.sprint_result import SprintResult

logger = logging.getLogger(__name__)


def get_constructor_trajectory(
    session: Session,
    season_year: int,
    constructor_id: str,
    up_to_round: Optional[int] = None,
) -> list[ConstructorTrajectoryItem]:
    """Return a constructor's progression across all races in a season.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        constructor_id: Jolpica constructor slug.
        up_to_round: Optional upper round cutoff (inclusive).

    Returns:
        List of ConstructorTrajectoryItem ordered by round ascending.
    """
    con = session.scalars(
        select(Constructor).where(Constructor.constructor_id == constructor_id)
    ).first()
    if con is None:
        return []

    # Query all race results for this constructor in this season
    query = (
        select(RaceResult, Race, Circuit)
        .join(Race, RaceResult.race_id == Race.id)
        .join(Circuit, Race.circuit_id == Circuit.id)
        .where(
            Race.season_year == season_year,
            RaceResult.constructor_id == con.id,
        )
    )
    if up_to_round is not None:
        query = query.where(Race.round <= up_to_round)

    query = query.order_by(Race.round.asc())
    rr_rows = session.execute(query).all()

    if not rr_rows:
        return []

    # Group by race
    # race_id -> dict with race, circuit, list of RaceResult
    races_dict: dict[int, dict] = {}
    for rr, race, circuit in rr_rows:
        if race.id not in races_dict:
            races_dict[race.id] = {
                "race": race,
                "circuit": circuit,
                "results": [],
            }
        races_dict[race.id]["results"].append(rr)

    race_ids = list(races_dict.keys())

    # Pre-fetch sprint points for this constructor grouped by race_id
    sprint_query = (
        select(SprintResult.race_id, func.coalesce(func.sum(SprintResult.points), Decimal("0.0")))
        .where(
            SprintResult.race_id.in_(race_ids),
            SprintResult.constructor_id == con.id,
        )
        .group_by(SprintResult.race_id)
    )
    sprint_points_map: dict[int, Decimal] = dict(session.execute(sprint_query).all())

    # Pre-fetch constructor standings at each round
    standings_query = select(ConstructorStanding.round, ConstructorStanding.position).where(
        ConstructorStanding.season_year == season_year,
        ConstructorStanding.constructor_id == con.id,
    )
    if up_to_round is not None:
        standings_query = standings_query.where(ConstructorStanding.round <= up_to_round)
    standing_pos_map: dict[int, int] = dict(session.execute(standings_query).all())

    # Sort races by round ascending
    sorted_races = sorted(races_dict.values(), key=lambda x: x["race"].round)

    trajectory: list[ConstructorTrajectoryItem] = []
    cum_race_pts = Decimal("0.0")
    cum_sprint_pts = Decimal("0.0")

    for race_data in sorted_races:
        race: Race = race_data["race"]
        circuit: Circuit = race_data["circuit"]
        results: list[RaceResult] = race_data["results"]

        race_pts = sum((r.points or Decimal("0.0")) for r in results)
        sprint_pts = sprint_points_map.get(race.id, Decimal("0.0"))
        round_total = race_pts + sprint_pts

        cum_race_pts += race_pts
        cum_sprint_pts += sprint_pts
        cum_total = cum_race_pts + cum_sprint_pts

        finishes = [r.source_position for r in results if r.source_position is not None]
        best_finish = min(finishes) if finishes else None
        podiums = sum(1 for pos in finishes if pos in (1, 2, 3))
        cars_classified = len(finishes)
        cars_entered = len(results)

        standing_pos = standing_pos_map.get(race.round)

        trajectory.append(
            ConstructorTrajectoryItem(
                season_year=season_year,
                round=race.round,
                race_name=race.race_name,
                circuit_name=circuit.circuit_name,
                race_date=race.race_date,
                constructor_id=con.constructor_id,
                constructor_name=con.name,
                race_points=race_pts,
                sprint_points=sprint_pts,
                total_round_points=round_total,
                cumulative_race_points=cum_race_pts,
                cumulative_sprint_points=cum_sprint_pts,
                cumulative_total_points=cum_total,
                best_finish=best_finish,
                podiums=podiums,
                cars_classified=cars_classified,
                cars_entered=cars_entered,
                championship_standing_position=standing_pos,
            )
        )

    return trajectory


def get_constructor_season_aggregate(
    session: Session,
    season_year: int,
    constructor_id: str,
    up_to_round: Optional[int] = None,
) -> Optional[ConstructorSeasonAggregate]:
    """Return aggregated season metrics and driver contribution breakdown for a constructor.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        constructor_id: Jolpica constructor slug.
        up_to_round: Optional upper round cutoff (inclusive).

    Returns:
        ConstructorSeasonAggregate or None if constructor not found or has no entries.
    """
    con = session.scalars(
        select(Constructor).where(Constructor.constructor_id == constructor_id)
    ).first()
    if con is None:
        return None

    trajectory = get_constructor_trajectory(
        session=session,
        season_year=season_year,
        constructor_id=constructor_id,
        up_to_round=up_to_round,
    )
    if not trajectory:
        return None

    actual_max_round = max(item.round for item in trajectory)
    target_cutoff = up_to_round if up_to_round is not None else actual_max_round

    races_entered = len(trajectory)
    total_car_starts = sum(item.cars_entered for item in trajectory)
    total_car_finishes = sum(item.cars_classified for item in trajectory)
    dnf_count = total_car_starts - total_car_finishes

    wins = sum(1 for item in trajectory if item.best_finish == 1)
    podiums = sum(item.podiums for item in trajectory)

    total_race_points = sum(item.race_points for item in trajectory)
    total_sprint_points = sum(item.sprint_points for item in trajectory)
    total_points = total_race_points + total_sprint_points

    # Compute Driver Contributions
    driver_rows = session.execute(
        select(Driver, RaceResult)
        .join(RaceResult, Driver.id == RaceResult.driver_id)
        .join(Race, RaceResult.race_id == Race.id)
        .where(
            Race.season_year == season_year,
            RaceResult.constructor_id == con.id,
            Race.round <= target_cutoff,
        )
    ).all()

    # Pre-fetch sprint results by driver for this constructor
    sprint_driver_rows = session.execute(
        select(SprintResult.driver_id, func.coalesce(func.sum(SprintResult.points), Decimal("0.0")))
        .join(Race, SprintResult.race_id == Race.id)
        .where(
            Race.season_year == season_year,
            SprintResult.constructor_id == con.id,
            Race.round <= target_cutoff,
        )
        .group_by(SprintResult.driver_id)
    ).all()
    driver_sprint_pts: dict[int, Decimal] = dict(sprint_driver_rows)

    driver_data: dict[int, dict] = {}
    for drv, rr in driver_rows:
        if drv.id not in driver_data:
            driver_data[drv.id] = {
                "driver": drv,
                "race_points": Decimal("0.0"),
                "finishes": [],
                "entries": 0,
            }
        driver_data[drv.id]["entries"] += 1
        driver_data[drv.id]["race_points"] += (rr.points or Decimal("0.0"))
        if rr.source_position is not None:
            driver_data[drv.id]["finishes"].append(rr.source_position)

    contributions: list[ConstructorDriverContribution] = []
    for d_id, data in driver_data.items():
        drv: Driver = data["driver"]
        r_pts = data["race_points"]
        s_pts = driver_sprint_pts.get(d_id, Decimal("0.0"))
        d_total = r_pts + s_pts

        pct = (
            round(float(d_total / total_points * 100), 2)
            if total_points > 0
            else None
        )
        best_fin = min(data["finishes"]) if data["finishes"] else None

        contributions.append(
            ConstructorDriverContribution(
                driver_id=drv.driver_id,
                driver_name=f"{drv.given_name} {drv.family_name}",
                race_points=r_pts,
                sprint_points=s_pts,
                total_points=d_total,
                points_share_pct=pct,
                races_entered=data["entries"],
                best_finish=best_fin,
            )
        )

    # Sort contributions by total_points DESC, then driver_name
    contributions.sort(key=lambda c: (-c.total_points, c.driver_name))

    # Championship standing at the latest available round up to target_cutoff
    standing_query = (
        select(ConstructorStanding.position)
        .where(
            ConstructorStanding.season_year == season_year,
            ConstructorStanding.constructor_id == con.id,
            ConstructorStanding.round <= target_cutoff,
        )
        .order_by(ConstructorStanding.round.desc())
    )
    standing_pos = session.scalars(standing_query).first()

    return ConstructorSeasonAggregate(
        season_year=season_year,
        up_to_round=target_cutoff,
        constructor_id=con.constructor_id,
        constructor_name=con.name,
        races_entered=races_entered,
        total_car_starts=total_car_starts,
        total_car_finishes=total_car_finishes,
        dnf_count=dnf_count,
        wins=wins,
        podiums=podiums,
        total_race_points=total_race_points,
        total_sprint_points=total_sprint_points,
        total_points=total_points,
        driver_contributions=contributions,
        championship_standing=standing_pos,
    )


def get_all_constructors_season_aggregates(
    session: Session,
    season_year: int,
    up_to_round: Optional[int] = None,
) -> list[ConstructorSeasonAggregate]:
    """Return season aggregates for all constructors active in the season up to the given round.

    Ordered by championship standing (ascending), then points (descending),
    then wins (descending), then constructor name.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        up_to_round: Optional upper round cutoff (inclusive).

    Returns:
        List of ConstructorSeasonAggregate objects.
    """
    query = (
        select(Constructor.constructor_id)
        .distinct()
        .join(RaceResult, Constructor.id == RaceResult.constructor_id)
        .join(Race, RaceResult.race_id == Race.id)
        .where(Race.season_year == season_year)
    )
    if up_to_round is not None:
        query = query.where(Race.round <= up_to_round)

    con_slugs = session.scalars(query).all()

    aggregates: list[ConstructorSeasonAggregate] = []
    for slug in con_slugs:
        agg = get_constructor_season_aggregate(
            session=session,
            season_year=season_year,
            constructor_id=slug,
            up_to_round=up_to_round,
        )
        if agg is not None:
            aggregates.append(agg)

    def sort_key(item: ConstructorSeasonAggregate):
        standing = item.championship_standing if item.championship_standing is not None else 999
        return (standing, -item.total_points, -item.wins, item.constructor_name)

    aggregates.sort(key=sort_key)
    return aggregates

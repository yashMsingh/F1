"""Longitudinal driver analytics — trajectories and season aggregates.

All metrics are computed strictly from verified database records.
Sprint points are tracked distinctly from Grand Prix race points.
DNFs are tracked explicitly, and averages specify exact denominators.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.types import DriverSeasonAggregate, DriverTrajectoryItem
from app.db.models.circuit import Circuit
from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.driver_standing import DriverStanding
from app.db.models.pit_stop import PitStop
from app.db.models.race import Race
from app.db.models.race_result import RaceResult
from app.db.models.sprint_result import SprintResult

logger = logging.getLogger(__name__)


def _is_classified_result(position_text: Optional[str], status: Optional[str]) -> bool:
    """Determine whether a race result represents an analytically classified finisher.

    Per F1 regulations and analytics-spec.md:
    - Classified finishers have a numeric position_text (e.g. '1', '2', '18').
    - DNFs have position_text 'R' or status indicating retirement.
    """
    if not position_text or not position_text.isdigit():
        return False
    stat_lower = (status or "").lower()
    if stat_lower in ("retired", "did not start", "disqualified", "withdrawn"):
        return False
    return True


def get_driver_trajectory(
    session: Session,
    season_year: int,
    driver_id: str,
    up_to_round: Optional[int] = None,
) -> list[DriverTrajectoryItem]:
    """Return a driver's progression across all races in a season.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        driver_id: Jolpica driver slug.
        up_to_round: Optional upper round cutoff (inclusive).

    Returns:
        List of DriverTrajectoryItem ordered by round ascending.
    """
    driver = session.scalars(
        select(Driver).where(Driver.driver_id == driver_id)
    ).first()
    if driver is None:
        return []

    # Query race results joined with Race, Circuit, Constructor
    query = (
        select(RaceResult, Race, Circuit, Constructor)
        .join(Race, RaceResult.race_id == Race.id)
        .join(Circuit, Race.circuit_id == Circuit.id)
        .join(Constructor, RaceResult.constructor_id == Constructor.id)
        .where(
            Race.season_year == season_year,
            RaceResult.driver_id == driver.id,
        )
    )
    if up_to_round is not None:
        query = query.where(Race.round <= up_to_round)

    query = query.order_by(Race.round.asc())
    rows = session.execute(query).all()

    if not rows:
        return []

    race_ids = [r[1].id for r in rows]

    # Pre-fetch sprint points in a single query (keyed by race_id)
    sprint_query = select(SprintResult.race_id, SprintResult.points).where(
        SprintResult.race_id.in_(race_ids),
        SprintResult.driver_id == driver.id,
    )
    sprint_points_map: dict[int, Decimal] = dict(session.execute(sprint_query).all())

    # Pre-fetch pit stop counts in a single query (keyed by race_id)
    pit_query = (
        select(PitStop.race_id, func.count(PitStop.id))
        .where(
            PitStop.race_id.in_(race_ids),
            PitStop.driver_id == driver.id,
        )
        .group_by(PitStop.race_id)
    )
    pit_count_map: dict[int, int] = dict(session.execute(pit_query).all())

    # Pre-fetch driver standings at each round in a single query (keyed by round)
    standings_query = select(DriverStanding.round, DriverStanding.position).where(
        DriverStanding.season_year == season_year,
        DriverStanding.driver_id == driver.id,
    )
    if up_to_round is not None:
        standings_query = standings_query.where(DriverStanding.round <= up_to_round)
    standing_pos_map: dict[int, int] = dict(session.execute(standings_query).all())

    trajectory: list[DriverTrajectoryItem] = []
    cum_race_pts = Decimal("0.0")
    cum_sprint_pts = Decimal("0.0")

    for rr, race, circuit, con in rows:
        race_pts = rr.points or Decimal("0.0")
        sprint_pts = sprint_points_map.get(race.id, Decimal("0.0"))
        round_total = race_pts + sprint_pts

        cum_race_pts += race_pts
        cum_sprint_pts += sprint_pts
        cum_total = cum_race_pts + cum_sprint_pts

        is_classified = _is_classified_result(rr.position_text, rr.status)
        finish_pos = rr.source_position if is_classified else None
        standing_pos = standing_pos_map.get(race.round)
        pit_count = pit_count_map.get(race.id, 0)

        trajectory.append(
            DriverTrajectoryItem(
                season_year=season_year,
                round=race.round,
                race_name=race.race_name,
                circuit_name=circuit.circuit_name,
                race_date=race.race_date,
                constructor_id=con.constructor_id,
                constructor_name=con.name,
                grid_position=rr.grid_position,
                finish_position=finish_pos,
                position_text=rr.position_text,
                status=rr.status,
                is_classified=is_classified,
                race_points=race_pts,
                sprint_points=sprint_pts,
                total_round_points=round_total,
                cumulative_race_points=cum_race_pts,
                cumulative_sprint_points=cum_sprint_pts,
                cumulative_total_points=cum_total,
                championship_standing_position=standing_pos,
                pit_stop_count=pit_count,
                fastest_lap_rank=rr.fastest_lap_rank,
            )
        )

    return trajectory


def get_driver_season_aggregate(
    session: Session,
    season_year: int,
    driver_id: str,
    up_to_round: Optional[int] = None,
) -> Optional[DriverSeasonAggregate]:
    """Return aggregated season metrics for a single driver.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        driver_id: Jolpica driver slug.
        up_to_round: Optional upper round cutoff (inclusive).

    Returns:
        DriverSeasonAggregate or None if driver not found or has no entries.
    """
    driver = session.scalars(
        select(Driver).where(Driver.driver_id == driver_id)
    ).first()
    if driver is None:
        return None

    trajectory = get_driver_trajectory(
        session=session,
        season_year=season_year,
        driver_id=driver_id,
        up_to_round=up_to_round,
    )
    if not trajectory:
        return None

    actual_max_round = max(item.round for item in trajectory)
    target_cutoff = up_to_round if up_to_round is not None else actual_max_round

    races_entered = len(trajectory)

    # Started races: did not DNS
    races_started = sum(
        1
        for item in trajectory
        if item.grid_position is not None
        or (item.status.lower() not in ("did not start", "dns") and not item.status.startswith("DNS"))
    )

    races_classified = sum(1 for item in trajectory if item.is_classified)
    dnf_count = sum(1 for item in trajectory if not item.is_classified)

    wins = sum(1 for item in trajectory if item.finish_position == 1)
    podiums = sum(
        1 for item in trajectory if item.finish_position is not None and item.finish_position in (1, 2, 3)
    )
    points_finishes = sum(1 for item in trajectory if item.race_points > 0)

    total_race_points = sum(item.race_points for item in trajectory)
    total_sprint_points = sum(item.sprint_points for item in trajectory)
    total_points = total_race_points + total_sprint_points

    # Grid calculations: exclude pit-lane starts (grid <= 0 or None)
    valid_grids = [
        item.grid_position
        for item in trajectory
        if item.grid_position is not None and item.grid_position > 0
    ]
    average_grid = round(sum(valid_grids) / len(valid_grids), 2) if valid_grids else None
    best_grid = min(valid_grids) if valid_grids else None

    # Finish calculations: strictly over classified finishes
    valid_finishes = [
        item.finish_position
        for item in trajectory
        if item.finish_position is not None
    ]
    average_finish = round(sum(valid_finishes) / len(valid_finishes), 2) if valid_finishes else None
    best_finish = min(valid_finishes) if valid_finishes else None

    # Laps completed from race_results
    total_laps_query = (
        select(func.coalesce(func.sum(RaceResult.laps_completed), 0))
        .join(Race, RaceResult.race_id == Race.id)
        .where(
            Race.season_year == season_year,
            RaceResult.driver_id == driver.id,
            Race.round <= target_cutoff,
        )
    )
    total_laps = int(session.scalar(total_laps_query) or 0)

    # Championship standing at the latest available round up to target_cutoff
    standing_query = (
        select(DriverStanding.position)
        .where(
            DriverStanding.season_year == season_year,
            DriverStanding.driver_id == driver.id,
            DriverStanding.round <= target_cutoff,
        )
        .order_by(DriverStanding.round.desc())
    )
    standing_pos = session.scalars(standing_query).first()

    latest_entry = trajectory[-1]

    return DriverSeasonAggregate(
        season_year=season_year,
        up_to_round=target_cutoff,
        driver_id=driver.driver_id,
        driver_code=driver.code,
        given_name=driver.given_name,
        family_name=driver.family_name,
        constructor_id=latest_entry.constructor_id,
        constructor_name=latest_entry.constructor_name,
        races_entered=races_entered,
        races_started=races_started,
        races_classified=races_classified,
        dnf_count=dnf_count,
        wins=wins,
        podiums=podiums,
        points_finishes=points_finishes,
        total_race_points=total_race_points,
        total_sprint_points=total_sprint_points,
        total_points=total_points,
        average_grid=average_grid,
        average_finish=average_finish,
        best_grid=best_grid,
        best_finish=best_finish,
        total_laps_completed=total_laps,
        championship_standing=standing_pos,
    )


def get_all_drivers_season_aggregates(
    session: Session,
    season_year: int,
    up_to_round: Optional[int] = None,
) -> list[DriverSeasonAggregate]:
    """Return season aggregates for all drivers active in the season up to the given round.

    Ordered by championship standing (ascending), then points (descending),
    then wins (descending), then best finish (ascending).

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        up_to_round: Optional upper round cutoff (inclusive).

    Returns:
        List of DriverSeasonAggregate objects.
    """
    # Find all driver IDs that have race results in the specified window
    query = (
        select(Driver.driver_id)
        .distinct()
        .join(RaceResult, Driver.id == RaceResult.driver_id)
        .join(Race, RaceResult.race_id == Race.id)
        .where(Race.season_year == season_year)
    )
    if up_to_round is not None:
        query = query.where(Race.round <= up_to_round)

    driver_slugs = session.scalars(query).all()

    aggregates: list[DriverSeasonAggregate] = []
    for slug in driver_slugs:
        agg = get_driver_season_aggregate(
            session=session,
            season_year=season_year,
            driver_id=slug,
            up_to_round=up_to_round,
        )
        if agg is not None:
            aggregates.append(agg)

    # Sort deterministically:
    # 1. Championship standing (if known, else 999)
    # 2. Total points DESC
    # 3. Wins DESC
    # 4. Best finish ASC (if known, else 999)
    def sort_key(item: DriverSeasonAggregate):
        standing = item.championship_standing if item.championship_standing is not None else 999
        best_fin = item.best_finish if item.best_finish is not None else 999
        return (standing, -item.total_points, -item.wins, best_fin, item.driver_id)

    aggregates.sort(key=sort_key)
    return aggregates

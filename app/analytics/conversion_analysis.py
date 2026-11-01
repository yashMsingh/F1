"""Qualifying-to-race conversion and race craft analytics (Phase 5B.2A).

Computes deterministic, evidence-grounded metrics:
1. Pole-to-Win Conversion Rate
2. Front-Row Podium Retention Rate
3. Segmented Grid-Tier Position Deltas (Front P1-P4, Midfield P5-P10, Lower P11-P20)
4. Top-10 Points Conversion Rate

Rules:
- Uses qualifying classification (QualifyingResult.position) for pole and front-row eligibility.
- Uses actual starting grid positions (RaceResult.grid_position) for grid tiers and top-10 conversion.
- DNS events are excluded from starts and conversions.
- Pit-lane starts (grid <= 0 or null) are tracked separately and excluded from grid-tier deltas.
- Unclassified finishes (DNFs, DSQs) are tracked separately and excluded from position delta calculations.
- Purely deterministic; zero LLM generation; zero DB mutations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.qualifying_result import QualifyingResult
from app.db.models.race import Race
from app.db.models.race_result import RaceResult

logger = logging.getLogger(__name__)

GRID_TIERS = {
    "front": (1, 4),
    "midfield": (5, 10),
    "lower": (11, 20),
}


def _is_classified_result(position_text: Optional[str], status: Optional[str]) -> bool:
    """Determine whether a race result represents an analytically classified finisher.

    Per F1 regulations:
    - Classified finishers have a numeric position_text.
    - DNFs have position_text 'R' or status indicating retirement.
    - DSQs and DNSs are not classified finishers.
    """
    if not position_text or not position_text.isdigit():
        return False
    stat_lower = (status or "").lower()
    if stat_lower in ("retired", "did not start", "disqualified", "withdrawn"):
        return False
    return True


def _is_actual_start(status: Optional[str], position_text: Optional[str]) -> bool:
    """Determine whether a driver actually started the Grand Prix.

    DNS events ('Did not start', 'Withdrawn', position_text 'W' or 'DNS') are excluded.
    """
    stat_lower = (status or "").lower()
    if stat_lower in ("did not start", "withdrawn", "dns"):
        return False
    if position_text and position_text.upper() in ("W", "DNS"):
        return False
    return True


@dataclass(frozen=True)
class GridTierSummary:
    """Analytical summary of position changes for a specific starting grid tier."""

    tier_name: str
    min_grid: int
    max_grid: int
    eligible_starts: int
    classified_finishes: int
    non_classified_results: int
    total_positions_gained: int
    avg_position_delta: Optional[float]


@dataclass(frozen=True)
class PoleToWinSummary:
    """Analytical summary of pole-to-win conversions."""

    total_poles: int
    wins_from_pole: int
    pole_to_win_rate: float


@dataclass(frozen=True)
class FrontRowSummary:
    """Analytical summary of front-row podium retention."""

    front_row_starts: int
    front_row_podiums: int
    front_row_podium_rate: float


@dataclass(frozen=True)
class Top10ConversionSummary:
    """Analytical summary of top-10 starting grid to top-10 finish conversions."""

    top10_starts: int
    top10_conversions: int
    top10_conversion_rate: float


@dataclass(frozen=True)
class DriverConversionSummary:
    """Complete multi-metric qualifying-to-race conversion profile for a driver."""

    season_year: int
    driver_id: str
    driver_name: str
    constructor_id: Optional[str]
    constructor_name: Optional[str]
    pole_to_win: PoleToWinSummary
    front_row: FrontRowSummary
    top10_conversion: Top10ConversionSummary
    grid_tiers: dict[str, GridTierSummary]
    rounds_included: list[int]
    pit_lane_starts_count: int
    dns_count: int


def get_driver_conversion_summary(
    session: Session,
    season_year: int,
    driver_id: str,
    up_to_round: Optional[int] = None,
) -> Optional[DriverConversionSummary]:
    """Retrieve full qualifying-to-race conversion summary for a specific driver.

    Args:
        session: Active database session.
        season_year: Championship season year.
        driver_id: Jolpica driver slug (e.g. 'max_verstappen').
        up_to_round: Optional round cutoff (inclusive).

    Returns:
        DriverConversionSummary instance, or None if driver has no records in season.
    """
    driver = session.scalars(
        select(Driver).where(Driver.driver_id == driver_id)
    ).first()
    if driver is None:
        return None

    # Query races for the season
    race_query = select(Race).where(Race.season_year == season_year)
    if up_to_round is not None:
        race_query = race_query.where(Race.round <= up_to_round)
    race_query = race_query.order_by(Race.round.asc())
    races = session.scalars(race_query).all()

    if not races:
        return None

    race_ids = [r.id for r in races]
    round_by_race_id = {r.id: r.round for r in races}

    # Query QualifyingResult and RaceResult for this driver
    q_results = session.scalars(
        select(QualifyingResult)
        .where(
            QualifyingResult.race_id.in_(race_ids),
            QualifyingResult.driver_id == driver.id,
        )
    ).all()
    quali_by_race = {q.race_id: q for q in q_results}

    r_results = session.scalars(
        select(RaceResult)
        .where(
            RaceResult.race_id.in_(race_ids),
            RaceResult.driver_id == driver.id,
        )
    ).all()
    race_by_race = {r.race_id: r for r in r_results}

    if not quali_by_race and not race_by_race:
        return None

    # Track constructor info
    primary_constructor_id: Optional[str] = None
    primary_constructor_name: Optional[str] = None
    if r_results:
        cid = r_results[-1].constructor_id
        con = session.get(Constructor, cid) if cid else None
        if con:
            primary_constructor_id = con.constructor_id
            primary_constructor_name = con.name

    # Tracking state
    total_poles = 0
    wins_from_pole = 0

    front_row_starts = 0
    front_row_podiums = 0

    top10_starts = 0
    top10_conversions = 0

    tier_stats = {
        t: {
            "eligible_starts": 0,
            "classified_finishes": 0,
            "non_classified_results": 0,
            "total_positions_gained": 0,
        }
        for t in GRID_TIERS
    }

    pit_lane_starts_count = 0
    dns_count = 0
    rounds_included: list[int] = []

    # Process round by round
    for race in races:
        r_id = race.id
        q_res = quali_by_race.get(r_id)
        r_res = race_by_race.get(r_id)

        if q_res is None and r_res is None:
            continue

        rounds_included.append(race.round)

        # Check whether driver actually started the race
        is_dns = False
        if r_res is not None:
            if not _is_actual_start(r_res.status, r_res.position_text):
                is_dns = True
                dns_count += 1
        elif q_res is not None:
            # Driver had qualifying result but no race result
            is_dns = True
            dns_count += 1

        # Evaluate Qualifying classification metrics (Pole and Front-Row)
        if q_res is not None:
            if q_res.position == 1:
                total_poles += 1
                if not is_dns and r_res is not None:
                    classified = _is_classified_result(r_res.position_text, r_res.status)
                    if classified and r_res.source_position == 1:
                        wins_from_pole += 1

            if q_res.position in (1, 2):
                if not is_dns and r_res is not None:
                    front_row_starts += 1
                    classified = _is_classified_result(r_res.position_text, r_res.status)
                    if classified and r_res.source_position is not None and r_res.source_position <= 3:
                        front_row_podiums += 1

        # Evaluate Starting Grid metrics (Grid Tiers and Top-10 Conversion)
        if r_res is not None:
            if is_dns:
                continue

            classified = _is_classified_result(r_res.position_text, r_res.status)
            grid = r_res.grid_position
            finish = r_res.source_position

            if grid is None or grid <= 0:
                pit_lane_starts_count += 1
                continue

            # Top-10 conversion
            if 1 <= grid <= 10:
                top10_starts += 1
                if classified and finish is not None and 1 <= finish <= 10:
                    top10_conversions += 1

            # Grid tiers
            tier_name = None
            for t_name, (low, high) in GRID_TIERS.items():
                if low <= grid <= high:
                    tier_name = t_name
                    break

            if tier_name is not None:
                st = tier_stats[tier_name]
                st["eligible_starts"] += 1
                if classified and finish is not None:
                    st["classified_finishes"] += 1
                    delta = grid - finish
                    st["total_positions_gained"] += delta
                else:
                    st["non_classified_results"] += 1

    # Compute rates
    pole_rate = round(wins_from_pole / total_poles * 100.0, 2) if total_poles > 0 else 0.0
    front_row_rate = round(front_row_podiums / front_row_starts * 100.0, 2) if front_row_starts > 0 else 0.0
    top10_rate = round(top10_conversions / top10_starts * 100.0, 2) if top10_starts > 0 else 0.0

    # Build GridTierSummary dict
    built_tiers: dict[str, GridTierSummary] = {}
    for t_name, (low, high) in GRID_TIERS.items():
        st = tier_stats[t_name]
        c_fin = st["classified_finishes"]
        avg_d = round(st["total_positions_gained"] / c_fin, 4) if c_fin > 0 else None
        built_tiers[t_name] = GridTierSummary(
            tier_name=t_name,
            min_grid=low,
            max_grid=high,
            eligible_starts=st["eligible_starts"],
            classified_finishes=c_fin,
            non_classified_results=st["non_classified_results"],
            total_positions_gained=st["total_positions_gained"],
            avg_position_delta=avg_d,
        )

    driver_full_name = f"{driver.given_name} {driver.family_name}".strip()

    return DriverConversionSummary(
        season_year=season_year,
        driver_id=driver.driver_id,
        driver_name=driver_full_name,
        constructor_id=primary_constructor_id,
        constructor_name=primary_constructor_name,
        pole_to_win=PoleToWinSummary(
            total_poles=total_poles,
            wins_from_pole=wins_from_pole,
            pole_to_win_rate=pole_rate,
        ),
        front_row=FrontRowSummary(
            front_row_starts=front_row_starts,
            front_row_podiums=front_row_podiums,
            front_row_podium_rate=front_row_rate,
        ),
        top10_conversion=Top10ConversionSummary(
            top10_starts=top10_starts,
            top10_conversions=top10_conversions,
            top10_conversion_rate=top10_rate,
        ),
        grid_tiers=built_tiers,
        rounds_included=sorted(rounds_included),
        pit_lane_starts_count=pit_lane_starts_count,
        dns_count=dns_count,
    )


def get_all_drivers_conversion_summaries(
    session: Session,
    season_year: int,
    up_to_round: Optional[int] = None,
) -> list[DriverConversionSummary]:
    """Retrieve qualifying-to-race conversion summaries for all active drivers in a season.

    Args:
        session: Active database session.
        season_year: Championship season year.
        up_to_round: Optional round cutoff (inclusive).

    Returns:
        List of DriverConversionSummary sorted deterministically by driver_id.
    """
    # Active drivers have at least one race or qualifying record in this season
    driver_ids_query = (
        select(Driver.driver_id)
        .join(RaceResult, RaceResult.driver_id == Driver.id)
        .join(Race, RaceResult.race_id == Race.id)
        .where(Race.season_year == season_year)
    )
    if up_to_round is not None:
        driver_ids_query = driver_ids_query.where(Race.round <= up_to_round)

    active_driver_ids = sorted(set(session.scalars(driver_ids_query).all()))

    summaries: list[DriverConversionSummary] = []
    for d_id in active_driver_ids:
        summ = get_driver_conversion_summary(session, season_year, d_id, up_to_round)
        if summ is not None:
            summaries.append(summ)

    return summaries

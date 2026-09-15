"""Longitudinal teammate comparisons — event-level and aggregated season head-to-heads.

Teammate relationships are event-scoped based on constructor_id in each race result.
Driver pairings are strictly ordered driver_a < driver_b by driver_id (alphabetical).
Driver substitutions (e.g. Bearman for Sainz in Round 2) are tracked as distinct pairings.
Qualifying and race head-to-head metrics explicitly report comparable rounds.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.qualifying_analysis import _best_time_millis
from app.analytics.types import SeasonTeammateComparison, TeammateEventComparison
from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.qualifying_result import QualifyingResult
from app.db.models.race import Race
from app.db.models.race_result import RaceResult
from app.db.models.sprint_result import SprintResult

def _is_classified_result(position_text: Optional[str], status: Optional[str]) -> bool:
    """Determine whether a race result represents an analytically classified finisher."""
    if not position_text or not position_text.isdigit():
        return False
    stat_lower = (status or "").lower()
    if stat_lower in ("retired", "did not start", "disqualified", "withdrawn"):
        return False
    return True


def get_event_teammate_comparisons(
    session: Session,
    season_year: int,
    round_num: int,
) -> list[TeammateEventComparison]:
    """Return head-to-head teammate comparisons for all constructors in a single round.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        round_num: Round number within the season.

    Returns:
        List of TeammateEventComparison objects.
    """
    race = session.scalars(
        select(Race).where(Race.season_year == season_year, Race.round == round_num)
    ).first()
    if race is None:
        return []

    # Query all race results with constructor and driver
    rr_rows = session.execute(
        select(RaceResult, Constructor, Driver)
        .join(Constructor, RaceResult.constructor_id == Constructor.id)
        .join(Driver, RaceResult.driver_id == Driver.id)
        .where(RaceResult.race_id == race.id)
    ).all()

    # Group by constructor
    by_constructor: dict[int, dict] = defaultdict(lambda: {"constructor": None, "drivers": []})
    for rr, con, drv in rr_rows:
        by_constructor[con.id]["constructor"] = con
        by_constructor[con.id]["drivers"].append((rr, drv))

    # Pre-fetch qualifying results for this race
    qr_rows = session.execute(
        select(QualifyingResult)
        .where(QualifyingResult.race_id == race.id)
    ).scalars().all()
    qr_map: dict[int, QualifyingResult] = {qr.driver_id: qr for qr in qr_rows}

    # Pre-fetch sprint results for this race
    sr_rows = session.execute(
        select(SprintResult.driver_id, SprintResult.points)
        .where(SprintResult.race_id == race.id)
    ).all()
    sprint_map: dict[int, Decimal] = dict(sr_rows)

    comparisons: list[TeammateEventComparison] = []

    for con_id, group in by_constructor.items():
        drivers_list = group["drivers"]
        if len(drivers_list) < 2:
            continue

        con: Constructor = group["constructor"]

        # Sort alphabetically by driver_id for deterministic pair ordering
        drivers_list.sort(key=lambda x: x[1].driver_id)
        rr_a, drv_a = drivers_list[0]
        rr_b, drv_b = drivers_list[1]

        # Qualifying comparison
        qr_a = qr_map.get(drv_a.id)
        qr_b = qr_map.get(drv_b.id)

        best_a = _best_time_millis(qr_a) if qr_a else None
        best_b = _best_time_millis(qr_b) if qr_b else None
        quali_delta = (best_a - best_b) if (best_a is not None and best_b is not None) else None

        pos_a = qr_a.position if qr_a else None
        pos_b = qr_b.position if qr_b else None
        is_comp_quali = pos_a is not None and pos_b is not None

        ahead_quali: Optional[str] = None
        if is_comp_quali:
            if pos_a < pos_b:
                ahead_quali = drv_a.driver_id
            elif pos_b < pos_a:
                ahead_quali = drv_b.driver_id

        # Race comparison
        fin_a = rr_a.source_position if _is_classified_result(rr_a.position_text, rr_a.status) else None
        fin_b = rr_b.source_position if _is_classified_result(rr_b.position_text, rr_b.status) else None
        is_comp_finish = fin_a is not None and fin_b is not None

        ahead_race: Optional[str] = None
        if is_comp_finish:
            if fin_a < fin_b:
                ahead_race = drv_a.driver_id
            elif fin_b < fin_a:
                ahead_race = drv_b.driver_id

        sprint_a = sprint_map.get(drv_a.id, Decimal("0.0"))
        sprint_b = sprint_map.get(drv_b.id, Decimal("0.0"))

        comparisons.append(
            TeammateEventComparison(
                season_year=season_year,
                round=round_num,
                race_name=race.race_name,
                constructor_id=con.constructor_id,
                constructor_name=con.name,
                driver_a_id=drv_a.driver_id,
                driver_a_name=f"{drv_a.given_name} {drv_a.family_name}",
                driver_b_id=drv_b.driver_id,
                driver_b_name=f"{drv_b.given_name} {drv_b.family_name}",
                qualifying_a_pos=pos_a,
                qualifying_b_pos=pos_b,
                qualifying_delta_millis=quali_delta,
                grid_a=rr_a.grid_position,
                grid_b=rr_b.grid_position,
                finish_a=fin_a,
                finish_b=fin_b,
                status_a=rr_a.status,
                status_b=rr_b.status,
                points_a=rr_a.points or Decimal("0.0"),
                points_b=rr_b.points or Decimal("0.0"),
                sprint_points_a=sprint_a,
                sprint_points_b=sprint_b,
                is_comparable_qualifying=is_comp_quali,
                is_comparable_finish=is_comp_finish,
                ahead_in_qualifying=ahead_quali,
                ahead_in_race=ahead_race,
            )
        )

    comparisons.sort(key=lambda c: c.constructor_name)
    return comparisons


def get_season_teammate_comparisons(
    session: Session,
    season_year: int,
    up_to_round: Optional[int] = None,
    constructor_id: Optional[str] = None,
) -> list[SeasonTeammateComparison]:
    """Return season-aggregated teammate comparisons across rounds.

    Pairings are keyed by (constructor_id, driver_a_id, driver_b_id) so that
    driver substitutions are naturally partitioned into separate pairing records.

    Args:
        session: Active SQLAlchemy session.
        season_year: Championship season year.
        up_to_round: Optional upper round cutoff (inclusive).
        constructor_id: Optional filter for a specific constructor slug.

    Returns:
        List of SeasonTeammateComparison objects.
    """
    # Fetch distinct rounds in this season up to up_to_round
    race_query = select(Race.round).where(Race.season_year == season_year)
    if up_to_round is not None:
        race_query = race_query.where(Race.round <= up_to_round)
    race_rounds = sorted(session.scalars(race_query).all())

    if not race_rounds:
        return []

    target_cutoff = up_to_round if up_to_round is not None else max(race_rounds)

    # Collect event comparisons for each round
    pairing_events: dict[tuple[str, str, str], list[TeammateEventComparison]] = defaultdict(list)

    for r_num in race_rounds:
        event_comps = get_event_teammate_comparisons(
            session=session,
            season_year=season_year,
            round_num=r_num,
        )
        for ec in event_comps:
            if constructor_id is not None and ec.constructor_id != constructor_id:
                continue
            key = (ec.constructor_id, ec.driver_a_id, ec.driver_b_id)
            pairing_events[key].append(ec)

    season_comps: list[SeasonTeammateComparison] = []

    for (c_id, d_a_id, d_b_id), events in pairing_events.items():
        first_event = events[0]
        con_name = first_event.constructor_name
        d_a_name = first_event.driver_a_name
        d_b_name = first_event.driver_b_name

        rounds_together = len(events)

        comp_quali_count = sum(1 for e in events if e.is_comparable_qualifying)
        quali_h2h_a = sum(1 for e in events if e.ahead_in_qualifying == d_a_id)
        quali_h2h_b = sum(1 for e in events if e.ahead_in_qualifying == d_b_id)

        comp_race_count = sum(1 for e in events if e.is_comparable_finish)
        race_h2h_a = sum(1 for e in events if e.ahead_in_race == d_a_id)
        race_h2h_b = sum(1 for e in events if e.ahead_in_race == d_b_id)

        pts_a = sum(e.points_a for e in events)
        pts_b = sum(e.points_b for e in events)
        s_pts_a = sum(e.sprint_points_a for e in events)
        s_pts_b = sum(e.sprint_points_b for e in events)

        season_comps.append(
            SeasonTeammateComparison(
                season_year=season_year,
                up_to_round=target_cutoff,
                constructor_id=c_id,
                constructor_name=con_name,
                driver_a_id=d_a_id,
                driver_a_name=d_a_name,
                driver_b_id=d_b_id,
                driver_b_name=d_b_name,
                rounds_together=rounds_together,
                qualifying_head_to_head_a=quali_h2h_a,
                qualifying_head_to_head_b=quali_h2h_b,
                qualifying_comparable_rounds=comp_quali_count,
                race_head_to_head_a=race_h2h_a,
                race_head_to_head_b=race_h2h_b,
                race_comparable_rounds=comp_race_count,
                points_a=pts_a,
                points_b=pts_b,
                sprint_points_a=s_pts_a,
                sprint_points_b=s_pts_b,
                total_points_a=pts_a + s_pts_a,
                total_points_b=pts_b + s_pts_b,
            )
        )

    season_comps.sort(key=lambda s: (s.constructor_name, s.driver_a_name))
    return season_comps

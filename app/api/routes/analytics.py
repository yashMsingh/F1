"""Analytics routes: qualifying, pit stops, lap times, and standings."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.lap_time_analysis import get_driver_lap_times
from app.analytics.pit_stop_analysis import (
    get_constructor_pit_stops,
    get_driver_pit_stops,
)
from app.analytics.qualifying_analysis import (
    get_qualifying_order,
    get_teammate_qualifying_comparison,
)
from app.analytics.standings_analysis import (
    get_constructor_standings,
    get_driver_standings,
)
from app.api.deps import get_db
from app.api.schemas import (
    ConstructorPitStopSummaryItem,
    ConstructorStandingItem,
    DriverStandingItem,
    LapTimesResponse,
    LapTimeSummaryItem,
    PitStopsResponse,
    PitStopSummaryItem,
    QualifyingOrderItem,
    QualifyingResponse,
    StandingsResponse,
    TeammateQualifyingComparisonItem,
)
from app.db.models.race import Race

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/races/{season}/{round_num}", tags=["analytics"])


def _ensure_race_exists(db: Session, season: int, round_num: int) -> Race:
    """Verify that a race exists or raise HTTP 404."""
    race = db.scalars(
        select(Race).where(Race.season_year == season, Race.round == round_num)
    ).first()
    if race is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Race not found for season {season}, round {round_num}",
        )
    return race


@router.get("/qualifying", response_model=QualifyingResponse)
def get_qualifying(
    season: int,
    round_num: int,
    db: Session = Depends(get_db),
) -> QualifyingResponse:
    """Return qualifying classifications and teammate delta comparisons."""
    _ensure_race_exists(db, season, round_num)

    orders = get_qualifying_order(db, season, round_num)
    teammates = get_teammate_qualifying_comparison(db, season, round_num)

    return QualifyingResponse(
        qualifying_order=[QualifyingOrderItem.model_validate(q) for q in orders],
        teammate_comparisons=[
            TeammateQualifyingComparisonItem.model_validate(t) for t in teammates
        ],
    )


@router.get("/pit-stops", response_model=PitStopsResponse)
def get_pit_stops(
    season: int,
    round_num: int,
    db: Session = Depends(get_db),
) -> PitStopsResponse:
    """Return per-driver and per-constructor pit stop aggregations."""
    _ensure_race_exists(db, season, round_num)

    drivers = get_driver_pit_stops(db, season, round_num)
    constructors = get_constructor_pit_stops(db, season, round_num)

    return PitStopsResponse(
        drivers=[PitStopSummaryItem.model_validate(d) for d in drivers],
        constructors=[
            ConstructorPitStopSummaryItem.model_validate(c) for c in constructors
        ],
    )


@router.get("/laps", response_model=LapTimesResponse)
def get_laps(
    season: int,
    round_num: int,
    db: Session = Depends(get_db),
) -> LapTimesResponse:
    """Return per-driver lap time summary."""
    _ensure_race_exists(db, season, round_num)

    laps = get_driver_lap_times(db, season, round_num)
    return LapTimesResponse(
        laps=[LapTimeSummaryItem.model_validate(l) for l in laps]
    )


@router.get("/standings", response_model=StandingsResponse)
def get_standings(
    season: int,
    round_num: int,
    db: Session = Depends(get_db),
) -> StandingsResponse:
    """Return driver and constructor championship standings after this round."""
    _ensure_race_exists(db, season, round_num)

    driver_standings = get_driver_standings(db, season, round_num)
    constructor_standings = get_constructor_standings(db, season, round_num)

    return StandingsResponse(
        drivers=[DriverStandingItem.model_validate(d) for d in driver_standings],
        constructors=[
            ConstructorStandingItem.model_validate(c) for c in constructor_standings
        ],
    )

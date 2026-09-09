"""Race-level routes: available races, overview, and results."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.race_analysis import (
    get_grid_vs_finish,
    get_race_overview,
    get_race_results,
)
from app.api.deps import get_db
from app.api.schemas import (
    GridVsFinishItem,
    RaceListItem,
    RaceOverviewResponse,
    RaceResultItem,
    RaceResultsResponse,
)
from app.db.models.circuit import Circuit
from app.db.models.race import Race

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/races", tags=["races"])


@router.get("", response_model=list[RaceListItem])
def list_races(
    season: Optional[int] = Query(None, description="Optional season filter"),
    db: Session = Depends(get_db),
) -> list[RaceListItem]:
    """List available races from the database for the race selector."""
    stmt = (
        select(Race, Circuit.circuit_name)
        .join(Circuit, Race.circuit_id == Circuit.id)
        .order_by(Race.season_year.desc(), Race.round.asc())
    )
    if season is not None:
        stmt = stmt.where(Race.season_year == season)

    rows = db.execute(stmt).all()
    return [
        RaceListItem(
            season_year=race.season_year,
            round=race.round,
            race_name=race.race_name,
            circuit_name=circuit_name,
            race_date=race.race_date,
        )
        for race, circuit_name in rows
    ]


@router.get("/{season}/{round_num}", response_model=RaceOverviewResponse)
def get_race(
    season: int,
    round_num: int,
    db: Session = Depends(get_db),
) -> RaceOverviewResponse:
    """Return high-level overview for a single Grand Prix event."""
    overview = get_race_overview(db, season, round_num)
    if overview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Race not found for season {season}, round {round_num}",
        )
    return RaceOverviewResponse.model_validate(overview)


@router.get("/{season}/{round_num}/results", response_model=RaceResultsResponse)
def get_race_classification(
    season: int,
    round_num: int,
    db: Session = Depends(get_db),
) -> RaceResultsResponse:
    """Return full race classification and starting-grid vs finishing position changes."""
    overview = get_race_overview(db, season, round_num)
    if overview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Race not found for season {season}, round {round_num}",
        )

    results = get_race_results(db, season, round_num)
    grid_vs_finish = get_grid_vs_finish(db, season, round_num)

    return RaceResultsResponse(
        overview=RaceOverviewResponse.model_validate(overview),
        results=[RaceResultItem.model_validate(r) for r in results],
        grid_vs_finish=[GridVsFinishItem.model_validate(g) for g in grid_vs_finish],
    )

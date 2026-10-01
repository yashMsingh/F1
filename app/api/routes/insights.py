"""Deterministic insights route with traceability."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import (
    InsightResponse,
    InsightsResponse,
    InsightTraceabilityResponse,
    SeasonInsightsResponse,
)
from app.db.models.race import Race
from app.insights.engine import InsightEngine
from app.services.longitudinal_service import LongitudinalInsightService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["insights"])


@router.get("/races/{season}/{round_num}/insights", response_model=InsightsResponse)
def get_insights(
    season: int,
    round_num: int,
    db: Session = Depends(get_db),
) -> InsightsResponse:
    """Return all approved deterministic insights for a race, with full audit trail."""
    race = db.scalars(
        select(Race).where(Race.season_year == season, Race.round == round_num)
    ).first()
    if race is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Race not found for season {season}, round {round_num}",
        )

    insights = InsightEngine.evaluate_race_insights(db, season, round_num)

    serialized: list[InsightResponse] = []
    for ins in insights:
        trace_data = asdict(ins.traceability)
        trace_resp = InsightTraceabilityResponse(**trace_data)

        serialized.append(
            InsightResponse(
                insight_id=ins.insight_id,
                rule_id=ins.rule_id,
                category=ins.category.value,
                subject_id=ins.subject_id,
                comparison_subject_id=ins.comparison_subject_id,
                metric=ins.metric,
                direction=ins.direction.value,
                magnitude=ins.magnitude,
                unit=ins.unit,
                evidence_strength=ins.evidence_strength.value,
                sample_size=ins.sample_size,
                scope="race",
                explanation=ins.explanation,
                traceability=trace_resp,
            )
        )

    return InsightsResponse(insights=serialized, total=len(serialized))


@router.get("/season/{season}/insights", response_model=SeasonInsightsResponse)
def get_season_insights(
    season: int,
    driver_id: Optional[str] = Query(None, description="Optional driver filter"),
    constructor_id: Optional[str] = Query(None, description="Optional constructor filter"),
    driver_a_id: Optional[str] = Query(None, description="First driver in teammate pair"),
    driver_b_id: Optional[str] = Query(None, description="Second driver in teammate pair"),
    up_to_round: Optional[int] = Query(None, description="Optional round cutoff"),
    db: Session = Depends(get_db),
) -> SeasonInsightsResponse:
    """Return longitudinal deterministic insights for a championship season with full audit trail."""
    if driver_a_id and driver_b_id:
        insights = LongitudinalInsightService.get_teammate_insights(
            db, season, driver_a_id, driver_b_id, up_to_round
        )
    elif driver_id:
        insights = LongitudinalInsightService.get_driver_insights(
            db, season, driver_id, up_to_round
        )
    elif constructor_id:
        insights = LongitudinalInsightService.get_constructor_insights(
            db, season, constructor_id, up_to_round
        )
    else:
        insights = LongitudinalInsightService.get_season_insights(
            db, season, up_to_round
        )

    serialized: list[InsightResponse] = []
    for ins in insights:
        trace_data = asdict(ins.traceability)
        trace_resp = InsightTraceabilityResponse(**trace_data)

        serialized.append(
            InsightResponse(
                insight_id=ins.insight_id,
                rule_id=ins.rule_id,
                category=ins.category.value,
                subject_id=ins.subject_id,
                comparison_subject_id=ins.comparison_subject_id,
                metric=ins.metric,
                direction=ins.direction.value,
                magnitude=ins.magnitude,
                unit=ins.unit,
                evidence_strength=ins.evidence_strength.value,
                sample_size=ins.sample_size,
                scope="longitudinal",
                explanation=ins.explanation,
                traceability=trace_resp,
            )
        )

    return SeasonInsightsResponse(
        season=season,
        scope="longitudinal",
        insights=serialized,
        total=len(serialized),
    )

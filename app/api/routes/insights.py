"""Deterministic insights route with traceability."""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import (
    InsightResponse,
    InsightsResponse,
    InsightTraceabilityResponse,
)
from app.db.models.race import Race
from app.insights.engine import InsightEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/races/{season}/{round_num}/insights", tags=["insights"])


@router.get("", response_model=InsightsResponse)
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
                traceability=trace_resp,
            )
        )

    return InsightsResponse(insights=serialized, total=len(serialized))

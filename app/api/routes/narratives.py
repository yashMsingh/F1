"""Grounded AI Narrative route with resilient fallback handling."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.exceptions import AIError
from app.ai.narrative import NarrativeService
from app.api.deps import get_db
from app.api.schemas import NarrativeResponse
from app.db.models.race import Race
from app.insights.engine import InsightEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/races/{season}/{round_num}/narrative", tags=["narrative"])


@router.get("", response_model=NarrativeResponse)
def get_narrative(
    season: int,
    round_num: int,
    db: Session = Depends(get_db),
) -> NarrativeResponse:
    """Return a grounded natural-language explanation generated from deterministic evidence.

    Fails gracefully if the AI provider is unavailable, unconfigured, or invalid,
    ensuring the deterministic analytics dashboard remains 100% operational.
    """
    race = db.scalars(
        select(Race).where(Race.season_year == season, Race.round == round_num)
    ).first()
    if race is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Race not found for season {season}, round {round_num}",
        )

    # 1. Fetch approved deterministic insights
    insights = InsightEngine.evaluate_race_insights(db, season, round_num)
    if not insights:
        return NarrativeResponse(
            status="unavailable",
            error="No deterministic insights available to generate an explanation.",
            limitations=["Empty insight set for this Grand Prix."],
            evidence_references=[],
        )

    # 2. Invoke AI narrative service with defensive error handling
    try:
        service = NarrativeService()
        result = service.generate_narrative(insights)
        return NarrativeResponse(
            status="available",
            provider=service.config.provider,
            model=service.config.model,
            narrative=result.narrative,
            limitations=result.limitations,
            evidence_references=result.evidence_references,
        )
    except AIError as err:
        logger.warning(
            "AI narrative generation failed for season=%d round=%d: %s",
            season,
            round_num,
            err,
        )
        return NarrativeResponse(
            status="unavailable",
            error=f"AI explanation unavailable: {err}",
            limitations=["AI provider or validation error encountered."],
            evidence_references=[],
        )
    except Exception as err:
        logger.error(
            "Unexpected error generating AI narrative for season=%d round=%d: %s",
            season,
            round_num,
            err,
            exc_info=True,
        )
        return NarrativeResponse(
            status="unavailable",
            error="AI explanation temporarily unavailable.",
            limitations=[],
            evidence_references=[],
        )

"""Grounded AI Narrative route with resilient fallback handling."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.exceptions import AIError
from app.ai.narrative import NarrativeService
from app.api.deps import get_db
from app.api.schemas import NarrativeGenerateRequest, NarrativeResponse
from app.db.models.race import Race
from app.insights.engine import InsightEngine
from app.insights.types import Insight
from app.services.longitudinal_service import LongitudinalInsightService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["narrative"])


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


def _generate_narrative_with_fallback(
    insights: list[Insight],
    scope: Optional[str] = None,
) -> NarrativeResponse:
    """Helper invoking NarrativeService with defensive error handling."""
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
            scope=scope,
        )
    except AIError as err:
        logger.warning("AI narrative generation failed: %s", err)
        return NarrativeResponse(
            status="unavailable",
            error=f"AI explanation unavailable: {err}",
            limitations=["AI provider or validation error encountered."],
            evidence_references=[],
            scope=scope,
        )
    except Exception as err:
        logger.error("Unexpected error generating AI narrative: %s", err, exc_info=True)
        return NarrativeResponse(
            status="unavailable",
            error="AI explanation temporarily unavailable.",
            limitations=[],
            evidence_references=[],
            scope=scope,
        )


@router.get("/races/{season}/{round_num}/narrative", response_model=NarrativeResponse)
def get_race_narrative(
    season: int,
    round_num: int,
    db: Session = Depends(get_db),
) -> NarrativeResponse:
    """Return a grounded natural-language explanation generated from deterministic race evidence.

    Fails gracefully if the AI provider is unavailable, unconfigured, or invalid,
    ensuring the deterministic analytics dashboard remains 100% operational.
    """
    _ensure_race_exists(db, season, round_num)

    # 1. Fetch approved deterministic insights
    insights = InsightEngine.evaluate_race_insights(db, season, round_num)
    if not insights:
        return NarrativeResponse(
            status="unavailable",
            error="No deterministic insights available to generate an explanation.",
            limitations=["Empty insight set for this Grand Prix."],
            evidence_references=[],
            scope="race",
        )

    # 2. Invoke AI narrative service with defensive error handling
    return _generate_narrative_with_fallback(insights, scope="race")


@router.post("/narrative", response_model=NarrativeResponse)
def generate_narrative_endpoint(
    req: NarrativeGenerateRequest,
    db: Session = Depends(get_db),
) -> NarrativeResponse:
    """Generate an evidence-backed AI narrative for race, longitudinal, or mixed evidence.

    Accepts structured filter criteria (season, driver, constructor, teammate pair, round)
    and orchestrates deterministic evidence extraction via application services before
    synthesizing an explanatory narrative with full grounding constraints.
    """
    if req.scope not in ("race", "longitudinal", "mixed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope '{req.scope}'. Supported scopes: 'race', 'longitudinal', 'mixed'.",
        )

    insights: list[Insight] = []

    if req.scope == "race":
        if req.round_num is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Field 'round_num' is required when scope='race'.",
            )
        _ensure_race_exists(db, req.season, req.round_num)
        race_insights = InsightEngine.evaluate_race_insights(db, req.season, req.round_num)
        if req.driver_id:
            race_insights = [
                i for i in race_insights
                if i.subject_id == req.driver_id or i.comparison_subject_id == req.driver_id
            ]
        if req.constructor_id:
            race_insights = [
                i for i in race_insights
                if i.subject_id == req.constructor_id or i.traceability.constructor_id == req.constructor_id
            ]
        insights = race_insights

    elif req.scope == "longitudinal":
        if req.driver_a_id and req.driver_b_id:
            insights = LongitudinalInsightService.get_teammate_insights(
                db, req.season, req.driver_a_id, req.driver_b_id, req.up_to_round
            )
        elif req.driver_id:
            insights = LongitudinalInsightService.get_driver_insights(
                db, req.season, req.driver_id, req.up_to_round
            )
        elif req.constructor_id:
            insights = LongitudinalInsightService.get_constructor_insights(
                db, req.season, req.constructor_id, req.up_to_round
            )
        else:
            insights = LongitudinalInsightService.get_season_insights(
                db, req.season, req.up_to_round
            )

    elif req.scope == "mixed":
        race_insights = []
        if req.round_num is not None:
            _ensure_race_exists(db, req.season, req.round_num)
            race_insights = InsightEngine.evaluate_race_insights(db, req.season, req.round_num)
            if req.driver_id:
                race_insights = [
                    i for i in race_insights
                    if i.subject_id == req.driver_id or i.comparison_subject_id == req.driver_id
                ]
            if req.constructor_id:
                race_insights = [
                    i for i in race_insights
                    if i.subject_id == req.constructor_id or i.traceability.constructor_id == req.constructor_id
                ]

        long_insights = []
        if req.driver_a_id and req.driver_b_id:
            long_insights = LongitudinalInsightService.get_teammate_insights(
                db, req.season, req.driver_a_id, req.driver_b_id, req.up_to_round
            )
        elif req.driver_id:
            long_insights = LongitudinalInsightService.get_driver_insights(
                db, req.season, req.driver_id, req.up_to_round
            )
        elif req.constructor_id:
            long_insights = LongitudinalInsightService.get_constructor_insights(
                db, req.season, req.constructor_id, req.up_to_round
            )
        else:
            long_insights = LongitudinalInsightService.get_season_insights(
                db, req.season, req.up_to_round
            )

        insights = race_insights + long_insights

    if not insights:
        return NarrativeResponse(
            status="unavailable",
            error="No deterministic insights available to generate an explanation.",
            limitations=["Empty insight set for the requested criteria."],
            evidence_references=[],
            scope=req.scope,
        )

    return _generate_narrative_with_fallback(insights, scope=req.scope)

"""Deterministic insight engine coordinating rule evaluations and deduplication."""

from __future__ import annotations

import logging
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.analytics.constructor_analysis import get_teammate_comparison
from app.analytics.qualifying_analysis import get_teammate_qualifying_comparison
from app.analytics.race_analysis import get_grid_vs_finish
from app.insights.evaluators.pit_stops import (
    evaluate_fast_pit_stop,
    evaluate_pit_stop_variability,
)
from app.insights.evaluators.position_change import (
    evaluate_single_driver_position_change,
)
from app.insights.evaluators.qualifying import (
    evaluate_qualifying_teammate_insight,
)
from app.insights.evaluators.race_pace import (
    evaluate_fastest_recorded_lap,
    evaluate_teammate_race_pace,
)
from app.insights.evaluators.teammate import (
    evaluate_teammate_comparison,
)
from app.insights.types import Insight
from app.statistics.pit_stops import compute_pit_stop_stats
from app.statistics.race_pace import compute_lap_time_stats

logger = logging.getLogger(__name__)


class InsightEngine:
    """Deterministic, rule-based insight generation engine."""

    @staticmethod
    def deduplicate(insights: Sequence[Insight]) -> list[Insight]:
        """Filter out duplicates based on deterministic insight_id while preserving order.

        Args:
            insights: Sequence of potentially duplicate insights.

        Returns:
            Deduplicated list of insights.
        """
        seen: set[str] = set()
        unique: list[Insight] = []
        for ins in insights:
            if ins.insight_id not in seen:
                seen.add(ins.insight_id)
                unique.append(ins)
        return unique

    @classmethod
    def evaluate_race_insights(
        cls,
        session: Session,
        season_year: int,
        round_num: int,
    ) -> list[Insight]:
        """Generate all deterministic insights for a single Grand Prix event.

        Consumes data from app.analytics and app.statistics.
        Never calls external APIs or LLMs.

        Args:
            session: Active database session.
            season_year: Championship season year.
            round_num: Championship round number.

        Returns:
            Deduplicated, deterministically ordered list of Insight instances.
        """
        raw_insights: list[Insight] = []

        # 1. Qualifying teammate comparisons
        quali_comps = get_teammate_qualifying_comparison(session, season_year, round_num)
        for qc in quali_comps:
            ins = evaluate_qualifying_teammate_insight(
                qc, season_year=season_year, round_num=round_num
            )
            if ins is not None:
                raw_insights.append(ins)

        # 2. Starting grid vs finishing position changes
        gvf_records = get_grid_vs_finish(session, season_year, round_num)
        for gvf in gvf_records:
            pos_insights = evaluate_single_driver_position_change(
                gvf, season_year=season_year, round_num=round_num
            )
            raw_insights.extend(pos_insights)

        # 3. Teammate head-to-head race comparisons
        # Distinct constructors in this race
        constructor_ids = {qc.constructor_id for qc in quali_comps}
        for con_id in constructor_ids:
            t_comp = get_teammate_comparison(session, season_year, round_num, con_id)
            if t_comp is not None:
                t_insights = evaluate_teammate_comparison(
                    t_comp, season_year=season_year, round_num=round_num
                )
                raw_insights.extend(t_insights)

        # Deduplicate and sort deterministically
        deduped = cls.deduplicate(raw_insights)
        deduped.sort(key=lambda x: (x.category.value, x.rule_id, x.subject_id, x.insight_id))
        return deduped

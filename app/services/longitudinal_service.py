"""Service boundary orchestrating longitudinal analytics, statistics, and deterministic insights.

This service acts as the boundary between the API layer and the underlying
deterministic insight engine, ensuring API endpoints do not directly import
or orchestrate low-level statistical routines.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.longitudinal_constructor import get_constructor_trajectory
from app.analytics.longitudinal_driver import get_driver_trajectory
from app.analytics.longitudinal_teammate import get_event_teammate_comparisons
from app.db.models.race import Race
from app.insights.engine import InsightEngine
from app.insights.types import Insight
from app.statistics.longitudinal import (
    compute_driver_form_summary,
    compute_driver_longitudinal_stats,
    compute_longitudinal_teammate_h2h_stats,
)

logger = logging.getLogger(__name__)


class LongitudinalInsightService:
    """Application service for retrieving deterministic longitudinal insights."""

    @staticmethod
    def get_driver_insights(
        session: Session,
        season_year: int,
        driver_id: str,
        up_to_round: Optional[int] = None,
    ) -> list[Insight]:
        """Retrieve longitudinal insights for a specific driver.

        Pipeline:
            Phase 3B trajectory SQL
            -> Phase 3C longitudinal stats & rolling form
            -> Phase 3D deterministic driver insight evaluators

        Args:
            session: Active database session.
            season_year: Championship season year.
            driver_id: Driver slug (e.g. 'max_verstappen').
            up_to_round: Optional round cutoff (inclusive).

        Returns:
            Deduplicated, deterministically ordered list of Insight instances.
        """
        traj = get_driver_trajectory(session, season_year, driver_id, up_to_round)
        if not traj:
            return []

        stats = compute_driver_longitudinal_stats(traj)
        form = compute_driver_form_summary(traj, window_size=3)
        return InsightEngine.evaluate_driver_longitudinal_insights(
            stats, form, driver_id=driver_id
        )

    @staticmethod
    def get_constructor_insights(
        session: Session,
        season_year: int,
        constructor_id: str,
        up_to_round: Optional[int] = None,
    ) -> list[Insight]:
        """Retrieve longitudinal insights for a specific constructor.

        Pipeline:
            Phase 3B constructor trajectory SQL
            -> Phase 3D deterministic constructor insight evaluators

        Args:
            session: Active database session.
            season_year: Championship season year.
            constructor_id: Constructor slug (e.g. 'red_bull').
            up_to_round: Optional round cutoff (inclusive).

        Returns:
            Deduplicated, deterministically ordered list of Insight instances.
        """
        traj = get_constructor_trajectory(session, season_year, constructor_id, up_to_round)
        if not traj:
            return []

        return InsightEngine.evaluate_constructor_longitudinal_insights(
            traj, season_year, constructor_id
        )

    @staticmethod
    def get_teammate_insights(
        session: Session,
        season_year: int,
        driver_a_id: str,
        driver_b_id: str,
        up_to_round: Optional[int] = None,
    ) -> list[Insight]:
        """Retrieve longitudinal insights for a specific teammate pairing.

        Pipeline:
            Phase 3B event-scoped teammate comparisons SQL
            -> Phase 3C teammate H2H statistics across all rounds
            -> Phase 3D deterministic teammate H2H evaluators

        Args:
            session: Active database session.
            season_year: Championship season year.
            driver_a_id: First driver slug.
            driver_b_id: Second driver slug.
            up_to_round: Optional round cutoff (inclusive).

        Returns:
            Deduplicated, deterministically ordered list of Insight instances.
        """
        max_round_query = select(func.max(Race.round)).where(Race.season_year == season_year)
        if up_to_round is not None:
            max_round_query = max_round_query.where(Race.round <= up_to_round)
        max_r = session.scalar(max_round_query)

        if not max_r:
            return []

        all_comps = []
        for r in range(1, max_r + 1):
            all_comps.extend(get_event_teammate_comparisons(session, season_year, r))

        if not all_comps:
            return []

        h2h_dict = compute_longitudinal_teammate_h2h_stats(all_comps)
        sorted_pair = sorted([driver_a_id, driver_b_id])
        target_pair = (sorted_pair[0], sorted_pair[1])

        raw_insights: list[Insight] = []
        for (con_id, d_a, d_b), h2h in h2h_dict.items():
            if (d_a, d_b) == target_pair:
                pair_insights = InsightEngine.evaluate_teammate_longitudinal_insights(
                    h2h, season_year
                )
                raw_insights.extend(pair_insights)

        deduped = InsightEngine.deduplicate(raw_insights)
        deduped.sort(key=lambda x: (x.category.value, x.rule_id, x.subject_id, x.insight_id))
        return deduped

    @staticmethod
    def get_season_insights(
        session: Session,
        season_year: int,
        up_to_round: Optional[int] = None,
    ) -> list[Insight]:
        """Retrieve all longitudinal insights for a season across drivers, teammates, and constructors.

        Args:
            session: Active database session.
            season_year: Championship season year.
            up_to_round: Optional round cutoff (inclusive).

        Returns:
            Deduplicated, deterministically ordered list of Insight instances.
        """
        return InsightEngine.evaluate_season_longitudinal_insights(
            session, season_year, up_to_round
        )

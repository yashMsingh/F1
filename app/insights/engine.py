"""Deterministic insight engine coordinating rule evaluations and deduplication."""

from __future__ import annotations

import logging
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.analytics.constructor_analysis import get_teammate_comparison
from app.analytics.qualifying_analysis import get_teammate_qualifying_comparison
from app.analytics.race_analysis import get_grid_vs_finish
from app.insights.evaluators.longitudinal import (
    evaluate_constructor_longitudinal_insights,
    evaluate_driver_longitudinal_insights,
    evaluate_longitudinal_teammate_h2h,
)
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
from app.analytics.types import ConstructorTrajectoryItem
from app.statistics.types import (
    DriverFormSummary,
    DriverLongitudinalStats,
    TeammateH2HStatistics,
)
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

    @classmethod
    def evaluate_driver_longitudinal_insights(
        cls,
        stats: DriverLongitudinalStats,
        form_summary: Optional[DriverFormSummary] = None,
        driver_id: Optional[str] = None,
    ) -> list[Insight]:
        """Generate all deterministic longitudinal insights for a driver profile.

        Args:
            stats: DriverLongitudinalStats from Phase 3C.
            form_summary: Optional DriverFormSummary from Phase 3C.
            driver_id: Optional explicit driver slug override.

        Returns:
            Deduplicated, deterministically ordered list of Insight instances.
        """
        raw = evaluate_driver_longitudinal_insights(stats, form_summary, driver_id=driver_id)
        deduped = cls.deduplicate(raw)
        deduped.sort(key=lambda x: (x.category.value, x.rule_id, x.subject_id, x.insight_id))
        return deduped

    @classmethod
    def evaluate_teammate_longitudinal_insights(
        cls,
        h2h_stats: TeammateH2HStatistics,
        season_year: int,
    ) -> list[Insight]:
        """Generate all deterministic longitudinal insights for a teammate pairing.

        Args:
            h2h_stats: TeammateH2HStatistics from Phase 3C.
            season_year: Championship season year.

        Returns:
            Deduplicated, deterministically ordered list of Insight instances.
        """
        raw = evaluate_longitudinal_teammate_h2h(h2h_stats, season_year)
        deduped = cls.deduplicate(raw)
        deduped.sort(key=lambda x: (x.category.value, x.rule_id, x.subject_id, x.insight_id))
        return deduped

    @classmethod
    def evaluate_constructor_longitudinal_insights(
        cls,
        trajectory: Sequence[ConstructorTrajectoryItem],
        season_year: int,
        constructor_id: str,
    ) -> list[Insight]:
        """Generate all deterministic longitudinal insights for a constructor trajectory.

        Args:
            trajectory: Sequence of ConstructorTrajectoryItem from Phase 3B.
            season_year: Championship season year.
            constructor_id: Constructor slug.

        Returns:
            Deduplicated, deterministically ordered list of Insight instances.
        """
        raw = evaluate_constructor_longitudinal_insights(trajectory, season_year, constructor_id)
        deduped = cls.deduplicate(raw)
        deduped.sort(key=lambda x: (x.category.value, x.rule_id, x.subject_id, x.insight_id))
        return deduped

    @classmethod
    def evaluate_season_longitudinal_insights(
        cls,
        session: Session,
        season_year: int,
        up_to_round: Optional[int] = None,
    ) -> list[Insight]:
        """Generate all deterministic longitudinal insights across all drivers, teammates, and constructors.

        Orchestrates:
        1. SQL analytical queries (Phase 3B)
        2. Statistical aggregations (Phase 3C)
        3. Deterministic rule evaluation (Phase 3D)

        Strictly downstream of analytical SQL. Never invokes LLM.

        Args:
            session: Active database session.
            season_year: Championship season year.
            up_to_round: Optional round cutoff (inclusive).

        Returns:
            Deduplicated, deterministically ordered list of Insight instances.
        """
        from sqlalchemy import func, select
        from app.analytics.longitudinal_constructor import get_constructor_trajectory
        from app.analytics.longitudinal_driver import get_driver_trajectory
        from app.analytics.longitudinal_teammate import get_event_teammate_comparisons
        from app.db.models.constructor import Constructor
        from app.db.models.driver import Driver
        from app.db.models.race import Race
        from app.db.models.race_result import RaceResult
        from app.statistics.longitudinal import (
            compute_driver_form_summary,
            compute_driver_longitudinal_stats,
            compute_longitudinal_teammate_h2h_stats,
        )

        raw_insights: list[Insight] = []

        # 1. Driver Longitudinal Insights
        driver_query = (
            select(Driver.driver_id)
            .join(RaceResult, RaceResult.driver_id == Driver.id)
            .join(Race, RaceResult.race_id == Race.id)
            .where(Race.season_year == season_year)
        )
        if up_to_round is not None:
            driver_query = driver_query.where(Race.round <= up_to_round)
        driver_ids = sorted(set(session.scalars(driver_query).all()))

        for drv_id in driver_ids:
            traj = get_driver_trajectory(session, season_year, drv_id, up_to_round)
            if traj:
                stats = compute_driver_longitudinal_stats(traj)
                form = compute_driver_form_summary(traj, window_size=3)
                driver_insights = evaluate_driver_longitudinal_insights(stats, form, driver_id=drv_id)
                raw_insights.extend(driver_insights)

        # 2. Teammate Longitudinal Insights
        max_round_query = select(func.max(Race.round)).where(Race.season_year == season_year)
        if up_to_round is not None:
            max_round_query = max_round_query.where(Race.round <= up_to_round)
        max_r = session.scalar(max_round_query)

        if max_r:
            all_comps = []
            for r in range(1, max_r + 1):
                all_comps.extend(get_event_teammate_comparisons(session, season_year, r))
            if all_comps:
                h2h_dict = compute_longitudinal_teammate_h2h_stats(all_comps)
                for h2h in h2h_dict.values():
                    teammate_insights = evaluate_longitudinal_teammate_h2h(h2h, season_year)
                    raw_insights.extend(teammate_insights)

        # 3. Constructor Longitudinal Insights
        con_query = (
            select(Constructor.constructor_id)
            .join(RaceResult, RaceResult.constructor_id == Constructor.id)
            .join(Race, RaceResult.race_id == Race.id)
            .where(Race.season_year == season_year)
        )
        if up_to_round is not None:
            con_query = con_query.where(Race.round <= up_to_round)
        con_ids = sorted(set(session.scalars(con_query).all()))

        for cid in con_ids:
            con_traj = get_constructor_trajectory(session, season_year, cid, up_to_round)
            if con_traj:
                con_insights = evaluate_constructor_longitudinal_insights(con_traj, season_year, cid)
                raw_insights.extend(con_insights)

        # Deduplicate and sort deterministically
        deduped = cls.deduplicate(raw_insights)
        deduped.sort(key=lambda x: (x.category.value, x.rule_id, x.subject_id, x.insight_id))
        return deduped

"""Deterministic evaluator for teammate head-to-head multi-dimensional insights.

Rules:
- Evaluates 4 independent dimensions: qualifying, grid, finish, points.
- Zero composite scores, zero ratings, zero winner declarations.
- Driver ordering is strictly alphabetical by driver_id (driver_a < driver_b).
"""

from __future__ import annotations

from typing import Optional, Union

from app.analytics.types import TeammateComparison
from app.insights.rules import (
    RULE_TEAMMATE_FINISH_ADVANTAGE,
    RULE_TEAMMATE_GRID_ADVANTAGE,
    RULE_TEAMMATE_POINTS_ADVANTAGE,
    RULE_TEAMMATE_POINTS_DEFICIT,
    get_rule,
)
from app.insights.types import (
    Direction,
    Insight,
    InsightCategory,
    InsightTraceability,
    classify_evidence_strength,
)
from app.statistics.types import TeammateHeadToHeadStats


def evaluate_teammate_comparison(
    item: Union[TeammateComparison, TeammateHeadToHeadStats],
    *,
    season_year: Optional[int] = None,
    round_num: Optional[int] = None,
) -> list[Insight]:
    """Evaluate teammate comparison evidence across independent dimensions.

    Args:
        item: TeammateComparison (single race) or TeammateHeadToHeadStats (multi-race).
        season_year: Optional season context.
        round_num: Optional round context.

    Returns:
        List of generated independent insights.
    """
    if isinstance(item, TeammateComparison):
        constructor_id = item.constructor_id
        driver_a = item.driver_a_id
        driver_b = item.driver_b_id
        grid_d = float(item.grid_delta) if item.grid_delta is not None else None
        finish_d = float(item.finish_delta) if item.finish_delta is not None else None
        points_d = float(item.points_delta) if item.points_delta is not None else None
        sample_size = 1
        source_func = "get_teammate_comparison"
    elif isinstance(item, TeammateHeadToHeadStats):
        constructor_id = item.constructor_id
        driver_a = item.driver_a_id
        driver_b = item.driver_b_id
        grid_d = item.grid_delta.mean
        finish_d = item.finish_delta.mean
        points_d = item.points_delta.mean
        sample_size = item.quality.valid_observations
        source_func = "compute_teammate_head_to_head_stats"
    else:
        return []

    insights: list[Insight] = []

    # 1. Starting Grid Dimension (negative delta = driver_a started ahead)
    if grid_d is not None and grid_d < 0:
        rule = get_rule(RULE_TEAMMATE_GRID_ADVANTAGE)
        strength = classify_evidence_strength(sample_size, rule.min_sample_size)
        trace = InsightTraceability(
            source_metric="grid_delta",
            source_function=source_func,
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=grid_d,
            unit="positions",
            sample_size=sample_size,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="grid_a - grid_b; negative means driver_a started ahead on the grid",
            season_year=season_year,
            round_num=round_num,
            driver_id=driver_a,
            constructor_id=constructor_id,
        )
        insights.append(
            Insight(
                insight_id=f"{rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{driver_a}:{driver_b}",
                rule_id=rule.rule_id,
                category=InsightCategory.TEAMMATE,
                subject_id=driver_a,
                comparison_subject_id=driver_b,
                metric="grid_delta",
                direction=Direction.HIGHER,
                magnitude=abs(grid_d),
                unit="positions",
                evidence_strength=strength,
                sample_size=sample_size,
                traceability=trace,
            )
        )

    # 2. Finishing Position Dimension (negative delta = driver_a finished ahead)
    if finish_d is not None and finish_d < 0:
        rule = get_rule(RULE_TEAMMATE_FINISH_ADVANTAGE)
        strength = classify_evidence_strength(sample_size, rule.min_sample_size)
        trace = InsightTraceability(
            source_metric="finish_delta",
            source_function=source_func,
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=finish_d,
            unit="positions",
            sample_size=sample_size,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="finish_a - finish_b; negative means driver_a finished ahead",
            season_year=season_year,
            round_num=round_num,
            driver_id=driver_a,
            constructor_id=constructor_id,
        )
        insights.append(
            Insight(
                insight_id=f"{rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{driver_a}:{driver_b}",
                rule_id=rule.rule_id,
                category=InsightCategory.TEAMMATE,
                subject_id=driver_a,
                comparison_subject_id=driver_b,
                metric="finish_delta",
                direction=Direction.HIGHER,
                magnitude=abs(finish_d),
                unit="positions",
                evidence_strength=strength,
                sample_size=sample_size,
                traceability=trace,
            )
        )

    # 3. Points Dimension (positive delta = driver_a scored more points)
    if points_d is not None:
        if points_d > 0:
            rule = get_rule(RULE_TEAMMATE_POINTS_ADVANTAGE)
            direction = Direction.HIGHER
        elif points_d < 0:
            rule = get_rule(RULE_TEAMMATE_POINTS_DEFICIT)
            direction = Direction.LOWER
        else:
            rule = None
            direction = None

        if rule is not None and direction is not None:
            strength = classify_evidence_strength(sample_size, rule.min_sample_size)
            trace = InsightTraceability(
                source_metric="points_delta",
                source_function=source_func,
                rule_id=rule.rule_id,
                rule_parameters=rule.thresholds,
                observed_value=points_d,
                unit="points",
                sample_size=sample_size,
                minimum_sample_size=rule.min_sample_size,
                sign_convention="points_a - points_b; positive means driver_a scored more",
                season_year=season_year,
                round_num=round_num,
                driver_id=driver_a,
                constructor_id=constructor_id,
            )
            insights.append(
                Insight(
                    insight_id=f"{rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{driver_a}:{driver_b}",
                    rule_id=rule.rule_id,
                    category=InsightCategory.TEAMMATE,
                    subject_id=driver_a,
                    comparison_subject_id=driver_b,
                    metric="points_delta",
                    direction=direction,
                    magnitude=abs(points_d),
                    unit="points",
                    evidence_strength=strength,
                    sample_size=sample_size,
                    traceability=trace,
                )
            )

    return insights

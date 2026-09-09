"""Deterministic evaluator for qualifying teammate comparisons."""

from __future__ import annotations

from typing import Optional, Union

from app.analytics.types import TeammateQualifyingComparison
from app.insights.rules import (
    RULE_QUALIFYING_TEAMMATE_ADVANTAGE,
    RULE_QUALIFYING_TEAMMATE_DEFICIT,
    RULE_QUALIFYING_TEAMMATE_EQUAL,
    get_rule,
)
from app.insights.types import (
    Direction,
    Insight,
    InsightCategory,
    InsightTraceability,
    classify_evidence_strength,
)
from app.statistics.types import QualifyingDeltaStats


def evaluate_qualifying_teammate_insight(
    item: Union[TeammateQualifyingComparison, QualifyingDeltaStats],
    *,
    season_year: Optional[int] = None,
    round_num: Optional[int] = None,
) -> Optional[Insight]:
    """Evaluate a qualifying teammate delta into a deterministic Insight.

    Sign convention: delta = driver_a - driver_b (in milliseconds).
    - delta < 0 -> Driver A faster than Driver B
    - delta > 0 -> Driver A slower than Driver B
    - delta == 0 -> Driver A and Driver B set identical times

    Args:
        item: TeammateQualifyingComparison or QualifyingDeltaStats.
        season_year: Optional championship season context.
        round_num: Optional championship round context.

    Returns:
        Insight instance, or None if sample size is insufficient or delta is missing.
    """
    if isinstance(item, TeammateQualifyingComparison):
        constructor_id = item.constructor_id
        driver_a = item.driver_a_id
        driver_b = item.driver_b_id
        delta = item.delta_millis
        sample_size = 1 if delta is not None else 0
        source_func = "get_teammate_qualifying_comparison"
    elif isinstance(item, QualifyingDeltaStats):
        constructor_id = item.constructor_id
        driver_a = item.driver_a_id
        driver_b = item.driver_b_id
        delta = item.stats.mean
        sample_size = item.stats.sample_size
        source_func = "compute_qualifying_delta_stats"
    else:
        return None

    if delta is None or sample_size < 1:
        return None

    if delta < 0:
        rule = get_rule(RULE_QUALIFYING_TEAMMATE_ADVANTAGE)
        direction = Direction.FASTER
    elif delta > 0:
        rule = get_rule(RULE_QUALIFYING_TEAMMATE_DEFICIT)
        direction = Direction.SLOWER
    else:
        rule = get_rule(RULE_QUALIFYING_TEAMMATE_EQUAL)
        direction = Direction.EQUAL

    strength = classify_evidence_strength(sample_size, rule.min_sample_size)
    insight_id = f"{rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{driver_a}:{driver_b}"

    traceability = InsightTraceability(
        source_metric="qualifying_delta_millis",
        source_function=source_func,
        rule_id=rule.rule_id,
        rule_parameters=rule.thresholds,
        observed_value=delta,
        unit="milliseconds",
        sample_size=sample_size,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="delta = driver_a - driver_b; negative means driver_a was faster",
        season_year=season_year,
        round_num=round_num,
        driver_id=driver_a,
        constructor_id=constructor_id,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=InsightCategory.QUALIFYING,
        subject_id=driver_a,
        comparison_subject_id=driver_b,
        metric="qualifying_delta_millis",
        direction=direction,
        magnitude=abs(float(delta)),
        unit="milliseconds",
        evidence_strength=strength,
        sample_size=sample_size,
        traceability=traceability,
    )

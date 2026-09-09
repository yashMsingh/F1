"""Deterministic evaluator for position change insights."""

from __future__ import annotations

from typing import Optional, Union

from app.analytics.types import GridVsFinish
from app.insights.rules import (
    LARGE_POSITION_GAIN_THRESHOLD,
    RULE_LARGE_POSITION_GAIN,
    RULE_POSITION_GAIN,
    RULE_POSITION_LOSS,
    RULE_POSITION_MAINTAINED,
    get_rule,
)
from app.insights.types import (
    Direction,
    Insight,
    InsightCategory,
    InsightTraceability,
    classify_evidence_strength,
)
from app.statistics.types import PositionChangeStats


def evaluate_single_driver_position_change(
    record: GridVsFinish,
    *,
    season_year: Optional[int] = None,
    round_num: Optional[int] = None,
) -> list[Insight]:
    """Evaluate a single race GridVsFinish record for a driver.

    DNFs, missing grids, and unclassified finishes have position_change=None
    and emit zero insights.

    Args:
        record: GridVsFinish record.
        season_year: Optional season context.
        round_num: Optional round context.

    Returns:
        List of generated insights (may include large position gain).
    """
    if record.position_change is None:
        return []

    change = record.position_change
    insights: list[Insight] = []

    if change > 0:
        base_rule = get_rule(RULE_POSITION_GAIN)
        base_direction = Direction.GAINED
    elif change < 0:
        base_rule = get_rule(RULE_POSITION_LOSS)
        base_direction = Direction.LOST
    else:
        base_rule = get_rule(RULE_POSITION_MAINTAINED)
        base_direction = Direction.STABLE

    base_id = f"{base_rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{record.driver_id}:none"
    strength = classify_evidence_strength(1, base_rule.min_sample_size)

    trace = InsightTraceability(
        source_metric="position_change",
        source_function="get_grid_vs_finish",
        rule_id=base_rule.rule_id,
        rule_parameters=base_rule.thresholds,
        observed_value=change,
        unit="positions",
        sample_size=1,
        minimum_sample_size=base_rule.min_sample_size,
        sign_convention="position_change = grid_position - finish_position; positive means gained positions",
        season_year=season_year,
        round_num=round_num,
        driver_id=record.driver_id,
    )

    insights.append(
        Insight(
            insight_id=base_id,
            rule_id=base_rule.rule_id,
            category=InsightCategory.POSITION_CHANGE,
            subject_id=record.driver_id,
            comparison_subject_id=None,
            metric="position_change",
            direction=base_direction,
            magnitude=abs(float(change)),
            unit="positions",
            evidence_strength=strength,
            sample_size=1,
            traceability=trace,
        )
    )

    # Large position gain threshold check
    if change >= LARGE_POSITION_GAIN_THRESHOLD:
        large_rule = get_rule(RULE_LARGE_POSITION_GAIN)
        large_id = f"{large_rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{record.driver_id}:none"
        large_trace = InsightTraceability(
            source_metric="position_change",
            source_function="get_grid_vs_finish",
            rule_id=large_rule.rule_id,
            rule_parameters=large_rule.thresholds,
            observed_value=change,
            unit="positions",
            sample_size=1,
            minimum_sample_size=large_rule.min_sample_size,
            sign_convention="position_change >= 5",
            season_year=season_year,
            round_num=round_num,
            driver_id=record.driver_id,
        )
        insights.append(
            Insight(
                insight_id=large_id,
                rule_id=large_rule.rule_id,
                category=InsightCategory.POSITION_CHANGE,
                subject_id=record.driver_id,
                comparison_subject_id=None,
                metric="position_change",
                direction=Direction.GAINED,
                magnitude=float(change),
                unit="positions",
                evidence_strength=strength,
                sample_size=1,
                traceability=large_trace,
            )
        )

    return insights


def evaluate_multi_race_position_change(
    driver_id: str,
    stats: PositionChangeStats,
    *,
    season_year: Optional[int] = None,
) -> Optional[Insight]:
    """Evaluate multi-race position change summary for a driver.

    Args:
        driver_id: Jolpica driver slug.
        stats: PositionChangeStats from statistics layer.
        season_year: Optional season context.

    Returns:
        Insight instance, or None if sample size is insufficient.
    """
    if stats.stats.sample_size < 1 or stats.stats.mean is None:
        return None

    mean_change = stats.stats.mean
    n = stats.stats.sample_size

    if mean_change > 0:
        rule = get_rule(RULE_POSITION_GAIN)
        direction = Direction.GAINED
    elif mean_change < 0:
        rule = get_rule(RULE_POSITION_LOSS)
        direction = Direction.LOST
    else:
        rule = get_rule(RULE_POSITION_MAINTAINED)
        direction = Direction.STABLE

    strength = classify_evidence_strength(n, rule.min_sample_size)
    insight_id = f"{rule.rule_id}:{season_year or 'na'}:all:{driver_id}:none"

    trace = InsightTraceability(
        source_metric="mean_position_change",
        source_function="compute_position_change_stats",
        rule_id=rule.rule_id,
        rule_parameters=rule.thresholds,
        observed_value=mean_change,
        unit="positions",
        sample_size=n,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="mean position change; positive means gained positions on average",
        season_year=season_year,
        driver_id=driver_id,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=InsightCategory.POSITION_CHANGE,
        subject_id=driver_id,
        comparison_subject_id=None,
        metric="mean_position_change",
        direction=direction,
        magnitude=abs(mean_change),
        unit="positions",
        evidence_strength=strength,
        sample_size=n,
        traceability=trace,
    )

"""Deterministic evaluator for lap time and race pace insights."""

from __future__ import annotations

from typing import Optional

from app.insights.rules import (
    RULE_FASTEST_RECORDED_LAP,
    RULE_RACE_PACE_TEAMMATE_ADVANTAGE,
    RULE_RACE_PACE_TEAMMATE_DEFICIT,
    get_rule,
)
from app.insights.types import (
    Direction,
    Insight,
    InsightCategory,
    InsightTraceability,
    classify_evidence_strength,
)
from app.statistics.types import LapTimeStats


def evaluate_fastest_recorded_lap(
    driver_id: str,
    fastest_millis: Optional[int],
    *,
    season_year: Optional[int] = None,
    round_num: Optional[int] = None,
) -> Optional[Insight]:
    """Emit an insight for a driver's fastest recorded lap time.

    Args:
        driver_id: Jolpica driver slug.
        fastest_millis: Fastest recorded lap time in milliseconds.
        season_year: Optional season context.
        round_num: Optional round context.

    Returns:
        Insight instance, or None if fastest_millis is None.
    """
    if fastest_millis is None:
        return None

    rule = get_rule(RULE_FASTEST_RECORDED_LAP)
    strength = classify_evidence_strength(1, rule.min_sample_size)
    insight_id = f"{rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{driver_id}:none"

    trace = InsightTraceability(
        source_metric="fastest_recorded_millis",
        source_function="compute_lap_time_stats",
        rule_id=rule.rule_id,
        rule_parameters=rule.thresholds,
        observed_value=fastest_millis,
        unit="milliseconds",
        sample_size=1,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="minimum recorded lap time in milliseconds",
        season_year=season_year,
        round_num=round_num,
        driver_id=driver_id,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=InsightCategory.RACE_PACE,
        subject_id=driver_id,
        comparison_subject_id=None,
        metric="fastest_recorded_millis",
        direction=Direction.FASTER,
        magnitude=float(fastest_millis),
        unit="milliseconds",
        evidence_strength=strength,
        sample_size=1,
        traceability=trace,
    )


def evaluate_teammate_race_pace(
    driver_a_id: str,
    driver_b_id: str,
    stats_a: LapTimeStats,
    stats_b: LapTimeStats,
    *,
    constructor_id: Optional[str] = None,
    season_year: Optional[int] = None,
    round_num: Optional[int] = None,
) -> Optional[Insight]:
    """Compare average lap times between two teammates in a race.

    Sign convention: delta = mean_a - mean_b (in milliseconds).
    Negative delta means Driver A had lower/faster average lap time.

    Args:
        driver_a_id: Alphabetically first driver slug.
        driver_b_id: Alphabetically second driver slug.
        stats_a: LapTimeStats for driver A.
        stats_b: LapTimeStats for driver B.
        constructor_id: Optional constructor context.
        season_year: Optional season context.
        round_num: Optional round context.

    Returns:
        Insight instance, or None if either driver has insufficient lap data.
    """
    if (
        stats_a.stats.mean is None
        or stats_b.stats.mean is None
        or stats_a.stats.sample_size < 1
        or stats_b.stats.sample_size < 1
    ):
        return None

    delta = stats_a.stats.mean - stats_b.stats.mean
    sample_size = min(stats_a.stats.sample_size, stats_b.stats.sample_size)

    if delta < 0:
        rule = get_rule(RULE_RACE_PACE_TEAMMATE_ADVANTAGE)
        direction = Direction.FASTER
    elif delta > 0:
        rule = get_rule(RULE_RACE_PACE_TEAMMATE_DEFICIT)
        direction = Direction.SLOWER
    else:
        return None  # Perfectly identical pace

    strength = classify_evidence_strength(sample_size, rule.min_sample_size)
    insight_id = f"{rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{driver_a_id}:{driver_b_id}"

    trace = InsightTraceability(
        source_metric="mean_lap_time_millis",
        source_function="compute_lap_time_stats",
        rule_id=rule.rule_id,
        rule_parameters=rule.thresholds,
        observed_value=delta,
        unit="milliseconds",
        sample_size=sample_size,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="delta = mean_a - mean_b; negative means driver_a had faster average pace",
        season_year=season_year,
        round_num=round_num,
        driver_id=driver_a_id,
        constructor_id=constructor_id,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=InsightCategory.RACE_PACE,
        subject_id=driver_a_id,
        comparison_subject_id=driver_b_id,
        metric="pace_delta_millis",
        direction=direction,
        magnitude=abs(float(delta)),
        unit="milliseconds",
        evidence_strength=strength,
        sample_size=sample_size,
        traceability=trace,
    )

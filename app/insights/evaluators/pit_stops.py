"""Deterministic evaluator for pit stop insights."""

from __future__ import annotations

from typing import Optional

from app.insights.rules import (
    FAST_PIT_STOP_THRESHOLD_MILLIS,
    PIT_STOP_HIGH_VARIABILITY_THRESHOLD_MILLIS,
    RULE_FAST_PIT_STOP,
    RULE_PIT_STOP_HIGH_VARIABILITY,
    get_rule,
)
from app.insights.types import (
    Direction,
    Insight,
    InsightCategory,
    InsightTraceability,
    classify_evidence_strength,
)
from app.statistics.types import PitStopStats


def evaluate_fast_pit_stop(
    subject_id: str,
    duration_millis: Optional[int],
    *,
    season_year: Optional[int] = None,
    round_num: Optional[int] = None,
) -> Optional[Insight]:
    """Emit an insight if a pit stop duration was under the fast pit stop threshold.

    Args:
        subject_id: Driver or constructor identifier.
        duration_millis: Pit stop duration in milliseconds.
        season_year: Optional season context.
        round_num: Optional round context.

    Returns:
        Insight instance, or None if duration is missing or does not meet threshold.
    """
    if duration_millis is None or duration_millis >= FAST_PIT_STOP_THRESHOLD_MILLIS:
        return None

    rule = get_rule(RULE_FAST_PIT_STOP)
    strength = classify_evidence_strength(1, rule.min_sample_size)
    insight_id = f"{rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{subject_id}:none"

    trace = InsightTraceability(
        source_metric="duration_millis",
        source_function="compute_pit_stop_stats",
        rule_id=rule.rule_id,
        rule_parameters=rule.thresholds,
        observed_value=duration_millis,
        unit="milliseconds",
        sample_size=1,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="pit stop duration under 25000 ms",
        season_year=season_year,
        round_num=round_num,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=InsightCategory.PIT_STOP,
        subject_id=subject_id,
        comparison_subject_id=None,
        metric="duration_millis",
        direction=Direction.FASTER,
        magnitude=float(duration_millis),
        unit="milliseconds",
        evidence_strength=strength,
        sample_size=1,
        traceability=trace,
    )


def evaluate_pit_stop_variability(
    subject_id: str,
    stats: PitStopStats,
    *,
    season_year: Optional[int] = None,
    round_num: Optional[int] = None,
) -> Optional[Insight]:
    """Emit an insight if pit stop duration standard deviation exceeds threshold.

    Requires minimum sample size n >= 2. Returns None if n < 2 or stddev <= threshold.

    Args:
        subject_id: Driver or constructor identifier.
        stats: PitStopStats containing sample standard deviation.
        season_year: Optional season context.
        round_num: Optional round context.

    Returns:
        Insight instance, or None if sample size < 2 or threshold not exceeded.
    """
    rule = get_rule(RULE_PIT_STOP_HIGH_VARIABILITY)
    n = stats.stats.sample_size

    # Strict sample size requirement
    if n < rule.min_sample_size or stats.stats.stddev is None:
        return None

    stddev_val = stats.stats.stddev
    if stddev_val <= PIT_STOP_HIGH_VARIABILITY_THRESHOLD_MILLIS:
        return None

    strength = classify_evidence_strength(n, rule.min_sample_size)
    insight_id = f"{rule.rule_id}:{season_year or 'na'}:{round_num or 'na'}:{subject_id}:none"

    trace = InsightTraceability(
        source_metric="stddev_duration_millis",
        source_function="compute_pit_stop_stats",
        rule_id=rule.rule_id,
        rule_parameters=rule.thresholds,
        observed_value=stddev_val,
        unit="milliseconds",
        sample_size=n,
        minimum_sample_size=rule.min_sample_size,
        sign_convention=f"sample standard deviation exceeds {PIT_STOP_HIGH_VARIABILITY_THRESHOLD_MILLIS} ms",
        season_year=season_year,
        round_num=round_num,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=InsightCategory.PIT_STOP,
        subject_id=subject_id,
        comparison_subject_id=None,
        metric="stddev_duration_millis",
        direction=Direction.HIGHER,
        magnitude=float(stddev_val),
        unit="milliseconds",
        evidence_strength=strength,
        sample_size=n,
        traceability=trace,
    )

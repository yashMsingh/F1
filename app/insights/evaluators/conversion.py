"""Deterministic evaluators for qualifying-to-race conversion insights (Phase 5B.2A).

Rules evaluated:
- RULE_POLE_TO_WIN_CONVERSION
- RULE_FRONT_ROW_PODIUM_RETENTION
- RULE_GRID_TIER_POSITION_LOSS
- RULE_GRID_TIER_POSITION_GAIN
- RULE_TOP10_CONVERSION_HIGH

All evaluators:
- Are strictly deterministic and reproducible.
- Enforce explicit minimum sample sizes (no insights for N < min_sample_size).
- Exclude DNS and pit-lane starts from grid tiers.
- Generate full audit trail in InsightTraceability.
- Produce descriptive, non-causal explanations.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.insights.rules import (
    GRID_TIER_FRONT_LOSS_THRESHOLD,
    GRID_TIER_LOWER_GAIN_THRESHOLD,
    GRID_TIER_MIN_SAMPLE_SIZE,
    POLE_TO_WIN_MIN_SAMPLE_SIZE,
    RULE_FRONT_ROW_PODIUM_RETENTION,
    RULE_GRID_TIER_POSITION_GAIN,
    RULE_GRID_TIER_POSITION_LOSS,
    RULE_POLE_TO_WIN_CONVERSION,
    RULE_TOP10_CONVERSION_HIGH,
    TOP10_CONVERSION_HIGH_THRESHOLD,
    TOP10_CONVERSION_MIN_SAMPLE_SIZE,
    get_rule,
)
from app.insights.types import (
    Direction,
    Insight,
    InsightCategory,
    InsightTraceability,
)
from app.statistics.conversion import DriverConversionStats

logger = logging.getLogger(__name__)


def _format_rounds_str(rounds_included: list[int]) -> str:
    """Format rounds list into deterministic range string."""
    if not rounds_included:
        return "none"
    min_r = min(rounds_included)
    max_r = max(rounds_included)
    if min_r == max_r:
        return f"round_{min_r}"
    return f"rounds_{min_r}-{max_r}"


def evaluate_pole_to_win_conversion(
    stats: DriverConversionStats,
) -> Optional[Insight]:
    """Evaluate pole-to-win conversion for a driver."""
    p_stats = stats.pole_to_win
    rule = get_rule(RULE_POLE_TO_WIN_CONVERSION)

    if not p_stats.evidence.is_available or p_stats.total_poles < rule.min_sample_size:
        return None

    rate = p_stats.conversion_rate
    direction = Direction.HIGHER if rate >= 50.0 else Direction.LOWER
    r_str = _format_rounds_str(stats.rounds_included)
    insight_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{stats.driver_id}:none"

    explanation = (
        f"Across {p_stats.total_poles} pole starts in {stats.season_year}, {stats.driver_id} "
        f"converted {p_stats.wins_from_pole} into Grand Prix wins ({rate:.1f}% conversion rate)."
    )

    trace = InsightTraceability(
        source_metric=rule.metric,
        source_function="compute_pole_to_win_stats",
        rule_id=rule.rule_id,
        rule_parameters={"min_sample_size": rule.min_sample_size},
        observed_value=rate,
        unit="percentage",
        sample_size=p_stats.total_poles,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="Percentage between 0.0% and 100.0%",
        season_year=stats.season_year,
        driver_id=stats.driver_id,
        constructor_id=stats.constructor_id,
        rounds_included=stats.rounds_included,
        excluded_observations=p_stats.evidence.excluded_observations,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=rule.category,
        subject_id=stats.driver_id,
        comparison_subject_id=None,
        metric=rule.metric,
        direction=direction,
        magnitude=rate,
        unit="percentage",
        evidence_strength=p_stats.evidence.evidence_strength,
        sample_size=p_stats.total_poles,
        traceability=trace,
        explanation=explanation,
    )


def evaluate_front_row_podium_retention(
    stats: DriverConversionStats,
) -> Optional[Insight]:
    """Evaluate front-row podium retention for a driver."""
    fr_stats = stats.front_row
    rule = get_rule(RULE_FRONT_ROW_PODIUM_RETENTION)

    if not fr_stats.evidence.is_available or fr_stats.front_row_starts < rule.min_sample_size:
        return None

    rate = fr_stats.retention_rate
    direction = Direction.HIGHER if rate >= 50.0 else Direction.LOWER
    r_str = _format_rounds_str(stats.rounds_included)
    insight_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{stats.driver_id}:none"

    explanation = (
        f"Across {fr_stats.front_row_starts} front-row starts in {stats.season_year}, {stats.driver_id} "
        f"retained {fr_stats.front_row_podiums} as podium finishes ({rate:.1f}% podium retention rate)."
    )

    trace = InsightTraceability(
        source_metric=rule.metric,
        source_function="compute_front_row_stats",
        rule_id=rule.rule_id,
        rule_parameters={"min_sample_size": rule.min_sample_size},
        observed_value=rate,
        unit="percentage",
        sample_size=fr_stats.front_row_starts,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="Percentage between 0.0% and 100.0%",
        season_year=stats.season_year,
        driver_id=stats.driver_id,
        constructor_id=stats.constructor_id,
        rounds_included=stats.rounds_included,
        excluded_observations=fr_stats.evidence.excluded_observations,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=rule.category,
        subject_id=stats.driver_id,
        comparison_subject_id=None,
        metric=rule.metric,
        direction=direction,
        magnitude=rate,
        unit="percentage",
        evidence_strength=fr_stats.evidence.evidence_strength,
        sample_size=fr_stats.front_row_starts,
        traceability=trace,
        explanation=explanation,
    )


def evaluate_grid_tier_position_loss(
    stats: DriverConversionStats,
) -> Optional[Insight]:
    """Evaluate position loss when starting from front tier (P1-P4)."""
    gt = stats.grid_tiers.get("front")
    rule = get_rule(RULE_GRID_TIER_POSITION_LOSS)

    if gt is None or not gt.evidence.is_available or gt.eligible_starts < rule.min_sample_size:
        return None

    if gt.avg_position_delta is None or gt.avg_position_delta > GRID_TIER_FRONT_LOSS_THRESHOLD:
        return None

    r_str = _format_rounds_str(stats.rounds_included)
    insight_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{stats.driver_id}:front"

    explanation = (
        f"When starting from the front tier (P1-P4) across {gt.eligible_starts} races in {stats.season_year}, "
        f"{stats.driver_id} experienced an average position change of {gt.avg_position_delta:+.2f} "
        f"positions across {gt.classified_finishes} classified finishes (net {gt.total_positions_gained:+d} positions)."
    )

    trace = InsightTraceability(
        source_metric=rule.metric,
        source_function="compute_grid_tier_stats",
        rule_id=rule.rule_id,
        rule_parameters={
            "loss_threshold": GRID_TIER_FRONT_LOSS_THRESHOLD,
            "min_sample_size": rule.min_sample_size,
        },
        observed_value=gt.avg_position_delta,
        unit="positions",
        sample_size=gt.eligible_starts,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="Positive means positions gained; negative means positions lost",
        season_year=stats.season_year,
        driver_id=stats.driver_id,
        constructor_id=stats.constructor_id,
        rounds_included=stats.rounds_included,
        excluded_observations=gt.non_classified_results,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=rule.category,
        subject_id=stats.driver_id,
        comparison_subject_id=None,
        metric=rule.metric,
        direction=Direction.LOST,
        magnitude=abs(gt.avg_position_delta),
        unit="positions",
        evidence_strength=gt.evidence.evidence_strength,
        sample_size=gt.eligible_starts,
        traceability=trace,
        explanation=explanation,
    )


def evaluate_grid_tier_position_gain(
    stats: DriverConversionStats,
) -> Optional[Insight]:
    """Evaluate position gain when starting from lower tier (P11-P20)."""
    gt = stats.grid_tiers.get("lower")
    rule = get_rule(RULE_GRID_TIER_POSITION_GAIN)

    if gt is None or not gt.evidence.is_available or gt.eligible_starts < rule.min_sample_size:
        return None

    if gt.avg_position_delta is None or gt.avg_position_delta < GRID_TIER_LOWER_GAIN_THRESHOLD:
        return None

    r_str = _format_rounds_str(stats.rounds_included)
    insight_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{stats.driver_id}:lower"

    explanation = (
        f"When starting from the lower tier (P11-P20) across {gt.eligible_starts} races in {stats.season_year}, "
        f"{stats.driver_id} achieved an average position gain of {gt.avg_position_delta:+.2f} "
        f"positions across {gt.classified_finishes} classified finishes (net {gt.total_positions_gained:+d} positions)."
    )

    trace = InsightTraceability(
        source_metric=rule.metric,
        source_function="compute_grid_tier_stats",
        rule_id=rule.rule_id,
        rule_parameters={
            "gain_threshold": GRID_TIER_LOWER_GAIN_THRESHOLD,
            "min_sample_size": rule.min_sample_size,
        },
        observed_value=gt.avg_position_delta,
        unit="positions",
        sample_size=gt.eligible_starts,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="Positive means positions gained; negative means positions lost",
        season_year=stats.season_year,
        driver_id=stats.driver_id,
        constructor_id=stats.constructor_id,
        rounds_included=stats.rounds_included,
        excluded_observations=gt.non_classified_results,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=rule.category,
        subject_id=stats.driver_id,
        comparison_subject_id=None,
        metric=rule.metric,
        direction=Direction.GAINED,
        magnitude=gt.avg_position_delta,
        unit="positions",
        evidence_strength=gt.evidence.evidence_strength,
        sample_size=gt.eligible_starts,
        traceability=trace,
        explanation=explanation,
    )


def evaluate_top10_conversion_high(
    stats: DriverConversionStats,
) -> Optional[Insight]:
    """Evaluate high top-10 points conversion rate (>= 90%)."""
    t10 = stats.top10_conversion
    rule = get_rule(RULE_TOP10_CONVERSION_HIGH)

    if not t10.evidence.is_available or t10.top10_starts < rule.min_sample_size:
        return None

    if t10.conversion_rate < TOP10_CONVERSION_HIGH_THRESHOLD:
        return None

    r_str = _format_rounds_str(stats.rounds_included)
    insight_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{stats.driver_id}:none"

    explanation = (
        f"Across {t10.top10_starts} top-10 grid starts in {stats.season_year}, {stats.driver_id} "
        f"converted {t10.top10_conversions} into classified top-10 finishes ({t10.conversion_rate:.1f}% conversion rate)."
    )

    trace = InsightTraceability(
        source_metric=rule.metric,
        source_function="compute_top10_conversion_stats",
        rule_id=rule.rule_id,
        rule_parameters={
            "conversion_threshold": TOP10_CONVERSION_HIGH_THRESHOLD,
            "min_sample_size": rule.min_sample_size,
        },
        observed_value=t10.conversion_rate,
        unit="percentage",
        sample_size=t10.top10_starts,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="Percentage between 0.0% and 100.0%",
        season_year=stats.season_year,
        driver_id=stats.driver_id,
        constructor_id=stats.constructor_id,
        rounds_included=stats.rounds_included,
        excluded_observations=t10.evidence.excluded_observations,
    )

    return Insight(
        insight_id=insight_id,
        rule_id=rule.rule_id,
        category=rule.category,
        subject_id=stats.driver_id,
        comparison_subject_id=None,
        metric=rule.metric,
        direction=Direction.HIGHER,
        magnitude=t10.conversion_rate,
        unit="percentage",
        evidence_strength=t10.evidence.evidence_strength,
        sample_size=t10.top10_starts,
        traceability=trace,
        explanation=explanation,
    )


def evaluate_driver_conversion_insights(
    stats: DriverConversionStats,
) -> list[Insight]:
    """Generate all deterministic conversion insights for a driver.

    Args:
        stats: DriverConversionStats instance.

    Returns:
        List of generated Insight instances.
    """
    insights: list[Insight] = []

    p_ins = evaluate_pole_to_win_conversion(stats)
    if p_ins is not None:
        insights.append(p_ins)

    fr_ins = evaluate_front_row_podium_retention(stats)
    if fr_ins is not None:
        insights.append(fr_ins)

    ftl_ins = evaluate_grid_tier_position_loss(stats)
    if ftl_ins is not None:
        insights.append(ftl_ins)

    ltg_ins = evaluate_grid_tier_position_gain(stats)
    if ltg_ins is not None:
        insights.append(ltg_ins)

    t10_ins = evaluate_top10_conversion_high(stats)
    if t10_ins is not None:
        insights.append(t10_ins)

    return insights

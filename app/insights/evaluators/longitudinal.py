"""Deterministic evaluators for longitudinal statistical insights.

Consumes Phase 3C statistical models (DriverLongitudinalStats, DriverFormSummary,
TeammateH2HStatistics) and Phase 3B analytical trajectories (ConstructorTrajectoryItem).

Rules:
- Strictly deterministic, evidence-backed, and reproducible.
- Zero external database queries, zero network calls, zero LLM dependencies.
- Minimum sample size safeguards strictly enforced.
- Conservative thresholds; no global driver ratings or composite scores.
- Non-causal, descriptive human-readable explanations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Sequence

from app.analytics.types import ConstructorTrajectoryItem
from app.insights.rules import (
    LONGITUDINAL_CONSTRUCTOR_PODIUM_RATE_THRESHOLD,
    LONGITUDINAL_FINISH_CONSISTENCY_STDDEV_THRESHOLD,
    LONGITUDINAL_GRID_CONSISTENCY_STDDEV_THRESHOLD,
    LONGITUDINAL_POINTS_PER_ROUND_THRESHOLD,
    LONGITUDINAL_POINTS_PER_START_THRESHOLD,
    LONGITUDINAL_POSITION_GAIN_PATTERN_THRESHOLD,
    LONGITUDINAL_POSITION_LOSS_PATTERN_THRESHOLD,
    LONGITUDINAL_RECENT_FORM_FINISH_THRESHOLD,
    LONGITUDINAL_RECENT_FORM_WINDOW_SIZE,
    LONGITUDINAL_TEAMMATE_POINTS_DIFF_THRESHOLD,
    LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD,
    RULE_LONGITUDINAL_CONSTRUCTOR_TRAJECTORY,
    RULE_LONGITUDINAL_FINISH_CONSISTENCY,
    RULE_LONGITUDINAL_POINTS_PER_ROUND,
    RULE_LONGITUDINAL_POINTS_PER_START,
    RULE_LONGITUDINAL_POSITION_GAIN_PATTERN,
    RULE_LONGITUDINAL_POSITION_LOSS_PATTERN,
    RULE_LONGITUDINAL_QUALIFYING_CONSISTENCY,
    RULE_LONGITUDINAL_RECENT_FORM,
    RULE_LONGITUDINAL_TEAMMATE_POINTS_H2H,
    RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H,
    RULE_LONGITUDINAL_TEAMMATE_RACE_H2H,
    get_rule,
)
from app.insights.types import (
    Direction,
    EvidenceStrength,
    Insight,
    InsightCategory,
    InsightTraceability,
    classify_evidence_strength,
)
from app.statistics.types import (
    DriverFormSummary,
    DriverLongitudinalStats,
    TeammateH2HStatistics,
)


def evaluate_longitudinal_qualifying_consistency(
    stats: DriverLongitudinalStats,
    driver_id: Optional[str] = None,
) -> Optional[Insight]:
    """Evaluate longitudinal qualifying starting grid consistency for a driver.

    Triggers when standard deviation of starting grid positions is <= 1.5
    across at least 3 valid grid starts. Pit-lane starts are excluded from stats.

    Args:
        stats: DriverLongitudinalStats instance from Phase 3C.
        driver_id: Optional explicit driver slug override.

    Returns:
        Insight instance, or None if conditions/thresholds not met.
    """
    drv = driver_id or stats.driver_id
    if not drv:
        return None

    n = stats.grid_position.sample_size
    stddev = stats.grid_position.stddev
    mean_pos = stats.grid_position.mean
    rule = get_rule(RULE_LONGITUDINAL_QUALIFYING_CONSISTENCY)

    if n < rule.min_sample_size or stddev is None or mean_pos is None:
        return None

    if stddev <= LONGITUDINAL_GRID_CONSISTENCY_STDDEV_THRESHOLD:
        strength = classify_evidence_strength(n, rule.min_sample_size)
        rounds_inc = stats.evidence.rounds_included
        r_str = f"rounds_{min(rounds_inc)}-{max(rounds_inc)}" if rounds_inc else "all"
        ins_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{drv}:none"

        explanation = (
            f"Across {n} qualifying sessions in {stats.season_year}, {drv} achieved high grid "
            f"consistency with a standard deviation of {stddev:.2f} positions (mean grid P{mean_pos:.1f})."
        )

        trace = InsightTraceability(
            source_metric="grid_position_stddev",
            source_function="compute_driver_longitudinal_stats",
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=round(stddev, 3),
            unit="positions",
            sample_size=n,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="lower standard deviation indicates higher grid position consistency",
            season_year=stats.season_year,
            driver_id=drv,
            rounds_included=rounds_inc,
            excluded_observations=stats.evidence.excluded_observations,
        )

        return Insight(
            insight_id=ins_id,
            rule_id=rule.rule_id,
            category=rule.category,
            subject_id=drv,
            comparison_subject_id=None,
            metric="grid_position_stddev",
            direction=Direction.STABLE,
            magnitude=round(stddev, 3),
            unit="positions",
            evidence_strength=strength,
            sample_size=n,
            traceability=trace,
            explanation=explanation,
        )

    return None


def evaluate_longitudinal_finish_consistency(
    stats: DriverLongitudinalStats,
    driver_id: Optional[str] = None,
) -> Optional[Insight]:
    """Evaluate longitudinal race finish position consistency for a driver.

    Triggers when standard deviation of classified finishing positions is <= 1.5
    across at least 3 classified finishes. Non-finishes (DNFs) are strictly excluded.

    Args:
        stats: DriverLongitudinalStats instance from Phase 3C.
        driver_id: Optional explicit driver slug override.

    Returns:
        Insight instance, or None if conditions/thresholds not met.
    """
    drv = driver_id or stats.driver_id
    if not drv:
        return None

    n = stats.finish_position.sample_size
    stddev = stats.finish_position.stddev
    mean_pos = stats.finish_position.mean
    rule = get_rule(RULE_LONGITUDINAL_FINISH_CONSISTENCY)

    if n < rule.min_sample_size or stddev is None or mean_pos is None:
        return None

    if stddev <= LONGITUDINAL_FINISH_CONSISTENCY_STDDEV_THRESHOLD:
        strength = classify_evidence_strength(n, rule.min_sample_size)
        rounds_inc = stats.evidence.rounds_included
        r_str = f"rounds_{min(rounds_inc)}-{max(rounds_inc)}" if rounds_inc else "all"
        ins_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{drv}:none"

        explanation = (
            f"Across {n} classified finishes in {stats.season_year}, {drv} achieved high finish "
            f"consistency with a standard deviation of {stddev:.2f} positions (mean finish P{mean_pos:.1f})."
        )

        trace = InsightTraceability(
            source_metric="finish_position_stddev",
            source_function="compute_driver_longitudinal_stats",
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=round(stddev, 3),
            unit="positions",
            sample_size=n,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="lower standard deviation indicates higher finish position consistency; DNFs excluded",
            season_year=stats.season_year,
            driver_id=drv,
            rounds_included=rounds_inc,
            excluded_observations=stats.evidence.total_races - n,
        )

        return Insight(
            insight_id=ins_id,
            rule_id=rule.rule_id,
            category=rule.category,
            subject_id=drv,
            comparison_subject_id=None,
            metric="finish_position_stddev",
            direction=Direction.STABLE,
            magnitude=round(stddev, 3),
            unit="positions",
            evidence_strength=strength,
            sample_size=n,
            traceability=trace,
            explanation=explanation,
        )

    return None


def evaluate_longitudinal_position_change_pattern(
    stats: DriverLongitudinalStats,
    driver_id: Optional[str] = None,
) -> list[Insight]:
    """Evaluate multi-race position gain or loss patterns for a driver.

    Requires at least 3 valid observations (valid grid start > 0 and classified finish).
    DNFs and pit starts are excluded.

    Args:
        stats: DriverLongitudinalStats instance from Phase 3C.
        driver_id: Optional explicit driver slug override.

    Returns:
        List of generated insights (empty, or contains gain/loss pattern).
    """
    drv = driver_id or stats.driver_id
    if not drv:
        return []

    n = stats.position_change.quality.valid_observations
    mean_chg = stats.position_change.stats.mean

    if n < 3 or mean_chg is None:
        return []

    rounds_inc = stats.evidence.rounds_included
    r_str = f"rounds_{min(rounds_inc)}-{max(rounds_inc)}" if rounds_inc else "all"

    # Gain pattern
    if mean_chg >= LONGITUDINAL_POSITION_GAIN_PATTERN_THRESHOLD:
        rule = get_rule(RULE_LONGITUDINAL_POSITION_GAIN_PATTERN)
        strength = classify_evidence_strength(n, rule.min_sample_size)
        ins_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{drv}:none"

        explanation = (
            f"Across {n} valid races in {stats.season_year}, {drv} gained an average of "
            f"{mean_chg:.1f} positions from starting grid to classified finish."
        )

        trace = InsightTraceability(
            source_metric="mean_position_change",
            source_function="compute_driver_longitudinal_stats",
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=round(mean_chg, 2),
            unit="positions",
            sample_size=n,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="positive mean indicates positions gained from grid to finish",
            season_year=stats.season_year,
            driver_id=drv,
            rounds_included=rounds_inc,
            excluded_observations=stats.position_change.quality.excluded_observations,
        )

        return [
            Insight(
                insight_id=ins_id,
                rule_id=rule.rule_id,
                category=rule.category,
                subject_id=drv,
                comparison_subject_id=None,
                metric="mean_position_change",
                direction=Direction.GAINED,
                magnitude=round(abs(mean_chg), 2),
                unit="positions",
                evidence_strength=strength,
                sample_size=n,
                traceability=trace,
                explanation=explanation,
            )
        ]

    # Loss pattern
    if mean_chg <= LONGITUDINAL_POSITION_LOSS_PATTERN_THRESHOLD:
        rule = get_rule(RULE_LONGITUDINAL_POSITION_LOSS_PATTERN)
        strength = classify_evidence_strength(n, rule.min_sample_size)
        ins_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{drv}:none"

        explanation = (
            f"Across {n} valid races in {stats.season_year}, {drv} lost an average of "
            f"{abs(mean_chg):.1f} positions from starting grid to classified finish."
        )

        trace = InsightTraceability(
            source_metric="mean_position_change",
            source_function="compute_driver_longitudinal_stats",
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=round(mean_chg, 2),
            unit="positions",
            sample_size=n,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="negative mean indicates positions lost from grid to finish",
            season_year=stats.season_year,
            driver_id=drv,
            rounds_included=rounds_inc,
            excluded_observations=stats.position_change.quality.excluded_observations,
        )

        return [
            Insight(
                insight_id=ins_id,
                rule_id=rule.rule_id,
                category=rule.category,
                subject_id=drv,
                comparison_subject_id=None,
                metric="mean_position_change",
                direction=Direction.LOST,
                magnitude=round(abs(mean_chg), 2),
                unit="positions",
                evidence_strength=strength,
                sample_size=n,
                traceability=trace,
                explanation=explanation,
            )
        ]

    return []


def evaluate_longitudinal_points_per_start(
    stats: DriverLongitudinalStats,
    driver_id: Optional[str] = None,
) -> Optional[Insight]:
    """Evaluate Grand Prix points-per-start rate for a driver.

    Denominator: Grand Prix race starts only (excludes Sprint points and DNS).

    Args:
        stats: DriverLongitudinalStats instance from Phase 3C.
        driver_id: Optional explicit driver slug override.

    Returns:
        Insight instance, or None if conditions/thresholds not met.
    """
    drv = driver_id or stats.driver_id
    if not drv:
        return None

    gp_starts = stats.points.grand_prix_starts
    pp_start = stats.points.points_per_gp_start
    rule = get_rule(RULE_LONGITUDINAL_POINTS_PER_START)

    if gp_starts < rule.min_sample_size or pp_start is None:
        return None

    if pp_start >= LONGITUDINAL_POINTS_PER_START_THRESHOLD:
        strength = classify_evidence_strength(gp_starts, rule.min_sample_size)
        rounds_inc = stats.evidence.rounds_included
        r_str = f"rounds_{min(rounds_inc)}-{max(rounds_inc)}" if rounds_inc else "all"
        ins_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{drv}:none"
        tot_race = stats.points.total_race_points

        explanation = (
            f"Across {gp_starts} Grand Prix starts in {stats.season_year}, {drv} scored {tot_race} "
            f"race points, averaging {pp_start:.2f} points per start (excluding sprint sessions)."
        )

        trace = InsightTraceability(
            source_metric="points_per_gp_start",
            source_function="compute_driver_points_stats",
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=round(pp_start, 2),
            unit="points",
            sample_size=gp_starts,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="total_race_points / grand_prix_starts; sprint points excluded",
            season_year=stats.season_year,
            driver_id=drv,
            rounds_included=rounds_inc,
            excluded_observations=stats.evidence.total_races - gp_starts,
        )

        return Insight(
            insight_id=ins_id,
            rule_id=rule.rule_id,
            category=rule.category,
            subject_id=drv,
            comparison_subject_id=None,
            metric="points_per_gp_start",
            direction=Direction.HIGHER,
            magnitude=round(pp_start, 2),
            unit="points",
            evidence_strength=strength,
            sample_size=gp_starts,
            traceability=trace,
            explanation=explanation,
        )

    return None


def evaluate_longitudinal_points_per_round(
    stats: DriverLongitudinalStats,
    driver_id: Optional[str] = None,
) -> Optional[Insight]:
    """Evaluate championship points per round rate for a driver (includes sprints).

    Denominator: All championship rounds entered.

    Args:
        stats: DriverLongitudinalStats instance from Phase 3C.
        driver_id: Optional explicit driver slug override.

    Returns:
        Insight instance, or None if conditions/thresholds not met.
    """
    drv = driver_id or stats.driver_id
    if not drv:
        return None

    rounds = stats.points.rounds_entered
    pp_round = stats.points.points_per_round_total
    rule = get_rule(RULE_LONGITUDINAL_POINTS_PER_ROUND)

    if rounds < rule.min_sample_size or pp_round is None:
        return None

    if pp_round >= LONGITUDINAL_POINTS_PER_ROUND_THRESHOLD:
        strength = classify_evidence_strength(rounds, rule.min_sample_size)
        rounds_inc = stats.evidence.rounds_included
        r_str = f"rounds_{min(rounds_inc)}-{max(rounds_inc)}" if rounds_inc else "all"
        ins_id = f"{rule.rule_id}:{stats.season_year}:{r_str}:{drv}:none"
        tot_champ = stats.points.total_championship_points
        tot_race = stats.points.total_race_points
        tot_sprint = stats.points.total_sprint_points

        explanation = (
            f"Across {rounds} championship rounds in {stats.season_year}, {drv} scored {tot_champ} "
            f"total points ({tot_race} race, {tot_sprint} sprint), averaging {pp_round:.2f} points per round."
        )

        trace = InsightTraceability(
            source_metric="points_per_round_total",
            source_function="compute_driver_points_stats",
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=round(pp_round, 2),
            unit="points",
            sample_size=rounds,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="total_championship_points / rounds_entered; includes sprint and race points",
            season_year=stats.season_year,
            driver_id=drv,
            rounds_included=rounds_inc,
            excluded_observations=0,
        )

        return Insight(
            insight_id=ins_id,
            rule_id=rule.rule_id,
            category=rule.category,
            subject_id=drv,
            comparison_subject_id=None,
            metric="points_per_round_total",
            direction=Direction.HIGHER,
            magnitude=round(pp_round, 2),
            unit="points",
            evidence_strength=strength,
            sample_size=rounds,
            traceability=trace,
            explanation=explanation,
        )

    return None


def evaluate_longitudinal_recent_form(
    form_summary: DriverFormSummary,
    driver_id: Optional[str] = None,
    window_size: int = LONGITUDINAL_RECENT_FORM_WINDOW_SIZE,
) -> Optional[Insight]:
    """Evaluate recent finishing form over the latest trailing rolling window.

    Strictly descriptive: states the observed average finish across valid finishes.
    Contains zero predictive claims or ratings.

    Args:
        form_summary: DriverFormSummary from Phase 3C.
        driver_id: Optional explicit driver slug override.
        window_size: Rolling window size (default: 3).

    Returns:
        Insight instance, or None if conditions/thresholds not met.
    """
    drv = driver_id or form_summary.driver_id
    if not drv:
        return None

    # Find the most recent finish_position rolling window for the requested window size
    finish_windows = [
        w
        for w in form_summary.rolling_windows
        if w.metric_name == "finish_position" and w.window_size_requested == window_size
    ]
    if not finish_windows:
        return None

    # Most recent window corresponds to highest round number
    latest_window = max(finish_windows, key=lambda w: w.round)
    rule = get_rule(RULE_LONGITUDINAL_RECENT_FORM)

    if latest_window.valid_observations < rule.min_sample_size or latest_window.mean is None:
        return None

    if latest_window.mean <= LONGITUDINAL_RECENT_FORM_FINISH_THRESHOLD:
        strength = classify_evidence_strength(latest_window.valid_observations, rule.min_sample_size)
        r_start = min(latest_window.rounds_included) if latest_window.rounds_included else latest_window.round
        r_end = max(latest_window.rounds_included) if latest_window.rounds_included else latest_window.round
        ins_id = f"{rule.rule_id}:{form_summary.season_year}:w{window_size}_r{latest_window.round}:{drv}:none"

        explanation = (
            f"Over the most recent {window_size} rounds (R{r_start}-R{r_end}), {drv} recorded an average "
            f"finish of P{latest_window.mean:.1f} across {latest_window.valid_observations} valid finishes."
        )

        trace = InsightTraceability(
            source_metric="rolling_mean_finish",
            source_function="compute_rolling_window_stats",
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=round(latest_window.mean, 2),
            unit="positions",
            sample_size=latest_window.valid_observations,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="mean finishing position over trailing window; DNFs excluded",
            season_year=form_summary.season_year,
            round_num=latest_window.round,
            driver_id=drv,
            rounds_included=latest_window.rounds_included,
            excluded_observations=len(latest_window.rounds_included) - latest_window.valid_observations,
        )

        return Insight(
            insight_id=ins_id,
            rule_id=rule.rule_id,
            category=rule.category,
            subject_id=drv,
            comparison_subject_id=None,
            metric="rolling_mean_finish",
            direction=Direction.HIGHER,
            magnitude=round(latest_window.mean, 2),
            unit="positions",
            evidence_strength=strength,
            sample_size=latest_window.valid_observations,
            traceability=trace,
            explanation=explanation,
        )

    return None


def evaluate_driver_longitudinal_insights(
    stats: DriverLongitudinalStats,
    form_summary: Optional[DriverFormSummary] = None,
    driver_id: Optional[str] = None,
) -> list[Insight]:
    """Aggregate all longitudinal deterministic insights for a single driver profile.

    Args:
        stats: DriverLongitudinalStats instance.
        form_summary: Optional DriverFormSummary instance.
        driver_id: Optional explicit driver slug override.

    Returns:
        List of generated deterministic insights.
    """
    insights: list[Insight] = []

    # 1. Starting grid consistency
    q_ins = evaluate_longitudinal_qualifying_consistency(stats, driver_id=driver_id)
    if q_ins is not None:
        insights.append(q_ins)

    # 2. Race finish consistency
    f_ins = evaluate_longitudinal_finish_consistency(stats, driver_id=driver_id)
    if f_ins is not None:
        insights.append(f_ins)

    # 3. Position change patterns
    pos_insights = evaluate_longitudinal_position_change_pattern(stats, driver_id=driver_id)
    insights.extend(pos_insights)

    # 4. Points per GP start
    pts_start_ins = evaluate_longitudinal_points_per_start(stats, driver_id=driver_id)
    if pts_start_ins is not None:
        insights.append(pts_start_ins)

    # 5. Points per round total
    pts_round_ins = evaluate_longitudinal_points_per_round(stats, driver_id=driver_id)
    if pts_round_ins is not None:
        insights.append(pts_round_ins)

    # 6. Recent form
    if form_summary is not None:
        form_ins = evaluate_longitudinal_recent_form(form_summary, driver_id=driver_id)
        if form_ins is not None:
            insights.append(form_ins)

    return insights


def evaluate_longitudinal_teammate_h2h(
    h2h: TeammateH2HStatistics,
    season_year: int,
) -> list[Insight]:
    """Evaluate multi-race teammate head-to-head performance across independent dimensions.

    Evaluates 3 distinct, non-collapsed dimensions:
    1. Qualifying dimension (win rate >= 70% in comparable sessions)
    2. Race finish dimension (win rate >= 70% in two-car classified finishes)
    3. Points dimension (difference >= 15.0 championship points)

    Mid-season substitutions are partitioned by (constructor_id, driver_a_id, driver_b_id).
    Pairs with fewer than 3 comparable/shared rounds emit zero insights.

    Args:
        h2h: TeammateH2HStatistics instance from Phase 3C.
        season_year: Championship season year context.

    Returns:
        List of independent teammate H2H insights.
    """
    insights: list[Insight] = []
    con_id = h2h.constructor_id
    drv_a = h2h.driver_a_id
    drv_b = h2h.driver_b_id

    # ── Dimension 1: Qualifying H2H ──
    q_rule = get_rule(RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H)
    q_comp = h2h.qualifying_comparable_rounds
    if q_comp >= q_rule.min_sample_size:
        strength = classify_evidence_strength(q_comp, q_rule.min_sample_size)
        rounds_inc = h2h.qualifying_evidence.rounds_included

        # Check driver A advantage
        if h2h.qualifying_win_rate_a is not None and h2h.qualifying_win_rate_a >= LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD:
            rate = h2h.qualifying_win_rate_a
            wins_w, wins_l = h2h.qualifying_wins_a, h2h.qualifying_wins_b
            mean_delta = h2h.qualifying_delta_stats.mean  # negative means A faster
            delta_str = f" with an average delta of {abs(mean_delta):.1f} ms" if mean_delta is not None else ""

            explanation = (
                f"Across {q_comp} comparable qualifying sessions for {con_id} in {season_year}, "
                f"{drv_a} out-qualified {drv_b} {wins_w}-{wins_l} ({rate:.0%}){delta_str}."
            )

            trace = InsightTraceability(
                source_metric="qualifying_win_rate",
                source_function="compute_longitudinal_teammate_h2h_stats",
                rule_id=q_rule.rule_id,
                rule_parameters=q_rule.thresholds,
                observed_value=round(rate, 3),
                unit="win_rate",
                sample_size=q_comp,
                minimum_sample_size=q_rule.min_sample_size,
                sign_convention="qualifying_wins / comparable_qualifying_rounds",
                season_year=season_year,
                driver_id=drv_a,
                constructor_id=con_id,
                rounds_included=rounds_inc,
                excluded_observations=h2h.rounds_together - q_comp,
            )

            insights.append(
                Insight(
                    insight_id=f"{q_rule.rule_id}:{season_year}:{con_id}:{drv_a}:{drv_b}",
                    rule_id=q_rule.rule_id,
                    category=q_rule.category,
                    subject_id=drv_a,
                    comparison_subject_id=drv_b,
                    metric="qualifying_win_rate",
                    direction=Direction.FASTER,
                    magnitude=round(rate, 3),
                    unit="win_rate",
                    evidence_strength=strength,
                    sample_size=q_comp,
                    traceability=trace,
                    explanation=explanation,
                )
            )

        # Check driver B advantage
        elif h2h.qualifying_win_rate_b is not None and h2h.qualifying_win_rate_b >= LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD:
            rate = h2h.qualifying_win_rate_b
            wins_w, wins_l = h2h.qualifying_wins_b, h2h.qualifying_wins_a
            mean_delta = -h2h.qualifying_delta_stats.mean if h2h.qualifying_delta_stats.mean is not None else None
            delta_str = f" with an average delta of {abs(mean_delta):.1f} ms" if mean_delta is not None else ""

            explanation = (
                f"Across {q_comp} comparable qualifying sessions for {con_id} in {season_year}, "
                f"{drv_b} out-qualified {drv_a} {wins_w}-{wins_l} ({rate:.0%}){delta_str}."
            )

            trace = InsightTraceability(
                source_metric="qualifying_win_rate",
                source_function="compute_longitudinal_teammate_h2h_stats",
                rule_id=q_rule.rule_id,
                rule_parameters=q_rule.thresholds,
                observed_value=round(rate, 3),
                unit="win_rate",
                sample_size=q_comp,
                minimum_sample_size=q_rule.min_sample_size,
                sign_convention="qualifying_wins / comparable_qualifying_rounds",
                season_year=season_year,
                driver_id=drv_b,
                constructor_id=con_id,
                rounds_included=rounds_inc,
                excluded_observations=h2h.rounds_together - q_comp,
            )

            insights.append(
                Insight(
                    insight_id=f"{q_rule.rule_id}:{season_year}:{con_id}:{drv_b}:{drv_a}",
                    rule_id=q_rule.rule_id,
                    category=q_rule.category,
                    subject_id=drv_b,
                    comparison_subject_id=drv_a,
                    metric="qualifying_win_rate",
                    direction=Direction.FASTER,
                    magnitude=round(rate, 3),
                    unit="win_rate",
                    evidence_strength=strength,
                    sample_size=q_comp,
                    traceability=trace,
                    explanation=explanation,
                )
            )

    # ── Dimension 2: Race Finish H2H ──
    r_rule = get_rule(RULE_LONGITUDINAL_TEAMMATE_RACE_H2H)
    r_comp = h2h.race_comparable_rounds
    if r_comp >= r_rule.min_sample_size:
        strength = classify_evidence_strength(r_comp, r_rule.min_sample_size)
        rounds_inc = h2h.race_evidence.rounds_included

        # Check driver A advantage
        if h2h.race_win_rate_a is not None and h2h.race_win_rate_a >= LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD:
            rate = h2h.race_win_rate_a
            wins_w, wins_l = h2h.race_wins_a, h2h.race_wins_b

            explanation = (
                f"Across {r_comp} comparable two-car finishes for {con_id} in {season_year}, "
                f"{drv_a} finished ahead of {drv_b} {wins_w}-{wins_l} ({rate:.0%})."
            )

            trace = InsightTraceability(
                source_metric="race_win_rate",
                source_function="compute_longitudinal_teammate_h2h_stats",
                rule_id=r_rule.rule_id,
                rule_parameters=r_rule.thresholds,
                observed_value=round(rate, 3),
                unit="win_rate",
                sample_size=r_comp,
                minimum_sample_size=r_rule.min_sample_size,
                sign_convention="race_wins / comparable_finish_rounds; both cars classified",
                season_year=season_year,
                driver_id=drv_a,
                constructor_id=con_id,
                rounds_included=rounds_inc,
                excluded_observations=h2h.rounds_together - r_comp,
            )

            insights.append(
                Insight(
                    insight_id=f"{r_rule.rule_id}:{season_year}:{con_id}:{drv_a}:{drv_b}",
                    rule_id=r_rule.rule_id,
                    category=r_rule.category,
                    subject_id=drv_a,
                    comparison_subject_id=drv_b,
                    metric="race_win_rate",
                    direction=Direction.HIGHER,
                    magnitude=round(rate, 3),
                    unit="win_rate",
                    evidence_strength=strength,
                    sample_size=r_comp,
                    traceability=trace,
                    explanation=explanation,
                )
            )

        # Check driver B advantage
        elif h2h.race_win_rate_b is not None and h2h.race_win_rate_b >= LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD:
            rate = h2h.race_win_rate_b
            wins_w, wins_l = h2h.race_wins_b, h2h.race_wins_a

            explanation = (
                f"Across {r_comp} comparable two-car finishes for {con_id} in {season_year}, "
                f"{drv_b} finished ahead of {drv_a} {wins_w}-{wins_l} ({rate:.0%})."
            )

            trace = InsightTraceability(
                source_metric="race_win_rate",
                source_function="compute_longitudinal_teammate_h2h_stats",
                rule_id=r_rule.rule_id,
                rule_parameters=r_rule.thresholds,
                observed_value=round(rate, 3),
                unit="win_rate",
                sample_size=r_comp,
                minimum_sample_size=r_rule.min_sample_size,
                sign_convention="race_wins / comparable_finish_rounds; both cars classified",
                season_year=season_year,
                driver_id=drv_b,
                constructor_id=con_id,
                rounds_included=rounds_inc,
                excluded_observations=h2h.rounds_together - r_comp,
            )

            insights.append(
                Insight(
                    insight_id=f"{r_rule.rule_id}:{season_year}:{con_id}:{drv_b}:{drv_a}",
                    rule_id=r_rule.rule_id,
                    category=r_rule.category,
                    subject_id=drv_b,
                    comparison_subject_id=drv_a,
                    metric="race_win_rate",
                    direction=Direction.HIGHER,
                    magnitude=round(rate, 3),
                    unit="win_rate",
                    evidence_strength=strength,
                    sample_size=r_comp,
                    traceability=trace,
                    explanation=explanation,
                )
            )

    # ── Dimension 3: Points H2H ──
    p_rule = get_rule(RULE_LONGITUDINAL_TEAMMATE_POINTS_H2H)
    p_rounds = h2h.rounds_together
    diff = float(h2h.points_difference)

    if p_rounds >= p_rule.min_sample_size and abs(diff) >= LONGITUDINAL_TEAMMATE_POINTS_DIFF_THRESHOLD:
        strength = classify_evidence_strength(p_rounds, p_rule.min_sample_size)
        rounds_inc = h2h.points_evidence.rounds_included

        if diff > 0:
            winner, loser = drv_a, drv_b
            pts_w, pts_l = h2h.total_points_a, h2h.total_points_b
            race_w, sprint_w = h2h.points_a, h2h.sprint_points_a
            race_l, sprint_l = h2h.points_b, h2h.sprint_points_b
        else:
            winner, loser = drv_b, drv_a
            pts_w, pts_l = h2h.total_points_b, h2h.total_points_a
            race_w, sprint_w = h2h.points_b, h2h.sprint_points_b
            race_l, sprint_l = h2h.points_a, h2h.sprint_points_a

        explanation = (
            f"Across {p_rounds} rounds together for {con_id} in {season_year}, {winner} scored "
            f"{pts_w} points vs {loser} {pts_l} points (differential: +{abs(diff):.1f} points; "
            f"race: {race_w} vs {race_l}, sprint: {sprint_w} vs {sprint_l})."
        )

        trace = InsightTraceability(
            source_metric="points_difference",
            source_function="compute_longitudinal_teammate_h2h_stats",
            rule_id=p_rule.rule_id,
            rule_parameters=p_rule.thresholds,
            observed_value=round(abs(diff), 2),
            unit="points",
            sample_size=p_rounds,
            minimum_sample_size=p_rule.min_sample_size,
            sign_convention="total_points_winner - total_points_loser; includes sprint points",
            season_year=season_year,
            driver_id=winner,
            constructor_id=con_id,
            rounds_included=rounds_inc,
            excluded_observations=0,
        )

        insights.append(
            Insight(
                insight_id=f"{p_rule.rule_id}:{season_year}:{con_id}:{winner}:{loser}",
                rule_id=p_rule.rule_id,
                category=p_rule.category,
                subject_id=winner,
                comparison_subject_id=loser,
                metric="points_difference",
                direction=Direction.HIGHER,
                magnitude=round(abs(diff), 2),
                unit="points",
                evidence_strength=strength,
                sample_size=p_rounds,
                traceability=trace,
                explanation=explanation,
            )
        )

    return insights


def evaluate_constructor_longitudinal_insights(
    trajectory: Sequence[ConstructorTrajectoryItem],
    season_year: int,
    constructor_id: str,
) -> list[Insight]:
    """Evaluate longitudinal trajectory and consistency insights for a constructor.

    Args:
        trajectory: Sequence of ConstructorTrajectoryItem from Phase 3B.
        season_year: Championship season year.
        constructor_id: Constructor slug.

    Returns:
        List of generated constructor insights.
    """
    n = len(trajectory)
    rule = get_rule(RULE_LONGITUDINAL_CONSTRUCTOR_TRAJECTORY)

    if n < rule.min_sample_size:
        return []

    podium_rounds = sum(1 for item in trajectory if item.podiums > 0)
    podium_rate = podium_rounds / n

    if podium_rate >= LONGITUDINAL_CONSTRUCTOR_PODIUM_RATE_THRESHOLD:
        strength = classify_evidence_strength(n, rule.min_sample_size)
        rounds_inc = [item.round for item in trajectory]
        r_str = f"rounds_{min(rounds_inc)}-{max(rounds_inc)}" if rounds_inc else "all"
        ins_id = f"{rule.rule_id}:{season_year}:{r_str}:{constructor_id}:none"
        cum_pts = trajectory[-1].cumulative_total_points

        explanation = (
            f"Across {n} rounds in {season_year}, {constructor_id} achieved podium finishes in "
            f"{podium_rounds} rounds ({podium_rate:.0%}), accumulating {cum_pts} championship points."
        )

        trace = InsightTraceability(
            source_metric="podium_rate",
            source_function="get_constructor_trajectory",
            rule_id=rule.rule_id,
            rule_parameters=rule.thresholds,
            observed_value=round(podium_rate, 3),
            unit="rate",
            sample_size=n,
            minimum_sample_size=rule.min_sample_size,
            sign_convention="podium_rounds / rounds_entered",
            season_year=season_year,
            constructor_id=constructor_id,
            rounds_included=rounds_inc,
            excluded_observations=0,
        )

        return [
            Insight(
                insight_id=ins_id,
                rule_id=rule.rule_id,
                category=rule.category,
                subject_id=constructor_id,
                comparison_subject_id=None,
                metric="podium_rate",
                direction=Direction.HIGHER,
                magnitude=round(podium_rate, 3),
                unit="rate",
                evidence_strength=strength,
                sample_size=n,
                traceability=trace,
                explanation=explanation,
            )
        ]

    return []

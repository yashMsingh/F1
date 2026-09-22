"""Longitudinal statistical analysis and evidence generation.

All calculations are pure, deterministic functions downstream of analytical SQL.
Strictly zero database access, zero network calls, and zero external side effects.
"""

from __future__ import annotations

import statistics
from decimal import Decimal
from typing import Optional, Sequence

from app.analytics.types import (
    DriverTrajectoryItem,
    TeammateEventComparison,
)
from app.statistics.descriptive import (
    compute_consistency_stats,
    compute_descriptive_stats,
)
from app.statistics.position_change import compute_position_change_stats
from app.statistics.types import (
    ConsistencyStats,
    DescriptiveStats,
    DriverFormSummary,
    DriverLongitudinalStats,
    EvidenceStrength,
    LongitudinalEvidenceMetadata,
    PointsStats,
    PositionChangeStats,
    QualityMetadata,
    RaceToRaceDelta,
    RollingWindowStats,
    TeammateH2HStatistics,
    classify_evidence_strength,
)


def compute_longitudinal_evidence_metadata(
    total_races: int,
    valid_observations: int,
    rounds_included: list[int],
    min_required_observations: int = 1,
    window_size_requested: Optional[int] = None,
) -> LongitudinalEvidenceMetadata:
    """Construct structured audit metadata for a longitudinal statistical observation set."""
    excluded = max(0, total_races - valid_observations)
    is_avail = valid_observations >= min_required_observations and valid_observations > 0
    strength = classify_evidence_strength(valid_observations, min_required_observations)

    return LongitudinalEvidenceMetadata(
        total_races=total_races,
        valid_observations=valid_observations,
        excluded_observations=excluded,
        min_required_observations=min_required_observations,
        is_available=is_avail,
        evidence_strength=strength,
        rounds_included=sorted(rounds_included),
        window_size_requested=window_size_requested,
    )


def compute_driver_points_stats(
    trajectory: Sequence[DriverTrajectoryItem],
) -> PointsStats:
    """Compute points scoring statistics differentiating Grand Prix starts, entries, and sprints.

    Denominators:
    - points_per_gp_start: total_race_points / grand_prix_starts (Grand Prix race starts only).
    - points_per_gp_entry: total_race_points / rounds_entered (all rounds entered by driver).
    - points_per_round_total: total_championship_points / rounds_entered (race + sprint points).
    """
    rounds_entered = len(trajectory)
    if rounds_entered == 0:
        empty_stats = compute_descriptive_stats([])
        evidence = compute_longitudinal_evidence_metadata(0, 0, [])
        return PointsStats(
            total_championship_points=Decimal("0.0"),
            total_race_points=Decimal("0.0"),
            total_sprint_points=Decimal("0.0"),
            grand_prix_starts=0,
            rounds_entered=0,
            points_per_gp_start=None,
            points_per_gp_entry=None,
            points_per_round_total=None,
            race_points_stats=empty_stats,
            total_points_stats=empty_stats,
            evidence=evidence,
        )

    tot_race = sum((item.race_points for item in trajectory), Decimal("0.0"))
    tot_sprint = sum((item.sprint_points for item in trajectory), Decimal("0.0"))
    tot_champ = tot_race + tot_sprint

    # Grand Prix starts: driver took part in the Grand Prix (not DNS / Did not start)
    gp_starts = sum(
        1
        for item in trajectory
        if item.status.lower() != "did not start" and item.position_text.lower() != "dns"
    )

    pp_gp_start = (float(tot_race) / gp_starts) if gp_starts > 0 else None
    pp_gp_entry = (float(tot_race) / rounds_entered) if rounds_entered > 0 else None
    pp_round_tot = (float(tot_champ) / rounds_entered) if rounds_entered > 0 else None

    race_pts_list = [float(item.race_points) for item in trajectory]
    tot_pts_list = [float(item.total_round_points) for item in trajectory]

    race_stats = compute_descriptive_stats(race_pts_list)
    tot_stats = compute_descriptive_stats(tot_pts_list)

    evidence = compute_longitudinal_evidence_metadata(
        total_races=rounds_entered,
        valid_observations=rounds_entered,
        rounds_included=[item.round for item in trajectory],
    )

    return PointsStats(
        total_championship_points=tot_champ,
        total_race_points=tot_race,
        total_sprint_points=tot_sprint,
        grand_prix_starts=gp_starts,
        rounds_entered=rounds_entered,
        points_per_gp_start=round(pp_gp_start, 4) if pp_gp_start is not None else None,
        points_per_gp_entry=round(pp_gp_entry, 4) if pp_gp_entry is not None else None,
        points_per_round_total=round(pp_round_tot, 4) if pp_round_tot is not None else None,
        race_points_stats=race_stats,
        total_points_stats=tot_stats,
        evidence=evidence,
    )


def compute_driver_longitudinal_stats(
    trajectory: Sequence[DriverTrajectoryItem],
) -> DriverLongitudinalStats:
    """Compute comprehensive multi-race statistical profile for a driver.

    Args:
        trajectory: Sequence of DriverTrajectoryItem objects ordered chronologically.

    Returns:
        DriverLongitudinalStats instance with full descriptive statistics and evidence.
    """
    if not trajectory:
        empty_desc = compute_descriptive_stats([])
        empty_cons = compute_consistency_stats([])
        empty_pos_change = compute_position_change_stats([])
        empty_points = compute_driver_points_stats([])
        empty_meta = compute_longitudinal_evidence_metadata(0, 0, [])
        return DriverLongitudinalStats(
            driver_id="",
            season_year=0,
            up_to_round=0,
            finish_position=empty_desc,
            finish_position_consistency=empty_cons,
            grid_position=empty_desc,
            grid_position_consistency=empty_cons,
            position_change=empty_pos_change,
            position_change_consistency=empty_cons,
            points=empty_points,
            points_consistency=empty_cons,
            evidence=empty_meta,
        )

    driver_id = trajectory[0].driver_id if hasattr(trajectory[0], "driver_id") else ""
    season_year = trajectory[0].season_year
    up_to_round = max(item.round for item in trajectory)
    rounds_included = [item.round for item in trajectory]
    total_rounds = len(trajectory)

    # 1. Finish position: DNFs have finish_position is None and are strictly excluded from numeric stats
    finish_vals = [item.finish_position for item in trajectory if item.finish_position is not None]
    finish_stats = compute_descriptive_stats(finish_vals)
    finish_cons = compute_consistency_stats(finish_vals)

    # 2. Grid position: Exclude pit lane starts (grid_position is None or <= 0)
    grid_vals = [
        item.grid_position
        for item in trajectory
        if item.grid_position is not None and item.grid_position > 0
    ]
    grid_stats = compute_descriptive_stats(grid_vals)
    grid_cons = compute_consistency_stats(grid_vals)

    # 3. Position change: Requires both valid grid (> 0) and classified finish
    pos_change_items: list[Optional[int]] = []
    for item in trajectory:
        if item.grid_position is not None and item.grid_position > 0 and item.finish_position is not None:
            pos_change_items.append(item.grid_position - item.finish_position)
        else:
            pos_change_items.append(None)

    pos_change_stats = compute_position_change_stats(pos_change_items)
    valid_changes = [c for c in pos_change_items if c is not None]
    pos_change_cons = compute_consistency_stats(valid_changes)

    # 4. Points
    points_stats = compute_driver_points_stats(trajectory)
    tot_points_vals = [float(item.total_round_points) for item in trajectory]
    points_cons = compute_consistency_stats(tot_points_vals, allow_cv=False)

    evidence = compute_longitudinal_evidence_metadata(
        total_races=total_rounds,
        valid_observations=total_rounds,
        rounds_included=rounds_included,
    )

    return DriverLongitudinalStats(
        driver_id=driver_id,
        season_year=season_year,
        up_to_round=up_to_round,
        finish_position=finish_stats,
        finish_position_consistency=finish_cons,
        grid_position=grid_stats,
        grid_position_consistency=grid_cons,
        position_change=pos_change_stats,
        position_change_consistency=pos_change_cons,
        points=points_stats,
        points_consistency=points_cons,
        evidence=evidence,
    )


def compute_rolling_window_stats(
    values_by_round: Sequence[tuple[int, Optional[float | int]]],
    window_size: int = 3,
    metric_name: str = "metric",
    min_observations: int = 1,
) -> list[RollingWindowStats]:
    """Calculate rolling window statistics chronologically across rounds.

    For each round N, includes up to `window_size` previous chronological observations
    ending at round N.
    Does NOT silently impute or manufacture missing values.

    Args:
        values_by_round: Sequence of (round_number, value) pairs sorted by round.
        window_size: Number of races requested in the rolling window.
        metric_name: Label identifying the metric.
        min_observations: Minimum valid observations required to report statistics.

    Returns:
        List of RollingWindowStats for each round evaluated.
    """
    results: list[RollingWindowStats] = []
    n = len(values_by_round)

    for i in range(n):
        start_idx = max(0, i - window_size + 1)
        window_slice = values_by_round[start_idx : i + 1]

        target_round = values_by_round[i][0]
        rounds_included = [r for r, _ in window_slice]
        valid_vals = [float(v) for _, v in window_slice if v is not None]
        valid_count = len(valid_vals)

        if valid_count >= min_observations and valid_count > 0:
            mean_val = statistics.mean(valid_vals)
            median_val = statistics.median(valid_vals)
            stddev_val = statistics.stdev(valid_vals) if valid_count >= 2 else None
            min_val = min(valid_vals)
            max_val = max(valid_vals)
        else:
            mean_val = None
            median_val = None
            stddev_val = None
            min_val = None
            max_val = None

        evidence = compute_longitudinal_evidence_metadata(
            total_races=len(window_slice),
            valid_observations=valid_count,
            rounds_included=rounds_included,
            min_required_observations=min_observations,
            window_size_requested=window_size,
        )

        results.append(
            RollingWindowStats(
                metric_name=metric_name,
                window_size_requested=window_size,
                round=target_round,
                rounds_included=rounds_included,
                valid_observations=valid_count,
                mean=round(mean_val, 4) if mean_val is not None else None,
                median=round(median_val, 4) if median_val is not None else None,
                stddev=round(stddev_val, 4) if stddev_val is not None else None,
                minimum=round(min_val, 4) if min_val is not None else None,
                maximum=round(max_val, 4) if max_val is not None else None,
                evidence=evidence,
            )
        )

    return results


def compute_driver_form_summary(
    trajectory: Sequence[DriverTrajectoryItem],
    window_size: int = 3,
) -> DriverFormSummary:
    """Compute recent driver form summaries using rolling windows and race-to-race deltas.

    Args:
        trajectory: Chronologically sorted trajectory entries for a driver.
        window_size: Requested rolling window size (default: 3).

    Returns:
        DriverFormSummary instance.
    """
    if not trajectory:
        empty_meta = compute_longitudinal_evidence_metadata(0, 0, [])
        return DriverFormSummary(
            driver_id="",
            season_year=0,
            up_to_round=0,
            rolling_windows=[],
            race_to_race_deltas=[],
            evidence=empty_meta,
        )

    driver_id = trajectory[0].driver_id if hasattr(trajectory[0], "driver_id") else ""
    season_year = trajectory[0].season_year
    up_to_round = max(item.round for item in trajectory)
    rounds_included = [item.round for item in trajectory]

    # 1. Rolling windows across metrics
    finish_pairs = [(item.round, item.finish_position) for item in trajectory]
    pts_pairs = [(item.round, float(item.total_round_points)) for item in trajectory]

    pos_chg_pairs: list[tuple[int, Optional[float]]] = []
    for item in trajectory:
        if item.grid_position is not None and item.grid_position > 0 and item.finish_position is not None:
            pos_chg_pairs.append((item.round, float(item.grid_position - item.finish_position)))
        else:
            pos_chg_pairs.append((item.round, None))

    finish_rolling = compute_rolling_window_stats(finish_pairs, window_size, "finish_position")
    pts_rolling = compute_rolling_window_stats(pts_pairs, window_size, "points")
    pos_chg_rolling = compute_rolling_window_stats(pos_chg_pairs, window_size, "position_change")

    all_rolling = finish_rolling + pts_rolling + pos_chg_rolling

    # 2. Race-to-race deltas between consecutive rounds
    deltas: list[RaceToRaceDelta] = []
    for i in range(1, len(trajectory)):
        prev = trajectory[i - 1]
        curr = trajectory[i]

        if prev.finish_position is not None and curr.finish_position is not None:
            f_delta = float(curr.finish_position - prev.finish_position)
        else:
            f_delta = None
        deltas.append(
            RaceToRaceDelta(
                from_round=prev.round,
                to_round=curr.round,
                metric_name="finish_position",
                delta=f_delta,
            )
        )

        p_delta = float(curr.total_round_points - prev.total_round_points)
        deltas.append(
            RaceToRaceDelta(
                from_round=prev.round,
                to_round=curr.round,
                metric_name="points",
                delta=p_delta,
            )
        )

    evidence = compute_longitudinal_evidence_metadata(
        total_races=len(trajectory),
        valid_observations=len(trajectory),
        rounds_included=rounds_included,
        window_size_requested=window_size,
    )

    return DriverFormSummary(
        driver_id=driver_id,
        season_year=season_year,
        up_to_round=up_to_round,
        rolling_windows=all_rolling,
        race_to_race_deltas=deltas,
        evidence=evidence,
    )


def compute_longitudinal_teammate_h2h_stats(
    comparisons: Sequence[TeammateEventComparison],
) -> dict[tuple[str, str, str], TeammateH2HStatistics]:
    """Compute multi-race head-to-head statistical summaries for each teammate pairing.

    Driver ordering is strictly alphabetical (driver_a_id < driver_b_id).
    Pairings are grouped by (constructor_id, driver_a_id, driver_b_id), naturally
    partitioning mid-season substitutions into independent comparisons.

    Args:
        comparisons: Sequence of TeammateEventComparison objects.

    Returns:
        Dict mapping (constructor_id, driver_a_id, driver_b_id) to TeammateH2HStatistics.
    """
    by_pairing: dict[tuple[str, str, str], list[TeammateEventComparison]] = {}
    for comp in comparisons:
        key = (comp.constructor_id, comp.driver_a_id, comp.driver_b_id)
        if key not in by_pairing:
            by_pairing[key] = []
        by_pairing[key].append(comp)

    results: dict[tuple[str, str, str], TeammateH2HStatistics] = {}

    for (con_id, drv_a, drv_b), comps in by_pairing.items():
        rounds_together = len(comps)
        all_rounds = [c.round for c in comps]

        # ── 1. Qualifying Dimension ──
        comp_quali = [
            c
            for c in comps
            if c.is_comparable_qualifying and c.qualifying_delta_millis is not None
        ]
        q_comp_rounds = len(comp_quali)

        # Wins counted only from comparable qualifying rounds (consistent numerator/denominator)
        q_wins_a = sum(1 for c in comp_quali if c.ahead_in_qualifying == drv_a)
        q_wins_b = sum(1 for c in comp_quali if c.ahead_in_qualifying == drv_b)
        q_rate_a = (q_wins_a / q_comp_rounds) if q_comp_rounds > 0 else None
        q_rate_b = (q_wins_b / q_comp_rounds) if q_comp_rounds > 0 else None

        q_deltas = [c.qualifying_delta_millis for c in comp_quali if c.qualifying_delta_millis is not None]
        q_delta_stats = compute_descriptive_stats(q_deltas)
        q_delta_cons = compute_consistency_stats(q_deltas)

        q_evidence = compute_longitudinal_evidence_metadata(
            total_races=rounds_together,
            valid_observations=q_comp_rounds,
            rounds_included=[c.round for c in comp_quali],
            min_required_observations=1,
        )

        # ── 2. Race Finish Dimension ──
        comp_race = [
            c
            for c in comps
            if c.is_comparable_finish and c.finish_a is not None and c.finish_b is not None
        ]
        r_comp_rounds = len(comp_race)

        # Wins counted only from comparable race finish rounds (consistent numerator/denominator)
        r_wins_a = sum(1 for c in comp_race if c.ahead_in_race == drv_a)
        r_wins_b = sum(1 for c in comp_race if c.ahead_in_race == drv_b)
        r_rate_a = (r_wins_a / r_comp_rounds) if r_comp_rounds > 0 else None
        r_rate_b = (r_wins_b / r_comp_rounds) if r_comp_rounds > 0 else None

        r_deltas = [(c.finish_a - c.finish_b) for c in comp_race if c.finish_a is not None and c.finish_b is not None]
        r_delta_stats = compute_descriptive_stats(r_deltas)
        r_delta_cons = compute_consistency_stats(r_deltas)

        r_evidence = compute_longitudinal_evidence_metadata(
            total_races=rounds_together,
            valid_observations=r_comp_rounds,
            rounds_included=[c.round for c in comp_race],
            min_required_observations=1,
        )

        # ── 3. Points Dimension ──
        pts_a = sum((c.points_a for c in comps), Decimal("0.0"))
        pts_b = sum((c.points_b for c in comps), Decimal("0.0"))
        sprint_a = sum((c.sprint_points_a for c in comps), Decimal("0.0"))
        sprint_b = sum((c.sprint_points_b for c in comps), Decimal("0.0"))

        tot_pts_a = pts_a + sprint_a
        tot_pts_b = pts_b + sprint_b
        pts_diff = tot_pts_a - tot_pts_b

        round_pts_deltas = [
            float((c.points_a + c.sprint_points_a) - (c.points_b + c.sprint_points_b))
            for c in comps
        ]
        pts_delta_stats = compute_descriptive_stats(round_pts_deltas)

        pts_evidence = compute_longitudinal_evidence_metadata(
            total_races=rounds_together,
            valid_observations=rounds_together,
            rounds_included=all_rounds,
            min_required_observations=1,
        )

        results[(con_id, drv_a, drv_b)] = TeammateH2HStatistics(
            constructor_id=con_id,
            driver_a_id=drv_a,
            driver_b_id=drv_b,
            rounds_together=rounds_together,
            qualifying_wins_a=q_wins_a,
            qualifying_wins_b=q_wins_b,
            qualifying_comparable_rounds=q_comp_rounds,
            qualifying_win_rate_a=round(q_rate_a, 4) if q_rate_a is not None else None,
            qualifying_win_rate_b=round(q_rate_b, 4) if q_rate_b is not None else None,
            qualifying_delta_stats=q_delta_stats,
            qualifying_delta_consistency=q_delta_cons,
            qualifying_evidence=q_evidence,
            race_wins_a=r_wins_a,
            race_wins_b=r_wins_b,
            race_comparable_rounds=r_comp_rounds,
            race_win_rate_a=round(r_rate_a, 4) if r_rate_a is not None else None,
            race_win_rate_b=round(r_rate_b, 4) if r_rate_b is not None else None,
            race_delta_stats=r_delta_stats,
            race_delta_consistency=r_delta_cons,
            race_evidence=r_evidence,
            points_a=pts_a,
            points_b=pts_b,
            sprint_points_a=sprint_a,
            sprint_points_b=sprint_b,
            total_points_a=tot_pts_a,
            total_points_b=tot_pts_b,
            points_difference=pts_diff,
            points_delta_stats=pts_delta_stats,
            points_evidence=pts_evidence,
        )

    return results

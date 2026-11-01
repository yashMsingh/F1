"""Statistical layer for qualifying-to-race conversion and race craft (Phase 5B.2A).

Transforms analytical conversion summaries into structured statistical evidence models
with full audit traceability and sample-size safeguarding.

Safeguards:
- Safe division by zero (returns 0.0 or None).
- Explicit minimum sample-size thresholds:
  - Pole-to-Win Conversion: min 3 poles.
  - Front-Row Podium Retention: min 3 front-row starts.
  - Grid-Tier Position Delta: min 5 eligible starts in tier.
  - Top-10 Points Conversion: min 5 top-10 starts.
- Rigorous evidence classification (INSUFFICIENT, LOW, MODERATE, HIGH).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.analytics.conversion_analysis import (
    DriverConversionSummary,
    FrontRowSummary,
    GridTierSummary,
    PoleToWinSummary,
    Top10ConversionSummary,
)
from app.statistics.types import (
    EvidenceStrength,
    LongitudinalEvidenceMetadata,
    classify_evidence_strength,
)

logger = logging.getLogger(__name__)

MIN_SAMPLE_SIZE_POLE = 3
MIN_SAMPLE_SIZE_FRONT_ROW = 3
MIN_SAMPLE_SIZE_GRID_TIER = 5
MIN_SAMPLE_SIZE_TOP10 = 5


@dataclass(frozen=True)
class PoleToWinStats:
    """Statistical evidence for a driver's pole-to-win conversion."""

    total_poles: int
    wins_from_pole: int
    conversion_rate: float
    evidence: LongitudinalEvidenceMetadata


@dataclass(frozen=True)
class FrontRowStats:
    """Statistical evidence for a driver's front-row podium retention."""

    front_row_starts: int
    front_row_podiums: int
    retention_rate: float
    evidence: LongitudinalEvidenceMetadata


@dataclass(frozen=True)
class GridTierStats:
    """Statistical evidence for a driver's position changes within a specific grid tier."""

    tier_name: str
    min_grid: int
    max_grid: int
    eligible_starts: int
    classified_finishes: int
    non_classified_results: int
    total_positions_gained: int
    avg_position_delta: Optional[float]
    evidence: LongitudinalEvidenceMetadata


@dataclass(frozen=True)
class Top10ConversionStats:
    """Statistical evidence for a driver's top-10 starting grid to top-10 finish conversion."""

    top10_starts: int
    top10_conversions: int
    conversion_rate: float
    evidence: LongitudinalEvidenceMetadata


@dataclass(frozen=True)
class DriverConversionStats:
    """Comprehensive statistical conversion profile for a driver across a championship season."""

    season_year: int
    driver_id: str
    driver_name: str
    constructor_id: Optional[str]
    constructor_name: Optional[str]
    pole_to_win: PoleToWinStats
    front_row: FrontRowStats
    top10_conversion: Top10ConversionStats
    grid_tiers: dict[str, GridTierStats]
    rounds_included: list[int]
    pit_lane_starts_count: int
    dns_count: int


def compute_pole_to_win_stats(
    total_poles: int,
    wins_from_pole: int,
    rounds_included: list[int],
) -> PoleToWinStats:
    """Compute pole-to-win conversion statistical evidence."""
    rate = round(wins_from_pole / total_poles * 100.0, 2) if total_poles > 0 else 0.0
    ev_strength = classify_evidence_strength(total_poles, MIN_SAMPLE_SIZE_POLE)
    is_avail = total_poles >= MIN_SAMPLE_SIZE_POLE

    evidence = LongitudinalEvidenceMetadata(
        total_races=len(rounds_included),
        valid_observations=total_poles,
        excluded_observations=max(0, len(rounds_included) - total_poles),
        min_required_observations=MIN_SAMPLE_SIZE_POLE,
        is_available=is_avail,
        evidence_strength=ev_strength,
        rounds_included=rounds_included,
    )

    return PoleToWinStats(
        total_poles=total_poles,
        wins_from_pole=wins_from_pole,
        conversion_rate=rate,
        evidence=evidence,
    )


def compute_front_row_stats(
    front_row_starts: int,
    front_row_podiums: int,
    rounds_included: list[int],
    dns_count: int = 0,
) -> FrontRowStats:
    """Compute front-row podium retention statistical evidence."""
    rate = round(front_row_podiums / front_row_starts * 100.0, 2) if front_row_starts > 0 else 0.0
    ev_strength = classify_evidence_strength(front_row_starts, MIN_SAMPLE_SIZE_FRONT_ROW)
    is_avail = front_row_starts >= MIN_SAMPLE_SIZE_FRONT_ROW

    evidence = LongitudinalEvidenceMetadata(
        total_races=len(rounds_included),
        valid_observations=front_row_starts,
        excluded_observations=max(0, len(rounds_included) - front_row_starts + dns_count),
        min_required_observations=MIN_SAMPLE_SIZE_FRONT_ROW,
        is_available=is_avail,
        evidence_strength=ev_strength,
        rounds_included=rounds_included,
    )

    return FrontRowStats(
        front_row_starts=front_row_starts,
        front_row_podiums=front_row_podiums,
        retention_rate=rate,
        evidence=evidence,
    )


def compute_grid_tier_stats(
    tier_name: str,
    min_grid: int,
    max_grid: int,
    eligible_starts: int,
    classified_finishes: int,
    non_classified_results: int,
    total_positions_gained: int,
    rounds_included: list[int],
) -> GridTierStats:
    """Compute grid-tier position delta statistical evidence."""
    avg_d = (
        round(total_positions_gained / classified_finishes, 4)
        if classified_finishes > 0
        else None
    )
    ev_strength = classify_evidence_strength(eligible_starts, MIN_SAMPLE_SIZE_GRID_TIER)
    is_avail = eligible_starts >= MIN_SAMPLE_SIZE_GRID_TIER

    evidence = LongitudinalEvidenceMetadata(
        total_races=len(rounds_included),
        valid_observations=eligible_starts,
        excluded_observations=non_classified_results,
        min_required_observations=MIN_SAMPLE_SIZE_GRID_TIER,
        is_available=is_avail,
        evidence_strength=ev_strength,
        rounds_included=rounds_included,
    )

    return GridTierStats(
        tier_name=tier_name,
        min_grid=min_grid,
        max_grid=max_grid,
        eligible_starts=eligible_starts,
        classified_finishes=classified_finishes,
        non_classified_results=non_classified_results,
        total_positions_gained=total_positions_gained,
        avg_position_delta=avg_d,
        evidence=evidence,
    )


def compute_top10_conversion_stats(
    top10_starts: int,
    top10_conversions: int,
    rounds_included: list[int],
    dns_count: int = 0,
) -> Top10ConversionStats:
    """Compute top-10 starting grid to finish conversion statistical evidence."""
    rate = round(top10_conversions / top10_starts * 100.0, 2) if top10_starts > 0 else 0.0
    ev_strength = classify_evidence_strength(top10_starts, MIN_SAMPLE_SIZE_TOP10)
    is_avail = top10_starts >= MIN_SAMPLE_SIZE_TOP10

    evidence = LongitudinalEvidenceMetadata(
        total_races=len(rounds_included),
        valid_observations=top10_starts,
        excluded_observations=max(0, len(rounds_included) - top10_starts + dns_count),
        min_required_observations=MIN_SAMPLE_SIZE_TOP10,
        is_available=is_avail,
        evidence_strength=ev_strength,
        rounds_included=rounds_included,
    )

    return Top10ConversionStats(
        top10_starts=top10_starts,
        top10_conversions=top10_conversions,
        conversion_rate=rate,
        evidence=evidence,
    )


def compute_driver_conversion_stats(
    summary: DriverConversionSummary,
) -> DriverConversionStats:
    """Transform analytical DriverConversionSummary into statistical DriverConversionStats."""
    p_stats = compute_pole_to_win_stats(
        total_poles=summary.pole_to_win.total_poles,
        wins_from_pole=summary.pole_to_win.wins_from_pole,
        rounds_included=summary.rounds_included,
    )

    fr_stats = compute_front_row_stats(
        front_row_starts=summary.front_row.front_row_starts,
        front_row_podiums=summary.front_row.front_row_podiums,
        rounds_included=summary.rounds_included,
        dns_count=summary.dns_count,
    )

    t10_stats = compute_top10_conversion_stats(
        top10_starts=summary.top10_conversion.top10_starts,
        top10_conversions=summary.top10_conversion.top10_conversions,
        rounds_included=summary.rounds_included,
        dns_count=summary.dns_count,
    )

    tiers_built: dict[str, GridTierStats] = {}
    for t_name, gt in summary.grid_tiers.items():
        tiers_built[t_name] = compute_grid_tier_stats(
            tier_name=gt.tier_name,
            min_grid=gt.min_grid,
            max_grid=gt.max_grid,
            eligible_starts=gt.eligible_starts,
            classified_finishes=gt.classified_finishes,
            non_classified_results=gt.non_classified_results,
            total_positions_gained=gt.total_positions_gained,
            rounds_included=summary.rounds_included,
        )

    return DriverConversionStats(
        season_year=summary.season_year,
        driver_id=summary.driver_id,
        driver_name=summary.driver_name,
        constructor_id=summary.constructor_id,
        constructor_name=summary.constructor_name,
        pole_to_win=p_stats,
        front_row=fr_stats,
        top10_conversion=t10_stats,
        grid_tiers=tiers_built,
        rounds_included=summary.rounds_included,
        pit_lane_starts_count=summary.pit_lane_starts_count,
        dns_count=summary.dns_count,
    )

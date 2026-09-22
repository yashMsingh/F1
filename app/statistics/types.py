"""Typed result dataclasses for the statistical analysis & evidence layer.

All structures are immutable (frozen) and explicitly track sample sizes,
data quality (valid vs excluded observations), and metric-specific semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class QualityMetadata:
    """Metadata detailing observation counts and exclusions.

    Attributes:
        total_observations: Total number of records inspected.
        valid_observations: Number of records containing valid numeric values.
        excluded_observations: Records excluded due to missing/invalid values (e.g. DNF, NULL).
    """

    total_observations: int
    valid_observations: int
    excluded_observations: int


@dataclass(frozen=True)
class DescriptiveStats:
    """Standard descriptive statistical summary for a numeric sample.

    Sample size rules:
        - n = 0: All statistical fields are None, sample_size = 0.
        - n = 1: mean, median, minimum, maximum are equal to the value; stddev, q1, q3, iqr are None.
        - n >= 2: stddev is calculated using sample standard deviation (Bessel's correction, N - 1).
        - n >= 2: q1, q3, iqr calculated via standard median-split or inclusive quantiles.

    Attributes:
        sample_size: Number of valid observations (n).
        mean: Arithmetic mean, or None if n < 1.
        median: Median value (50th percentile), or None if n < 1.
        stddev: Sample standard deviation, or None if n < 2.
        minimum: Smallest observed value, or None if n < 1.
        maximum: Largest observed value, or None if n < 1.
        q1: First quartile (25th percentile), or None if n < 2.
        q3: Third quartile (75th percentile), or None if n < 2.
        iqr: Interquartile range (q3 - q1), or None if n < 2.
    """

    sample_size: int
    mean: Optional[float]
    median: Optional[float]
    stddev: Optional[float]
    minimum: Optional[float]
    maximum: Optional[float]
    q1: Optional[float] = None
    q3: Optional[float] = None
    iqr: Optional[float] = None


@dataclass(frozen=True)
class PositionChangeDistribution:
    """Categorical distribution of position changes.

    Rates are computed strictly using valid_observations (sample_size) as the denominator,
    never the total race entries.

    Attributes:
        sample_size: Number of valid position changes evaluated.
        positive_count: Number of observations where position was gained (> 0).
        negative_count: Number of observations where position was lost (< 0).
        zero_count: Number of observations where position remained unchanged (== 0).
        positive_rate: Proportion of positive changes (positive_count / sample_size), or None if sample_size == 0.
        negative_rate: Proportion of negative changes (negative_count / sample_size), or None if sample_size == 0.
        zero_rate: Proportion of unchanged positions (zero_count / sample_size), or None if sample_size == 0.
    """

    sample_size: int
    positive_count: int
    negative_count: int
    zero_count: int
    positive_rate: Optional[float]
    negative_rate: Optional[float]
    zero_rate: Optional[float]


@dataclass(frozen=True)
class PositionChangeStats:
    """Complete statistical evidence for driver or race position changes.

    Attributes:
        stats: Descriptive statistics of position changes (positive = gained, negative = lost).
        distribution: Categorical breakdown into gained, lost, unchanged.
        quality: Quality and exclusion tracking (e.g. DNFs, pit lane starts).
    """

    stats: DescriptiveStats
    distribution: PositionChangeDistribution
    quality: QualityMetadata


@dataclass(frozen=True)
class QualifyingDeltaStats:
    """Statistical summary of qualifying time deltas between teammates across races.

    Delta convention:
        delta = driver_a_time - driver_b_time (in milliseconds).
        Negative delta means driver_a was faster.
        Positive delta means driver_b was faster.
        Ordering: driver_a < driver_b alphabetically by driver_id.

    Attributes:
        constructor_id: Jolpica constructor slug.
        driver_a_id: Alphabetically first driver slug.
        driver_b_id: Alphabetically second driver slug.
        stats: Descriptive statistics of the delta in milliseconds.
        quality: Quality metadata tracking compared races vs excluded races.
    """

    constructor_id: str
    driver_a_id: str
    driver_b_id: str
    stats: DescriptiveStats
    quality: QualityMetadata


@dataclass(frozen=True)
class LapTimeStats:
    """Statistical evidence for lap times in integer milliseconds.

    Attributes:
        stats: Descriptive statistics of lap times (milliseconds).
        quality: Quality metadata tracking valid vs missing/unrecorded laps.
        fastest_recorded_millis: Minimum recorded lap time in the sample.
    """

    stats: DescriptiveStats
    quality: QualityMetadata
    fastest_recorded_millis: Optional[int]


@dataclass(frozen=True)
class PitStopStats:
    """Statistical evidence for pit stop durations in milliseconds.

    Attributes:
        stats: Descriptive statistics of pit stop durations (milliseconds).
        quality: Quality metadata tracking valid durations vs missing/unrecorded durations.
        fastest_duration_millis: Minimum duration in the sample.
    """

    stats: DescriptiveStats
    quality: QualityMetadata
    fastest_duration_millis: Optional[int]


@dataclass(frozen=True)
class ConsistencyStats:
    """Consistency and dispersion metrics for an observation set.

    Attributes:
        stats: Underlying descriptive statistics.
        range: Difference between maximum and minimum (maximum - minimum), or None if n < 1.
        iqr: Interquartile range (q3 - q1), or None if n < 2.
        coefficient_of_variation: stddev / mean. Strictly None if mean <= 0, metric can be negative,
            or stddev is None.
    """

    stats: DescriptiveStats
    range: Optional[float]
    iqr: Optional[float]
    coefficient_of_variation: Optional[float]


@dataclass(frozen=True)
class TeammateHeadToHeadStats:
    """Head-to-head multi-race statistical comparison across four key dimensions.

    Driver ordering is strictly alphabetical by driver_id (driver_a < driver_b).
    All deltas are driver_a - driver_b.
    No composite ratings or winner designations are provided.

    Attributes:
        constructor_id: Jolpica constructor slug.
        driver_a_id: Alphabetically first driver slug.
        driver_b_id: Alphabetically second driver slug.
        qualifying_delta: Descriptive statistics for qualifying time delta (ms).
        grid_delta: Descriptive statistics for grid position delta.
        finish_delta: Descriptive statistics for finish position delta.
        points_delta: Descriptive statistics for points scored delta.
        quality: Quality metadata tracking total vs compared races.
    """

    constructor_id: str
    driver_a_id: str
    driver_b_id: str
    qualifying_delta: DescriptiveStats
    grid_delta: DescriptiveStats
    finish_delta: DescriptiveStats
    points_delta: DescriptiveStats
    quality: QualityMetadata


# ─── Longitudinal Statistical Types ──────────────────────────────────────────


class EvidenceStrength(str, Enum):
    """Categorical heuristic for evidence strength based on valid sample size.

    Note: This is an empirical evidence-strength heuristic, NOT a formal
    inferential confidence interval or hypothesis test.
    """

    INSUFFICIENT = "INSUFFICIENT"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


def classify_evidence_strength(
    sample_size: int,
    min_sample_size: int = 1,
) -> EvidenceStrength:
    """Classify evidence strength based on sample size and minimum requirement.

    Policy:
    - sample_size < min_sample_size or sample_size <= 0 -> INSUFFICIENT
    - sample_size == 1 -> LOW
    - 2 <= sample_size <= 4 -> MODERATE
    - sample_size >= 5 -> HIGH
    """
    if sample_size < min_sample_size or sample_size <= 0:
        return EvidenceStrength.INSUFFICIENT
    if sample_size == 1:
        return EvidenceStrength.LOW
    if 2 <= sample_size <= 4:
        return EvidenceStrength.MODERATE
    return EvidenceStrength.HIGH


@dataclass(frozen=True)
class LongitudinalEvidenceMetadata:
    """Audit metadata detailing sample size, exclusion reasons, and evidence strength."""

    total_races: int
    valid_observations: int
    excluded_observations: int
    min_required_observations: int
    is_available: bool
    evidence_strength: EvidenceStrength
    rounds_included: list[int]
    window_size_requested: Optional[int] = None


@dataclass(frozen=True)
class PointsStats:
    """Statistical summary of points scoring across Grand Prix and Sprint sessions.

    Denominators are strictly documented and differentiated:
    - points_per_gp_start: total_race_points / grand_prix_starts (Grand Prix race starts only).
    - points_per_gp_entry: total_race_points / rounds_entered (Grand Prix entries, DNS counted in denom).
    - points_per_round_total: total_championship_points / rounds_entered (includes Sprint points).
    """

    total_championship_points: Decimal
    total_race_points: Decimal
    total_sprint_points: Decimal
    grand_prix_starts: int
    rounds_entered: int
    points_per_gp_start: Optional[float]
    points_per_gp_entry: Optional[float]
    points_per_round_total: Optional[float]
    race_points_stats: DescriptiveStats
    total_points_stats: DescriptiveStats
    evidence: LongitudinalEvidenceMetadata


@dataclass(frozen=True)
class DriverLongitudinalStats:
    """Comprehensive multi-race statistical profile for a driver."""

    driver_id: str
    season_year: int
    up_to_round: int
    finish_position: DescriptiveStats
    finish_position_consistency: ConsistencyStats
    grid_position: DescriptiveStats
    grid_position_consistency: ConsistencyStats
    position_change: PositionChangeStats
    position_change_consistency: ConsistencyStats
    points: PointsStats
    points_consistency: ConsistencyStats
    evidence: LongitudinalEvidenceMetadata


@dataclass(frozen=True)
class RollingWindowStats:
    """Statistical evidence for a fixed-size chronological rolling window."""

    metric_name: str
    window_size_requested: int
    round: int
    rounds_included: list[int]
    valid_observations: int
    mean: Optional[float]
    median: Optional[float]
    stddev: Optional[float]
    minimum: Optional[float]
    maximum: Optional[float]
    evidence: LongitudinalEvidenceMetadata


@dataclass(frozen=True)
class RaceToRaceDelta:
    """Chronological race-to-race delta between consecutive rounds."""

    from_round: int
    to_round: int
    metric_name: str
    delta: Optional[float]


@dataclass(frozen=True)
class DriverFormSummary:
    """Summary of recent driver form over rolling windows and race-to-race deltas."""

    driver_id: str
    season_year: int
    up_to_round: int
    rolling_windows: list[RollingWindowStats]
    race_to_race_deltas: list[RaceToRaceDelta]
    evidence: LongitudinalEvidenceMetadata


@dataclass(frozen=True)
class TeammateH2HStatistics:
    """Statistical summary of multi-race head-to-head performance between teammates.

    Driver ordering is strictly alphabetical (driver_a < driver_b).
    Deltas: driver_a - driver_b (negative qualifying delta = driver_a faster).
    """

    constructor_id: str
    driver_a_id: str
    driver_b_id: str
    rounds_together: int

    # Qualifying dimension
    qualifying_wins_a: int
    qualifying_wins_b: int
    qualifying_comparable_rounds: int
    qualifying_win_rate_a: Optional[float]
    qualifying_win_rate_b: Optional[float]
    qualifying_delta_stats: DescriptiveStats
    qualifying_delta_consistency: ConsistencyStats
    qualifying_evidence: LongitudinalEvidenceMetadata

    # Race finish dimension
    race_wins_a: int
    race_wins_b: int
    race_comparable_rounds: int
    race_win_rate_a: Optional[float]
    race_win_rate_b: Optional[float]
    race_delta_stats: DescriptiveStats
    race_delta_consistency: ConsistencyStats
    race_evidence: LongitudinalEvidenceMetadata

    # Points dimension
    points_a: Decimal
    points_b: Decimal
    sprint_points_a: Decimal
    sprint_points_b: Decimal
    total_points_a: Decimal
    total_points_b: Decimal
    points_difference: Decimal  # total_points_a - total_points_b
    points_delta_stats: DescriptiveStats
    points_evidence: LongitudinalEvidenceMetadata


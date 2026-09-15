"""Typed result dataclasses for the analytical data layer.

Every analytical query returns frozen dataclasses — never raw rows.
NULL values from the database are represented as None in Python.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


# ─── Race Analysis ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RaceOverview:
    """Summary of a single Grand Prix event.

    Attributes:
        season_year: Championship season.
        round: Round number within the season.
        race_name: Official Grand Prix name.
        circuit_name: Name of the circuit.
        race_date: Calendar date of the race.
        winner_given_name: Winner's first name, or None if no classified finisher.
        winner_family_name: Winner's surname, or None if no classified finisher.
        winner_constructor: Name of the winning constructor, or None.
        winner_time_millis: Winner's race time in milliseconds, or None.
        winner_time_text: Winner's race time as a display string, or None.
        classified_count: Number of drivers with a numeric finishing position.
        total_result_count: Total entries (classified + retired/DSQ/DNS).
    """

    season_year: int
    round: int
    race_name: str
    circuit_name: str
    race_date: date
    winner_given_name: Optional[str]
    winner_family_name: Optional[str]
    winner_constructor: Optional[str]
    winner_time_millis: Optional[int]
    winner_time_text: Optional[str]
    classified_count: int
    total_result_count: int


@dataclass(frozen=True)
class GridVsFinish:
    """A single driver's grid-to-finish comparison.

    Attributes:
        driver_id: Jolpica slug identifier for the driver.
        given_name: Driver's first name.
        family_name: Driver's surname.
        constructor_name: Constructor name.
        grid_position: Starting grid position; None for pit-lane starts.
        finish_position: Classified finishing position; None for DNF/DSQ/DNS.
        position_change: grid_position − finish_position (positive = gained).
            NULL if either grid_position or finish_position is None.
        status: Race status string (e.g. "Finished", "Engine", "+1 Lap").
        points: Championship points scored.
    """

    driver_id: str
    given_name: str
    family_name: str
    constructor_name: str
    grid_position: Optional[int]
    finish_position: Optional[int]
    position_change: Optional[int]
    status: str
    points: Decimal


@dataclass(frozen=True)
class RaceResultRow:
    """Full race result for a single driver.

    Attributes:
        driver_id: Jolpica slug identifier.
        given_name: Driver's first name.
        family_name: Driver's surname.
        constructor_id: Jolpica constructor slug.
        constructor_name: Constructor display name.
        car_number: Car number, or None.
        grid_position: Starting grid, or None.
        source_position: Classified finishing position from source, or None.
        position_text: Position display string (e.g. "1", "R", "D").
        points: Championship points.
        laps_completed: Number of laps completed.
        status: Race status.
        time_millis: Total race time in milliseconds, or None.
        time_text: Race time display string, or None.
        fastest_lap_rank: Official fastest-lap ranking, or None.
        fastest_lap_number: Lap number of official fastest lap, or None.
        fastest_lap_time: Official fastest lap time string, or None.
        fastest_lap_time_millis: Official fastest lap time in ms, or None.
    """

    driver_id: str
    given_name: str
    family_name: str
    constructor_id: str
    constructor_name: str
    car_number: Optional[int]
    grid_position: Optional[int]
    source_position: Optional[int]
    position_text: str
    points: Decimal
    laps_completed: int
    status: str
    time_millis: Optional[int]
    time_text: Optional[str]
    fastest_lap_rank: Optional[int]
    fastest_lap_number: Optional[int]
    fastest_lap_time: Optional[str]
    fastest_lap_time_millis: Optional[int]


# ─── Qualifying Analysis ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class QualifyingOrder:
    """A single driver's qualifying classification.

    Attributes:
        driver_id: Jolpica slug identifier.
        given_name: Driver's first name.
        family_name: Driver's surname.
        constructor_name: Constructor display name.
        position: Qualifying classification position.
        q1_time_millis: Q1 time in milliseconds, or None if no time set.
        q2_time_millis: Q2 time in milliseconds, or None.
        q3_time_millis: Q3 time in milliseconds, or None.
    """

    driver_id: str
    given_name: str
    family_name: str
    constructor_name: str
    position: int
    q1_time_millis: Optional[int]
    q2_time_millis: Optional[int]
    q3_time_millis: Optional[int]


@dataclass(frozen=True)
class TeammateQualifyingComparison:
    """Qualifying comparison between two teammates at the same constructor.

    Attributes:
        constructor_id: Jolpica constructor slug.
        constructor_name: Constructor display name.
        driver_a_id: Alphabetically first driver slug.
        driver_a_name: Display name "Given Family".
        driver_b_id: Alphabetically second driver slug.
        driver_b_name: Display name "Given Family".
        best_time_a_millis: Best qualifying time for driver A, or None.
        best_time_b_millis: Best qualifying time for driver B, or None.
        delta_millis: best_time_a − best_time_b in milliseconds.
            None if either driver has no valid qualifying time.
            Negative means driver A was faster.
    """

    constructor_id: str
    constructor_name: str
    driver_a_id: str
    driver_a_name: str
    driver_b_id: str
    driver_b_name: str
    best_time_a_millis: Optional[int]
    best_time_b_millis: Optional[int]
    delta_millis: Optional[int]


# ─── Pit Stop Analysis ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PitStopSummary:
    """Per-driver pit stop aggregation for a single race.

    Denominator for avg_duration_millis and fastest_stop_millis:
        Only pit stops where duration_millis IS NOT NULL are included.
        stop_count uses MAX(stop_number) from all pit stop rows.

    Attributes:
        driver_id: Jolpica slug identifier.
        given_name: Driver's first name.
        family_name: Driver's surname.
        stop_count: Total number of pit stops (from MAX(stop_number)).
        total_duration_millis: Sum of all non-NULL durations, or None if all NULL.
        avg_duration_millis: Average of non-NULL durations, or None.
        fastest_stop_millis: Minimum non-NULL duration, or None.
    """

    driver_id: str
    given_name: str
    family_name: str
    stop_count: int
    total_duration_millis: Optional[int]
    avg_duration_millis: Optional[int]
    fastest_stop_millis: Optional[int]


@dataclass(frozen=True)
class ConstructorPitStopSummary:
    """Per-constructor pit stop aggregation for a single race.

    Aggregates across both drivers in the constructor.
    Denominator: only non-NULL duration_millis values.

    Attributes:
        constructor_id: Jolpica constructor slug.
        constructor_name: Constructor display name.
        total_stops: Combined stop count across all drivers.
        avg_duration_millis: Average of all non-NULL durations, or None.
        fastest_stop_millis: Fastest non-NULL stop across the team, or None.
    """

    constructor_id: str
    constructor_name: str
    total_stops: int
    avg_duration_millis: Optional[int]
    fastest_stop_millis: Optional[int]


# ─── Lap Time Analysis ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LapTimeSummary:
    """Per-driver lap time aggregation for a single race.

    IMPORTANT: This reflects the fastest *recorded* lap from the lap_times
    table. The *official* fastest lap is in race_results.fastest_lap_rank /
    fastest_lap_time_millis. These may differ (e.g. deleted lap times).

    Denominator for avg_lap_millis and fastest_lap_millis:
        Only laps where time_millis IS NOT NULL.
    lap_count: Total number of lap rows (including NULL time_millis).

    Attributes:
        driver_id: Jolpica slug identifier.
        given_name: Driver's first name.
        family_name: Driver's surname.
        lap_count: Total recorded laps.
        fastest_lap_millis: Minimum non-NULL time_millis, or None.
        avg_lap_millis: Average of non-NULL time_millis (integer), or None.
    """

    driver_id: str
    given_name: str
    family_name: str
    lap_count: int
    fastest_lap_millis: Optional[int]
    avg_lap_millis: Optional[int]


# ─── Standings ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DriverStandingRow:
    """A single driver's championship standing from persisted standings data.

    Source: driver_standings table — NOT reconstructed from race results.

    Attributes:
        driver_id: Jolpica slug identifier.
        given_name: Driver's first name.
        family_name: Driver's surname.
        position: Championship position.
        points: Cumulative championship points.
        wins: Number of wins.
    """

    driver_id: str
    given_name: str
    family_name: str
    position: int
    points: Decimal
    wins: int


@dataclass(frozen=True)
class ConstructorStandingRow:
    """A single constructor's championship standing from persisted standings data.

    Source: constructor_standings table — NOT reconstructed from race results.

    Attributes:
        constructor_id: Jolpica constructor slug.
        constructor_name: Constructor display name.
        position: Championship position.
        points: Cumulative championship points.
        wins: Number of wins.
    """

    constructor_id: str
    constructor_name: str
    position: int
    points: Decimal
    wins: int


# ─── Driver Race Summary ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class DriverRaceSummary:
    """Comprehensive single-driver race summary.

    pit_stop_count is retrieved via a separate scalar subquery to avoid
    row multiplication from joining pit_stops with race_results.

    Attributes:
        driver_id: Jolpica slug identifier.
        given_name: Driver's first name.
        family_name: Driver's surname.
        constructor_name: Constructor display name.
        grid_position: Starting grid, or None.
        finish_position: Classified finishing position, or None.
        position_change: grid − finish (positive = gained), or None.
        points: Championship points.
        laps_completed: Number of laps completed.
        status: Race status string.
        pit_stop_count: Number of pit stops made (from pit_stops table).
        race_time_millis: Total race time in milliseconds, or None.
    """

    driver_id: str
    given_name: str
    family_name: str
    constructor_name: str
    grid_position: Optional[int]
    finish_position: Optional[int]
    position_change: Optional[int]
    points: Decimal
    laps_completed: int
    status: str
    pit_stop_count: int
    race_time_millis: Optional[int]


# ─── Constructor / Teammate Comparison ────────────────────────────────────────


@dataclass(frozen=True)
class TeammateComparison:
    """Head-to-head comparison between two teammates in a single race.

    Driver ordering: driver_a < driver_b by driver_id alphabetical order
    (deterministic, no subjective ordering).

    All deltas are driver_a_value − driver_b_value.
    No "better/worse" labels — this layer provides evidence only.

    Attributes:
        constructor_id: Jolpica constructor slug.
        constructor_name: Constructor display name.
        driver_a_id: Alphabetically first driver slug.
        driver_a_name: Display name "Given Family".
        driver_b_id: Alphabetically second driver slug.
        driver_b_name: Display name "Given Family".
        qualifying_delta_millis: Best qualifying time A − B (ms), or None.
        grid_delta: Grid position A − B, or None if either missing.
        finish_delta: Finish position A − B, or None if either missing.
        points_delta: Points A − B (always available as Decimal).
    """

    constructor_id: str
    constructor_name: str
    driver_a_id: str
    driver_a_name: str
    driver_b_id: str
    driver_b_name: str
    qualifying_delta_millis: Optional[int]
    grid_delta: Optional[int]
    finish_delta: Optional[int]
    points_delta: Decimal


# ─── Longitudinal / Multi-Race Analytics ──────────────────────────────────────


@dataclass(frozen=True)
class DriverTrajectoryItem:
    """A driver's performance data point for a single race in a season trajectory."""

    season_year: int
    round: int
    race_name: str
    circuit_name: str
    race_date: date
    constructor_id: str
    constructor_name: str
    grid_position: Optional[int]
    finish_position: Optional[int]
    position_text: str
    status: str
    is_classified: bool
    race_points: Decimal
    sprint_points: Decimal
    total_round_points: Decimal
    cumulative_race_points: Decimal
    cumulative_sprint_points: Decimal
    cumulative_total_points: Decimal
    championship_standing_position: Optional[int]
    pit_stop_count: int
    fastest_lap_rank: Optional[int]


@dataclass(frozen=True)
class DriverSeasonAggregate:
    """Summary of a driver's season performance up to a given round."""

    season_year: int
    up_to_round: int
    driver_id: str
    driver_code: Optional[str]
    given_name: str
    family_name: str
    constructor_id: str
    constructor_name: str
    races_entered: int
    races_started: int
    races_classified: int
    dnf_count: int
    wins: int
    podiums: int
    points_finishes: int
    total_race_points: Decimal
    total_sprint_points: Decimal
    total_points: Decimal
    average_grid: Optional[float]
    average_finish: Optional[float]
    best_grid: Optional[int]
    best_finish: Optional[int]
    total_laps_completed: int
    championship_standing: Optional[int]


@dataclass(frozen=True)
class ConstructorTrajectoryItem:
    """A constructor's performance data point for a single race in a season trajectory."""

    season_year: int
    round: int
    race_name: str
    circuit_name: str
    race_date: date
    constructor_id: str
    constructor_name: str
    race_points: Decimal
    sprint_points: Decimal
    total_round_points: Decimal
    cumulative_race_points: Decimal
    cumulative_sprint_points: Decimal
    cumulative_total_points: Decimal
    best_finish: Optional[int]
    podiums: int
    cars_classified: int
    cars_entered: int
    championship_standing_position: Optional[int]


@dataclass(frozen=True)
class ConstructorDriverContribution:
    """Breakdown of points contributed by a driver to a constructor in a season."""

    driver_id: str
    driver_name: str
    race_points: Decimal
    sprint_points: Decimal
    total_points: Decimal
    points_share_pct: Optional[float]
    races_entered: int
    best_finish: Optional[int]


@dataclass(frozen=True)
class ConstructorSeasonAggregate:
    """Summary of a constructor's season performance up to a given round."""

    season_year: int
    up_to_round: int
    constructor_id: str
    constructor_name: str
    races_entered: int
    total_car_starts: int
    total_car_finishes: int
    dnf_count: int
    wins: int
    podiums: int
    total_race_points: Decimal
    total_sprint_points: Decimal
    total_points: Decimal
    driver_contributions: list[ConstructorDriverContribution]
    championship_standing: Optional[int]


@dataclass(frozen=True)
class TeammateEventComparison:
    """Event-level head-to-head comparison between two drivers on the same constructor."""

    season_year: int
    round: int
    race_name: str
    constructor_id: str
    constructor_name: str
    driver_a_id: str
    driver_a_name: str
    driver_b_id: str
    driver_b_name: str
    qualifying_a_pos: Optional[int]
    qualifying_b_pos: Optional[int]
    qualifying_delta_millis: Optional[int]
    grid_a: Optional[int]
    grid_b: Optional[int]
    finish_a: Optional[int]
    finish_b: Optional[int]
    status_a: str
    status_b: str
    points_a: Decimal
    points_b: Decimal
    sprint_points_a: Decimal
    sprint_points_b: Decimal
    is_comparable_qualifying: bool
    is_comparable_finish: bool
    ahead_in_qualifying: Optional[str]
    ahead_in_race: Optional[str]


@dataclass(frozen=True)
class SeasonTeammateComparison:
    """Aggregated season head-to-head comparison between two drivers who were teammates."""

    season_year: int
    up_to_round: int
    constructor_id: str
    constructor_name: str
    driver_a_id: str
    driver_a_name: str
    driver_b_id: str
    driver_b_name: str
    rounds_together: int
    qualifying_head_to_head_a: int
    qualifying_head_to_head_b: int
    qualifying_comparable_rounds: int
    race_head_to_head_a: int
    race_head_to_head_b: int
    race_comparable_rounds: int
    points_a: Decimal
    points_b: Decimal
    sprint_points_a: Decimal
    sprint_points_b: Decimal
    total_points_a: Decimal
    total_points_b: Decimal


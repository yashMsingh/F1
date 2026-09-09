"""Pydantic schemas for API request and response validation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ─── Health & Base ────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


# ─── Races ────────────────────────────────────────────────────────────────────


class RaceListItem(BaseModel):
    season_year: int
    round: int
    race_name: str
    circuit_name: str
    race_date: date

    model_config = ConfigDict(from_attributes=True)


class RaceOverviewResponse(BaseModel):
    season_year: int
    round: int
    race_name: str
    circuit_name: str
    race_date: date
    winner_given_name: Optional[str] = None
    winner_family_name: Optional[str] = None
    winner_constructor: Optional[str] = None
    winner_time_millis: Optional[int] = None
    winner_time_text: Optional[str] = None
    classified_count: int
    total_result_count: int

    model_config = ConfigDict(from_attributes=True)


# ─── Results & Grid vs Finish ─────────────────────────────────────────────────


class GridVsFinishItem(BaseModel):
    driver_id: str
    given_name: str
    family_name: str
    constructor_name: str
    grid_position: Optional[int] = None
    finish_position: Optional[int] = None
    position_change: Optional[int] = None
    status: str
    points: Decimal

    model_config = ConfigDict(from_attributes=True)


class RaceResultItem(BaseModel):
    driver_id: str
    given_name: str
    family_name: str
    constructor_id: str
    constructor_name: str
    car_number: Optional[int] = None
    grid_position: Optional[int] = None
    source_position: Optional[int] = None
    position_text: str
    points: Decimal
    laps_completed: int
    status: str
    time_millis: Optional[int] = None
    time_text: Optional[str] = None
    fastest_lap_rank: Optional[int] = None
    fastest_lap_number: Optional[int] = None
    fastest_lap_time: Optional[str] = None
    fastest_lap_time_millis: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RaceResultsResponse(BaseModel):
    overview: Optional[RaceOverviewResponse] = None
    results: list[RaceResultItem]
    grid_vs_finish: list[GridVsFinishItem]


# ─── Qualifying ───────────────────────────────────────────────────────────────


class QualifyingOrderItem(BaseModel):
    driver_id: str
    given_name: str
    family_name: str
    constructor_name: str
    position: int
    q1_time_millis: Optional[int] = None
    q2_time_millis: Optional[int] = None
    q3_time_millis: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TeammateQualifyingComparisonItem(BaseModel):
    constructor_id: str
    constructor_name: str
    driver_a_id: str
    driver_a_name: str
    driver_b_id: str
    driver_b_name: str
    best_time_a_millis: Optional[int] = None
    best_time_b_millis: Optional[int] = None
    delta_millis: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class QualifyingResponse(BaseModel):
    qualifying_order: list[QualifyingOrderItem]
    teammate_comparisons: list[TeammateQualifyingComparisonItem]


# ─── Pit Stops ────────────────────────────────────────────────────────────────


class PitStopSummaryItem(BaseModel):
    driver_id: str
    given_name: str
    family_name: str
    stop_count: int
    total_duration_millis: Optional[int] = None
    avg_duration_millis: Optional[int] = None
    fastest_stop_millis: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ConstructorPitStopSummaryItem(BaseModel):
    constructor_id: str
    constructor_name: str
    total_stops: int
    avg_duration_millis: Optional[int] = None
    fastest_stop_millis: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PitStopsResponse(BaseModel):
    drivers: list[PitStopSummaryItem]
    constructors: list[ConstructorPitStopSummaryItem]


# ─── Lap Times ────────────────────────────────────────────────────────────────


class LapTimeSummaryItem(BaseModel):
    driver_id: str
    given_name: str
    family_name: str
    lap_count: int
    fastest_lap_millis: Optional[int] = None
    avg_lap_millis: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class LapTimesResponse(BaseModel):
    laps: list[LapTimeSummaryItem]


# ─── Standings ────────────────────────────────────────────────────────────────


class DriverStandingItem(BaseModel):
    driver_id: str
    given_name: str
    family_name: str
    position: int
    points: Decimal
    wins: int

    model_config = ConfigDict(from_attributes=True)


class ConstructorStandingItem(BaseModel):
    constructor_id: str
    constructor_name: str
    position: int
    points: Decimal
    wins: int

    model_config = ConfigDict(from_attributes=True)


class StandingsResponse(BaseModel):
    drivers: list[DriverStandingItem]
    constructors: list[ConstructorStandingItem]


# ─── Insights & Traceability ──────────────────────────────────────────────────


class InsightTraceabilityResponse(BaseModel):
    source_metric: str
    source_function: str
    rule_id: str
    rule_parameters: dict[str, Any]
    observed_value: Any
    unit: Optional[str] = None
    sample_size: int
    minimum_sample_size: int
    sign_convention: Optional[str] = None
    season_year: Optional[int] = None
    round_num: Optional[int] = None
    race_id: Optional[int] = None
    driver_id: Optional[str] = None
    constructor_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InsightResponse(BaseModel):
    insight_id: str
    rule_id: str
    category: str
    subject_id: str
    comparison_subject_id: Optional[str] = None
    metric: str
    direction: str
    magnitude: Optional[float] = None
    unit: Optional[str] = None
    evidence_strength: str
    sample_size: int
    traceability: InsightTraceabilityResponse

    model_config = ConfigDict(from_attributes=True)


class InsightsResponse(BaseModel):
    insights: list[InsightResponse]
    total: int


# ─── AI Narrative ─────────────────────────────────────────────────────────────


class NarrativeResponse(BaseModel):
    status: str  # "available" or "unavailable"
    provider: Optional[str] = None
    model: Optional[str] = None
    narrative: Optional[str] = None
    limitations: list[str] = []
    evidence_references: list[str] = []
    error: Optional[str] = None

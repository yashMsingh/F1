/**
 * TypeScript API contracts matching the FastAPI backend schemas.
 */

export interface RaceListItem {
  season_year: number;
  round: number;
  race_name: string;
  circuit_name: string;
  race_date: string;
}

export interface RaceOverview {
  season_year: number;
  round: number;
  race_name: string;
  circuit_name: string;
  race_date: string;
  winner_given_name: string | null;
  winner_family_name: string | null;
  winner_constructor: string | null;
  winner_time_millis: number | null;
  winner_time_text: string | null;
  classified_count: number;
  total_result_count: number;
}

export interface GridVsFinishItem {
  driver_id: string;
  given_name: string;
  family_name: string;
  constructor_name: string;
  grid_position: number | null;
  finish_position: number | null;
  position_change: number | null;
  status: string;
  points: number | string;
}

export interface RaceResultItem {
  driver_id: string;
  given_name: string;
  family_name: string;
  constructor_id: string;
  constructor_name: string;
  car_number: number | null;
  grid_position: number | null;
  source_position: number | null;
  position_text: string;
  points: number | string;
  laps_completed: number;
  status: string;
  time_millis: number | null;
  time_text: string | null;
  fastest_lap_rank: number | null;
  fastest_lap_number: number | null;
  fastest_lap_time: string | null;
  fastest_lap_time_millis: number | null;
}

export interface RaceResultsResponse {
  overview: RaceOverview | null;
  results: RaceResultItem[];
  grid_vs_finish: GridVsFinishItem[];
}

export interface QualifyingOrderItem {
  driver_id: string;
  given_name: string;
  family_name: string;
  constructor_name: string;
  position: number;
  q1_time_millis: number | null;
  q2_time_millis: number | null;
  q3_time_millis: number | null;
}

export interface TeammateQualifyingComparisonItem {
  constructor_id: string;
  constructor_name: string;
  driver_a_id: string;
  driver_a_name: string;
  driver_b_id: string;
  driver_b_name: string;
  best_time_a_millis: number | null;
  best_time_b_millis: number | null;
  delta_millis: number | null;
}

export interface QualifyingResponse {
  qualifying_order: QualifyingOrderItem[];
  teammate_comparisons: TeammateQualifyingComparisonItem[];
}

export interface PitStopSummaryItem {
  driver_id: string;
  given_name: string;
  family_name: string;
  stop_count: number;
  total_duration_millis: number | null;
  avg_duration_millis: number | null;
  fastest_stop_millis: number | null;
}

export interface ConstructorPitStopSummaryItem {
  constructor_id: string;
  constructor_name: string;
  total_stops: number;
  avg_duration_millis: number | null;
  fastest_stop_millis: number | null;
}

export interface PitStopsResponse {
  drivers: PitStopSummaryItem[];
  constructors: ConstructorPitStopSummaryItem[];
}

export interface LapTimeSummaryItem {
  driver_id: string;
  given_name: string;
  family_name: string;
  lap_count: number;
  fastest_lap_millis: number | null;
  avg_lap_millis: number | null;
}

export interface LapTimesResponse {
  laps: LapTimeSummaryItem[];
}

export interface DriverStandingItem {
  driver_id: string;
  given_name: string;
  family_name: string;
  position: number;
  points: number | string;
  wins: number;
}

export interface ConstructorStandingItem {
  constructor_id: string;
  constructor_name: string;
  position: number;
  points: number | string;
  wins: number;
}

export interface StandingsResponse {
  drivers: DriverStandingItem[];
  constructors: ConstructorStandingItem[];
}

export interface InsightTraceability {
  source_metric: string;
  source_function: string;
  rule_id: string;
  rule_parameters: Record<string, unknown>;
  observed_value: unknown;
  unit: string | null;
  sample_size: number;
  minimum_sample_size: number;
  sign_convention: string | null;
  season_year: number | null;
  round_num: number | null;
  race_id: number | null;
  driver_id: string | null;
  constructor_id: string | null;
}

export interface InsightItem {
  insight_id: string;
  rule_id: string;
  category: string;
  subject_id: string;
  comparison_subject_id: string | null;
  metric: string;
  direction: string;
  magnitude: number | null;
  unit: string | null;
  evidence_strength: "INSUFFICIENT" | "LOW" | "MODERATE" | "HIGH";
  sample_size: number;
  traceability: InsightTraceability;
}

export interface InsightsResponse {
  insights: InsightItem[];
  total: number;
}

export interface NarrativeResponse {
  status: "available" | "unavailable";
  provider: string | null;
  model: string | null;
  narrative: string | null;
  limitations: string[];
  evidence_references: string[];
  error: string | null;
}

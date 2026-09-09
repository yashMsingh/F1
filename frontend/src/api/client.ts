/**
 * Centralized API client for the F1 Race Intelligence backend.
 */

import type {
  InsightsResponse,
  LapTimesResponse,
  NarrativeResponse,
  PitStopsResponse,
  QualifyingResponse,
  RaceListItem,
  RaceOverview,
  RaceResultsResponse,
  StandingsResponse,
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function get<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      let errDetail = `HTTP ${res.status} ${res.statusText}`;
      try {
        const body = await res.json();
        if (body.detail) errDetail = body.detail;
      } catch {
        // Ignore json parse error on error responses
      }
      throw new ApiError(res.status, errDetail);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new Error(`Network error connecting to backend API at ${url}: ${(err as Error).message}`);
  }
}

export const api = {
  getRaces: (season?: number): Promise<RaceListItem[]> => {
    const query = season ? `?season=${season}` : "";
    return get<RaceListItem[]>(`/races${query}`);
  },

  getRaceOverview: (season: number, round: number): Promise<RaceOverview> => {
    return get<RaceOverview>(`/races/${season}/${round}`);
  },

  getRaceResults: (season: number, round: number): Promise<RaceResultsResponse> => {
    return get<RaceResultsResponse>(`/races/${season}/${round}/results`);
  },

  getQualifying: (season: number, round: number): Promise<QualifyingResponse> => {
    return get<QualifyingResponse>(`/races/${season}/${round}/qualifying`);
  },

  getPitStops: (season: number, round: number): Promise<PitStopsResponse> => {
    return get<PitStopsResponse>(`/races/${season}/${round}/pit-stops`);
  },

  getLapTimes: (season: number, round: number): Promise<LapTimesResponse> => {
    return get<LapTimesResponse>(`/races/${season}/${round}/laps`);
  },

  getStandings: (season: number, round: number): Promise<StandingsResponse> => {
    return get<StandingsResponse>(`/races/${season}/${round}/standings`);
  },

  getInsights: (season: number, round: number): Promise<InsightsResponse> => {
    return get<InsightsResponse>(`/races/${season}/${round}/insights`);
  },

  getNarrative: (season: number, round: number): Promise<NarrativeResponse> => {
    return get<NarrativeResponse>(`/races/${season}/${round}/narrative`);
  },
};

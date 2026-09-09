import React, { useEffect, useState } from "react";
import { api } from "./api/client";
import type {
  InsightItem,
  LapTimesResponse,
  NarrativeResponse,
  PitStopsResponse,
  QualifyingResponse,
  RaceListItem,
  RaceResultsResponse,
  StandingsResponse,
} from "./types/api";
import { Navbar } from "./components/Navbar";
import { HeroHeader } from "./components/HeroHeader";
import { RaceResultsTable } from "./components/RaceResultsTable";
import { GridVsFinishChart } from "./components/GridVsFinishChart";
import { QualifyingSection } from "./components/QualifyingSection";
import { PitStopSection } from "./components/PitStopSection";
import { LapTimeSection } from "./components/LapTimeSection";
import { StandingsSection } from "./components/StandingsSection";
import { InsightsSection } from "./components/InsightsSection";
import { NarrativeSection } from "./components/NarrativeSection";
import { ErrorBoundary, LoadingSkeleton } from "./components/LoadingSkeleton";
import { Flag, Gauge, Wrench, Timer, Award, AlertCircle } from "lucide-react";

type TabKey = "results" | "qualifying" | "pit-stops" | "laps" | "standings";

export const App: React.FC = () => {
  // Navigation & selection
  const [races, setRaces] = useState<RaceListItem[]>([]);
  const [selectedSeason, setSelectedSeason] = useState<number>(2024);
  const [selectedRound, setSelectedRound] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<TabKey>("results");

  // Data states
  const [resultsData, setResultsData] = useState<RaceResultsResponse | null>(null);
  const [qualifyingData, setQualifyingData] = useState<QualifyingResponse | null>(null);
  const [pitStopsData, setPitStopsData] = useState<PitStopsResponse | null>(null);
  const [lapsData, setLapsData] = useState<LapTimesResponse | null>(null);
  const [standingsData, setStandingsData] = useState<StandingsResponse | null>(null);
  const [insights, setInsights] = useState<InsightItem[]>([]);
  const [narrativeData, setNarrativeData] = useState<NarrativeResponse | null>(null);

  // Status flags
  const [loading, setLoading] = useState<boolean>(true);
  const [narrativeLoading, setNarrativeLoading] = useState<boolean>(false);
  const [apiConnected, setApiConnected] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // 1. Initial load: list races
  useEffect(() => {
    async function loadRaces() {
      try {
        const raceList = await api.getRaces();
        setRaces(raceList);
        setApiConnected(true);

        // Prefer 2024 round 1 if present, otherwise default to first available race
        const defaultRace =
          raceList.find((r) => r.season_year === 2024 && r.round === 1) || raceList[0];
        if (defaultRace) {
          setSelectedSeason(defaultRace.season_year);
          setSelectedRound(defaultRace.round);
        }
      } catch (err) {
        console.error("Failed to load races:", err);
        setApiConnected(false);
        setErrorMessage("Unable to connect to the F1 Race Intelligence backend API.");
      }
    }
    loadRaces();
  }, []);

  // 2. Load race data when selection changes
  useEffect(() => {
    if (!selectedSeason || !selectedRound) return;

    let isMounted = true;

    async function loadEventData() {
      setLoading(true);
      setErrorMessage(null);

      try {
        // Load deterministic analytics concurrently
        const [res, quali, pits, laps, std, ins] = await Promise.all([
          api.getRaceResults(selectedSeason, selectedRound),
          api.getQualifying(selectedSeason, selectedRound),
          api.getPitStops(selectedSeason, selectedRound),
          api.getLapTimes(selectedSeason, selectedRound),
          api.getStandings(selectedSeason, selectedRound),
          api.getInsights(selectedSeason, selectedRound),
        ]);

        if (isMounted) {
          setResultsData(res);
          setQualifyingData(quali);
          setPitStopsData(pits);
          setLapsData(laps);
          setStandingsData(std);
          setInsights(ins.insights);
          setApiConnected(true);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Failed to load race analytics:", err);
          setErrorMessage((err as Error).message);
          setLoading(false);
        }
      }

      // Load AI narrative independently (non-blocking for deterministic analytics)
      if (isMounted) {
        setNarrativeLoading(true);
      }
      try {
        const narrativeRes = await api.getNarrative(selectedSeason, selectedRound);
        if (isMounted) {
          setNarrativeData(narrativeRes);
          setNarrativeLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          console.warn("AI narrative call failed gracefully:", err);
          setNarrativeData({
            status: "unavailable",
            provider: null,
            model: null,
            narrative: null,
            limitations: [],
            evidence_references: [],
            error: (err as Error).message,
          });
          setNarrativeLoading(false);
        }
      }
    }

    loadEventData();

    return () => {
      isMounted = false;
    };
  }, [selectedSeason, selectedRound]);

  const handleSelectRace = (season: number, round: number) => {
    setSelectedSeason(season);
    setSelectedRound(round);
  };

  return (
    <div className="min-h-screen bg-surface-dark text-text-primary flex flex-col font-sans selection:bg-f1-red selection:text-white">
      {/* Top Navbar */}
      <Navbar
        races={races}
        selectedSeason={selectedSeason}
        selectedRound={selectedRound}
        onSelectRace={handleSelectRace}
        apiConnected={apiConnected}
        loading={loading}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Global Error Notice */}
        {errorMessage && (
          <div className="card bg-red-950/40 border border-red-500/40 p-4 rounded-xl flex items-center gap-3 text-red-200">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            <div className="text-sm">
              <strong className="font-bold">Error loading event data:</strong> {errorMessage}
            </div>
          </div>
        )}

        {/* Hero Header */}
        {loading ? (
          <LoadingSkeleton rows={2} />
        ) : (
          <ErrorBoundary fallbackTitle="Could not load race header">
            <HeroHeader overview={resultsData?.overview || null} />
          </ErrorBoundary>
        )}

        {/* Grounded AI Narrative Section */}
        <ErrorBoundary fallbackTitle="Could not render AI Narrative">
          <NarrativeSection narrativeData={narrativeData} loading={narrativeLoading} />
        </ErrorBoundary>

        {/* Deterministic Insights Section */}
        {loading ? (
          <LoadingSkeleton rows={4} />
        ) : (
          <ErrorBoundary fallbackTitle="Could not render Deterministic Insights">
            <InsightsSection insights={insights} />
          </ErrorBoundary>
        )}

        {/* Grid vs Finish Overview Chart */}
        {!loading && resultsData && resultsData.grid_vs_finish.length > 0 && (
          <ErrorBoundary fallbackTitle="Could not render Grid vs Finish">
            <GridVsFinishChart items={resultsData.grid_vs_finish} />
          </ErrorBoundary>
        )}

        {/* Navigation Tabs for Deep-Dive Sections */}
        <div className="border-b border-border-subtle">
          <nav className="flex space-x-2 sm:space-x-4 overflow-x-auto py-1" aria-label="Tabs">
            <button
              onClick={() => setActiveTab("results")}
              className={`tab-btn ${activeTab === "results" ? "tab-btn-active" : "tab-btn-inactive"}`}
            >
              <Flag className="w-4 h-4" />
              <span>Race Results</span>
            </button>

            <button
              onClick={() => setActiveTab("qualifying")}
              className={`tab-btn ${activeTab === "qualifying" ? "tab-btn-active" : "tab-btn-inactive"}`}
            >
              <Gauge className="w-4 h-4" />
              <span>Qualifying</span>
            </button>

            <button
              onClick={() => setActiveTab("pit-stops")}
              className={`tab-btn ${activeTab === "pit-stops" ? "tab-btn-active" : "tab-btn-inactive"}`}
            >
              <Wrench className="w-4 h-4" />
              <span>Pit Stops</span>
            </button>

            <button
              onClick={() => setActiveTab("laps")}
              className={`tab-btn ${activeTab === "laps" ? "tab-btn-active" : "tab-btn-inactive"}`}
            >
              <Timer className="w-4 h-4" />
              <span>Lap Times</span>
            </button>

            <button
              onClick={() => setActiveTab("standings")}
              className={`tab-btn ${activeTab === "standings" ? "tab-btn-active" : "tab-btn-inactive"}`}
            >
              <Award className="w-4 h-4" />
              <span>Standings</span>
            </button>
          </nav>
        </div>

        {/* Active Tab Panel */}
        <div className="pt-2">
          {loading ? (
            <LoadingSkeleton rows={8} />
          ) : (
            <>
              {activeTab === "results" && (
                <ErrorBoundary fallbackTitle="Could not load race classification">
                  <RaceResultsTable
                    results={resultsData?.results || []}
                    gridVsFinish={resultsData?.grid_vs_finish || []}
                  />
                </ErrorBoundary>
              )}

              {activeTab === "qualifying" && (
                <ErrorBoundary fallbackTitle="Could not load qualifying results">
                  <QualifyingSection data={qualifyingData} />
                </ErrorBoundary>
              )}

              {activeTab === "pit-stops" && (
                <ErrorBoundary fallbackTitle="Could not load pit stop results">
                  <PitStopSection data={pitStopsData} />
                </ErrorBoundary>
              )}

              {activeTab === "laps" && (
                <ErrorBoundary fallbackTitle="Could not load lap time analytics">
                  <LapTimeSection data={lapsData} />
                </ErrorBoundary>
              )}

              {activeTab === "standings" && (
                <ErrorBoundary fallbackTitle="Could not load championship standings">
                  <StandingsSection data={standingsData} />
                </ErrorBoundary>
              )}
            </>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-border-subtle/60 py-6 px-4 text-center text-xs text-text-muted bg-surface-dark">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            <strong>F1 Race Intelligence Platform</strong> — Portfolio Grade Motorsport Analytics
          </div>
          <div className="text-text-muted">
            Database is the Source of Truth • Deterministic Rules • Grounded AI Explanations
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;

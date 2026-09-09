import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { HeroHeader } from "./HeroHeader";
import { RaceResultsTable } from "./RaceResultsTable";
import { InsightsSection } from "./InsightsSection";
import { NarrativeSection } from "./NarrativeSection";
import { RaceSelector } from "./RaceSelector";
import type {
  GridVsFinishItem,
  InsightItem,
  NarrativeResponse,
  RaceListItem,
  RaceOverview,
  RaceResultItem,
} from "../types/api";

describe("Frontend Components Test Suite", () => {
  it("renders HeroHeader with winner and race details", () => {
    const overview: RaceOverview = {
      season_year: 2024,
      round: 1,
      race_name: "Bahrain Grand Prix",
      circuit_name: "Bahrain International Circuit",
      race_date: "2024-03-02",
      winner_given_name: "Max",
      winner_family_name: "Verstappen",
      winner_constructor: "Red Bull",
      winner_time_millis: 5504742,
      winner_time_text: "1:31:44.742",
      classified_count: 5,
      total_result_count: 6,
    };

    render(<HeroHeader overview={overview} />);

    expect(screen.getByText("Bahrain Grand Prix")).toBeDefined();
    expect(screen.getByText("Max Verstappen")).toBeDefined();
    expect(screen.getByText("Red Bull")).toBeDefined();
    expect(screen.getByText("5 / 6 Classified")).toBeDefined();
  });

  it("renders RaceResultsTable with driver standings, position change, and DNF status", () => {
    const results: RaceResultItem[] = [
      {
        driver_id: "max_verstappen",
        given_name: "Max",
        family_name: "Verstappen",
        constructor_id: "red_bull",
        constructor_name: "Red Bull",
        car_number: 1,
        grid_position: 1,
        source_position: 1,
        position_text: "1",
        points: "26.0",
        laps_completed: 57,
        status: "Finished",
        time_millis: 5504742,
        time_text: "1:31:44.742",
        fastest_lap_rank: 1,
        fastest_lap_number: 39,
        fastest_lap_time: "1:32.608",
        fastest_lap_time_millis: 92608,
      },
      {
        driver_id: "sargeant",
        given_name: "Logan",
        family_name: "Sargeant",
        constructor_id: "williams",
        constructor_name: "Williams",
        car_number: 2,
        grid_position: 18,
        source_position: null,
        position_text: "R",
        points: "0.0",
        laps_completed: 24,
        status: "Engine",
        time_millis: null,
        time_text: null,
        fastest_lap_rank: null,
        fastest_lap_number: null,
        fastest_lap_time: null,
        fastest_lap_time_millis: null,
      },
    ];

    const gridVsFinish: GridVsFinishItem[] = [
      {
        driver_id: "max_verstappen",
        given_name: "Max",
        family_name: "Verstappen",
        constructor_name: "Red Bull",
        grid_position: 1,
        finish_position: 1,
        position_change: 0,
        status: "Finished",
        points: "26.0",
      },
    ];

    render(<RaceResultsTable results={results} gridVsFinish={gridVsFinish} />);

    expect(screen.getByText("Max Verstappen")).toBeDefined();
    expect(screen.getByText("Logan Sargeant")).toBeDefined();
    expect(screen.getByText("FL")).toBeDefined(); // Fastest Lap badge
    expect(screen.getByText("Engine")).toBeDefined(); // DNF status preserved
  });

  it("renders InsightsSection and expands traceability audit trail", () => {
    const mockInsight: InsightItem = {
      insight_id: "quali_adv:2024:1:max_verstappen:perez",
      rule_id: "QUALIFYING_TEAMMATE_ADVANTAGE",
      category: "QUALIFYING",
      subject_id: "max_verstappen",
      comparison_subject_id: "perez",
      metric: "qualifying_delta_millis",
      direction: "faster",
      magnitude: 358,
      unit: "milliseconds",
      evidence_strength: "LOW",
      sample_size: 1,
      traceability: {
        source_metric: "qualifying_delta_millis",
        source_function: "get_teammate_qualifying_comparison",
        rule_id: "QUALIFYING_TEAMMATE_ADVANTAGE",
        rule_parameters: { threshold_ms: 100 },
        observed_value: -358,
        unit: "milliseconds",
        sample_size: 1,
        minimum_sample_size: 1,
        sign_convention: "Negative delta means driver A was faster than driver B.",
        season_year: 2024,
        round_num: 1,
        race_id: null,
        driver_id: "max_verstappen",
        constructor_id: "red_bull",
      },
    };

    render(<InsightsSection insights={[mockInsight]} />);

    expect(screen.getByText("max_verstappen")).toBeDefined();
    expect(screen.getByText("View Audit Trail")).toBeDefined();

    // Click to expand audit trail
    fireEvent.click(screen.getByText("View Audit Trail"));

    expect(screen.getByText("Traceability Audit Trail")).toBeDefined();
    expect(screen.getByText("get_teammate_qualifying_comparison")).toBeDefined();
  });

  it("renders NarrativeSection in available state with provider and limitations", () => {
    const narrativeData: NarrativeResponse = {
      status: "available",
      provider: "groq",
      model: "openai/gpt-oss-120b",
      narrative: "Verstappen took pole position and secured a dominant victory.",
      limitations: ["Sample size is 1 race."],
      evidence_references: ["qualifying_delta_millis"],
      error: null,
    };

    render(<NarrativeSection narrativeData={narrativeData} loading={false} />);

    expect(screen.getByText("Grounded AI Race Explanation")).toBeDefined();
    expect(screen.getByText(/groq/i)).toBeDefined();
    expect(screen.getByText("Verstappen took pole position and secured a dominant victory.")).toBeDefined();
    expect(screen.getByText("Sample size is 1 race.")).toBeDefined();
  });

  it("renders NarrativeSection fallback gracefully when unavailable without throwing", () => {
    const narrativeData: NarrativeResponse = {
      status: "unavailable",
      provider: null,
      model: null,
      narrative: null,
      limitations: [],
      evidence_references: [],
      error: "AI Provider API key not configured.",
    };

    render(<NarrativeSection narrativeData={narrativeData} loading={false} />);

    expect(screen.getByText("AI Explanation Unavailable")).toBeDefined();
    expect(screen.getByText("AI Provider API key not configured.")).toBeDefined();
    expect(screen.getByText(/Deterministic Analytics Intact/i)).toBeDefined();
  });

  it("triggers onSelect callback when selecting a race in RaceSelector", () => {
    const races: RaceListItem[] = [
      {
        season_year: 2024,
        round: 1,
        race_name: "Bahrain Grand Prix",
        circuit_name: "Sakhir",
        race_date: "2024-03-02",
      },
      {
        season_year: 2024,
        round: 2,
        race_name: "Saudi Arabian Grand Prix",
        circuit_name: "Jeddah",
        race_date: "2024-03-09",
      },
    ];

    const onSelect = vi.fn();
    render(
      <RaceSelector
        races={races}
        selectedSeason={2024}
        selectedRound={1}
        onSelect={onSelect}
      />
    );

    const roundSelect = screen.getByLabelText("Select Grand Prix Round");
    fireEvent.change(roundSelect, { target: { value: "2" } });

    expect(onSelect).toHaveBeenCalledWith(2024, 2);
  });
});

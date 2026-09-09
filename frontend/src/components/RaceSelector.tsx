import React from "react";
import { Calendar, Flag } from "lucide-react";
import type { RaceListItem } from "../types/api";

interface RaceSelectorProps {
  races: RaceListItem[];
  selectedSeason: number;
  selectedRound: number;
  onSelect: (season: number, round: number) => void;
  disabled?: boolean;
}

export const RaceSelector: React.FC<RaceSelectorProps> = ({
  races,
  selectedSeason,
  selectedRound,
  onSelect,
  disabled = false,
}) => {
  // Extract distinct seasons
  const seasons = Array.from(new Set(races.map((r) => r.season_year))).sort(
    (a, b) => b - a
  );

  // Races in current season
  const roundsInSeason = races
    .filter((r) => r.season_year === selectedSeason)
    .sort((a, b) => a.round - b.round);

  const handleSeasonChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const season = parseInt(e.target.value, 10);
    const firstRound = races.find((r) => r.season_year === season)?.round || 1;
    onSelect(season, firstRound);
  };

  const handleRoundChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const round = parseInt(e.target.value, 10);
    onSelect(selectedSeason, round);
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Season select */}
      <div className="relative flex items-center">
        <label htmlFor="season-select" className="sr-only">
          Select Season
        </label>
        <div className="absolute left-3 pointer-events-none text-gray-400">
          <Calendar className="w-4 h-4" />
        </div>
        <select
          id="season-select"
          value={selectedSeason}
          onChange={handleSeasonChange}
          disabled={disabled || seasons.length === 0}
          className="select-input pl-9 pr-8"
        >
          {seasons.map((s) => (
            <option key={s} value={s}>
              Season {s}
            </option>
          ))}
        </select>
      </div>

      {/* Round / Grand Prix select */}
      <div className="relative flex items-center">
        <label htmlFor="round-select" className="sr-only">
          Select Grand Prix Round
        </label>
        <div className="absolute left-3 pointer-events-none text-gray-400">
          <Flag className="w-4 h-4 text-f1-red" />
        </div>
        <select
          id="round-select"
          value={selectedRound}
          onChange={handleRoundChange}
          disabled={disabled || roundsInSeason.length === 0}
          className="select-input pl-9 pr-8"
        >
          {roundsInSeason.map((r) => (
            <option key={r.round} value={r.round}>
              R{r.round} — {r.race_name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

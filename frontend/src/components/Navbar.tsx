import React from "react";
import { RaceSelector } from "./RaceSelector";
import type { RaceListItem } from "../types/api";

interface NavbarProps {
  races: RaceListItem[];
  selectedSeason: number;
  selectedRound: number;
  onSelectRace: (season: number, round: number) => void;
  apiConnected: boolean;
  loading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  races,
  selectedSeason,
  selectedRound,
  onSelectRace,
  apiConnected,
  loading,
}) => {
  return (
    <header className="sticky top-0 z-50 bg-surface-dark/95 backdrop-blur border-b border-border-subtle py-3 px-4 sm:px-6">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-black text-xl tracking-tighter text-text-primary">
            <span className="bg-f1-red text-white px-2 py-0.5 rounded font-black text-sm tracking-widest">
              F1
            </span>
            <span>RACE INTELLIGENCE</span>
          </div>

          <div className="hidden md:flex items-center gap-1.5 text-xs text-text-muted border-l border-border-subtle pl-3">
            <span
              className={`w-2 h-2 rounded-full ${
                apiConnected ? "bg-green-500 shadow-sm shadow-green-500/50" : "bg-red-500"
              }`}
            ></span>
            <span>{apiConnected ? "API Connected" : "API Offline"}</span>
          </div>
        </div>

        {/* Controls: Race Selector */}
        <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
          <RaceSelector
            races={races}
            selectedSeason={selectedSeason}
            selectedRound={selectedRound}
            onSelect={onSelectRace}
            disabled={loading}
          />
        </div>
      </div>
    </header>
  );
};

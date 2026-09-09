import React from "react";
import { Trophy, MapPin, Calendar, CheckCircle2, Timer } from "lucide-react";
import type { RaceOverview } from "../types/api";

interface HeroHeaderProps {
  overview: RaceOverview | null;
}

export const HeroHeader: React.FC<HeroHeaderProps> = ({ overview }) => {
  if (!overview) return null;

  const winnerName =
    overview.winner_given_name && overview.winner_family_name
      ? `${overview.winner_given_name} ${overview.winner_family_name}`
      : "Not classified";

  return (
    <div className="hero-card border border-border-subtle bg-surface-card rounded-xl p-6 relative overflow-hidden shadow-lg">
      {/* Red motorsport decorative stripe */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-f1-red via-red-600 to-amber-500"></div>

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        {/* Left: Race context */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="badge-pill bg-f1-red/20 text-f1-red border border-f1-red/30">
              {overview.season_year} Season
            </span>
            <span className="badge-pill bg-surface-elevated text-text-secondary border border-border-subtle">
              Round {overview.round}
            </span>
          </div>

          <h1 className="text-3xl lg:text-4xl font-black text-text-primary tracking-tight">
            {overview.race_name}
          </h1>

          <div className="flex flex-wrap items-center gap-4 text-sm text-text-muted mt-2">
            <span className="flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-gray-400" />
              {overview.circuit_name}
            </span>
            <span className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-gray-400" />
              {overview.race_date}
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              {overview.classified_count} / {overview.total_result_count} Classified
            </span>
          </div>
        </div>

        {/* Right: Winner badge card */}
        <div className="flex items-center gap-4 bg-surface-elevated/80 border border-border-subtle/80 rounded-lg p-4 min-w-[280px]">
          <div className="w-12 h-12 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center shrink-0">
            <Trophy className="w-6 h-6 text-amber-400" />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-amber-400/90 font-bold">
              Race Winner
            </div>
            <div className="text-lg font-bold text-text-primary">{winnerName}</div>
            <div className="text-xs text-text-secondary font-medium">
              {overview.winner_constructor || "—"}
            </div>
            {overview.winner_time_text && (
              <div className="flex items-center gap-1 text-xs text-text-muted mt-1 font-mono">
                <Timer className="w-3 h-3" />
                {overview.winner_time_text}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

import React from "react";
import { Award, Users } from "lucide-react";
import type { StandingsResponse } from "../types/api";
import { formatPoints } from "../utils/formatters";

interface StandingsSectionProps {
  data: StandingsResponse | null;
}

export const StandingsSection: React.FC<StandingsSectionProps> = ({ data }) => {
  if (!data || (data.drivers.length === 0 && data.constructors.length === 0)) {
    return (
      <div className="card text-center py-8 text-text-muted">
        No championship standings recorded after this round.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 1. Driver Championship Standings */}
      <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Award className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-bold text-text-primary tracking-tight">
            Driver Championship Standings
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" role="table">
            <thead>
              <tr className="border-b border-border-subtle text-xs uppercase text-text-muted">
                <th className="py-2.5 px-3 font-semibold">Pos</th>
                <th className="py-2.5 px-3 font-semibold">Driver</th>
                <th className="py-2.5 px-3 font-semibold text-center">Wins</th>
                <th className="py-2.5 px-3 font-semibold text-right">Points</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle/50 font-sans">
              {data.drivers.map((d) => (
                <tr
                  key={d.driver_id}
                  className="hover:bg-surface-elevated/40 transition-colors"
                >
                  <td className="py-2.5 px-3 font-bold">
                    <span
                      className={`inline-flex items-center justify-center w-6 h-6 rounded ${
                        d.position === 1
                          ? "bg-amber-500 text-black font-extrabold"
                          : d.position === 2
                          ? "bg-gray-300 text-black font-extrabold"
                          : d.position === 3
                          ? "bg-amber-700 text-white font-extrabold"
                          : "text-text-primary"
                      }`}
                    >
                      {d.position}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-text-primary">
                    {d.given_name} {d.family_name}
                  </td>
                  <td className="py-2.5 px-3 text-center font-mono text-xs text-text-secondary">
                    {d.wins}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono font-bold text-text-primary">
                    {formatPoints(d.points)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. Constructor Championship Standings */}
      <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-5 h-5 text-cyan-400" />
          <h3 className="text-lg font-bold text-text-primary tracking-tight">
            Constructor Championship Standings
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" role="table">
            <thead>
              <tr className="border-b border-border-subtle text-xs uppercase text-text-muted">
                <th className="py-2.5 px-3 font-semibold">Pos</th>
                <th className="py-2.5 px-3 font-semibold">Constructor</th>
                <th className="py-2.5 px-3 font-semibold text-center">Wins</th>
                <th className="py-2.5 px-3 font-semibold text-right">Points</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle/50 font-sans">
              {data.constructors.map((c) => (
                <tr
                  key={c.constructor_id}
                  className="hover:bg-surface-elevated/40 transition-colors"
                >
                  <td className="py-2.5 px-3 font-bold">
                    <span
                      className={`inline-flex items-center justify-center w-6 h-6 rounded ${
                        c.position === 1
                          ? "bg-amber-500 text-black font-extrabold"
                          : "text-text-primary"
                      }`}
                    >
                      {c.position}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-text-primary">
                    {c.constructor_name}
                  </td>
                  <td className="py-2.5 px-3 text-center font-mono text-xs text-text-secondary">
                    {c.wins}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono font-bold text-text-primary">
                    {formatPoints(c.points)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

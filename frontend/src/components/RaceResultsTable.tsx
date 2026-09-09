import React from "react";
import { Zap } from "lucide-react";
import type { GridVsFinishItem, RaceResultItem } from "../types/api";
import { formatPoints, formatPositionChange } from "../utils/formatters";

interface RaceResultsTableProps {
  results: RaceResultItem[];
  gridVsFinish?: GridVsFinishItem[];
}

export const RaceResultsTable: React.FC<RaceResultsTableProps> = ({
  results,
  gridVsFinish = [],
}) => {
  if (!results || results.length === 0) {
    return (
      <div className="card text-center py-8 text-text-muted">
        No race results available for this event.
      </div>
    );
  }

  // Pre-index backend-calculated position changes by driver_id
  const posChangeMap = new Map<string, number | null>();
  for (const item of gridVsFinish) {
    posChangeMap.set(item.driver_id, item.position_change);
  }

  return (
    <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-text-primary tracking-tight">
          Race Classification
        </h2>
        <span className="text-xs text-text-muted">
          {results.length} total entries recorded
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm" role="table">
          <thead>
            <tr className="border-b border-border-subtle text-xs uppercase text-text-muted">
              <th className="py-2.5 px-3 font-semibold">Pos</th>
              <th className="py-2.5 px-3 font-semibold">No</th>
              <th className="py-2.5 px-3 font-semibold">Driver</th>
              <th className="py-2.5 px-3 font-semibold">Constructor</th>
              <th className="py-2.5 px-3 font-semibold text-center">Grid</th>
              <th className="py-2.5 px-3 font-semibold text-center">Change</th>
              <th className="py-2.5 px-3 font-semibold">Laps</th>
              <th className="py-2.5 px-3 font-semibold">Time / Gap</th>
              <th className="py-2.5 px-3 font-semibold">Status</th>
              <th className="py-2.5 px-3 font-semibold text-right">Pts</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle/50 font-sans">
            {results.map((row) => {
              const fullName = `${row.given_name} ${row.family_name}`;
              // Consume pre-computed backend position change (never recomputed in frontend)
              const posChange = posChangeMap.get(row.driver_id) ?? null;
              const changeInfo = formatPositionChange(posChange);
              const isPodium = row.source_position && row.source_position <= 3;
              const isDNF = row.status !== "Finished" && !row.status.startsWith("+");

              return (
                <tr
                  key={row.driver_id}
                  className={`hover:bg-surface-elevated/40 transition-colors ${
                    isPodium ? "bg-amber-500/5 font-medium" : ""
                  }`}
                >
                  {/* Position */}
                  <td className="py-3 px-3 font-bold">
                    {row.source_position ? (
                      <span
                        className={`inline-flex items-center justify-center w-6 h-6 rounded ${
                          row.source_position === 1
                            ? "bg-amber-500 text-black font-extrabold"
                            : row.source_position === 2
                            ? "bg-gray-300 text-black font-extrabold"
                            : row.source_position === 3
                            ? "bg-amber-700 text-white font-extrabold"
                            : "text-text-primary"
                        }`}
                      >
                        {row.source_position}
                      </span>
                    ) : (
                      <span className="text-red-400 font-bold">
                        {row.position_text || "DNF"}
                      </span>
                    )}
                  </td>

                  {/* Car Number */}
                  <td className="py-3 px-3 font-mono text-xs text-text-muted">
                    {row.car_number != null ? `#${row.car_number}` : "—"}
                  </td>

                  {/* Driver */}
                  <td className="py-3 px-3 font-semibold text-text-primary">
                    <div className="flex items-center gap-2">
                      <span>{fullName}</span>
                      {row.fastest_lap_rank === 1 && (
                        <span
                          className="inline-flex items-center gap-1 text-[11px] font-bold text-purple-400 bg-purple-950/60 px-1.5 py-0.5 rounded border border-purple-500/30"
                          title={`Official Fastest Lap: ${row.fastest_lap_time || "—"}`}
                        >
                          <Zap className="w-3 h-3 fill-purple-400" /> FL
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Constructor */}
                  <td className="py-3 px-3 text-text-secondary">
                    {row.constructor_name}
                  </td>

                  {/* Grid */}
                  <td className="py-3 px-3 text-center font-mono text-xs text-text-muted">
                    {row.grid_position != null ? `P${row.grid_position}` : "Pit Lane"}
                  </td>

                  {/* Position Change */}
                  <td className="py-3 px-3 text-center">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold font-mono ${
                        changeInfo.badgeClass === "pos-gain"
                          ? "bg-green-500/20 text-green-400 border border-green-500/30"
                          : changeInfo.badgeClass === "pos-loss"
                          ? "bg-red-500/20 text-red-400 border border-red-500/30"
                          : "bg-surface-elevated text-text-muted border border-border-subtle"
                      }`}
                    >
                      <span>{changeInfo.icon}</span>
                      <span>{changeInfo.label}</span>
                    </span>
                  </td>

                  {/* Laps */}
                  <td className="py-3 px-3 font-mono text-xs text-text-muted">
                    {row.laps_completed}
                  </td>

                  {/* Time / Gap */}
                  <td className="py-3 px-3 font-mono text-xs text-text-secondary">
                    {row.time_text || (isDNF ? "—" : row.status)}
                  </td>

                  {/* Status */}
                  <td className="py-3 px-3 text-xs">
                    <span
                      className={
                        isDNF
                          ? "text-red-400 font-semibold"
                          : "text-text-muted"
                      }
                    >
                      {row.status}
                    </span>
                  </td>

                  {/* Points */}
                  <td className="py-3 px-3 text-right font-mono font-bold text-text-primary">
                    {formatPoints(row.points)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

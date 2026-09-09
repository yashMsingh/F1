import React from "react";
import { Timer, AlertCircle } from "lucide-react";
import type { LapTimesResponse } from "../types/api";
import { formatMillisToLapTime } from "../utils/formatters";

interface LapTimeSectionProps {
  data: LapTimesResponse | null;
}

export const LapTimeSection: React.FC<LapTimeSectionProps> = ({ data }) => {
  if (!data || data.laps.length === 0) {
    return (
      <div className="card text-center py-8 text-text-muted">
        No lap time data recorded for this event.
      </div>
    );
  }

  return (
    <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Timer className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-bold text-text-primary tracking-tight">
            Recorded Lap Time Summary
          </h3>
        </div>

        {/* Epistemic note: fastest recorded vs official fastest lap */}
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-elevated border border-border-subtle text-xs text-text-muted">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
          <span>
            Note: Fastest recorded lap from timing telemetry may differ from official FIA fastest lap (e.g. track limits).
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm" role="table">
          <thead>
            <tr className="border-b border-border-subtle text-xs uppercase text-text-muted">
              <th className="py-2.5 px-3 font-semibold">Driver</th>
              <th className="py-2.5 px-3 font-semibold text-center">Recorded Laps</th>
              <th className="py-2.5 px-3 font-semibold text-right">Fastest Recorded Lap</th>
              <th className="py-2.5 px-3 font-semibold text-right">Average Lap Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle/50 font-sans">
            {data.laps.map((l) => (
              <tr
                key={l.driver_id}
                className="hover:bg-surface-elevated/40 transition-colors"
              >
                <td className="py-2.5 px-3 font-semibold text-text-primary">
                  {l.given_name} {l.family_name}
                </td>
                <td className="py-2.5 px-3 text-center font-mono text-xs text-text-secondary">
                  {l.lap_count}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-xs font-bold text-purple-400">
                  {formatMillisToLapTime(l.fastest_lap_millis)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-xs text-text-secondary">
                  {formatMillisToLapTime(l.avg_lap_millis)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

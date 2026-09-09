import React from "react";
import { Wrench, ShieldAlert } from "lucide-react";
import type { PitStopsResponse } from "../types/api";
import { formatMillisToSeconds } from "../utils/formatters";

interface PitStopSectionProps {
  data: PitStopsResponse | null;
}

export const PitStopSection: React.FC<PitStopSectionProps> = ({ data }) => {
  if (!data || (data.drivers.length === 0 && data.constructors.length === 0)) {
    return (
      <div className="card text-center py-8 text-text-muted">
        No pit stop data available for this event.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1. Driver Pit Stop Performance */}
      <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Wrench className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-bold text-text-primary tracking-tight">
            Driver Pit Stop Analysis
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" role="table">
            <thead>
              <tr className="border-b border-border-subtle text-xs uppercase text-text-muted">
                <th className="py-2.5 px-3 font-semibold">Driver</th>
                <th className="py-2.5 px-3 font-semibold text-center">Stops</th>
                <th className="py-2.5 px-3 font-semibold text-right">Fastest Stop</th>
                <th className="py-2.5 px-3 font-semibold text-right">Average Stop</th>
                <th className="py-2.5 px-3 font-semibold text-right">Total Pit Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle/50 font-sans">
              {data.drivers.map((d) => (
                <tr
                  key={d.driver_id}
                  className="hover:bg-surface-elevated/40 transition-colors"
                >
                  <td className="py-2.5 px-3 font-semibold text-text-primary">
                    {d.given_name} {d.family_name}
                  </td>
                  <td className="py-2.5 px-3 text-center font-mono font-bold text-text-secondary">
                    {d.stop_count}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-xs font-semibold text-green-400">
                    {formatMillisToSeconds(d.fastest_stop_millis)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-xs text-text-secondary">
                    {formatMillisToSeconds(d.avg_duration_millis)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-xs text-text-muted">
                    {formatMillisToSeconds(d.total_duration_millis)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. Constructor Pit Stop Performance */}
      <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <ShieldAlert className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-bold text-text-primary tracking-tight">
            Constructor Pit Stop Execution
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.constructors.map((c) => (
            <div
              key={c.constructor_id}
              className="p-4 rounded-lg bg-surface-elevated/50 border border-border-subtle"
            >
              <div className="font-bold text-text-primary text-base mb-2">
                {c.constructor_name}
              </div>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-text-muted">Total Stops:</span>
                  <span className="font-mono font-bold text-text-primary">
                    {c.total_stops}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Fastest Team Stop:</span>
                  <span className="font-mono font-bold text-green-400">
                    {formatMillisToSeconds(c.fastest_stop_millis)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Average Team Stop:</span>
                  <span className="font-mono text-text-secondary">
                    {formatMillisToSeconds(c.avg_duration_millis)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

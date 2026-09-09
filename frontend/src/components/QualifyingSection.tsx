import React from "react";
import { Info, Gauge } from "lucide-react";
import type { QualifyingResponse } from "../types/api";
import { formatDeltaMillis, formatMillisToLapTime } from "../utils/formatters";

interface QualifyingSectionProps {
  data: QualifyingResponse | null;
}

export const QualifyingSection: React.FC<QualifyingSectionProps> = ({ data }) => {
  if (!data || (data.qualifying_order.length === 0 && data.teammate_comparisons.length === 0)) {
    return (
      <div className="card text-center py-8 text-text-muted">
        No qualifying data available for this event.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1. Teammate Qualifying Comparisons */}
      {data.teammate_comparisons.length > 0 && (
        <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
            <div>
              <h3 className="text-lg font-bold text-text-primary tracking-tight">
                Teammate Qualifying Deltas
              </h3>
              <p className="text-xs text-text-muted mt-0.5">
                Head-to-head comparison within each constructor
              </p>
            </div>

            {/* Sign convention explanation badge */}
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-blue-950/40 border border-blue-500/30 text-xs text-blue-300">
              <Info className="w-3.5 h-3.5 shrink-0 text-blue-400" />
              <span>
                <strong>Sign Convention:</strong> Negative (–) = Driver A faster; Positive (+) = Driver B faster
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.teammate_comparisons.map((tc) => {
              const delta = tc.delta_millis;
              const hasDelta = delta != null;
              const isDriverAFaster = hasDelta && delta < 0;
              const isDriverBFaster = hasDelta && delta > 0;

              return (
                <div
                  key={tc.constructor_id}
                  className="p-4 rounded-lg bg-surface-elevated/50 border border-border-subtle"
                >
                  <div className="text-xs uppercase font-bold tracking-wider text-text-muted mb-3 flex items-center justify-between">
                    <span>{tc.constructor_name}</span>
                    <span className="font-mono text-text-secondary">
                      {formatDeltaMillis(delta)}
                    </span>
                  </div>

                  <div className="space-y-2">
                    {/* Driver A */}
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-text-primary">
                          {tc.driver_a_name}
                        </span>
                        {isDriverAFaster && (
                          <span className="text-[10px] uppercase font-bold px-1.5 py-0.2 bg-green-500/20 text-green-400 border border-green-500/30 rounded">
                            Faster
                          </span>
                        )}
                      </div>
                      <span className="font-mono text-xs text-text-secondary">
                        {formatMillisToLapTime(tc.best_time_a_millis)}
                      </span>
                    </div>

                    {/* Driver B */}
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-text-primary">
                          {tc.driver_b_name}
                        </span>
                        {isDriverBFaster && (
                          <span className="text-[10px] uppercase font-bold px-1.5 py-0.2 bg-green-500/20 text-green-400 border border-green-500/30 rounded">
                            Faster
                          </span>
                        )}
                      </div>
                      <span className="font-mono text-xs text-text-secondary">
                        {formatMillisToLapTime(tc.best_time_b_millis)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 2. Qualifying Classification Order */}
      <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Gauge className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-bold text-text-primary tracking-tight">
            Qualifying Classification Order
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" role="table">
            <thead>
              <tr className="border-b border-border-subtle text-xs uppercase text-text-muted">
                <th className="py-2.5 px-3 font-semibold">Pos</th>
                <th className="py-2.5 px-3 font-semibold">Driver</th>
                <th className="py-2.5 px-3 font-semibold">Constructor</th>
                <th className="py-2.5 px-3 font-semibold text-right">Q1 Time</th>
                <th className="py-2.5 px-3 font-semibold text-right">Q2 Time</th>
                <th className="py-2.5 px-3 font-semibold text-right">Q3 Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle/50 font-sans">
              {data.qualifying_order.map((q) => (
                <tr
                  key={q.driver_id}
                  className="hover:bg-surface-elevated/40 transition-colors"
                >
                  <td className="py-2.5 px-3 font-bold">
                    <span
                      className={`inline-flex items-center justify-center w-6 h-6 rounded ${
                        q.position === 1
                          ? "bg-amber-500 text-black font-extrabold"
                          : "text-text-primary"
                      }`}
                    >
                      {q.position}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-text-primary">
                    {q.given_name} {q.family_name}
                  </td>
                  <td className="py-2.5 px-3 text-text-secondary">
                    {q.constructor_name}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-xs text-text-muted">
                    {formatMillisToLapTime(q.q1_time_millis)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-xs text-text-muted">
                    {formatMillisToLapTime(q.q2_time_millis)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-xs font-bold text-text-primary">
                    {formatMillisToLapTime(q.q3_time_millis)}
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

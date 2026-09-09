import React from "react";
import { ArrowRight, TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { GridVsFinishItem } from "../types/api";

interface GridVsFinishChartProps {
  items: GridVsFinishItem[];
}

export const GridVsFinishChart: React.FC<GridVsFinishChartProps> = ({ items }) => {
  if (!items || items.length === 0) return null;

  // Filter classified drivers with valid grid & finish
  const validItems = items.filter(
    (item) => item.grid_position != null && item.finish_position != null
  );

  return (
    <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-text-primary tracking-tight">
            Grid to Finish Progress
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Positions gained or conceded relative to starting grid
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {validItems.map((item) => {
          const change = item.position_change ?? 0;
          const isGain = change > 0;
          const isLoss = change < 0;

          return (
            <div
              key={item.driver_id}
              className="flex items-center justify-between p-3 rounded-lg bg-surface-elevated/50 border border-border-subtle hover:border-border-hover transition-colors"
            >
              <div className="min-w-0 pr-2">
                <div className="font-semibold text-sm text-text-primary truncate">
                  {item.given_name} {item.family_name}
                </div>
                <div className="text-xs text-text-secondary truncate">
                  {item.constructor_name}
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                {/* Grid -> Finish */}
                <div className="flex items-center gap-1.5 font-mono text-xs text-text-muted">
                  <span className="bg-surface-elevated px-1.5 py-0.5 rounded border border-border-subtle">
                    P{item.grid_position}
                  </span>
                  <ArrowRight className="w-3 h-3 text-gray-500" />
                  <span className="bg-surface-elevated px-1.5 py-0.5 rounded border border-border-subtle font-bold text-text-primary">
                    P{item.finish_position}
                  </span>
                </div>

                {/* Change Badge */}
                <div
                  className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-bold min-w-[44px] justify-center ${
                    isGain
                      ? "bg-green-500/20 text-green-400 border border-green-500/30"
                      : isLoss
                      ? "bg-red-500/20 text-red-400 border border-red-500/30"
                      : "bg-surface-elevated text-text-muted border border-border-subtle"
                  }`}
                >
                  {isGain && <TrendingUp className="w-3 h-3" />}
                  {isLoss && <TrendingDown className="w-3 h-3" />}
                  {!isGain && !isLoss && <Minus className="w-3 h-3" />}
                  <span>{isGain ? `+${change}` : change}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

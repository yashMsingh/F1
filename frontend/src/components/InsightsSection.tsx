import React, { useState } from "react";
import { ChevronDown, ChevronUp, Database, CheckCircle } from "lucide-react";
import type { InsightItem } from "../types/api";

interface InsightsSectionProps {
  insights: InsightItem[];
}

export const InsightsSection: React.FC<InsightsSectionProps> = ({ insights }) => {
  const [expandedInsightId, setExpandedInsightId] = useState<string | null>(null);

  if (!insights || insights.length === 0) {
    return (
      <div className="card border border-border-subtle bg-surface-card rounded-xl p-8 text-center text-text-muted">
        No deterministic insights met statistical thresholds for this Grand Prix.
      </div>
    );
  }

  const toggleExpand = (id: string) => {
    setExpandedInsightId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="card border border-border-subtle bg-surface-card rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-red-600/20 border border-red-600/40 flex items-center justify-center">
            <Database className="w-4 h-4 text-f1-red" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-text-primary tracking-tight">
              Deterministic Insights Engine
            </h2>
            <p className="text-xs text-text-muted mt-0.5">
              Rule-based statistical findings strictly derived from persisted telemetry & database records
            </p>
          </div>
        </div>

        <span className="badge-pill bg-surface-elevated text-text-secondary border border-border-subtle">
          {insights.length} verified findings
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {insights.map((ins) => {
          const isExpanded = expandedInsightId === ins.insight_id;
          const strengthColor =
            ins.evidence_strength === "HIGH"
              ? "bg-green-500/20 text-green-400 border-green-500/30"
              : ins.evidence_strength === "MODERATE"
              ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
              : ins.evidence_strength === "LOW"
              ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
              : "bg-gray-500/20 text-gray-400 border-gray-500/30";

          return (
            <div
              key={ins.insight_id}
              className={`rounded-lg border transition-all ${
                isExpanded
                  ? "bg-surface-elevated border-border-hover shadow-md"
                  : "bg-surface-elevated/50 border-border-subtle hover:border-border-hover"
              }`}
            >
              <div className="p-4">
                {/* Header: Category & Evidence Strength */}
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono uppercase tracking-wider font-bold text-text-muted bg-surface-card px-2 py-0.5 rounded border border-border-subtle">
                    {ins.category}
                  </span>

                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${strengthColor}`}
                  >
                    Strength: {ins.evidence_strength}
                  </span>
                </div>

                {/* Main Subject & Finding */}
                <div className="mb-2">
                  <div className="font-bold text-base text-text-primary">
                    {ins.subject_id}
                    {ins.comparison_subject_id && (
                      <span className="text-text-muted font-normal">
                        {" "}
                        vs {ins.comparison_subject_id}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-text-secondary mt-1">
                    Observed:{" "}
                    <strong className="text-text-primary">
                      {ins.direction} ({ins.magnitude != null ? ins.magnitude : "—"} {ins.unit || ""})
                    </strong>{" "}
                    on <code className="text-[11px] font-mono text-cyan-300">{ins.metric}</code>
                  </div>
                </div>

                {/* Sample Size info */}
                <div className="flex items-center justify-between text-xs text-text-muted mt-3 pt-2 border-t border-border-subtle/50">
                  <span>Sample size: {ins.sample_size}</span>
                  <button
                    onClick={() => toggleExpand(ins.insight_id)}
                    className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 font-semibold"
                    aria-expanded={isExpanded}
                  >
                    <span>{isExpanded ? "Hide Audit Trail" : "View Audit Trail"}</span>
                    {isExpanded ? (
                      <ChevronUp className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Expandable Traceability Audit Trail */}
              {isExpanded && (
                <div className="px-4 pb-4 pt-2 border-t border-border-subtle bg-surface-card/60 rounded-b-lg text-xs space-y-2 font-mono">
                  <div className="text-[11px] font-sans font-bold uppercase tracking-wider text-text-muted mb-1 flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                    Traceability Audit Trail
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-text-secondary">
                    <div>
                      <span className="text-text-muted block text-[10px]">RULE ID:</span>
                      <span className="text-text-primary">{ins.rule_id}</span>
                    </div>
                    <div>
                      <span className="text-text-muted block text-[10px]">SOURCE FUNCTION:</span>
                      <span className="text-text-primary">{ins.traceability.source_function}</span>
                    </div>
                    <div>
                      <span className="text-text-muted block text-[10px]">SOURCE METRIC:</span>
                      <span className="text-cyan-300">{ins.traceability.source_metric}</span>
                    </div>
                    <div>
                      <span className="text-text-muted block text-[10px]">OBSERVED VALUE:</span>
                      <span className="text-text-primary">
                        {String(ins.traceability.observed_value)} {ins.traceability.unit || ""}
                      </span>
                    </div>
                    <div>
                      <span className="text-text-muted block text-[10px]">MIN SAMPLE REQ:</span>
                      <span className="text-text-primary">{ins.traceability.minimum_sample_size}</span>
                    </div>
                    <div>
                      <span className="text-text-muted block text-[10px]">SAMPLE SIZE:</span>
                      <span className="text-text-primary">{ins.traceability.sample_size}</span>
                    </div>
                  </div>

                  {ins.traceability.sign_convention && (
                    <div className="mt-2 pt-1 border-t border-border-subtle/50 text-[11px] font-sans text-text-muted">
                      <strong>Sign Convention:</strong> {ins.traceability.sign_convention}
                    </div>
                  )}

                  {Object.keys(ins.traceability.rule_parameters || {}).length > 0 && (
                    <div className="mt-1 text-[10px] text-text-muted">
                      <span>Parameters: </span>
                      {JSON.stringify(ins.traceability.rule_parameters)}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

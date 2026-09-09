import React from "react";
import { Sparkles, Bot, AlertTriangle, ShieldCheck, Cpu } from "lucide-react";
import type { NarrativeResponse } from "../types/api";

interface NarrativeSectionProps {
  narrativeData: NarrativeResponse | null;
  loading: boolean;
}

export const NarrativeSection: React.FC<NarrativeSectionProps> = ({
  narrativeData,
  loading,
}) => {
  return (
    <div className="card border border-purple-500/30 bg-surface-card rounded-xl p-6 shadow-md relative overflow-hidden">
      {/* Decorative gradient top bar distinguishing AI narrative from deterministic data */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-indigo-500 to-pink-500"></div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-purple-500/20 border border-purple-500/40 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-purple-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-text-primary tracking-tight">
                Grounded AI Race Explanation
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                Narrator Layer
              </span>
            </div>
            <p className="text-xs text-text-muted mt-0.5">
              Natural-language synthesis strictly constrained to approved deterministic statistical findings
            </p>
          </div>
        </div>

        {/* Active Provider Info */}
        {narrativeData?.provider && (
          <div className="flex items-center gap-1.5 text-xs text-text-muted bg-surface-elevated px-2.5 py-1 rounded border border-border-subtle">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span>
              Provider: <strong className="text-text-primary uppercase">{narrativeData.provider}</strong>
              {narrativeData.model && (
                <span className="text-text-muted"> ({narrativeData.model})</span>
              )}
            </span>
          </div>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="space-y-2.5 animate-pulse py-4">
          <div className="h-4 bg-surface-elevated/70 rounded w-full"></div>
          <div className="h-4 bg-surface-elevated/70 rounded w-5/6"></div>
          <div className="h-4 bg-surface-elevated/70 rounded w-4/6"></div>
          <div className="text-xs text-purple-300/60 font-mono mt-2 flex items-center gap-2">
            <Bot className="w-3.5 h-3.5 animate-bounce" />
            Synthesizing deterministic evidence...
          </div>
        </div>
      )}

      {/* Fallback / Error state: AI unavailable */}
      {!loading && (!narrativeData || narrativeData.status === "unavailable") && (
        <div className="p-4 rounded-lg bg-surface-elevated/60 border border-border-subtle text-text-secondary text-sm space-y-2">
          <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs uppercase tracking-wider">
            <AlertTriangle className="w-4 h-4" />
            AI Explanation Unavailable
          </div>
          <p className="text-xs text-text-muted">
            {narrativeData?.error || "AI provider credentials unconfigured or timed out."}
          </p>
          <div className="text-xs text-text-secondary bg-surface-card p-2.5 rounded border border-border-subtle flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-green-400 shrink-0" />
            <span>
              <strong>Deterministic Analytics Intact:</strong> The underlying SQL, statistics, and deterministic insight engine remain 100% operational.
            </span>
          </div>
        </div>
      )}

      {/* Available state */}
      {!loading && narrativeData?.status === "available" && narrativeData.narrative && (
        <div className="space-y-4">
          <div className="text-sm sm:text-base text-text-primary leading-relaxed bg-surface-elevated/40 p-4 rounded-lg border border-purple-500/20">
            {narrativeData.narrative}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs border-t border-border-subtle/60">
            {/* Referenced Evidence */}
            {narrativeData.evidence_references && narrativeData.evidence_references.length > 0 && (
              <div>
                <span className="font-bold text-text-secondary block mb-1">
                  Evidence Anchors:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {narrativeData.evidence_references.map((ref, idx) => (
                    <span
                      key={idx}
                      className="font-mono text-[11px] px-2 py-0.5 rounded bg-surface-elevated text-cyan-300 border border-border-subtle"
                    >
                      {ref}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Documented Limitations */}
            {narrativeData.limitations && narrativeData.limitations.length > 0 && (
              <div>
                <span className="font-bold text-text-secondary block mb-1">
                  Epistemic Limitations:
                </span>
                <ul className="list-disc list-inside text-text-muted space-y-0.5">
                  {narrativeData.limitations.map((lim, idx) => (
                    <li key={idx}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

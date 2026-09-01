# ADR 0001: Separation of Truth (Database) and Explanation (LLM)

> **Status**: Accepted
> **Date**: 2026-09-01
> **Deciders**: Technical Lead & Senior Software Architect

---

## Context

The F1 Race Intelligence platform aims to provide analytics, statistical insights, and automated natural-language explanations of Formula 1 race performance.

In many AI-enabled platforms, LLMs are improperly tasked with calculating metrics, parsing raw logs on the fly, or generating statistical summaries directly. This approach leads to hallucinated statistics, inconsistent metric definitions, ungrounded speculation, and a lack of auditability.

---

## Decision

We decide that:
1. **The Database & Python Analytics Engine are the sole sources of truth.** All numbers, rankings, rolling averages, Z-scores, and telemetry metrics must be computed deterministically via SQL queries and Python code (Pandas/SciPy).
2. **The LLM is strictly an explanation and natural-language generator.** It receives pre-computed, structured JSON payloads ("Evidence Packages") and translates them into readable insights.
3. **No LLM Data Generation for Charts.** All visualization configurations and numerical chart series come directly from database API endpoints, never from LLM output.
4. **Epistemic Classification.** Every AI statement must explicitly distinguish between observed facts, statistical findings, model predictions, and interpretations.

---

## Alternatives Considered

### Alternative 1: Direct LLM Prompting over Raw Data / RAG
- *Description*: Feed raw race result text or unstructured race summaries into an LLM and prompt it to "summarize key race insights and statistics".
- *Why Rejected*: High risk of hallucinated stats (e.g., wrong lap times, incorrect points totals), impossible to write unit tests for metric correctness, high latency and API cost.

### Alternative 2: End-to-End Autonomous Agentic SQL Generation in Core Pipeline
- *Description*: Have an AI agent write SQL queries dynamically for every standard dashboard metric and chart.
- *Why Rejected*: Slow, non-deterministic, security risk of erroneous SQL mutations or execution timeouts. Dynamic SQL generation will be strictly reserved for Phase 10 ("Ask the Data") behind a read-only DB user with explicit AST keyword whitelisting.

---

## Reasons & Consequences

### Positive Consequences
- **100% Auditability**: Every number shown on the dashboard or in an AI insight can be traced directly back to a SQL query and source API field.
- **Testability**: Unit tests can independently verify analytics logic (`pytest`) without needing LLM calls.
- **Model Agnostic**: The LLM layer can switch between OpenAI, Anthropic, Gemini, or local models without breaking any analytics logic.
- **Lower Cost & Latency**: LLMs are invoked only for verified, high-value candidate findings, not for standard chart rendering.

### Negative / Challenging Consequences
- Requires strict documentation of data schemas and evidence contracts (`docs/ai-insight-spec.md`).
- Higher upfront engineering effort in building deterministic anomaly detectors and evidence package generators.

---

## References
- `docs/product-spec.md`
- `docs/architecture.md`
- `docs/ai-insight-spec.md`
- `AGENTS.md`

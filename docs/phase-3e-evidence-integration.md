# Phase 3E — Longitudinal Evidence Integration

## 1. Overview & Architectural Role

Phase 3E connects the deterministic multi-race analytics and insights established in Phases 3B, 3C, and 3D to the downstream grounded AI narrative and API layers.

```text
PostgreSQL (Rounds 1–5)
      ↓
Longitudinal Analytical SQL (Phase 3B)
      ↓
Longitudinal Statistical Aggregations (Phase 3C)
      ↓
Deterministic Longitudinal Insight Engine (Phase 3D)
      ↓
Application Services Boundary (`LongitudinalInsightService`) (Phase 3E)
      ↓
Evidence Context Builder (`build_evidence_context`) (Phase 3E)
      ↓
Unified Narrative Service (`NarrativeService`) (Phase 3E)
      ↓
FastAPI Endpoints (`POST /api/narrative`, `GET /api/season/{season}/insights`) (Phase 3E)
```

**Non-Negotiable Grounding Constraint**: The LLM is an **explanatory narrator, never an analyst**. All statistics, sample sizes, and win ratios originate strictly from the analytical database. The LLM does not perform math, speculate on causality, or forecast future performance.

---

## 2. Longitudinal Evidence Context

The evidence context builder (`app/ai/context.py`) automatically distinguishes between single-race and multi-race evidence:

- **Scope Detection**:
  - `scope: "race"`: For single-round event observations.
  - `scope: "longitudinal"`: For multi-round aggregates and trajectories (`rounds_included` length > 1 or rule ID prefix `LONGITUDINAL_`).

- **Longitudinal Audit Fields**:
  - `season`: Championship season year.
  - `subject_id` & `comparison_subject_id`: Driver, constructor, or teammate pairing identity.
  - `rule_id`: Deterministic rule identifier.
  - `metric`: Statistical metric evaluated.
  - `observed_value`: Exact numeric aggregate from SQL/statistics.
  - `sample_size` / `valid_observations`: Number of included, valid data points.
  - `excluded_observations`: Excluded unclassified races or non-comparable sessions (e.g. DNFs).
  - `rounds_included`: List of specific championship round numbers included in the evaluation.
  - `evidence_strength`: Statistical evidence rating (`LOW`, `MODERATE`, `HIGH`).
  - `source_function` & `sign_convention`: Traceability audit trail.
  - `explanation`: Deterministic baseline sentence template.

- **Mandatory Caveats Injected**:
  - *"Longitudinal findings describe only the supplied rounds in the observed season; do not extrapolate beyond the observed sample, make career-level conclusions, or predict future performance."*
  - Missing telemetry, tyre compound/degradation, and weather data caveats are strictly enforced.

---

## 3. Grounding Rules & Prompt Engineering

The system prompt (`app/ai/prompts.py`) enforces strict multi-race guidelines:
1. **Descriptive, not predictive**: Narrate historical outcomes across the supplied round range only. Never generate championship predictions, race forecasts, or career-level pronouncements.
2. **Preserve exact sample sizes and exclusions**: State exact valid finishes and acknowledge excluded rounds (e.g., 4 finishes across 5 starts with 1 DNF).
3. **Distinguish GP vs Sprint points**: Separate Grand Prix race points from sprint session points when present in the evidence.
4. **No causal speculation**: Do not infer mechanical, psychological, or setup causes unless explicitly provided in the deterministic evidence package.
5. **No driver ranking or composite scores**: Never synthesize ungrounded driver rankings or subjective claims (e.g., converting a 5–0 qualifying advantage into "Driver X is definitively faster").

---

## 4. Response Validation & Contradiction Detection

The validation layer (`app/ai/validation.py`) enforces post-generation integrity checks:
1. **Schema Validation**: Validates JSON structure, non-empty `narrative`, list of `limitations`, and `evidence_references`.
2. **Direction Contradictions**: Rejects narratives asserting a driver was slower when the insight direction is `FASTER`, or lost positions when `GAINED`.
3. **DNF Exclusion Contradictions**: Flags and rejects any narrative claiming a driver "finished all races" or "had no DNFs" when the evidence records `excluded_observations > 0`.
4. **H2H Score / Ratio Contradictions**: Detects and rejects claims claiming an incorrect head-to-head record (e.g., "won 3 of 5" or "3-2") when the mathematical evidence records 5 wins in 5 sessions.
5. **Sample Size Mismatches**: Validates that claimed finish counts match valid observation counts.

---

## 5. API Endpoints & Service Boundary

### 5.1 Clean Service Boundary (`app/services/longitudinal_service.py`)
API endpoints do not directly query statistical formulas. Instead, they interact with `LongitudinalInsightService`:
- `get_driver_insights(db, season_year, driver_id, up_to_round)`
- `get_constructor_insights(db, season_year, constructor_id, up_to_round)`
- `get_teammate_insights(db, season_year, driver_a_id, driver_b_id, up_to_round)`
- `get_season_insights(db, season_year, up_to_round)`

Driver substitutions (such as Oliver Bearman replacing Carlos Sainz in Round 2) are partitioned into isolated teammate pairings and never cross-pollinated into the primary driver pairing.

### 5.2 API Routes
- **`POST /api/narrative`**: Unified endpoint generating grounded AI narratives across all scopes:
  - `scope: "longitudinal"`: Filters by `driver_id`, `constructor_id`, or `(driver_a_id, driver_b_id)`.
  - `scope: "race"`: Requires `round_num` and generates single-race narrative.
  - `scope: "mixed"`: Concurrently packages single-race and multi-race evidence.
- **`GET /api/season/{season}/insights`**: Retrieves deterministic longitudinal insights without LLM synthesis.
- **`GET /api/races/{season}/{round_num}/narrative`**: Preserved for 100% backward compatibility.

---

## 6. Provider Abstraction

The LLM abstraction protocol (`LLMProvider`) supports both **Groq** and **OpenRouter** transparently:
- Identical JSON schema prompt formatting.
- `temperature = 0.0` for maximum deterministic reproducibility.
- Automated fallback and error isolation: If an AI provider rate limit or timeout occurs, the API returns `status: "unavailable"` with HTTP 200, ensuring dashboard operations remain unblocked.

---

## 7. Limitations of the 5-Round Dataset

- All multi-round insights are derived exclusively from **2024 Rounds 1–5** (Bahrain, Saudi Arabia, Australia, Japan, China).
- Sample sizes (N = 1 to 5) are suitable for early-season descriptive summaries only.
- Narratives must explicitly reflect these sample boundaries and refrain from asserting season-long dominance or definitive career conclusions.

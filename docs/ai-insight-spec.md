# F1 Race Intelligence — AI Insight Engine & Grounding Specification

> Last updated: 2026-09-01
> Status: Specification Complete — Architecture & Prompt Contract Defined

This document specifies the architecture, data contracts, prompt engineering rules, epistemic classifications, and output schemas for the AI Insight Generation Engine.

---

## 1. Core Philosophy & Immutable Rules

1. **The LLM is NOT the source of truth.** All numbers, rankings, driver metrics, percentages, and statistical conclusions originate from PostgreSQL queries and Python statistical calculations.
2. **Deterministic Discovery First.** Insights are discovered by statistical algorithms and SQL rules, NOT by asking an LLM to "find interesting things in the data".
3. **Strict Grounding via Evidence Packages.** The LLM receives a structured JSON payload (Evidence Package) containing pre-calculated metrics, statistical significance parameters, comparison baselines, and data provenance pointers.
4. **Epistemic Honesty.** Explanations must strictly categorize claims into four distinct levels:
   - `OBSERVED_FACT`: Direct database observations (e.g., "Norris started P1 and finished P1").
   - `STATISTICAL_FINDING`: Statistically calculated metrics (e.g., "Piastri's 5-race rolling average pace improved by 3.2 positions, p < 0.05").
   - `MODEL_PREDICTION`: Mathematical or ML projections (e.g., "Expected pit window delta was +1.4 seconds").
   - `INTERPRETATION`: Plausible contextual explanation (e.g., "The track position loss during stint 2 coincided with an undercut attempt by Mercedes").
5. **No Fabricated Statistics or Hallucinated Technical Causes.** If telemetry or tyre data is absent from the evidence package (e.g., tyre degradation, temperature, aerodynamic damage), the LLM MUST NOT invent those causes.

---

## 2. Insight Generation Pipeline

```
 PostgreSQL / FastF1 Data
           │
           ▼
    SQL Analytics Layer
 (Aggregations, Window Funcs)
           │
           ▼
  Statistical Analytics Engine
 (Z-Scores, Rolling Avgs, SciPy)
           │
           ▼
 Insight Detection Engine (Rules)
 (Surfaces Candidate Findings)
           │
           ▼
   Evidence Package Generator
 (Assembles JSON Data Payload)
           │
           ▼
    LLM Explanation Layer
 (Enforces Grounding & Narrative)
           │
           ▼
  Structured AI Insight Payload
   (Saved to DB & Served to UI)
```

---

## 3. Evidence Package Schema (Data Contract)

Before an LLM API call is made, the Python engine serializes an `EvidencePackage` schema using Pydantic:

```json
{
  "finding_id": "EV-2025-R01-NOR-001",
  "insight_type": "UNEXPECTED_UNDERPERFORMANCE",
  "season": 2025,
  "round": 1,
  "race_name": "Australian Grand Prix",
  "target_entity": {
    "entity_type": "DRIVER",
    "id": "norris",
    "name": "Lando Norris",
    "constructor": "McLaren"
  },
  "observed_facts": [
    {"key": "grid_position", "value": 1, "unit": "position"},
    {"key": "finishing_position", "value": 9, "unit": "position"},
    {"key": "laps_completed", "value": 57, "unit": "laps"},
    {"key": "status", "value": "Finished", "unit": "status"}
  ],
  "statistical_findings": [
    {
      "metric_name": "position_delta",
      "observed_value": -8,
      "baseline_mean": +1.2,
      "baseline_std": 1.4,
      "z_score": -6.57,
      "sample_size": 24,
      "statistically_significant": true
    },
    {
      "metric_name": "median_lap_time_rank",
      "observed_value": 7,
      "baseline_value": 1,
      "unit": "rank"
    }
  ],
  "contextual_benchmarks": {
    "teammate_id": "piastri",
    "teammate_finishing_position": 2,
    "teammate_grid_position": 2,
    "winner_driver_id": "max_verstappen"
  },
  "data_limitations": [
    "No tyre compound or degradation telemetry available in this dataset.",
    "Pit stop duration included 1.2s delay due to traffic in pit lane."
  ]
}
```

---

## 4. LLM System Prompt Template

```markdown
You are an expert Formula 1 telemetry and statistical analyst for the F1 Race Intelligence platform.

Your duty is to generate a concise, objective, evidence-backed narrative explaining a pre-detected statistical finding.

RULES YOU MUST OBEY:
1. Refer ONLY to the numerical values and facts provided in the EVIDENCE PACKAGE JSON.
2. DO NOT invent telemetry, tyre degradation numbers, weather conditions, or team radio messages if they are not explicitly listed in the evidence package.
3. Every sentence in your explanation must belong to one of four epistemic categories:
   - [FACT]: Verifiable event in the raw data.
   - [STAT]: Statistically derived finding or comparison.
   - [PRED]: Model or mathematical calculation.
   - [INTERP]: Plausible interpretation consistent with facts.
4. Output MUST be valid JSON matching the requested schema.

EVIDENCE PACKAGE:
{evidence_package_json}
```

---

## 5. Structured AI Insight Output Schema

The output returned by the LLM is parsed and validated against this JSON schema:

```json
{
  "title": "Lando Norris Suffers Significant Position Loss at Australian GP",
  "summary": "Starting from Pole position (P1), Lando Norris dropped 8 positions to finish P9, marking a -6.57 Z-score deviation from his season baseline.",
  "severity": "HIGH",
  "epistemic_breakdown": {
    "observed_fact": "Lando Norris qualified on pole (P1) but finished in P9 at the Australian Grand Prix.",
    "statistical_finding": "The 8-position deficit represents a statistically significant anomaly (Z-score: -6.57, p < 0.001) compared to his average position gain of +1.2.",
    "model_prediction": "Expected finishing position based on qualifying pace and historical track position retention was P1-P2.",
    "interpretation": "While pace dropped relative to teammate Oscar Piastri (who finished P2), available telemetry does not contain tyre temperature data to confirm thermal degradation as the root cause."
  },
  "key_metrics": [
    {"name": "Grid Position", "value": "1"},
    {"name": "Finish Position", "value": "9"},
    {"name": "Position Delta", "value": "-8"},
    {"name": "Z-Score Anomaly", "value": "-6.57"}
  ],
  "methodology": "Z-score anomaly detection against 24-race historical baseline.",
  "confidence_score": 0.95,
  "visualization_metadata": {
    "recommended_chart_type": "POSITIONS_GAINED_BAR",
    "x_axis_key": "driver_id",
    "y_axis_key": "positions_gained",
    "highlight_ids": ["norris", "piastri"]
  }
}
```

---

## 6. Catalog of Insight Types

| Insight Type | Trigger Condition | Primary Metrics | Severity |
|--------------|-------------------|-----------------|----------|
| `UNEXPECTED_UNDERPERFORMANCE` | `finishing_position > season_avg + 2.0*std` | Grid, Finish, Z-Score | HIGH |
| `SIGNIFICANT_IMPROVEMENT` | `5_race_rolling_avg` improved by > 3.0 positions | Rolling Avg, Finish | MEDIUM |
| `CONSTRUCTOR_PERFORMANCE_SHIFT` | Team avg points change > 50% between 4-race blocks | Team Points, Quali Pace | HIGH |
| `TEAMMATE_DIVERGENCE` | Teammate gap > 3x points or > 5 positions over 3 races | H2H Delta, Points Share | MEDIUM |
| `UNUSUALLY_FAST_PITSTOP` | Pit stop duration < season_min + 0.2s | Stop Duration, Rank | LOW |
| `PIT_STRATEGY_ANOMALY` | Stop count differs from 80%+ of field | Stop Count, Stint Laps | MEDIUM |
| `QUALIFYING_RACE_PACE_DISCONNECT` | Top 3 quali, non-points finish (or vice versa) | Quali Rank, Race Pace Rank | HIGH |
| `RELIABILITY_CLUSTER` | ≥ 2 mechanical DNFs for team within 3 races | Status, Mechanical DNF Count | HIGH |

---

## 7. Quality Assurance & Evaluation

To ensure grounding integrity:
1. **Automated Assertion Check**: Validate that every number in the LLM response text exists within the original Evidence Package JSON.
2. **Negative Test Suite**: Pass dummy evidence packages with missing telemetry to test if the LLM falsely claims "tyre overheating" or "engine failure". Any such hallucination fails CI.

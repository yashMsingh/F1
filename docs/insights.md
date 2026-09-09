# Deterministic Insight Engine

## 1. Overview & Purpose

The deterministic insight engine (`app/insights/`) converts statistical evidence (`app/statistics/`) and analytical facts (`app/analytics/`) into strongly typed, machine-readable, traceable Formula 1 insights.

This layer does **not** generate natural-language prose, call LLMs, or make predictions. Its sole responsibility is to evaluate structured evidence against deterministic rules with explicit thresholds and sample-size requirements.

```text
Jolpica F1 API
      ↓
API Client (Phase 2B.1)
      ↓
Parser + Validation (Phase 2B.2)
      ↓
ETL / Persistence Layer (Phase 2B.3)
      ↓
PostgreSQL / SQLite Database
      ↓
Analytical SQL Layer (Phase 2B.4)
      ↓
Statistical Evidence Layer (Phase 2B.5)
      ↓
Deterministic Insight Engine (Phase 2B.6)  ← THIS LAYER
      ↓
AI Narrative Layer (Future Phase)
      ↓
Dashboard (Future Phase)
```

---

## 2. Core Principles

### 2.1 Insights, Not Prose
The insight engine emits strongly typed `Insight` dataclasses containing exact metrics, directions, magnitudes, and units. It does **not** emit subjective statements like *"Max Verstappen was clearly the superior driver"*.

Natural language explanation is exclusively the role of the future AI narrative layer, which will consume these structured objects.

### 2.2 Traceability Guarantee
Every generated insight contains an `InsightTraceability` block answering exactly why it was created:
$$\text{Insight} \longrightarrow \text{Rule ID} \longrightarrow \text{Statistical Evidence} \longrightarrow \text{Analytical Metric} \longrightarrow \text{Database Records}$$

### 2.3 Strict Evidence Strength (Heuristic, Not Hypothesis Test)
Evidence strength is classified into:
- **`INSUFFICIENT`**: $n < \text{min\_sample\_size}$ or $n = 0$.
- **`LOW`**: $n = 1$ (single-race or single-session observation).
- **`MODERATE`**: $2 \le n \le 4$ (small repeated sample).
- **`HIGH`**: $n \ge 5$ (larger repeated sample).

*Note*: This classification represents the volume of observed evidence, **not** a formal statistical confidence interval or $p$-value.

### 2.4 No Arbitrary or Hidden Thresholds
All numerical thresholds (e.g. `LARGE_POSITION_GAIN_THRESHOLD = 5`, `FAST_PIT_STOP_THRESHOLD_MILLIS = 25000`) are explicit named constants declared in `app/insights/rules.py` and recorded in the insight's `rule_parameters` traceability field.

### 2.5 No Global Driver Scores or Composite Rankings
Driver performance is evaluated along distinct, independent dimensions (qualifying deltas, grid movement, race pace, pit stops, points). There is no "Driver Score", "Rating", or weighted index.

### 2.6 No Causal Claims
Deterministic insights describe mathematical differences and associations (e.g. `FASTER`, `GAINED`, `LOST`), never causation. The engine never claims a pit stop *"caused"* a loss of position.

---

## 3. Rule Registry

Every rule has a unique, stable string identifier and documented metadata:

| Rule ID | Category | Metric | Min Sample | Threshold | Description |
|---|---|---|---|---|---|
| `QUALIFYING_TEAMMATE_ADVANTAGE` | `QUALIFYING` | `qualifying_delta_millis` | 1 | $\Delta < 0$ | Driver A set a faster qualifying lap time than teammate Driver B. |
| `QUALIFYING_TEAMMATE_DEFICIT` | `QUALIFYING` | `qualifying_delta_millis` | 1 | $\Delta > 0$ | Driver A set a slower qualifying lap time than teammate Driver B. |
| `QUALIFYING_TEAMMATE_EQUAL` | `QUALIFYING` | `qualifying_delta_millis` | 1 | $\Delta = 0$ | Teammates set identical qualifying times. |
| `POSITION_GAIN` | `POSITION_CHANGE` | `position_change` | 1 | $\text{change} > 0$ | Driver gained one or more positions from starting grid to finish. |
| `POSITION_LOSS` | `POSITION_CHANGE` | `position_change` | 1 | $\text{change} < 0$ | Driver lost one or more positions from starting grid to finish. |
| `POSITION_MAINTAINED` | `POSITION_CHANGE` | `position_change` | 1 | $\text{change} = 0$ | Driver finished in the exact position they started on the grid. |
| `LARGE_POSITION_GAIN` | `POSITION_CHANGE` | `position_change` | 1 | $\text{change} \ge 5$ | Driver gained 5 or more positions from starting grid. |
| `FASTEST_RECORDED_LAP` | `RACE_PACE` | `fastest_recorded_millis` | 1 | None | Driver recorded the fastest lap time in the session/race sample. |
| `RACE_PACE_TEAMMATE_ADVANTAGE` | `RACE_PACE` | `pace_delta_millis` | 1 | $\Delta < 0$ | Driver A recorded lower average/median lap time than Driver B. |
| `RACE_PACE_TEAMMATE_DEFICIT` | `RACE_PACE` | `pace_delta_millis` | 1 | $\Delta > 0$ | Driver A recorded higher average/median lap time than Driver B. |
| `FAST_PIT_STOP` | `PIT_STOP` | `duration_millis` | 1 | $< 25,000\text{ ms}$ | Pit stop duration was under 25 seconds. |
| `PIT_STOP_HIGH_VARIABILITY` | `PIT_STOP` | `stddev_duration_millis` | 2 | $> 1,500\text{ ms}$ | Pit stop duration sample standard deviation exceeds 1.5 seconds. |
| `TEAMMATE_POINTS_ADVANTAGE` | `TEAMMATE` | `points_delta` | 1 | $\Delta > 0$ | Driver A scored more points than Driver B. |
| `TEAMMATE_POINTS_DEFICIT` | `TEAMMATE` | `points_delta` | 1 | $\Delta < 0$ | Driver A scored fewer points than Driver B. |
| `TEAMMATE_FINISH_ADVANTAGE` | `TEAMMATE` | `finish_delta` | 1 | $\Delta < 0$ | Driver A finished ahead of Driver B. |
| `TEAMMATE_GRID_ADVANTAGE` | `TEAMMATE` | `grid_delta` | 1 | $\Delta < 0$ | Driver A started ahead of Driver B on the starting grid. |

---

## 4. Sign Conventions

- **Qualifying Delta**: $\text{time}_A - \text{time}_B$ in milliseconds. Negative means Driver A was faster.
- **Race Pace Delta**: $\text{pace}_A - \text{pace}_B$ in milliseconds. Negative means Driver A had lower (faster) lap times.
- **Position Change**: $\text{grid} - \text{finish}$. Positive means positions were gained.
- **Teammate Finish Delta**: $\text{finish}_A - \text{finish}_B$. Negative means Driver A finished ahead (e.g. $1 - 2 = -1$).
- **Teammate Grid Delta**: $\text{grid}_A - \text{grid}_B$. Negative means Driver A started ahead on the grid.
- **Teammate Points Delta**: $\text{points}_A - \text{points}_B$. Positive means Driver A scored more points.
- **Driver Ordering**: Teammates are ordered alphabetically by `driver_id` (`driver_a < driver_b`).

---

## 5. Insight Data Structure Example

```python
Insight(
    insight_id="QUALIFYING_TEAMMATE_ADVANTAGE:2024:1:max_verstappen:perez",
    rule_id="QUALIFYING_TEAMMATE_ADVANTAGE",
    category=InsightCategory.QUALIFYING,
    subject_id="max_verstappen",
    comparison_subject_id="perez",
    metric="qualifying_delta_millis",
    direction=Direction.FASTER,
    magnitude=358.0,
    unit="milliseconds",
    evidence_strength=EvidenceStrength.LOW,
    sample_size=1,
    traceability=InsightTraceability(
        source_metric="qualifying_delta_millis",
        source_function="get_teammate_qualifying_comparison",
        rule_id="QUALIFYING_TEAMMATE_ADVANTAGE",
        rule_parameters={},
        observed_value=-358,
        unit="milliseconds",
        sample_size=1,
        minimum_sample_size=1,
        sign_convention="delta = driver_a - driver_b; negative means driver_a was faster",
        season_year=2024,
        round_num=1,
        driver_id="max_verstappen",
        constructor_id="red_bull",
    ),
)
```

---

## 6. Contract with Future AI Narrative Layer

The future AI narrative layer will consume these structured `Insight` objects:
1. **Source of Truth**: The AI layer must **never** perform data recalculations or invent statistics.
2. **Grounded Narrative**: The LLM will translate the `Insight` properties (`subject_id`, `metric`, `direction`, `magnitude`, `unit`, `evidence_strength`) into fluent, informative prose.
3. **Epistemic Qualification**: When `evidence_strength == LOW`, the AI explanation must explicitly note that this is based on a single race or qualifying session and not claim a persistent season trend.

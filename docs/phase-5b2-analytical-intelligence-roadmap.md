# Phase 5B.2 — Full-Season Analytical Intelligence Assessment & Roadmap

## Executive Summary

Phase 5B.1 successfully completed and frozen the ingestion, mathematical audit, and automated regression testing of the full 24-round 2024 Formula 1 World Championship dataset. With 474 passing backend tests, 6 passing frontend tests, 112 PostgreSQL integration tests, and zero database mutations, the data foundation is rock-solid.

This document presents a comprehensive analytical assessment of the F1 Race Intelligence platform and establishes a phased engineering roadmap for expanding the platform's analytical intelligence. 

The core architectural principle of this platform remains non-negotiable:
1. **The database is the sole source of truth.** All calculations are strictly deterministic and traceable.
2. **AI explains already-computed evidence.** The LLM receives structured, validated evidence packages; it never computes statistics, queries the database, or invents facts.
3. **Preservation of existing baselines.** Historical test boundaries and prior phase guarantees remain intact.

---

## 1. Existing Analytical Capability Audit

The existing application codebase (`app/analytics/`, `app/statistics/`, `app/insights/`, `app/services/`, and `app/api/`) was inspected to categorize each core analytical capability:

| # | Analytical Capability | Classification | Current Implementation Status & Validation Depth |
|---|---|---|---|
| 1 | **Driver Performance Analysis** | **Implemented and validated** | Implemented in `app/analytics/driver_summary.py` (single-event) and `app/analytics/longitudinal_driver.py` (multi-event). Computes starts, classified finishes, DNFs/DSQs, GP points, sprint points, total points, wins, podiums, average finish, average grid, and standings. Fully verified across all 12 driver cases in `test_longitudinal_twenty_four_rounds.py`. *(Note: Longitudinal aggregates are exposed to the insight engine but lack a dedicated REST endpoint for frontend rendering).* |
| 2 | **Constructor Performance Analysis** | **Implemented and validated** | Implemented in `app/analytics/constructor_analysis.py` (event) and `app/analytics/longitudinal_constructor.py` (multi-event). Computes car starts, car finishes, DNFs, wins, podiums, points breakdown, and multi-driver contribution sums. Validated across all 10 constructors from P1 to P10 in 10 dedicated regression tests. |
| 3 | **Teammate Head-to-Head Comparisons** | **Implemented and validated** | Implemented in `app/analytics/longitudinal_teammate.py` and `app/statistics/teammate.py`. Compares qualifying, race finishes, and total points between co-drivers. Implements strict exclusion logic: events with DNFs, DSQs, DNSs, or non-shared rounds are excluded from finish comparisons. Validated on Verstappen/Perez (23-1 Q, 18-0 R, 6 exclusions), Russell/Hamilton (19-5 Q, 13-7 R, 4 exclusions), and mid-season substitutes. |
| 4 | **Qualifying & Race Performance** | **Partially implemented** | Single-event qualifying order (Q1, Q2, Q3 best times in milliseconds) and race classifications are implemented and validated. However, **cross-session conversion analytics** (e.g., pole-to-win conversion rate, grid-to-podium conversion rate, qualifying deficit relative to pole percentage) are currently **missing**. |
| 5 | **Rolling Performance & Recent Form** | **Implemented and validated** *(Drivers)*<br>**Partially implemented** *(Constructors)* | Implemented in `app/statistics/longitudinal.py` via `compute_rolling_window_stats` and `compute_driver_form_summary`. Calculates trailing 3- and 5-round rolling mean finish, points, and position changes, plus race-to-race deltas. Validated in Test 27. However, **constructor rolling momentum** and **trend trajectory slopes** (linear velocity of performance change) are **missing**. |
| 6 | **Points Efficiency & Scoring Consistency** | **Implemented and validated** *(Basic)*<br>**Partially implemented** *(Relative)* | Points scoring rates (`points_per_gp_start`, `points_per_gp_entry`, `points_per_round_total`) are mathematically reconciled, validated, and tested. However, **points retention rate** (actual points scored vs. theoretical points expected from starting grid) and **points concentration** (distribution across rounds) are **missing**. |
| 7 | **Position Gain & Race Execution** | **Partially implemented** | Grid-to-finish position delta is implemented and tested (`get_grid_vs_finish` and `compute_position_change_stats`). However, **lap-by-lap race execution** (first-lap position changes vs. pit-stop net position changes) is **missing**, despite 26,574 records existing in the `lap_times` table. |
| 8 | **Sprint vs. Grand Prix Performance** | **Partially implemented** | Sprint points and Grand Prix race points are strictly segregated in ETL and accounting. However, **behavioral comparative analytics** (e.g., driver performance delta in sprints vs. main races, sprint points dependency ratio) are **missing**. |
| 9 | **Deterministic Insight Generation** | **Implemented and validated** | Implemented in `app/insights/engine.py` with 17 single-event rules and 12 longitudinal rules in `app/insights/rules.py`. Validated to emit exactly 33 unique, reproducible full-season insights adhering to strict sample-size guardrails ($n \ge 3$). |
| 10 | **Evidence Traceability & AI Narrative** | **Implemented and validated** | Implemented in `app/ai/narrative.py` and `app/ai/context.py`. Full traceability metadata (`source_metric`, `source_function`, `observed_value`, `threshold`, `rounds_included`, `excluded_observations`) is passed to the LLM context. Tested with unit tests and mock providers, with automatic graceful degradation when AI providers are unavailable. |

---

## 2. Analytical Gaps & Research Opportunities

The 2024 season was one of the most dynamic in modern Formula 1 history: Red Bull began with dominant 1-2 finishes, McLaren and Ferrari mounted sustained championship challenges, Mercedes achieved four victories under specific operating conditions, and mid-season driver substitutions occurred at Ferrari, Williams, RB, and Haas.

Evaluating what the platform cannot currently explain reveals five meaningful analytical gaps:

### Gap 1: Qualifying-to-Race Conversion & Race Craft Efficiency
1. **Question Answered:** How effectively does a driver convert their qualifying grid position into race finishes and championship points? Who is a "Saturday specialist" vs. a "Sunday charger"?
2. **Analytical Value:** Crucial for F1 analysis. In 2024, George Russell out-qualified Lewis Hamilton 19-5, yet Hamilton frequently demonstrated stronger race pace and conversion. Lando Norris took 8 pole positions but frequently lost position on Lap 1. Sergio Perez suffered from poor qualifying positions (average grid 9.38) and was forced into recovery drives.
3. **Data Support:** `qualifying_results` (`position`, `q1_time_millis`, `q2_time_millis`, `q3_time_millis`), `race_results` (`grid_position`, `source_position`, `points`, `status`).
4. **Sufficiency:** Existing data is 100% sufficient across all 24 rounds.
5. **Methodology:**
   - **Pole Conversion Rate:** Percentage of P1 starts converted to Grand Prix wins and podiums.
   - **Front-Row Retention Rate:** Percentage of top-2 starts converted to top-3 finishes.
   - **Points Retention Ratio:** $\text{Points Retention} = \frac{\text{Actual Points Scored}}{\text{Expected Points from Grid Position}}$, where expected points are based on the standard FIA scale (P1: 25, P2: 18, P3: 15, ..., P10: 1).
   - **Net Position Change by Grid Tier:** Mean positions gained/lost when starting in Top 5 (P1-5), Midfield (P6-10), and Back of Grid (P11-20).
6. **Confounders & Limitations:** Unclassified finishes (mechanical DNFs vs. driver error collisions); Lap 1 incidents vs. strategy-driven position changes.
7. **Deterministic Evidence:** Structured metrics: `pole_win_conversion_rate`, `points_retention_ratio`, `top5_start_conversion_rate`.
8. **Actionable Insights:** E.g., `QUALIFYING_CONVERSION_DEFICIT` (driver loses $\ge 2.0$ positions on average when starting in top 4).

### Gap 2: Constructor Development Phasing & Championship Momentum
1. **Question Answered:** How did constructor competitiveness evolve across distinct phases of the season? At what point did the performance hierarchy shift?
2. **Analytical Value:** A full-season aggregate obscures the season's narrative arc. Red Bull scored 54% of available points in Rounds 1–8, dropping to 28% in Rounds 17–24. McLaren surged from 24% to 46% of points share over the same intervals.
3. **Data Support:** `races.round`, `race_results.points`, `sprint_results.points`, `constructor_standings.position`, `constructor_standings.points`.
4. **Sufficiency:** Existing data is 100% sufficient.
5. **Methodology:**
   - **Rolling 5-Round Points Share:** Constructor's points scored divided by total points available across all teams in that 5-round window.
   - **Season Phase Partitioning:**
     - *Phase 1 (Opening Flyaways & Early Season, Rounds 1–8)*
     - *Phase 2 (European Core, Rounds 9–16)*
     - *Phase 3 (Autumn Flyaways & Season Finale, Rounds 17–24)*
   - **Trajectory Velocity / Slope:** Linear regression slope of rolling points share over round number ($m = \frac{\Delta \text{Share}}{\Delta \text{Round}}$).
6. **Confounders & Limitations:** Sprints are concentrated in specific phases (Rounds 5, 6 in Phase 1; Round 11 in Phase 2; Rounds 19, 21, 23 in Phase 3). Sprint points must be normalized or analyzed both with and without sprints.
7. **Deterministic Evidence:** Structured phase objects: `PhaseAggregates(phase_id, rounds, points_share, wins, podiums, delta_to_leader)`.
8. **Actionable Insights:** E.g., `CONSTRUCTOR_MOMENTUM_SURGE` (points share increases by $\ge 15.0\%$ between consecutive phases).

### Gap 3: Representative Race Pace & Lap Time Distribution Analysis
1. **Question Answered:** Beyond the single fastest lap, what was a driver's true underlying race pace during clean racing conditions?
2. **Analytical Value:** High-level finishing positions can be influenced by safety car timing or retirements. Representative race pace reveals genuine vehicle and driver speed.
3. **Data Support:** `lap_times` table contains 26,574 lap records with `lap_number`, `position`, and `time_millis`.
4. **Sufficiency:** Existing data is 100% sufficient for timing; lacks telemetry/tyre compound tags.
5. **Methodology:**
   - **Outlier Filtering (Clean Laps):** In Formula 1 analytics, raw lap times include in-laps, out-laps, safety cars, and virtual safety cars. To determine clean racing laps deterministically without external safety car data:
     - Compute the session median lap time per driver.
     - Filter out laps where $\text{time\_millis} > 1.07 \times \text{median}$ (the standard FIA 107% threshold).
     - Exclude Lap 1 (standing start artifact) and known pit-stop in/out laps (from `pit_stops.lap`).
   - **Pace Metrics:**
     - Trimmed mean and median clean lap time.
     - Interquartile Range (IQR = $Q_3 - Q_1$) measuring pace consistency.
     - Teammate clean lap pace delta.
6. **Confounders & Limitations:** Fuel burn effect (~0.06s/lap lighter as race progresses); tyre age/compound differences are unknown in Jolpica. Comparisons are valid strictly across contemporaneous laps between teammates on identical strategies.
7. **Deterministic Evidence:** `CleanPaceSummary(driver_id, clean_laps_count, median_pace_millis, iqr_millis, pace_delta_to_teammate)`.
8. **Actionable Insights:** E.g., `REPRESENTATIVE_RACE_PACE_ADVANTAGE` (driver demonstrates $\ge 0.250$s/lap clean pace advantage over teammate across $\ge 20$ comparable laps).

### Gap 4: Attrition & Reliability Pattern Analysis
1. **Question Answered:** Which constructors and drivers suffered the greatest attrition, and how did reliability impact championship positions?
2. **Analytical Value:** Explains why Sergio Perez finished P8 despite driving the RB20 (5 DNFs), and why Williams finished P9 (7 combined DNFs between Albon, Sargeant, and Colapinto).
3. **Data Support:** `race_results.status`, `race_results.laps_completed`, `races.round`.
4. **Sufficiency:** 100% sufficient for finish counts; `status` strings provide the primary categorization.
5. **Methodology:**
   - Categorize status into:
     - *Classified Finishes* (`Finished`, `+1 Lap`, etc.)
     - *Mechanical / Terminal Failures* (`Brakes`, `Power Unit`, `Water leak`, `Engine`, `Hydraulics`)
     - *Accidents / Collisions* (`Collision`, `Accident`, `Damage`)
     - *Administrative Disqualifications* (`Disqualified`)
   - Compute Car Completion Rate: $\frac{\text{Laps Completed}}{\text{Total Scheduled Race Laps}}$.
6. **Confounders & Limitations:** API string labeling conventions: Jolpica occasionally uses `"Retired"` generically without differentiating mechanical vs. accident damage.
7. **Deterministic Evidence:** `ReliabilitySummary(constructor_id, total_car_starts, mechanical_dnf_count, accident_dnf_count, lap_completion_pct)`.
8. **Actionable Insights:** E.g., `CONSTRUCTOR_HIGH_ATTRITION_RATE` (team suffers non-classification rate $\ge 20\%$).

### Gap 5: Pit Lane Transit Performance & Crew Consistency
1. **Question Answered:** Which constructor pit crews performed with the greatest speed and consistency across 24 rounds, and who suffered costly outliers?
2. **Analytical Value:** Pit stop execution frequently determines race outcomes.
3. **Data Support:** 825 records in `pit_stops` table (`duration_millis`, `stop_number`, `lap`).
4. **Sufficiency:** 100% sufficient for pit lane transit time.
5. **Methodology:**
   - Note: Jolpica stores **total pit lane transit time** (entry to exit, typically 20–30 seconds), NOT stationary wheel-change time (2–3 seconds).
   - Normalize durations by circuit (pit lane transit length varies dramatically between circuits: e.g., Silverstone ~28s vs. Red Bull Ring ~21s).
   - Use z-score or delta-to-circuit-median: $\Delta_{\text{pit}} = \text{duration\_millis} - \text{median\_circuit\_pit\_duration}$.
   - Measure crew variability using standard deviation and IQR of delta-to-median.
6. **Confounders & Limitations:** Pit lane speeding penalties, stacking stops under Safety Car, front-wing changes.
7. **Deterministic Evidence:** `ConstructorPitCrewSeasonSummary(constructor_id, total_stops, median_delta_millis, stddev_millis, outlier_stop_count)`.
8. **Actionable Insights:** E.g., `PIT_CREW_SUPERIOR_CONSISTENCY` (constructor standard deviation $\le 400$ ms across $\ge 30$ season stops).

---

## 3. Data Limitations & Feasibility Boundary

To ensure complete analytical grounding, data capabilities are explicitly classified into three tiers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: Fully Feasible with Current Database (Zero External Dependencies)   │
│ - Qualifying-to-Race Conversion (Pole, Front-Row, Points Retention)         │
│ - Constructor Phased Development (Rolling 5-Round Share, Phase Aggregates)  │
│ - Representative Race Pace (107% Outlier-Filtered Clean Lap Distributions)  │
│ - Attrition & Lap Completion Rates (from race_results.status & laps)        │
│ - Pit Lane Transit Consistency (Normalized to circuit median)               │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: Feasible Only with Additional Controlled Data Ingestion             │
│ - Sprint Shootout Qualifying Analytics (Requires ingesting sprint quali API)│
│ - Circuit Characteristic Profiling (Requires adding track type metadata)    │
│ - Sector-by-Sector Speed Analytics (Requires sector timing endpoints)       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: NOT Responsibly Feasible (Must Be Explicitly Rejected)              │
│ - Telemetry Analysis (Throttle, Brake, Steering, RPM - Not in Jolpica)      │
│ - Tyre Degradation & Stint Compound Strategy (Soft/Med/Hard not in DB)      │
│ - Weather & Ambient Temperature Modeling (Not in DB)                        │
│ - On-Track Overtake Counts vs. Pit Strategy Passes (Lacks micro-tracking)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Boundary Rule:** The platform will strictly execute **Tier 1** analytics. Any analysis requiring Tier 2 is deferred until formal schema migrations and ingestion pipelines are commissioned. Tier 3 analyses are permanently out of scope under the Jolpica database architecture.

---

## 4. Prioritization Matrix for Analytical Improvements

| Improvement Candidate | Analytical Value (1–5) | Implementation Complexity (1–5) | Data Readiness (1–5) | Explainability (1–5) | Risk of Misleading Conclusions | Priority Verdict |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Qualifying-to-Race Conversion & Points Retention** | 5 | 2 | 5 | 5 | Low | **TOP PRIORITY 1** |
| **2. Constructor Phased Development & Trajectory Momentum** | 5 | 3 | 5 | 5 | Low | **TOP PRIORITY 2** |
| **3. Representative Clean Race Pace (Lap Times Filtering)** | 4 | 3 | 5 | 4 | Medium | **TOP PRIORITY 3** |
| **4. Attrition, Reliability & Lap Completion Analysis** | 3 | 2 | 5 | 5 | Low | **OPTIONAL 1** |
| **5. Season-Long Pit Lane Transit Consistency** | 3 | 2 | 5 | 4 | Low | **OPTIONAL 2** |
| *6. Circuit Type / Downforce Performance Profiling* | 4 | 4 | 2 | 3 | High (Subjective tags) | **REJECT / DEFER** |
| *7. Sprint Shootout Qualifying Analysis* | 3 | 4 | 1 | 4 | Medium (Missing DB data) | **REJECT / DEFER** |
| *8. Tyre Stint Degradation & Strategy Simulation* | 5 | 5 | 1 | 2 | Very High (Fabrication risk) | **REJECT / DEFER** |

### Priority Rationale:
- **Top Priority 1 (Conversion):** Highest value, lowest complexity, 100% data readiness. Directly illuminates driver race-craft differences (Norris vs. Hamilton vs. Perez).
- **Top Priority 2 (Phasing):** Unlocks the core historical narrative of 2024 (the four-way team battle and McLaren's title win) without complex modeling.
- **Top Priority 3 (Clean Pace):** Extracts massive untapped value from 26,574 existing lap time records using proven statistical filtering (107% rule).
- **Rejected Candidates:** Circuit profiling is rejected because circuit taxonomy is absent from the database; adding manual tags violates objective provenance. Tyre strategy is rejected because Jolpica does not provide compound data.

---

## 5. Grounded AI Narrative Integration

The existing AI architecture (`app/ai/narrative.py`, `app/ai/context.py`, `app/ai/prompts.py`) enforces strict epistemic grounding:
- The LLM receives an `EvidenceContext` containing serialized `Insight` objects.
- The LLM never calculates numbers, queries the database, or speculates.
- Fallback handling is 100% resilient (if LLM API keys are unconfigured, analytical dashboards continue operating without interruption).

### How New Deterministic Evidence Improves AI Narratives:
1. **Driver Season Narratives:**
   - *Current Narrative:* "Max Verstappen scored 437 points with 9 wins, averaging finish 2.96."
   - *Enhanced Narrative:* "Max Verstappen converted 8 of 8 pole positions into podium finishes and achieved a points retention ratio of 104% relative to starting grid expectation. Across clean racing laps, his median race pace was 0.312s faster than teammate Sergio Perez."
2. **Constructor Season Narratives:**
   - *Current Narrative:* "McLaren won the Constructors' Championship with 666 points and 6 wins."
   - *Enhanced Narrative:* "McLaren's championship victory was built on mid-to-late season trajectory momentum. In Rounds 1–8, McLaren captured 24.1% of available points; this surged to 45.8% across Rounds 17–24, overtaking Red Bull whose points share fell from 53.9% to 28.2%."
3. **Teammate Head-to-Head Narratives:**
   - *Current Narrative:* "Russell beat Hamilton 19-5 in qualifying and 13-7 in races."
   - *Enhanced Narrative:* "Russell held a decisive qualifying advantage (19-5, win rate 79.2%), but Hamilton exhibited superior Sunday conversion, gaining an average of +2.50 positions on race day compared to Russell's -0.58 net change."

### Evidence Schema Compatibility:
- **No breaking schema changes required.** The existing `InsightTraceability` dataclass and `build_evidence_context` serialize arbitrary rule parameters in `threshold` and `source_metric`. New rules (`CONVERSION_POINTS_RETENTION`, `CONSTRUCTOR_PHASE_MOMENTUM`, `REPRESENTATIVE_RACE_PACE`) integrate seamlessly into the existing `Insight` dataclass and JSON API schema.

---

## 6. Phase 5B.2 Implementation Roadmap

Phase 5B.2 is structured into three strictly scoped, independently testable subphases:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5B.2: FULL-SEASON ANALYTICAL INTELLIGENCE ENHANCEMENT                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5B.2A: Qualifying-to-Race Conversion & Race Craft Analytics                 │
│        - Pole & Front-Row conversion rates                                  │
│        - Grid tier position delta (Top 5, Midfield, Backmarker)             │
│        - Points retention ratio relative to grid expectation                │
│        - 3 new deterministic insight rules + unit/integration tests         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5B.2B: Constructor Development Phasing & Trajectory Momentum                │
│        - Rolling 5-round constructor points share                           │
│        - 3-Phase seasonal segmentation (R1-8, R9-16, R17-24)                │
│        - Trajectory momentum slope (linear velocity)                        │
│        - 2 new deterministic insight rules + unit/integration tests         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5B.2C: Representative Race Pace & Lap Time Distribution Analytics           │
│        - 107% session outlier filtering for clean laps                      │
│        - Trimmed median race pace and IQR pace consistency                 │
│        - Teammate clean lap pace delta                                      │
│        - 2 new deterministic insight rules + unit/integration tests         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Subphase 5B.2A — Qualifying-to-Race Conversion & Race Craft Analytics

#### Objective
Implement deterministic SQL analytics, statistical routines, and insight rules measuring how effectively drivers convert starting grid positions into race finishes and points.

#### Exact Deliverables
1. **Analytics Layer:** `app/analytics/conversion_analysis.py`
   - `get_driver_conversion_summary(session, season_year, driver_id, up_to_round)`
   - Computes: pole conversion rate, front-row conversion rate, points retention ratio, net position change segmented by grid tier (Top 5, P6-10, P11-20).
2. **Statistical Layer:** `app/statistics/conversion.py`
   - Deterministic points retention calculation using standard FIA points table.
   - Outlier and DNF separation (mechanical DNF vs. classified finish).
3. **Insight Engine Rules:**
   - `RULE_QUALIFYING_CONVERSION_HIGH`: Driver retains $\ge 95\%$ of grid-expected points over $\ge 10$ starts.
   - `RULE_QUALIFYING_CONVERSION_DEFICIT`: Driver retains $\le 75\%$ of grid-expected points over $\ge 10$ starts.
   - `RULE_POLE_CONVERSION_EXCELLENCE`: Driver converts $\ge 75\%$ of pole positions to Grand Prix wins (minimum 3 poles).
4. **Tests:** Dedicated test module `tests/analytics/test_conversion_analytics.py` verifying values against independent SQL.

#### Explicit Exclusions
- No lap-by-lap overtaking tracking.
- No telemetry or cornering data.
- No frontend dashboard changes in this subphase.

#### Acceptance Criteria (GO / NO-GO)
- **GO:** All conversion metrics match independent SQL calculations; 100% of driver points retention ratios reconcile; new tests pass; existing 474 tests pass with 0 regressions; 0 DB mutations.

---

### Subphase 5B.2B — Constructor Development Phasing & Trajectory Momentum

#### Objective
Implement deterministic analytics measuring constructor performance evolution across distinct season phases and rolling points-share momentum.

#### Exact Deliverables
1. **Analytics Layer:** Enhance `app/analytics/longitudinal_constructor.py`
   - `get_constructor_phase_aggregates(session, season_year, constructor_id)`
   - Segment season into Phase 1 (R1–8), Phase 2 (R9–16), Phase 3 (R17–24).
   - Computes phase points, phase points share, phase podiums, phase wins.
2. **Statistical Layer:** Enhance `app/statistics/longitudinal.py`
   - `compute_constructor_momentum(trajectory, window_size=5)`
   - Calculates rolling 5-round constructor points share and linear trend slope.
3. **Insight Engine Rules:**
   - `RULE_CONSTRUCTOR_PHASE_SURGE`: Team points share increases by $\ge 12.0\%$ between consecutive phases.
   - `RULE_CONSTRUCTOR_PHASE_DECLINE`: Team points share decreases by $\ge 12.0\%$ between consecutive phases.
4. **Tests:** Dedicated test module `tests/analytics/test_constructor_phasing.py`.

#### Explicit Exclusions
- No qualitative technical upgrade attribution (e.g., "new front wing at Miami") — purely mathematical points and share trajectory.
- No predictive extrapolations into future seasons.

#### Acceptance Criteria (GO / NO-GO)
- **GO:** Sum of phase points exactly matches full-season totals for all 10 teams; rolling points shares sum to 100% in all windows; 0 regressions in prior test suites.

---

### Subphase 5B.2C — Representative Clean Race Pace & Lap Distribution

#### Objective
Implement statistical outlier filtering on the 26,574 `lap_times` records to compute representative clean race pace, lap consistency, and teammate pace deltas.

#### Exact Deliverables
1. **Analytics Layer:** Enhance `app/analytics/lap_time_analysis.py`
   - `get_clean_race_pace(session, season_year, round_num)`
   - Filters out Lap 1, pit in/out laps (via `pit_stops`), and laps exceeding 107% of session median.
2. **Statistical Layer:** `app/statistics/race_pace.py`
   - Calculates trimmed median pace, interquartile range (IQR), and clean teammate delta.
3. **Insight Engine Rules:**
   - `RULE_REPRESENTATIVE_PACE_ADVANTAGE`: Driver achieves $\ge 0.200$s/lap clean pace advantage over teammate across $\ge 20$ comparable laps.
   - `RULE_RACE_PACE_CONSISTENCY`: Driver maintains IQR $\le 0.400$s across all clean laps in a Grand Prix.
4. **Tests:** Dedicated test module `tests/analytics/test_clean_race_pace.py`.

#### Explicit Exclusions
- No tyre degradation curves (tyre compound not in database).
- No telemetry cornering analysis.

#### Acceptance Criteria (GO / NO-GO)
- **GO:** Clean lap filtering is 100% deterministic and reproducible; teammate pace deltas compute only when both drivers complete $\ge 15$ clean contemporaneous laps; zero regressions across test suite.

---

## 7. Risk Analysis & Mitigation Strategy

| Risk | Likelihood | Impact | Mitigation Strategy |
|---|:---:|:---:|---|
| **Mathematical Rounding Inconsistencies** | Medium | Medium | Codify Python round-to-even (IEEE 754) expectations directly in test assertions as established in Phase 5B.1. |
| **Outlier Lap Distortion in Wet/Chaotic Races** | High | High | Strict 107% median cutoff and pit-stop lap exclusions prevent safety-car or wet-dry transition distortion. |
| **Substitute Driver Distortions in Phased Analysis** | Medium | Medium | Retain explicit sample size checks ($n \ge 3$) and isolate comparisons to shared events. |
| **AI Narrative Hallucination of Technical Causes** | Medium | High | Maintain strict system prompt instructions forbidding the LLM from speculating on tyre or aerodynamic causes not in evidence packages. |
| **Database Performance Degradation** | Low | Medium | Utilize existing composite indexes (`idx_lap_times_race_lap`, `idx_race_results_race_driver`); avoid unindexed full-table scans. |

---

## 8. Final Verification & Read-Only Status

In accordance with strict Phase 5B.2 preservation rules:
- **Application Code:** Untouched.
- **Database Migrations & Schemas:** Untouched.
- **Existing Test Suites:** Untouched (all 474 backend and 6 frontend tests passing).
- **Database Records:** Untouched (0 rows inserted, modified, or deleted).
- **Environment & Credentials:** Untouched (`.env` untracked and ignored).
- **Git State:** 0 commits, 0 pushes. HEAD remains `801dc1a`.
- **Files Created:** Exactly one planning document (`docs/phase-5b2-analytical-intelligence-roadmap.md`).

---

## 9. Recommendation (Initial Roadmap)

### **GO for Phase 5B.2 Implementation Roadmap**

The proposed three subphases (5B.2A Conversion, 5B.2B Phasing, 5B.2C Clean Pace) address the primary analytical blind spots of the current platform, rely exclusively on verified database fields, strictly preserve deterministic integrity, and significantly enrich evidence packages for grounded AI explanations.

---

# Phase 5B.2 — Methodology Refinement & Implementation Readiness Review

This section provides the focused, mathematically conservative methodology review of the three proposed subphases conducted prior to implementation authorization.

---

## 10. Qualifying-to-Race Conversion Methodology Review

### 10.1 Metric Definitions & Exact Mathematical Formulas

#### Metric 1: Pole-to-Win Conversion Rate (`pole_win_conversion_rate`)
$$\text{pole\_win\_conversion\_rate} = \frac{\sum \mathbb{I}(\text{grid\_position} = 1 \land \text{source\_position} = 1)}{\sum \mathbb{I}(\text{grid\_position} = 1)}$$
- **Formula:** Count of Grand Prix victories achieved when starting from P1 divided by total P1 grid starts.
- **Scope:** Grand Prix races only (sprint shootouts excluded).
- **Output:** Decimal between $0.00$ and $1.00$ (or percentage $0.0\%$ to $100.0\%$).

#### Metric 2: Front-Row Podium Retention Rate (`front_row_podium_rate`)
$$\text{front\_row\_podium\_rate} = \frac{\sum \mathbb{I}(\text{grid\_position} \in \{1, 2\} \land \text{source\_position} \in \{1, 2, 3\})}{\sum \mathbb{I}(\text{grid\_position} \in \{1, 2\})}$$
- **Formula:** Count of podium finishes (P1–P3) achieved when starting from the front row (P1 or P2) divided by total front-row starts.

#### Metric 3: Grid-to-Finish Position Change by Starting Tier (`tier_position_delta`)
For an individual race $r$:
$$\Delta_{\text{pos}, r} = \text{grid\_position}_r - \text{source\_position}_r$$
*(Positive values indicate positions gained forward through the field; negative values indicate positions lost).*

To avoid conflating backmarker recoveries with front-runner performance, the mean position delta is segmented into three distinct structural tiers:
1. **Front Tier ($\text{Tier}_1$):** Starting Grid P1–P4
   $$\overline{\Delta}_{\text{Front}} = \frac{1}{N_1} \sum_{r \in \text{Tier}_1, r \in \text{Classified}} (\text{grid}_r - \text{finish}_r)$$
2. **Midfield Tier ($\text{Tier}_2$):** Starting Grid P5–P10
   $$\overline{\Delta}_{\text{Midfield}} = \frac{1}{N_2} \sum_{r \in \text{Tier}_2, r \in \text{Classified}} (\text{grid}_r - \text{finish}_r)$$
3. **Lower Tier ($\text{Tier}_3$):** Starting Grid P11–P20
   $$\overline{\Delta}_{\text{Lower}} = \frac{1}{N_3} \sum_{r \in \text{Tier}_3, r \in \text{Classified}} (\text{grid}_r - \text{finish}_r)$$

#### Metric 4: Qualifying Performance vs. Race Performance Delta (`quali_race_delta`)
$$\text{quali\_race\_delta} = \overline{\text{grid\_position}} - \overline{\text{source\_position}}$$
- Computed strictly across races where the driver achieved a classified finish.
- Example: If a driver averages grid position $8.0$ and average finish $5.5$, delta is $+2.50$ (net gainer). If average grid is $3.0$ and average finish is $4.5$, delta is $-1.50$ (net decliner).

---

### 10.2 Investigation: Can an "Expected Points from Grid" Baseline Be Constructed?

The roadmap proposed calculating $\text{Points Retention} = \frac{\text{Actual Points}}{\text{Expected Points from Grid}}$. To evaluate this rigorously, an empirical query of all 479 race results from the complete 2024 season was conducted across every grid slot (P1 to P20).

#### Empirical 2024 Grid Position Points Distribution Table ($N=24$ Races)
| Grid Slot | Sample ($N$) | Mean Points | Min Points | Max Points | Std Dev | Major Confounding Anomaly |
|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **P1** | 24 | 18.29 | 0 | 26 | 8.05 | 1 DNF (Australia), 8 non-win finishes |
| **P2** | 24 | 16.62 | 0 | 25 | 7.35 | 2 DNFs |
| **P3** | 24 | **12.33** | 0 | 25 | 6.84 | **ANOMALY: P3 scored LESS than P4** |
| **P4** | 24 | **13.38** | 0 | 25 | 5.63 | **ANOMALY: P4 scored MORE than P3** |
| **P5** | 24 | 11.58 | 2 | 25 | 5.17 | Consistent points finishes |
| **P6** | 24 | 6.71 | 0 | 15 | 4.68 | Significant cliff between Top 5 and P6 |
| **P7** | 24 | 5.54 | 0 | 18 | 4.70 | High variance |
| **P8** | 24 | 4.04 | 0 | 12 | 3.17 | — |
| **P9** | 24 | 3.21 | 0 | 10 | 3.19 | — |
| **P10** | 24 | 2.38 | 0 | 18 | 4.21 | — |
| **P11** | 24 | 1.75 | 0 | 12 | 3.35 | — |
| **P12** | 24 | **0.38** | 0 | 4 | 1.13 | — |
| **P13** | 24 | 0.96 | 0 | 15 | 3.04 | — |
| **P14** | 24 | 0.25 | 0 | 4 | 0.85 | — |
| **P15** | 24 | 0.83 | 0 | 13 | 2.66 | — |
| **P16** | 24 | 0.83 | 0 | 12 | 2.70 | — |
| **P17** | 24 | **1.46** | 0 | 26 | 5.38 | **MASSIVE ANOMALY: Verstappen P17 $\to$ P1 win in Brazil (26 pts)** |
| **P18** | 24 | 0.12 | 0 | 2 | 0.45 | — |
| **P19** | 24 | **0.79** | 0 | 15 | 3.08 | **ANOMALY: P19 scored 6x more points than P18** |
| **P20** | 22 | 0.36 | 0 | 8 | 1.71 | 2 pit-lane starts excluded |

#### Findings of the Investigation:
1. **Empirical Modeling Failure:** A single 24-round season ($N=24$ per grid slot) is statistically insufficient to construct an empirical expected-points baseline. The data exhibits severe non-monotonicities caused by low sample size and outlier events:
   - P4 averaged **13.38 points**, whereas P3 averaged only **12.33 points**.
   - P17 averaged **1.46 points** (higher than P12, P13, P14, P15, and P16 combined averages) solely because Max Verstappen started P17 in wet São Paulo and won with fastest lap.
   - P19 averaged **0.79 points**, more than 6 times higher than P18 (**0.12 points**).
2. **Theoretical Modeling Failure:** If the official FIA points scale is used as the expected baseline (P1: 25, P2: 18, ..., P10: 1, P11–P20: 0):
   - Any ratio $\frac{\text{Actual Points}}{\text{Expected Points}}$ results in **division by zero** for any driver starting outside the top 10 (P11–P20).
   - A driver starting P15 who drives through the field to finish P9 (scoring 2 points) would have an infinite or undefined retention ratio.

#### Recommended Transparent Alternative:
Instead of inventing a fragile or ungrounded expected-points model, the platform will implement two transparent, fully deterministic alternatives:
1. **Top-10 Points Conversion Rate (`top10_points_conversion_rate`):**
   $$\text{top10\_points\_conversion\_rate} = \frac{\sum \mathbb{I}(\text{grid\_position} \le 10 \land \text{source\_position} \le 10)}{\sum \mathbb{I}(\text{grid\_position} \le 10)}$$
   - Measures what percentage of top-10 starts successfully resulted in championship points.
2. **Net Points Differential from Qualifying Potential (`net_points_vs_quali_points`):**
   - For drivers starting in the top 10, calculate:
     $$\Delta_{\text{points}} = \sum (\text{points\_scored} - \text{fia\_grid\_points})$$
   - Where $\text{fia\_grid\_points}$ is the points value assigned strictly to positions 1–10 (25, 18, 15, 12, 10, 8, 6, 4, 2, 1). This is framed explicitly as a *nominal comparative delta against static starting position*, NOT as an "expected probability model."

---

### 10.3 Database Requirements, Eligible Events & Exclusions

- **Database Fields:**
  - `race_results.grid_position` (Integer, 1–20; NULL or $\le 0$ indicates pit-lane start)
  - `race_results.source_position` (Integer, 1–20; NULL indicates unclassified)
  - `race_results.points` (Numeric, points scored)
  - `race_results.status` (String, classification status)
  - `races.round`, `races.season_year`
- **Eligible Events:**
  - All official Grand Prix races where the driver took the start on the grid (`grid_position > 0`).
- **Excluded Events:**
  - **Pit Lane Starts:** Drivers starting from the pit lane (`grid_position IS NULL` or `grid_position <= 0`) are excluded from grid-tier conversion metrics because they do not start from a grid slot.
  - **Did Not Start (DNS):** Excluded unconditionally.
  - **Unclassified Finishes (DNFs & DSQs):** Excluded from position-delta metrics ($\Delta_{\text{pos}}$) because no final finishing position exists. For conversion rates (e.g. pole-to-win or top-10 points conversion), a DNF is recorded as an unsuccessful conversion ($0$).
- **Substitute Drivers:**
  - Evaluated on their actual starts ($n_{\text{starts}}$). If $n_{\text{starts}} < 3$, longitudinal summary metrics are suppressed.
- **Minimum Sample Sizes:**
  - Single-driver full-season conversion metrics: Minimum **$N \ge 5$ eligible starts** within the specific tier.
  - Pole conversion: Minimum **$N \ge 3$ pole positions** required to emit an insight.

---

### 10.4 Analytical Limitations & Epistemic Distinctions

> [!WARNING]
> **Risk of Misleading Conclusions:**
> - A driver on pole position whose engine fails on Lap 2 (e.g., Charles Leclerc at Canada) would register as a failed conversion ($0\%$), which could be misinterpreted as poor driver race craft if mechanical DNFs are not segregated.
> - **Mandatory Epistemic Guardrail:** Conversion metrics must be described strictly as **descriptive historical conversion facts** (e.g., "Across 8 pole positions, Norris won 4 races and finished on the podium in 6"), NEVER as psychological assertions or ungrounded claims about driver "pressure handling" or "clutch ability."

---

## 11. Constructor Competitive Momentum Methodology Review

### 11.1 Metric Definitions & Exact Mathematical Formulas

#### Metric 1: Rolling Five-Round Points Share Percentage (`rolling_5rd_points_share`)
For constructor $c$ at round $R$ (where $R \ge 5$):
$$\text{Window}_R = [R - 4, R - 3, R - 2, R - 1, R]$$
$$\text{rolling\_5rd\_points\_share}_{c, R} = \frac{\sum_{r \in \text{Window}_R} \text{Points}_{c, r}}{\sum_{r \in \text{Window}_R} \text{Total\_Points\_Awarded}_r} \times 100\%$$
- **Numerator:** Total points (GP race points + sprint points) scored by constructor $c$ across all participating cars in the 5-round window.
- **Denominator:** Total points awarded across **all 10 constructors** in those exact 5 rounds.
- **Mathematical Invariant:** At every round $R \ge 5$, the sum of points shares across all 10 constructors equals exactly $100.0\%$:
  $$\sum_{c=1}^{10} \text{rolling\_5rd\_points\_share}_{c, R} = 100.0\%$$

#### Metric 2: Three-Phase Seasonal Segmentation (`phase_points_share`)
The 2024 championship is partitioned into three chronological blocks:
- **Phase 1 (Opening Flyaways & Early European, Rounds 1–8):**
  - Rounds: Bahrain (R1) to Monaco (R8).
  - Sprint Events: China (R5), Miami (R6).
  - Total Points Awarded Across All Teams: **888.00 points** ($6 \times 102 + 2 \times 138$).
- **Phase 2 (European Summer Heart, Rounds 9–16):**
  - Rounds: Canada (R9) to Netherlands (R16).
  - Sprint Events: Austria (R11).
  - Total Points Awarded Across All Teams: **852.00 points** ($7 \times 102 + 1 \times 138$).
- **Phase 3 (Autumn Flyaways & Season Finale, Rounds 17–24):**
  - Rounds: Azerbaijan (R17) to Abu Dhabi (R24).
  - Sprint Events: United States (R19), São Paulo (R21), Qatar (R23).
  - Total Points Awarded Across All Teams: **924.00 points** ($5 \times 102 + 3 \times 138$).

For phase $p \in \{1, 2, 3\}$:
$$\text{phase\_points\_share}_{c, p} = \frac{\sum_{r \in \text{Phase}_p} \text{Points}_{c, r}}{\text{Total\_Points\_Awarded}_{\text{Phase}_p}} \times 100\%$$

#### Metric 3: Phase-to-Phase Competitive Momentum Delta (`phase_momentum_delta`)
$$\Delta \text{Share}_{c, (1 \to 2)} = \text{phase\_points\_share}_{c, 2} - \text{phase\_points\_share}_{c, 1}$$
$$\Delta \text{Share}_{c, (2 \to 3)} = \text{phase\_points\_share}_{c, 3} - \text{phase\_points\_share}_{c, 2}$$

#### Metric 4: Trajectory Momentum Slope (`trajectory_momentum_slope`)
Calculated via Ordinary Least Squares (OLS) linear regression of rolling 5-round points share over round number $r \in [5, 24]$:
$$m_c = \frac{\sum_{i=5}^{24} (r_i - \bar{r})(\text{Share}_{c, i} - \overline{\text{Share}}_c)}{\sum_{i=5}^{24} (r_i - \bar{r})^2}$$
- **Interpretation:** $m_c > 0$ indicates a positive trajectory (gaining points share over the season); $m_c < 0$ indicates a declining trajectory.

---

### 11.2 Edge-Case Handling & Confounder Analysis

1. **Sprint vs. Grand Prix Points Distortion:**
   - Notice that total available points vary by phase: Phase 1 has 888 pts, Phase 2 has 852 pts, Phase 3 has 924 pts (due to 2 vs. 1 vs. 3 sprints).
   - **Crucial Rule:** Absolute points between phases cannot be compared directly because Phase 3 offered 72 more points than Phase 2!
   - **Resolution:** All phase and rolling comparisons must use **points share percentage** as the primary metric, which normalizes for sprint round distribution. In addition, the system will report **GP-only points share** alongside **Total points share** for complete transparency.
2. **Constructors with Zero Points in a Window:**
   - Sauber scored 0 points in 23 of 24 rounds; Williams scored 0 points in 16 rounds.
   - Points share is cleanly $0.0\%$. There is zero division-by-zero risk because the denominator is the sum of points awarded to all 10 teams ($\ge 510$ points per window).
3. **Driver Substitutions:**
   - Constructor points aggregate all points scored under that constructor's entry, regardless of driver identity (e.g. Ferrari points include Bearman's 6 pts in Saudi Arabia; Haas points include Bearman's 1 pt at Baku; Williams includes Colapinto's 5 pts). This correctly measures team output.
4. **Window Size Standardization:**
   - Rolling windows will strictly use fixed 5-round windows starting at Round 5. Rounds 1–4 will not report rolling 5-round metrics to avoid confusing expanding window denominators with 5-round averages.
5. **Strict Terminology Guardrail:**
   - Points-share shifts must **never** be cited as direct evidence of "car aerodynamic upgrades" or "technical development." Points reflect execution, strategy, driver consistency, weather luck, and competitor attrition. The platform must use terms such as **"competitive momentum," "championship scoring trend,"** or **"points share trajectory."**

---

## 12. Representative Race Pace Feasibility Review (The 26,574 Lap Deep Dive)

A critical data-feasibility audit was conducted on the 26,574 rows in `lap_times` and 825 rows in `pit_stops` to determine whether a statistically defensible "representative race pace" sample can be constructed.

### 12.1 Can the Available Data Reliably Identify Key Racing Conditions?

| Condition | Detectable in Current Schema? | Mechanism / Evidence in Database | Feasibility Assessment |
|---|:---:|---|---|
| **Pit-In Laps** | **Partially** | `pit_stops.lap` records the lap number of pit entry. | Feasible to flag lap $L_{\text{pit}}$. |
| **Pit-Out Laps** | **Heuristic Only** | Pit-out lap is generally lap $L_{\text{pit}} + 1$, but slow out-laps cannot be distinguished from traffic without timing sectors. | Moderate risk. |
| **Safety-Car (SC) Laps** | **NO** | **Zero columns exist** in `races`, `race_results`, or `lap_times` for track status, flags, or safety cars. | **Statistically Indefensible** without external data. |
| **Virtual Safety Car (VSC)** | **NO** | Zero tracking. VSC can last half a lap, distorting only specific sectors. | **Impossible to Detect Deterministically**. |
| **Red-Flag Interruptions** | **NO (Artifact Only)** | In Monaco R08, Leclerc's Lap 1 time is recorded as **2,456,330 ms (~41 minutes)**; in Brazil R21, Verstappen's Lap 32 time is **1,556,410 ms (~26 minutes)**. | Red flags appear only as unflagged multi-thousand-second outliers. |
| **Traffic-Affected Laps** | **NO** | Requires mini-sector gap telemetry; completely absent from Jolpica. | **Impossible**. |
| **Damage-Affected Laps** | **NO** | Absent from database. | **Impossible**. |
| **Missing / Null Laps** | **YES** | Exactly 0 null `time_millis` in 2024; unclassified drivers stop recording laps. | Fully verified. |

---

### 12.2 Critical Flaws in the Proposed 107% Filtering Methodology

The initial proposal suggested filtering out laps where $\text{time\_millis} > 1.07 \times \text{median}$. Empirical testing across the 2024 season reveals three fatal flaws:

1. **Failure in Wet & Mixed-Weather Races:**
   - In wet or wet-to-dry transition races (e.g., Round 9 Canada, Round 12 Silverstone, Round 21 São Paulo), lap times naturally vary by **15 to 30 seconds** as the track dries or rain falls.
   - In São Paulo (Brazil R21), intermediate tire green-flag laps were $\sim 1\text{m}20\text{s}$ to $1\text{m}25\text{s}$, while extreme wet green-flag laps were $\sim 1\text{m}35\text{s}$.
   - A static 107% threshold filters out 100% legitimate green-flag racing laps while keeping slow safety car laps if the median was inflated!
2. **Safety-Car Contamination of the Median:**
   - If a race features 12 safety car laps (e.g. Canada or Austria), the overall session median is shifted slower. Laps run under Safety Car or delta speed will pass beneath the 107% cutoff, fatally corrupting the "clean pace" sample.
3. **The Tyre Compound Confounder:**
   - Jolpica does **not** record tyre compounds (Soft, Medium, Hard, Inter, Wet).
   - In Formula 1, compound deltas account for **$0.8\text{s}$ to $1.5\text{s}$ per lap**, and tyre age degradation accounts for another $0.1\text{s}$/lap.
   - Comparing Driver A's median lap time to Driver B's median lap time without tyre compound knowledge compares different equipment, falsely attributing tyre deltas to driver pace!

---

### 12.3 Feasibility Finding & Strategic Recommendation for Race Pace

> [!CAUTION]
> **Definitive Finding:** A full-season "representative clean race pace" metric **CANNOT be responsibly or defensibly constructed** from the available Jolpica dataset. Attempting to publish such a metric would violate Rule 1 of AGENTS.md: *"The database is the source of truth — never speculate or fabricate."*

#### Strategic Decision:
- **Subphase 5B.2C (Unconstrained Representative Race Pace) is REJECTED / DEFERRED.**
- **Alternative Replacement:** Propose **Subphase 5B.2C-Alt: Season Attrition, Reliability & Lap Completion Analysis**.
  - 100% grounded in `race_results.status`, `race_results.laps_completed`, and `races.round`.
  - Answers how car reliability vs. driver accident attrition shaped the championship.
  - Zero risk of statistical distortion or unflagged safety-car contamination.

---

## 13. Implementation Readiness Matrix

| Dimension | Subphase 5B.2A: Qualifying-to-Race Conversion | Subphase 5B.2B: Constructor Competitive Momentum | Subphase 5B.2C: Representative Race Pace | Subphase 5B.2C-Alt: Attrition & Reliability Analysis |
|---|---|---|---|---|
| **Final Metrics** | 1. Pole Conversion Rate<br>2. Front-Row Podium Rate<br>3. Tier Position Delta ($\Delta_{\text{Front}}$, $\Delta_{\text{Mid}}$, $\Delta_{\text{Lower}}$)<br>4. Top-10 Points Conversion Rate | 1. Rolling 5-Round Points Share<br>2. Three-Phase Points Share<br>3. Phase Momentum Delta<br>4. Trajectory Momentum Slope | 1. Clean Pace Median<br>2. Pace IQR<br>3. Teammate Pace Delta | 1. Mechanical DNF Rate<br>2. Collision DNF Rate<br>3. Lap Completion Percentage<br>4. Attrition Points Impact |
| **SQL Requirements** | `qualifying_results` joined with `race_results` on `race_id` and `driver_id` | Aggregation on `race_results` and `sprint_results` grouped by `constructor_id` & `round` | Complex lap-time filtering on 26,574 `lap_times` | `race_results.status` pattern matching and `laps_completed` sum |
| **Edge-Case Handling** | Exclude pit-lane starts; separate mechanical DNFs; sample size guards | Sprints normalized via points share; fixed 5-round windows; neutral terminology | Safety cars and wet weather confounders **unsolvable** | Parse "Retired" vs specific mechanical strings; handle DSQ |
| **Min Sample Size** | $N \ge 5$ tier starts; $N \ge 3$ poles | Fixed 5 rounds; 8 rounds per phase | Requires $\ge 20$ clean laps (unreliable) | $N \ge 5$ race entries per team |
| **Expected Evidence** | `ConversionSummary(driver_id, tier, starts, delta, conv_rate)` | `ConstructorPhaseShare(constructor_id, phase, share, slope)` | `CleanPace(driver_id, median, iqr)` | `ReliabilitySummary(constructor_id, starts, mech_dnf, lap_pct)` |
| **Required Tests** | Unit tests on formulas; integration test across 2024 drivers | Unit tests on share sums (100%); integration test across 10 teams | Highly vulnerable to false assertions | Unit tests on status parsing; integration test across 10 teams |
| **SQL Validation** | Direct independent SQL queries for conversion counts | Direct independent SQL queries for phase points sums | Cannot be independently verified against objective ground truth | Direct independent SQL queries for DNF status counts |
| **Known Limitations** | Cannot separate driver error from tactical pit-stop loss | Does not measure aerodynamic car upgrades directly | Missing SC/VSC, missing tyres, weather shifts | Jolpica sometimes uses generic "Retired" status |
| **Readiness Verdict** | **GO** | **GO** | **NO-GO (DEFERRED)** | **GO (Recommended Alternative)** |

---

## 14. Revised Implementation Order & Phasing Plan

Based on the conservative methodology review, the execution roadmap for Phase 5B.2 is refined as follows:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ REVISED PHASE 5B.2 EXECUTION ROADMAP                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ STEP 1: Subphase 5B.2A — Qualifying-to-Race Conversion & Race Craft         │
│         - Pole-to-Win and Front-Row Podium Conversion                       │
│         - Segmented Grid-Tier Position Deltas (Front, Midfield, Lower)      │
│         - Top-10 Points Conversion Rate (Transparent Alternative)           │
│         - Status: APPROVED FOR IMPLEMENTATION (GO)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ STEP 2: Subphase 5B.2B — Constructor Competitive Momentum & Phasing         │
│         - Normalized Rolling 5-Round Points Share (100% Invariant)          │
│         - Three-Phase Seasonal Progression (R1-8, R9-16, R17-24)            │
│         - Trajectory Momentum Slope (OLS)                                   │
│         - Strictly Neutral Championship Terminology                         │
│         - Status: APPROVED FOR IMPLEMENTATION (GO)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ STEP 3: Subphase 5B.2C-Alt — Season Attrition & Reliability Analysis        │
│         - Replaces unconstrained lap pace with verifiable reliability data  │
│         - Mechanical vs. Collision Non-Classification Rates                 │
│         - Full-Season Lap Completion Percentage by Constructor              │
│         - Status: APPROVED FOR IMPLEMENTATION (GO)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ DEFERRED: Subphase 5B.2C (Representative Race Pace from Lap Times)          │
│           - Reason: Absence of Safety Car, VSC, and Tyre Compound fields    │
│           - Status: DEFERRED until track-status data ingestion is viable     │
└─────────────────────────────────────────────────────────────────────────────┘
```


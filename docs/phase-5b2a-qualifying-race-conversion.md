# Phase 5B.2A — Qualifying-to-Race Conversion & Race Craft Analytics

**Status:** COMPLETE & INDEPENDENTLY VALIDATED  
**Championship Season:** 2024 Formula 1 (24 Rounds)  
**Database Mode:** Strictly Read-Only (Zero Mutations Verified)  
**Branch / HEAD:** `master` @ `801dc1a`  

---

## 1. Executive Summary

Subphase 5B.2A extends the F1 Race Intelligence analytical foundation with four deterministic, statistically grounded qualifying-to-race conversion capabilities:
1. **Pole-to-Win Conversion Rate:** Measuring how effectively pole position qualifiers convert P1 starts into Grand Prix victories.
2. **Front-Row Podium Retention Rate:** Measuring how consistently P1 and P2 qualifiers retain top-3 podium finishes.
3. **Segmented Grid-Tier Position Deltas:** Measuring position gains and losses ($\Delta_{\text{pos}} = \text{grid} - \text{finish}$) segmented into **Front Tier (P1–P4)**, **Midfield Tier (P5–P10)**, and **Lower Tier (P11–P20)**.
4. **Top-10 Points Conversion Rate:** Measuring what percentage of top-10 starting grid slots successfully yield classified top-10 championship points.

All metrics are derived directly from PostgreSQL source tables (`qualifying_results`, `race_results`, `races`, `drivers`, `constructors`) without LLM generation or heuristic fabrication. All 12 independent regression tests pass, all 474 existing backend tests pass with zero regressions, all 6 frontend tests pass, the Vite production build succeeds, and all 13 PostgreSQL tables exhibit exactly zero row mutations.

---

## 2. Mathematical Metric Definitions & Formulas

### 2.1 Pole-to-Win Conversion Rate (`pole_to_win_rate`)
$$\text{pole\_to\_win\_rate} = \frac{\text{wins\_from\_pole}}{\text{total\_poles}} \times 100$$
- **Eligibility:** Driver classified P1 in official Qualifying (`QualifyingResult.position = 1`) who actually took the race start (non-DNS).
- **Winning Condition:** Race classification `source_position = 1` and `_is_classified_result(position_text, status) = True`.
- **Zero-Denominator Safeguard:** If $\text{total\_poles} = 0$, rate defaults safely to $0.0\%$.
- **Statistical Threshold:** Minimum **$N \ge 3$ pole starts** required before emitting an insight.

### 2.2 Front-Row Podium Retention Rate (`front_row_podium_rate`)
$$\text{front\_row\_podium\_rate} = \frac{\text{front\_row\_podiums}}{\text{front\_row\_starts}} \times 100$$
- **Eligibility:** Driver classified P1 or P2 in official Qualifying (`QualifyingResult.position \in \{1, 2\}`) who actually took the race start (non-DNS).
- **Podium Condition:** Race classification `source_position \le 3` and `_is_classified_result(position_text, status) = True`.
- **Attrition Rule:** Unclassified race finishes (DNFs, DSQs) count as failed retention ($0$) provided the driver started. DNS events are excluded from starts.
- **Statistical Threshold:** Minimum **$N \ge 3$ front-row starts** required before emitting an insight.

### 2.3 Segmented Grid-Tier Position Delta (`avg_position_delta`)
For an individual race $r$:
$$\Delta_{\text{pos}, r} = \text{grid\_position}_r - \text{source\_position}_r$$
*(Positive values indicate forward progress / positions gained; negative values indicate positions lost).*

To prevent conflating backmarker recoveries with front-runner performance, position changes are segmented into three fixed structural tiers:
- **Front Tier ($\text{Tier}_1$):** Starting Grid P1–P4
  $$\overline{\Delta}_{\text{Front}} = \frac{1}{N_{\text{class}, 1}} \sum_{r \in \text{Tier}_1, \text{Classified}} (\text{grid}_r - \text{finish}_r)$$
- **Midfield Tier ($\text{Tier}_2$):** Starting Grid P5–P10
  $$\overline{\Delta}_{\text{Midfield}} = \frac{1}{N_{\text{class}, 2}} \sum_{r \in \text{Tier}_2, \text{Classified}} (\text{grid}_r - \text{finish}_r)$$
- **Lower Tier ($\text{Tier}_3$):** Starting Grid P11–P20
  $$\overline{\Delta}_{\text{Lower}} = \frac{1}{N_{\text{class}, 3}} \sum_{r \in \text{Tier}_3, \text{Classified}} (\text{grid}_r - \text{finish}_r)$$
- **Exclusion of Non-Classified Results:** Unclassified finishes (DNFs, DSQs) are recorded in `non_classified_results` and strictly excluded from the $\Delta_{\text{pos}}$ summation. No fictitious finishing positions are fabricated.
- **Statistical Threshold:** Minimum **$N \ge 5$ eligible starts** in the specific tier required before emitting an insight.

### 2.4 Top-10 Points Conversion Rate (`top10_conversion_rate`)
$$\text{top10\_conversion\_rate} = \frac{\text{classified\_top10\_finishes\_from\_top10\_starts}}{\text{actual\_top10\_starts}} \times 100$$
- **Eligibility:** Starting grid position $1 \le \text{grid\_position} \le 10$ with actual race start (non-DNS).
- **Conversion Condition:** Classified race finish $1 \le \text{source\_position} \le 10$.
- **Statistical Threshold:** Minimum **$N \ge 5$ top-10 starts** required before emitting an insight.

---

## 3. Full-Season 2024 Empirical Results

### 3.1 Pole-to-Win Conversion ($N=24$ Poles)
| Driver | Poles | Wins from Pole | Pole-to-Win Rate | Sample Size Status ($N \ge 3$) | Insight Generated |
|---|:---:|:---:|:---:|:---:|:---:|
| **Max Verstappen** | 10 | 6 | **60.0%** | Valid ($N=10$) | `POLE_TO_WIN_CONVERSION` (Direction: HIGHER) |
| **Lando Norris** | 8 | 3 | **37.5%** | Valid ($N=8$) | `POLE_TO_WIN_CONVERSION` (Direction: LOWER) |
| **George Russell** | 3 | 1 | **33.3%** | Valid ($N=3$) | `POLE_TO_WIN_CONVERSION` (Direction: LOWER) |
| **Charles Leclerc** | 2 | 1 | 50.0% | Suppressed ($N=2 < 3$) | None (Protected) |
| **Carlos Sainz** | 1 | 1 | 100.0% | Suppressed ($N=1 < 3$) | None (Protected) |

*Total Grand Prix Poles: 10 + 8 + 3 + 2 + 1 = 24.*

### 3.2 Front-Row Podium Retention ($N=48$ Starts)
| Driver | Front-Row Starts | Podiums | Retention Rate | Sample Size Status ($N \ge 3$) | Insight Generated |
|---|:---:|:---:|:---:|:---:|:---:|
| **Carlos Sainz** | 3 | 3 | **100.0%** | Valid ($N=3$) | `FRONT_ROW_PODIUM_RETENTION` (Direction: HIGHER) |
| **Charles Leclerc** | 6 | 5 | **83.3%** | Valid ($N=6$) | `FRONT_ROW_PODIUM_RETENTION` (Direction: HIGHER) |
| **Max Verstappen** | 16 | 12 | **75.0%** | Valid ($N=16$) | `FRONT_ROW_PODIUM_RETENTION` (Direction: HIGHER) |
| **Lando Norris** | 9 | 6 | **66.7%** | Valid ($N=9$) | `FRONT_ROW_PODIUM_RETENTION` (Direction: HIGHER) |
| **Oscar Piastri** | 6 | 4 | **66.7%** | Valid ($N=6$) | `FRONT_ROW_PODIUM_RETENTION` (Direction: HIGHER) |
| **George Russell** | 5 | 2 | **40.0%** | Valid ($N=5$) | `FRONT_ROW_PODIUM_RETENTION` (Direction: LOWER) |
| **Sergio Perez** | 2 | 2 | 100.0% | Suppressed ($N=2 < 3$) | None (Protected) |
| **Lewis Hamilton** | 1 | 1 | 100.0% | Suppressed ($N=1 < 3$) | None (Protected) |

*Total Front-Row Starts: 3 + 6 + 16 + 9 + 6 + 5 + 2 + 1 = 48.*

### 3.3 Top-10 Points Conversion
| Driver | Top-10 Starts | Converted Finishes | Conversion Rate | Sample Size ($N \ge 5$) | Insight Generated |
|---|:---:|:---:|:---:|:---:|:---:|
| **Lando Norris** | 23 | 22 | **95.7%** | Valid ($N=23$) | `TOP10_CONVERSION_HIGH` |
| **Oscar Piastri** | 23 | 22 | **95.7%** | Valid ($N=23$) | `TOP10_CONVERSION_HIGH` |
| **Max Verstappen** | 22 | 21 | **95.5%** | Valid ($N=22$) | `TOP10_CONVERSION_HIGH` |
| **Charles Leclerc** | 21 | 20 | **95.2%** | Valid ($N=21$) | `TOP10_CONVERSION_HIGH` |
| **Carlos Sainz** | 21 | 20 | **95.2%** | Valid ($N=21$) | `TOP10_CONVERSION_HIGH` |
| **Lewis Hamilton** | 17 | 16 | **94.1%** | Valid ($N=17$) | `TOP10_CONVERSION_HIGH` |
| **George Russell** | 22 | 19 | 86.4% | Valid ($N=22$) | None ($< 90\%$) |
| **Sergio Perez** | 14 | 11 | 78.6% | Valid ($N=14$) | None ($< 90\%$) |
| **Fernando Alonso** | 17 | 13 | 76.5% | Valid ($N=17$) | None ($< 90\%$) |
| **Pierre Gasly** | 7 | 5 | 71.4% | Valid ($N=7$) | None ($< 90\%$) |
| **Yuki Tsunoda** | 12 | 8 | 66.7% | Valid ($N=12$) | None ($< 90\%$) |
| **Lance Stroll** | 6 | 4 | 66.7% | Valid ($N=6$) | None ($< 90\%$) |
| **Nico Hulkenberg** | 11 | 7 | 63.6% | Valid ($N=11$) | None ($< 90\%$) |
| **Alexander Albon** | 7 | 4 | 57.1% | Valid ($N=7$) | None ($< 90\%$) |
| **Esteban Ocon** | 4 | 3 | 75.0% | Suppressed ($N=4 < 5$) | None (Protected) |
| **Kevin Magnussen** | 3 | 2 | 66.7% | Suppressed ($N=3 < 5$) | None (Protected) |
| **Daniel Ricciardo** | 3 | 1 | 33.3% | Suppressed ($N=3 < 5$) | None (Protected) |
| **Valtteri Bottas** | 2 | 0 | 0.0% | Suppressed ($N=2 < 5$) | None (Protected) |
| **Oliver Bearman** | 1 | 1 | 100.0% | Suppressed ($N=1 < 5$) | None (Protected) |
| **Franco Colapinto** | 1 | 1 | 100.0% | Suppressed ($N=1 < 5$) | None (Protected) |
| **Liam Lawson** | 1 | 1 | 100.0% | Suppressed ($N=1 < 5$) | None (Protected) |

### 3.4 Segmented Grid-Tier Position Deltas

#### Front Tier (P1–P4 Starting Grid)
| Driver | Starts | Classified | Non-Classified | Total Net Delta | Avg Position Delta | Insight Generated |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Lando Norris** | 19 | 19 | 0 | -36 | **-1.89** | `GRID_TIER_POSITION_LOSS` |
| **Max Verstappen** | 18 | 17 | 1 (R03 DNF) | -9 | **-0.53** | None ($> -1.50$) |
| **Carlos Sainz** | 13 | 12 | 1 (R17 DNF) | 0 | **+0.00** | None ($> -1.50$) |
| **Charles Leclerc** | 12 | 12 | 0 | +2 | **+0.17** | None ($> -1.50$) |
| **George Russell** | 11 | 10 | 1 (R12 DNF) | -14 | **-1.40** | None ($> -1.50$) |
| **Oscar Piastri** | 8 | 8 | 0 | -7 | **-0.88** | None ($> -1.50$) |
| **Sergio Perez** | 6 | 5 | 1 (R17 DNF) | -5 | **-1.00** | None ($> -1.50$) |
| **Lewis Hamilton** | 4 | 4 | 0 | 0 | +0.00 | Suppressed ($N=4 < 5$) |
| *Drivers with $N < 4$* | — | — | — | — | — | Suppressed ($N < 5$) |

#### Lower Tier (P11–P20 Starting Grid, Minimum $N \ge 5$ Starts)
| Driver | Starts | Classified | Non-Classified | Total Net Delta | Avg Position Delta | Insight Generated |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Lewis Hamilton** | 7 | 5 | 2 (R03, R19) | +41 | **+8.20** | `GRID_TIER_POSITION_GAIN` |
| **Franco Colapinto** | 8 | 5 | 3 (R21, R22, R23) | +22 | **+4.40** | `GRID_TIER_POSITION_GAIN` |
| **Sergio Perez** | 10 | 8 | 2 (R08, R09) | +28 | **+3.50** | `GRID_TIER_POSITION_GAIN` |
| **Pierre Gasly** | 16 | 14 | 2 (R03, R11) | +38 | **+2.71** | `GRID_TIER_POSITION_GAIN` |
| **Nico Hulkenberg** | 13 | 10 | 3 (R08, R10, R21) | +22 | **+2.20** | `GRID_TIER_POSITION_GAIN` |
| **Guanyu Zhou** | 24 | 22 | 2 (R08, R11) | +48 | **+2.18** | `GRID_TIER_POSITION_GAIN` |
| **Kevin Magnussen** | 19 | 17 | 2 (R08, R11) | +35 | **+2.06** | `GRID_TIER_POSITION_GAIN` |
| **Fernando Alonso** | 7 | 6 | 1 (R20) | +12 | **+2.00** | `GRID_TIER_POSITION_GAIN` |
| **Liam Lawson** | 5 | 4 | 1 (R23) | +7 | **+1.75** | None ($< +2.00$) |
| **Daniel Ricciardo** | 15 | 13 | 2 (R04, R05) | +19 | **+1.46** | None ($< +2.00$) |
| **Esteban Ocon** | 18 | 16 | 2 (R10, R23) | +15 | **+0.94** | None ($< +2.00$) |
| **Alexander Albon** | 16 | 12 | 4 (R08, R14, R18, R20) | +11 | **+0.92** | None ($< +2.00$) |
| **Logan Sargeant** | 14 | 12 | 2 (R04, R06) | +10 | **+0.83** | None ($< +2.00$) |
| **Lance Stroll** | 17 | 15 | 2 (R02, R16) | +11 | **+0.73** | None ($< +2.00$) |
| **Valtteri Bottas** | 22 | 22 | 0 | 0 | **+0.00** | None ($< +2.00$) |
| **Yuki Tsunoda** | 12 | 8 | 4 (R03, R08, R14, R16) | -4 | **-0.50** | None ($< +2.00$) |

---

## 4. Edge-Case Handling Architecture

### 4.1 Did Not Start (DNS) Handling
- **Database Signature:** `position_text = 'W'` or `status ILIKE '%start%'`.
- **Occurrences in 2024:**
  1. Pierre Gasly (Round 12, British GP): Qualified P20, grid 19, gearbox issue on formation lap (`status='Did not start'`).
  2. Alexander Albon (Round 21, São Paulo GP): Qualified P7, severe crash in qualifying, unable to repair car (`status='Did not start'`).
  3. Lance Stroll (Round 21, São Paulo GP): Qualified P10, formation lap spin into gravel (`status='Did not start'`).
- **Policy:** Excluded unconditionally from starting grid counts, tier counts, and top-10 conversion starts. Gasly, Albon, and Stroll record `dns_count = 1`. Albon and Stroll had qualifying P7 and P10 but are NOT penalized in Top-10 Conversion rate.

### 4.2 Pit-Lane Starts
- **Database Signature:** `grid_position IS NULL` or `grid_position <= 0`.
- **Occurrence in 2024:** Esteban Ocon (Round 20, Mexico GP): Started from pit lane (`grid_position = 0`, finished P13).
- **Policy:** Tracked separately in `pit_lane_starts_count`. Excluded from grid tiers (Front, Midfield, Lower) and top-10 starts because the driver did not line up on the physical grid.

### 4.3 Unclassified Finishes (DNFs & DSQs)
- **Database Signature:** `position_text` non-numeric or `status` in `('Retired', 'Disqualified', 'Did not start', 'Withdrawn')`.
- **Policy:**
  - For conversion rates (e.g. pole-to-win, front-row podium retention, top-10 points conversion), an unclassified finish is counted as a failed conversion ($0$).
  - For position deltas ($\Delta_{\text{pos}}$), unclassified results are tracked in `non_classified_results` and strictly excluded from the delta summation. No arbitrary or artificial finishing positions are invented.

### 4.4 Substitute Drivers
- **Oliver Bearman:** 3 starts (R02 Ferrari P7 finish, R17 Haas P10 finish, R21 Haas P12 finish). Top-10 starts = 1, converted = 1 ($100.0\%$). Sample size $1 < 5 \implies$ zero insights emitted.
- **Franco Colapinto:** 9 starts (R16–R24 Williams). Lower tier starts = 8, classified = 5, non-classified = 3, net delta = +22, avg delta = +4.40. Sample size $8 \ge 5 \implies$ emits `GRID_TIER_POSITION_GAIN`.
- **Liam Lawson:** 6 starts (R19–R24 RB). Lower tier starts = 5, classified = 4, non-classified = 1, avg delta = +1.75 ($< +2.00 \implies$ no insight emitted).
- **Reference-Only Entities:** Andrea Kimi Antonelli and Jack Doohan have zero Grand Prix starts $\implies$ produce zero conversion insights.

---

## 5. Architectural Deliverables & File Changes

```
app/
  analytics/
    conversion_analysis.py          [NEW: Pure SQL analytical summary layer]
  statistics/
    conversion.py                   [NEW: Statistical aggregation & evidence metadata layer]
  insights/
    rules.py                        [MODIFIED: 5 new deterministic conversion rules registered]
    evaluators/
      conversion.py                 [NEW: Deterministic rule evaluators with sample-size safeguards]
    engine.py                       [MODIFIED: Integrated conversion insight evaluators]
  services/
    longitudinal_service.py         [MODIFIED: Added driver & season conversion insight service methods]
tests/
  analytics/
    test_conversion_analytics.py    [NEW: 12 comprehensive independent regression tests]
```

### 5.1 Preservation of Baseline Boundaries
- `LongitudinalInsightService.get_season_insights(session, season_year, up_to_round)` remains completely untouched, returning the exact **33 baseline longitudinal insights** verified in Phase 5B.1.
- `LongitudinalInsightService.get_season_conversion_insights(session, season_year, up_to_round)` returns the dedicated **24 deterministic conversion insights**.

---

## 6. Verification & Test Suite Execution

### 6.1 Backend Test Results
```bash
pytest tests/analytics/test_conversion_analytics.py -v
============================= 12 passed in 1.33s ==============================

pytest -m unit -q
================ 363 passed, 123 deselected, 1 warning in 8.79s ================

pytest -m integration -rs -q
================ 123 passed, 363 deselected, 1 warning in 8.32s ================
```
**Total Backend Tests:** **486 passed** (363 unit + 123 integration), 0 failed, 0 skipped.

### 6.2 Frontend Test & Build Results
```bash
cd frontend && npm test -- --run
Test Files  1 passed (1)
     Tests  6 passed (6)
  Duration  5.03s

npm run build
✓ built in 1.33s (0 TypeScript errors)
```

### 6.3 Database Immutability Verification
| Table | Pre-Phase 5B.2A | Post-Phase 5B.2A | Delta | Integrity Status |
|---|:---:|:---:|:---:|:---:|
| `seasons` | 1 | 1 | 0 | EXACT MATCH |
| `circuits` | 24 | 24 | 0 | EXACT MATCH |
| `constructors` | 10 | 10 | 0 | EXACT MATCH |
| `drivers` | 25 | 25 | 0 | EXACT MATCH |
| `races` | 24 | 24 | 0 | EXACT MATCH |
| `qualifying_results` | 479 | 479 | 0 | EXACT MATCH |
| `sprint_results` | 120 | 120 | 0 | EXACT MATCH |
| `race_results` | 479 | 479 | 0 | EXACT MATCH |
| `lap_times` | 26,574 | 26,574 | 0 | EXACT MATCH |
| `pit_stops` | 825 | 825 | 0 | EXACT MATCH |
| `driver_standings` | 519 | 519 | 0 | EXACT MATCH |
| `constructor_standings` | 240 | 240 | 0 | EXACT MATCH |
| `etl_log` | 38 | 38 | 0 | EXACT MATCH |

**Result:** Zero database records created, modified, or deleted.

---

## 7. Known Limitations & Epistemic Boundaries

1. **Descriptive, Not Causal:** Conversion rates describe what occurred across historical races; they do not isolate driver talent from car performance, tyre strategy, or race incident luck.
2. **Qualifying Grid Penalties:** A driver who qualifies P1 but takes an engine penalty (e.g. Verstappen in Belgium qualifying P1, starting P11) is tracked on Qualifying classification for pole metrics, and on actual grid slot (P11) for grid tiers.
3. **No Lap-by-Lap Telemetry:** Position changes represent net start-to-finish changes; they do not measure intermediate overtakes or pit-stop cycle overtakes.

---

## 8. GO / NO-GO Recommendation

**Recommendation:** **GO — FREEZE & ACCEPT PHASE 5B.2A**

All 8 acceptance criteria are fully met:
1. All four analytical conversion capabilities implemented and mathematically sound.
2. Independent SQL reference queries reconcile 100% with application summaries.
3. Minimum sample-size safeguards strictly enforced across all rules.
4. All edge cases (DNS, DNF, DSQ, pit-lane starts, substitute drivers) verified with explicit tests.
5. Evidence traceability complete with audit trail in every insight.
6. All existing 474 backend and 6 frontend tests pass without modification.
7. Database row counts exhibit zero mutations across all 13 tables.
8. Git working tree is clean on tracked files; `.env` remains untracked and protected.

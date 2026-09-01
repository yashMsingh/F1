# F1 Race Intelligence — Analytics Specification

> Last updated: 2026-09-01
> Status: Initial specification — metrics defined but not yet implemented

This document defines every analytical metric used by the platform. Each metric has a name, definition, formula, source fields, edge cases, example, and interpretation.

**Rule**: No metric may be implemented before it is specified in this document.

---

## 1. Driver Performance Metrics

### 1.1 Average Finishing Position

| Property | Value |
|----------|-------|
| **Name** | Average Finishing Position |
| **Definition** | Mean finishing position across classified race finishes |
| **Formula** | `SUM(finishing_position) / COUNT(classified_finishes)` |
| **Source Fields** | `race_results.finishing_position`, `race_results.status` |
| **Scope** | Per driver, per season or career |
| **Edge Cases** | Exclude DNF, DNS, DSQ (where `finishing_position` IS NULL or status indicates non-classification). Include lapped finishers ("+1 Lap", "+2 Laps") as classified. |
| **Example** | Norris finishes P1, P3, P2, DNF, P4 → avg = (1+3+2+4)/4 = 2.5 |
| **Interpretation** | Lower is better. Compare within era (field size = 20 drivers consistently in modern F1). |

### 1.2 Average Qualifying Position

| Property | Value |
|----------|-------|
| **Name** | Average Qualifying Position |
| **Definition** | Mean qualifying position across sessions where driver set a time |
| **Formula** | `SUM(qualifying_position) / COUNT(qualifying_entries)` |
| **Source Fields** | `qualifying_results.position` |
| **Scope** | Per driver, per season or career |
| **Edge Cases** | Exclude races where driver did not participate in qualifying (grid penalties may differ from qualifying position — we use qualifying position, not grid position). Some historical races lack qualifying data. |
| **Example** | Driver qualifies P2, P5, P1, P3 → avg = 2.75 |
| **Interpretation** | Lower is better. Measures one-lap pace. |

### 1.3 Positions Gained / Lost

| Property | Value |
|----------|-------|
| **Name** | Positions Gained/Lost |
| **Definition** | Difference between starting grid position and finishing position |
| **Formula** | `grid_position - finishing_position` |
| **Source Fields** | `race_results.grid_position`, `race_results.finishing_position` |
| **Scope** | Per driver per race |
| **Edge Cases** | **Both must be non-NULL and > 0**. Exclude: DNS (grid but no finish), DNF (may have NULL finishing_position), DSQ, pit-lane starts (grid=0). If `grid_position = 0`, treat as NULL/excluded. |
| **Example** | Grid P16, Finish P4 → gained 12 positions. Grid P1, Finish P9 → lost 8 positions. |
| **Interpretation** | Positive = gained positions (good race pace / start). Negative = lost positions. Zero = maintained position. |

### 1.4 DNF Rate

| Property | Value |
|----------|-------|
| **Name** | DNF Rate |
| **Definition** | Proportion of race entries that did not finish |
| **Formula** | `COUNT(dnf_races) / COUNT(races_entered)` |
| **Source Fields** | `race_results.status` |
| **Classification** | A race is a "DNF" if `status` is NOT one of: `'Finished'`, or matches pattern `'+N Lap(s)'`. All other statuses (Retired, Collision, Engine, Gearbox, etc.) count as DNF. Disqualified counts as DNF for this metric. |
| **Scope** | Per driver, per season or career |
| **Edge Cases** | DNS (did not start) should be excluded from both numerator and denominator — the driver did not "race". |
| **Example** | 20 races entered, 3 DNFs → rate = 0.15 (15%) |
| **Interpretation** | Lower is better. Separable into "mechanical DNF" vs "incident DNF" if status values are categorized. |

### 1.5 Points Per Race

| Property | Value |
|----------|-------|
| **Name** | Points Per Race |
| **Definition** | Average points scored per race entered |
| **Formula** | `SUM(points) / COUNT(races_entered)` |
| **Source Fields** | `race_results.points` |
| **Scope** | Per driver, per season |
| **Edge Cases** | Include sprint points if aggregating total. Define "races entered" = races where driver started (exclude DNS). Points include fastest-lap bonus point where awarded. |
| **Example** | 423 points in 24 races → 17.6 PPR |
| **Interpretation** | Higher is better. Context-dependent (dominant car inflates this). |

### 1.6 Win Rate

| Property | Value |
|----------|-------|
| **Name** | Win Rate |
| **Definition** | Proportion of race entries resulting in a win |
| **Formula** | `COUNT(finishing_position = 1) / COUNT(races_entered)` |
| **Source Fields** | `race_results.finishing_position` |
| **Scope** | Per driver, per season or career |
| **Edge Cases** | DNS excluded from denominator. |
| **Example** | 7 wins in 24 races → 29.2% |
| **Interpretation** | Higher is better. |

### 1.7 Podium Rate

| Property | Value |
|----------|-------|
| **Name** | Podium Rate |
| **Definition** | Proportion of race entries resulting in a top-3 finish |
| **Formula** | `COUNT(finishing_position <= 3) / COUNT(races_entered)` |
| **Source Fields** | `race_results.finishing_position` |
| **Scope** | Per driver, per season or career |
| **Edge Cases** | Same as Win Rate. |
| **Example** | 18 podiums in 24 races → 75% |
| **Interpretation** | Higher is better. |

### 1.8 Qualifying vs Race Performance Delta

| Property | Value |
|----------|-------|
| **Name** | Qualifying-to-Race Delta |
| **Definition** | Average positions gained or lost from qualifying position to finishing position |
| **Formula** | `AVG(qualifying_position - finishing_position)` over classified races |
| **Source Fields** | `qualifying_results.position`, `race_results.finishing_position` |
| **Scope** | Per driver, per season |
| **Edge Cases** | Only include races where both qualifying position and classified finishing position exist. Grid penalties may cause grid ≠ qualifying; this metric uses QUALIFYING position (pure pace) not grid. |
| **Example** | Qualifies P5, finishes P2 → delta = +3 (gained). Avg over season measures "race craft". |
| **Interpretation** | Positive = typically finishes ahead of qualifying (strong race pace). Negative = typically finishes behind qualifying. |

### 1.9 Teammate Head-to-Head

| Property | Value |
|----------|-------|
| **Name** | Teammate Qualifying Head-to-Head |
| **Definition** | Number of races where driver out-qualified their teammate |
| **Formula** | `COUNT(driver_quali < teammate_quali) / COUNT(shared_races)` |
| **Source Fields** | `qualifying_results.position`, `race_results.constructor_id` |
| **Scope** | Per driver pair, per season |
| **Edge Cases** | Mid-season driver changes — only count races where both teammates participated. If one driver DNS'd qualifying, exclude that race. |
| **Example** | Norris beats Piastri in qualifying 14/24 races → 58.3% |
| **Interpretation** | >50% = generally faster in qualifying than teammate. |

**Variant**: Teammate Race Head-to-Head — same logic but using `finishing_position`. Only count races where both teammates are classified.

---

## 2. Constructor Performance Metrics

### 2.1 Constructor Points

| Property | Value |
|----------|-------|
| **Name** | Total Constructor Points |
| **Definition** | Sum of points scored by both drivers |
| **Formula** | `SUM(points) WHERE constructor_id = X AND season = Y` |
| **Source Fields** | `race_results.points`, `race_results.constructor_id` |
| **Edge Cases** | Include sprint points. Handle mid-season constructor name changes. |

### 2.2 Constructor Reliability Index

| Property | Value |
|----------|-------|
| **Name** | Mechanical DNF Rate |
| **Definition** | Proportion of entries retired due to mechanical failure |
| **Formula** | `COUNT(mechanical_dnf) / COUNT(entries)` |
| **Source Fields** | `race_results.status` |
| **Classification** | Mechanical DNF = status IN ('Engine', 'Gearbox', 'Hydraulics', 'Brakes', 'Suspension', 'Electrical', 'Transmission', etc.). Accident/Collision are NOT mechanical. |
| **Edge Cases** | Ambiguous statuses (e.g., "Retired" without detail) may need manual categorization or separate "unknown" category. |

### 2.3 Constructor Qualifying Pace

| Property | Value |
|----------|-------|
| **Name** | Average Team Qualifying Position |
| **Definition** | Average qualifying position across both drivers |
| **Formula** | `AVG(qualifying_position) WHERE constructor = X` |
| **Source Fields** | `qualifying_results.position`, `qualifying_results.constructor_id` |
| **Edge Cases** | One driver may DNS qualifying (exclude that entry). |

### 2.4 Driver Contribution Index

| Property | Value |
|----------|-------|
| **Name** | Driver Point Contribution |
| **Definition** | Percentage of constructor points contributed by each driver |
| **Formula** | `driver_points / constructor_total_points * 100` |
| **Source Fields** | `race_results.points` |
| **Edge Cases** | Constructor with 0 total points → undefined (display as N/A). |

---

## 3. Race-Level Metrics

### 3.1 Pit Stop Performance

| Property | Value |
|----------|-------|
| **Name** | Pit Stop Duration |
| **Definition** | Total time spent in pit lane per stop |
| **Formula** | Direct from `pit_stops.duration_seconds` |
| **Source Fields** | `pit_stops.duration_seconds` |
| **Edge Cases** | Red-flag pit stops have anomalously long durations — **must be filtered or flagged**. Duration includes pit-lane speed limit time, not just stationary time. Some very old seasons may lack pit-stop data. |

### 3.2 Number of Pit Stops Per Race

| Property | Value |
|----------|-------|
| **Name** | Stop Count |
| **Definition** | Total pit stops made by a driver in a race |
| **Formula** | `MAX(stop_number) WHERE race = X AND driver = Y` |
| **Source Fields** | `pit_stops.stop_number` |
| **Edge Cases** | Red-flag stops inflated count. |

### 3.3 Race Pace (Median Lap Time)

| Property | Value |
|----------|-------|
| **Name** | Race Pace |
| **Definition** | Median lap time excluding outlier laps |
| **Formula** | `MEDIAN(time_millis)` excluding lap 1, in-laps, out-laps, safety-car laps |
| **Source Fields** | `lap_times.time_millis` |
| **Edge Cases** | Lap 1 is always slow (standing start). In-laps and out-laps around pit stops are slow. Safety-car periods produce slow laps. We may not have safety-car data — use statistical outlier removal (e.g., exclude laps > 1.1x median). |
| **Interpretation** | Measures genuine race pace. Median is more robust to outliers than mean. |

---

## 4. Championship Progression Metrics

### 4.1 Championship Points Trajectory

| Property | Value |
|----------|-------|
| **Name** | Points Trajectory |
| **Definition** | Cumulative points after each round |
| **Formula** | Cumulative sum from `driver_standings` ordered by round |
| **Source Fields** | `driver_standings.points`, `driver_standings.round` |
| **Edge Cases** | Point deductions (rare) may cause non-monotonic progression. |
| **Visualization** | Line chart, one line per driver, x-axis = round, y-axis = cumulative points |

### 4.2 Championship Gap

| Property | Value |
|----------|-------|
| **Name** | Gap to Leader |
| **Definition** | Point difference between driver and championship leader at each round |
| **Formula** | `leader_points - driver_points` at each round |
| **Source Fields** | `driver_standings` |
| **Interpretation** | Shows how the championship battle evolves over the season. |

---

## 5. Statistical Methods

### 5.1 Rolling Average

| Property | Value |
|----------|-------|
| **Name** | N-Race Rolling Average |
| **Definition** | Moving average over last N races |
| **Formula** | `AVG(metric) OVER (ORDER BY race_date ROWS BETWEEN N-1 PRECEDING AND CURRENT ROW)` |
| **Parameters** | N = 5 (default for "recent form") |
| **Use Case** | Detecting performance trends, smoothing noise |
| **Edge Cases** | Fewer than N races available at start of career/season — use available races with annotation |

### 5.2 Z-Score (Outlier Detection)

| Property | Value |
|----------|-------|
| **Name** | Z-Score |
| **Definition** | How many standard deviations a value is from the mean |
| **Formula** | `(x - μ) / σ` |
| **Use Case** | Identifying anomalous performances (e.g., unusually fast pit stop, unexpectedly poor finishing position) |
| **Threshold** | |z| > 2.0 flagged as potential anomaly; |z| > 3.0 flagged as significant anomaly |
| **Edge Cases** | Requires sufficient sample size (N ≥ 10 recommended). σ = 0 if all values identical (skip). |

### 5.3 Pearson Correlation

| Property | Value |
|----------|-------|
| **Name** | Pearson Correlation Coefficient |
| **Definition** | Linear correlation between two continuous variables |
| **Formula** | Standard Pearson's r |
| **Use Case** | E.g., correlation between qualifying position and finishing position |
| **Requirements** | Both variables continuous, approximately normal, N ≥ 20 |
| **Output** | r value (-1 to +1) and p-value |
| **Interpretation** | r > 0.7 strong positive; r < -0.7 strong negative; always report p-value |

### 5.4 Linear Regression

| Property | Value |
|----------|-------|
| **Name** | OLS Linear Regression |
| **Definition** | Fit a linear model to identify trends |
| **Use Case** | Performance trend over time (e.g., is a driver improving over the season?) |
| **Output** | Slope, intercept, R², p-value of slope |
| **Requirements** | N ≥ 10 data points; check residuals for normality |
| **Interpretation** | Slope direction indicates trend. R² indicates explanatory power. Always report confidence interval on slope. |

### 5.5 Confidence Interval

| Property | Value |
|----------|-------|
| **Name** | Confidence Interval |
| **Definition** | Range within which the true parameter is expected to lie |
| **Formula** | `x̄ ± t(α/2, n-1) × (s / √n)` |
| **Level** | 95% (default) |
| **Use Case** | Reporting uncertainty on averages (e.g., "average finishing position: 3.2 ± 0.8") |
| **Requirements** | N ≥ 10 for t-distribution approximation |

---

## 6. Insight Detection Triggers

These are the deterministic rules that the Insight Engine uses to identify candidate findings.

| Trigger | Detection Rule | Severity |
|---------|---------------|----------|
| Unexpected Underperformance | Finishing position > (season avg + 2σ) for that driver | MEDIUM |
| Significant Improvement | 5-race rolling avg improved by > 3 positions vs prior 5 races | MEDIUM |
| Constructor Shift | Constructor's avg finishing position changed by > 2 positions between race windows | HIGH |
| Teammate Divergence | One teammate scores ≥ 3x more points than other over 5-race window | MEDIUM |
| Unusual Strategy | Number of pit stops differs from ≥ 80% of field | LOW |
| Large Position Gain | Positions gained > 10 in a single race | LOW |
| Reliability Anomaly | ≥ 2 mechanical DNFs in 3 races for same constructor | HIGH |
| Pace Anomaly | Median race pace > 1.5σ faster/slower than season average for that driver | MEDIUM |
| Qualifying Anomaly | Qualifying position > 2σ from driver's season average | LOW |
| Championship Momentum | Points gap to leader changed by > 20 points in 3 races | HIGH |

> **Note**: These thresholds are initial values. They should be calibrated against historical data during implementation and adjusted if they produce too many or too few findings.

---

## 7. Metric Implementation Priority

| Priority | Metrics | Phase |
|----------|---------|-------|
| P0 (Critical) | Positions Gained/Lost, Average Finishing Position, Points Per Race, DNF Rate, Championship Points Trajectory | Phase 4 (SQL Analytics) |
| P1 (High) | Teammate H2H, Qualifying vs Race Delta, Pit Stop Duration, Constructor Reliability | Phase 4 |
| P2 (Medium) | Rolling Averages, Z-Score outlier detection, Race Pace, Constructor Qualifying Pace | Phase 5 (Statistics) |
| P3 (Future) | Correlation, Regression, Confidence Intervals, all Insight Triggers | Phase 5-6 |

# Statistical Analysis & Evidence Layer

## 1. Overview & Purpose

The statistical analysis and evidence layer (`app/statistics/`) transforms deterministic analytical facts from the SQL layer (`app/analytics/`) into structured, reproducible statistical evidence.

The layer provides raw numerical distributions, descriptive statistics, dispersion metrics, and sample-size metadata. It does **not** interpret data or generate narrative insights.

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
Statistical Analysis / Evidence Layer (Phase 2B.5)  ← THIS LAYER
      ↓
Deterministic Insight Engine (Future Phase)
      ↓
AI Narrative (Future Phase)
      ↓
Dashboard (Future Phase)
```

---

## 2. Critical Principles

### 2.1 Evidence ≠ Insight
This layer produces purely mathematical evidence. It never emits subjective statements or labels such as:
- *"Driver X was dominant"*
- *"Driver Y is inconsistent"*
- *"Team Z has the best pit crew"*

Instead, it outputs structured facts:
```text
mean_qualifying_delta = -358.0 ms
sample_size = 1
stddev = None
```
Interpretation belongs strictly to downstream layers.

### 2.2 Sample Size is Mandatory
Every statistical summary exposes `sample_size` alongside `QualityMetadata` (`total_observations`, `valid_observations`, `excluded_observations`). An average over 2 races must never be treated as having the same epistemic weight as an average over 40 races.

### 2.3 Strict Handling of Missing Values (No Silent Coercion)
- Missing starting grid (e.g. pit lane start) or missing finish (e.g. DNF, DNS, DSQ) is strictly excluded and logged as an excluded observation.
- Missing values are **never** coerced to 0.
- Missing pit stop durations or missing lap times are excluded from averages and never treated as zero-second events.

### 2.4 No Global Driver Scores or Composite Ratings
There is no "Driver Performance Index", "Driver Score", or composite ranking. Drivers are evaluated across independent evidence dimensions (qualifying deltas, position changes, lap times, points).

### 2.5 No Causal Claims
Statistical outputs represent associations and distributions, never causation. Claims such as *"pit stops caused the driver to lose positions"* are strictly prohibited.

---

## 3. Mathematical Formulas & Definitions

### 3.1 Sample Size Contracts
Let $n$ be the number of valid (non-`None`) observations in a sample:
- **$n = 0$**: All statistics (`mean`, `median`, `stddev`, `min`, `max`, `q1`, `q3`, `iqr`) are `None`. `sample_size = 0`.
- **$n = 1$**: `mean = median = min = max = x_1`. Dispersion statistics (`stddev`, `q1`, `q3`, `iqr`) are strictly `None`.
- **$n \ge 2$**: Full descriptive summary is computed.

### 3.2 Mean (Arithmetic Average)
$$\bar{x} = \frac{1}{n} \sum_{i=1}^n x_i$$

### 3.3 Median
For an ordered sequence $x_{(1)} \le x_{(2)} \le \dots \le x_{(n)}$:
$$\text{median} = \begin{cases} x_{\left(\frac{n+1}{2}\right)} & \text{if } n \text{ is odd} \\ \frac{1}{2}\left(x_{\left(\frac{n}{2}\right)} + x_{\left(\frac{n}{2} + 1\right)}\right) & \text{if } n \text{ is even} \end{cases}$$

### 3.4 Sample Standard Deviation (Bessel's Correction)
For $n \ge 2$, sample standard deviation uses $n - 1$ in the denominator to provide an unbiased estimate of population variance:
$$s = \sqrt{\frac{1}{n - 1} \sum_{i=1}^n (x_i - \bar{x})^2}$$
For $n < 2$, $s = \text{None}$.

### 3.5 Quantiles and Interquartile Range (IQR)
Quantiles are calculated using the inclusive percentile method via `statistics.quantiles(data, n=4, method='inclusive')`:
$$\text{IQR} = Q_3 - Q_1$$
For $n < 2$, $Q_1$, $Q_3$, and $\text{IQR}$ are `None`.

### 3.6 Position-Change Categorical Rates
For a set of valid position changes of size $n$:
$$\text{positive\_rate} = \frac{\text{count}(x > 0)}{n}, \quad \text{negative\_rate} = \frac{\text{count}(x < 0)}{n}, \quad \text{zero\_rate} = \frac{\text{count}(x = 0)}{n}$$
*Denominator rule*: The denominator is strictly $n = \text{valid\_observations}$, **never** total entries.

### 3.7 Coefficient of Variation (CV)
$$\text{CV} = \frac{s}{\bar{x}}$$
*Restrictions*:
- Only evaluated when `allow_cv=True` is explicitly passed.
- Strictly restricted to naturally positive ratio scales (e.g. pit stop durations).
- If $\bar{x} \le 0$ or the metric can legitimately cross zero (such as position change or time deltas), $\text{CV} = \text{None}$.

---

## 4. Sign Conventions & Units

| Metric | Unit | Sign Convention |
|---|---|---|
| Qualifying Delta | Integer milliseconds | $\text{driver\_a} - \text{driver\_b}$ (Negative = Driver A faster) |
| Grid Delta | Integer positions | $\text{grid\_a} - \text{grid\_b}$ (Negative = Driver A started ahead) |
| Finish Delta | Integer positions | $\text{finish\_a} - \text{finish\_b}$ (Negative = Driver A finished ahead) |
| Points Delta | Decimal points | $\text{points\_a} - \text{points\_b}$ (Positive = Driver A scored more) |
| Position Change | Integer positions | $\text{grid} - \text{finish}$ (Positive = Gained, Negative = Lost) |
| Lap Times | Integer milliseconds | Absolute elapsed time per lap |
| Pit Stop Duration | Integer milliseconds | Total elapsed pit lane duration |

*Driver Ordering Rule*: Teammates are ordered alphabetically by `driver_id` (`driver_a < driver_b`). This prevents arbitrary or subjective assignment of who is "A" vs "B".

---

## 5. Module Architecture

The `app/statistics/` package contains:

| Module | Purpose | Key Functions |
|---|---|---|
| `types.py` | Immutable result schemas | `DescriptiveStats`, `QualityMetadata`, `PositionChangeStats`, `PositionChangeDistribution`, `QualifyingDeltaStats`, `LapTimeStats`, `PitStopStats`, `ConsistencyStats`, `TeammateHeadToHeadStats` |
| `descriptive.py` | Core mathematical algorithms | `compute_descriptive_stats()`, `compute_consistency_stats()` |
| `position_change.py` | Position change statistics & distributions | `compute_position_change_stats()`, `compute_position_change_distribution()`, `compute_driver_position_change_stats()` |
| `qualifying.py` | Teammate qualifying delta statistics | `compute_qualifying_delta_stats()`, `compute_constructor_qualifying_delta()` |
| `race_pace.py` | Lap time statistics & fastest recorded lap | `compute_lap_time_stats()` |
| `pit_stops.py` | Pit stop duration stats & variability | `compute_pit_stop_stats()` |
| `teammate.py` | Multi-race teammate head-to-head evidence | `compute_teammate_head_to_head_stats()`, `compute_constructor_head_to_head()` |

---

## 6. Current Dataset Limitations & Deferred Capabilities

1. **One-Race Dataset (Bahrain 2024)**:
   - For single-race summaries, multi-race statistics will naturally have `sample_size = 1`.
   - Where $n = 1$, standard deviation is legitimately `None`. The system does not fabricate artificial multi-race samples.
2. **Hypothesis Testing & p-values**:
   - Hypothesis tests (e.g. t-tests, Mann-Whitney U) are intentionally deferred until multi-race and multi-season datasets are available to avoid violating statistical assumptions on tiny sample sizes.
3. **Correlation & Regression**:
   - Linear regression and Pearson correlation across multiple races are deferred to prevent spurious correlations on insufficient data.
4. **Outlier Removal**:
   - Outliers are intentionally **not** automatically stripped. Unusually slow laps (e.g. safety car, damage) and pit stops (e.g. front wing change) represent genuine historical evidence.

---

## 7. Zero Dependency Verification

All statistical operations in `app/statistics/` are implemented using standard library modules (`statistics`, `math`, `typing`, `collections`, `dataclasses`). No third-party data science dependencies were added to `pyproject.toml`.

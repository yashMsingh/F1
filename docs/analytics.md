# Analytical Data Layer & SQL Analytics Foundation

## 1. Overview

The analytical data layer provides a set of deterministic, reusable queries and aggregations that operate on persisted PostgreSQL (or SQLite fallback) data. It transforms normalized database records into typed, structured analytical evidence without relying on external API calls, AI/LLMs, or heuristics.

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
Analytical SQL Layer (Phase 2B.4)  ← THIS LAYER
      ↓
Statistical Analysis (Future Phase)
      ↓
Deterministic Insight Engine (Future Phase)
      ↓
AI Narrative (Future Phase)
      ↓
Dashboard (Future Phase)
```

---

## 2. Design Principles & Non-Negotiables

1. **Database as Source of Truth**: Analytics never calls the Jolpica API or any external network service. All metrics originate directly from persisted database records.
2. **Deterministic & Grounded Evidence**: The analytical layer does not label drivers or constructors as "better", "worse", or "best". It computes exact mathematical deltas and provides raw evidence. Epistemic interpretation belongs strictly to future insight layers.
3. **No Row Multiplication**: Relational joins with 1-to-many children (such as `pit_stops` or `lap_times`) must never duplicate race result rows. Aggregations and counts are computed using isolated scalar subqueries or dedicated grouped queries.
4. **Preserve Missing Values**: `NULL` remains `NULL`. Missing starting positions (e.g. pit-lane starts) or missing finish positions (e.g. DNFs) never silently convert to `0`. Position change is strictly `None` when either starting or finishing position is missing.
5. **Exact Millisecond Arithmetic**: All lap time and duration calculations operate on integer milliseconds (`time_millis`, `duration_millis`) to avoid floating-point drift.
6. **Fully Parameterized**: Queries accept `(season_year, round)` and optional identifiers (`driver_id`, `constructor_id`), allowing arbitrary race and season analytics without hardcoded constants.

---

## 3. Module Structure

The package is located at `app/analytics/`:

| Module | Purpose | Primary Functions |
|---|---|---|
| `app.analytics.types` | Frozen dataclass schemas for all analytical results | `RaceOverview`, `GridVsFinish`, `RaceResultRow`, etc. |
| `app.analytics.race_analysis` | Grand Prix summaries, grid vs. finish changes, and full classified results | `get_race_overview()`, `get_grid_vs_finish()`, `get_race_results()` |
| `app.analytics.qualifying_analysis` | Qualifying order and teammate best-session time comparisons | `get_qualifying_order()`, `get_teammate_qualifying_comparison()` |
| `app.analytics.pit_stop_analysis` | Per-driver and per-constructor pit stop metrics | `get_driver_pit_stops()`, `get_constructor_pit_stops()` |
| `app.analytics.lap_time_analysis` | Per-driver lap time metrics (fastest recorded, average pace) | `get_driver_lap_times()` |
| `app.analytics.standings_analysis` | Official championship standings | `get_driver_standings()`, `get_constructor_standings()` |
| `app.analytics.driver_summary` | Single-driver multi-metric race profile without join multiplication | `get_driver_race_summary()` |
| `app.analytics.constructor_analysis` | Teammate head-to-head comparison per constructor | `get_teammate_comparison()` |

---

## 4. Query Specifications & Metrics

### 4.1 Race Overview (`get_race_overview`)
* **Input**: `(season_year: int, round_num: int)`
* **Returns**: `Optional[RaceOverview]`
* **Metrics**:
  * Race name, circuit name, and race date
  * Winner details: given name, family name, constructor name, total time millis/text (based on `source_position == 1`)
  * `classified_count`: Total drivers with non-NULL `source_position`
  * `total_result_count`: Total entries recorded for the race (classified + retired/DSQ/DNS)

### 4.2 Grid vs Finish (`get_grid_vs_finish`)
* **Input**: `(season_year: int, round_num: int)`
* **Returns**: `list[GridVsFinish]`
* **Formula**: `position_change = grid_position - finish_position`
* **Semantics**:
  * Positive integer (+N): positions gained from starting grid.
  * Negative integer (-N): positions lost.
  * Zero (0): finished at exact grid position.
  * `None`: if `grid_position` is missing (pit-lane start) or `finish_position` is missing (DNF / DNS / DSQ).

### 4.3 Qualifying Analysis (`get_qualifying_order`, `get_teammate_qualifying_comparison`)
* **Deepest-Session Time Logic**:
  * Evaluates driver performance using the deepest session reached: `Q3` > `Q2` > `Q1`.
* **Teammate Comparison**:
  * Pairings grouped by constructor.
  * Deterministic driver ordering: alphabetical by `driver_id` (`driver_a` vs `driver_b`).
  * `delta_millis = best_time_a - best_time_b`.
  * Negative delta indicates `driver_a` set a faster time.
  * Returns `None` if either driver lacks a valid time in any qualifying session.

### 4.4 Pit Stop Analysis (`get_driver_pit_stops`, `get_constructor_pit_stops`)
* **Denominator Rules**:
  * `stop_count`: Uses `MAX(stop_number)` across all stops for the driver.
  * `avg_duration_millis`: `SUM(duration_millis) / COUNT(duration_millis)` strictly filtering out `NULL` durations.
  * `fastest_stop_millis`: `MIN(duration_millis)` on non-NULL durations.
* **Constructor Aggregation**:
  * Maps driver to constructor via `race_results` without joining directly against the main table to avoid multiplicity.
  * Total constructor stops = sum of maximum stops per driver.

### 4.5 Lap Time Analysis (`get_driver_lap_times`)
* **Fastest Recorded vs. Official Fastest Lap**:
  * **Fastest Recorded Lap**: Computed as `MIN(lap_times.time_millis)` across recorded laps in `lap_times`.
  * **Official Fastest Lap**: Recorded in `race_results.fastest_lap_rank` and `race_results.fastest_lap_time_millis` as officially classified by FIA/source data.
* **Denominator Rule**: Laps with `time_millis IS NULL` are counted in `lap_count`, but strictly excluded from `avg_lap_millis` and `fastest_lap_millis`.

### 4.6 Standings Analysis (`get_driver_standings`, `get_constructor_standings`)
* **Source**: Direct queries against persisted `driver_standings` and `constructor_standings` tables.
* **Rule**: Standings are **never** dynamically reconstructed from individual race points. They reflect the official championship state after the specified round.

### 4.7 Driver Race Summary (`get_driver_race_summary`)
* **Anti-Multiplication Strategy**:
  * Rather than joining `race_results` with `pit_stops` (which would duplicate result rows by the number of pit stops), the function queries `race_results` as a single row and evaluates `pit_stop_count` through a scalar count query:
  ```sql
  SELECT COUNT(id) FROM pit_stops WHERE race_id = :race_id AND driver_id = :driver_id
  ```

### 4.8 Constructor & Teammate Analysis (`get_teammate_comparison`)
* **Deterministic Ordering**: Drivers are assigned to `driver_a` and `driver_b` in alphabetical order of `driver_id`.
* **Deltas**:
  * `qualifying_delta_millis`: `best_time_a - best_time_b` (or `None` if either did not set a time)
  * `grid_delta`: `grid_a - grid_b` (or `None` if either had a pit-lane start)
  * `finish_delta`: `finish_a - finish_b` (or `None` if either retired / DNF)
  * `points_delta`: `points_a - points_b` (always Decimal)

---

## 5. Verification & Testing

Tests are located in `tests/analytics/`:
* `test_race_analysis.py`: Race overview, grid vs finish, race results filtering.
* `test_qualifying_analysis.py`: Qualifying classification ordering, teammate qualifying deltas.
* `test_pit_stop_analysis.py`: Per-driver and per-constructor aggregations, NULL duration exclusion.
* `test_lap_time_analysis.py`: Fastest recorded lap, lap pace average, NULL time exclusion.
* `test_standings_analysis.py`: Direct reading from persisted tables.
* `test_driver_summary.py`: Verification of no row multiplication and NULL handling.
* `test_constructor_analysis.py`: Teammate comparisons, deterministic ordering, delta computations.

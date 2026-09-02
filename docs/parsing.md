# Jolpica Parsing, Validation & Time Transformation Layer

## 1. Overview & Architecture

The parsing and validation layer sits strictly between the Jolpica API client (Phase 2B.1) and the future ETL database ingestion layer (Phase 2B.3). It transforms raw Jolpica API response dictionaries or `APIResponse` instances into clean, validated, normalized Python domain dataclasses without making database calls, executing SQL, or modifying models.

```text
Jolpica F1 API
      ↓
Phase 2B.1 — API Client (`app.f1.client`)
      ↓
Raw APIResponse / dictionaries (`MRData` envelope)
      ↓
Phase 2B.2 — Parser + Validation + Time Transformation (`app.f1.parsing`)  ← THIS LAYER
      ↓
Phase 2B.3 — ETL / Idempotent Database Ingestion (Future)
      ↓
SQL Analytics (Future)
      ↓
Deterministic Insight Engine (Future)
      ↓
AI Narrative Layer (Future)
      ↓
Dashboard (Future)
```

## 2. Core Responsibilities

1. **Envelope Extraction**: Extracts and validates the `MRData` response envelope, handling both raw dictionary payloads and client `APIResponse` instances.
2. **Resource Parsing**: Deterministically maps all 12 core Jolpica resources into strongly typed, immutable dataclasses (`app.f1.parsing.models`).
3. **Type Coercion**: Casts numeric strings to appropriate types (`int`, `Decimal`) while rejecting malformed values.
4. **Time & Duration Parsing**: Converts race elapsed times, lap times, pit stop durations, and time gaps into integer milliseconds using integer-only arithmetic to eliminate floating-point drift.
5. **Source-Value Preservation**: Preserves raw source classifications, status values, and text strings alongside converted numeric metrics.
6. **Strict Validation**: Enforces domain validity constraints, raising explicit `F1ValidationError` or `F1StructureError` exceptions instead of guessing or silently corrupting data.

## 3. Explicit Non-Responsibilities

- **No Network Requests**: Does not call external APIs, perform HTTP retries, or paginate.
- **No Database Persistence**: Does not interact with SQLAlchemy, PostgreSQL, Alembic, or sessions.
- **No Analytical Interpretation**: Does not infer DNF cause categories, driver form, tire degradation, or championship momentum.
- **No AI / LLM Calls**: Does not generate text or summaries.

---

## 4. Supported Resources & Domain Records

All domain records are defined in `app/f1/parsing/models.py` as frozen dataclasses:

| Entity | Jolpica Endpoint / Table | Domain Dataclass | Preserved Source Values |
| :--- | :--- | :--- | :--- |
| **Seasons** | `SeasonTable.Seasons` | `ParsedSeason` | `year`, `url` |
| **Circuits** | `CircuitTable.Circuits` | `ParsedCircuit` | `circuit_id`, `circuit_name`, `locality`, `country`, `latitude`, `longitude`, `url` |
| **Constructors** | `ConstructorTable.Constructors` | `ParsedConstructor` | `constructor_id`, `name`, `nationality`, `url` |
| **Drivers** | `DriverTable.Drivers` | `ParsedDriver` | `driver_id`, `given_name`, `family_name`, `code`, `permanent_number`, `date_of_birth`, `nationality`, `url` |
| **Races (Schedule)** | `RaceTable.Races` | `ParsedRace` | `season`, `round`, `race_name`, `circuit_id`, `race_date`, `race_time`, `url` |
| **Race Results** | `RaceTable.Races[].Results` | `ParsedRaceResult` | `source_position`, `position_text`, `status`, `time_text`, `time_millis`, `fastest_lap_time`, `fastest_lap_time_millis`, `car_number`, `grid_position`, `laps_completed`, `points` |
| **Qualifying Results** | `RaceTable.Races[].QualifyingResults` | `ParsedQualifyingResult` | `position`, `car_number`, `q1_time`, `q1_time_millis`, `q2_time`, `q2_time_millis`, `q3_time`, `q3_time_millis` |
| **Sprint Results** | `RaceTable.Races[].SprintResults` | `ParsedSprintResult` | `source_position`, `position_text`, `status`, `time_text`, `time_millis`, `fastest_lap_time`, `fastest_lap_time_millis`, `car_number`, `grid_position`, `laps_completed`, `points` |
| **Pit Stops** | `RaceTable.Races[].PitStops` | `ParsedPitStop` | `stop_number`, `lap`, `time_of_day`, `duration_text`, `duration_millis` |
| **Lap Times** | `RaceTable.Races[].Laps[].Timings` | `ParsedLapTime` | `lap_number`, `position`, `time`, `time_millis` |
| **Driver Standings** | `StandingsTable.StandingsLists[].DriverStandings` | `ParsedDriverStanding` | `position`, `points`, `wins`, `driver_id` |
| **Constructor Standings** | `StandingsTable.StandingsLists[].ConstructorStandings` | `ParsedConstructorStanding` | `position`, `points`, `wins`, `constructor_id` |

---

## 5. Time Transformation Mechanics

Located in `app/f1/parsing/time.py`, the time parser converts string timing values to **canonical integer milliseconds (`int`)**.

### Why Integer Milliseconds?
Floating-point representation (e.g., `float("20.647") * 1000` -> `20647.000000000004`) causes rounding drift in comparisons, delta calculations, and database indexing. Integer arithmetic guarantees exact reproducibility.

### Supported Time Formats

| Format | Pattern | Example Input | Parsed Output (ms) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Elapsed Time (Hours)** | `H:MM:SS.sss` | `"1:31:44.742"` | `5504742` | `(1*3600 + 31*60 + 44)*1000 + 742` |
| **Lap Time / Minutes** | `M:SS.sss` | `"1:22.167"` | `82167` | `(1*60 + 22)*1000 + 167` |
| **Multi-Minute Pit Stop** | `MM:SS.sss` | `"40:55.302"` | `2455302` | `(40*60 + 55)*1000 + 302` (Red flag duration) |
| **Short Duration (Seconds)** | `SS.sss` | `"24.123"` | `24123` | `24*1000 + 123` |
| **Whole Seconds** | `SS` | `"24"` | `24000` | Optional millisecond component defaults to 0 |
| **Whole Hours/Minutes/Seconds** | `H:MM:SS` | `"1:31:44"` | `5504000` | Optional millisecond component defaults to 0 |
| **Positive Gap** | `+SS.sss` / `+M:SS.sss` | `"+0.500"`, `"+22.457"` | `500`, `22457` | Parsed via `parse_gap_to_millis` |
| **Signed Negative Gap** | `-SS.sss` / `-M:SS.sss` | `"-0.500"` | `-500` | Allowed when `allow_negative=True` |

### Categorical Status Filtering
Status strings like `"+1 Lap"`, `"+2 Laps"`, `"Lapped"`, `"Finished"`, or `"Retired"` are **not durations**.
`parse_gap_to_millis` automatically returns `None` for any string containing alphabetic characters, preventing false parsing of status strings as numbers.

---

## 6. Source-Value Preservation Rules

Per architectural decisions in `docs/schema-review.md`:

### 1. Finishing Positions & Status
- Drivers who DNF/retire receive a numeric `position` (e.g. `"18"`), a code `positionText` (e.g. `"R"`), and a reason `status` (e.g. `"Engine"`).
- The parser **preserves `source_position=18`** as an integer alongside `position_text="R"` and `status="Engine"`. It never replaces `source_position` with `None`.

### 2. Pit Stop Durations
- Red flag pit stops are formatted as `MM:SS.sss` (e.g., `"40:55.302"`).
- The parser stores both:
  - `duration_text`: `"40:55.302"` (raw string)
  - `duration_millis`: `2455302` (exact integer milliseconds)
- `"40:55.302"` is never mistakenly parsed as 40.553 seconds.

### 3. Driver & Constructor Independence
- Drivers are not statically bound to constructors. A driver's team association is recorded on the event result (`ParsedRaceResult`, `ParsedQualifyingResult`, `ParsedSprintResult`), preserving mid-season team swaps (e.g., Lawson driving for RB and Red Bull).

---

## 7. Validation & Missing Data Policy

### Exception Hierarchy

```text
F1APIError (app.f1.exceptions)
    └── F1ParsingError (app.f1.parsing.exceptions)
            ├── F1ValidationError (field-level domain constraint failures)
            ├── F1TimeParsingError (time/duration format and boundary errors)
            └── F1StructureError (missing MRData envelope or resource table)
```

### Missing Data vs. Malformed Data

| Condition | Action |
| :--- | :--- |
| **Legitimately missing optional field** (e.g. `Q2` time for Q1-eliminated driver) | Returns `None` |
| **Required field missing / empty** (e.g. `driverId=""`) | Raises `F1ValidationError` |
| **Malformed numeric field** (e.g. `points="twenty"`) | Raises `F1ValidationError` |
| **Impossible time component** (e.g. `seconds=65`, `minutes=75` in `H:MM:SS`) | Raises `F1TimeParsingError` |
| **Negative duration when disallowed** | Raises `F1TimeParsingError` |
| **Invalid stop / lap number** (e.g. `stop=0`, `lap=-1`) | Raises `F1ValidationError` |
| **Missing response table** (e.g. no `RaceTable`) | Raises `F1StructureError` |

**Zero Fabrication Rule**: Missing or invalid values are **never silently replaced with `0` or guessed defaults**.

---

## 8. Usage Example

```python
from app.f1.client import JolpicaClient
from app.f1.parsing import (
    parse_race_results,
    parse_pit_stops,
    parse_qualifying_results,
)

with JolpicaClient() as client:
    response = client.get_race_results(season=2024, round_number=1)
    results = parse_race_results(response)

    for r in results:
        print(f"P{r.source_position} ({r.position_text}): {r.driver_id} [{r.constructor_id}] - {r.status}")
```

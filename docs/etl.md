# ETL & Database Ingestion Infrastructure

## 1. Overview & Architecture

The ETL / persistence layer (`app.etl`) is responsible for taking validated, normalized domain dataclasses produced by the parsing layer (Phase 2B.2) and idempotently persisting them into the relational PostgreSQL database using SQLAlchemy models.

```text
Jolpica F1 API
      ↓
Phase 2B.1 — API Client (`app.f1.client`)
      ↓
Raw APIResponse / dictionaries (`MRData` envelope)
      ↓
Phase 2B.2 — Parser + Validation + Time Transformation (`app.f1.parsing`)
      ↓
Parsed domain records (`Parsed*` dataclasses)
      ↓
Phase 2B.3A — ETL / Persistence Infrastructure (`app.etl`)  ← THIS LAYER
      ├── repositories/ (Entity-specific upsert & dependency resolution)
      ├── service.py (ETLService orchestration & transaction boundaries)
      └── types.py (IngestionStats & IngestionResult tracking)
      ↓
Phase 2B.3B — Controlled Real-Data Ingestion (Future)
      ↓
PostgreSQL Database (Source of Truth)
```

## 2. Core Responsibilities

1. **Transactional Persistence**: Wraps database writes in atomic transaction boundaries. All mutations within an operation succeed together or rollback completely.
2. **Strict Idempotency**: Running the same ingestion repeatedly never generates duplicate logical records.
3. **Change Detection**: Compares incoming field values with existing records using semantic equality (`values_equal`), updating only mutated fields and accurately classifying rows as `inserted`, `updated`, or `skipped`.
4. **Dependency-Aware Ordering**: Resolves natural keys and slug identifiers (e.g. `circuit_id="bahrain"`, `driver_id="max_verstappen"`) to internal surrogate integer foreign keys (`circuit.id`, `driver.id`), strictly enforcing foreign-key hierarchies.
5. **Auditing & Provenance**: Records every ingestion run in the `etl_log` table with timestamps, endpoints, status (`RUNNING`, `SUCCESS`, `FAILED`), and record counters.
6. **Error Visibility**: Never silently swallows database or constraint errors. If a dependency is missing, raises an explicit `F1DependencyError`.

## 3. Explicit Non-Responsibilities

- **No HTTP / Network Calls**: Does not fetch API data, retry HTTP requests, or handle pagination.
- **No JSON / String Parsing**: Operates exclusively on pre-parsed, typed dataclasses.
- **No Time Transformations**: Time string parsing to milliseconds is handled upstream in `app.f1.parsing.time`.
- **No Schema Changes**: Operates strictly against the approved Phase 2A database schema without adding columns or migrations.
- **No Analytics or AI**: Does not compute pace, degradation, driver scores, or generate narrative text.

---

## 4. Entity Persistence & Natural Keys

Every entity is protected by natural unique constraints defined at the schema level:

| Entity | Repository | Natural / Unique Key | Target Database Table |
| :--- | :--- | :--- | :--- |
| **Season** | `SeasonRepository` | `season_year` | `seasons` |
| **Circuit** | `CircuitRepository` | `circuit_id` (slug) | `circuits` |
| **Constructor** | `ConstructorRepository` | `constructor_id` (slug) | `constructors` |
| **Driver** | `DriverRepository` | `driver_id` (slug) | `drivers` |
| **Race** | `RaceRepository` | `(season_year, round)` | `races` |
| **Race Result** | `RaceResultRepository` | `(race_id, driver_id)` | `race_results` |
| **Qualifying Result** | `QualifyingResultRepository` | `(race_id, driver_id)` | `qualifying_results` |
| **Sprint Result** | `SprintResultRepository` | `(race_id, driver_id)` | `sprint_results` |
| **Pit Stop** | `PitStopRepository` | `(race_id, driver_id, stop_number)` | `pit_stops` |
| **Lap Time** | `LapTimeRepository` | `(race_id, driver_id, lap_number)` | `lap_times` |
| **Driver Standing** | `DriverStandingRepository` | `(season_year, round, driver_id)` | `driver_standings` |
| **Constructor Standing** | `ConstructorStandingRepository` | `(season_year, round, constructor_id)` | `constructor_standings` |
| **ETL Log** | `EtlLogRepository` | `id` (autoincrement) | `etl_log` |

---

## 5. Dependency-Aware Execution Order

Child records referencing parent entities must only be ingested after parent records exist:

```text
1. seasons
      ↓
2. circuits
      ↓
3. constructors & drivers
      ↓
4. races (depends on season_year, circuit_id)
      ↓
5. race_results, qualifying_results, sprint_results, pit_stops, lap_times (depend on race_id, driver_id, constructor_id)
      ↓
6. driver_standings, constructor_standings (depend on season_year, driver_id/constructor_id)
```

If a referenced parent (such as a driver or constructor slug) is missing from the database, the repository raises an explicit `F1DependencyError`, aborting the child insertion and rolling back the transaction.

---

## 6. Upsert and Mutation Strategy

When an entity is processed:
1. **Lookup**: The repository checks whether an entity with the natural key exists.
2. **Insert**: If absent, creates a new ORM model instance and adds it to the session (`records_inserted += 1`).
3. **Update**: If present, compares each mutable field with incoming values using `values_equal`:
   - If any field changed, updates the attribute on the existing model (`records_updated += 1`).
   - If all fields match, takes no action (`records_skipped += 1`).

This avoids destructive DELETE-then-INSERT patterns and prevents database ID churn.

---

## 7. Transaction Boundaries & Rollback

- Operations inside `ETLService` execute within a transactional block.
- On success: all record insertions, updates, and the final `etl_log` entry with status `SUCCESS` are flushed/committed.
- On failure: `session.rollback()` is executed immediately, ensuring no partial or corrupted data remains in the database.
- A failed run is recorded in `etl_log` with status `FAILED` and the error message captured.
- The original exception is re-raised so failures remain visible to callers.

---

## 8. ETL Logging & Provenance

Every run records:
- `source`: `"jolpica"`
- `entity_type`: Target entity name or `"race_weekend"`
- `endpoint`: API endpoint path if provided
- `season_year` and `round`: Grand Prix context if available
- `status`: `"RUNNING"` -> `"SUCCESS"` or `"FAILED"`
- `records_processed`, `records_inserted`, `records_updated`, `records_skipped`
- `error_message`: Error details on failure
- `started_at` and `completed_at`: UTC timestamps

---

## 9. Code Usage Example

```python
from app.db.session import get_session_factory
from app.etl import ETLService
from app.f1.parsing.models import ParsedSeason, ParsedCircuit

SessionFactory = get_session_factory()
with SessionFactory() as session:
    service = ETLService(session=session, auto_commit=True)

    # Ingest seasons
    result = service.ingest_seasons([
        ParsedSeason(year=2024, url="https://en.wikipedia.org/wiki/2024_Formula_One_World_Championship")
    ])

    print(f"Status: {result.status}")
    print(f"Inserted: {result.stats.records_inserted}, Skipped: {result.stats.records_skipped}")
```

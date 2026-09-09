# Controlled Real-Data Ingestion: 2024 Bahrain Grand Prix

## 1. Objective & Purpose

Phase 2B.3B validates the end-to-end integration of the Formula 1 Race Intelligence ingestion pipeline using real data from the Jolpica F1 API for a single controlled race weekend:

- **Season**: 2024
- **Round**: 1
- **Race**: Bahrain Grand Prix (Sakhir)
- **Source**: Jolpica F1 API (`https://api.jolpi.ca/ergast/f1/`)
- **Scope**: One Grand Prix weekend only

This phase proves that the pipeline architecture works seamlessly from HTTP extraction through parsing and validation to idempotent relational database persistence without manual interventions or data corruption.

```text
Jolpica F1 API (live endpoints)
        ↓
Phase 2B.1 — JolpicaClient (`app.f1.client`)
        ↓
Phase 2B.2 — Parsers (`app.f1.parsing.parsers`)
        ↓
Phase 2B.3A — ETL Persistence Layer (`app.etl.service.ETLService`)
        ↓
Database Repositories (`app.etl.repositories`)
        ↓
Relational Database (Tables & Constraints)
        ↓
Post-Ingestion Audit & Integrity Verification
```

---

## 2. Ingested Resources & Scope

The controlled runner retrieves and persists the complete relational hierarchy for the event:

| Entity | Endpoint | Count | Notes |
| :--- | :--- | :--- | :--- |
| **Season** | `/seasons.json` | 1 | Year 2024 |
| **Circuit** | `/2024/1/circuits.json` | 1 | `bahrain` (Bahrain International Circuit) |
| **Constructors** | `/2024/1/constructors.json` | 10 | All 10 participating teams |
| **Drivers** | `/2024/1/drivers.json` | 20 | All 20 participating drivers |
| **Race** | `/2024/1.json` | 1 | 2024 Round 1 Bahrain GP |
| **Race Results** | `/2024/1/results.json` | 20 | Finishing order, points, status, fastest lap |
| **Qualifying Results** | `/2024/1/qualifying.json` | 20 | Q1, Q2, Q3 lap times and grid ranking |
| **Sprint Results** | `/2024/1/sprint.json` | 0 | Not applicable (no sprint race held in Bahrain 2024) |
| **Pit Stops** | `/2024/1/pitstops.json` | 43 | Paginated extraction across all stops |
| **Lap Times** | `/2024/1/laps.json` | 1129 | Paginated extraction across all 57 laps |
| **Driver Standings** | `/2024/1/driverStandings.json` | 20 | Standings after Round 1 |
| **Constructor Standings** | `/2024/1/constructorStandings.json` | 10 | Standings after Round 1 |
| **ETL Log** | Database table | 2 | Run 1 and Run 2 execution audit entries |

---

## 3. Execution Flow & Architecture

The ingestion is coordinated by `app/etl/runners/bahrain_2024.py`:

1. **`fetch_and_parse_bahrain_2024(client)`**:
   - Calls the existing `JolpicaClient` methods.
   - Paginates large collections (pit stops, lap times) using `client.iter_pages(endpoint, page_limit=100)`.
   - Passes all API payloads through Phase 2B.2 parsers (`parse_seasons`, `parse_circuits`, `parse_constructors`, `parse_drivers`, `parse_races`, `parse_race_results`, `parse_qualifying_results`, `parse_sprint_results`, `parse_pit_stops`, `parse_lap_times`, `parse_driver_standings`, `parse_constructor_standings`).
   - Collects typed domain dataclasses (`Parsed*`).
2. **`ingest_bahrain_2024(client, service)`**:
   - Passes parsed dataclasses to `ETLService.ingest_race_weekend(...)`.
   - Strictly enforces dependency order:
     `season` $\to$ `circuits` $\to$ `constructors` & `drivers` $\to$ `races` $\to$ child race session data $\to$ championship standings.
   - Executes inside an audited transaction boundary.

---

## 4. Idempotency & Verification

### Double-Run Idempotency Proof
The ingestion script executes the entire pipeline **twice in succession** against the target database:

- **Run 1 (Initial Ingestion)**:
  - `records_processed`: 1275
  - `records_inserted`: 1275
  - `records_updated`: 0
  - `records_skipped`: 0
  - `records_failed`: 0
  - Status: `SUCCESS`
- **Run 2 (Idempotency Run)**:
  - `records_processed`: 1275
  - `records_inserted`: 0
  - `records_updated`: 0
  - `records_skipped`: 1275
  - `records_failed`: 0
  - Status: `SUCCESS`

**Row counts across all 12 tables remain 100% identical between Run 1 and Run 2.**

### Factual & Integrity Checks
- **Winner Check**: Max Verstappen (`driver_id="max_verstappen"`), P1, 26.00 points (25 for win + 1 for fastest lap), 57 laps completed.
- **Pole Check**: Max Verstappen, Q3 lap time `1:29.179`.
- **Pit Stops**: Exactly 43 pit stops recorded, each with valid `stop_number`, `lap`, and parsed duration milliseconds.
- **Lap Times**: Exactly 1129 lap timing entries recorded.
- **No Sprint Session**: Handled gracefully as an empty collection without fabrication or failure.
- **Zero Foreign-Key Violations**: All child rows resolve to valid parent PKs.

---

## 5. How to Run the Controlled Ingestion

### Live Jolpica Run
Run the standalone integration script:

```bash
python scripts/ingest_bahrain_2024.py
```

The script will:
1. Connect to PostgreSQL if accessible via `DATABASE_URL`; otherwise, initialize a local SQLite file database (`data/f1_bahrain_2024.db`) with `PRAGMA foreign_keys=ON`.
2. Execute Run 1 against the live Jolpica API.
3. Verify all SQL row counts and factual data.
4. Execute Run 2 against the live Jolpica API to test idempotency.
5. Print audit logs from `etl_log`.
6. Exit with status code 0 upon success.

### Automated Test Suite (Deterministic Fixtures)
Run automated unit and integration tests without network dependency:

```bash
python -m pytest tests/etl/test_bahrain_ingestion.py -v
```

Or run the entire project test suite:

```bash
python -m pytest tests/ -v
```

---

## 6. Environment & Database Distinction

- **Live Jolpica API Verification**: Real HTTP calls executed against `https://api.jolpi.ca/ergast/f1/` with automatic HTTP 429 rate-limit backoff handling.
- **SQLite File Verification**: Executed during manual script run with foreign key enforcement active (`PRAGMA foreign_keys=ON`).
- **SQLite In-Memory Automated Testing**: Executed during `pytest` test runs with mock responses to ensure fast, deterministic, non-flaky test execution.
- **PostgreSQL Verification**: Configured in project settings (`postgresql://f1user:changeme@localhost:5432/f1_race_intelligence`). In this run, PostgreSQL failed authentication (`FATAL: password authentication failed for user "f1user"`); hence SQLite was utilized and clearly logged per Phase 2B.3B rules.

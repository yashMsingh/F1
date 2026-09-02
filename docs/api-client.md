# F1 Race Intelligence — Jolpica API Client Documentation

> Status: Implemented (Phase 2B.1)
> Package: `app.f1`

---

## 1. Responsibilities & Architecture Boundary

The **Jolpica API Client** is a dedicated transport-layer client responsible for:

- HTTP communication with the Jolpica F1 API (`https://api.jolpi.ca/ergast/f1/`)
- Safe URL construction with automatic `.json` formatting
- Query parameter encoding
- Structural validation of the top-level `MRData` response envelope
- Automated pagination across multi-page datasets
- Bounded exponential backoff retries on transient errors and rate limits (`429`, `500`, `502`, `503`, `504`)
- Configurable timeouts
- Meaningful domain-specific exception hierarchies

### Architecture Boundary
```
Jolpica API
   │
   ▼
HTTP Client (`app.f1.JolpicaClient`)   ◄─── (Phase 2B.1 — This Layer)
   │
   ▼
Raw API Response (`APIResponse`)
   │
   ▼
Parser & Validator                     ◄─── (Phase 2B.2 — Next Layer)
   │
   ▼
PostgreSQL Upsert Repository           ◄─── (Phase 2B.3 — Subsequent)
```

The client does **NOT**:
- Insert, update, or query PostgreSQL models
- Parse Formula 1 specific time strings (e.g. converting lap times to milliseconds)
- Calculate points or standings
- Perform analytical classifications

---

## 2. Configuration & Initialization

The client is configured using `ClientConfig`:

```python
from app.f1 import JolpicaClient, ClientConfig

config = ClientConfig(
    base_url="https://api.jolpi.ca/ergast/f1",
    timeout=15.0,
    max_retries=3,
    backoff_factor=0.5,
    max_backoff=10.0,
)

with JolpicaClient(config=config) as client:
    response = client.get_race_results(season=2024, round_number=1)
```

---

## 3. Supported Endpoint Categories

| Category | Method | Endpoint Pattern | Verified Structure |
| :--- | :--- | :--- | :--- |
| **Seasons** | `get_seasons()`, `get_all_seasons()` | `/seasons.json` | `SeasonTable.Seasons` |
| **Circuits** | `get_circuits()`, `get_all_circuits()` | `/circuits.json` | `CircuitTable.Circuits` |
| **Constructors** | `get_constructors()`, `get_all_constructors()` | `/constructors.json` | `ConstructorTable.Constructors` |
| **Drivers** | `get_drivers()`, `get_all_drivers()` | `/drivers.json` | `DriverTable.Drivers` |
| **Schedule / Races**| `get_races(season)`, `get_all_races(season)` | `/{season}.json` | `RaceTable.Races` |
| **Race Results** | `get_race_results(season, round)` | `/{season}/{round}/results.json` | `RaceTable.Races[0].Results` |
| **Qualifying** | `get_qualifying_results(season, round)` | `/{season}/{round}/qualifying.json`| `RaceTable.Races[0].QualifyingResults` |
| **Sprint** | `get_sprint_results(season, round)` | `/{season}/{round}/sprint.json` | `RaceTable.Races[0].SprintResults` |
| **Pit Stops** | `get_pit_stops(...)`, `get_all_pit_stops(...)` | `/{season}/{round}/pitstops.json` | `RaceTable.Races[0].PitStops` |
| **Lap Times** | `get_lap_times(...)`, `get_all_lap_times(...)` | `/{season}/{round}/laps.json` | `RaceTable.Races[0].Laps` |
| **Driver Standings** | `get_driver_standings(season, round=None)` | `/{season}/driverStandings.json` | `StandingsTable.StandingsLists` |
| **Constructor Standings** | `get_constructor_standings(season, round=None)` | `/{season}/constructorStandings.json` | `StandingsTable.StandingsLists` |

---

## 4. Pagination Model

Jolpica returns pagination metadata in `MRData` with string integers: `limit`, `offset`, and `total`.

The client provides three levels of pagination:
1. **Single Page (`get_page`)**: Returns one `APIResponse` object with `metadata` (`limit`, `offset`, `total`).
2. **Page Generator (`iter_pages`)**: Yields successive `APIResponse` pages until `offset >= total`.
3. **Record Aggregator (`get_all_*`)**: Iterates all pages and aggregates raw records into a single list (e.g. `get_all_pit_stops` or `get_all_lap_times`).

---

## 5. Retry, Rate Limiting & Backoff

- **Retryable Status Codes**: `429` (Rate Limited), `500` (Internal Server Error), `502` (Bad Gateway), `503` (Service Unavailable), `504` (Gateway Timeout), plus network connection failures and timeouts.
- **Non-Retryable Codes**: `400`, `401`, `403`, `404` raise `F1HTTPError` immediately without unnecessary retries.
- **Rate Limit Handling**: When HTTP `429` is returned, the client checks for a `Retry-After` header. If present, it waits for the specified seconds (bounded by `max_backoff`). If absent, it applies exponential backoff: $\text{delay} = \min(\text{backoff\_factor} \times 2^{\text{attempt} - 1}, \text{max\_backoff})$.

---

## 6. Error Hierarchy

```text
F1APIError (Base)
├── F1HTTPError
│   └── F1RateLimitError (HTTP 429 after retries)
├── F1TimeoutError
└── F1ResponseError (Malformed JSON or missing MRData envelope)
```

---

## 7. Testing Approach

- **Mocked Unit Tests (`tests/f1/test_client.py`)**: Uses native `httpx.MockTransport` to simulate 200 OK, 404 Not Found, 429 Rate Limiting with `Retry-After`, 500/503 Server Errors, Read Timeouts, malformed JSON, and multi-page pagination with zero live internet dependencies.
- **Live Smoke Test (`scripts/smoke_test_jolpica.py`)**: Standalone script to verify real connectivity with a single Grand Prix round.

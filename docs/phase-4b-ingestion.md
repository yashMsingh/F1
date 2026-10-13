# Phase 4B — Controlled Historical Dataset Expansion (2024 Rounds 6–10)

## 1. Executive Summary

**Status**: **COMPLETED & ACCEPTED**  
**Dataset Ingested**: 2024 Formula 1 Rounds 6 to 10 (Miami, Emilia Romagna / Imola, Monaco, Canada, Spain)  
**Database**: PostgreSQL 16 (port 5434)  
**Target Season Coverage**: 2024 Rounds 1–10 (10 Grand Prix events, 2 Sprint events)  

The F1 Race Intelligence platform has successfully expanded its historical dataset from the Phase 3F baseline (2024 Rounds 1–5) through 2024 Round 10. All mandatory pre-ingestion gates, deterministic source-fact verifications, idempotency checks, live API regression tests, and frontend build validations have passed with 100% fidelity.

---

## 2. Pre-Ingestion Blocking Gates

Before initiating ingestion, all four mandatory blocking gates were executed and verified:

| Gate | Verification Check | Expected Target | Observed Result | Status |
|---|---|---|---|---|
| **Gate 1: Container & Baseline** | Docker `f1_postgres` status and Phase 3F row counts | Container healthy on port 5434; 13 tables match baseline | Exact match across all 13 tables (99 race results, 4,959 laps, etc.) | **PASS** |
| **Gate 2: Version Control Exclusion** | Exclude `backups/` and `*.sql` from Git | `.gitignore` updated and verified via `git status` | `backups/` and `.sql` completely untracked | **PASS** |
| **Gate 3: Physical Database Backup** | Snapshot creation via `pg_dump` | Non-empty host file `backups/phase3f_baseline.sql` | Created: 364,177 bytes | **PASS** |
| **Gate 4: Restore Validation** | Dry-run restore into disposable DB | Disposable DB `f1_restore_validation` matches baseline | Exact match across all 13 tables; disposable DB dropped cleanly | **PASS** |

---

## 3. Ingestion Execution & Operational Telemetry

### Exact Command Executed:
```bash
python scripts/ingest_historical.py --season 2024 --start 6 --end 10 --pace-delay 0.25
```

### Operational Telemetry:
- **Batch Range**: 2024 Rounds 6 to 10 (Miami, Imola, Monaco, Canada, Spain)
- **Total Ingestion Processing**:
  - Processed: **6,863 records**
  - Inserted: **6,706 records**
  - Skipped: **157 records** (existing reference entities)
  - Updated: **0 records**
- **HTTP Request Volume**: 114 requests total ($50$ entity requests $+ 64$ paginated lap time requests)
- **Rate-Limit Resilience (Jolpica API)**:
  - During lap-time pagination for Round 10 (Spain), the Jolpica API returned intermittent `HTTP 429 Too Many Requests` due to sustained request frequency.
  - `JolpicaClient` automatically engaged exponential backoff (`0.5s` $\to$ `1.0s` $\to$ `2.0s`) and parsed retry parameters.
  - **100% of throttled requests succeeded on retry** with HTTP 200 OK without any fatal exceptions or dropped records.

---

## 4. Per-Round ETL Audit Outcomes

Audited directly from `etl_log` table:

| Round | Event Name | Circuit Slug | Status | Processed | Inserted | Skipped | Failed |
|---|---|---|---|---|---|---|---|
| **Round 6** | Miami Grand Prix | `miami` | **SUCCESS** | 1,262 | 1,231 | 31 | 0 |
| **Round 7** | Emilia Romagna Grand Prix | `imola` | **SUCCESS** | 1,370 | 1,338 | 32 | 0 |
| **Round 8** | Monaco Grand Prix | `monaco` | **SUCCESS** | 1,360 | 1,329 | 31 | 0 |
| **Round 9** | Canadian Grand Prix | `villeneuve` | **SUCCESS** | 1,414 | 1,383 | 31 | 0 |
| **Round 10** | Spanish Grand Prix | `catalunya` | **SUCCESS** | 1,457 | 1,425 | 32 | 0 |

---

## 5. Post-Ingestion Database Row Counts

### Deterministic Tables (Source-Derived Fixed Expectations)
| Table Name | Phase 3F Baseline | Phase 4B Post-Ingestion | Net Increase | Expected Target | Status |
|---|---|---|---|---|---|
| `seasons` | 1 | **1** | +0 | 1 (2024) | Exact Match |
| `circuits` | 5 | **10** | +5 | 10 (+5 new circuits) | Exact Match |
| `constructors` | 10 | **10** | +0 | 10 (no new teams) | Exact Match |
| `drivers` | 21 | **22** | +1 | 22 (Jack Doohan FP1 debut in Canada) | Verified Source |
| `races` | 5 | **10** | +5 | 10 | Exact Match |
| `race_results` | 99 | **199** | +100 | 199 (20 per round for R6–R10) | Exact Match |
| `qualifying_results` | 99 | **199** | +100 | 199 (20 per round for R6–R10) | Exact Match |
| `sprint_results` | 20 | **40** | +20 | 40 (Miami Round 6 Sprint) | Exact Match |
| `driver_standings` | 104 | **209** | +105 | 209 (21 drivers/round) | Exact Match |
| `constructor_standings` | 50 | **100** | +50 | 100 (10 teams/round) | Exact Match |

### Empirical / Telemetry Tables (Observed Source Ranges)
| Table Name | Phase 3F Baseline | Phase 4B Post-Ingestion | Net Increase | Expected Range | Status |
|---|---|---|---|---|---|
| `pit_stops` | 192 | **354** | +162 | 350–400 | Within Range |
| `lap_times` | 4,959 | **11,117** | +6,158 | 10,700 ± 500 | Within Range |
| `etl_log` | 7 | **12** | +5 | +5 successful runs | Exact Match |

---

## 6. Historical Fact & Source Verification

### Grand Prix Winners (Rounds 6–10):
- **Round 6 (Miami)**: **Lando Norris** (`norris`, McLaren) — P1, 25.00 pts (Maiden Formula 1 victory)
- **Round 7 (Imola)**: **Max Verstappen** (`max_verstappen`, Red Bull) — P1, 25.00 pts
- **Round 8 (Monaco)**: **Charles Leclerc** (`leclerc`, Ferrari) — P1, 25.00 pts (Maiden home victory)
- **Round 9 (Canada)**: **Max Verstappen** (`max_verstappen`, Red Bull) — P1, 25.00 pts
- **Round 10 (Spain)**: **Max Verstappen** (`max_verstappen`, Red Bull) — P1, 25.00 pts

### Miami Sprint Results Accounting (Round 6):
- **Sprint P1**: **Max Verstappen** (Red Bull) — 8.00 sprint points (Finished)
- **Sprint P2**: **Charles Leclerc** (Ferrari) — 7.00 sprint points (Finished)
- **Sprint P3**: **Sergio Pérez** (Red Bull) — 6.00 sprint points (Finished)
- **Sprint P4**: Daniel Ricciardo (RB) — 5.00 sprint points (Finished)
- **Sprint P5**: Carlos Sainz (Ferrari) — 4.00 sprint points (Finished)
- **Norris Sprint Classification**: **Retired** (`position_text = 'R'`), 0.00 sprint points.
- **Sprint vs. Grand Prix Point Segregation**:
  - Norris Grand Prix points: 25.00
  - Norris Sprint points: 0.00
  - Norris Combined Round 6 points: 25.00

### Max Verstappen Cumulative Points Verification:
- Grand Prix Race Points (R1–R10): **203.00**
- Sprint Points (R1–R10): **16.00** (8 China + 8 Miami)
- Combined Championship Points: **219.00**
- Standings after Round 10: Position 1, **219.00 points**, **7 wins** (Verified exact match against source standings).

---

## 7. Relational Integrity & Idempotency Audit

### Relational Integrity:
- **Natural-Key Uniqueness**: Audited across all tables (`race_results`, `qualifying_results`, `sprint_results`, `pit_stops`, `lap_times`, `driver_standings`, `constructor_standings`). Exactly **0 duplicate key groups**.
- **Foreign-Key Validity**: Audited across circuits, races, drivers, constructors, and telemetry children. Exactly **0 orphan records**.

### Idempotency Acceptance Test:
A full re-ingestion of 2024 Rounds 6–10 was executed against the populated database:
- **Command**: `python scripts/ingest_historical.py --season 2024 --start 6 --end 10 --pace-delay 0.25`
- **Result**:
  - Total records processed: **6,863**
  - Total records inserted: **0**
  - Total records skipped: **6,863**
  - Total records updated: **0**
- **Outcome**: **100% Idempotent** — Zero duplicates created; table row counts remained perfectly invariant.

---

## 8. Downstream Analytical, API & Frontend Regression Testing

1. **Longitudinal Integration Suite**:
   - `pytest tests/services/test_longitudinal_integration.py`
   - **8 passed in 9.30s (100% PASS)**
   - Verified driver trajectories, constructor aggregates, teammate head-to-head comparisons, Oliver Bearman single-race separation, evidence context building, and adversarial anti-hallucination rejections.
2. **FastAPI Application Endpoints**:
   - `GET /api/races?season=2024` $\to$ Returns 10 races (HTTP 200)
   - `GET /api/races/2024/{6..10}/results` $\to$ Returns valid 20-car classifications (HTTP 200)
   - `GET /api/races/2024/6/pit-stops` $\to$ Returns 20 driver pit-stop summaries (HTTP 200)
   - `GET /api/races/2024/6/laps` $\to$ Returns 20 driver lap summaries (HTTP 200)
   - `GET /api/races/2024/10/standings` $\to$ Returns P1 Max Verstappen with 219.00 points (HTTP 200)
   - `GET /api/season/2024/insights?up_to_round=10` $\to$ Evaluates 33 deterministic longitudinal insights (HTTP 200)
   - `POST /api/narrative` (scope="race", Round 6 Miami) $\to$ Generates grounded AI narrative celebrating Lando Norris's maiden win (HTTP 200)
   - `POST /api/narrative` (scope="longitudinal", Verstappen up to Round 10) $\to$ Generates grounded narrative over 10 rounds (HTTP 200)
3. **Frontend Production Build**:
   - `npm run build` in `frontend/`
   - TypeScript compilation and Vite bundling completed in 39.56s with **0 errors**.

---

## 9. Conclusion & Baseline Status

The F1 Race Intelligence platform historical dataset is now formally certified through **2024 Round 10**.

- Phase 3F baseline preserved and cleanly expanded.
- Grounded AI and deterministic analytics validated against 10 continuous championship rounds.
- Full backup safely preserved in `backups/phase3f_baseline.sql` (git-ignored).

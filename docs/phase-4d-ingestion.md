# Phase 4D.1 — Historical Dataset Ingestion Report (2024 Rounds 11–15)

**Phase**: 4D.1 — Controlled Historical Ingestion  
**Execution Date**: 2026-11-01  
**Database Host/Target**: `localhost:5432/f1_race_intelligence` (PostgreSQL 16.15)  
**Ingestion Status**: **SUCCESS (All 5 rounds ingested, audited, and idempotency-verified)**

---

## 1. Ingestion Scope & Source

- **Championship Season**: 2024 Formula 1 World Championship
- **Target Rounds**:
  - **Round 11**: Austrian Grand Prix (`red_bull_ring`, Spielberg) — *Sprint Weekend*
  - **Round 12**: British Grand Prix (`silverstone`, Silverstone Circuit)
  - **Round 13**: Hungarian Grand Prix (`hungaroring`, Hungaroring)
  - **Round 14**: Belgian Grand Prix (`spa`, Circuit de Spa-Francorchamps)
  - **Round 15**: Dutch Grand Prix (`zandvoort`, Circuit Park Zandvoort)
- **Data Source**: Jolpica F1 API (Ergast-compatible REST API at `https://api.jolpi.ca/ergast/f1/`)
- **Ingestion Runner**: `scripts/ingest_historical.py` via `app.etl.runners.season_slice.ingest_season_slice`

---

## 2. Ingestion Execution & Pacing

### 2.1 Execution Command
```bash
python scripts/ingest_historical.py --season 2024 --start 11 --end 15 --pace-delay 0.35
```

### 2.2 Per-Round Ingestion Results (First Pass)

| Round | Grand Prix | Status | Records Processed | Records Inserted | Records Skipped | Records Updated | Execution Duration |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **11** | Austrian Grand Prix | **SUCCESS** | 1,574 | 1,543 | 31 | 0 | ~1m 06s |
| **12** | British Grand Prix | **SUCCESS** | 1,112 | 1,079 | 33 | 0 | ~47s |
| **13** | Hungarian Grand Prix | **SUCCESS** | 1,500 | 1,468 | 32 | 0 | ~1m 04s |
| **14** | Belgian Grand Prix | **SUCCESS** | 979 | 948 | 31 | 0 | ~41s |
| **15** | Dutch Grand Prix | **SUCCESS** | 1,556 | 1,525 | 31 | 0 | ~1m 07s |
| **Total** | **Rounds 11–15** | **SUCCESS** | **6,721** | **6,563** | **158** | **0** | **~4m 45s** |

*Note on Skipped Records*: In each round, existing season (2024) and constructor records (10 teams) are recognized as existing entities and skipped idempotently.

---

## 3. Database Row Counts: Pre-Ingestion vs. Post-Ingestion

Exact row counts were audited via SQL `SELECT COUNT(*)` on the active PostgreSQL database before and after execution:

| Table Name | Pre-Ingestion Baseline (R1–10) | Phase 4D Planning Projection | Actual Post-Ingestion Count | Net Records Added | Status vs Projection |
|---|:---:|:---:|:---:|:---:|:---:|
| `seasons` | 1 | 1 | **1** | +0 | **EXACT MATCH** |
| `circuits` | 10 | 15 | **15** | +5 | **EXACT MATCH** |
| `constructors` | 10 | 10 | **10** | +0 | **EXACT MATCH** |
| `drivers` | 22 | 23 | **23** | +1 | **EXACT MATCH** |
| `races` | 10 | 15 | **15** | +5 | **EXACT MATCH** |
| `race_results` | 199 | 299 | **299** | +100 | **EXACT MATCH** |
| `qualifying_results` | 199 | 299 | **299** | +100 | **EXACT MATCH** |
| `sprint_results` | 40 | 60 | **60** | +20 | **EXACT MATCH** |
| `pit_stops` | 354 | 544 | **544** | +190 | **EXACT MATCH** |
| `lap_times` | 11,117 | 17,104 | **17,104** | +5,987 | **EXACT MATCH** |
| `driver_standings` | 209 | 314 | **314** | +105 | **EXACT MATCH** |
| `constructor_standings` | 100 | 150 | **150** | +50 | **EXACT MATCH** |
| `etl_log` | 10 | 15 | **15** | +5 | **EXACT MATCH** |

*Result*: 100% agreement across all 13 core tables with zero discrepancy against planning estimates.

---

## 4. Special Historical Edge Case Audits

Direct SQL queries independently verified each of the four designated edge cases:

### 4.1 Austria (Round 11) — Sprint Disaggregation & Verstappen/Russell Distinction
- **Sprint Result**: Max Verstappen won the Sprint (`position_text='1'`, `points=8.00`, `status='Finished'`).
- **Grand Prix Winner**: George Russell won the Grand Prix (`position_text='1'`, `points=25.00`, `status='Finished'`).
- **Verstappen Grand Prix Result**: Following a Lap 64 collision with Lando Norris, Verstappen finished P5 (`position_text='5'`, `points=10.00`, `status='Finished'`).
- **Finding**: Sprint results are stored in `sprint_results` and GP results in `race_results`. Verstappen's Sprint victory is cleanly isolated from his GP P5 finish.

### 4.2 Britain (Round 12) — Franco Colapinto FP1 Appearance Integrity
- **Drivers Table**: Franco Colapinto was added as driver entity `id=51`, `driver_id='colapinto'`, `code='COL'`.
- **Race Results**: `0` records.
- **Qualifying Results**: `0` records.
- **Driver Standings**: `0` records.
- **Finding**: Colapinto exists solely as a reference entity; he is not recorded as a race starter, qualifier, or championship point scorer.

### 4.3 Belgium (Round 14) — George Russell Post-Race Disqualification (DSQ)
- **Official GP Winner**: Lewis Hamilton (`position_text='1'`, `points=25.00`, `status='Finished'`).
- **Russell Classification**: `source_position=20`, `position_text='20'`, `points=0.00`, `status='Disqualified'`.
- **Finding**: Russell's disqualification (underweight car) is accurately recorded. He received 0 points and does not appear as a classified podium finisher.

### 4.4 Netherlands (Round 15) — Logan Sargeant Missing Qualifying & Race Participation
- **Qualifying**: Logan Sargeant crashed in FP3 and did not set a lap time. In `qualifying_results`, he is recorded with `position=20`, `q1_time=NULL`, `q1_time_millis=NULL`, `q2_time=NULL`, `q3_time=NULL`.
- **Grand Prix**: Sargeant started the race from `grid_position=18` and finished `source_position=16`, `position_text='16'`, `status='Lapped'`, `points=0.00`.
- **Finding**: Missing qualifying times are correctly represented as `NULL` while preserving his valid Grand Prix participation.

---

## 5. Data Integrity Audit

Direct relational queries confirmed the following integrity invariants:
- **Foreign Key Orphans**:
  - `race_results` without valid `races`, `drivers`, or `constructors`: **0**
  - `qualifying_results` without valid parent FKs: **0**
  - `sprint_results` without valid parent FKs: **0**
  - `pit_stops` without valid parent FKs: **0**
  - `lap_times` without valid parent FKs: **0**
- **Natural Key Uniqueness**:
  - Duplicate `(season_year, round)` in `races`: **0**
  - Duplicate `(race_id, driver_id)` in `race_results`: **0**
  - Duplicate `(race_id, driver_id)` in `qualifying_results`: **0**
  - Duplicate `(race_id, driver_id)` in `sprint_results`: **0**
- **Sprint Exclusivity**:
  - Sprint results for non-sprint rounds (R1–R4, R7–R10, R12–R15): **0** (strictly present only for R5 China, R6 Miami, and R11 Austria).

---

## 6. Historical Preservation of Rounds 1–10

A round-by-round programmatic audit compared the pre-ingestion snapshot in `scratch/pre_ingestion_baseline.json` against the live PostgreSQL state across all 10 historical rounds:

| Round | Event Name | Race Results Match | Quali Match | Sprint Match | Pit Stops Match | Lap Times Match | Standings Match |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | Bahrain Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |
| **2** | Saudi Arabian Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |
| **3** | Australian Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |
| **4** | Japanese Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |
| **5** | Chinese Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |
| **6** | Miami Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |
| **7** | Emilia Romagna Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |
| **8** | Monaco Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |
| **9** | Canadian Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |
| **10** | Spanish Grand Prix | 100% | 100% | 100% | 100% | 100% | 100% |

*Result*: **100% identical**. Not a single row, value, or timestamp in Rounds 1–10 was mutated.

---

## 7. Idempotency Verification

A second complete execution of the exact same command was run immediately following the first pass:
```bash
python scripts/ingest_historical.py --season 2024 --start 11 --end 15 --pace-delay 0.35
```

### Second Pass Summary
```text
  Round 11: Status=SUCCESS Processed=1574  Inserted=0  Skipped=1574  Updated=0
  Round 12: Status=SUCCESS Processed=1112  Inserted=0  Skipped=1112  Updated=0
  Round 13: Status=SUCCESS Processed=1500  Inserted=0  Skipped=1500  Updated=0
  Round 14: Status=SUCCESS Processed=979   Inserted=0  Skipped=979   Updated=0
  Round 15: Status=SUCCESS Processed=1556  Inserted=0  Skipped=1556  Updated=0

Totals: Processed=6,721, Inserted=0, Skipped=6,721 (100%), Updated=0
```

- **Inserted**: `0`
- **Updated**: `0`
- **Skipped**: `6,721` (100% of processed records)
- **Database Row Counts**: 100% identical before and after second pass.

---

## 8. Known Limitations & Next Steps

1. **Unbounded `up_to_round=None` in Ten-Round Tests**:
   - In `tests/analytics/test_longitudinal_ten_rounds.py`, two assertions test default parameter behavior (`get_driver_season_aggregate(..., up_to_round=None)` and `get_constructor_season_aggregate(..., up_to_round=None)`).
   - Because the database now contains 15 rounds, the unbounded query returns 15-round totals (Verstappen 15 starts, Red Bull 434 pts) rather than 10-round totals.
   - Per the Phase 4D roadmap, explicit 15-round regression tests and parameterization updates are scheduled for **Phase 4D.3**, following the independent SQL calculations in Phase 4D.2.
2. **Current Readiness**:
   - Ingestion is fully complete and audited.
   - The dataset is ready for Phase 4D.2 (Independent SQL reference calculations).

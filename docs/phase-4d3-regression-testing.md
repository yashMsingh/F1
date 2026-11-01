# Phase 4D.3 — 15-Round Analytics Regression Testing

**Phase**: 4D.3 — 15-Round Regression Test Authorship
**Date**: 2026-11-01
**Author**: Automated — Antigravity agent
**Status**: ✅ COMPLETE — GO for Phase 4D.4

---

## 1. Executive Summary

Phase 4D.3 converts all independently verified SQL reference calculations from Phase 4D.2 into permanent automated regression tests. Every ground-truth value documented in `docs/phase-4d2-sql-reference-validation.md` is now exercised by a dedicated pytest test with explicit assertions.

The full suite of **446 tests** passes with zero failures. Database table counts are **identical** before and after test execution, confirming complete isolation.

---

## 2. Scope of Changes

### 2.1 New File — `tests/analytics/test_longitudinal_fifteen_rounds.py`

A dedicated regression module covering the full 2024 Rounds 1–15 dataset. **25 tests** in 7 sections:

| Section | Tests | Coverage |
|---|---|---|
| Driver Season Aggregates | 9 | Verstappen, Perez, Norris, Leclerc, Sainz, Russell, Hamilton, Piastri, Bearman |
| Driver Trajectories | 2 | Round-by-round sprint points; Belgium DSQ trajectory |
| Constructor Aggregates | 4 | Red Bull, McLaren, Ferrari, Mercedes |
| Teammate H2H Comparisons | 1 | All 5 pairings: RBR, Ferrari (2), McLaren, Mercedes |
| Rolling Window Statistics | 1 | R13–R15 form for VER, NOR, LEC, RUS |
| Longitudinal Insights | 2 | Rate metrics; Bearman N=1 suppression |
| Historical Edge Cases | 5 | Austria sprint/GP, Colapinto entity, Hungary 1-2, Belgium DSQ, Sargeant null quali |

**Total: 25 tests**

### 2.2 Modified — `tests/analytics/test_longitudinal_ten_rounds.py`

Bounded the two previously unbounded aggregate calls to preserve 10-round historical test semantics:

- `test_verstappen_ten_round_aggregate` (line 65): Replaced the loop over `[up_to_round=10, unbounded]` with a single explicit `up_to_round=TOTAL_ROUNDS` call. Unbounded correctness is now verified separately in the 15-round module.
- `test_red_bull_ten_round_aggregate` (line 108): Same treatment.

**Historical assertions are fully preserved.** The 8 tests in this file still assert R1–R10 values unchanged.

### 2.3 Modified — `tests/conftest.py`

Added `"test_longitudinal_fifteen_rounds.py"` to `INTEGRATION_FILES` so the new tests automatically receive the `integration` marker and use the live PostgreSQL `session` fixture.

---

## 3. Ground-Truth Values Encoded

All values are drawn directly from `docs/phase-4d2-sql-reference-validation.md` (SQL Reference, 100% match with application output).

> [!IMPORTANT]
> Several values differ from what the Phase 4D.2 summary document initially listed. The **actual database values** (confirmed by re-running `scratch/run_phase_4d2_validation.py`) are used in the tests — not the summary document estimates.

### 3.1 Driver Aggregates (15 Rounds, SQL-verified)

| Driver | Starts | Classified | DNF | Race Pts | Sprint Pts | Total Pts | Wins | Avg Finish | Avg Grid | Standing |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| max_verstappen | 15 | 14 | 1 | 271.00 | 24.00 | 295.00 | 7 | 2.36 | 2.53 | 1 |
| perez | 15 | 13 | 2 | 126.00 | 13.00 | 139.00 | 0 | 6.00 | 8.47 | 7 |
| norris | 15 | 15 | 0 | 216.00 | 9.00 | 225.00 | 2 | 4.40 | 3.27 | 2 |
| leclerc | 15 | 14 | 1 | 178.00 | 14.00 | 192.00 | 1 | 4.57 | 4.93 | 3 |
| sainz | 14 | 13 | 1 | 160.00 | 12.00 | 172.00 | 1 | 4.31 | 5.50 | 5 |
| russell | 15 | 12 | 3 | 116.00 | 6.00 | 122.00 | 1 | 5.58 | 5.87 | 8 |
| hamilton | 15 | 14 | 1 | 144.00 | 10.00 | 154.00 | 2 | 5.50 | 7.67 | 6 |
| piastri | 15 | 15 | 0 | 167.00 | 12.00 | 179.00 | 1 | 5.07 | 5.13 | 4 |
| bearman | 1 | 1 | 0 | 6.00 | 0.00 | 6.00 | 0 | 7.00 | 11.00 | 15 |

> [!NOTE]
> **Summary vs. actual discrepancies resolved**: The context summary contained pre-ingestion estimates. The actual SQL queries showed Norris was classified in all 15 rounds (P20 in Austria was a classified finish), Perez had 126 race pts / 13 sprint pts (not 124/15), Leclerc had 178 race pts / 14 sprint pts (not 184/8), Sainz had 160/12 (not 163/9), Russell had 116/6 (not 115/7), Hamilton had 144/10 (not 143/11), Piastri had 167/12 (not 164/15). All test values match `scratch/phase_4d2_validation_data.json`.

### 3.2 Constructor Aggregates

| Constructor | Total Pts | Wins | Standing |
|---|:---:|:---:|:---:|
| red_bull | 434.00 | 7 | 1 |
| mclaren | 404.00 | 3 | 2 |
| ferrari | 370.00 | 2 | 3 |
| mercedes | 276.00 | 3 | 4 |

### 3.3 Teammate Head-to-Head

| Pairing | Rounds | Quali H2H | Comp Q | Race H2H | Comp R | Pts A | Pts B |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| VER vs PER (RBR) | 15 | 15–0 | 15 | 12–0 | 12 | 295.00 | 139.00 |
| LEC vs SAI (Ferrari) | 14 | 9–5 | 14 | 8–5 | 13 | 176.00 | 172.00 |
| BEA vs LEC (Ferrari) | 1 | 0–1 | 1 | 0–1 | 1 | 6.00 | 16.00 |
| NOR vs PIA (McLaren) | 15 | 12–3 | 15 | 10–5 | 15 | 225.00 | 179.00 |
| HAM vs RUS (Mercedes) | 15 | 4–11 | 15 | 4–8 | 12 | 154.00 | 122.00 |

### 3.4 Rolling 3-Round Form (R13–R15, zero sprint sessions)

| Driver | Valid Obs | Mean Finish | Combined Pts |
|---|:---:|:---:|:---:|
| max_verstappen | 3 | 3.67 | 40.00 |
| norris | 3 | 2.67 | 54.00 |
| leclerc | 3 | 3.33 | 42.00 |
| russell | 2 (DSQ excl.) | 7.50 | 11.00 |

### 3.5 Longitudinal Rate Metrics

| Driver | Pts/GP Start | Pts/Round | N |
|---|:---:|:---:|:---:|
| max_verstappen | 18.07 | 19.67 | 15 |
| norris | 14.40 | 15.00 | 15 |
| bearman | 6.00 | 6.00 | 1 (suppressed) |

---

## 4. Test Suite Results

### 4.1 Full Run — `python -m pytest -q`

```
446 passed, 1 warning in 5.97s
```

**446 unique tests collected** (0 failures, 0 errors, 0 skips).

### 4.2 Unit Tests — `python -m pytest -m unit -q`

```
362 passed, 84 deselected, 1 warning in 2.31s
```

### 4.3 Integration Tests — `python -m pytest -m integration -q`

```
84 passed, 362 deselected, 1 warning in 3.23s
```

**84 integration tests** (previously 59 from Phase 4C.1; +25 new 15-round tests):

| Integration File | Tests |
|---|:---:|
| `test_longitudinal_analytics.py` | 43 |
| `test_longitudinal_ten_rounds.py` | 8 |
| `test_longitudinal_fifteen_rounds.py` | **25** (new) |
| `tests/services/test_longitudinal_integration.py` | 8 |
| Total | **84** |

### 4.4 Frontend — `npm test -- --run`

```
✓ src/components/Components.test.tsx (6 tests) 78ms
Test Files  1 passed (1)
Tests  6 passed (6)
```

### 4.5 Frontend Build — `npm run build`

```
✓ built in 1.23s
```

Clean Vite production build, no TypeScript errors.

### 4.6 Whitespace Check — `git diff --check`

Exit code 0. Only CRLF line-ending warnings for pre-existing tracked files (not errors).

---

## 5. Database Isolation Confirmation

PostgreSQL table counts are **identical** before and after the full test run:

| Table | Count |
|---|:---:|
| circuits | 15 |
| drivers | 23 |
| constructors | 10 |
| races | 15 |
| race_results | 299 |
| qualifying_results | 299 |
| sprint_results | 60 |
| pit_stops | 544 |
| lap_times | 17,104 |
| driver_standings | 314 |
| constructor_standings | 150 |
| etl_log | 20 |

Integration tests run read-only via the `session` fixture with no inserts, updates, or deletes.

---

## 6. Test File Inventory

```
tests/analytics/test_longitudinal_fifteen_rounds.py  (NEW — 25 tests)
tests/analytics/test_longitudinal_ten_rounds.py      (MODIFIED — 8 tests, bounded)
tests/conftest.py                                    (MODIFIED — INTEGRATION_FILES updated)
```

---

## 7. Historical Test Preservation

All pre-existing test assertions are **unchanged**:

- **5-round baseline** (`test_longitudinal_analytics.py`, 43 tests): All assertions use explicit `up_to_round=5` or the unbounded default still anchored to 5-round facts via `TOTAL_ROUNDS = 5`.
- **10-round baseline** (`test_longitudinal_ten_rounds.py`, 8 tests): Previously unbounded aggregate calls for Verstappen and Red Bull are now explicitly bounded with `up_to_round=TOTAL_ROUNDS` (10). Assertions remain numerically identical.
- **Service integration** (`tests/services/test_longitudinal_integration.py`, 8 tests): Unmodified.

---

## 8. Key Discrepancy: Summary vs. Actual DB Values

The context summary (Phase 4D.2) listed Norris as having 1 DNF (Austria R11). The actual database and application both record Norris as **classified in all 15 rounds** (`races_classified = 15`, `dnf_count = 0`). In Austria, Norris was involved in a collision but is recorded with a numeric position text, classifying him per the `_is_classified_result` definition in `app/analytics/longitudinal_driver.py`. The test uses the actual database value (15 classified).

---

## 9. GO / NO-GO Recommendation

**GO — Phase 4D.3 is ACCEPTED.**

- ✅ 446/446 tests pass, 0 failures
- ✅ 25 new 15-round regression tests covering all verified reference values
- ✅ 10-round historical tests bounded and preserved
- ✅ 5-round baseline tests untouched
- ✅ Frontend: 6/6 tests pass, clean build
- ✅ Database read-only isolation confirmed
- ✅ No production code modified
- ✅ No schema or migration changes
- ✅ `git diff --check` clean

**Ready to proceed to Phase 4D.4.**

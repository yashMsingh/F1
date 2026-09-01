# F1 Race Intelligence — Data Dictionary

> Last updated: 2026-09-01
> Status: Initial draft — based on verified Jolpica API fields

This document defines the meaning, source, type, and edge cases of every key data field used in the platform.

---

## 1. Core Entity Fields

### Driver Fields

| Field | DB Column | Type | Source | Description | Edge Cases |
|-------|-----------|------|--------|-------------|------------|
| Driver ID | `driver_id` | VARCHAR(100) | Jolpica `driverId` | Unique API slug (e.g., `norris`, `max_verstappen`) | Stable across seasons |
| Permanent Number | `permanent_number` | INTEGER | Jolpica `permanentNumber` | Car number chosen by driver | NULL for pre-2014 drivers; may differ from `number` in results |
| Code | `code` | VARCHAR(3) | Jolpica `code` | Three-letter abbreviation (e.g., `NOR`) | NULL for some historical drivers |
| Given Name | `given_name` | VARCHAR(255) | Jolpica `givenName` | First name | — |
| Family Name | `family_name` | VARCHAR(255) | Jolpica `familyName` | Last name | — |
| Date of Birth | `date_of_birth` | DATE | Jolpica `dateOfBirth` | ISO-8601 date | NULL for very old historical drivers |
| Nationality | `nationality` | VARCHAR(100) | Jolpica `nationality` | Full nationality string (e.g., `British`) | — |

### Constructor Fields

| Field | DB Column | Type | Source | Description | Edge Cases |
|-------|-----------|------|--------|-------------|------------|
| Constructor ID | `constructor_id` | VARCHAR(100) | Jolpica `constructorId` | Unique API slug (e.g., `mclaren`, `red_bull`) | Name changes over time (e.g., `rb` for Racing Bulls) |
| Name | `name` | VARCHAR(255) | Jolpica `name` | Display name | Changes historically (e.g., Toro Rosso → AlphaTauri → RB) |
| Nationality | `nationality` | VARCHAR(100) | Jolpica `nationality` | Team nationality | — |

### Circuit Fields

| Field | DB Column | Type | Source | Description | Edge Cases |
|-------|-----------|------|--------|-------------|------------|
| Circuit ID | `circuit_id` | VARCHAR(100) | Jolpica `circuitId` | Unique slug (e.g., `albert_park`) | Stable across seasons |
| Circuit Name | `circuit_name` | VARCHAR(255) | Jolpica `circuitName` | Full name | May change (e.g., sponsor in name) |
| Locality | `locality` | VARCHAR(255) | Jolpica `Location.locality` | City/town | — |
| Country | `country` | VARCHAR(255) | Jolpica `Location.country` | Country name | — |
| Latitude | `latitude` | DECIMAL(10,6) | Jolpica `Location.lat` | GPS latitude | Returned as string; parse to float |
| Longitude | `longitude` | DECIMAL(10,6) | Jolpica `Location.long` | GPS longitude | Returned as string; parse to float |

### Race Fields

| Field | DB Column | Type | Source | Description | Edge Cases |
|-------|-----------|------|--------|-------------|------------|
| Season | `season_year` | INTEGER | Jolpica `season` | Championship year | — |
| Round | `round` | INTEGER | Jolpica `round` | Round number within season | Starts at 1 |
| Race Name | `race_name` | VARCHAR(255) | Jolpica `raceName` | Grand Prix name | May change year-to-year |
| Race Date | `race_date` | DATE | Jolpica `date` | ISO-8601 date | — |
| Race Time | `race_time` | TIME | Jolpica `time` | UTC start time | May be NULL for historical races |

---

## 2. Result Fields

### Race Result Fields

| Field | DB Column | Type | Source | Description | Edge Cases |
|-------|-----------|------|--------|-------------|------------|
| Car Number | `car_number` | INTEGER | Jolpica `number` | Car number used in race | Returned as string; parse to int |
| Grid Position | `grid_position` | INTEGER | Jolpica `grid` | Starting position | NULL or `0` for pit-lane starts, DNS |
| Finishing Position | `finishing_position` | INTEGER | Jolpica `position` | Classified finishing order | Not always meaningful for retired drivers |
| Position Text | `position_text` | VARCHAR(10) | Jolpica `positionText` | API-provided position string | `"R"` = Retired, `"D"` = Disqualified, `"E"` = Excluded, `"W"` = Withdrawn, `"F"` = Failed to qualify, `"N"` = Not classified |
| Points | `points` | DECIMAL(5,2) | Jolpica `points` | Points awarded | Returned as string; can be `0.0` for non-scorers; half-points possible (2021 Belgium) |
| Laps Completed | `laps_completed` | INTEGER | Jolpica `laps` | Number of laps completed | `0` for DNS or immediate retirement |
| Status | `status` | VARCHAR(100) | Jolpica `status` | Race outcome | `"Finished"`, `"Retired"`, `"+1 Lap"`, `"+2 Laps"`, `"Collision"`, `"Engine"`, etc. |
| Finish Time (ms) | `time_millis` | BIGINT | Jolpica `Time.millis` | Finish time in milliseconds | Winner: absolute race time; Others: may be gap or NULL |
| Finish Time (text) | `time_text` | VARCHAR(50) | Jolpica `Time.time` | Formatted time string | Winner: `"1:42:06.304"`; Others: `"+0.895"` |
| Fastest Lap Rank | `fastest_lap_rank` | INTEGER | Jolpica `FastestLap.rank` | Ranking of fastest lap among all drivers | NULL if no fastest lap recorded (e.g., DNS, lap-0 retirement) |
| Fastest Lap Number | `fastest_lap_number` | INTEGER | Jolpica `FastestLap.lap` | Lap on which fastest time was set | NULL if no fastest lap |
| Fastest Lap Time | `fastest_lap_time` | VARCHAR(20) | Jolpica `FastestLap.Time.time` | Fastest lap time string | NULL if no fastest lap |

### Qualifying Result Fields

| Field | DB Column | Type | Source | Description | Edge Cases |
|-------|-----------|------|--------|-------------|------------|
| Position | `position` | INTEGER | Jolpica `position` | Qualifying position | — |
| Q1 Time | `q1_time` | VARCHAR(20) | Jolpica `Q1` | Q1 lap time | Empty string `""` if no time set (e.g., 107% rule, mechanical issue) |
| Q2 Time | `q2_time` | VARCHAR(20) | Jolpica `Q2` | Q2 lap time | NULL if driver eliminated in Q1 |
| Q3 Time | `q3_time` | VARCHAR(20) | Jolpica `Q3` | Q3 lap time | NULL if eliminated before Q3 |

### Pit Stop Fields

| Field | DB Column | Type | Source | Description | Edge Cases |
|-------|-----------|------|--------|-------------|------------|
| Stop Number | `stop_number` | INTEGER | Jolpica `stop` | Sequential stop number for this driver | Starts at 1 |
| Lap | `lap` | INTEGER | Jolpica `lap` | Lap on which pit stop occurred | — |
| Time of Day | `time_of_day` | VARCHAR(20) | Jolpica `time` | Time of day (local) | Format: `"HH:MM:SS"` |
| Duration | `duration_seconds` | DECIMAL(10,3) | Jolpica `duration` | Total pit stop duration in seconds | Includes pit-lane time; returned as string (e.g., `"13.341"`); RED FLAG pit stops will have anomalously long durations |

### Lap Time Fields

| Field | DB Column | Type | Source | Description | Edge Cases |
|-------|-----------|------|--------|-------------|------------|
| Lap Number | `lap_number` | INTEGER | Jolpica `number` | Lap number | Starts at 1 |
| Position | `position` | INTEGER | Jolpica `Timings[].position` | Driver's position at end of this lap | — |
| Lap Time | `time` | VARCHAR(20) | Jolpica `Timings[].time` | Lap time string | Format: `"M:SS.sss"` or `"SS.sss"`; Lap 1 includes formation/standing start time; in/out laps around pit stops are slower |
| Lap Time (ms) | `time_millis` | INTEGER | Derived | Parsed lap time in milliseconds | Computed in ETL from time string |

### Standings Fields

| Field | DB Column | Type | Source | Description | Edge Cases |
|-------|-----------|------|--------|-------------|------------|
| Position | `position` | INTEGER | Jolpica `position` | Championship position | — |
| Points | `points` | DECIMAL(7,2) | Jolpica `points` | Total championship points | Returned as string |
| Wins | `wins` | INTEGER | Jolpica `wins` | Total race wins in season | — |

---

## 3. Derived / Computed Fields

These fields do NOT exist in the source API. They are computed by the analytics engine.

| Metric | Formula | Dependencies | Edge Cases | Notes |
|--------|---------|-------------|------------|-------|
| Positions Gained/Lost | `grid_position - finishing_position` | `grid_position`, `finishing_position` | Both must be non-NULL and > 0; exclude DNS, DNF, DSQ; pit-lane starts (grid=0 or NULL) must be handled separately | Positive = positions gained; Negative = positions lost |
| DNF Flag | `status NOT IN ('Finished', '+1 Lap', '+2 Laps', ...)` | `status` | Need to enumerate all valid "classified" statuses; lapped drivers are classified, not DNF | Boolean derived field |
| Points Per Race | `total_points / races_started` | Aggregated from race_results | Define "races started" (exclude DNS? include DNF?) | Must document denominator |
| Average Finishing Position | `AVG(finishing_position)` | `finishing_position` | Exclude NULL (DNF/DNS/DSQ); state this clearly | Can be misleading if many DNFs |
| Average Qualifying Position | `AVG(position)` | qualifying_results.`position` | Some historical races may lack qualifying data | — |
| DNF Rate | `COUNT(DNFs) / COUNT(races_started)` | Derived from `status` | Define what constitutes DNF vs classified finish | Percentage |
| Teammate Delta | Driver's metric minus teammate's metric for same race/constructor | Multiple fields | Mid-season driver swaps; shared constructors | Requires identifying teammates per race |
| Pit Stop Efficiency | `duration_seconds` relative to season/race average | `duration_seconds` | Exclude red-flag stops; anomalous durations | Z-score or percentile |

---

## 4. Time String Parsing Rules

The Jolpica API returns all times as strings. The ETL must parse them consistently.

### Lap Time Format
- Pattern: `M:SS.sss` (e.g., `"1:22.167"`) or `SS.sss` (e.g., `"59.123"`)
- Parse to milliseconds: `minutes * 60000 + seconds * 1000 + millis`
- Example: `"1:22.167"` → `(1 * 60000) + (22 * 1000) + 167 = 82167 ms`

### Race Time Format
- Winner: `"H:MM:SS.sss"` (e.g., `"1:42:06.304"`)
- Others: `"+S.sss"` or `"+M:SS.sss"` (gap to winner)
- `millis` field (BIGINT) is the canonical numeric value when available

### Pit Stop Duration
- Pattern: `"SS.sss"` (e.g., `"13.341"`)
- Parse directly to DECIMAL

### Qualifying Times
- Same format as lap times: `"M:SS.sss"`
- Empty string `""` means no time was set

---

## 5. Status Values Observed

From verified API responses, the following `status` values have been observed:

| Status | Meaning | Classified? |
|--------|---------|------------|
| `Finished` | Completed all laps | Yes |
| `+1 Lap` | Finished 1 lap behind leader | Yes |
| `+2 Laps` | Finished 2 laps behind leader | Yes |
| `Retired` | Did not finish (generic) | No |
| `Collision` | Retired due to collision | No |
| `Engine` | Retired due to engine failure | No |
| `Gearbox` | Retired due to gearbox failure | No |
| `Hydraulics` | Retired due to hydraulic failure | No |
| `Brakes` | Retired due to brake failure | No |
| `Suspension` | Retired due to suspension failure | No |
| `Accident` | Retired due to accident | No |
| `Spun off` | Retired after spinning off | No |
| `Disqualified` | Disqualified from results | No |

> **Note**: This is not exhaustive. Historical data contains dozens of different status values. The ETL should treat any status not matching a known "classified" pattern as a DNF.

---

## 6. Known Data Gaps

| Gap | Impact | Mitigation |
|-----|--------|-----------|
| No tyre compound data in Jolpica | Cannot analyze tyre strategy from API alone | Add FastF1 in Phase 2 |
| No sector times in Jolpica | Cannot analyze sector-level performance | Add FastF1 in Phase 2 |
| No weather data in Jolpica | Cannot correlate weather with performance | Add FastF1 in Phase 2 |
| No practice session data | Cannot track Friday-to-Sunday performance evolution | Consider FastF1 or accept as limitation |
| Empty Q1 time for some drivers | Cannot compute qualifying lap times | Store as NULL; note in analytics |
| Sprint qualifying data unverified | Uncertain field structure | Test endpoint before ingesting |
| Variable historical data quality | Older seasons may have fewer fields | Validate per-season; document gaps |
| `positionText` not standardized | Different codes for different retirement reasons | Map to canonical categories in ETL |

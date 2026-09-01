# F1 Race Intelligence - Phase 2 Schema Review

> Status: Pre-implementation design gate
> Date: 2026-09-01
> Scope: Documentation-only review before PostgreSQL, SQLAlchemy, Alembic, or ingestion implementation

## 1. Executive Summary

The proposed Jolpica-first Phase 1 schema is directionally correct and should remain centered on the current entities:

- `seasons`
- `circuits`
- `constructors`
- `drivers`
- `races`
- `race_results`
- `qualifying_results`
- `sprint_results`
- `pit_stops`
- `lap_times`
- `driver_standings`
- `constructor_standings`
- `etl_log`

The schema is not ready for implementation until a few analytical-contract issues are corrected. The largest issue is classification semantics: Jolpica can provide a numeric source `position` even for retired drivers, so the database must not overwrite every DNF/DNS/DSQ source position with `NULL`. The source-provided classification fields should be preserved, and analytical eligibility should be derived separately.

The second major issue is time preservation. Jolpica pit-stop `duration` values can be simple seconds, such as `20.647`, or minute-based durations, such as the verified red-flag case `40:55.302`. The schema must preserve raw time strings and store parsed numeric values in explicit units.

The third issue is scope control. Jolpica supports race metadata, classifications, qualifying, sprint results where present, pit stops, lap timing, and standings. It does not by itself provide tyre compounds, tyre temperatures, detailed weather streams, safety-car periods, sector telemetry, or high-frequency car telemetry. Phase 1 analytics must not make unsupported claims from unavailable fields.

## 2. Source-to-Database Mapping

### 2.1 Jolpica Response Envelope

All Jolpica responses use a top-level `MRData` envelope with query metadata:

| Source Field | Target | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `MRData.url` | provenance or `etl_log.source_url` | text | yes | Store retrieval URL when useful | yes | no |
| `MRData.limit` | ingestion metadata | integer | yes | Parse string integer | optional | yes |
| `MRData.offset` | ingestion metadata | integer | yes | Parse string integer | optional | yes |
| `MRData.total` | ingestion metadata | integer | yes | Parse string integer | optional | yes |

Endpoint limitations: pagination is required for high-volume endpoints, especially lap times and pit stops. Numeric values are represented as strings and must be parsed explicitly.

### 2.2 Seasons and Races

Source endpoints:

- `/{season}.json`
- `/{season}/{round}/results.json`
- `/{season}/{round}/qualifying.json`
- `/{season}/{round}/sprint.json`
- `/{season}/{round}/pitstops.json`
- `/{season}/{round}/laps.json`

| Source Field | Target Field | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `season` | `seasons.season_year`, `races.season_year` | integer | no | Parse string integer | no | yes |
| `round` | `races.round` | integer | no | Parse string integer | no | yes |
| `url` | `races.url` | text | yes | Direct copy | yes | no |
| `raceName` | `races.race_name` | text | no | Direct copy | yes | no |
| `date` | `races.race_date` | date | no for modern records | Parse ISO date | yes if raw field retained in payload archive | yes |
| `time` | `races.race_time_utc` | time or timestamptz component | yes | Parse `HH:MM:SSZ`; preserve UTC meaning | yes | yes |
| `FirstPractice`, `SecondPractice`, `ThirdPractice`, `Qualifying`, `Sprint` | future session metadata or optional race schedule fields | date/time | yes | Only store if included in final schema | yes | yes |

Recommendation: keep `races` as the weekend/event anchor for Phase 1. If storing session schedule fields now, keep them optional and source-aligned; do not introduce a full generic `sessions` table until the project intentionally supports broader session ingestion.

### 2.3 Circuits

Source endpoints:

- `/circuits.json`
- Race schedule/result endpoints include nested `Circuit`

| Source Field | Target Field | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `Circuit.circuitId` | `circuits.circuit_id` | varchar | no | Direct copy | yes | no |
| `Circuit.url` | `circuits.url` | text | yes | Direct copy | yes | no |
| `Circuit.circuitName` | `circuits.circuit_name` | text | no | Direct copy | yes | no |
| `Circuit.Location.lat` | `circuits.latitude` | decimal | yes | Parse string decimal | yes | yes |
| `Circuit.Location.long` | `circuits.longitude` | decimal | yes | Parse string decimal | yes | yes |
| `Circuit.Location.locality` | `circuits.locality` | text | yes | Direct copy | yes | no |
| `Circuit.Location.country` | `circuits.country` | text | yes | Direct copy | yes | no |

### 2.4 Drivers

Source endpoints:

- `/drivers.json`
- Result, qualifying, sprint, and standings endpoints include nested `Driver`

| Source Field | Target Field | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `Driver.driverId` | `drivers.driver_id` | varchar | no | Direct copy | yes | no |
| `Driver.permanentNumber` | `drivers.permanent_number` | integer | yes | Parse string integer | yes | yes |
| `Driver.code` | `drivers.code` | varchar(3) | yes | Direct copy | yes | no |
| `Driver.url` | `drivers.url` | text | yes | Direct copy | yes | no |
| `Driver.givenName` | `drivers.given_name` | text | no for normal records | Direct copy | yes | no |
| `Driver.familyName` | `drivers.family_name` | text | no for normal records | Direct copy | yes | no |
| `Driver.dateOfBirth` | `drivers.date_of_birth` | date | yes | Parse ISO date | yes | yes |
| `Driver.nationality` | `drivers.nationality` | text | yes | Direct copy | yes | no |

Do not store a permanent constructor on `drivers`.

### 2.5 Constructors

Source endpoints:

- `/constructors.json`
- Result, qualifying, sprint, and standings endpoints include nested `Constructor`

| Source Field | Target Field | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `Constructor.constructorId` | `constructors.constructor_id` | varchar | no | Direct copy | yes | no |
| `Constructor.url` | `constructors.url` | text | yes | Direct copy | yes | no |
| `Constructor.name` | `constructors.name` | text | no | Direct copy | yes | no |
| `Constructor.nationality` | `constructors.nationality` | text | yes | Direct copy | yes | no |

Constructor lineage/rebranding can be a future analytical mapping. It is not required for the Phase 1 source-aligned schema.

### 2.6 Race Results

Source endpoint: `/{season}/{round}/results.json`

Source entity: `RaceTable.Races[].Results[]`

| Source Field | Target Field | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `number` | `race_results.car_number` | integer | yes | Parse string integer | yes | yes |
| `position` | `race_results.source_position` or `finishing_position` | integer | no when result exists | Parse string integer | yes | yes |
| `positionText` | `race_results.position_text` | varchar | no | Direct copy | yes | no |
| `points` | `race_results.points` | decimal | no | Parse string decimal | yes | yes |
| `grid` | `race_results.grid_position` | integer | yes | Parse string integer; `0` means special start such as pit lane | yes | yes |
| `laps` | `race_results.laps_completed` | integer | no | Parse string integer | yes | yes |
| `status` | `race_results.status` | varchar | no | Direct copy | yes | no |
| `Driver.*` | `drivers`, `race_results.driver_id` | FK | no | Upsert driver and link | yes | yes |
| `Constructor.*` | `constructors`, `race_results.constructor_id` | FK | no | Upsert constructor and link | yes | yes |
| `Time.millis` | `race_results.time_millis` | bigint | yes | Parse string integer | yes | yes |
| `Time.time` | `race_results.time_text` | varchar | yes | Direct copy; winner absolute, others may be gap | yes | optional parsed interval |
| `FastestLap.rank` | `race_results.fastest_lap_rank` | integer | yes | Parse string integer | yes | yes |
| `FastestLap.lap` | `race_results.fastest_lap_number` | integer | yes | Parse string integer | yes | yes |
| `FastestLap.Time.time` | `race_results.fastest_lap_time_text` | varchar | yes | Direct copy | yes | yes, add `fastest_lap_time_millis` |
| `FastestLap.AverageSpeed.units` | `race_results.fastest_lap_avg_speed_units` | varchar | yes | Direct copy | yes | no |
| `FastestLap.AverageSpeed.speed` | `race_results.fastest_lap_avg_speed` | decimal | yes | Parse string decimal | yes | yes |

Required correction: preserve the source `position` even for retired/non-classified entries. If the final column is named `finishing_position`, its definition must be "source-provided result position/classification order", not "NULL for every DNF". Analytical inclusion belongs in derived logic.

### 2.7 Qualifying Results

Source endpoint: `/{season}/{round}/qualifying.json`

Source entity: `RaceTable.Races[].QualifyingResults[]`

| Source Field | Target Field | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `number` | `qualifying_results.car_number` | integer | yes | Parse string integer | yes | yes |
| `position` | `qualifying_results.position` | integer | no when result exists | Parse string integer | yes | yes |
| `Driver.*` | `drivers`, `qualifying_results.driver_id` | FK | no | Upsert driver and link | yes | yes |
| `Constructor.*` | `constructors`, `qualifying_results.constructor_id` | FK | no | Upsert constructor and link | yes | yes |
| `Q1` | `q1_time_text`, `q1_time_millis` | text/integer | yes | Empty or absent means no time | yes | yes |
| `Q2` | `q2_time_text`, `q2_time_millis` | text/integer | yes | Empty or absent means no time | yes | yes |
| `Q3` | `q3_time_text`, `q3_time_millis` | text/integer | yes | Empty or absent means no time | yes | yes |

Required correction: store parsed milliseconds for Q1/Q2/Q3 if these times will be used for pace analysis. Text-only storage blocks efficient SQL comparisons.

### 2.8 Sprint Results

Source endpoint: `/{season}/{round}/sprint.json`

Source entity: `RaceTable.Races[].SprintResults[]`

The sprint payload mirrors race results closely, including `number`, `position`, `positionText`, `points`, `Driver`, `Constructor`, `grid`, `laps`, `status`, optional `Time`, and optional `FastestLap`.

Recommendation: keep `sprint_results` separate in Phase 1. Race results and sprint results are analytically similar but not identical: they have different point systems, calendar availability, distances, and downstream interpretation. Separate tables reduce accidental mixing while keeping SQL simple. A generic session-result model can be revisited when FastF1 or sprint qualifying data becomes a first-class source.

Required correction: apply the same classification and time-preservation rules as `race_results`.

### 2.9 Pit Stops

Source endpoint: `/{season}/{round}/pitstops.json`

Source entity: `RaceTable.Races[].PitStops[]`

| Source Field | Target Field | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `driverId` | `pit_stops.driver_id` | FK | no | Resolve to `drivers` | yes | yes |
| `lap` | `pit_stops.lap` | integer | no | Parse string integer | yes | yes |
| `stop` | `pit_stops.stop_number` | integer | no | Parse string integer | yes | yes |
| `time` | `pit_stops.time_of_day_text` | varchar | yes | Direct copy | yes | optional time |
| `duration` | `pit_stops.duration_text` | varchar | yes | Direct copy | yes | no |
| `duration` | `pit_stops.duration_millis` | bigint | yes | Parse `SS.sss` and `M:SS.sss`/`MM:SS.sss` | yes | yes |

Required correction: add a raw duration field and use a parsed numeric unit that handles minute-based values. Do not assume all durations are simple seconds. Do not discard or overwrite long stops.

Endpoint limitation: pit-stop data availability is historical-era dependent and may be absent for older seasons. Absence must be represented as source unavailability, not as zero stops.

### 2.10 Lap Times

Source endpoint: `/{season}/{round}/laps.json`

Source entity: `RaceTable.Races[].Laps[].Timings[]`

| Source Field | Target Field | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `Laps[].number` | `lap_times.lap_number` | integer | no | Parse string integer | yes | yes |
| `Timings[].driverId` | `lap_times.driver_id` | FK | no | Resolve to `drivers` | yes | yes |
| `Timings[].position` | `lap_times.position` | integer | no | Parse string integer | yes | yes |
| `Timings[].time` | `lap_times.time_text` | varchar | no | Direct copy | yes | no |
| `Timings[].time` | `lap_times.time_millis` | integer | yes | Parse lap-time string | yes | yes |

Endpoint limitation: Jolpica lap timing does not provide tyre compound, in-lap/out-lap flags, track status, weather, or sector detail.

### 2.11 Standings

Source endpoints:

- `/{season}/driverStandings.json`
- `/{season}/{round}/driverStandings.json` if round snapshots are ingested
- `/{season}/constructorStandings.json`
- `/{season}/{round}/constructorStandings.json` if round snapshots are ingested

| Source Field | Target Field | Type | Nullable | Transformation | Preserve Raw? | Parsed Analytical Value? |
| --- | --- | --- | --- | --- | --- | --- |
| `position` | `driver_standings.position`, `constructor_standings.position` | integer | no | Parse string integer | yes | yes |
| `positionText` | recommended `position_text` on standings tables | varchar | yes | Direct copy | yes | no |
| `points` | standings `points` | decimal | no | Parse string decimal | yes | yes |
| `wins` | standings `wins` | integer | no | Parse string integer | yes | yes |
| `Driver` | `driver_standings.driver_id` | FK | no | Resolve driver | yes | yes |
| `Constructors[]` | optional raw/provenance only | JSON or omitted | yes | Do not model as one permanent team | yes | no |
| `Constructor` | `constructor_standings.constructor_id` | FK | no | Resolve constructor | yes | yes |

Recommendation: if round-by-round trajectories are required, ingest standings from round-specific endpoints and key them by `(season_year, round, entity_id)`. If only season endpoints are used, store final standings with an explicit final-round marker.

## 3. Recommended Entity Model

The existing entity list remains the recommended Phase 1 model. It is source-compatible, easy to query, and avoids theoretical normalization that would slow implementation.

No generic `sessions` table is required before Phase 2 implementation. The known Jolpica source surface has separate race, qualifying, sprint, pit-stop, lap, and standings resources. A generic session model may be valuable once FastF1 practice, sprint qualifying, weather, tyre, and telemetry streams are included.

Race and sprint results should remain separate for Phase 1. They share a shape but differ in meaning, point rules, distance, availability, and expected analysis. Separate tables make it harder to accidentally combine sprint and Grand Prix results in metrics like win rate or podium rate.

## 4. Key Relationships

- `seasons` to `races`: one season has many race weekends.
- `circuits` to `races`: one circuit can host many races over time.
- `drivers` to results/laps/pit stops/standings: one driver participates in many events.
- `constructors` to results/qualifying/sprints/standings: constructor relationship is captured at the event/session result level.
- `races` to `race_results`: one race has one result row per classified/entered driver.
- `races` to `qualifying_results`: one race weekend has zero or more qualifying classification rows.
- `races` to `sprint_results`: one race weekend has zero or more sprint classification rows.
- `races` to `pit_stops`: one race has zero or more pit-stop rows.
- `races` to `lap_times`: one race has zero or more lap-timing rows.

Driver-constructor relationships must never be represented as permanent driver attributes. A driver can change constructors during a season or career, and standings may list multiple constructors for a driver. The correct relationship is the constructor attached to a specific race, qualifying result, sprint result, or standing context.

## 5. Primary and Unique Keys

Recommended primary keys may remain surrogate integer IDs for implementation convenience, except `seasons.season_year` can remain a natural primary key.

Recommended business keys:

| Entity | Business Key | Assessment |
| --- | --- | --- |
| `seasons` | `season_year` | Correct. |
| `circuits` | `circuit_id` | Correct for Jolpica source identity. |
| `constructors` | `constructor_id` | Correct for Jolpica source identity. |
| `drivers` | `driver_id` | Correct for Jolpica source identity. |
| `races` | `(season_year, round)` | Correct for F1 championship rounds in Jolpica. |
| `race_results` | `(race_id, driver_id)` | Correct for one Grand Prix result per driver per race. |
| `qualifying_results` | `(race_id, driver_id)` | Correct for current Phase 1 qualifying result shape. |
| `sprint_results` | `(race_id, driver_id)` | Correct while there is only one sprint race per race weekend. If future sprint qualifying is modeled in the same table, add session discriminator. |
| `pit_stops` | `(race_id, driver_id, stop_number)` | Correct because `stop` is source-provided as the driver's sequential stop count in that race. |
| `lap_times` | `(race_id, driver_id, lap_number)` | Correct because Jolpica has one timing row per driver per race lap. |
| `driver_standings` | `(season_year, round, driver_id)` | Correct for round snapshots. |
| `constructor_standings` | `(season_year, round, constructor_id)` | Correct for round snapshots. |
| `etl_log` | surrogate `id` | Correct; log rows represent runs, not source entities. |

## 6. Index Recommendations

Keep indexes focused on real Phase 1 access patterns:

| Table | Recommended Indexes | Reason |
| --- | --- | --- |
| `races` | unique `(season_year, round)`, index `circuit_id`, optional `(season_year, race_date)` | Race lookup and season ordering. |
| `race_results` | unique `(race_id, driver_id)`, indexes `(driver_id, race_id)`, `(constructor_id, race_id)`, `(race_id, source_position)` | Race classification, driver history, constructor aggregations. |
| `qualifying_results` | unique `(race_id, driver_id)`, indexes `(driver_id, race_id)`, `(constructor_id, race_id)`, `(race_id, position)` | Qualifying history and teammate comparisons. |
| `sprint_results` | unique `(race_id, driver_id)`, indexes `(driver_id, race_id)`, `(constructor_id, race_id)`, `(race_id, source_position)` | Sprint classification and sprint points. |
| `pit_stops` | unique `(race_id, driver_id, stop_number)`, indexes `(race_id, lap)`, `(driver_id, race_id)`, `(race_id, duration_millis)` | Pit windows, driver stop history, pit duration rankings. |
| `lap_times` | unique `(race_id, driver_id, lap_number)`, indexes `(race_id, lap_number)`, `(driver_id, race_id, lap_number)`, optional `(race_id, position)` | Largest table; supports lap charts and race pace queries. |
| `driver_standings` | unique `(season_year, round, driver_id)`, indexes `(driver_id, season_year, round)`, `(season_year, round, position)` | Championship trajectories. |
| `constructor_standings` | unique `(season_year, round, constructor_id)`, indexes `(constructor_id, season_year, round)`, `(season_year, round, position)` | Constructor trajectories. |
| `etl_log` | `(source, entity_type, season_year, round)`, `(status, started_at)` | Observability and rerun diagnosis. |

Table partitioning is not needed for Phase 1. Revisit if multi-decade lap timing becomes slow.

## 7. DNF, DNS, DSQ, and Classification Semantics

### 7.1 Source Fact

Preserve these source fields exactly:

- `position`: numeric source classification order when present.
- `positionText`: source display/classification text, such as numeric strings, `R`, `D`, `W`, or other historical codes.
- `status`: source classification/status reason, such as `Finished`, `Lapped`, `+1 Lap`, `Retired`, `Engine`, `Collision`, or `Disqualified`.
- `laps`: source laps completed.
- `grid`: source starting grid value, including `0` when provided.

Source data should not be overwritten for analytical convenience.

### 7.2 Recommended Field Names

To avoid ambiguity, prefer:

- `source_position`: integer parsed from Jolpica `position`; preserves official/source order.
- `position_text`: text copied from Jolpica `positionText`.
- `status`: text copied from Jolpica `status`.
- `classification_status`: derived analytical enum.

If the existing schema keeps the name `finishing_position`, redefine it as source-provided result position/classification order and do not force it to `NULL` for every DNF. The clearer option is to rename it to `source_position` before migrations are created.

### 7.3 What NULL Means

For `source_position`/`finishing_position`, `NULL` should mean the source did not provide a numeric result position or no result row was available. It should not mean "DNF" by itself.

For analytical metrics, missing eligibility should be represented in derived logic or views, not by nulling source facts.

### 7.4 Normalized Analytical Classification

Recommended derived field or analytical-view expression: `classification_status`.

Allowed values:

- `CLASSIFIED_FINISHER`: completed the race distance and has a normal classified finish.
- `LAPPED_FINISHER`: classified but completed fewer laps than the winner/race distance.
- `RETIRED_DNF`: started but did not finish or was not classified due to retirement/failure/incident.
- `DNS`: did not start.
- `DSQ`: disqualified.
- `WITHDRAWN`: withdrawn or did not take part after entry.
- `MISSING_RESULT`: no result row exists where one was expected.
- `UNKNOWN_STATUS`: source status cannot be confidently mapped.

Derivation uses a combination of `position_text`, `status`, `laps_completed`, `grid_position`, and race total laps when available. The source does not provide this normalized enum directly.

Suggested derivation order:

1. If no expected result row exists, classify as `MISSING_RESULT`.
2. If `position_text` or `status` clearly indicates disqualification, classify as `DSQ`.
3. If `position_text` or `status` clearly indicates did-not-start, classify as `DNS`.
4. If `position_text` or `status` indicates withdrawn, classify as `WITHDRAWN`.
5. If `position_text` is numeric and `status` is `Finished`, classify as `CLASSIFIED_FINISHER`.
6. If `position_text` is numeric and `status` is `Lapped` or matches a lapped pattern such as `+1 Lap`, `+2 Laps`, classify as `LAPPED_FINISHER`.
7. If `position_text` is numeric but `laps_completed` is below race distance and `status` is still a classified representation, classify as `LAPPED_FINISHER`.
8. If `position_text` is `R`, or `status` indicates mechanical/incident retirement, classify as `RETIRED_DNF`.
9. Otherwise classify as `UNKNOWN_STATUS` and log the unmapped source status.

This mapping should be tested against known modern and historical cases.

## 8. Lapped Driver Handling

Modern Jolpica payloads can contain `status = "Lapped"` for classified lapped drivers. Other representations may use text like `+1 Lap` or `+2 Laps`. Analytical classification must not depend on one exact text pattern.

Robust lapped handling should:

- Preserve `status` exactly as the source provided it.
- Treat `status = "Lapped"` as classified unless contradicted by disqualification/withdrawal semantics.
- Treat statuses matching a lapped interval pattern as classified.
- Use `position_text` numeric status as supporting evidence that the driver appears in the ordered classification.
- Use `laps_completed` and race winner/race distance to distinguish full-distance finishers from lapped finishers when needed.
- Never treat lapped classified finishers as DNFs.

## 9. Positions Gained/Lost Definition

Do not implement this metric until the schema has settled. The source result must never be modified to make this metric easier.

Recommended contract:

- Name: `positions_gained_lost`
- Formula: `grid_position - analytical_finish_position`
- Analytical finish position: the source result position for entries eligible for this metric.
- Positive value: positions gained.
- Negative value: positions lost.
- Zero: held position.

Eligibility:

- Include only rows with `grid_position > 0`.
- Include only rows with a non-null numeric source position.
- Include `CLASSIFIED_FINISHER` and `LAPPED_FINISHER`.
- Exclude `DNS`, `DSQ`, `WITHDRAWN`, `MISSING_RESULT`, and `UNKNOWN_STATUS`.
- Exclude `RETIRED_DNF` for the default "classified position gain" metric.
- Define a separate optional "classification-order delta including retirements" if product requirements later need it.

Pit-lane starts:

- Jolpica can use `grid = 0` for pit-lane/special starts.
- Default positions gained/lost should exclude `grid = 0` because the ordinal starting position is not equivalent to P0.
- A future metric can map pit-lane starts to an analytical start rank only with a documented rule.

Examples:

- Grid P16, classified finish P4: `16 - 4 = +12`.
- Grid P1, classified finish P9: `1 - 9 = -8`.
- Grid P12, lapped classified finish P15: `12 - 15 = -3`.
- Grid P3, retired with source position P19: excluded from default metric.
- Grid `0`, classified finish P10: excluded from default metric.
- DNS with no meaningful start: excluded.
- DSQ after finishing on track: excluded from default classified metric; source position remains preserved.

Expected SQL behavior:

- Use a `CASE` expression or analytical view that returns `NULL` for excluded cases.
- Do not mutate `grid_position` or `source_position`.
- Count denominators from rows where `positions_gained_lost IS NOT NULL`.

## 10. Time Representation

All time-like source values should retain raw text when the source representation carries meaning or can vary by context.

Recommended units:

- Durations used for SQL arithmetic: integer milliseconds.
- Decimal seconds can be exposed in API responses, but milliseconds avoid floating-point drift.
- Time of day: preserve raw text; parse to `TIME` only when timezone semantics are documented.

| Field | Raw Field | Parsed Field | Unit | Notes |
| --- | --- | --- | --- | --- |
| Race start time | `races.race_time_text` or current `race_time` with clear UTC docs | `race_time_utc` | time | Source often includes `Z`; do not silently treat as local time. |
| Race result time/gap | `race_results.time_text` | `race_results.time_millis` plus optional `time_gap_millis` | ms | Winner is absolute elapsed race time; others may be absolute milliseconds plus gap text. Document semantics. |
| Fastest lap time | `fastest_lap_time_text` | `fastest_lap_time_millis` | ms | Needed for fastest-lap pace comparisons. |
| Qualifying Q1/Q2/Q3 | `q1_time_text`, `q2_time_text`, `q3_time_text` | `q1_time_millis`, `q2_time_millis`, `q3_time_millis` | ms | Empty strings should become raw text plus parsed `NULL`, or be normalized to `NULL` with payload archive preserving raw. |
| Lap time | `lap_times.time_text` | `lap_times.time_millis` | ms | Lap-time analytics depend on parsed values. |
| Pit-stop duration | `pit_stops.duration_text` | `pit_stops.duration_millis` | ms | Parser must handle `SS.sss`, `M:SS.sss`, and `MM:SS.sss`. |
| Pit-stop time of day | `pit_stops.time_of_day_text` | optional `time_of_day` | time | Treat timezone/locality carefully; source examples are time-of-day strings without date. |

Parser requirements:

- Accept `SS.sss`.
- Accept `M:SS.sss` and `MM:SS.sss`.
- Accept race elapsed times such as `H:MM:SS.sss`.
- Accept gap strings such as `+S.sss` and `+M:SS.sss` without confusing them with absolute elapsed times.
- Return `NULL` for empty strings and absent fields while preserving the source text or raw payload.
- Log unparseable non-empty values.

## 11. Pit-Stop Treatment

Raw pit-stop duration must always be preserved. The database should not hardcode a rule such as "exclude durations above 60 seconds."

Recommended fields:

- `duration_text`: raw source string.
- `duration_millis`: parsed numeric duration in milliseconds.
- Optional derived analytical flag in a view: `is_duration_outlier`.
- Optional derived analytical reason field in a view: `duration_context`, with values like `normal`, `long_stop`, `red_flag_candidate`, or `unknown`, only when supported by evidence.

Analytical usage:

- Raw stop listing: use all stops.
- Median pit-stop performance: use context-aware filtering or robust statistics and report the denominator.
- Outlier analysis: include long stops and flag them.
- Strategy stop count: count all source stops, but disclose that red-flag conditions can inflate counts.

Jolpica does not provide enough context to prove every long stop is caused by a red flag. A long duration can be a candidate signal, not a definitive cause.

## 12. Data Provenance

Minimum useful provenance for Phase 1:

- `etl_log.source`: e.g. `jolpica`.
- `etl_log.entity_type`: target resource/table.
- `etl_log.season_year` and `etl_log.round` where applicable.
- `etl_log.source_url` or `endpoint`: exact request URL or endpoint path.
- `etl_log.started_at` and `completed_at`.
- `etl_log.records_processed`, `records_inserted`, `records_updated`, `records_skipped`.
- `etl_log.status` and `error_message`.

Recommended row-level timestamps:

- `created_at`
- `updated_at`
- Optional `source_retrieved_at` for mutable source rows where useful.

Do not add heavy row-level provenance tables before ingestion exists. If full raw payload archiving is implemented, store raw responses by source, endpoint, season, round, retrieval timestamp, and content hash.

## 13. Idempotency Strategy

Every ingestion routine should upsert by the business keys listed in Section 5. `ON CONFLICT DO UPDATE` should update changed source fields and `updated_at`, while preserving created timestamps.

Important notes:

- Race schedule rows should upsert on `(season_year, round)`.
- Result rows should upsert on `(race_id, driver_id)` because a driver should have one race result and one sprint result per race weekend.
- Pit stops should upsert on `(race_id, driver_id, stop_number)`, not on duration or lap, because those are mutable values that could be corrected upstream.
- Lap times should upsert on `(race_id, driver_id, lap_number)`.
- Standings snapshots require a clear round. If ingesting final season standings only, do not accidentally store them as every round.
- Empty sprint payloads should not create fake sprint result rows.

Skipped or quarantined records should be logged; records must not be silently discarded.

## 14. Analytical-Layer Separation

Layer 1 - Source-aligned data:

- Database tables preserve Jolpica entities and fields with minimal transformations.
- String numbers are parsed for relational use, but raw source representations remain available for ambiguous values.
- No LLM-generated facts are stored as source data.

Layer 2 - Analytical views / derived metrics:

- SQL views or materialized views compute positions gained/lost, classified eligibility, race summaries, standings trajectories, teammate comparisons, pit statistics, and denominator-aware aggregations.
- Derived fields must be named so they cannot be confused with source fields.

Layer 3 - Statistical analysis:

- Python/Pandas/NumPy/SciPy compute statistics such as rolling averages, z-scores, confidence intervals, regression, and distribution tests.
- Statistical assumptions and minimum sample sizes remain documented in `docs/analytics-spec.md`.

Layer 4 - Deterministic insight detection:

- Rules and thresholds identify candidate findings.
- No LLM involvement in discovery.

Layer 5 - Evidence package:

- Structured JSON carries observed facts, statistical findings, model outputs, methodology, source references, and limitations.

Layer 6 - AI narrative:

- The LLM explains only supplied evidence.
- It does not calculate metrics, invent data, infer unavailable telemetry, or establish unsupported causes.

## 15. AI Evidence-Contract Review

The existing AI architecture is directionally correct, but the evidence contract should be tightened before implementation.

Required evidence package properties:

- Separate arrays or sections for `observed_facts`, `statistical_findings`, `model_predictions`, and `interpretations`.
- Every numeric claim must include `key`, `value`, `unit`, and either `source_record` or `methodology`.
- `data_limitations` must be first-class and passed to the LLM.
- Evidence records should identify source table, record key, query name or hash, and field names used.
- Model predictions must include model name/version and input features, or be omitted.
- Interpretations must be explicitly non-authoritative unless backed by data.

Bad claim:

- "Ferrari's tyres overheated."

Acceptable claim:

- "Ferrari's race pace declined during the second stint. The available dataset does not contain sufficient tyre-temperature information to establish the cause."

Contradiction to resolve: `docs/product-spec.md` and `docs/ai-insight-spec.md` show different evidence package schema shapes. Before implementing the AI layer, choose one canonical schema or define one as product-level conceptual and one as implementation-level Pydantic. The implementation contract should enforce traceable fields and epistemic categories.

## 16. Analytics Metric Contracts

The existing analytics spec covers the right high-priority metrics, but some eligibility rules need correction to account for preserved source positions and lapped statuses.

| Metric | Contract Review |
| --- | --- |
| Average finishing position | Should average only analytically eligible classified finishers: `CLASSIFIED_FINISHER` and usually `LAPPED_FINISHER`. Do not rely on `finishing_position IS NOT NULL` as DNF logic. |
| Qualifying position | Source `position` is usable. Add parsed Q-time fields for pace analysis. Missing qualifying rows and empty segment times should be handled explicitly. |
| Positions gained/lost | Use `grid_position - source_position` only for eligible classified results with `grid_position > 0`; exclude default DNF/DNS/DSQ/withdrawn/unknown cases. |
| DNF rate | Denominator should be starts, excluding DNS/withdrawn. Numerator should be `RETIRED_DNF` and, if desired by metric variant, DSQ separately. Do not count lapped finishers as DNFs. |
| Points per race | Denominator must specify race starts or race entries. Include sprint points only in explicitly combined metrics. |
| Podium rate | Use source position <= 3 only for eligible classified race results. Sprint podiums should be a separate metric unless explicitly combined. |
| Driver consistency | Requires a defined measure before implementation, such as standard deviation of eligible classified finishing positions or lap-time variance after documented filtering. |
| Constructor performance | Use event-level constructor on result rows. Do not join through a permanent driver-team relationship. Sprint/race points must be separated or explicitly combined. |

## 17. Required Changes Before Database Implementation

These should be resolved before creating migrations:

1. Rename or redefine `race_results.finishing_position` and `sprint_results.finishing_position` so they preserve Jolpica `position` even for DNF/retired rows. Prefer `source_position`.
2. Add a derived analytical classification contract, preferably `classification_status`, with allowed values and derivation rules documented above.
3. Update DNF/DNS/DSQ logic so lapped finishers are classified and not treated as DNFs.
4. Add raw and parsed pit-stop duration fields: `duration_text` and `duration_millis`.
5. Ensure pit-stop duration parsing supports minute-based values such as `40:55.302`.
6. Add parsed millisecond fields for qualifying segment times and fastest-lap times if those values will be analytically compared.
7. Clarify race time/gap semantics so `time_millis` and `time_text` are not misread as the same kind of duration for every result row.
8. Add or document minimal provenance fields on `etl_log`, especially endpoint/source URL.
9. Update analytics contracts to use derived classification eligibility rather than `finishing_position IS NULL` as the DNF mechanism.

## 18. Recommended Changes

These improve maintainability but are not blockers for basic schema implementation:

1. Add `position_text` to driver and constructor standings to preserve source display values.
2. Store `source_retrieved_at` on source-aligned tables or raw payload records if upstream corrections need auditing.
3. Add optional `fastest_lap_avg_speed` and `fastest_lap_avg_speed_units` to race results because Jolpica can provide them.
4. Create a small status-mapping reference document or enum test fixture before writing classification code.
5. Use clearer names such as `time_text`, `time_millis`, `duration_text`, and `duration_millis` consistently across all tables.
6. Keep a raw payload archive only if implementation time allows; otherwise rely on `etl_log` plus preserved source fields.

## 19. No Change Needed

The following parts of the current architecture should remain:

- Jolpica-first Phase 1 source strategy.
- The 12 source-aligned core tables plus `etl_log`.
- Surrogate integer primary keys for most tables with Jolpica IDs preserved as unique natural keys.
- Event-level driver-constructor relationships through result/qualifying/sprint rows.
- Separate race and sprint result tables for Phase 1.
- SQL/Python/statistics as the source of truth.
- Evidence packages before AI narrative generation.
- No migrations, models, ingestion, or executable code in this review task.

## 20. Future Enhancements

Explicitly out of scope for Phase 2 database setup unless separately planned:

- Generic `sessions` table covering every F1 session type.
- Sprint qualifying/shootout modeling unless the endpoint is verified.
- Tyre compounds, tyre age, stint definitions, tyre temperatures, and degradation causality.
- Safety car, VSC, red flag, and race-control event tables.
- Sector times, mini-sectors, telemetry, GPS traces, throttle/brake/DRS/RPM/gear streams.
- Weather and track temperature tables.
- Constructor lineage/rebranding model.
- Predictive ML feature tables.
- Natural-language-to-SQL query history.

These belong to FastF1 or additional-source integration after the Phase 1 database is stable.

## 21. Final Schema Recommendation

### Recommended Phase 1 Entities

Use the existing 12-table Jolpica-first model:

- `seasons`
- `circuits`
- `constructors`
- `drivers`
- `races`
- `race_results`
- `qualifying_results`
- `sprint_results`
- `pit_stops`
- `lap_times`
- `driver_standings`
- `constructor_standings`
- `etl_log`

### Important Fields

- Preserve Jolpica IDs: `driver_id`, `constructor_id`, `circuit_id`.
- Preserve event identity: `season_year`, `round`, `race_id`.
- Preserve result source facts: `source_position`, `position_text`, `status`, `grid_position`, `laps_completed`, `points`.
- Preserve raw time strings where context matters.
- Store parsed milliseconds for lap, qualifying, fastest-lap, race elapsed/gap, and pit-stop duration analysis.

### Important Constraints

- Unique `(season_year, round)` on `races`.
- Unique source IDs on `drivers`, `constructors`, and `circuits`.
- Unique `(race_id, driver_id)` on race, qualifying, and sprint result tables.
- Unique `(race_id, driver_id, stop_number)` on pit stops.
- Unique `(race_id, driver_id, lap_number)` on lap times.
- Unique `(season_year, round, driver_id)` and `(season_year, round, constructor_id)` on standings snapshots.

### Important Indexes

- Season/race lookup: `races(season_year, round)`.
- Result history: `(driver_id, race_id)`, `(constructor_id, race_id)`.
- Classification: `(race_id, source_position)`.
- Lap charts: `(race_id, lap_number)`, `(driver_id, race_id, lap_number)`.
- Pit analysis: `(race_id, lap)`, `(race_id, duration_millis)`.
- Standings trajectories: `(season_year, round, position)` and entity-season-round indexes.

### Analytical Fields Derived Rather Than Stored as Source Facts

- `classification_status`
- `is_classified`
- `is_lapped`
- `is_dnf`
- `is_dns`
- `is_dsq`
- `positions_gained_lost`
- pit-stop outlier flags
- clean-lap eligibility
- race pace aggregates
- driver consistency metrics
- constructor performance summaries

These may live in analytical views/materialized views. If stored later for performance, their derivation must remain documented and reproducible.

### Data That Must Remain Raw

- Result `positionText`
- Result `status`
- Race result `Time.time`
- Fastest lap `Time.time`
- Qualifying `Q1`, `Q2`, `Q3`
- Lap timing `time`
- Pit-stop `time`
- Pit-stop `duration`
- Source URL/endpoint in ETL provenance

### Future FastF1 / Additional-Source Data

Do not claim these from Jolpica alone:

- Tyre compounds and tyre age
- Tyre temperature or degradation causes
- Safety car/VSC/red flag periods
- Detailed weather and track temperature
- Sector/mini-sector data
- High-frequency telemetry
- GPS traces and car channels
- Practice session timing

## 22. Final Recommendation

Proceed to Phase 2 implementation only after reconciling the required schema and analytics-contract changes above. The entity model is sound, but the current treatment of finishing position, lapped results, DNF semantics, and pit-stop durations would create misleading analytics if implemented unchanged.

Once those documentation corrections are accepted, the exact next implementation task should be: create the Python project skeleton, PostgreSQL/Alembic configuration, and an initial migration for the corrected source-aligned schema, with tests that verify the database constraints and the documented time/status parsing contracts.

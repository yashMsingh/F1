import psycopg2
import json

conn = psycopg2.connect('postgresql://f1user:changeme@localhost:5432/f1_race_intelligence')
cur = conn.cursor()

print("=" * 80)
print("PHASE 5A: FULL-SEASON INTEGRITY AUDIT (2024 ROUNDS 1-24)")
print("=" * 80)

# 1. Total races
cur.execute("SELECT COUNT(*) FROM races WHERE season_year = 2024")
race_cnt = cur.fetchone()[0]
print(f"2024 Races: {race_cnt} (expected 24) -> {'PASS' if race_cnt == 24 else 'FAIL'}")

# 2. Check all rounds present from 1 to 24 without gaps
cur.execute("SELECT round FROM races WHERE season_year = 2024 ORDER BY round")
rounds = [r[0] for r in cur.fetchall()]
print(f"Round sequence: {rounds[0]} to {rounds[-1]} (contiguous: {rounds == list(range(1, 25))})")

# 3. Table counts
tables = [
    'seasons', 'circuits', 'constructors', 'drivers', 'races',
    'race_results', 'qualifying_results', 'sprint_results', 'pit_stops',
    'lap_times', 'driver_standings', 'constructor_standings', 'etl_log'
]
print("\nTable Counts:")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t:<24}: {cur.fetchone()[0]}")

# 4. Check natural keys uniqueness
checks = [
    ('race_results', '(race_id, driver_id)'),
    ('qualifying_results', '(race_id, driver_id)'),
    ('sprint_results', '(race_id, driver_id)'),
    ('pit_stops', '(race_id, driver_id, stop_number)'),
    ('driver_standings', '(season_year, round, driver_id)'),
    ('constructor_standings', '(season_year, round, constructor_id)')
]
print("\nNatural Key Uniqueness:")
all_keys_ok = True
for tbl, key in checks:
    cur.execute(f"SELECT {key}, COUNT(*) FROM {tbl} GROUP BY {key} HAVING COUNT(*) > 1")
    dups = cur.fetchall()
    ok = len(dups) == 0
    if not ok: all_keys_ok = False
    print(f"  {tbl:<24} {key:<35}: {len(dups)} duplicates -> {'PASS' if ok else 'FAIL'}")

# 5. Check foreign key integrity
fk_checks = [
    ("race_results -> races", "SELECT COUNT(*) FROM race_results WHERE race_id NOT IN (SELECT id FROM races)"),
    ("race_results -> drivers", "SELECT COUNT(*) FROM race_results WHERE driver_id NOT IN (SELECT id FROM drivers)"),
    ("race_results -> constructors", "SELECT COUNT(*) FROM race_results WHERE constructor_id NOT IN (SELECT id FROM constructors)"),
    ("qualifying_results -> races", "SELECT COUNT(*) FROM qualifying_results WHERE race_id NOT IN (SELECT id FROM races)"),
    ("sprint_results -> races", "SELECT COUNT(*) FROM sprint_results WHERE race_id NOT IN (SELECT id FROM races)"),
    ("pit_stops -> races", "SELECT COUNT(*) FROM pit_stops WHERE race_id NOT IN (SELECT id FROM races)"),
    ("lap_times -> races", "SELECT COUNT(*) FROM lap_times WHERE race_id NOT IN (SELECT id FROM races)"),
    ("driver_standings -> drivers", "SELECT COUNT(*) FROM driver_standings WHERE driver_id NOT IN (SELECT id FROM drivers)"),
    ("constructor_standings -> constructors", "SELECT COUNT(*) FROM constructor_standings WHERE constructor_id NOT IN (SELECT id FROM constructors)"),
]
print("\nForeign Key Referential Integrity:")
all_fk_ok = True
for desc, q in fk_checks:
    cur.execute(q)
    orphans = cur.fetchone()[0]
    ok = orphans == 0
    if not ok: all_fk_ok = False
    print(f"  {desc:<40}: {orphans} orphans -> {'PASS' if ok else 'FAIL'}")

# 6. Check Rounds 1-15 preservation against baseline
with open('scratch/pre_phase_5a_baseline.json') as f:
    pre = json.load(f)

cur.execute("SELECT COUNT(*) FROM race_results rr JOIN races r ON rr.race_id = r.id WHERE r.season_year = 2024 AND r.round <= 15")
r1_15_res = cur.fetchone()[0]
res_ok = r1_15_res == pre['table_counts']['race_results']

cur.execute("SELECT COUNT(*) FROM sprint_results sr JOIN races r ON sr.race_id = r.id WHERE r.season_year = 2024 AND r.round <= 15")
r1_15_sr = cur.fetchone()[0]
sr_ok = r1_15_sr == pre['table_counts']['sprint_results']

cur.execute("SELECT COUNT(*) FROM pit_stops ps JOIN races r ON ps.race_id = r.id WHERE r.season_year = 2024 AND r.round <= 15")
r1_15_pits = cur.fetchone()[0]
pits_ok = r1_15_pits == pre['table_counts']['pit_stops']

cur.execute("SELECT COUNT(*) FROM lap_times lt JOIN races r ON lt.race_id = r.id WHERE r.season_year = 2024 AND r.round <= 15")
r1_15_laps = cur.fetchone()[0]
laps_ok = r1_15_laps == pre['table_counts']['lap_times']

print("\nRounds 1-15 Preservation:")
print(f"  Race Results (R1-R15)  : {r1_15_res} vs baseline {pre['table_counts']['race_results']} -> {'PASS' if res_ok else 'FAIL'}")
print(f"  Sprint Results (R1-R15): {r1_15_sr} vs baseline {pre['table_counts']['sprint_results']} -> {'PASS' if sr_ok else 'FAIL'}")
print(f"  Pit Stops (R1-R15)     : {r1_15_pits} vs baseline {pre['table_counts']['pit_stops']} -> {'PASS' if pits_ok else 'FAIL'}")
print(f"  Lap Times (R1-R15)     : {r1_15_laps} vs baseline {pre['table_counts']['lap_times']} -> {'PASS' if laps_ok else 'FAIL'}")

# 7. Check ETL log statuses
cur.execute("SELECT status, COUNT(*) FROM etl_log GROUP BY status")
etl_statuses = dict(cur.fetchall())
print(f"\nETL Logs (Total 38): {etl_statuses}")

conn.close()

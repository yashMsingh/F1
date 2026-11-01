import psycopg2
import json

conn = psycopg2.connect('postgresql://f1user:changeme@localhost:5432/f1_race_intelligence')
cur = conn.cursor()

# 1. 24 races check
cur.execute('SELECT COUNT(*) FROM races WHERE season_year = 2024')
print('2024 Races count:', cur.fetchone()[0])

# Read pre-ingestion baseline snapshot
with open('scratch/pre_phase_5a_baseline.json') as f:
    pre = json.load(f)

# 2. Check Rounds 1-15 preservation
cur.execute('SELECT COUNT(*) FROM race_results rr JOIN races r ON rr.race_id = r.id WHERE r.season_year = 2024 AND r.round <= 15')
r1_15_res = cur.fetchone()[0]
print(f"Rounds 1-15 race results: {r1_15_res} (baseline was {pre['table_counts']['race_results']})")

cur.execute('SELECT COUNT(*) FROM sprint_results sr JOIN races r ON sr.race_id = r.id WHERE r.season_year = 2024 AND r.round <= 15')
r1_15_sr = cur.fetchone()[0]
print(f"Rounds 1-15 sprint results: {r1_15_sr} (baseline was {pre['table_counts']['sprint_results']})")

cur.execute('SELECT COUNT(*) FROM pit_stops ps JOIN races r ON ps.race_id = r.id WHERE r.season_year = 2024 AND r.round <= 15')
r1_15_pits = cur.fetchone()[0]
print(f"Rounds 1-15 pit stops: {r1_15_pits} (baseline was {pre['table_counts']['pit_stops']})")

cur.execute('SELECT COUNT(*) FROM lap_times lt JOIN races r ON lt.race_id = r.id WHERE r.season_year = 2024 AND r.round <= 15')
r1_15_laps = cur.fetchone()[0]
print(f"Rounds 1-15 lap times: {r1_15_laps} (baseline was {pre['table_counts']['lap_times']})")

# 3. Check Natural Key Uniqueness across all tables
checks = [
    ('race_results', '(race_id, driver_id)'),
    ('qualifying_results', '(race_id, driver_id)'),
    ('sprint_results', '(race_id, driver_id)'),
    ('pit_stops', '(race_id, driver_id, stop_number)'),
    ('driver_standings', '(season_year, round, driver_id)'),
    ('constructor_standings', '(season_year, round, constructor_id)')
]
print('\nNatural Key Duplicates Check:')
for tbl, key in checks:
    cur.execute(f'SELECT {key}, COUNT(*) FROM {tbl} GROUP BY {key} HAVING COUNT(*) > 1')
    dups = cur.fetchall()
    print(f'  {tbl:<25} {key:<35}: {len(dups)} duplicates')

# 4. Check Reference entities (Antonelli, Doohan pre-R24)
cur.execute("SELECT d.driver_id, COUNT(rr.id) FROM drivers d LEFT JOIN race_results rr ON d.id = rr.driver_id WHERE d.driver_id IN ('antonelli', 'doohan') GROUP BY d.driver_id")
for row in cur.fetchall():
    print(f'Driver {row[0]}: {row[1]} race starts')

# 5. Check foreign key integrity
fk_checks = [
    ("race_results without race", "SELECT COUNT(*) FROM race_results WHERE race_id NOT IN (SELECT id FROM races)"),
    ("race_results without driver", "SELECT COUNT(*) FROM race_results WHERE driver_id NOT IN (SELECT id FROM drivers)"),
    ("race_results without constructor", "SELECT COUNT(*) FROM race_results WHERE constructor_id NOT IN (SELECT id FROM constructors)"),
    ("qualifying_results without race", "SELECT COUNT(*) FROM qualifying_results WHERE race_id NOT IN (SELECT id FROM races)"),
    ("sprint_results without race", "SELECT COUNT(*) FROM sprint_results WHERE race_id NOT IN (SELECT id FROM races)"),
    ("pit_stops without race", "SELECT COUNT(*) FROM pit_stops WHERE race_id NOT IN (SELECT id FROM races)"),
    ("lap_times without race", "SELECT COUNT(*) FROM lap_times WHERE race_id NOT IN (SELECT id FROM races)"),
]
print('\nForeign Key Integrity Checks:')
for desc, q in fk_checks:
    cur.execute(q)
    print(f'  {desc:<35}: {cur.fetchone()[0]} orphaned records')

conn.close()

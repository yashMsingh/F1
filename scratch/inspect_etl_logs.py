from sqlalchemy import create_engine, text

url = 'postgresql://f1user:changeme@localhost:5432/f1_race_intelligence'
eng = create_engine(url)

with eng.connect() as conn:
    logs = conn.execute(text('''
        SELECT id, season_year, round, status,
               started_at, completed_at,
               records_processed, records_inserted, records_skipped, records_updated,
               error_message
        FROM etl_log
        ORDER BY id ASC
    ''')).fetchall()

    print(f"Total etl_log entries: {len(logs)}")
    print("-" * 115)
    print(f"{'ID':<4} | {'Year':<5} | {'Rnd':<4} | {'Status':<8} | {'Started At':<19} | {'Completed At':<19} | {'Proc':<5} | {'Ins':<5} | {'Skip':<5} | {'Upd':<4}")
    print("-" * 115)
    for l in logs:
        s_at = str(l[4])[:19] if l[4] else 'None'
        c_at = str(l[5])[:19] if l[5] else 'None'
        print(f"{l[0]:<4} | {l[1]:<5} | {l[2]:<4} | {l[3]:<8} | {s_at:<19} | {c_at:<19} | {l[6]:<5} | {l[7]:<5} | {l[8]:<5} | {l[9]:<4}")

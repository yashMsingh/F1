from sqlalchemy import create_engine, text

url = 'postgresql://f1user:changeme@localhost:5432/f1_race_intelligence'
eng = create_engine(url)

with eng.connect() as conn:
    print('=== 1. AUSTRIA ROUND 11: SPRINT VS GP RESULTS ===')
    sp_winner = conn.execute(text('''
        SELECT d.driver_id, d.code, sr.position_text, sr.points, sr.status
        FROM sprint_results sr
        JOIN races r ON sr.race_id = r.id
        JOIN drivers d ON sr.driver_id = d.id
        WHERE r.round = 11 AND sr.position_text = '1'
    ''')).fetchone()
    print('Sprint Winner:', sp_winner)

    gp_winner = conn.execute(text('''
        SELECT d.driver_id, d.code, rr.position_text, rr.points, rr.status
        FROM race_results rr
        JOIN races r ON rr.race_id = r.id
        JOIN drivers d ON rr.driver_id = d.id
        WHERE r.round = 11 AND rr.position_text = '1'
    ''')).fetchone()
    print('GP Winner:', gp_winner)

    ver_gp = conn.execute(text('''
        SELECT d.driver_id, d.code, rr.position_text, rr.points, rr.status
        FROM race_results rr
        JOIN races r ON rr.race_id = r.id
        JOIN drivers d ON rr.driver_id = d.id
        WHERE r.round = 11 AND d.driver_id = 'max_verstappen'
    ''')).fetchone()
    print('Verstappen GP Result:', ver_gp)

    print('\n=== 2. BRITAIN ROUND 12: COLAPINTO INTEGRITY ===')
    col_driver = conn.execute(text("SELECT id, driver_id, code, given_name, family_name FROM drivers WHERE driver_id = 'colapinto'")).fetchone()
    print('Colapinto in drivers table:', col_driver)
    col_race_results = conn.execute(text("SELECT count(*) FROM race_results rr JOIN drivers d ON rr.driver_id = d.id WHERE d.driver_id = 'colapinto'")).scalar()
    print('Colapinto race_results count:', col_race_results)
    col_quali = conn.execute(text("SELECT count(*) FROM qualifying_results qr JOIN drivers d ON qr.driver_id = d.id WHERE d.driver_id = 'colapinto'")).scalar()
    print('Colapinto qualifying_results count:', col_quali)
    col_standings = conn.execute(text("SELECT count(*) FROM driver_standings ds JOIN drivers d ON ds.driver_id = d.id WHERE d.driver_id = 'colapinto'")).scalar()
    print('Colapinto driver_standings count:', col_standings)

    print('\n=== 3. BELGIUM ROUND 14: RUSSELL DISQUALIFICATION ===')
    bel_winner = conn.execute(text('''
        SELECT d.driver_id, d.code, rr.position_text, rr.points, rr.status
        FROM race_results rr
        JOIN races r ON rr.race_id = r.id
        JOIN drivers d ON rr.driver_id = d.id
        WHERE r.round = 14 AND rr.position_text = '1'
    ''')).fetchone()
    print('Belgium Official Winner (P1):', bel_winner)

    russell_bel = conn.execute(text('''
        SELECT d.driver_id, d.code, rr.source_position, rr.position_text, rr.points, rr.status
        FROM race_results rr
        JOIN races r ON rr.race_id = r.id
        JOIN drivers d ON rr.driver_id = d.id
        WHERE r.round = 14 AND d.driver_id = 'russell'
    ''')).fetchone()
    print('Russell Belgium Result:', russell_bel)

    print('\n=== 4. NETHERLANDS ROUND 15: SARGEANT QUALIFYING & RACE ===')
    sar_q = conn.execute(text('''
        SELECT d.driver_id, qr.position, qr.q1_time, qr.q1_time_millis, qr.q2_time, qr.q3_time
        FROM qualifying_results qr
        JOIN races r ON qr.race_id = r.id
        JOIN drivers d ON qr.driver_id = d.id
        WHERE r.round = 15 AND d.driver_id = 'sargeant'
    ''')).fetchone()
    print('Sargeant Zandvoort Qualifying:', sar_q)

    sar_race = conn.execute(text('''
        SELECT d.driver_id, rr.grid_position, rr.source_position, rr.position_text, rr.status, rr.points
        FROM race_results rr
        JOIN races r ON rr.race_id = r.id
        JOIN drivers d ON rr.driver_id = d.id
        WHERE r.round = 15 AND d.driver_id = 'sargeant'
    ''')).fetchone()
    print('Sargeant Zandvoort Race Result:', sar_race)

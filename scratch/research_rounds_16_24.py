"""Research Jolpica API data for 2024 Rounds 16 to 24."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.f1.client import JolpicaClient

client = JolpicaClient()

print("=" * 80)
print("RESEARCHING 2024 ROUNDS 16-24 VIA JOLPICA API")
print("=" * 80)

research_data = {}

for rnd in range(16, 25):
    print(f"\n--- Round {rnd} ---")
    rnd_info = {}

    # 1. Race details
    race_page = client.get_page(f"2024/{rnd}")
    race_table = race_page.data.get("RaceTable", {})
    races = race_table.get("Races", [])
    if races:
        r = races[0]
        rnd_info["race_name"] = r.get("raceName")
        rnd_info["circuit_id"] = r.get("Circuit", {}).get("circuitId")
        rnd_info["circuit_name"] = r.get("Circuit", {}).get("circuitName")
        rnd_info["date"] = r.get("date")
        rnd_info["has_sprint"] = "Sprint" in r
        print(f"Race: {rnd_info['race_name']} at {rnd_info['circuit_name']} ({rnd_info['date']}) | Sprint: {rnd_info['has_sprint']}")

    # 2. Results
    res_page = client.get_race_results(2024, rnd)
    res_races = res_page.data.get("RaceTable", {}).get("Races", [])
    results = res_races[0].get("Results", []) if res_races else []
    rnd_info["results_count"] = len(results)
    winner = results[0] if results else {}
    winner_name = f"{winner.get('Driver', {}).get('givenName')} {winner.get('Driver', {}).get('familyName')}"
    rnd_info["winner"] = winner_name
    drivers_in_race = [f"{res.get('Driver', {}).get('driverId')}" for res in results]
    rnd_info["drivers"] = drivers_in_race

    # Check non-classified / special statuses
    special_statuses = []
    for res in results:
        pos_text = res.get("positionText")
        status = res.get("status")
        pos = res.get("position")
        d_id = res.get("Driver", {}).get("driverId")
        if not pos_text.isdigit() or status.lower() in ("retired", "did not start", "disqualified", "withdrawn"):
            special_statuses.append({"driver": d_id, "pos": pos, "pos_text": pos_text, "status": status})
    rnd_info["special_results"] = special_statuses

    # 3. Qualifying
    q_page = client.get_qualifying_results(2024, rnd)
    q_races = q_page.data.get("RaceTable", {}).get("Races", [])
    q_results = q_races[0].get("QualifyingResults", []) if q_races else []
    rnd_info["qualifying_count"] = len(q_results)
    null_q_times = []
    for qr in q_results:
        d_id = qr.get("Driver", {}).get("driverId")
        if not qr.get("Q1") and not qr.get("Q2") and not qr.get("Q3"):
            null_q_times.append(d_id)
    rnd_info["null_quali_drivers"] = null_q_times

    # 4. Sprint
    sprint_results = []
    if rnd_info.get("has_sprint"):
        sr_page = client.get_sprint_results(2024, rnd)
        sr_races = sr_page.data.get("RaceTable", {}).get("Races", [])
        sprint_results = sr_races[0].get("SprintResults", []) if sr_races else []
    rnd_info["sprint_count"] = len(sprint_results)

    # 5. Pit stops
    pits = client.get_all_pit_stops(2024, rnd)
    rnd_info["pit_stops_count"] = len(pits)

    # 6. Standings
    ds_page = client.get_driver_standings(2024, rnd)
    ds_list = ds_page.data.get("StandingsTable", {}).get("StandingsLists", [])
    ds_count = len(ds_list[0].get("DriverStandings", [])) if ds_list else 0
    rnd_info["driver_standings_count"] = ds_count

    cs_page = client.get_constructor_standings(2024, rnd)
    cs_list = cs_page.data.get("StandingsTable", {}).get("StandingsLists", [])
    cs_count = len(cs_list[0].get("ConstructorStandings", [])) if cs_list else 0
    rnd_info["constructor_standings_count"] = cs_count

    print(f"  Results: {len(results)} | Winner: {winner_name} | Special: {len(special_statuses)}")
    print(f"  Qualifying: {len(q_results)} | Null Q: {null_q_times}")
    print(f"  Sprint: {len(sprint_results)} | Pits: {len(pits)} | Standings: D={ds_count}, C={cs_count}")

    research_data[rnd] = rnd_info

with open("scratch/research_rounds_16_24.json", "w") as f:
    json.dump(research_data, f, indent=2)

print("\nResearch complete and saved to scratch/research_rounds_16_24.json")

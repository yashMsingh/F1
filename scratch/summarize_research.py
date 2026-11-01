import json

with open("scratch/research_rounds_16_24.json") as f:
    data = json.load(f)

total_results = 0
total_quali = 0
total_sprint = 0
total_pits = 0
all_drivers = set()

for rnd, info in data.items():
    print(f"R{rnd}: {info['race_name']} | Sprint: {info['has_sprint']} | Winner: {info['winner']} | Pits: {info['pit_stops_count']}")
    total_results += info["results_count"]
    total_quali += info["qualifying_count"]
    total_sprint += info["sprint_count"]
    total_pits += info["pit_stops_count"]
    all_drivers.update(info["drivers"])

print(f"\nTotals: Results={total_results}, Quali={total_quali}, Sprint={total_sprint}, Pits={total_pits}")
print(f"Distinct drivers across R16-R24 ({len(all_drivers)}): {sorted(list(all_drivers))}")

print("\n=== SPECIAL / RETIREMENT STATUSES ===")
for rnd, info in data.items():
    if info["special_results"]:
        print(f"R{rnd} ({info['race_name']}):")
        for s in info["special_results"]:
            print(f"  {s['driver']}: pos={s['pos']} text={s['pos_text']} status={s['status']}")

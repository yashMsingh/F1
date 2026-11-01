"""Exercise every mounted API endpoint against the live PostgreSQL database."""

import sys
from pathlib import Path
from decimal import Decimal

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.api.app import app
from app.api.deps import get_db

client = TestClient(app)

print("=" * 80)
print("PHASE 4D.4: API ENDPOINT EXERCISE (15-ROUND 2024 DATASET)")
print("=" * 80)

endpoints_tested = []

def test_endpoint(name, method, url, json_body=None, expected_status=200):
    try:
        if method == "GET":
            resp = client.get(url)
        elif method == "POST":
            resp = client.post(url, json=json_body)
        status_ok = resp.status_code == expected_status
        data = resp.json() if resp.status_code != 500 else resp.text
        res = {
            "name": name,
            "method": method,
            "url": url,
            "status_code": resp.status_code,
            "expected_status": expected_status,
            "ok": status_ok,
            "data_summary": None,
        }
        if status_ok:
            if isinstance(data, list):
                res["data_summary"] = f"list (len={len(data)})"
            elif isinstance(data, dict):
                keys = list(data.keys())
                res["data_summary"] = f"dict (keys={keys[:6]}...)"
            else:
                res["data_summary"] = str(data)[:60]
        else:
            res["data_summary"] = f"ERROR: {str(data)[:100]}"
        endpoints_tested.append(res)
        tag = "PASS" if status_ok else "FAIL"
        print(f"[{tag}] {method:<5} {url:<45} -> {resp.status_code} ({res['data_summary']})")
    except Exception as e:
        endpoints_tested.append({
            "name": name, "method": method, "url": url,
            "status_code": None, "expected_status": expected_status,
            "ok": False, "data_summary": f"EXCEPTION: {e}"
        })
        print(f"[FAIL] {method:<5} {url:<45} -> EXCEPTION: {e}")

# 1. Health
test_endpoint("Health Check", "GET", "/api/health")

# 2. Schedule / Races List
test_endpoint("Races List 2024", "GET", "/api/races?season=2024")
test_endpoint("Races List All", "GET", "/api/races")

# 3. Race Details (R15 Dutch GP)
test_endpoint("Race Details R15", "GET", "/api/races/2024/15")
test_endpoint("Race Details 404", "GET", "/api/races/2024/99", expected_status=404)

# 4. Race Results
test_endpoint("Race Results R15", "GET", "/api/races/2024/15/results")
test_endpoint("Race Results R11 (Austria)", "GET", "/api/races/2024/11/results")

# 5. Qualifying Results
test_endpoint("Qualifying Results R15", "GET", "/api/races/2024/15/qualifying")

# 6. Pit Stops
test_endpoint("Pit Stops R15", "GET", "/api/races/2024/15/pit-stops")

# 7. Lap Times
test_endpoint("Lap Times R15 (Sample)", "GET", "/api/races/2024/15/laps")

# 8. Standings
test_endpoint("Standings after R15", "GET", "/api/races/2024/15/standings")
test_endpoint("Standings after R10", "GET", "/api/races/2024/10/standings")

# 9. Event Insights
test_endpoint("Event Insights R15", "GET", "/api/races/2024/15/insights")
test_endpoint("Event Insights R1", "GET", "/api/races/2024/1/insights")

# 10. Season Longitudinal Insights
test_endpoint("Season Insights 2024 (Default)", "GET", "/api/season/2024/insights")
test_endpoint("Season Insights 2024 (Driver: Verstappen)", "GET", "/api/season/2024/insights?driver_id=max_verstappen")
test_endpoint("Season Insights 2024 (Driver: Bearman)", "GET", "/api/season/2024/insights?driver_id=bearman")

# 11. Event Narrative
test_endpoint("Event Narrative R15", "GET", "/api/races/2024/15/narrative")

# 12. Ad-hoc Narrative Generation (POST)
payload_longitudinal = {
    "season": 2024,
    "scope": "longitudinal",
    "driver_id": "max_verstappen",
    "up_to_round": 15,
}
test_endpoint("Post Narrative (Longitudinal)", "POST", "/api/narrative", json_body=payload_longitudinal)

payload_race = {
    "season": 2024,
    "scope": "race",
    "round_num": 15,
}
test_endpoint("Post Narrative (Race Event)", "POST", "/api/narrative", json_body=payload_race)

# Summary
total = len(endpoints_tested)
passed = sum(1 for e in endpoints_tested if e["ok"])
print("\n" + "=" * 80)
print(f"API EXERCISE SUMMARY: {passed}/{total} endpoints passed")
print("=" * 80)

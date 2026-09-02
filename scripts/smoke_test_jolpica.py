"""Optional live smoke test script for the Jolpica F1 API.

This script tests live connectivity to the real Jolpica F1 API by requesting a small,
known single-race result dataset (2024 Round 1).
It is intended for manual validation and is NOT part of the automated unit test suite.
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.f1.client import JolpicaClient
from app.f1.exceptions import F1APIError


def main():
    print("==================================================")
    print("Jolpica F1 API — Live Smoke Test")
    print("==================================================")

    try:
        with JolpicaClient() as client:
            print("Requesting 2024 Round 1 (Bahrain Grand Prix) results from live API...")
            response = client.get_race_results(season=2024, round_number=1)

            print(f"[SUCCESS] HTTP response received and validated.")
            print(f" - URL retrieved: {response.metadata.url}")
            print(f" - Total classified records: {response.metadata.total}")
            print(f" - Page limit: {response.metadata.limit}, offset: {response.metadata.offset}")

            race_table = response.data.get("RaceTable", {})
            races = race_table.get("Races", [])
            if races:
                race = races[0]
                print(f" - Grand Prix: {race.get('raceName')} ({race.get('date')})")
                print(f" - Circuit: {race.get('Circuit', {}).get('circuitName')}")
                results = race.get("Results", [])
                if results:
                    winner = results[0]
                    driver = winner.get("Driver", {})
                    constructor = winner.get("Constructor", {})
                    print(f" - Winner: {driver.get('givenName')} {driver.get('familyName')} ({constructor.get('name')})")
                    print(f" - Time: {winner.get('Time', {}).get('time')}")
            print("==================================================")
            print("Smoke test completed successfully!")
            print("==================================================")

    except F1APIError as e:
        print(f"[ERROR] Jolpica API client error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error during live smoke test: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

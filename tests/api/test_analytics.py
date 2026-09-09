"""Tests for analytics endpoints: qualifying, pit stops, laps, standings."""


def test_get_qualifying(client):
    """Verify qualifying endpoint returns session order and teammate deltas."""
    response = client.get("/api/races/2024/1/qualifying")
    assert response.status_code == 200
    data = response.json()
    assert "qualifying_order" in data
    assert "teammate_comparisons" in data

    order = data["qualifying_order"]
    assert len(order) == 5
    assert order[0]["driver_id"] == "max_verstappen"
    assert order[0]["position"] == 1
    assert order[0]["q3_time_millis"] == 89179

    comps = data["teammate_comparisons"]
    assert len(comps) == 2  # Red Bull and Ferrari have 2 drivers in quali
    rb = next(c for c in comps if c["constructor_id"] == "red_bull")
    # Verstappen (89179) vs Perez (89537): driver_a is max_verstappen, driver_b is perez
    assert rb["delta_millis"] == -358  # 89179 - 89537


def test_get_pit_stops(client):
    """Verify pit stop endpoint returns driver and constructor aggregations."""
    response = client.get("/api/races/2024/1/pit-stops")
    assert response.status_code == 200
    data = response.json()
    assert "drivers" in data
    assert "constructors" in data

    drivers = data["drivers"]
    ver = next(d for d in drivers if d["driver_id"] == "max_verstappen")
    assert ver["stop_count"] == 2
    assert ver["fastest_stop_millis"] == 23856

    constructors = data["constructors"]
    rb = next(c for c in constructors if c["constructor_id"] == "red_bull")
    assert rb["total_stops"] == 4  # 2 + 2


def test_get_laps(client):
    """Verify laps endpoint returns driver lap time summary."""
    response = client.get("/api/races/2024/1/laps")
    assert response.status_code == 200
    data = response.json()
    assert "laps" in data
    assert len(data["laps"]) == 2  # Verstappen and Leclerc have lap rows

    ver = next(l for l in data["laps"] if l["driver_id"] == "max_verstappen")
    assert ver["lap_count"] == 2
    assert ver["fastest_lap_millis"] == 92608


def test_get_standings(client):
    """Verify standings endpoint returns official persisted standings."""
    response = client.get("/api/races/2024/1/standings")
    assert response.status_code == 200
    data = response.json()
    assert "drivers" in data
    assert "constructors" in data

    drivers = data["drivers"]
    assert len(drivers) == 4
    assert drivers[0]["driver_id"] == "max_verstappen"
    assert drivers[0]["position"] == 1
    assert float(drivers[0]["points"]) == 26.0

    constructors = data["constructors"]
    assert len(constructors) == 2
    assert constructors[0]["constructor_id"] == "red_bull"
    assert constructors[0]["position"] == 1
    assert float(constructors[0]["points"]) == 44.0


def test_analytics_endpoints_not_found(client):
    """Verify 404 behavior for invalid race on all analytics routes."""
    for path in ["qualifying", "pit-stops", "laps", "standings"]:
        res = client.get(f"/api/races/2024/999/{path}")
        assert res.status_code == 404

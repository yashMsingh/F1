"""Tests for race-level API endpoints."""


def test_list_races(client):
    """Verify listing races returns seeded Bahrain race."""
    response = client.get("/api/races")
    assert response.status_code == 200
    races = response.json()
    assert len(races) >= 1
    assert races[0]["season_year"] == 2024
    assert races[0]["round"] == 1
    assert races[0]["race_name"] == "Bahrain Grand Prix"
    assert races[0]["circuit_name"] == "Bahrain International Circuit"


def test_list_races_season_filter(client):
    """Verify season query parameter filters properly."""
    res_2024 = client.get("/api/races?season=2024")
    assert res_2024.status_code == 200
    assert len(res_2024.json()) == 1

    res_1999 = client.get("/api/races?season=1999")
    assert res_1999.status_code == 200
    assert len(res_1999.json()) == 0


def test_get_race_overview(client):
    """Verify race overview returns winner and classification stats."""
    response = client.get("/api/races/2024/1")
    assert response.status_code == 200
    data = response.json()
    assert data["season_year"] == 2024
    assert data["round"] == 1
    assert data["race_name"] == "Bahrain Grand Prix"
    assert data["winner_given_name"] == "Max"
    assert data["winner_family_name"] == "Verstappen"
    assert data["winner_constructor"] == "Red Bull"
    assert data["classified_count"] == 5
    assert data["total_result_count"] == 6


def test_get_race_overview_not_found(client):
    """Verify non-existent race returns 404."""
    response = client.get("/api/races/2024/999")
    assert response.status_code == 404
    assert "Race not found" in response.json()["detail"]


def test_get_race_classification(client):
    """Verify classification and grid vs finish results."""
    response = client.get("/api/races/2024/1/results")
    assert response.status_code == 200
    data = response.json()
    assert "overview" in data
    assert "results" in data
    assert "grid_vs_finish" in data

    assert len(data["results"]) == 6
    assert data["results"][0]["driver_id"] == "max_verstappen"
    assert data["results"][0]["source_position"] == 1

    # Grid vs finish
    gvf = data["grid_vs_finish"]
    assert len(gvf) == 6
    # Perez gained 3 places (P5 to P2)
    per = next(x for x in gvf if x["driver_id"] == "perez")
    assert per["position_change"] == 3


def test_get_race_classification_not_found(client):
    """Verify non-existent race classification returns 404."""
    response = client.get("/api/races/2024/999/results")
    assert response.status_code == 404

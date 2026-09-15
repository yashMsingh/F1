"""Unit tests for the parameterized season slice ingestion runner."""

from unittest.mock import MagicMock, call

import pytest
from sqlalchemy import select

from app.db.models import Race, RaceResult, Season
from app.etl.runners.season_slice import (
    fetch_and_parse_race_weekend,
    ingest_race_weekend_round,
    ingest_season_slice,
)
from app.etl.service import ETLService
from app.etl.types import IngestionStatus
from app.f1.types import APIResponse, PageMetadata


def _make_resp(data: dict, url: str = "https://example.com") -> APIResponse:
    raw = {"MRData": {**data, "limit": "30", "offset": "0", "total": "1", "url": url}}
    return APIResponse(
        metadata=PageMetadata(limit=30, offset=0, total=1, url=url),
        data=data,
        raw=raw,
    )


@pytest.fixture
def mock_slice_client():
    """Mock JolpicaClient that deterministically returns minimal valid payloads for any round."""
    client = MagicMock()

    client.get_seasons.return_value = _make_resp(
        {"SeasonTable": {"Seasons": [{"season": "2024", "url": "https://example.com"}]}}
    )

    def mock_get_page(endpoint: str):
        if "circuits" in endpoint:
            return _make_resp({
                "CircuitTable": {
                    "Circuits": [
                        {
                            "circuitId": "circuit_test",
                            "circuitName": "Test Circuit",
                            "Location": {"locality": "City", "country": "Country"},
                        }
                    ]
                }
            })
        elif "constructors" in endpoint:
            return _make_resp({
                "ConstructorTable": {
                    "Constructors": [{"constructorId": "team_test", "name": "Test Team"}]
                }
            })
        elif "drivers" in endpoint:
            return _make_resp({
                "DriverTable": {
                    "Drivers": [
                        {
                            "driverId": "driver_test",
                            "givenName": "Test",
                            "familyName": "Driver",
                            "dateOfBirth": "1997-01-01",
                        }
                    ]
                }
            })
        else:
            # Race schedule endpoint
            parts = endpoint.split("/")
            s = parts[0]
            r = parts[1]
            return _make_resp({
                "RaceTable": {
                    "Races": [
                        {
                            "season": s,
                            "round": r,
                            "raceName": f"Test GP {r}",
                            "Circuit": {"circuitId": "circuit_test", "circuitName": "Test Circuit"},
                            "date": "2024-03-01",
                        }
                    ]
                }
            })

    client.get_page.side_effect = mock_get_page

    def mock_race_results(s, r):
        return _make_resp({
            "RaceTable": {
                "Races": [
                    {
                        "season": str(s),
                        "round": str(r),
                        "Results": [
                            {
                                "number": "1",
                                "position": "1",
                                "positionText": "1",
                                "points": "25",
                                "Driver": {"driverId": "driver_test", "givenName": "Test", "familyName": "Driver"},
                                "Constructor": {"constructorId": "team_test", "name": "Test Team"},
                                "grid": "1",
                                "laps": "50",
                                "status": "Finished",
                            }
                        ],
                    }
                ]
            }
        })

    client.get_race_results.side_effect = mock_race_results

    def mock_qualifying(s, r):
        return _make_resp({
            "RaceTable": {
                "Races": [
                    {
                        "season": str(s),
                        "round": str(r),
                        "QualifyingResults": [
                            {
                                "number": "1",
                                "position": "1",
                                "Driver": {"driverId": "driver_test"},
                                "Constructor": {"constructorId": "team_test"},
                                "Q1": "1:30.000",
                            }
                        ],
                    }
                ]
            }
        })

    client.get_qualifying_results.side_effect = mock_qualifying
    client.get_sprint_results.return_value = _make_resp({"RaceTable": {"Races": []}})
    client.iter_pages.return_value = iter([])
    client.get_driver_standings.return_value = _make_resp({"StandingsTable": {"StandingsLists": []}})
    client.get_constructor_standings.return_value = _make_resp({"StandingsTable": {"StandingsLists": []}})

    return client


def test_season_slice_invalid_bounds(mock_slice_client, session):
    """Raise ValueError when start_round > end_round."""
    service = ETLService(session=session)
    with pytest.raises(ValueError, match="cannot be greater than end_round"):
        ingest_season_slice(
            client=mock_slice_client,
            service=service,
            season_year=2024,
            start_round=3,
            end_round=2,
        )


def test_fetch_and_parse_race_weekend(mock_slice_client):
    """Validate fetch_and_parse_race_weekend correctly populates domain dictionaries."""
    data = fetch_and_parse_race_weekend(
        client=mock_slice_client,
        season_year=2024,
        round_num=2,
        include_laps=False,
        pace_delay_seconds=0,
    )

    assert data["season"].year == 2024
    assert len(data["circuits"]) == 1
    assert data["circuits"][0].circuit_id == "circuit_test"
    assert len(data["races"]) == 1
    assert data["races"][0].round == 2
    assert len(data["race_results"]) == 1
    assert data["race_results"][0].round == 2
    assert len(data["lap_times"]) == 0  # include_laps was False


def test_ingest_season_slice_multi_round(mock_slice_client, session):
    """Ingesting a slice of multiple rounds persists records for each round."""
    service = ETLService(session=session, auto_commit=False)

    results = ingest_season_slice(
        client=mock_slice_client,
        service=service,
        season_year=2024,
        start_round=1,
        end_round=3,
        include_laps=False,
        pace_delay_seconds=0,
    )

    assert len(results) == 3
    for r in results:
        assert r.status == IngestionStatus.SUCCESS
        assert r.stats.records_inserted > 0

    # Verify races table in DB contains rounds 1, 2, 3
    races = session.scalars(
        select(Race).where(Race.season_year == 2024).order_by(Race.round.asc())
    ).all()
    assert len(races) == 3
    assert [r.round for r in races] == [1, 2, 3]


def test_ingest_season_slice_idempotency(mock_slice_client, session):
    """Running ingestion a second time for the same slice inserts 0 rows."""
    service = ETLService(session=session, auto_commit=False)

    # First run
    res1 = ingest_season_slice(
        client=mock_slice_client,
        service=service,
        season_year=2024,
        start_round=1,
        end_round=2,
        include_laps=False,
        pace_delay_seconds=0,
    )
    assert sum(r.stats.records_inserted for r in res1) > 0

    # Second run
    res2 = ingest_season_slice(
        client=mock_slice_client,
        service=service,
        season_year=2024,
        start_round=1,
        end_round=2,
        include_laps=False,
        pace_delay_seconds=0,
    )
    assert sum(r.stats.records_inserted for r in res2) == 0
    assert sum(r.stats.records_skipped for r in res2) > 0

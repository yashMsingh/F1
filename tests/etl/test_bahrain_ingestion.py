"""Integration and unit tests for controlled 2024 Bahrain GP ingestion."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.db.models import (
    Circuit,
    Constructor,
    ConstructorStanding,
    Driver,
    DriverStanding,
    EtlLog,
    LapTime,
    PitStop,
    QualifyingResult,
    Race,
    RaceResult,
    Season,
    SprintResult,
)
from app.etl.exceptions import F1DependencyError
from app.etl.runners.bahrain_2024 import fetch_and_parse_bahrain_2024, ingest_bahrain_2024
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
def mock_bahrain_client():
    """Mock JolpicaClient that deterministically returns valid Bahrain 2024 API responses."""
    client = MagicMock()

    # 1. Season response
    client.get_seasons.return_value = _make_resp(
        {
            "SeasonTable": {
                "Seasons": [
                    {"season": "2024", "url": "https://en.wikipedia.org/wiki/2024_Formula_One_World_Championship"}
                ]
            }
        },
        url="https://api.jolpi.ca/ergast/f1/seasons.json",
    )

    # 2. Circuits response
    circuits_resp = _make_resp(
        {
            "CircuitTable": {
                "Circuits": [
                    {
                        "circuitId": "bahrain",
                        "circuitName": "Bahrain International Circuit",
                        "Location": {
                            "lat": "26.0325",
                            "long": "50.5106",
                            "locality": "Sakhir",
                            "country": "Bahrain",
                        },
                        "url": "https://en.wikipedia.org/wiki/Bahrain_International_Circuit",
                    }
                ]
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1/circuits.json",
    )

    # 3. Constructors response
    constructors_resp = _make_resp(
        {
            "ConstructorTable": {
                "Constructors": [
                    {"constructorId": "red_bull", "name": "Red Bull", "nationality": "Austrian"},
                    {"constructorId": "ferrari", "name": "Ferrari", "nationality": "Italian"},
                ]
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1/constructors.json",
    )

    # 4. Drivers response
    drivers_resp = _make_resp(
        {
            "DriverTable": {
                "Drivers": [
                    {
                        "driverId": "max_verstappen",
                        "permanentNumber": "33",
                        "code": "VER",
                        "givenName": "Max",
                        "familyName": "Verstappen",
                        "dateOfBirth": "1997-09-30",
                        "nationality": "Dutch",
                    },
                    {
                        "driverId": "leclerc",
                        "permanentNumber": "16",
                        "code": "LEC",
                        "givenName": "Charles",
                        "familyName": "Leclerc",
                        "dateOfBirth": "1997-10-16",
                        "nationality": "Monegasque",
                    },
                ]
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1/drivers.json",
    )

    # 5. Race schedule response
    races_resp = _make_resp(
        {
            "RaceTable": {
                "season": "2024",
                "round": "1",
                "Races": [
                    {
                        "season": "2024",
                        "round": "1",
                        "raceName": "Bahrain Grand Prix",
                        "Circuit": {"circuitId": "bahrain", "circuitName": "Bahrain International Circuit"},
                        "date": "2024-03-02",
                        "time": "15:00:00Z",
                    }
                ],
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1.json",
    )

    # Dispatch get_page calls
    def mock_get_page(endpoint, params=None):
        if "circuits" in endpoint:
            return circuits_resp
        elif "constructors" in endpoint:
            return constructors_resp
        elif "drivers" in endpoint:
            return drivers_resp
        elif endpoint == "2024/1":
            return races_resp
        raise ValueError(f"Unhandled endpoint in mock: {endpoint}")

    client.get_page.side_effect = mock_get_page

    # 6. Race results
    client.get_race_results.return_value = _make_resp(
        {
            "RaceTable": {
                "season": "2024",
                "round": "1",
                "Races": [
                    {
                        "season": "2024",
                        "round": "1",
                        "Results": [
                            {
                                "number": "1",
                                "position": "1",
                                "positionText": "1",
                                "points": "26",
                                "Driver": {"driverId": "max_verstappen"},
                                "Constructor": {"constructorId": "red_bull"},
                                "grid": "1",
                                "laps": "57",
                                "status": "Finished",
                                "Time": {"millis": "5504742", "time": "1:31:44.742"},
                                "FastestLap": {"rank": "1", "lap": "39", "Time": {"time": "1:32.608"}},
                            },
                            {
                                "number": "16",
                                "position": "4",
                                "positionText": "4",
                                "points": "12",
                                "Driver": {"driverId": "leclerc"},
                                "Constructor": {"constructorId": "ferrari"},
                                "grid": "2",
                                "laps": "57",
                                "status": "Finished",
                                "Time": {"millis": "5544440", "time": "+39.698"},
                            },
                        ],
                    }
                ],
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1/results.json",
    )

    # 7. Qualifying results
    client.get_qualifying_results.return_value = _make_resp(
        {
            "RaceTable": {
                "season": "2024",
                "round": "1",
                "Races": [
                    {
                        "season": "2024",
                        "round": "1",
                        "QualifyingResults": [
                            {
                                "number": "1",
                                "position": "1",
                                "Driver": {"driverId": "max_verstappen"},
                                "Constructor": {"constructorId": "red_bull"},
                                "Q1": "1:30.031",
                                "Q2": "1:29.374",
                                "Q3": "1:29.179",
                            }
                        ],
                    }
                ],
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1/qualifying.json",
    )

    # 8. Sprint results (Bahrain had no sprint, empty races list)
    client.get_sprint_results.return_value = _make_resp(
        {"RaceTable": {"season": "2024", "round": "1", "Races": []}},
        url="https://api.jolpi.ca/ergast/f1/2024/1/sprint.json",
    )

    # 9. Pit stops (iter_pages)
    pitstops_page = _make_resp(
        {
            "RaceTable": {
                "season": "2024",
                "round": "1",
                "Races": [
                    {
                        "season": "2024",
                        "round": "1",
                        "PitStops": [
                            {
                                "driverId": "max_verstappen",
                                "stop": "1",
                                "lap": "17",
                                "time": "18:31:18",
                                "duration": "24.123",
                            }
                        ],
                    }
                ],
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1/pitstops.json",
    )

    # 10. Lap times (iter_pages)
    laps_page = _make_resp(
        {
            "RaceTable": {
                "season": "2024",
                "round": "1",
                "Races": [
                    {
                        "season": "2024",
                        "round": "1",
                        "Laps": [
                            {
                                "number": "1",
                                "Timings": [
                                    {"driverId": "max_verstappen", "position": "1", "time": "1:36.415"}
                                ],
                            }
                        ],
                    }
                ],
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1/laps.json",
    )

    def mock_iter_pages(endpoint, page_limit=100):
        if "pitstops" in endpoint:
            yield pitstops_page
        elif "laps" in endpoint:
            yield laps_page

    client.iter_pages.side_effect = mock_iter_pages

    # 11. Standings
    client.get_driver_standings.return_value = _make_resp(
        {
            "StandingsTable": {
                "season": "2024",
                "round": "1",
                "StandingsLists": [
                    {
                        "season": "2024",
                        "round": "1",
                        "DriverStandings": [
                            {
                                "position": "1",
                                "points": "26",
                                "wins": "1",
                                "Driver": {"driverId": "max_verstappen"},
                            }
                        ],
                    }
                ],
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1/driverStandings.json",
    )

    client.get_constructor_standings.return_value = _make_resp(
        {
            "StandingsTable": {
                "season": "2024",
                "round": "1",
                "StandingsLists": [
                    {
                        "season": "2024",
                        "round": "1",
                        "ConstructorStandings": [
                            {
                                "position": "1",
                                "points": "44",
                                "wins": "1",
                                "Constructor": {"constructorId": "red_bull"},
                            }
                        ],
                    }
                ],
            }
        },
        url="https://api.jolpi.ca/ergast/f1/2024/1/constructorStandings.json",
    )

    return client


class TestBahrainIngestion:
    def test_end_to_end_orchestration_and_idempotency(self, session, mock_bahrain_client):
        service = ETLService(session=session, auto_commit=False)

        # ── Run 1: Clean ingestion
        res1 = ingest_bahrain_2024(mock_bahrain_client, service)
        assert res1.status == IngestionStatus.SUCCESS
        assert res1.stats.records_inserted > 0
        assert res1.stats.records_failed == 0

        # Verify DB records
        season = session.scalars(select(Season).where(Season.season_year == 2024)).first()
        assert season is not None

        circuit = session.scalars(select(Circuit).where(Circuit.circuit_id == "bahrain")).first()
        assert circuit is not None

        race = session.scalars(select(Race).where(Race.season_year == 2024, Race.round == 1)).first()
        assert race is not None
        assert race.circuit_id == circuit.id

        results = session.scalars(select(RaceResult).where(RaceResult.race_id == race.id)).all()
        assert len(results) == 2

        # Winner check
        winner = next(r for r in results if r.source_position == 1)
        assert winner.points == 26
        assert winner.fastest_lap_rank == 1

        # Pit stop check
        pitstops = session.scalars(select(PitStop).where(PitStop.race_id == race.id)).all()
        assert len(pitstops) == 1
        assert pitstops[0].duration_millis == 24123

        # Lap times check
        laps = session.scalars(select(LapTime).where(LapTime.race_id == race.id)).all()
        assert len(laps) == 1
        assert laps[0].lap_number == 1
        assert laps[0].time_millis == 96415

        # Sprint check (0 sprint rows)
        sprints = session.scalars(select(SprintResult).where(SprintResult.race_id == race.id)).all()
        assert len(sprints) == 0

        # Standings check
        d_stand = session.scalars(select(DriverStanding).where(DriverStanding.season_year == 2024)).all()
        c_stand = session.scalars(select(ConstructorStanding).where(ConstructorStanding.season_year == 2024)).all()
        assert len(d_stand) == 1
        assert len(c_stand) == 1

        # ETL Log check
        log = session.get(EtlLog, res1.log_id)
        assert log is not None
        assert log.status == IngestionStatus.SUCCESS.value
        assert log.records_inserted == res1.stats.records_inserted

        # ── Run 2: Exact same payload (Idempotency)
        res2 = ingest_bahrain_2024(mock_bahrain_client, service)
        assert res2.status == IngestionStatus.SUCCESS
        assert res2.stats.records_inserted == 0
        assert res2.stats.records_skipped == res1.stats.records_inserted

        # Verify row counts remain unchanged
        assert len(session.scalars(select(RaceResult).where(RaceResult.race_id == race.id)).all()) == 2
        assert len(session.scalars(select(PitStop).where(PitStop.race_id == race.id)).all()) == 1

    def test_missing_dependency_rollback(self, session, mock_bahrain_client):
        # Corrupt the mock so race results point to a non-existent driver
        mock_bahrain_client.get_race_results.return_value = _make_resp(
            {
                "RaceTable": {
                    "season": "2024",
                    "round": "1",
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "Results": [
                                {
                                    "number": "99",
                                    "position": "1",
                                    "positionText": "1",
                                    "points": "25",
                                    "Driver": {"driverId": "unknown_driver"},
                                    "Constructor": {"constructorId": "red_bull"},
                                    "grid": "1",
                                    "laps": "57",
                                    "status": "Finished",
                                }
                            ],
                        }
                    ],
                }
            },
            url="https://api.jolpi.ca/ergast/f1/2024/1/results.json",
        )

        service = ETLService(session=session, auto_commit=False)

        with pytest.raises(F1DependencyError) as exc_info:
            ingest_bahrain_2024(mock_bahrain_client, service)

        assert exc_info.value.missing_entity == "drivers"
        assert exc_info.value.missing_id == "unknown_driver"

        # Verify full transaction rollback: 0 records persisted in database
        assert session.scalar(select(Season.season_year).where(Season.season_year == 2024)) is None
        assert session.scalar(select(Circuit.circuit_id).where(Circuit.circuit_id == "bahrain")) is None
        assert len(session.scalars(select(RaceResult)).all()) == 0

        # Verify FAILED entry logged in etl_log
        failed_logs = session.scalars(select(EtlLog).where(EtlLog.status == IngestionStatus.FAILED.value)).all()
        assert len(failed_logs) == 1
        assert "unknown_driver" in failed_logs[0].error_message

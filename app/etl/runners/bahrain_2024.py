"""Controlled real-data ingestion runner for the 2024 Bahrain Grand Prix (Round 1).

Flow:
    JolpicaClient (app.f1.client)
        ↓
    Parsers (app.f1.parsing.parsers)
        ↓
    ETLService (app.etl.service)
        ↓
    Database Repositories & Models
"""

from __future__ import annotations

import logging
from typing import Any

from app.etl.service import ETLService
from app.etl.types import IngestionResult
from app.f1.client import JolpicaClient
from app.f1.parsing.models import (
    ParsedCircuit,
    ParsedConstructor,
    ParsedConstructorStanding,
    ParsedDriver,
    ParsedDriverStanding,
    ParsedLapTime,
    ParsedPitStop,
    ParsedQualifyingResult,
    ParsedRace,
    ParsedRaceResult,
    ParsedSeason,
    ParsedSprintResult,
)
from app.f1.parsing.parsers import (
    parse_circuits,
    parse_constructor_standings,
    parse_constructors,
    parse_driver_standings,
    parse_drivers,
    parse_lap_times,
    parse_pit_stops,
    parse_qualifying_results,
    parse_race_results,
    parse_races,
    parse_seasons,
    parse_sprint_results,
)

logger = logging.getLogger(__name__)


def fetch_and_parse_bahrain_2024(client: JolpicaClient) -> dict[str, Any]:
    """Retrieve raw 2024 Bahrain GP payloads and parse into typed domain dataclasses.

    Args:
        client: Configured Jolpica API client instance.

    Returns:
        Dictionary containing parsed entities ready for ETL ingestion.
    """
    logger.info("Fetching Season 2024 metadata...")
    season_resp = client.get_seasons(limit=100)
    seasons = parse_seasons(season_resp)
    season_2024 = next((s for s in seasons if s.year == 2024), ParsedSeason(year=2024))

    logger.info("Fetching 2024 Round 1 Circuit...")
    circuit_resp = client.get_page("2024/1/circuits")
    circuits = parse_circuits(circuit_resp)

    logger.info("Fetching 2024 Round 1 Constructors and Drivers...")
    con_resp = client.get_page("2024/1/constructors")
    constructors = parse_constructors(con_resp)

    drv_resp = client.get_page("2024/1/drivers")
    drivers = parse_drivers(drv_resp)

    logger.info("Fetching 2024 Round 1 Race schedule...")
    race_resp = client.get_page("2024/1")
    races = parse_races(race_resp)

    logger.info("Fetching 2024 Round 1 Race results...")
    rr_resp = client.get_race_results(2024, 1)
    race_results = parse_race_results(rr_resp)

    logger.info("Fetching 2024 Round 1 Qualifying results...")
    qr_resp = client.get_qualifying_results(2024, 1)
    qualifying_results = parse_qualifying_results(qr_resp)

    logger.info("Fetching 2024 Round 1 Sprint results (if applicable)...")
    sr_resp = client.get_sprint_results(2024, 1)
    sprint_results = parse_sprint_results(sr_resp)

    logger.info("Fetching 2024 Round 1 Pit stops (paginated)...")
    pit_stops: list[ParsedPitStop] = []
    for page in client.iter_pages("2024/1/pitstops", page_limit=100):
        pit_stops.extend(parse_pit_stops(page))

    logger.info("Fetching 2024 Round 1 Lap times (paginated)...")
    lap_times: list[ParsedLapTime] = []
    for page in client.iter_pages("2024/1/laps", page_limit=100):
        lap_times.extend(parse_lap_times(page))

    logger.info("Fetching 2024 Round 1 Standings...")
    ds_resp = client.get_driver_standings(2024, 1)
    driver_standings = parse_driver_standings(ds_resp)

    cs_resp = client.get_constructor_standings(2024, 1)
    constructor_standings = parse_constructor_standings(cs_resp)

    return {
        "season": season_2024,
        "circuits": circuits,
        "constructors": constructors,
        "drivers": drivers,
        "races": races,
        "race_results": race_results,
        "qualifying_results": qualifying_results,
        "sprint_results": sprint_results,
        "pit_stops": pit_stops,
        "lap_times": lap_times,
        "driver_standings": driver_standings,
        "constructor_standings": constructor_standings,
    }


def ingest_bahrain_2024(client: JolpicaClient, service: ETLService) -> IngestionResult:
    """Execute complete controlled ingestion of 2024 Bahrain GP into the database.

    Args:
        client: Jolpica API client.
        service: Configured ETL persistence service.

    Returns:
        IngestionResult containing execution statistics and status.
    """
    data = fetch_and_parse_bahrain_2024(client)

    return service.ingest_race_weekend(
        season=data["season"],
        circuits=data["circuits"],
        constructors=data["constructors"],
        drivers=data["drivers"],
        races=data["races"],
        race_results=data["race_results"],
        qualifying_results=data["qualifying_results"],
        sprint_results=data["sprint_results"],
        pit_stops=data["pit_stops"],
        lap_times=data["lap_times"],
        driver_standings=data["driver_standings"],
        constructor_standings=data["constructor_standings"],
        endpoint="2024/1",
    )

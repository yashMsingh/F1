"""F1 Race Intelligence — Parameterized Season Slice Ingestion Runner.

Enables controlled, bounded ingestion of multi-race sequences across a season.

Flow for each round:
    JolpicaClient (app.f1.client)
        ↓ (with pace delay)
    Parsers (app.f1.parsing.parsers)
        ↓
    ETLService (app.etl.service)
        ↓
    Database Repositories & Models (Idempotent ON CONFLICT)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

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


def fetch_and_parse_race_weekend(
    client: JolpicaClient,
    season_year: int,
    round_num: int,
    include_laps: bool = True,
    pace_delay_seconds: float = 0.25,
) -> dict[str, Any]:
    """Retrieve raw payloads for a specific Grand Prix and parse into typed domain dataclasses.

    Args:
        client: Configured Jolpica API client instance.
        season_year: Championship season year (e.g. 2024).
        round_num: Grand Prix round number (e.g. 1, 2, 5).
        include_laps: Whether to fetch granular lap times (defaults to True).
        pace_delay_seconds: Polite delay between paginated sub-requests to avoid HTTP 429.

    Returns:
        Dictionary containing parsed domain entities ready for ETL ingestion.
    """
    logger.info("Fetching Season %d metadata...", season_year)
    season_resp = client.get_seasons(limit=100)
    seasons = parse_seasons(season_resp)
    season = next(
        (s for s in seasons if s.year == season_year),
        ParsedSeason(year=season_year),
    )

    if pace_delay_seconds > 0:
        time.sleep(pace_delay_seconds)

    logger.info("Fetching Season %d Round %d Circuit...", season_year, round_num)
    circuit_resp = client.get_page(f"{season_year}/{round_num}/circuits")
    circuits = parse_circuits(circuit_resp)

    if pace_delay_seconds > 0:
        time.sleep(pace_delay_seconds)

    logger.info("Fetching Season %d Round %d Constructors and Drivers...", season_year, round_num)
    con_resp = client.get_page(f"{season_year}/{round_num}/constructors")
    constructors = parse_constructors(con_resp)

    if pace_delay_seconds > 0:
        time.sleep(pace_delay_seconds)

    drv_resp = client.get_page(f"{season_year}/{round_num}/drivers")
    drivers = parse_drivers(drv_resp)

    if pace_delay_seconds > 0:
        time.sleep(pace_delay_seconds)

    logger.info("Fetching Season %d Round %d Race schedule...", season_year, round_num)
    race_resp = client.get_page(f"{season_year}/{round_num}")
    races = parse_races(race_resp)

    if pace_delay_seconds > 0:
        time.sleep(pace_delay_seconds)

    logger.info("Fetching Season %d Round %d Race results...", season_year, round_num)
    rr_resp = client.get_race_results(season_year, round_num)
    race_results = parse_race_results(rr_resp)

    if pace_delay_seconds > 0:
        time.sleep(pace_delay_seconds)

    logger.info("Fetching Season %d Round %d Qualifying results...", season_year, round_num)
    qr_resp = client.get_qualifying_results(season_year, round_num)
    qualifying_results = parse_qualifying_results(qr_resp)

    if pace_delay_seconds > 0:
        time.sleep(pace_delay_seconds)

    logger.info("Fetching Season %d Round %d Sprint results (if applicable)...", season_year, round_num)
    sr_resp = client.get_sprint_results(season_year, round_num)
    sprint_results = parse_sprint_results(sr_resp)

    if pace_delay_seconds > 0:
        time.sleep(pace_delay_seconds)

    logger.info("Fetching Season %d Round %d Pit stops (paginated)...", season_year, round_num)
    pit_stops: list[ParsedPitStop] = []
    for page in client.iter_pages(f"{season_year}/{round_num}/pitstops", page_limit=100):
        pit_stops.extend(parse_pit_stops(page))
        if pace_delay_seconds > 0:
            time.sleep(pace_delay_seconds)

    lap_times: list[ParsedLapTime] = []
    if include_laps:
        logger.info("Fetching Season %d Round %d Lap times (paginated)...", season_year, round_num)
        for page in client.iter_pages(f"{season_year}/{round_num}/laps", page_limit=100):
            lap_times.extend(parse_lap_times(page))
            if pace_delay_seconds > 0:
                time.sleep(pace_delay_seconds)

    logger.info("Fetching Season %d Round %d Standings...", season_year, round_num)
    ds_resp = client.get_driver_standings(season_year, round_num)
    driver_standings = parse_driver_standings(ds_resp)

    if pace_delay_seconds > 0:
        time.sleep(pace_delay_seconds)

    cs_resp = client.get_constructor_standings(season_year, round_num)
    constructor_standings = parse_constructor_standings(cs_resp)

    return {
        "season": season,
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


def ingest_race_weekend_round(
    client: JolpicaClient,
    service: ETLService,
    season_year: int,
    round_num: int,
    include_laps: bool = True,
    pace_delay_seconds: float = 0.25,
) -> IngestionResult:
    """Execute complete controlled ingestion of a single race weekend into the database.

    Args:
        client: Configured Jolpica API client.
        service: Active ETL persistence service.
        season_year: Championship season year.
        round_num: Round number within the season.
        include_laps: Whether to persist lap times.
        pace_delay_seconds: Delay between paginated sub-requests.

    Returns:
        IngestionResult containing execution statistics and status.
    """
    data = fetch_and_parse_race_weekend(
        client=client,
        season_year=season_year,
        round_num=round_num,
        include_laps=include_laps,
        pace_delay_seconds=pace_delay_seconds,
    )

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
        endpoint=f"{season_year}/{round_num}",
    )


def ingest_season_slice(
    client: JolpicaClient,
    service: ETLService,
    season_year: int,
    start_round: int,
    end_round: int,
    include_laps: bool = True,
    pace_delay_seconds: float = 0.25,
) -> list[IngestionResult]:
    """Ingest a contiguous slice of race weekends for a championship season.

    Args:
        client: Configured Jolpica API client.
        service: Active ETL persistence service.
        season_year: Championship season year (e.g. 2024).
        start_round: Inclusive starting round index (e.g. 1).
        end_round: Inclusive ending round index (e.g. 5).
        include_laps: Whether to persist lap times.
        pace_delay_seconds: Pacing delay between API requests.

    Returns:
        List of IngestionResult instances, one per processed round.
    """
    if start_round > end_round:
        raise ValueError(
            f"start_round ({start_round}) cannot be greater than end_round ({end_round})"
        )

    results: list[IngestionResult] = []
    for r in range(start_round, end_round + 1):
        logger.info(">>> Processing Season %d Round %d of %d...", season_year, r, end_round)
        res = ingest_race_weekend_round(
            client=client,
            service=service,
            season_year=season_year,
            round_num=r,
            include_laps=include_laps,
            pace_delay_seconds=pace_delay_seconds,
        )
        results.append(res)
        logger.info(
            "Season %d Round %d completed with status '%s' (inserted=%d, skipped=%d, updated=%d)",
            season_year,
            r,
            res.status.value,
            res.stats.records_inserted,
            res.stats.records_skipped,
            res.stats.records_updated,
        )

    return results

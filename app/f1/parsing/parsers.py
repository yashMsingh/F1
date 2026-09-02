"""F1 Race Intelligence — Jolpica response parsers.

Deterministic parsers that convert raw Jolpica API response dictionaries into
typed domain records.  No network calls, no database writes, no analytics.

Each ``parse_*`` function accepts the ``MRData`` dict (or the full envelope)
returned by the API client and produces a list of the corresponding
``Parsed*`` dataclass instances.

Usage::

    from app.f1.parsing.parsers import parse_race_results
    results: list[ParsedRaceResult] = parse_race_results(api_response_dict)
"""

from __future__ import annotations

import datetime
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from app.f1.parsing.exceptions import (
    F1ParsingError,
    F1StructureError,
    F1ValidationError,
)
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
from app.f1.parsing.time import parse_gap_to_millis, parse_time_to_millis

logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _unwrap_mrdata(payload: Any) -> dict[str, Any]:
    """Extract the ``MRData`` envelope, accepting wrapped, unwrapped, or APIResponse."""
    if hasattr(payload, "data") and isinstance(payload.data, dict):
        payload = payload.data
    if isinstance(payload, dict):
        if "MRData" in payload:
            return payload["MRData"]
        return payload
    raise F1StructureError(
        f"Payload is not a dict or APIResponse, got {type(payload).__name__}",
        expected_key="MRData",
    )


def _require_table(mrdata: dict[str, Any], table_key: str) -> dict[str, Any]:
    """Return the resource table dict, raising if absent."""
    table = mrdata.get(table_key)
    if table is None:
        raise F1StructureError(
            f"Missing '{table_key}' in MRData", expected_key=table_key
        )
    return table


def _require_str(record: dict[str, Any], key: str, context: str = "") -> str:
    """Extract a required non-empty string field."""
    value = record.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        ctx = f" in {context}" if context else ""
        raise F1ValidationError(
            f"Required field '{key}' is missing or empty{ctx}",
            field=key,
        )
    return str(value).strip()


def _optional_str(record: dict[str, Any], key: str) -> Optional[str]:
    """Extract an optional string field — returns None if absent or empty."""
    value = record.get(key)
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _parse_int(value: Optional[str], field: str, context: str = "") -> int:
    """Parse a required string to int."""
    if value is None:
        ctx = f" in {context}" if context else ""
        raise F1ValidationError(
            f"Required integer field '{field}' is missing{ctx}",
            field=field,
        )
    try:
        return int(value)
    except (ValueError, TypeError):
        raise F1ValidationError(
            f"Invalid integer for '{field}': '{value}'",
            field=field,
            value=str(value),
        )


def _optional_int(value: Optional[str], field: str) -> Optional[int]:
    """Parse an optional string to int — returns None if absent."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        raise F1ValidationError(
            f"Invalid integer for '{field}': '{value}'",
            field=field,
            value=str(value),
        )


def _parse_decimal(value: Optional[str], field: str) -> Decimal:
    """Parse a required string to Decimal."""
    if value is None:
        raise F1ValidationError(
            f"Required decimal field '{field}' is missing",
            field=field,
        )
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise F1ValidationError(
            f"Invalid decimal for '{field}': '{value}'",
            field=field,
            value=str(value),
        )


def _optional_decimal(value: Optional[str], field: str) -> Optional[Decimal]:
    """Parse an optional string to Decimal — returns None if absent."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise F1ValidationError(
            f"Invalid decimal for '{field}': '{value}'",
            field=field,
            value=str(value),
        )


def _parse_date(value: Optional[str], field: str) -> datetime.date:
    """Parse an ISO-8601 date string (YYYY-MM-DD)."""
    if value is None:
        raise F1ValidationError(
            f"Required date field '{field}' is missing", field=field
        )
    try:
        return datetime.date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        raise F1ValidationError(
            f"Invalid date for '{field}': '{value}'",
            field=field,
            value=str(value),
        )


def _optional_date(value: Optional[str], field: str) -> Optional[datetime.date]:
    """Parse an optional ISO-8601 date string."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return datetime.date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        raise F1ValidationError(
            f"Invalid date for '{field}': '{value}'",
            field=field,
            value=str(value),
        )


def _parse_time_utc(value: Optional[str]) -> Optional[datetime.time]:
    """Parse a time string like '15:00:00Z' to datetime.time."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    s = value.strip().rstrip("Z")
    try:
        parts = s.split(":")
        if len(parts) == 3:
            return datetime.time(int(parts[0]), int(parts[1]), int(parts[2]))
        elif len(parts) == 2:
            return datetime.time(int(parts[0]), int(parts[1]))
    except (ValueError, TypeError):
        pass
    raise F1ValidationError(
        f"Invalid time string: '{value}'", field="time", value=value
    )


def _safe_time_millis(value: Optional[str], field: str) -> Optional[int]:
    """Parse a time string to millis, converting parse errors to validation errors."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return parse_time_to_millis(value)
    except F1ParsingError:
        raise F1ValidationError(
            f"Invalid time for '{field}': '{value}'",
            field=field,
            value=value,
        )


# ── Parsers ─────────────────────────────────────────────────────────────────


def parse_seasons(payload: dict[str, Any]) -> list[ParsedSeason]:
    """Parse seasons from a SeasonTable response."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "SeasonTable")
    seasons_raw = table.get("Seasons", [])

    results: list[ParsedSeason] = []
    for rec in seasons_raw:
        year = _parse_int(rec.get("season"), "season", context="Season")
        results.append(ParsedSeason(
            year=year,
            url=_optional_str(rec, "url"),
        ))
    return results


def parse_circuits(payload: dict[str, Any]) -> list[ParsedCircuit]:
    """Parse circuits from a CircuitTable response."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "CircuitTable")
    circuits_raw = table.get("Circuits", [])

    results: list[ParsedCircuit] = []
    for rec in circuits_raw:
        circuit_id = _require_str(rec, "circuitId", context="Circuit")
        circuit_name = _require_str(rec, "circuitName", context="Circuit")
        location = rec.get("Location", {})

        results.append(ParsedCircuit(
            circuit_id=circuit_id,
            circuit_name=circuit_name,
            locality=_optional_str(location, "locality"),
            country=_optional_str(location, "country"),
            latitude=_optional_decimal(location.get("lat"), "latitude"),
            longitude=_optional_decimal(location.get("long"), "longitude"),
            url=_optional_str(rec, "url"),
        ))
    return results


def parse_constructors(payload: dict[str, Any]) -> list[ParsedConstructor]:
    """Parse constructors from a ConstructorTable response."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "ConstructorTable")
    constructors_raw = table.get("Constructors", [])

    results: list[ParsedConstructor] = []
    for rec in constructors_raw:
        results.append(ParsedConstructor(
            constructor_id=_require_str(rec, "constructorId", context="Constructor"),
            name=_require_str(rec, "name", context="Constructor"),
            nationality=_optional_str(rec, "nationality"),
            url=_optional_str(rec, "url"),
        ))
    return results


def parse_drivers(payload: dict[str, Any]) -> list[ParsedDriver]:
    """Parse drivers from a DriverTable response."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "DriverTable")
    drivers_raw = table.get("Drivers", [])

    results: list[ParsedDriver] = []
    for rec in drivers_raw:
        results.append(ParsedDriver(
            driver_id=_require_str(rec, "driverId", context="Driver"),
            given_name=_require_str(rec, "givenName", context="Driver"),
            family_name=_require_str(rec, "familyName", context="Driver"),
            permanent_number=_optional_int(rec.get("permanentNumber"), "permanentNumber"),
            code=_optional_str(rec, "code"),
            date_of_birth=_optional_date(rec.get("dateOfBirth"), "dateOfBirth"),
            nationality=_optional_str(rec, "nationality"),
            url=_optional_str(rec, "url"),
        ))
    return results


def parse_races(payload: dict[str, Any]) -> list[ParsedRace]:
    """Parse races from a RaceTable response (schedule/race list)."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "RaceTable")
    races_raw = table.get("Races", [])

    results: list[ParsedRace] = []
    for rec in races_raw:
        season = _parse_int(rec.get("season"), "season", context="Race")
        round_num = _parse_int(rec.get("round"), "round", context="Race")
        race_name = _require_str(rec, "raceName", context="Race")

        circuit_data = rec.get("Circuit", {})
        circuit_id = _require_str(circuit_data, "circuitId", context="Race.Circuit")

        race_date = _parse_date(rec.get("date"), "date")
        race_time = _parse_time_utc(rec.get("time"))

        results.append(ParsedRace(
            season=season,
            round=round_num,
            race_name=race_name,
            circuit_id=circuit_id,
            race_date=race_date,
            race_time=race_time,
            url=_optional_str(rec, "url"),
        ))
    return results


def _parse_result_common(
    rec: dict[str, Any],
    season: int,
    round_num: int,
    context: str,
) -> dict[str, Any]:
    """Extract fields shared between race results and sprint results."""
    driver_data = rec.get("Driver", {})
    constructor_data = rec.get("Constructor", {})

    driver_id = _require_str(driver_data, "driverId", context=f"{context}.Driver")
    constructor_id = _require_str(
        constructor_data, "constructorId", context=f"{context}.Constructor"
    )

    position_text = _require_str(rec, "positionText", context=context)
    status = _require_str(rec, "status", context=context)

    # source_position: parse the numeric position the API provides
    source_position = _optional_int(rec.get("position"), "position")

    car_number = _optional_int(rec.get("number"), "number")
    grid_position = _optional_int(rec.get("grid"), "grid")
    laps_completed = _parse_int(rec.get("laps", "0"), "laps", context=context)
    points = _parse_decimal(rec.get("points", "0"), "points")

    # Finish time
    time_data = rec.get("Time", {})
    time_text = _optional_str(time_data, "time") if time_data else None
    time_millis = _optional_int(
        time_data.get("millis") if time_data else None, "Time.millis"
    )

    # Fastest lap
    fl_data = rec.get("FastestLap", {})
    fastest_lap_rank: Optional[int] = None
    fastest_lap_number: Optional[int] = None
    fastest_lap_time: Optional[str] = None
    fastest_lap_time_millis: Optional[int] = None

    if fl_data:
        fastest_lap_rank = _optional_int(fl_data.get("rank"), "FastestLap.rank")
        fastest_lap_number = _optional_int(fl_data.get("lap"), "FastestLap.lap")
        fl_time_data = fl_data.get("Time", {})
        if fl_time_data:
            fastest_lap_time = _optional_str(fl_time_data, "time")
            fastest_lap_time_millis = _safe_time_millis(fastest_lap_time, "FastestLap.Time.time")

    return {
        "season": season,
        "round": round_num,
        "driver_id": driver_id,
        "constructor_id": constructor_id,
        "source_position": source_position,
        "position_text": position_text,
        "status": status,
        "car_number": car_number,
        "grid_position": grid_position,
        "laps_completed": laps_completed,
        "points": points,
        "time_text": time_text,
        "time_millis": time_millis,
        "fastest_lap_rank": fastest_lap_rank,
        "fastest_lap_number": fastest_lap_number,
        "fastest_lap_time": fastest_lap_time,
        "fastest_lap_time_millis": fastest_lap_time_millis,
    }


def parse_race_results(payload: dict[str, Any]) -> list[ParsedRaceResult]:
    """Parse race results from a RaceTable response containing Results."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "RaceTable")
    races_raw = table.get("Races", [])

    results: list[ParsedRaceResult] = []
    for race in races_raw:
        season = _parse_int(race.get("season"), "season", context="Race")
        round_num = _parse_int(race.get("round"), "round", context="Race")

        results_raw = race.get("Results")
        if results_raw is None:
            raise F1StructureError(
                f"Missing 'Results' in Race (season={season}, round={round_num})",
                expected_key="Results",
            )

        for rec in results_raw:
            common = _parse_result_common(rec, season, round_num, "RaceResult")
            results.append(ParsedRaceResult(**common))

    return results


def parse_qualifying_results(payload: dict[str, Any]) -> list[ParsedQualifyingResult]:
    """Parse qualifying results from a RaceTable response containing QualifyingResults."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "RaceTable")
    races_raw = table.get("Races", [])

    results: list[ParsedQualifyingResult] = []
    for race in races_raw:
        season = _parse_int(race.get("season"), "season", context="Race")
        round_num = _parse_int(race.get("round"), "round", context="Race")

        quali_raw = race.get("QualifyingResults")
        if quali_raw is None:
            raise F1StructureError(
                f"Missing 'QualifyingResults' in Race (season={season}, round={round_num})",
                expected_key="QualifyingResults",
            )

        for rec in quali_raw:
            driver_data = rec.get("Driver", {})
            constructor_data = rec.get("Constructor", {})

            driver_id = _require_str(driver_data, "driverId", context="QualifyingResult.Driver")
            constructor_id = _require_str(
                constructor_data, "constructorId", context="QualifyingResult.Constructor"
            )

            position = _parse_int(rec.get("position"), "position", context="QualifyingResult")
            car_number = _optional_int(rec.get("number"), "number")

            # Q1, Q2, Q3 — each optional, preserving raw string + parsed millis
            q1_time = _optional_str(rec, "Q1")
            q1_millis = _safe_time_millis(q1_time, "Q1")
            q2_time = _optional_str(rec, "Q2")
            q2_millis = _safe_time_millis(q2_time, "Q2")
            q3_time = _optional_str(rec, "Q3")
            q3_millis = _safe_time_millis(q3_time, "Q3")

            results.append(ParsedQualifyingResult(
                season=season,
                round=round_num,
                driver_id=driver_id,
                constructor_id=constructor_id,
                position=position,
                car_number=car_number,
                q1_time=q1_time,
                q1_time_millis=q1_millis,
                q2_time=q2_time,
                q2_time_millis=q2_millis,
                q3_time=q3_time,
                q3_time_millis=q3_millis,
            ))

    return results


def parse_sprint_results(payload: dict[str, Any]) -> list[ParsedSprintResult]:
    """Parse sprint results from a RaceTable response containing SprintResults."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "RaceTable")
    races_raw = table.get("Races", [])

    results: list[ParsedSprintResult] = []
    for race in races_raw:
        season = _parse_int(race.get("season"), "season", context="Race")
        round_num = _parse_int(race.get("round"), "round", context="Race")

        sprint_raw = race.get("SprintResults")
        if sprint_raw is None:
            raise F1StructureError(
                f"Missing 'SprintResults' in Race (season={season}, round={round_num})",
                expected_key="SprintResults",
            )

        for rec in sprint_raw:
            common = _parse_result_common(rec, season, round_num, "SprintResult")
            results.append(ParsedSprintResult(**common))

    return results


def parse_pit_stops(payload: dict[str, Any]) -> list[ParsedPitStop]:
    """Parse pit stops from a RaceTable response containing PitStops."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "RaceTable")
    races_raw = table.get("Races", [])

    results: list[ParsedPitStop] = []
    for race in races_raw:
        season = _parse_int(race.get("season"), "season", context="Race")
        round_num = _parse_int(race.get("round"), "round", context="Race")

        pitstops_raw = race.get("PitStops")
        if pitstops_raw is None:
            raise F1StructureError(
                f"Missing 'PitStops' in Race (season={season}, round={round_num})",
                expected_key="PitStops",
            )

        for rec in pitstops_raw:
            driver_id = _require_str(rec, "driverId", context="PitStop")
            stop_number = _parse_int(rec.get("stop"), "stop", context="PitStop")
            lap = _parse_int(rec.get("lap"), "lap", context="PitStop")

            if stop_number < 1:
                raise F1ValidationError(
                    f"Stop number must be positive, got {stop_number}",
                    field="stop",
                    value=str(stop_number),
                )
            if lap < 0:
                raise F1ValidationError(
                    f"Lap number must be non-negative, got {lap}",
                    field="lap",
                    value=str(lap),
                )

            time_of_day = _optional_str(rec, "time")
            duration_text = _optional_str(rec, "duration")
            duration_millis = _safe_time_millis(duration_text, "duration")

            results.append(ParsedPitStop(
                season=season,
                round=round_num,
                driver_id=driver_id,
                stop_number=stop_number,
                lap=lap,
                time_of_day=time_of_day,
                duration_text=duration_text,
                duration_millis=duration_millis,
            ))

    return results


def parse_lap_times(payload: dict[str, Any]) -> list[ParsedLapTime]:
    """Parse lap times from a RaceTable response containing Laps/Timings."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "RaceTable")
    races_raw = table.get("Races", [])

    results: list[ParsedLapTime] = []
    for race in races_raw:
        season = _parse_int(race.get("season"), "season", context="Race")
        round_num = _parse_int(race.get("round"), "round", context="Race")

        laps_raw = race.get("Laps")
        if laps_raw is None:
            raise F1StructureError(
                f"Missing 'Laps' in Race (season={season}, round={round_num})",
                expected_key="Laps",
            )

        for lap_rec in laps_raw:
            lap_number = _parse_int(
                lap_rec.get("number"), "number", context="Lap"
            )
            if lap_number < 1:
                raise F1ValidationError(
                    f"Lap number must be positive, got {lap_number}",
                    field="number",
                    value=str(lap_number),
                )

            timings = lap_rec.get("Timings", [])
            for timing in timings:
                driver_id = _require_str(timing, "driverId", context="Timing")
                position = _parse_int(
                    timing.get("position"), "position", context="Timing"
                )

                time_str = _optional_str(timing, "time")
                time_millis = _safe_time_millis(time_str, "time")

                results.append(ParsedLapTime(
                    season=season,
                    round=round_num,
                    driver_id=driver_id,
                    lap_number=lap_number,
                    position=position,
                    time=time_str,
                    time_millis=time_millis,
                ))

    return results


def parse_driver_standings(payload: dict[str, Any]) -> list[ParsedDriverStanding]:
    """Parse driver standings from a StandingsTable response."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "StandingsTable")
    standings_lists = table.get("StandingsLists", [])

    results: list[ParsedDriverStanding] = []
    for standings_list in standings_lists:
        season = _parse_int(
            standings_list.get("season"), "season", context="StandingsList"
        )
        round_num = _parse_int(
            standings_list.get("round"), "round", context="StandingsList"
        )

        driver_standings = standings_list.get("DriverStandings")
        if driver_standings is None:
            raise F1StructureError(
                f"Missing 'DriverStandings' in StandingsList (season={season}, round={round_num})",
                expected_key="DriverStandings",
            )

        for rec in driver_standings:
            driver_data = rec.get("Driver", {})
            driver_id = _require_str(
                driver_data, "driverId", context="DriverStanding.Driver"
            )
            position = _parse_int(
                rec.get("position"), "position", context="DriverStanding"
            )
            points = _parse_decimal(rec.get("points", "0"), "points")
            wins = _parse_int(rec.get("wins", "0"), "wins", context="DriverStanding")

            results.append(ParsedDriverStanding(
                season=season,
                round=round_num,
                driver_id=driver_id,
                position=position,
                points=points,
                wins=wins,
            ))

    return results


def parse_constructor_standings(
    payload: dict[str, Any],
) -> list[ParsedConstructorStanding]:
    """Parse constructor standings from a StandingsTable response."""
    mrdata = _unwrap_mrdata(payload)
    table = _require_table(mrdata, "StandingsTable")
    standings_lists = table.get("StandingsLists", [])

    results: list[ParsedConstructorStanding] = []
    for standings_list in standings_lists:
        season = _parse_int(
            standings_list.get("season"), "season", context="StandingsList"
        )
        round_num = _parse_int(
            standings_list.get("round"), "round", context="StandingsList"
        )

        constructor_standings = standings_list.get("ConstructorStandings")
        if constructor_standings is None:
            raise F1StructureError(
                f"Missing 'ConstructorStandings' in StandingsList "
                f"(season={season}, round={round_num})",
                expected_key="ConstructorStandings",
            )

        for rec in constructor_standings:
            constructor_data = rec.get("Constructor", {})
            constructor_id = _require_str(
                constructor_data, "constructorId",
                context="ConstructorStanding.Constructor",
            )
            position = _parse_int(
                rec.get("position"), "position", context="ConstructorStanding"
            )
            points = _parse_decimal(rec.get("points", "0"), "points")
            wins = _parse_int(
                rec.get("wins", "0"), "wins", context="ConstructorStanding"
            )

            results.append(ParsedConstructorStanding(
                season=season,
                round=round_num,
                constructor_id=constructor_id,
                position=position,
                points=points,
                wins=wins,
            ))

    return results

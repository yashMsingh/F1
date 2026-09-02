"""F1 Race Intelligence — Parsing, validation, and time transformation layer."""

from app.f1.parsing.exceptions import (
    F1ParsingError,
    F1StructureError,
    F1TimeParsingError,
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
from app.f1.parsing.time import (
    parse_gap_to_millis,
    parse_time_to_millis,
)

__all__ = [
    # Exceptions
    "F1ParsingError",
    "F1ValidationError",
    "F1TimeParsingError",
    "F1StructureError",
    # Time
    "parse_time_to_millis",
    "parse_gap_to_millis",
    # Models
    "ParsedSeason",
    "ParsedCircuit",
    "ParsedConstructor",
    "ParsedDriver",
    "ParsedRace",
    "ParsedRaceResult",
    "ParsedQualifyingResult",
    "ParsedSprintResult",
    "ParsedPitStop",
    "ParsedLapTime",
    "ParsedDriverStanding",
    "ParsedConstructorStanding",
    # Parsers
    "parse_seasons",
    "parse_circuits",
    "parse_constructors",
    "parse_drivers",
    "parse_races",
    "parse_race_results",
    "parse_qualifying_results",
    "parse_sprint_results",
    "parse_pit_stops",
    "parse_lap_times",
    "parse_driver_standings",
    "parse_constructor_standings",
]

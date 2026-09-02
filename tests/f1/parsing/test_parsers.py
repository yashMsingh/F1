"""Comprehensive unit tests for all 12 Jolpica resource parsers."""

from datetime import date, time
from decimal import Decimal

import pytest

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
from app.f1.types import APIResponse, PageMetadata
from tests.f1.fixtures import (
    SAMPLE_CIRCUITS_PAYLOAD,
    SAMPLE_CONSTRUCTOR_STANDINGS_PAYLOAD,
    SAMPLE_DRIVER_STANDINGS_PAYLOAD,
    SAMPLE_LAPS_PAGE_1,
    SAMPLE_PITSTOPS_PAGE_1,
    SAMPLE_QUALIFYING_PAYLOAD,
    SAMPLE_RACE_RESULTS_PAYLOAD,
    SAMPLE_SPRINT_PAYLOAD,
)


# ── Season parser tests ──────────────────────────────────────────────────────


class TestParseSeasons:
    def test_parse_valid_seasons(self):
        payload = {
            "MRData": {
                "SeasonTable": {
                    "Seasons": [
                        {"season": "2023", "url": "https://en.wikipedia.org/wiki/2023_Formula_One_World_Championship"},
                        {"season": "2024", "url": "https://en.wikipedia.org/wiki/2024_Formula_One_World_Championship"},
                    ]
                }
            }
        }
        seasons = parse_seasons(payload)
        assert len(seasons) == 2
        assert seasons[0] == ParsedSeason(year=2023, url="https://en.wikipedia.org/wiki/2023_Formula_One_World_Championship")
        assert seasons[1] == ParsedSeason(year=2024, url="https://en.wikipedia.org/wiki/2024_Formula_One_World_Championship")

    def test_missing_table_raises_structure_error(self):
        with pytest.raises(F1StructureError) as exc_info:
            parse_seasons({"MRData": {}})
        assert exc_info.value.expected_key == "SeasonTable"

    def test_malformed_season_year_raises_validation_error(self):
        payload = {"MRData": {"SeasonTable": {"Seasons": [{"season": "two-thousand"}]}}}
        with pytest.raises(F1ValidationError):
            parse_seasons(payload)


# ── Circuit parser tests ────────────────────────────────────────────────────


class TestParseCircuits:
    def test_parse_valid_circuits(self):
        circuits = parse_circuits(SAMPLE_CIRCUITS_PAYLOAD)
        assert len(circuits) == 1
        c = circuits[0]
        assert isinstance(c, ParsedCircuit)
        assert c.circuit_id == "albert_park"
        assert c.circuit_name == "Albert Park Grand Prix Circuit"
        assert c.locality == "Melbourne"
        assert c.country == "Australia"
        assert c.latitude is None  # not in fixture
        assert c.longitude is None

    def test_coordinates_parsed_as_decimal(self):
        payload = {
            "MRData": {
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
                        }
                    ]
                }
            }
        }
        circuits = parse_circuits(payload)
        assert circuits[0].latitude == Decimal("26.0325")
        assert circuits[0].longitude == Decimal("50.5106")

    def test_missing_circuit_id_raises_validation_error(self):
        payload = {
            "MRData": {
                "CircuitTable": {
                    "Circuits": [{"circuitName": "Unnamed Track"}]
                }
            }
        }
        with pytest.raises(F1ValidationError):
            parse_circuits(payload)


# ── Constructor parser tests ────────────────────────────────────────────────


class TestParseConstructors:
    def test_parse_valid_constructors(self):
        payload = {
            "MRData": {
                "ConstructorTable": {
                    "Constructors": [
                        {
                            "constructorId": "mclaren",
                            "name": "McLaren",
                            "nationality": "British",
                            "url": "https://en.wikipedia.org/wiki/McLaren",
                        }
                    ]
                }
            }
        }
        constructors = parse_constructors(payload)
        assert len(constructors) == 1
        c = constructors[0]
        assert isinstance(c, ParsedConstructor)
        assert c.constructor_id == "mclaren"
        assert c.name == "McLaren"
        assert c.nationality == "British"

    def test_missing_name_raises_validation_error(self):
        payload = {
            "MRData": {
                "ConstructorTable": {
                    "Constructors": [{"constructorId": "ghost_team", "name": ""}]
                }
            }
        }
        with pytest.raises(F1ValidationError):
            parse_constructors(payload)


# ── Driver parser tests ─────────────────────────────────────────────────────


class TestParseDrivers:
    def test_parse_valid_drivers(self):
        payload = {
            "MRData": {
                "DriverTable": {
                    "Drivers": [
                        {
                            "driverId": "norris",
                            "permanentNumber": "4",
                            "code": "NOR",
                            "givenName": "Lando",
                            "familyName": "Norris",
                            "dateOfBirth": "1999-11-13",
                            "nationality": "British",
                            "url": "https://en.wikipedia.org/wiki/Lando_Norris",
                        }
                    ]
                }
            }
        }
        drivers = parse_drivers(payload)
        assert len(drivers) == 1
        d = drivers[0]
        assert isinstance(d, ParsedDriver)
        assert d.driver_id == "norris"
        assert d.permanent_number == 4
        assert d.code == "NOR"
        assert d.given_name == "Lando"
        assert d.family_name == "Norris"
        assert d.date_of_birth == date(1999, 11, 13)
        assert d.nationality == "British"

    def test_optional_driver_fields_handled(self):
        payload = {
            "MRData": {
                "DriverTable": {
                    "Drivers": [
                        {
                            "driverId": "historical_driver",
                            "givenName": "Old",
                            "familyName": "Driver",
                        }
                    ]
                }
            }
        }
        drivers = parse_drivers(payload)
        d = drivers[0]
        assert d.permanent_number is None
        assert d.code is None
        assert d.date_of_birth is None
        assert d.nationality is None


# ── Race schedule parser tests ──────────────────────────────────────────────


class TestParseRaces:
    def test_parse_valid_race_schedule(self):
        payload = {
            "MRData": {
                "RaceTable": {
                    "season": "2024",
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "raceName": "Bahrain Grand Prix",
                            "Circuit": {"circuitId": "bahrain"},
                            "date": "2024-03-02",
                            "time": "15:00:00Z",
                            "url": "https://en.wikipedia.org/wiki/2024_Bahrain_Grand_Prix",
                        }
                    ],
                }
            }
        }
        races = parse_races(payload)
        assert len(races) == 1
        r = races[0]
        assert isinstance(r, ParsedRace)
        assert r.season == 2024
        assert r.round == 1
        assert r.race_name == "Bahrain Grand Prix"
        assert r.circuit_id == "bahrain"
        assert r.race_date == date(2024, 3, 2)
        assert r.race_time == time(15, 0, 0)

    def test_missing_date_raises_validation_error(self):
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "raceName": "TBD GP",
                            "Circuit": {"circuitId": "bahrain"},
                        }
                    ]
                }
            }
        }
        with pytest.raises(F1ValidationError):
            parse_races(payload)


# ── Race results parser tests ───────────────────────────────────────────────


class TestParseRaceResults:
    def test_parse_sample_payload(self):
        results = parse_race_results(SAMPLE_RACE_RESULTS_PAYLOAD)
        assert len(results) == 2

        # Winner: Max Verstappen
        r1 = results[0]
        assert isinstance(r1, ParsedRaceResult)
        assert r1.season == 2024
        assert r1.round == 1
        assert r1.driver_id == "max_verstappen"
        assert r1.constructor_id == "red_bull"
        assert r1.car_number == 1
        assert r1.grid_position == 1
        assert r1.source_position == 1
        assert r1.position_text == "1"
        assert r1.points == Decimal("26")
        assert r1.laps_completed == 57
        assert r1.status == "Finished"
        assert r1.time_millis == 5504742
        assert r1.time_text == "1:31:44.742"
        assert r1.fastest_lap_rank == 1
        assert r1.fastest_lap_number == 39
        assert r1.fastest_lap_time == "1:32.608"
        assert r1.fastest_lap_time_millis == 92608

        # Second place: Sergio Perez
        r2 = results[1]
        assert r2.driver_id == "perez"
        assert r2.source_position == 2
        assert r2.position_text == "2"
        assert r2.points == Decimal("18")
        assert r2.time_text == "+22.457"
        assert r2.fastest_lap_rank is None  # no FastestLap in fixture for Perez

    def test_retired_dnf_preserves_source_position(self):
        """CRITICAL: DNF drivers have positionText='R', status='Engine', but position='18'.

        The parser MUST preserve source_position=18 and NOT overwrite with None.
        """
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "Results": [
                                {
                                    "number": "2",
                                    "position": "18",
                                    "positionText": "R",
                                    "points": "0",
                                    "Driver": {"driverId": "sargeant"},
                                    "Constructor": {"constructorId": "williams"},
                                    "grid": "18",
                                    "laps": "24",
                                    "status": "Engine",
                                }
                            ],
                        }
                    ]
                }
            }
        }
        results = parse_race_results(payload)
        r = results[0]
        assert r.source_position == 18
        assert r.position_text == "R"
        assert r.status == "Engine"
        assert r.points == Decimal("0")
        assert r.time_text is None
        assert r.time_millis is None

    def test_lapped_result_preserves_status(self):
        """Drivers who finished laps down: status='+1 Lap' or '+2 Laps'."""
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "Results": [
                                {
                                    "number": "24",
                                    "position": "15",
                                    "positionText": "15",
                                    "points": "0",
                                    "Driver": {"driverId": "zhou"},
                                    "Constructor": {"constructorId": "sauber"},
                                    "grid": "17",
                                    "laps": "56",
                                    "status": "+1 Lap",
                                }
                            ],
                        }
                    ]
                }
            }
        }
        results = parse_race_results(payload)
        r = results[0]
        assert r.source_position == 15
        assert r.position_text == "15"
        assert r.status == "+1 Lap"

    def test_disqualified_result_preserves_status(self):
        """Disqualified drivers: positionText='D', status='Disqualified'."""
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "Results": [
                                {
                                    "number": "44",
                                    "position": "20",
                                    "positionText": "D",
                                    "points": "0",
                                    "Driver": {"driverId": "hamilton"},
                                    "Constructor": {"constructorId": "mercedes"},
                                    "grid": "3",
                                    "laps": "56",
                                    "status": "Disqualified",
                                }
                            ],
                        }
                    ]
                }
            }
        }
        results = parse_race_results(payload)
        r = results[0]
        assert r.source_position == 20
        assert r.position_text == "D"
        assert r.status == "Disqualified"

    def test_missing_results_key_raises_structure_error(self):
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [{"season": "2024", "round": "1"}]
                }
            }
        }
        with pytest.raises(F1StructureError) as exc_info:
            parse_race_results(payload)
        assert exc_info.value.expected_key == "Results"

    def test_accepts_api_response_wrapper(self):
        """The parser should work with APIResponse object from client.py."""
        resp = APIResponse(
            metadata=PageMetadata(
                limit=30,
                offset=0,
                total=2,
                url="https://api.jolpi.ca/ergast/f1/2024/1/results.json",
            ),
            data=SAMPLE_RACE_RESULTS_PAYLOAD["MRData"],
            raw=SAMPLE_RACE_RESULTS_PAYLOAD["MRData"],
        )
        results = parse_race_results(resp)
        assert len(results) == 2


# ── Qualifying results parser tests ─────────────────────────────────────────


class TestParseQualifyingResults:
    def test_parse_sample_payload(self):
        results = parse_qualifying_results(SAMPLE_QUALIFYING_PAYLOAD)
        assert len(results) == 1
        q = results[0]
        assert isinstance(q, ParsedQualifyingResult)
        assert q.season == 2024
        assert q.round == 1
        assert q.driver_id == "max_verstappen"
        assert q.constructor_id == "red_bull"
        assert q.position == 1
        assert q.car_number == 1
        assert q.q1_time == "1:30.031"
        assert q.q1_time_millis == 90031
        assert q.q2_time == "1:29.374"
        assert q.q2_time_millis == 89374
        assert q.q3_time == "1:29.179"
        assert q.q3_time_millis == 89179

    def test_q1_only_eliminated_driver(self):
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "QualifyingResults": [
                                {
                                    "number": "2",
                                    "position": "18",
                                    "Driver": {"driverId": "sargeant"},
                                    "Constructor": {"constructorId": "williams"},
                                    "Q1": "1:31.750",
                                }
                            ],
                        }
                    ]
                }
            }
        }
        results = parse_qualifying_results(payload)
        q = results[0]
        assert q.position == 18
        assert q.q1_time == "1:31.750"
        assert q.q1_time_millis == 91750
        assert q.q2_time is None
        assert q.q2_time_millis is None
        assert q.q3_time is None
        assert q.q3_time_millis is None


# ── Sprint results parser tests ─────────────────────────────────────────────


class TestParseSprintResults:
    def test_parse_sample_payload(self):
        results = parse_sprint_results(SAMPLE_SPRINT_PAYLOAD)
        assert len(results) == 1
        s = results[0]
        assert isinstance(s, ParsedSprintResult)
        assert s.season == 2024
        assert s.round == 5
        assert s.driver_id == "max_verstappen"
        assert s.constructor_id == "red_bull"
        assert s.source_position == 1
        assert s.position_text == "1"
        assert s.points == Decimal("8")
        assert s.grid_position == 4
        assert s.laps_completed == 19
        assert s.status == "Finished"


# ── Pit stops parser tests ──────────────────────────────────────────────────


class TestParsePitStops:
    def test_parse_sample_payload(self):
        stops = parse_pit_stops(SAMPLE_PITSTOPS_PAGE_1)
        assert len(stops) == 2

        s1 = stops[0]
        assert isinstance(s1, ParsedPitStop)
        assert s1.season == 2024
        assert s1.round == 1
        assert s1.driver_id == "sainz"
        assert s1.stop_number == 1
        assert s1.lap == 14
        assert s1.time_of_day == "15:25:30"
        assert s1.duration_text == "24.123"
        assert s1.duration_millis == 24123

    def test_multi_minute_duration_preserved_and_converted(self):
        """CRITICAL: '40:55.302' must parse to 2455302 ms, NOT 40.553 seconds."""
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "PitStops": [
                                {
                                    "driverId": "alonso",
                                    "stop": "1",
                                    "lap": "20",
                                    "time": "16:00:00",
                                    "duration": "40:55.302",
                                }
                            ],
                        }
                    ]
                }
            }
        }
        stops = parse_pit_stops(payload)
        s = stops[0]
        assert s.duration_text == "40:55.302"
        assert s.duration_millis == 2455302

    def test_invalid_stop_number_raises_validation_error(self):
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "PitStops": [
                                {
                                    "driverId": "sainz",
                                    "stop": "0",  # invalid: must be >= 1
                                    "lap": "14",
                                }
                            ],
                        }
                    ]
                }
            }
        }
        with pytest.raises(F1ValidationError):
            parse_pit_stops(payload)


# ── Lap times parser tests ──────────────────────────────────────────────────


class TestParseLapTimes:
    def test_parse_sample_payload(self):
        laps = parse_lap_times(SAMPLE_LAPS_PAGE_1)
        assert len(laps) == 2

        l1 = laps[0]
        assert isinstance(l1, ParsedLapTime)
        assert l1.season == 2024
        assert l1.round == 1
        assert l1.driver_id == "max_verstappen"
        assert l1.lap_number == 1
        assert l1.position == 1
        assert l1.time == "1:36.415"
        assert l1.time_millis == 96415

        l2 = laps[1]
        assert l2.driver_id == "leclerc"
        assert l2.lap_number == 1
        assert l2.position == 2
        assert l2.time == "1:37.520"
        assert l2.time_millis == 97520

    def test_invalid_lap_number_raises_validation_error(self):
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "Laps": [
                                {
                                    "number": "0",  # invalid: must be >= 1
                                    "Timings": [{"driverId": "verstappen", "position": "1", "time": "1:35.000"}],
                                }
                            ],
                        }
                    ]
                }
            }
        }
        with pytest.raises(F1ValidationError):
            parse_lap_times(payload)


# ── Standings parser tests ──────────────────────────────────────────────────


class TestParseStandings:
    def test_parse_driver_standings(self):
        standings = parse_driver_standings(SAMPLE_DRIVER_STANDINGS_PAYLOAD)
        assert len(standings) == 1
        s = standings[0]
        assert isinstance(s, ParsedDriverStanding)
        assert s.season == 2024
        assert s.round == 1
        assert s.driver_id == "max_verstappen"
        assert s.position == 1
        assert s.points == Decimal("26")
        assert s.wins == 1

    def test_parse_constructor_standings(self):
        standings = parse_constructor_standings(SAMPLE_CONSTRUCTOR_STANDINGS_PAYLOAD)
        assert len(standings) == 1
        s = standings[0]
        assert isinstance(s, ParsedConstructorStanding)
        assert s.season == 2024
        assert s.round == 1
        assert s.constructor_id == "red_bull"
        assert s.position == 1
        assert s.points == Decimal("44")
        assert s.wins == 1


# ── Structural error tests ──────────────────────────────────────────────────


class TestStructureErrors:
    def test_non_dict_payload_raises_structure_error(self):
        with pytest.raises(F1StructureError):
            parse_seasons(["not", "a", "dict"])  # type: ignore

    def test_missing_resource_table_raises_structure_error(self):
        with pytest.raises(F1StructureError) as exc_info:
            parse_drivers({"MRData": {"limit": "30"}})
        assert exc_info.value.expected_key == "DriverTable"

    def test_empty_dict_without_expected_table_raises_structure_error(self):
        with pytest.raises(F1StructureError):
            parse_circuits({})

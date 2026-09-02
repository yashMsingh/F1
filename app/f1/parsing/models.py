"""F1 Race Intelligence — Typed domain records for parsed Jolpica data.

These dataclasses are the output of the parsing layer. They are independent
of SQLAlchemy models and represent the validated, normalized form of raw
Jolpica API responses.

Naming conventions:
  - Fields named *_text preserve the exact raw source string.
  - Fields named *_millis are derived integer millisecond values.
  - Fields using Jolpica slugs (driver_id, constructor_id, circuit_id) are the
    API identifier strings, NOT database integer PKs. FK resolution is the
    responsibility of the ETL layer.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


# ── Reference entities ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ParsedSeason:
    """A single F1 season (year)."""

    year: int
    url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ParsedCircuit:
    """A racing circuit."""

    circuit_id: str           # Jolpica slug, e.g. "bahrain"
    circuit_name: str
    locality: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ParsedConstructor:
    """A constructor / team."""

    constructor_id: str       # Jolpica slug, e.g. "red_bull"
    name: str
    nationality: Optional[str] = None
    url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ParsedDriver:
    """A driver (identity only — not bound to a specific constructor)."""

    driver_id: str            # Jolpica slug, e.g. "max_verstappen"
    given_name: str
    family_name: str
    permanent_number: Optional[int] = None
    code: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None
    nationality: Optional[str] = None
    url: Optional[str] = None


# ── Event entities ──────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ParsedRace:
    """A race weekend event."""

    season: int
    round: int
    race_name: str
    circuit_id: str           # Jolpica slug
    race_date: datetime.date
    race_time: Optional[datetime.time] = None
    url: Optional[str] = None


# ── Result entities ─────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ParsedRaceResult:
    """A single driver's race result — preserves all source values."""

    # Context
    season: int
    round: int
    driver_id: str            # Jolpica slug
    constructor_id: str       # Jolpica slug

    # Source position (preserved as the API gives it)
    source_position: Optional[int]
    position_text: str        # "1", "R", "D", "W", "N", "F", etc.
    status: str               # "Finished", "Engine", "+1 Lap", etc.

    # Race data
    car_number: Optional[int]
    grid_position: Optional[int]
    laps_completed: int
    points: Decimal

    # Finish time (raw + parsed)
    time_text: Optional[str] = None        # "1:31:44.742", "+22.457", None
    time_millis: Optional[int] = None      # from Time.millis (leader absolute ms)

    # Fastest lap (raw + parsed)
    fastest_lap_rank: Optional[int] = None
    fastest_lap_number: Optional[int] = None
    fastest_lap_time: Optional[str] = None         # raw "1:32.608"
    fastest_lap_time_millis: Optional[int] = None   # 92608


@dataclass(frozen=True, slots=True)
class ParsedQualifyingResult:
    """A single driver's qualifying result — preserves raw session times."""

    # Context
    season: int
    round: int
    driver_id: str
    constructor_id: str

    # Position / number
    position: int
    car_number: Optional[int]

    # Session times (raw + parsed)
    q1_time: Optional[str] = None
    q1_time_millis: Optional[int] = None
    q2_time: Optional[str] = None
    q2_time_millis: Optional[int] = None
    q3_time: Optional[str] = None
    q3_time_millis: Optional[int] = None


@dataclass(frozen=True, slots=True)
class ParsedSprintResult:
    """A single driver's sprint race result."""

    # Context
    season: int
    round: int
    driver_id: str
    constructor_id: str

    # Source position (preserved)
    source_position: Optional[int]
    position_text: str
    status: str

    # Race data
    car_number: Optional[int]
    grid_position: Optional[int]
    laps_completed: int
    points: Decimal

    # Finish time
    time_text: Optional[str] = None
    time_millis: Optional[int] = None

    # Fastest lap
    fastest_lap_rank: Optional[int] = None
    fastest_lap_number: Optional[int] = None
    fastest_lap_time: Optional[str] = None
    fastest_lap_time_millis: Optional[int] = None


# ── Operational entities ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ParsedPitStop:
    """A single pit stop — preserves raw duration string."""

    season: int
    round: int
    driver_id: str            # Jolpica slug
    stop_number: int
    lap: int
    time_of_day: Optional[str] = None     # "15:25:30"
    duration_text: Optional[str] = None   # raw "24.123" or "40:55.302"
    duration_millis: Optional[int] = None  # parsed milliseconds


@dataclass(frozen=True, slots=True)
class ParsedLapTime:
    """A single lap timing record — preserves raw time string."""

    season: int
    round: int
    driver_id: str
    lap_number: int
    position: int
    time: Optional[str] = None            # raw "1:22.167"
    time_millis: Optional[int] = None     # 82167


# ── Standings entities ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ParsedDriverStanding:
    """A driver's championship standing at a specific round."""

    season: int
    round: int
    driver_id: str
    position: int
    points: Decimal
    wins: int


@dataclass(frozen=True, slots=True)
class ParsedConstructorStanding:
    """A constructor's championship standing at a specific round."""

    season: int
    round: int
    constructor_id: str
    position: int
    points: Decimal
    wins: int

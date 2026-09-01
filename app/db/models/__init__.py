"""F1 Race Intelligence — ORM models package.

Importing this module registers all models with the shared Base.metadata,
which is required for Alembic auto-generation to detect every table.
"""

from app.db.models.season import Season
from app.db.models.circuit import Circuit
from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.race import Race
from app.db.models.race_result import RaceResult
from app.db.models.qualifying_result import QualifyingResult
from app.db.models.sprint_result import SprintResult
from app.db.models.pit_stop import PitStop
from app.db.models.lap_time import LapTime
from app.db.models.driver_standing import DriverStanding
from app.db.models.constructor_standing import ConstructorStanding
from app.db.models.etl_log import EtlLog

__all__ = [
    "Season",
    "Circuit",
    "Constructor",
    "Driver",
    "Race",
    "RaceResult",
    "QualifyingResult",
    "SprintResult",
    "PitStop",
    "LapTime",
    "DriverStanding",
    "ConstructorStanding",
    "EtlLog",
]

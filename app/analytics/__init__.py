"""Analytical Data Layer — deterministic, reusable SQL analytics for F1 data.

All queries operate on persisted database data only.
No Jolpica API calls from analytics.
"""

from app.analytics.constructor_analysis import get_teammate_comparison
from app.analytics.driver_summary import get_driver_race_summary
from app.analytics.lap_time_analysis import get_driver_lap_times
from app.analytics.longitudinal_constructor import (
    get_all_constructors_season_aggregates,
    get_constructor_season_aggregate,
    get_constructor_trajectory,
)
from app.analytics.longitudinal_driver import (
    get_all_drivers_season_aggregates,
    get_driver_season_aggregate,
    get_driver_trajectory,
)
from app.analytics.longitudinal_teammate import (
    get_event_teammate_comparisons,
    get_season_teammate_comparisons,
)
from app.analytics.pit_stop_analysis import get_constructor_pit_stops, get_driver_pit_stops
from app.analytics.qualifying_analysis import (
    get_qualifying_order,
    get_teammate_qualifying_comparison,
)
from app.analytics.race_analysis import (
    get_grid_vs_finish,
    get_race_overview,
    get_race_results,
)
from app.analytics.standings_analysis import (
    get_constructor_standings,
    get_driver_standings,
)
from app.analytics.types import (
    ConstructorDriverContribution,
    ConstructorPitStopSummary,
    ConstructorSeasonAggregate,
    ConstructorStandingRow,
    ConstructorTrajectoryItem,
    DriverRaceSummary,
    DriverSeasonAggregate,
    DriverStandingRow,
    DriverTrajectoryItem,
    GridVsFinish,
    LapTimeSummary,
    PitStopSummary,
    QualifyingOrder,
    RaceOverview,
    RaceResultRow,
    SeasonTeammateComparison,
    TeammateComparison,
    TeammateEventComparison,
    TeammateQualifyingComparison,
)

__all__ = [
    # Types
    "ConstructorDriverContribution",
    "ConstructorPitStopSummary",
    "ConstructorSeasonAggregate",
    "ConstructorStandingRow",
    "ConstructorTrajectoryItem",
    "DriverRaceSummary",
    "DriverSeasonAggregate",
    "DriverStandingRow",
    "DriverTrajectoryItem",
    "GridVsFinish",
    "LapTimeSummary",
    "PitStopSummary",
    "QualifyingOrder",
    "RaceOverview",
    "RaceResultRow",
    "SeasonTeammateComparison",
    "TeammateComparison",
    "TeammateEventComparison",
    "TeammateQualifyingComparison",
    # Functions
    "get_race_overview",
    "get_grid_vs_finish",
    "get_race_results",
    "get_qualifying_order",
    "get_teammate_qualifying_comparison",
    "get_driver_pit_stops",
    "get_constructor_pit_stops",
    "get_driver_lap_times",
    "get_driver_standings",
    "get_constructor_standings",
    "get_driver_race_summary",
    "get_teammate_comparison",
    "get_driver_trajectory",
    "get_driver_season_aggregate",
    "get_all_drivers_season_aggregates",
    "get_constructor_trajectory",
    "get_constructor_season_aggregate",
    "get_all_constructors_season_aggregates",
    "get_event_teammate_comparisons",
    "get_season_teammate_comparisons",
]


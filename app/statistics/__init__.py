"""Statistical Analysis & Evidence Layer.

Transforms analytical SQL outputs into reproducible, deterministic statistical evidence.
Outputs numbers, sample sizes, and distributions — strictly no subjective insights or driver ratings.
"""

from app.statistics.descriptive import (
    compute_consistency_stats,
    compute_descriptive_stats,
)
from app.statistics.longitudinal import (
    compute_driver_form_summary,
    compute_driver_longitudinal_stats,
    compute_driver_points_stats,
    compute_longitudinal_evidence_metadata,
    compute_longitudinal_teammate_h2h_stats,
    compute_rolling_window_stats,
)
from app.statistics.pit_stops import compute_pit_stop_stats
from app.statistics.position_change import (
    compute_driver_position_change_stats,
    compute_position_change_distribution,
    compute_position_change_stats,
)
from app.statistics.qualifying import (
    compute_constructor_qualifying_delta,
    compute_qualifying_delta_stats,
)
from app.statistics.race_pace import compute_lap_time_stats
from app.statistics.teammate import (
    compute_constructor_head_to_head,
    compute_teammate_head_to_head_stats,
)
from app.statistics.types import (
    ConsistencyStats,
    DescriptiveStats,
    DriverFormSummary,
    DriverLongitudinalStats,
    EvidenceStrength,
    LapTimeStats,
    LongitudinalEvidenceMetadata,
    PitStopStats,
    PointsStats,
    PositionChangeDistribution,
    PositionChangeStats,
    QualifyingDeltaStats,
    QualityMetadata,
    RaceToRaceDelta,
    RollingWindowStats,
    TeammateH2HStatistics,
    TeammateHeadToHeadStats,
    classify_evidence_strength,
)

__all__ = [
    # Types
    "ConsistencyStats",
    "DescriptiveStats",
    "DriverFormSummary",
    "DriverLongitudinalStats",
    "EvidenceStrength",
    "LapTimeStats",
    "LongitudinalEvidenceMetadata",
    "PitStopStats",
    "PointsStats",
    "PositionChangeDistribution",
    "PositionChangeStats",
    "QualifyingDeltaStats",
    "QualityMetadata",
    "RaceToRaceDelta",
    "RollingWindowStats",
    "TeammateH2HStatistics",
    "TeammateHeadToHeadStats",
    "classify_evidence_strength",
    # Functions
    "compute_descriptive_stats",
    "compute_consistency_stats",
    "compute_position_change_stats",
    "compute_position_change_distribution",
    "compute_driver_position_change_stats",
    "compute_qualifying_delta_stats",
    "compute_constructor_qualifying_delta",
    "compute_lap_time_stats",
    "compute_pit_stop_stats",
    "compute_teammate_head_to_head_stats",
    "compute_constructor_head_to_head",
    "compute_longitudinal_evidence_metadata",
    "compute_driver_points_stats",
    "compute_driver_longitudinal_stats",
    "compute_rolling_window_stats",
    "compute_driver_form_summary",
    "compute_longitudinal_teammate_h2h_stats",
]

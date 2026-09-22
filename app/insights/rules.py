"""Central registry and definitions for deterministic insight rules."""

from __future__ import annotations

from app.insights.types import InsightCategory, RuleDefinition

# ─── Stable Rule IDs ──────────────────────────────────────────────────────────

RULE_QUALIFYING_TEAMMATE_ADVANTAGE = "QUALIFYING_TEAMMATE_ADVANTAGE"
RULE_QUALIFYING_TEAMMATE_DEFICIT = "QUALIFYING_TEAMMATE_DEFICIT"
RULE_QUALIFYING_TEAMMATE_EQUAL = "QUALIFYING_TEAMMATE_EQUAL"

RULE_POSITION_GAIN = "POSITION_GAIN"
RULE_POSITION_LOSS = "POSITION_LOSS"
RULE_POSITION_MAINTAINED = "POSITION_MAINTAINED"
RULE_LARGE_POSITION_GAIN = "LARGE_POSITION_GAIN"

RULE_FASTEST_RECORDED_LAP = "FASTEST_RECORDED_LAP"
RULE_RACE_PACE_TEAMMATE_ADVANTAGE = "RACE_PACE_TEAMMATE_ADVANTAGE"
RULE_RACE_PACE_TEAMMATE_DEFICIT = "RACE_PACE_TEAMMATE_DEFICIT"

RULE_FAST_PIT_STOP = "FAST_PIT_STOP"
RULE_PIT_STOP_HIGH_VARIABILITY = "PIT_STOP_HIGH_VARIABILITY"

RULE_TEAMMATE_POINTS_ADVANTAGE = "TEAMMATE_POINTS_ADVANTAGE"
RULE_TEAMMATE_POINTS_DEFICIT = "TEAMMATE_POINTS_DEFICIT"
RULE_TEAMMATE_FINISH_ADVANTAGE = "TEAMMATE_FINISH_ADVANTAGE"
RULE_TEAMMATE_GRID_ADVANTAGE = "TEAMMATE_GRID_ADVANTAGE"

# ─── Longitudinal Rule IDs (Phase 3D) ─────────────────────────────────────────

RULE_LONGITUDINAL_QUALIFYING_CONSISTENCY = "LONGITUDINAL_QUALIFYING_CONSISTENCY"
RULE_LONGITUDINAL_FINISH_CONSISTENCY = "LONGITUDINAL_FINISH_CONSISTENCY"
RULE_LONGITUDINAL_POSITION_GAIN_PATTERN = "LONGITUDINAL_POSITION_GAIN_PATTERN"
RULE_LONGITUDINAL_POSITION_LOSS_PATTERN = "LONGITUDINAL_POSITION_LOSS_PATTERN"
RULE_LONGITUDINAL_RECENT_FORM = "LONGITUDINAL_RECENT_FORM"
RULE_LONGITUDINAL_POINTS_PER_START = "LONGITUDINAL_POINTS_PER_START"
RULE_LONGITUDINAL_POINTS_PER_ROUND = "LONGITUDINAL_POINTS_PER_ROUND"
RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H = "LONGITUDINAL_TEAMMATE_QUALIFYING_H2H"
RULE_LONGITUDINAL_TEAMMATE_RACE_H2H = "LONGITUDINAL_TEAMMATE_RACE_H2H"
RULE_LONGITUDINAL_TEAMMATE_POINTS_H2H = "LONGITUDINAL_TEAMMATE_POINTS_H2H"
RULE_LONGITUDINAL_CONSTRUCTOR_TRAJECTORY = "LONGITUDINAL_CONSTRUCTOR_TRAJECTORY"

# ─── Configurable Named Threshold Constants ──────────────────────────────────

LARGE_POSITION_GAIN_THRESHOLD = 5
FAST_PIT_STOP_THRESHOLD_MILLIS = 25000
PIT_STOP_HIGH_VARIABILITY_THRESHOLD_MILLIS = 1500

# Longitudinal Threshold Constants
LONGITUDINAL_GRID_CONSISTENCY_STDDEV_THRESHOLD = 1.5
LONGITUDINAL_FINISH_CONSISTENCY_STDDEV_THRESHOLD = 1.5
LONGITUDINAL_POSITION_GAIN_PATTERN_THRESHOLD = 2.0
LONGITUDINAL_POSITION_LOSS_PATTERN_THRESHOLD = -2.0
LONGITUDINAL_RECENT_FORM_FINISH_THRESHOLD = 5.0
LONGITUDINAL_RECENT_FORM_WINDOW_SIZE = 3
LONGITUDINAL_POINTS_PER_START_THRESHOLD = 15.0
LONGITUDINAL_POINTS_PER_ROUND_THRESHOLD = 15.0
LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD = 0.70
LONGITUDINAL_TEAMMATE_POINTS_DIFF_THRESHOLD = 15.0
LONGITUDINAL_CONSTRUCTOR_PODIUM_RATE_THRESHOLD = 0.60

# ─── Rule Registry ────────────────────────────────────────────────────────────

RULE_REGISTRY: dict[str, RuleDefinition] = {
    RULE_QUALIFYING_TEAMMATE_ADVANTAGE: RuleDefinition(
        rule_id=RULE_QUALIFYING_TEAMMATE_ADVANTAGE,
        category=InsightCategory.QUALIFYING,
        description="Driver A set a faster qualifying lap time than teammate Driver B (delta < 0).",
        metric="qualifying_delta_millis",
        min_sample_size=1,
    ),
    RULE_QUALIFYING_TEAMMATE_DEFICIT: RuleDefinition(
        rule_id=RULE_QUALIFYING_TEAMMATE_DEFICIT,
        category=InsightCategory.QUALIFYING,
        description="Driver A set a slower qualifying lap time than teammate Driver B (delta > 0).",
        metric="qualifying_delta_millis",
        min_sample_size=1,
    ),
    RULE_QUALIFYING_TEAMMATE_EQUAL: RuleDefinition(
        rule_id=RULE_QUALIFYING_TEAMMATE_EQUAL,
        category=InsightCategory.QUALIFYING,
        description="Driver A and Driver B set identical qualifying lap times (delta == 0).",
        metric="qualifying_delta_millis",
        min_sample_size=1,
    ),
    RULE_POSITION_GAIN: RuleDefinition(
        rule_id=RULE_POSITION_GAIN,
        category=InsightCategory.POSITION_CHANGE,
        description="Driver gained one or more positions from starting grid to classified finish.",
        metric="position_change",
        min_sample_size=1,
    ),
    RULE_POSITION_LOSS: RuleDefinition(
        rule_id=RULE_POSITION_LOSS,
        category=InsightCategory.POSITION_CHANGE,
        description="Driver lost one or more positions from starting grid to classified finish.",
        metric="position_change",
        min_sample_size=1,
    ),
    RULE_POSITION_MAINTAINED: RuleDefinition(
        rule_id=RULE_POSITION_MAINTAINED,
        category=InsightCategory.POSITION_CHANGE,
        description="Driver finished the race in the exact position they started on the grid.",
        metric="position_change",
        min_sample_size=1,
    ),
    RULE_LARGE_POSITION_GAIN: RuleDefinition(
        rule_id=RULE_LARGE_POSITION_GAIN,
        category=InsightCategory.POSITION_CHANGE,
        description=f"Driver gained {LARGE_POSITION_GAIN_THRESHOLD} or more positions from starting grid.",
        metric="position_change",
        min_sample_size=1,
        thresholds={"gain_threshold": LARGE_POSITION_GAIN_THRESHOLD},
    ),
    RULE_FASTEST_RECORDED_LAP: RuleDefinition(
        rule_id=RULE_FASTEST_RECORDED_LAP,
        category=InsightCategory.RACE_PACE,
        description="Driver recorded the fastest individual lap time in the session/race sample.",
        metric="fastest_recorded_millis",
        min_sample_size=1,
    ),
    RULE_RACE_PACE_TEAMMATE_ADVANTAGE: RuleDefinition(
        rule_id=RULE_RACE_PACE_TEAMMATE_ADVANTAGE,
        category=InsightCategory.RACE_PACE,
        description="Driver A achieved a lower average/median lap time than Driver B in the race.",
        metric="pace_delta_millis",
        min_sample_size=1,
    ),
    RULE_RACE_PACE_TEAMMATE_DEFICIT: RuleDefinition(
        rule_id=RULE_RACE_PACE_TEAMMATE_DEFICIT,
        category=InsightCategory.RACE_PACE,
        description="Driver A recorded a higher average/median lap time than Driver B in the race.",
        metric="pace_delta_millis",
        min_sample_size=1,
    ),
    RULE_FAST_PIT_STOP: RuleDefinition(
        rule_id=RULE_FAST_PIT_STOP,
        category=InsightCategory.PIT_STOP,
        description=f"Driver or team achieved a pit stop duration under {FAST_PIT_STOP_THRESHOLD_MILLIS} ms.",
        metric="duration_millis",
        min_sample_size=1,
        thresholds={"duration_threshold_millis": FAST_PIT_STOP_THRESHOLD_MILLIS},
    ),
    RULE_PIT_STOP_HIGH_VARIABILITY: RuleDefinition(
        rule_id=RULE_PIT_STOP_HIGH_VARIABILITY,
        category=InsightCategory.PIT_STOP,
        description=f"Pit stop sample standard deviation exceeds {PIT_STOP_HIGH_VARIABILITY_THRESHOLD_MILLIS} ms.",
        metric="stddev_duration_millis",
        min_sample_size=2,
        thresholds={"stddev_threshold_millis": PIT_STOP_HIGH_VARIABILITY_THRESHOLD_MILLIS},
    ),
    RULE_TEAMMATE_POINTS_ADVANTAGE: RuleDefinition(
        rule_id=RULE_TEAMMATE_POINTS_ADVANTAGE,
        category=InsightCategory.TEAMMATE,
        description="Driver A scored more championship points than teammate Driver B (delta > 0).",
        metric="points_delta",
        min_sample_size=1,
    ),
    RULE_TEAMMATE_POINTS_DEFICIT: RuleDefinition(
        rule_id=RULE_TEAMMATE_POINTS_DEFICIT,
        category=InsightCategory.TEAMMATE,
        description="Driver A scored fewer championship points than teammate Driver B (delta < 0).",
        metric="points_delta",
        min_sample_size=1,
    ),
    RULE_TEAMMATE_FINISH_ADVANTAGE: RuleDefinition(
        rule_id=RULE_TEAMMATE_FINISH_ADVANTAGE,
        category=InsightCategory.TEAMMATE,
        description="Driver A finished ahead of teammate Driver B (finish_delta < 0).",
        metric="finish_delta",
        min_sample_size=1,
    ),
    RULE_TEAMMATE_GRID_ADVANTAGE: RuleDefinition(
        rule_id=RULE_TEAMMATE_GRID_ADVANTAGE,
        category=InsightCategory.TEAMMATE,
        description="Driver A qualified/started ahead of teammate Driver B on the starting grid (grid_delta < 0).",
        metric="grid_delta",
        min_sample_size=1,
    ),
    RULE_LONGITUDINAL_QUALIFYING_CONSISTENCY: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_QUALIFYING_CONSISTENCY,
        category=InsightCategory.QUALIFYING,
        description=f"Driver achieved high starting grid consistency (stddev <= {LONGITUDINAL_GRID_CONSISTENCY_STDDEV_THRESHOLD} positions) across multiple rounds.",
        metric="grid_position_stddev",
        min_sample_size=3,
        thresholds={"stddev_threshold": LONGITUDINAL_GRID_CONSISTENCY_STDDEV_THRESHOLD},
    ),
    RULE_LONGITUDINAL_FINISH_CONSISTENCY: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_FINISH_CONSISTENCY,
        category=InsightCategory.RACE_RESULT,
        description=f"Driver achieved high race finish consistency (stddev <= {LONGITUDINAL_FINISH_CONSISTENCY_STDDEV_THRESHOLD} positions) across multiple classified finishes.",
        metric="finish_position_stddev",
        min_sample_size=3,
        thresholds={"stddev_threshold": LONGITUDINAL_FINISH_CONSISTENCY_STDDEV_THRESHOLD},
    ),
    RULE_LONGITUDINAL_POSITION_GAIN_PATTERN: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_POSITION_GAIN_PATTERN,
        category=InsightCategory.POSITION_CHANGE,
        description=f"Driver consistently gained positions between grid and finish (mean gain >= {LONGITUDINAL_POSITION_GAIN_PATTERN_THRESHOLD} positions) across multiple races.",
        metric="mean_position_change",
        min_sample_size=3,
        thresholds={"gain_threshold": LONGITUDINAL_POSITION_GAIN_PATTERN_THRESHOLD},
    ),
    RULE_LONGITUDINAL_POSITION_LOSS_PATTERN: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_POSITION_LOSS_PATTERN,
        category=InsightCategory.POSITION_CHANGE,
        description=f"Driver consistently lost positions between grid and finish (mean loss <= {LONGITUDINAL_POSITION_LOSS_PATTERN_THRESHOLD} positions) across multiple races.",
        metric="mean_position_change",
        min_sample_size=3,
        thresholds={"loss_threshold": LONGITUDINAL_POSITION_LOSS_PATTERN_THRESHOLD},
    ),
    RULE_LONGITUDINAL_RECENT_FORM: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_RECENT_FORM,
        category=InsightCategory.DRIVER_FORM,
        description=f"Driver achieved strong average finishing position (mean finish <= P{LONGITUDINAL_RECENT_FORM_FINISH_THRESHOLD:.0f}) over the most recent rolling window.",
        metric="rolling_mean_finish",
        min_sample_size=2,
        thresholds={
            "window_size": LONGITUDINAL_RECENT_FORM_WINDOW_SIZE,
            "finish_threshold": LONGITUDINAL_RECENT_FORM_FINISH_THRESHOLD,
        },
    ),
    RULE_LONGITUDINAL_POINTS_PER_START: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_POINTS_PER_START,
        category=InsightCategory.POINTS,
        description=f"Driver sustained a high points-scoring rate (>= {LONGITUDINAL_POINTS_PER_START_THRESHOLD} points per Grand Prix start) across multiple starts.",
        metric="points_per_gp_start",
        min_sample_size=3,
        thresholds={"points_per_start_threshold": LONGITUDINAL_POINTS_PER_START_THRESHOLD},
    ),
    RULE_LONGITUDINAL_POINTS_PER_ROUND: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_POINTS_PER_ROUND,
        category=InsightCategory.POINTS,
        description=f"Driver sustained a high total points-scoring rate (>= {LONGITUDINAL_POINTS_PER_ROUND_THRESHOLD} points per championship round) across multiple rounds.",
        metric="points_per_round_total",
        min_sample_size=3,
        thresholds={"points_per_round_threshold": LONGITUDINAL_POINTS_PER_ROUND_THRESHOLD},
    ),
    RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H,
        category=InsightCategory.TEAMMATE,
        description=f"Driver achieved a decisive qualifying advantage over teammate (win rate >= {LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD:.0%}) across comparable qualifying rounds.",
        metric="qualifying_win_rate",
        min_sample_size=3,
        thresholds={"win_rate_threshold": LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD},
    ),
    RULE_LONGITUDINAL_TEAMMATE_RACE_H2H: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_TEAMMATE_RACE_H2H,
        category=InsightCategory.TEAMMATE,
        description=f"Driver achieved a decisive race finish advantage over teammate (win rate >= {LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD:.0%}) across comparable two-car finishes.",
        metric="race_win_rate",
        min_sample_size=3,
        thresholds={"win_rate_threshold": LONGITUDINAL_TEAMMATE_WIN_RATE_THRESHOLD},
    ),
    RULE_LONGITUDINAL_TEAMMATE_POINTS_H2H: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_TEAMMATE_POINTS_H2H,
        category=InsightCategory.TEAMMATE,
        description=f"Driver outscored teammate by at least {LONGITUDINAL_TEAMMATE_POINTS_DIFF_THRESHOLD} total championship points across multiple rounds together.",
        metric="points_difference",
        min_sample_size=3,
        thresholds={"points_diff_threshold": LONGITUDINAL_TEAMMATE_POINTS_DIFF_THRESHOLD},
    ),
    RULE_LONGITUDINAL_CONSTRUCTOR_TRAJECTORY: RuleDefinition(
        rule_id=RULE_LONGITUDINAL_CONSTRUCTOR_TRAJECTORY,
        category=InsightCategory.CONSTRUCTOR,
        description=f"Constructor achieved podium finishes in at least {LONGITUDINAL_CONSTRUCTOR_PODIUM_RATE_THRESHOLD:.0%} of entered championship rounds across the season trajectory.",
        metric="podium_rate",
        min_sample_size=3,
        thresholds={"podium_rate_threshold": LONGITUDINAL_CONSTRUCTOR_PODIUM_RATE_THRESHOLD},
    ),
}


def get_rule(rule_id: str) -> RuleDefinition:
    """Retrieve rule definition from registry.

    Raises KeyError if rule_id is not registered.
    """
    if rule_id not in RULE_REGISTRY:
        raise KeyError(f"Rule ID '{rule_id}' is not registered in the rule registry.")
    return RULE_REGISTRY[rule_id]

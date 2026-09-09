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

# ─── Configurable Named Threshold Constants ──────────────────────────────────

LARGE_POSITION_GAIN_THRESHOLD = 5
FAST_PIT_STOP_THRESHOLD_MILLIS = 25000
PIT_STOP_HIGH_VARIABILITY_THRESHOLD_MILLIS = 1500

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
}


def get_rule(rule_id: str) -> RuleDefinition:
    """Retrieve rule definition from registry.

    Raises KeyError if rule_id is not registered.
    """
    if rule_id not in RULE_REGISTRY:
        raise KeyError(f"Rule ID '{rule_id}' is not registered in the rule registry.")
    return RULE_REGISTRY[rule_id]

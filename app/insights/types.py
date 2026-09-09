"""Typed representations and enums for the deterministic insight engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EvidenceStrength(str, Enum):
    """Categorical heuristic for evidence strength based on sample size.

    Note: This is an evidence-strength heuristic, NOT a formal statistical
    confidence level or p-value.
    """

    INSUFFICIENT = "INSUFFICIENT"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


def classify_evidence_strength(
    sample_size: int,
    min_sample_size: int = 1,
) -> EvidenceStrength:
    """Classify evidence strength based on sample size and minimum requirement.

    Policy:
    - sample_size < min_sample_size or sample_size == 0 -> INSUFFICIENT
    - sample_size == 1 -> LOW
    - 2 <= sample_size <= 4 -> MODERATE
    - sample_size >= 5 -> HIGH

    Args:
        sample_size: Number of valid observations.
        min_sample_size: Minimum required observations for the rule.

    Returns:
        EvidenceStrength enum member.
    """
    if sample_size < min_sample_size or sample_size <= 0:
        return EvidenceStrength.INSUFFICIENT
    if sample_size == 1:
        return EvidenceStrength.LOW
    if 2 <= sample_size <= 4:
        return EvidenceStrength.MODERATE
    return EvidenceStrength.HIGH


class InsightCategory(str, Enum):
    """Categorical taxonomy for insights."""

    QUALIFYING = "QUALIFYING"
    POSITION_CHANGE = "POSITION_CHANGE"
    RACE_PACE = "RACE_PACE"
    PIT_STOP = "PIT_STOP"
    TEAMMATE = "TEAMMATE"
    RACE_RESULT = "RACE_RESULT"


class Direction(str, Enum):
    """Mathematical direction of an observed finding."""

    FASTER = "faster"
    SLOWER = "slower"
    GAINED = "gained"
    LOST = "lost"
    STABLE = "stable"
    HIGHER = "higher"
    LOWER = "lower"
    EQUAL = "equal"


@dataclass(frozen=True)
class RuleDefinition:
    """Metadata definition for a deterministic rule in the rule registry.

    Attributes:
        rule_id: Unique, stable string identifier.
        category: Analytical category.
        description: Deterministic explanation of what triggers this rule.
        metric: Primary metric evaluated.
        min_sample_size: Minimum sample size required to emit an insight.
        thresholds: Dictionary of named configurable threshold parameters.
    """

    rule_id: str
    category: InsightCategory
    description: str
    metric: str
    min_sample_size: int = 1
    thresholds: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InsightTraceability:
    """Full audit trail linking an insight back to statistical and analytical origins.

    Attributes:
        source_metric: Exact metric name from the statistical or analytical layer.
        source_function: Function name that produced the underlying evidence.
        rule_id: Rule evaluated.
        rule_parameters: Thresholds or parameters supplied to the rule.
        observed_value: Actual numeric or structured value observed.
        unit: Unit of measurement (e.g. 'milliseconds', 'positions', 'points').
        sample_size: Count of valid observations evaluated.
        minimum_sample_size: Minimum threshold required by the rule.
        sign_convention: Explicit explanation of positive/negative signs.
        season_year: Optional championship season context.
        round_num: Optional round context.
        race_id: Optional internal race ID.
        driver_id: Optional driver slug context.
        constructor_id: Optional constructor slug context.
    """

    source_metric: str
    source_function: str
    rule_id: str
    rule_parameters: dict[str, Any]
    observed_value: Any
    unit: Optional[str]
    sample_size: int
    minimum_sample_size: int
    sign_convention: Optional[str]
    season_year: Optional[int] = None
    round_num: Optional[int] = None
    race_id: Optional[int] = None
    driver_id: Optional[str] = None
    constructor_id: Optional[str] = None


@dataclass(frozen=True)
class Insight:
    """Structured, machine-readable insight produced by a deterministic rule.

    Attributes:
        insight_id: Deterministic string ID (e.g. 'rule_id:season:round:subject:comp').
        rule_id: Stable identifier of the triggered rule.
        category: Analytical category.
        subject_id: Primary entity (driver_id or constructor_id).
        comparison_subject_id: Secondary entity when comparative (e.g. teammate_id), or None.
        metric: Metric evaluated.
        direction: Direction of difference or movement.
        magnitude: Absolute or relative numeric magnitude, or None.
        unit: Measurement unit (e.g. 'milliseconds', 'positions', 'points').
        evidence_strength: Evidence strength classification.
        sample_size: Valid observations supporting this insight.
        traceability: Complete audit trail back to statistical evidence.
    """

    insight_id: str
    rule_id: str
    category: InsightCategory
    subject_id: str
    comparison_subject_id: Optional[str]
    metric: str
    direction: Direction
    magnitude: Optional[float]
    unit: Optional[str]
    evidence_strength: EvidenceStrength
    sample_size: int
    traceability: InsightTraceability

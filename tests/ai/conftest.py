"""Pytest fixtures for AI narrative layer tests."""

import pytest

from app.insights.rules import (
    RULE_POSITION_GAIN,
    RULE_QUALIFYING_TEAMMATE_ADVANTAGE,
    get_rule,
)
from app.insights.types import (
    Direction,
    EvidenceStrength,
    Insight,
    InsightCategory,
    InsightTraceability,
)


@pytest.fixture
def sample_qualifying_insight() -> Insight:
    """Fixture providing a sample qualifying teammate advantage insight."""
    rule = get_rule(RULE_QUALIFYING_TEAMMATE_ADVANTAGE)
    traceability = InsightTraceability(
        source_metric="qualifying_delta_millis",
        source_function="get_teammate_qualifying_comparison",
        rule_id=rule.rule_id,
        rule_parameters={},
        observed_value=-358,
        unit="milliseconds",
        sample_size=1,
        minimum_sample_size=1,
        sign_convention="delta = driver_a - driver_b; negative means driver_a was faster",
        season_year=2024,
        round_num=1,
        driver_id="max_verstappen",
        constructor_id="red_bull",
    )
    return Insight(
        insight_id="QUALIFYING_TEAMMATE_ADVANTAGE:2024:1:max_verstappen:perez",
        rule_id=rule.rule_id,
        category=InsightCategory.QUALIFYING,
        subject_id="max_verstappen",
        comparison_subject_id="perez",
        metric="qualifying_delta_millis",
        direction=Direction.FASTER,
        magnitude=358.0,
        unit="milliseconds",
        evidence_strength=EvidenceStrength.LOW,
        sample_size=1,
        traceability=traceability,
    )


@pytest.fixture
def sample_position_gain_insight() -> Insight:
    """Fixture providing a sample position gain insight."""
    rule = get_rule(RULE_POSITION_GAIN)
    traceability = InsightTraceability(
        source_metric="position_change",
        source_function="get_grid_vs_finish",
        rule_id=rule.rule_id,
        rule_parameters={},
        observed_value=3,
        unit="positions",
        sample_size=1,
        minimum_sample_size=1,
        sign_convention="position_change = grid - finish; positive means gained positions",
        season_year=2024,
        round_num=1,
        driver_id="perez",
        constructor_id="red_bull",
    )
    return Insight(
        insight_id="POSITION_GAIN:2024:1:perez:none",
        rule_id=rule.rule_id,
        category=InsightCategory.POSITION_CHANGE,
        subject_id="perez",
        comparison_subject_id=None,
        metric="position_change",
        direction=Direction.GAINED,
        magnitude=3.0,
        unit="positions",
        evidence_strength=EvidenceStrength.LOW,
        sample_size=1,
        traceability=traceability,
    )

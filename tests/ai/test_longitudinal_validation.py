"""Unit tests for longitudinal AI response validation and contradiction checks."""

import json
import pytest

from app.ai.exceptions import AIResponseValidationError
from app.ai.validation import parse_and_validate_response
from app.insights.rules import (
    RULE_LONGITUDINAL_POINTS_PER_START,
    RULE_LONGITUDINAL_RECENT_FORM,
    RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H,
    get_rule,
)
from app.insights.types import (
    Direction,
    EvidenceStrength,
    Insight,
    InsightTraceability,
)


def _make_quali_h2h_insight() -> Insight:
    rule = get_rule(RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H)
    trace = InsightTraceability(
        source_metric="qualifying_win_rate",
        source_function="compute_longitudinal_teammate_h2h_stats",
        rule_id=rule.rule_id,
        rule_parameters=rule.thresholds,
        observed_value=1.0,
        unit="win_rate",
        sample_size=5,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="wins / rounds",
        season_year=2024,
        driver_id="max_verstappen",
        constructor_id="red_bull",
        rounds_included=[1, 2, 3, 4, 5],
        excluded_observations=0,
    )
    return Insight(
        insight_id="LONGITUDINAL_TEAMMATE_QUALIFYING_H2H:2024:red_bull:max_verstappen:perez",
        rule_id=rule.rule_id,
        category=rule.category,
        subject_id="max_verstappen",
        comparison_subject_id="perez",
        metric="qualifying_win_rate",
        direction=Direction.FASTER,
        magnitude=1.0,
        unit="win_rate",
        evidence_strength=EvidenceStrength.HIGH,
        sample_size=5,
        traceability=trace,
        explanation="Across 5 comparable qualifying rounds, max_verstappen out-qualified perez 5 of 5 times (100%).",
    )


def _make_dnf_driver_insight() -> Insight:
    rule = get_rule(RULE_LONGITUDINAL_POINTS_PER_START)
    trace = InsightTraceability(
        source_metric="points_per_gp_start",
        source_function="compute_driver_longitudinal_stats",
        rule_id=rule.rule_id,
        rule_parameters=rule.thresholds,
        observed_value=20.4,
        unit="points",
        sample_size=5,
        minimum_sample_size=rule.min_sample_size,
        sign_convention="total_gp_points / gp_starts",
        season_year=2024,
        driver_id="max_verstappen",
        rounds_included=[1, 2, 3, 4, 5],
        excluded_observations=1,
    )
    return Insight(
        insight_id="LONGITUDINAL_POINTS_PER_START:2024:rounds_1-5:max_verstappen:none",
        rule_id=rule.rule_id,
        category=rule.category,
        subject_id="max_verstappen",
        comparison_subject_id=None,
        metric="points_per_gp_start",
        direction=Direction.HIGHER,
        magnitude=20.4,
        unit="points",
        evidence_strength=EvidenceStrength.HIGH,
        sample_size=5,
        traceability=trace,
        explanation="Across 5 GP starts in 2024, max_verstappen averaged 20.4 points per start.",
    )


def _make_recent_form_insight() -> Insight:
    rule = get_rule(RULE_LONGITUDINAL_RECENT_FORM)
    trace = InsightTraceability(
        source_metric="rolling_mean_finish",
        source_function="compute_driver_form_summary",
        rule_id=rule.rule_id,
        rule_parameters=rule.thresholds,
        observed_value=1.0,
        unit="position",
        sample_size=2,
        minimum_sample_size=2,
        sign_convention="mean finishing position",
        season_year=2024,
        driver_id="max_verstappen",
        rounds_included=[3, 4, 5],
        excluded_observations=1,
    )
    return Insight(
        insight_id="LONGITUDINAL_RECENT_FORM:2024:w3_r5:max_verstappen:none",
        rule_id=rule.rule_id,
        category=rule.category,
        subject_id="max_verstappen",
        comparison_subject_id=None,
        metric="rolling_mean_finish",
        direction=Direction.HIGHER,
        magnitude=1.0,
        unit="position",
        evidence_strength=EvidenceStrength.MODERATE,
        sample_size=2,
        traceability=trace,
        explanation="Over the most recent 3 rounds (R3-R5), max_verstappen recorded an average finish of P1.0 across 2 valid finishes (1 DNF excluded).",
    )


class TestLongitudinalValidation:
    def test_valid_longitudinal_response_accepted(self):
        ins = _make_quali_h2h_insight()
        raw = json.dumps({
            "narrative": "Max Verstappen out-qualified Sergio Perez in all 5 comparable sessions across rounds 1 to 5.",
            "limitations": ["Limited to 5 rounds."],
            "evidence_references": [ins.insight_id],
        })
        resp = parse_and_validate_response(raw, [ins])
        assert "Max Verstappen" in resp.narrative
        assert len(resp.limitations) == 1

    def test_contradiction_dnf_claim_rejected(self):
        ins = _make_dnf_driver_insight()
        raw = json.dumps({
            "narrative": "Max Verstappen showed extreme consistency and finished all 5 races of the season.",
            "limitations": [],
            "evidence_references": [ins.insight_id],
        })
        with pytest.raises(AIResponseValidationError) as exc_info:
            parse_and_validate_response(raw, [ins])
        assert "finished all races" in str(exc_info.value) or "DNFs" in str(exc_info.value)

    def test_contradiction_h2h_ratio_rejected(self):
        ins = _make_quali_h2h_insight()
        raw = json.dumps({
            "narrative": "Max Verstappen won 3 of 5 qualifying comparisons against Sergio Perez.",
            "limitations": [],
            "evidence_references": [ins.insight_id],
        })
        with pytest.raises(AIResponseValidationError) as exc_info:
            parse_and_validate_response(raw, [ins])
        assert "Contradiction detected" in str(exc_info.value)
        assert "3 of 5" in str(exc_info.value)

    def test_contradiction_h2h_score_rejected(self):
        ins = _make_quali_h2h_insight()
        raw = json.dumps({
            "narrative": "In head-to-head qualifying, max_verstappen led perez with a score of 3-2.",
            "limitations": [],
            "evidence_references": [ins.insight_id],
        })
        with pytest.raises(AIResponseValidationError) as exc_info:
            parse_and_validate_response(raw, [ins])
        assert "Contradiction detected" in str(exc_info.value)
        assert "3-2" in str(exc_info.value)

    def test_contradiction_recent_form_finishes_rejected(self):
        ins = _make_recent_form_insight()
        raw = json.dumps({
            "narrative": "Max Verstappen recorded an average finish of P1.0 across 3 valid finishes.",
            "limitations": [],
            "evidence_references": [ins.insight_id],
        })
        with pytest.raises(AIResponseValidationError) as exc_info:
            parse_and_validate_response(raw, [ins])
        assert "across '3' valid finishes" in str(exc_info.value)

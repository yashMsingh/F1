"""Unit tests for response validation and contradiction checks."""

import json

import pytest

from app.ai.exceptions import AIResponseValidationError
from app.ai.validation import parse_and_validate_response
from app.insights.rules import RULE_POSITION_LOSS, get_rule
from app.insights.types import (
    Direction,
    EvidenceStrength,
    Insight,
    InsightCategory,
    InsightTraceability,
)


class TestValidation:
    def test_valid_json_response(self, sample_qualifying_insight):
        raw = json.dumps(
            {
                "narrative": "Max Verstappen set a faster lap than Sergio Perez by 358 ms.",
                "limitations": ["One qualifying session only."],
                "evidence_references": [sample_qualifying_insight.insight_id],
            }
        )
        resp = parse_and_validate_response(raw, [sample_qualifying_insight])
        assert resp.narrative == "Max Verstappen set a faster lap than Sergio Perez by 358 ms."
        assert len(resp.limitations) == 1
        assert resp.evidence_references == [sample_qualifying_insight.insight_id]

    def test_markdown_code_block_stripping(self, sample_qualifying_insight):
        raw = (
            "```json\n"
            "{\n"
            '  "narrative": "Verstappen was faster in Bahrain qualifying.",\n'
            '  "limitations": [],\n'
            '  "evidence_references": []\n'
            "}\n"
            "```"
        )
        resp = parse_and_validate_response(raw, [sample_qualifying_insight])
        assert resp.narrative == "Verstappen was faster in Bahrain qualifying."

    def test_empty_narrative_raises(self, sample_qualifying_insight):
        raw = json.dumps({"narrative": "   ", "limitations": [], "evidence_references": []})
        with pytest.raises(AIResponseValidationError) as exc_info:
            parse_and_validate_response(raw, [sample_qualifying_insight])
        assert "non-empty string" in str(exc_info.value)

    def test_missing_fields_raises(self, sample_qualifying_insight):
        raw = json.dumps({"narrative": "Valid text but no limitations"})
        with pytest.raises(AIResponseValidationError) as exc_info:
            parse_and_validate_response(raw, [sample_qualifying_insight])
        assert "limitations" in str(exc_info.value)

    def test_contradiction_faster_vs_slower(self, sample_qualifying_insight):
        # sample_qualifying_insight has subject='max_verstappen', comp='perez', direction=FASTER
        raw = json.dumps(
            {
                "narrative": "Max_Verstappen was slower than perez in qualifying.",
                "limitations": [],
                "evidence_references": [],
            }
        )
        with pytest.raises(AIResponseValidationError) as exc_info:
            parse_and_validate_response(raw, [sample_qualifying_insight])
        assert "Contradiction detected" in str(exc_info.value)

    def test_contradiction_gained_vs_lost(self, sample_position_gain_insight):
        # sample_position_gain_insight has subject='perez', direction=GAINED
        raw = json.dumps(
            {
                "narrative": "Perez lost positions during the race.",
                "limitations": [],
                "evidence_references": [],
            }
        )
        with pytest.raises(AIResponseValidationError) as exc_info:
            parse_and_validate_response(raw, [sample_position_gain_insight])
        assert "Contradiction detected" in str(exc_info.value)

    def test_contradiction_lost_vs_gained(self):
        rule = get_rule(RULE_POSITION_LOSS)
        ins = Insight(
            insight_id="POSITION_LOSS:2024:1:leclerc:none",
            rule_id=rule.rule_id,
            category=InsightCategory.POSITION_CHANGE,
            subject_id="leclerc",
            comparison_subject_id=None,
            metric="position_change",
            direction=Direction.LOST,
            magnitude=2.0,
            unit="positions",
            evidence_strength=EvidenceStrength.LOW,
            sample_size=1,
            traceability=InsightTraceability("m", "f", "r", {}, -2, "p", 1, 1, "s"),
        )
        raw = json.dumps(
            {
                "narrative": "Leclerc gained positions to advance up the field.",
                "limitations": [],
                "evidence_references": [],
            }
        )
        with pytest.raises(AIResponseValidationError) as exc_info:
            parse_and_validate_response(raw, [ins])
        assert "Contradiction detected" in str(exc_info.value)

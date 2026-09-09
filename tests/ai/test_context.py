"""Unit tests for the evidence context builder."""

from app.ai.context import build_evidence_context
from app.insights.types import Insight


class TestEvidenceContextBuilder:
    def test_single_insight_serialization(self, sample_qualifying_insight):
        ctx = build_evidence_context(sample_qualifying_insight)
        assert len(ctx.insights) == 1

        rec = ctx.insights[0]
        assert rec["insight_id"] == "QUALIFYING_TEAMMATE_ADVANTAGE:2024:1:max_verstappen:perez"
        assert rec["rule_id"] == "QUALIFYING_TEAMMATE_ADVANTAGE"
        assert rec["subject_id"] == "max_verstappen"
        assert rec["comparison_subject_id"] == "perez"
        assert rec["metric"] == "qualifying_delta_millis"
        assert rec["direction"] == "faster"
        assert rec["magnitude"] == 358.0
        assert rec["unit"] == "milliseconds"
        assert rec["evidence_strength"] == "LOW"
        assert rec["sample_size"] == 1

        # Check traceability fields
        trace = rec["traceability"]
        assert trace["observed_value"] == -358
        assert trace["season_year"] == 2024
        assert trace["round_num"] == 1

        # Check limitations injected for LOW evidence
        assert any("LOW evidence strength" in lim for lim in ctx.limitations)

    def test_multi_insight_serialization(self, sample_qualifying_insight, sample_position_gain_insight):
        ctx = build_evidence_context([sample_qualifying_insight, sample_position_gain_insight])
        assert len(ctx.insights) == 2
        ids = [i["insight_id"] for i in ctx.insights]
        assert sample_qualifying_insight.insight_id in ids
        assert sample_position_gain_insight.insight_id in ids

    def test_empty_insight_list(self):
        ctx = build_evidence_context([])
        assert ctx.insights == []
        assert len(ctx.limitations) >= 1

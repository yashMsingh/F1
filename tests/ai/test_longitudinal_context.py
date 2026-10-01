"""Unit tests for the longitudinal evidence context builder."""

from app.ai.context import build_evidence_context
from app.insights.rules import (
    RULE_LONGITUDINAL_POINTS_PER_START,
    RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H,
    get_rule,
)
from app.insights.types import (
    Direction,
    EvidenceStrength,
    Insight,
    InsightCategory,
    InsightTraceability,
)


def _make_longitudinal_driver_insight() -> Insight:
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
        insight_id=f"{rule.rule_id}:2024:rounds_1-5:max_verstappen:none",
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


def _make_longitudinal_teammate_insight() -> Insight:
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
        sign_convention="qualifying_wins / comparable_qualifying_rounds",
        season_year=2024,
        driver_id="max_verstappen",
        constructor_id="red_bull",
        rounds_included=[1, 2, 3, 4, 5],
        excluded_observations=0,
    )
    return Insight(
        insight_id=f"{rule.rule_id}:2024:red_bull:max_verstappen:perez",
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


class TestLongitudinalEvidenceContext:
    def test_single_race_retains_race_scope(self, sample_qualifying_insight):
        ctx = build_evidence_context(sample_qualifying_insight)
        assert len(ctx.insights) == 1
        rec = ctx.insights[0]
        assert rec["scope"] == "race"
        assert rec["rule_id"] == "QUALIFYING_TEAMMATE_ADVANTAGE"
        assert rec["sample_size"] == 1
        assert "valid_observations" not in rec  # only on longitudinal

    def test_longitudinal_driver_serialization(self):
        ins = _make_longitudinal_driver_insight()
        ctx = build_evidence_context(ins)
        assert len(ctx.insights) == 1

        rec = ctx.insights[0]
        assert rec["scope"] == "longitudinal"
        assert rec["rule_id"] == "LONGITUDINAL_POINTS_PER_START"
        assert rec["season"] == 2024
        assert rec["subject_id"] == "max_verstappen"
        assert rec["sample_size"] == 5
        assert rec["valid_observations"] == 5
        assert rec["excluded_observations"] == 1
        assert rec["rounds_included"] == [1, 2, 3, 4, 5]
        assert rec["evidence_strength"] == "HIGH"
        assert rec["explanation"] is not None

        trace = rec["traceability"]
        assert trace["source_metric"] == "points_per_gp_start"
        assert trace["source_function"] == "compute_driver_longitudinal_stats"
        assert trace["valid_observations"] == 5
        assert trace["excluded_observations"] == 1
        assert trace["rounds_included"] == [1, 2, 3, 4, 5]

    def test_mixed_context_serialization(self, sample_qualifying_insight):
        long_ins = _make_longitudinal_teammate_insight()
        ctx = build_evidence_context([sample_qualifying_insight, long_ins])
        assert len(ctx.insights) == 2

        scopes = {i["insight_id"]: i["scope"] for i in ctx.insights}
        assert scopes[sample_qualifying_insight.insight_id] == "race"
        assert scopes[long_ins.insight_id] == "longitudinal"

    def test_longitudinal_limitations_injected(self):
        long_ins = _make_longitudinal_driver_insight()
        ctx = build_evidence_context(long_ins)
        assert any(
            "Longitudinal findings describe only the supplied rounds" in lim
            for lim in ctx.limitations
        )

    def test_empty_insights(self):
        ctx = build_evidence_context([])
        assert ctx.insights == []
        assert len(ctx.limitations) >= 2

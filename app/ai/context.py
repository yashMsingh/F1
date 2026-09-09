"""Deterministic context builder converting Insight objects into LLM-safe evidence payloads."""

from __future__ import annotations

from typing import Any, Sequence, Union

from app.ai.types import EvidenceContext
from app.insights.types import EvidenceStrength, Insight


def build_evidence_context(
    insights: Union[Insight, Sequence[Insight]],
) -> EvidenceContext:
    """Serialize approved deterministic Insight objects into an EvidenceContext.

    Args:
        insights: Single Insight or sequence of Insight instances.

    Returns:
        EvidenceContext containing serialized insight records and explicit limitations.
    """
    if isinstance(insights, Insight):
        insight_list = [insights]
    else:
        insight_list = list(insights)

    serialized_insights: list[dict[str, Any]] = []
    limitations: list[str] = [
        "Telemetry, tyre compound/degradation, and weather data are absent from this evidence package; do not invent technical causes.",
        "The database and deterministic analytics are the sole source of truth; no external knowledge may be introduced.",
    ]

    has_low_evidence = False

    for ins in insight_list:
        t = ins.traceability
        rec: dict[str, Any] = {
            "insight_id": ins.insight_id,
            "rule_id": ins.rule_id,
            "category": ins.category.value,
            "subject_id": ins.subject_id,
            "comparison_subject_id": ins.comparison_subject_id,
            "metric": ins.metric,
            "direction": ins.direction.value,
            "magnitude": ins.magnitude,
            "unit": ins.unit,
            "evidence_strength": ins.evidence_strength.value,
            "sample_size": ins.sample_size,
            "traceability": {
                "source_metric": t.source_metric,
                "observed_value": t.observed_value,
                "sign_convention": t.sign_convention,
                "season_year": t.season_year,
                "round_num": t.round_num,
            },
        }
        serialized_insights.append(rec)

        if ins.evidence_strength == EvidenceStrength.LOW:
            has_low_evidence = True

    if has_low_evidence:
        limitations.append(
            "One or more insights have LOW evidence strength (sample size = 1); "
            "describe as an isolated session/race observation and NOT as a persistent trend."
        )

    return EvidenceContext(
        insights=serialized_insights,
        limitations=limitations,
    )

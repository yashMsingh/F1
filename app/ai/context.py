"""Deterministic context builder converting Insight objects into LLM-safe evidence payloads."""

from __future__ import annotations

from typing import Any, Sequence, Union

from app.ai.types import EvidenceContext
from app.insights.types import EvidenceStrength, Insight


def build_evidence_context(
    insights: Union[Insight, Sequence[Insight]],
) -> EvidenceContext:
    """Serialize approved deterministic Insight objects into an EvidenceContext.

    Supports both single-race insights and longitudinal multi-race insights.

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
    has_longitudinal = False

    for ins in insight_list:
        t = ins.traceability
        is_longitudinal = (
            ins.rule_id.startswith("LONGITUDINAL_")
            or (t.rounds_included is not None and len(t.rounds_included) > 1)
        )
        scope = "longitudinal" if is_longitudinal else "race"
        if is_longitudinal:
            has_longitudinal = True

        trace_data: dict[str, Any] = {
            "source_metric": t.source_metric,
            "source_function": t.source_function,
            "observed_value": t.observed_value,
            "sign_convention": t.sign_convention,
            "season_year": t.season_year,
            "round_num": t.round_num,
            "threshold": t.rule_parameters,
            "minimum_sample_size": t.minimum_sample_size,
        }

        rec: dict[str, Any] = {
            "insight_id": ins.insight_id,
            "scope": scope,
            "rule_id": ins.rule_id,
            "category": ins.category.value,
            "season": t.season_year,
            "subject_id": ins.subject_id,
            "comparison_subject_id": ins.comparison_subject_id,
            "metric": ins.metric,
            "direction": ins.direction.value,
            "magnitude": ins.magnitude,
            "unit": ins.unit,
            "evidence_strength": ins.evidence_strength.value,
            "sample_size": ins.sample_size,
            "traceability": trace_data,
        }

        if is_longitudinal:
            valid_obs = ins.sample_size
            excluded_obs = t.excluded_observations if t.excluded_observations is not None else 0
            rounds_inc = t.rounds_included or []

            rec["valid_observations"] = valid_obs
            rec["excluded_observations"] = excluded_obs
            rec["rounds_included"] = rounds_inc

            trace_data["valid_observations"] = valid_obs
            trace_data["excluded_observations"] = excluded_obs
            trace_data["rounds_included"] = rounds_inc

        if ins.explanation:
            rec["explanation"] = ins.explanation

        serialized_insights.append(rec)

        if ins.evidence_strength == EvidenceStrength.LOW:
            has_low_evidence = True

    if has_low_evidence:
        limitations.append(
            "One or more insights have LOW evidence strength (sample size = 1); "
            "describe as an isolated session/race observation and NOT as a persistent trend."
        )

    if has_longitudinal:
        limitations.append(
            "Longitudinal findings describe only the supplied rounds in the observed season; "
            "do not extrapolate beyond the observed sample, make career-level conclusions, or predict future performance."
        )

    return EvidenceContext(
        insights=serialized_insights,
        limitations=limitations,
    )

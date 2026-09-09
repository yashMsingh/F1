"""Type definitions and contracts for the grounded AI narrative layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.insights.types import Insight


@dataclass(frozen=True)
class EvidenceContext:
    """Serialized, compact evidence payload prepared for LLM consumption.

    Attributes:
        insights: List of serialized insight records with metrics and traceability.
        limitations: Explicit list of methodological or dataset limitations.
    """

    insights: list[dict[str, Any]]
    limitations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NarrativeRequest:
    """Request payload sent to an LLMProvider.

    Attributes:
        insights: The original approved deterministic Insight objects.
        context_payload: Compact serialized dictionary representing the evidence.
        system_prompt: Grounding system prompt defining narrator role and constraints.
        user_prompt: User prompt embedding the evidence payload and schema contract.
    """

    insights: list[Insight]
    context_payload: dict[str, Any]
    system_prompt: str
    user_prompt: str


@dataclass(frozen=True)
class NarrativeResponse:
    """Validated response from the AI narrative layer.

    Attributes:
        narrative: Concise, human-readable narrative grounded strictly in evidence.
        limitations: List of cited or confirmed data limitations.
        evidence_references: List of referenced insight IDs or metrics.
        raw_response: Optional raw dictionary returned by the provider.
    """

    narrative: str
    limitations: list[str]
    evidence_references: list[str]
    raw_response: Optional[dict[str, Any]] = None

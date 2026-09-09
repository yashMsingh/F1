"""High-level service orchestrating grounded AI narrative generation."""

from __future__ import annotations

import logging
from typing import Optional, Sequence, Union

from app.ai.config import AIConfig, load_ai_config
from app.ai.context import build_evidence_context
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.ai.providers.base import LLMProvider, get_provider
from app.ai.types import NarrativeRequest, NarrativeResponse
from app.insights.types import Insight

logger = logging.getLogger(__name__)

MAX_INSIGHTS_PER_REQUEST = 10


class NarrativeService:
    """Orchestrates grounded narrative generation from deterministic insights."""

    def __init__(
        self,
        config: Optional[AIConfig] = None,
        provider: Optional[LLMProvider] = None,
    ) -> None:
        """Initialize NarrativeService with optional configuration or custom provider.

        If config is omitted, loads from environment variables.
        If provider is omitted, instantiates provider matching config.
        """
        self.config = config or load_ai_config()
        self.provider = provider or get_provider(self.config)

    def generate_narrative(
        self,
        insights: Union[Insight, Sequence[Insight]],
    ) -> NarrativeResponse:
        """Generate an evidence-backed narrative for one or more approved deterministic insights.

        Args:
            insights: Single Insight or sequence of approved Insight objects.

        Returns:
            Validated NarrativeResponse instance.

        Raises:
            AIError: On configuration, provider communication, or validation failure.
        """
        if isinstance(insights, Insight):
            insight_list = [insights]
        else:
            insight_list = list(insights)

        if not insight_list:
            return NarrativeResponse(
                narrative="No insights provided for narrative generation.",
                limitations=["Empty insight payload."],
                evidence_references=[],
            )

        # Bound context scope
        bounded_insights = insight_list[:MAX_INSIGHTS_PER_REQUEST]

        # 1. Build deterministic evidence context
        context = build_evidence_context(bounded_insights)
        context_payload = {
            "insights": context.insights,
            "limitations": context.limitations,
        }

        # 2. Build prompts
        system_prompt = SYSTEM_PROMPT
        user_prompt = build_user_prompt(context_payload)

        # 3. Assemble request
        request = NarrativeRequest(
            insights=bounded_insights,
            context_payload=context_payload,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # 4. Invoke provider (which internally invokes parse_and_validate_response)
        return self.provider.generate(request)

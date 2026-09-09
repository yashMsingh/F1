"""Abstract interface and factory for LLM providers."""

from __future__ import annotations

from typing import Protocol

from app.ai.config import AIConfig
from app.ai.exceptions import AIUnsupportedProviderError
from app.ai.types import NarrativeRequest, NarrativeResponse


class LLMProvider(Protocol):
    """Abstract protocol for an LLM provider."""

    def generate(self, request: NarrativeRequest) -> NarrativeResponse:
        """Send a narrative request to the LLM and return a structured narrative response.

        Args:
            request: NarrativeRequest containing prompts and evidence context.

        Returns:
            NarrativeResponse with narrative, limitations, and references.

        Raises:
            AIAuthenticationError: If authentication fails (HTTP 401).
            AIRateLimitError: If rate limits are exceeded (HTTP 429).
            AITimeoutError: If the request times out.
            AIProviderError: If any other provider error occurs.
            AIResponseValidationError: If the returned output is malformed or invalid.
        """
        ...


def get_provider(config: AIConfig) -> LLMProvider:
    """Instantiate and return the configured LLMProvider.

    Args:
        config: Validated AIConfig instance.

    Returns:
        LLMProvider instance.

    Raises:
        AIUnsupportedProviderError: If the configured provider is not implemented.
    """
    from app.ai.providers.groq import GroqProvider
    from app.ai.providers.openrouter import OpenRouterProvider

    if config.provider == "groq":
        return GroqProvider(config)
    elif config.provider == "openrouter":
        return OpenRouterProvider(config)
    else:
        raise AIUnsupportedProviderError(f"Unsupported provider: '{config.provider}'")

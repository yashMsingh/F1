"""Grounded AI Narrative Layer.

Translates approved deterministic insights into human-readable F1 narrative explanations.
The LLM is strictly an explanatory narrator, not an analyst.
"""

from app.ai.config import AIConfig, load_ai_config
from app.ai.context import build_evidence_context
from app.ai.exceptions import (
    AIAuthenticationError,
    AIConfigError,
    AIError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AITimeoutError,
    AIUnsupportedProviderError,
)
from app.ai.narrative import NarrativeService
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.ai.providers.base import LLMProvider, get_provider
from app.ai.providers.groq import GroqProvider
from app.ai.providers.openrouter import OpenRouterProvider
from app.ai.types import EvidenceContext, NarrativeRequest, NarrativeResponse
from app.ai.validation import parse_and_validate_response

__all__ = [
    # Service & Config
    "NarrativeService",
    "AIConfig",
    "load_ai_config",
    # Types
    "EvidenceContext",
    "NarrativeRequest",
    "NarrativeResponse",
    # Providers
    "LLMProvider",
    "get_provider",
    "GroqProvider",
    "OpenRouterProvider",
    # Context, Prompts, & Validation
    "build_evidence_context",
    "SYSTEM_PROMPT",
    "build_user_prompt",
    "parse_and_validate_response",
    # Exceptions
    "AIError",
    "AIConfigError",
    "AIUnsupportedProviderError",
    "AIProviderError",
    "AIAuthenticationError",
    "AIRateLimitError",
    "AITimeoutError",
    "AIResponseValidationError",
]

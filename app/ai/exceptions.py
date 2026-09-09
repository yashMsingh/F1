"""Exceptions for the AI narrative layer.

All exceptions are provider-independent and avoid leaking secrets or credentials.
"""

from __future__ import annotations


class AIError(Exception):
    """Base exception for all AI narrative layer errors."""


class AIConfigError(AIError):
    """Raised when AI configuration is missing or invalid."""


class AIUnsupportedProviderError(AIConfigError):
    """Raised when an unrecognized LLM provider is requested."""


class AIProviderError(AIError):
    """Base exception for errors communicating with an LLM provider."""


class AIAuthenticationError(AIProviderError):
    """Raised when authentication with the provider fails (e.g. invalid API key)."""


class AIRateLimitError(AIProviderError):
    """Raised when the provider's rate limit is exceeded (HTTP 429)."""


class AITimeoutError(AIProviderError):
    """Raised when a request to the provider times out."""


class AIResponseValidationError(AIError):
    """Raised when an LLM response fails grounding, structure, or contradiction checks."""

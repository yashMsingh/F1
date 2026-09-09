"""Configuration management for the AI narrative layer."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

from app.ai.exceptions import AIConfigError, AIUnsupportedProviderError

# Load any .env variables if present
load_dotenv()

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"
DEFAULT_TIMEOUT_SECONDS = 30.0
SUPPORTED_PROVIDERS = {"groq", "openrouter"}


@dataclass(frozen=True)
class AIConfig:
    """Immutable configuration for an AI provider.

    Attributes:
        provider: Provider identifier ('groq' or 'openrouter').
        api_key: Provider API key.
        model: Selected model name.
        timeout_seconds: HTTP request timeout in seconds.
    """

    provider: str
    api_key: str
    model: str
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __repr__(self) -> str:
        """Mask the API key to prevent accidental leakage in logs or traces."""
        masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "***"
        return (
            f"AIConfig(provider='{self.provider}', model='{self.model}', "
            f"api_key='{masked_key}', timeout_seconds={self.timeout_seconds})"
        )


def load_ai_config(
    provider_override: Optional[str] = None,
    api_key_override: Optional[str] = None,
    model_override: Optional[str] = None,
    timeout_override: Optional[float] = None,
) -> AIConfig:
    """Load and validate AI configuration from environment variables or overrides.

    Args:
        provider_override: Optional manual provider selection ('groq' or 'openrouter').
        api_key_override: Optional manual API key override.
        model_override: Optional manual model override.
        timeout_override: Optional timeout override in seconds.

    Returns:
        Validated AIConfig instance.

    Raises:
        AIUnsupportedProviderError: If the provider is not supported.
        AIConfigError: If required credentials or settings are missing.
    """
    provider = (provider_override or os.environ.get("LLM_PROVIDER", "groq")).strip().lower()

    if provider not in SUPPORTED_PROVIDERS:
        raise AIUnsupportedProviderError(
            f"Unsupported LLM provider '{provider}'. Supported providers are: {sorted(SUPPORTED_PROVIDERS)}"
        )

    # Resolve timeout
    timeout = DEFAULT_TIMEOUT_SECONDS
    if timeout_override is not None:
        timeout = float(timeout_override)
    elif "LLM_TIMEOUT_SECONDS" in os.environ:
        try:
            timeout = float(os.environ["LLM_TIMEOUT_SECONDS"])
        except ValueError as err:
            raise AIConfigError(f"Invalid LLM_TIMEOUT_SECONDS value: {os.environ['LLM_TIMEOUT_SECONDS']}") from err

    # Resolve provider-specific settings
    if provider == "groq":
        api_key = api_key_override or os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            raise AIConfigError("GROQ_API_KEY environment variable is required when LLM_PROVIDER is 'groq'.")
        model = model_override or os.environ.get("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL
    elif provider == "openrouter":
        api_key = api_key_override or os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise AIConfigError("OPENROUTER_API_KEY environment variable is required when LLM_PROVIDER is 'openrouter'.")
        model = model_override or os.environ.get("OPENROUTER_MODEL", "").strip() or DEFAULT_OPENROUTER_MODEL
    else:
        raise AIUnsupportedProviderError(f"Unhandled provider: {provider}")

    return AIConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout,
    )

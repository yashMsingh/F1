"""OpenRouter LLM provider implementation using httpx."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.ai.config import AIConfig
from app.ai.exceptions import (
    AIAuthenticationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from app.ai.types import NarrativeRequest, NarrativeResponse
from app.ai.validation import parse_and_validate_response

logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider:
    """LLM Provider for OpenRouter API."""

    def __init__(self, config: AIConfig, client: httpx.Client | None = None) -> None:
        self.config = config
        self._client = client

    def generate(self, request: NarrativeRequest) -> NarrativeResponse:
        """Send narrative request to OpenRouter chat completions endpoint."""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yashMsingh/F1",
            "X-Title": "F1 Race Intelligence",
        }

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        client = self._client or httpx.Client(timeout=self.config.timeout_seconds)
        try:
            response = client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)
        except httpx.TimeoutException as err:
            raise AITimeoutError(
                f"OpenRouter API request timed out after {self.config.timeout_seconds}s"
            ) from err
        except httpx.RequestError as err:
            raise AIProviderError(f"OpenRouter API connection error: {err}") from err
        finally:
            if self._client is None:
                client.close()

        # Handle HTTP error codes
        if response.status_code == 401:
            raise AIAuthenticationError("OpenRouter API authentication failed. Verify OPENROUTER_API_KEY.")
        if response.status_code == 429:
            raise AIRateLimitError("OpenRouter API rate limit exceeded.")
        if response.status_code >= 400:
            raise AIProviderError(
                f"OpenRouter API returned HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            resp_data = response.json()
            content = resp_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as err:
            raise AIProviderError(f"Malformed response payload from OpenRouter: {err}") from err

        return parse_and_validate_response(content, request.insights)

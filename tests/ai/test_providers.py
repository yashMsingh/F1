"""Unit tests for Groq and OpenRouter providers with mocked HTTP client."""

import json
from unittest.mock import MagicMock

import httpx
import pytest

from app.ai.config import AIConfig
from app.ai.exceptions import (
    AIAuthenticationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from app.ai.providers import GroqProvider, OpenRouterProvider, get_provider
from app.ai.types import NarrativeRequest


@pytest.fixture
def dummy_request(sample_qualifying_insight) -> NarrativeRequest:
    return NarrativeRequest(
        insights=[sample_qualifying_insight],
        context_payload={"insights": []},
        system_prompt="System Prompt",
        user_prompt="User Prompt",
    )


class TestGroqProvider:
    def test_successful_generation(self, dummy_request):
        config = AIConfig(provider="groq", api_key="test_key", model="llama-3.3-70b-versatile")
        mock_client = MagicMock(spec=httpx.Client)

        response_json = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "narrative": "Max Verstappen was faster than Sergio Perez in qualifying by 358 ms.",
                                "limitations": ["Single race observation."],
                                "evidence_references": [dummy_request.insights[0].insight_id],
                            }
                        )
                    }
                }
            ]
        }
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = response_json
        mock_client.post.return_value = mock_response

        provider = GroqProvider(config, client=mock_client)
        resp = provider.generate(dummy_request)

        assert "Max Verstappen was faster than Sergio Perez" in resp.narrative
        assert resp.limitations == ["Single race observation."]
        assert resp.evidence_references == [dummy_request.insights[0].insight_id]

    def test_auth_error_401(self, dummy_request):
        config = AIConfig(provider="groq", api_key="bad_key", model="llama")
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = MagicMock(status_code=401, text="Unauthorized")

        provider = GroqProvider(config, client=mock_client)
        with pytest.raises(AIAuthenticationError):
            provider.generate(dummy_request)

    def test_rate_limit_429(self, dummy_request):
        config = AIConfig(provider="groq", api_key="key", model="llama")
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = MagicMock(status_code=429, text="Rate limit reached")

        provider = GroqProvider(config, client=mock_client)
        with pytest.raises(AIRateLimitError):
            provider.generate(dummy_request)

    def test_timeout_exception(self, dummy_request):
        config = AIConfig(provider="groq", api_key="key", model="llama")
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")

        provider = GroqProvider(config, client=mock_client)
        with pytest.raises(AITimeoutError):
            provider.generate(dummy_request)

    def test_malformed_response_json(self, dummy_request):
        config = AIConfig(provider="groq", api_key="key", model="llama")
        mock_client = MagicMock(spec=httpx.Client)
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"unexpected": "payload"}
        mock_client.post.return_value = mock_response

        provider = GroqProvider(config, client=mock_client)
        with pytest.raises(AIProviderError):
            provider.generate(dummy_request)


class TestOpenRouterProvider:
    def test_successful_generation(self, dummy_request):
        config = AIConfig(provider="openrouter", api_key="test_key", model="meta-llama")
        mock_client = MagicMock(spec=httpx.Client)

        response_json = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "narrative": "Max Verstappen finished ahead in qualifying by 358 ms.",
                                "limitations": ["One race."],
                                "evidence_references": ["QUALIFYING_TEAMMATE_ADVANTAGE:2024:1:max_verstappen:perez"],
                            }
                        )
                    }
                }
            ]
        }
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = response_json
        mock_client.post.return_value = mock_response

        provider = OpenRouterProvider(config, client=mock_client)
        resp = provider.generate(dummy_request)
        assert "Max Verstappen finished ahead" in resp.narrative

    def test_auth_error_401(self, dummy_request):
        config = AIConfig(provider="openrouter", api_key="bad_key", model="meta-llama")
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = MagicMock(status_code=401, text="Unauthorized")

        provider = OpenRouterProvider(config, client=mock_client)
        with pytest.raises(AIAuthenticationError):
            provider.generate(dummy_request)


class TestProviderFactory:
    def test_factory_groq(self):
        config = AIConfig(provider="groq", api_key="k", model="m")
        provider = get_provider(config)
        assert isinstance(provider, GroqProvider)

    def test_factory_openrouter(self):
        config = AIConfig(provider="openrouter", api_key="k", model="m")
        provider = get_provider(config)
        assert isinstance(provider, OpenRouterProvider)

"""Unit tests for NarrativeService orchestration."""

from unittest.mock import MagicMock

from app.ai.config import AIConfig
from app.ai.narrative import NarrativeService
from app.ai.providers.base import LLMProvider
from app.ai.types import NarrativeRequest, NarrativeResponse


class TestNarrativeService:
    def test_service_orchestration_success(self, sample_qualifying_insight):
        config = AIConfig(provider="groq", api_key="test_key", model="llama")
        mock_provider = MagicMock(spec=LLMProvider)

        expected_response = NarrativeResponse(
            narrative="Verstappen was 358ms faster than Perez.",
            limitations=["One race."],
            evidence_references=[sample_qualifying_insight.insight_id],
        )
        mock_provider.generate.return_value = expected_response

        service = NarrativeService(config=config, provider=mock_provider)
        response = service.generate_narrative(sample_qualifying_insight)

        assert response == expected_response
        mock_provider.generate.assert_called_once()
        req: NarrativeRequest = mock_provider.generate.call_args[0][0]
        assert req.insights == [sample_qualifying_insight]
        assert "EVIDENCE PACKAGE" in req.user_prompt
        assert "sole duty is to provide a concise" in req.system_prompt

    def test_service_empty_insights(self):
        config = AIConfig(provider="groq", api_key="test_key", model="llama")
        mock_provider = MagicMock(spec=LLMProvider)

        service = NarrativeService(config=config, provider=mock_provider)
        response = service.generate_narrative([])

        assert "No insights provided" in response.narrative
        mock_provider.generate.assert_not_called()

    def test_service_multi_insight_support(self, sample_qualifying_insight, sample_position_gain_insight):
        config = AIConfig(provider="openrouter", api_key="test_key", model="llama")
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.generate.return_value = NarrativeResponse("Narrative", [], [])

        service = NarrativeService(config=config, provider=mock_provider)
        service.generate_narrative([sample_qualifying_insight, sample_position_gain_insight])

        req: NarrativeRequest = mock_provider.generate.call_args[0][0]
        assert len(req.insights) == 2
        assert len(req.context_payload["insights"]) == 2

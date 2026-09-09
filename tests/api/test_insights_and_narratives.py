"""Tests for deterministic insights and AI narrative endpoints."""

from unittest.mock import MagicMock, patch

from app.ai.exceptions import AIRateLimitError
from app.ai.types import NarrativeResponse


def test_get_insights(client):
    """Verify deterministic insights endpoint returns rule findings with audit trail."""
    response = client.get("/api/races/2024/1/insights")
    assert response.status_code == 200
    data = response.json()
    assert "insights" in data
    assert "total" in data
    assert data["total"] > 0

    first_insight = data["insights"][0]
    assert "insight_id" in first_insight
    assert "rule_id" in first_insight
    assert "category" in first_insight
    assert "evidence_strength" in first_insight
    assert "traceability" in first_insight

    trace = first_insight["traceability"]
    assert "source_metric" in trace
    assert "source_function" in trace
    assert "sample_size" in trace
    assert "rule_parameters" in trace


def test_get_insights_not_found(client):
    """Verify 404 for nonexistent race insights."""
    response = client.get("/api/races/2024/999/insights")
    assert response.status_code == 404


def test_get_narrative_success(client):
    """Verify narrative endpoint returns available AI narrative when service succeeds."""
    mock_response = NarrativeResponse(
        narrative="Max Verstappen dominated the 2024 Bahrain Grand Prix from pole.",
        limitations=["Single race sample."],
        evidence_references=["qualifying_delta_millis"],
    )

    with patch("app.api.routes.narratives.NarrativeService") as mock_service_cls:
        instance = MagicMock()
        instance.generate_narrative.return_value = mock_response
        instance.config.provider = "groq"
        instance.config.model = "openai/gpt-oss-120b"
        mock_service_cls.return_value = instance

        response = client.get("/api/races/2024/1/narrative")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "available"
        assert data["provider"] == "groq"
        assert data["model"] == "openai/gpt-oss-120b"
        assert "Max Verstappen" in data["narrative"]
        assert len(data["limitations"]) == 1


def test_get_narrative_failure_isolation(client):
    """Verify AI provider failure degrades gracefully without crashing or 500 error."""
    with patch("app.api.routes.narratives.NarrativeService") as mock_service_cls:
        instance = MagicMock()
        instance.generate_narrative.side_effect = AIRateLimitError("Provider rate limit reached: 429")
        mock_service_cls.return_value = instance

        response = client.get("/api/races/2024/1/narrative")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["narrative"] is None
        assert "Provider rate limit" in data["error"]


def test_get_narrative_not_found(client):
    """Verify 404 for nonexistent race narrative."""
    response = client.get("/api/races/2024/999/narrative")
    assert response.status_code == 404

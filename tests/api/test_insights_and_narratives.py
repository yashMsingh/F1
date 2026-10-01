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


def test_post_narrative_longitudinal_driver(client):
    """Verify POST /api/narrative generates a grounded narrative for longitudinal driver evidence."""
    mock_response = NarrativeResponse(
        narrative="Max Verstappen demonstrated consistent top-tier performance across the opening 5 rounds.",
        limitations=["Longitudinal descriptive sample of 5 rounds."],
        evidence_references=["points_per_gp_start"],
    )

    with (
        patch("app.api.routes.narratives.LongitudinalInsightService.get_driver_insights") as mock_get_ins,
        patch("app.api.routes.narratives.NarrativeService") as mock_service_cls,
    ):
        mock_ins = MagicMock()
        mock_ins.insight_id = "test:driver"
        mock_get_ins.return_value = [mock_ins]

        instance = MagicMock()
        instance.generate_narrative.return_value = mock_response
        instance.config.provider = "groq"
        instance.config.model = "openai/gpt-oss-120b"
        mock_service_cls.return_value = instance

        payload = {
            "season": 2024,
            "scope": "longitudinal",
            "driver_id": "max_verstappen",
        }
        response = client.post("/api/narrative", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "available"
        assert data["scope"] == "longitudinal"
        assert "Max Verstappen" in data["narrative"]
        mock_get_ins.assert_called_once_with(
            mock_get_ins.call_args[0][0], 2024, "max_verstappen", None
        )


def test_post_narrative_longitudinal_constructor(client):
    """Verify POST /api/narrative handles constructor longitudinal requests."""
    mock_response = NarrativeResponse(
        narrative="Red Bull Racing achieved podium finishes across early rounds.",
        limitations=["5-round sample."],
        evidence_references=["podium_rate"],
    )

    with (
        patch("app.api.routes.narratives.LongitudinalInsightService.get_constructor_insights") as mock_get_ins,
        patch("app.api.routes.narratives.NarrativeService") as mock_service_cls,
    ):
        mock_ins = MagicMock()
        mock_get_ins.return_value = [mock_ins]

        instance = MagicMock()
        instance.generate_narrative.return_value = mock_response
        instance.config.provider = "openrouter"
        instance.config.model = "meta-llama/llama-3.3-70b-instruct"
        mock_service_cls.return_value = instance

        payload = {
            "season": 2024,
            "scope": "longitudinal",
            "constructor_id": "red_bull",
        }
        response = client.post("/api/narrative", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "available"
        assert data["provider"] == "openrouter"


def test_post_narrative_longitudinal_teammate(client):
    """Verify POST /api/narrative handles teammate pair requests."""
    mock_response = NarrativeResponse(
        narrative="Verstappen out-qualified Perez in all comparable sessions.",
        limitations=[],
        evidence_references=["qualifying_win_rate"],
    )

    with (
        patch("app.api.routes.narratives.LongitudinalInsightService.get_teammate_insights") as mock_get_ins,
        patch("app.api.routes.narratives.NarrativeService") as mock_service_cls,
    ):
        mock_ins = MagicMock()
        mock_get_ins.return_value = [mock_ins]

        instance = MagicMock()
        instance.generate_narrative.return_value = mock_response
        instance.config.provider = "groq"
        instance.config.model = "openai/gpt-oss-120b"
        mock_service_cls.return_value = instance

        payload = {
            "season": 2024,
            "scope": "longitudinal",
            "driver_a_id": "max_verstappen",
            "driver_b_id": "perez",
        }
        response = client.post("/api/narrative", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "available"


def test_post_narrative_race_scope(client):
    """Verify POST /api/narrative works with scope='race'."""
    mock_response = NarrativeResponse(
        narrative="Verstappen led from pole in Bahrain.",
        limitations=["Single race observation."],
        evidence_references=["qualifying_delta_millis"],
    )

    with patch("app.api.routes.narratives.NarrativeService") as mock_service_cls:
        instance = MagicMock()
        instance.generate_narrative.return_value = mock_response
        instance.config.provider = "groq"
        instance.config.model = "openai/gpt-oss-120b"
        mock_service_cls.return_value = instance

        payload = {
            "season": 2024,
            "round_num": 1,
            "scope": "race",
        }
        response = client.post("/api/narrative", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "available"
        assert data["scope"] == "race"


def test_post_narrative_invalid_scope(client):
    """Verify HTTP 400 for unsupported scope."""
    payload = {"season": 2024, "scope": "invalid_scope"}
    response = client.post("/api/narrative", json=payload)
    assert response.status_code == 400
    assert "Invalid scope" in response.json()["detail"]


def test_post_narrative_missing_round_for_race_scope(client):
    """Verify HTTP 400 when scope='race' but round_num is missing."""
    payload = {"season": 2024, "scope": "race"}
    response = client.post("/api/narrative", json=payload)
    assert response.status_code == 400
    assert "round_num" in response.json()["detail"]


def test_post_narrative_failure_isolation(client):
    """Verify provider failures degrade gracefully in POST /api/narrative."""
    with (
        patch("app.api.routes.narratives.LongitudinalInsightService.get_driver_insights") as mock_get_ins,
        patch("app.api.routes.narratives.NarrativeService") as mock_service_cls,
    ):
        mock_ins = MagicMock()
        mock_get_ins.return_value = [mock_ins]

        instance = MagicMock()
        instance.generate_narrative.side_effect = AIRateLimitError("Rate limit 429")
        mock_service_cls.return_value = instance

        payload = {"season": 2024, "scope": "longitudinal", "driver_id": "max_verstappen"}
        response = client.post("/api/narrative", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unavailable"
        assert "Rate limit" in data["error"]


def test_get_season_insights(client):
    """Verify GET /api/season/{season}/insights returns longitudinal insights."""
    with patch("app.api.routes.insights.LongitudinalInsightService.get_season_insights") as mock_get:
        mock_ins = MagicMock()
        mock_ins.insight_id = "LONGITUDINAL_POINTS_PER_START:2024:rounds_1-5:max_verstappen:none"
        mock_ins.rule_id = "LONGITUDINAL_POINTS_PER_START"
        mock_ins.category.value = "POINTS"
        mock_ins.subject_id = "max_verstappen"
        mock_ins.comparison_subject_id = None
        mock_ins.metric = "points_per_gp_start"
        mock_ins.direction.value = "higher"
        mock_ins.magnitude = 20.4
        mock_ins.unit = "points"
        mock_ins.evidence_strength.value = "HIGH"
        mock_ins.sample_size = 5
        mock_ins.explanation = "Averaged 20.4 points per start."

        mock_trace = MagicMock()
        mock_trace.source_metric = "points_per_gp_start"
        mock_trace.source_function = "compute_driver_longitudinal_stats"
        mock_trace.rule_id = "LONGITUDINAL_POINTS_PER_START"
        mock_trace.rule_parameters = {}
        mock_trace.observed_value = 20.4
        mock_trace.unit = "points"
        mock_trace.sample_size = 5
        mock_trace.minimum_sample_size = 3
        mock_trace.sign_convention = "total_gp_points / gp_starts"
        mock_trace.season_year = 2024
        mock_trace.round_num = None
        mock_trace.race_id = None
        mock_trace.driver_id = "max_verstappen"
        mock_trace.constructor_id = None
        mock_trace.rounds_included = [1, 2, 3, 4, 5]
        mock_trace.excluded_observations = 1

        mock_ins.traceability = mock_trace
        mock_get.return_value = [mock_ins]

        response = client.get("/api/season/2024/insights")
        assert response.status_code == 200
        data = response.json()
        assert data["season"] == 2024
        assert data["scope"] == "longitudinal"
        assert data["total"] == 1
        assert data["insights"][0]["rule_id"] == "LONGITUDINAL_POINTS_PER_START"
        assert data["insights"][0]["traceability"]["rounds_included"] == [1, 2, 3, 4, 5]


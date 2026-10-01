"""Phase 3E live verification — runs as a pytest test so it uses the project's
configured session fixture which auto-falls back to SQLite if Postgres unreachable."""
import json
from unittest.mock import MagicMock

import httpx
import pytest


@pytest.fixture(scope="module")
def longitudinal_session(session):
    """Re-expose the test session at module scope for these integration tests."""
    return session


def test_phase3e_driver_insights(session):
    from app.services.longitudinal_service import LongitudinalInsightService
    v = LongitudinalInsightService.get_driver_insights(session, 2024, "max_verstappen", 5)
    if not v:
        pytest.skip("No live data - postgres not reachable or dataset missing")
    rmap = {i.rule_id: i for i in v}
    pts = rmap.get("LONGITUDINAL_POINTS_PER_START")
    assert pts is not None, "Missing LONGITUDINAL_POINTS_PER_START"
    assert pts.traceability.observed_value == 20.4
    assert pts.sample_size == 5

    f_cons = rmap.get("LONGITUDINAL_FINISH_CONSISTENCY")
    assert f_cons is not None, "Missing LONGITUDINAL_FINISH_CONSISTENCY"
    assert f_cons.sample_size == 4
    assert f_cons.traceability.excluded_observations == 1


def test_phase3e_teammate_h2h(session):
    from app.services.longitudinal_service import LongitudinalInsightService
    rb = LongitudinalInsightService.get_teammate_insights(session, 2024, "max_verstappen", "perez", 5)
    if not rb:
        pytest.skip("No live data")
    rbmap = {i.rule_id: i for i in rb}
    q = rbmap.get("LONGITUDINAL_TEAMMATE_QUALIFYING_H2H")
    assert q and q.sample_size == 5 and q.magnitude == 1.0
    r = rbmap.get("LONGITUDINAL_TEAMMATE_RACE_H2H")
    assert r and r.sample_size == 4 and r.magnitude == 1.0
    pts = rbmap.get("LONGITUDINAL_TEAMMATE_POINTS_H2H")
    assert pts and pts.magnitude == 25.0


def test_phase3e_constructor(session):
    from app.services.longitudinal_service import LongitudinalInsightService
    rb = LongitudinalInsightService.get_constructor_insights(session, 2024, "red_bull", 5)
    if not rb:
        pytest.skip("No live data")
    pod = rb[0]
    assert "PODIUM_RATE" in pod.rule_id and pod.magnitude == 0.8 and pod.sample_size == 5


def test_phase3e_bearman_separation(session):
    from app.services.longitudinal_service import LongitudinalInsightService
    bearman = LongitudinalInsightService.get_teammate_insights(session, 2024, "bearman", "leclerc", 5)
    assert len(bearman) == 0, f"Bearman H2H should be 0, got {len(bearman)}"


def test_phase3e_evidence_context(session):
    from app.services.longitudinal_service import LongitudinalInsightService
    from app.ai.context import build_evidence_context
    v = LongitudinalInsightService.get_driver_insights(session, 2024, "max_verstappen", 5)
    if not v:
        pytest.skip("No live data")
    ctx = build_evidence_context(v)
    assert all(i["scope"] == "longitudinal" for i in ctx.insights)
    assert all("rounds_included" in i for i in ctx.insights)
    assert any("Longitudinal findings describe only the supplied rounds" in l for l in ctx.limitations)


def test_phase3e_contradiction_dnf_rejected(session):
    from app.services.longitudinal_service import LongitudinalInsightService
    from app.ai.validation import parse_and_validate_response
    from app.ai.exceptions import AIResponseValidationError
    import json
    v = LongitudinalInsightService.get_driver_insights(session, 2024, "max_verstappen", 5)
    if not v:
        pytest.skip("No live data")
    bad = json.dumps({"narrative": "Max Verstappen finished all 5 races.", "limitations": [], "evidence_references": []})
    with pytest.raises(AIResponseValidationError):
        parse_and_validate_response(bad, v)


def test_phase3e_contradiction_h2h_rejected(session):
    from app.services.longitudinal_service import LongitudinalInsightService
    from app.ai.validation import parse_and_validate_response
    from app.ai.exceptions import AIResponseValidationError
    import json
    rb = LongitudinalInsightService.get_teammate_insights(session, 2024, "max_verstappen", "perez", 5)
    if not rb:
        pytest.skip("No live data")
    bad = json.dumps({"narrative": "max_verstappen won 3 of 5 qualifying sessions against perez.", "limitations": [], "evidence_references": []})
    with pytest.raises(AIResponseValidationError):
        parse_and_validate_response(bad, rb)


def test_phase3e_provider_abstraction(session):
    from app.services.longitudinal_service import LongitudinalInsightService
    from app.ai.context import build_evidence_context
    from app.ai.config import AIConfig
    from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
    from app.ai.types import NarrativeRequest
    from app.ai.providers.groq import GroqProvider
    from app.ai.providers.openrouter import OpenRouterProvider
    import json

    v = LongitudinalInsightService.get_driver_insights(session, 2024, "max_verstappen", 5)
    if not v:
        pytest.skip("No live data")

    ctx = build_evidence_context(v[:3])
    ctx_payload = {"insights": ctx.insights, "limitations": ctx.limitations}
    good = json.dumps({
        "narrative": "Across the opening 5 rounds of 2024, Max Verstappen averaged 20.4 points per GP start with 1 DNF in Australia.",
        "limitations": ["5-round descriptive sample."],
        "evidence_references": ["LONGITUDINAL_POINTS_PER_START"],
    })

    req = NarrativeRequest(
        insights=v[:3],
        context_payload=ctx_payload,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_user_prompt(ctx_payload),
    )

    for ProvCls, provider_name, model in [
        (GroqProvider, "groq", "openai/gpt-oss-120b"),
        (OpenRouterProvider, "openrouter", "meta-llama/llama-3.3-70b-instruct"),
    ]:
        cfg = AIConfig(provider=provider_name, api_key="test_key", model=model)
        mock_client = MagicMock(spec=httpx.Client)
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"choices": [{"message": {"content": good}}]}
        mock_client.post.return_value = mock_resp
        prov = ProvCls(cfg, client=mock_client)
        res = prov.generate(req)
        assert "20.4 points" in res.narrative

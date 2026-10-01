"""Unit tests for longitudinal AI prompt construction and grounding instructions."""

import json

from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt


class TestLongitudinalPrompts:
    def test_narrator_role_explicitly_stated(self):
        assert "You are a narrator of supplied evidence, not an analyst" in SYSTEM_PROMPT

    def test_sample_size_and_exclusions_preserved(self):
        assert "Preserve exact sample sizes, excluded observations" in SYSTEM_PROMPT
        assert "describe only the supplied statistics" in SYSTEM_PROMPT

    def test_sprint_vs_gp_points_distinction(self):
        assert "Distinguish between Grand Prix race points and sprint points" in SYSTEM_PROMPT

    def test_no_prediction_or_causality_instructions(self):
        assert "Do not infer causality" in SYSTEM_PROMPT
        assert "predict future performance" in SYSTEM_PROMPT
        assert "Do not rank drivers against each other" in SYSTEM_PROMPT
        assert "create composite scores" in SYSTEM_PROMPT

    def test_small_sample_not_definitive(self):
        assert "Do not treat a multi-round sample" in SYSTEM_PROMPT
        assert "definitively the faster driver" in SYSTEM_PROMPT

    def test_build_user_prompt_with_longitudinal_evidence(self):
        payload = {
            "insights": [
                {
                    "insight_id": "LONGITUDINAL_POINTS_PER_START:2024:rounds_1-5:max_verstappen:none",
                    "scope": "longitudinal",
                    "subject_id": "max_verstappen",
                    "sample_size": 5,
                    "valid_observations": 5,
                    "excluded_observations": 1,
                    "rounds_included": [1, 2, 3, 4, 5],
                }
            ],
            "limitations": [
                "Longitudinal findings describe only the supplied rounds in the observed season."
            ],
        }
        prompt = build_user_prompt(payload)
        assert "EVIDENCE PACKAGE (DATA ONLY):" in prompt
        assert "LONGITUDINAL_POINTS_PER_START" in prompt
        assert "longitudinal" in prompt

        # Verify embedded JSON roundtrip
        start = prompt.find("```json\n") + len("```json\n")
        end = prompt.find("\n```", start)
        embedded_json = prompt[start:end]
        parsed = json.loads(embedded_json)
        assert parsed == payload

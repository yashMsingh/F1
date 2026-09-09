"""Unit tests for the rule registry and rule definitions."""

import pytest

from app.insights.rules import RULE_REGISTRY, get_rule


class TestRuleRegistry:
    def test_rules_have_unique_ids(self):
        rule_ids = list(RULE_REGISTRY.keys())
        assert len(rule_ids) == len(set(rule_ids))
        for rid, rule in RULE_REGISTRY.items():
            assert rule.rule_id == rid

    def test_rules_have_valid_metadata(self):
        for rid, rule in RULE_REGISTRY.items():
            assert rule.category is not None
            assert len(rule.description) > 5
            assert len(rule.metric) > 0
            assert rule.min_sample_size >= 1

    def test_get_rule_success_and_failure(self):
        rule = get_rule("QUALIFYING_TEAMMATE_ADVANTAGE")
        assert rule.rule_id == "QUALIFYING_TEAMMATE_ADVANTAGE"

        with pytest.raises(KeyError) as exc_info:
            get_rule("NON_EXISTENT_RULE")
        assert "NON_EXISTENT_RULE" in str(exc_info.value)

"""Unit tests for AI configuration loader."""

import pytest

from app.ai.config import AIConfig, load_ai_config
from app.ai.exceptions import AIConfigError, AIUnsupportedProviderError


class TestAIConfig:
    def test_load_groq_config_valid(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "test_groq_key_123456789")
        monkeypatch.setenv("GROQ_MODEL", "custom-groq-model")
        monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "45.0")

        config = load_ai_config()
        assert config.provider == "groq"
        assert config.api_key == "test_groq_key_123456789"
        assert config.model == "custom-groq-model"
        assert config.timeout_seconds == 45.0
        # Check secret masking
        assert "test_groq_key_123456789" not in repr(config)
        assert "test...6789" in repr(config)

    def test_load_openrouter_config_valid(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_or_key_abcdef123")
        monkeypatch.setenv("OPENROUTER_MODEL", "custom-or-model")

        config = load_ai_config()
        assert config.provider == "openrouter"
        assert config.api_key == "test_or_key_abcdef123"
        assert config.model == "custom-or-model"

    def test_missing_groq_api_key_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with pytest.raises(AIConfigError) as exc_info:
            load_ai_config(api_key_override="")
        assert "GROQ_API_KEY" in str(exc_info.value)

    def test_missing_openrouter_api_key_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        with pytest.raises(AIConfigError) as exc_info:
            load_ai_config(api_key_override="")
        assert "OPENROUTER_API_KEY" in str(exc_info.value)

    def test_unsupported_provider_raises(self):
        with pytest.raises(AIUnsupportedProviderError) as exc_info:
            load_ai_config(provider_override="unsupported_llm")
        assert "unsupported_llm" in str(exc_info.value)

    def test_invalid_timeout_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "key")
        monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "not_a_number")

        with pytest.raises(AIConfigError) as exc_info:
            load_ai_config()
        assert "LLM_TIMEOUT_SECONDS" in str(exc_info.value)

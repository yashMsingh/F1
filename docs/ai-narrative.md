# Grounded AI Narrative Layer

## 1. Overview & Architecture

The grounded AI narrative layer (`app/ai/`) translates already-approved deterministic insights (`app/insights/`) and their underlying statistical evidence (`app/statistics/`) into concise, human-readable Formula 1 analysis.

The LLM functions strictly as an **explanatory narrator, not an analyst**. It does not query the database, calculate statistics, invent facts, or make causal claims.

```text
Jolpica API
      ↓
API Client (Phase 2B.1)
      ↓
Parser + Validation (Phase 2B.2)
      ↓
ETL / Persistence Layer (Phase 2B.3)
      ↓
PostgreSQL / SQLite Database
      ↓
Analytical SQL Layer (Phase 2B.4)
      ↓
Statistical Evidence Layer (Phase 2B.5)
      ↓
Deterministic Insight Engine (Phase 2B.6)
      ↓
Evidence Context Builder (Phase 2B.7)  ← THIS PHASE
      ↓
LLM Provider Abstraction
  ├── Groq API
  └── OpenRouter API
      ↓
Deterministic Response Validation
      ↓
Application Consumer
```

---

## 2. Core Architectural Principles

### 2.1 The LLM is Downstream of Deterministic Analytics
The database and deterministic analytics are the sole sources of truth. The LLM receives a serialized, bounded JSON payload (`EvidencePackage`) and explains it.

### 2.2 Provider Abstraction
The system supports both **Groq** and **OpenRouter** behind a unified `LLMProvider` protocol. The application code depends solely on the abstract interface; provider switching occurs via configuration without altering business logic.

### 2.3 Prompt Injection Defense
All evidence fields are treated as **untrusted data**. The system prompt instructs the model that no string or text inside the evidence payload can alter its role, request system secrets, or bypass grounding constraints.

### 2.4 Deterministic Contradiction Checks
The application applies post-generation validation on the structured response to verify that the narrative does not contradict the underlying evidence (e.g., asserting a driver was slower when the insight direction is `FASTER`).

---

## 3. Configuration & Environment Variables

Configuration is loaded from environment variables via `app.ai.config.load_ai_config()`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | No | `groq` | Active provider: `groq` or `openrouter`. |
| `GROQ_API_KEY` | If provider is `groq` | None | API key for Groq Cloud. |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Model name for Groq completions. |
| `OPENROUTER_API_KEY` | If provider is `openrouter` | None | API key for OpenRouter. |
| `OPENROUTER_MODEL` | No | `meta-llama/llama-3.3-70b-instruct` | Model name for OpenRouter. |
| `LLM_TIMEOUT_SECONDS` | No | `30.0` | Global timeout for HTTP completion requests. |

*Security Rule*: API keys are masked in `__repr__` and never printed to logs, console, or test outputs.

---

## 4. Evidence Context & Prompts

### 4.1 Serialized Evidence Payload
The `EvidenceContext` structure bundles:
- `insights`: Serialized list of `Insight` objects with metrics, magnitudes, units, directions, and sample sizes.
- `limitations`: Explicit data limitations (e.g. absent telemetry, tyre degradation, or low sample size warnings).

### 4.2 System Prompt Enforcements
The system prompt strictly commands the LLM to:
1. Refer ONLY to values in the evidence package.
2. Never invent outside facts, telemetry, weather, or tyre degradation.
3. Respect evidence strength: when $n = 1$ (`LOW`), describe the finding as an isolated session observation, never as a persistent trend.
4. Output strictly valid JSON matching the schema.

---

## 5. Output Contract & Validation

The provider must return valid JSON parsed into a `NarrativeResponse`:

```json
{
  "narrative": "Max Verstappen outpaced teammate Sergio Perez in qualifying by 358 milliseconds.",
  "limitations": [
    "Comparison is based on a single race weekend.",
    "Telemetry and tyre telemetry are absent from this evidence package."
  ],
  "evidence_references": [
    "QUALIFYING_TEAMMATE_ADVANTAGE:2024:1:max_verstappen:perez"
  ]
}
```

Validation checks:
- `narrative`: Non-empty string.
- `limitations`: List of strings.
- `evidence_references`: List of strings.
- **Contradiction Rules**:
  - Rejects text claiming the subject was slower if the insight is `FASTER`.
  - Rejects text claiming the subject lost positions if the insight is `GAINED`.
  - Rejects text claiming the subject gained positions if the insight is `LOST`.

---

## 6. Error Handling

Provider-independent exceptions defined in `app.ai.exceptions`:
- `AIConfigError`: Missing or invalid environment configuration.
- `AIUnsupportedProviderError`: Unrecognized provider requested.
- `AIAuthenticationError`: HTTP 401 unauthorized.
- `AIRateLimitError`: HTTP 429 rate limit exceeded.
- `AITimeoutError`: Request exceeded configured timeout.
- `AIResponseValidationError`: Response failed JSON schema or contradiction checks.
- `AIProviderError`: Other provider/HTTP communication failures.

---

## 7. Testing Strategy

- **Pytest Automated Tests (`tests/ai/`)**:
  - 100% deterministic and network-independent using mocked `httpx` HTTP clients.
  - Tests cover configuration, context building, prompts, Groq provider, OpenRouter provider, validation, contradiction checks, and `NarrativeService`.
- **Manual Live Smoke Test (`scripts/smoke_test_ai.py`)**:
  - CLI script to verify real connectivity against Groq and OpenRouter using actual API keys.
  - Excluded from automated pytest execution.

---

## 8. Important Architectural Verification

> **Question**: If Groq and OpenRouter were both removed tomorrow, would the deterministic analytics, statistical evidence, and insight engine still work unchanged?
>
> **Answer**: **YES.** The analytical SQL layer (`app/analytics`), statistical evidence layer (`app/statistics`), and deterministic insight engine (`app/insights`) have zero dependencies on `app/ai`. The AI narrative layer is purely an optional downstream consumer.

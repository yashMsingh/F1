"""Manual live smoke-test script for AI narrative providers.

IMPORTANT:
- This script is for manual execution only and is NOT run by pytest.
- Never logs or prints API keys.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Ensure project root is on sys.path and stdout handles utf-8
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.ai.config import load_ai_config
from app.ai.narrative import NarrativeService
from app.insights.rules import RULE_QUALIFYING_TEAMMATE_ADVANTAGE, get_rule
from app.insights.types import (
    Direction,
    EvidenceStrength,
    Insight,
    InsightCategory,
    InsightTraceability,
)


def create_sample_insight() -> Insight:
    """Create a sample deterministic insight (Bahrain 2024 Red Bull qualifying delta)."""
    rule = get_rule(RULE_QUALIFYING_TEAMMATE_ADVANTAGE)
    traceability = InsightTraceability(
        source_metric="qualifying_delta_millis",
        source_function="get_teammate_qualifying_comparison",
        rule_id=rule.rule_id,
        rule_parameters={},
        observed_value=-358,
        unit="milliseconds",
        sample_size=1,
        minimum_sample_size=1,
        sign_convention="delta = driver_a - driver_b; negative means driver_a was faster",
        season_year=2024,
        round_num=1,
        driver_id="max_verstappen",
        constructor_id="red_bull",
    )
    return Insight(
        insight_id="QUALIFYING_TEAMMATE_ADVANTAGE:2024:1:max_verstappen:perez",
        rule_id=rule.rule_id,
        category=InsightCategory.QUALIFYING,
        subject_id="max_verstappen",
        comparison_subject_id="perez",
        metric="qualifying_delta_millis",
        direction=Direction.FASTER,
        magnitude=358.0,
        unit="milliseconds",
        evidence_strength=EvidenceStrength.LOW,
        sample_size=1,
        traceability=traceability,
    )


def run_smoke_test(provider_name: str) -> bool:
    """Run a live smoke test against the specified provider."""
    print(f"\n--- Testing Provider: {provider_name} ---")
    try:
        config = load_ai_config(provider_override=provider_name)
        print(f"Loaded config: provider='{config.provider}', model='{config.model}', timeout={config.timeout_seconds}s")

        service = NarrativeService(config=config)
        insight = create_sample_insight()

        print("Sending request to LLM provider...")
        response = service.generate_narrative(insight)

        print("\n=== SUCCESS ===")
        print(f"Provider: {config.provider}")
        print(f"Model: {config.model}")
        print(f"Insight ID: {insight.insight_id}")
        print(f"Narrative: {response.narrative}")
        print(f"Limitations: {response.limitations}")
        print(f"Evidence References: {response.evidence_references}")
        return True
    except Exception as err:
        print("\n=== FAILURE ===")
        print(f"Provider: {provider_name}")
        print(f"Error: {type(err).__name__}: {err}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Live smoke test for F1 AI Narrative Layer.")
    parser.add_argument(
        "--provider",
        choices=["groq", "openrouter", "both"],
        default="both",
        help="Which provider to test (default: both)",
    )
    args = parser.parse_args()

    providers = ["groq", "openrouter"] if args.provider == "both" else [args.provider]

    all_passed = True
    for p in providers:
        passed = run_smoke_test(p)
        if not passed:
            all_passed = False

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

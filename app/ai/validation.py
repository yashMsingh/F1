"""Deterministic validation and contradiction checks for AI narrative responses."""

from __future__ import annotations

import json
import re
from typing import Any, Sequence

from app.ai.exceptions import AIResponseValidationError
from app.ai.types import NarrativeResponse
from app.insights.types import Direction, Insight


def parse_and_validate_response(
    raw_text: str,
    insights: Sequence[Insight],
) -> NarrativeResponse:
    """Parse JSON model response and apply deterministic validation and contradiction checks.

    Args:
        raw_text: Raw string output from the LLM provider.
        insights: The approved deterministic insights used as evidence.

    Returns:
        Validated NarrativeResponse instance.

    Raises:
        AIResponseValidationError: If JSON is invalid, missing required fields,
            or directly contradicts the deterministic evidence.
    """
    if not raw_text or not raw_text.strip():
        raise AIResponseValidationError("LLM response is empty.")

    # 1. Parse JSON (handling possible markdown backticks)
    text = raw_text.strip()
    if text.startswith("```"):
        # Strip ```json and ```
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise AIResponseValidationError(f"Failed to parse LLM response as JSON: {err}") from err

    if not isinstance(data, dict):
        raise AIResponseValidationError("Parsed LLM output is not a JSON dictionary.")

    # 2. Schema checks
    narrative = data.get("narrative")
    if not isinstance(narrative, str) or not narrative.strip():
        raise AIResponseValidationError("Field 'narrative' must be a non-empty string.")

    limitations = data.get("limitations")
    if not isinstance(limitations, list):
        raise AIResponseValidationError("Field 'limitations' must be a list of strings.")

    evidence_references = data.get("evidence_references")
    if not isinstance(evidence_references, list):
        raise AIResponseValidationError("Field 'evidence_references' must be a list of strings.")

    # 3. Deterministic Contradiction Checks
    narrative_lower = narrative.lower()

    for ins in insights:
        subj = ins.subject_id.lower()
        comp = (ins.comparison_subject_id or "").lower()
        t = ins.traceability

        # Direction checks: FASTER vs SLOWER
        if ins.direction == Direction.FASTER and comp:
            # Rejects statements like "norris was slower than piastri" or "verstappen was slower"
            # if the insight claims faster
            pattern = rf"\b{re.escape(subj)}\b.*?\b(slower|deficit|behind)\b.*?\b{re.escape(comp)}\b"
            if re.search(pattern, narrative_lower):
                raise AIResponseValidationError(
                    f"Contradiction detected: Narrative states '{subj}' was slower than '{comp}', "
                    f"contradicting insight direction '{ins.direction.value}'."
                )

        # Direction checks: GAINED vs LOST
        if ins.direction == Direction.GAINED:
            # Rejects statements like "driver lost positions"
            pattern = rf"\b{re.escape(subj)}\b.*?\b(lost positions|dropped positions|lost ground)\b"
            if re.search(pattern, narrative_lower):
                raise AIResponseValidationError(
                    f"Contradiction detected: Narrative states '{subj}' lost positions, "
                    f"contradicting insight direction '{ins.direction.value}'."
                )

        if ins.direction == Direction.LOST:
            # Rejects statements like "driver gained positions"
            pattern = rf"\b{re.escape(subj)}\b.*?\b(gained positions|moved up|improved position)\b"
            if re.search(pattern, narrative_lower):
                raise AIResponseValidationError(
                    f"Contradiction detected: Narrative states '{subj}' gained positions, "
                    f"contradicting insight direction '{ins.direction.value}'."
                )

        # 4. Longitudinal Contradiction Checks

        # DNF / Finish Contradiction
        if t.excluded_observations is not None and t.excluded_observations > 0:
            total_races = (
                len(t.rounds_included)
                if t.rounds_included
                else (ins.sample_size + t.excluded_observations)
            )
            dnf_pattern = (
                rf"\b{re.escape(subj)}\b.*?\b(finished all|completed all|finished every|no dnfs?|never retired|100% finish)\b"
            )
            count_pattern = rf"\b(finished all|completed all)\s+{total_races}\b"
            if re.search(dnf_pattern, narrative_lower) or re.search(count_pattern, narrative_lower):
                raise AIResponseValidationError(
                    f"Contradiction detected: Narrative states '{subj}' finished all races / had no DNFs, "
                    f"contradicting evidence of {t.excluded_observations} excluded observation(s) (DNFs)."
                )

        # Teammate H2H Record Contradiction (e.g. "won 3 of 5" when evidence is 5 of 5)
        if ins.metric in ("qualifying_win_rate", "race_win_rate") and ins.magnitude is not None and ins.sample_size > 0:
            expected_wins = round(ins.magnitude * ins.sample_size)
            ratio_matches = re.finditer(r"\b(\d+)\s+(?:of|out of)\s+(\d+)\b", narrative_lower)
            for rm in ratio_matches:
                claimed_wins = int(rm.group(1))
                claimed_total = int(rm.group(2))
                if claimed_total == ins.sample_size and claimed_wins != expected_wins:
                    raise AIResponseValidationError(
                        f"Contradiction detected: Narrative states '{claimed_wins} of {claimed_total}' for '{subj}', "
                        f"contradicting evidence of {expected_wins} wins out of {ins.sample_size}."
                    )

            score_matches = re.finditer(r"\b(\d+)\s*-\s*(\d+)\b", narrative_lower)
            for sm in score_matches:
                w, l = int(sm.group(1)), int(sm.group(2))
                if w + l == ins.sample_size and w != expected_wins:
                    raise AIResponseValidationError(
                        f"Contradiction detected: Narrative states score '{w}-{l}' for '{subj}', "
                        f"contradicting evidence of {expected_wins}-{ins.sample_size - expected_wins}."
                    )

        # Recent form valid finishes count contradiction
        if ins.rule_id == "LONGITUDINAL_RECENT_FORM":
            finish_matches = re.finditer(r"\bacross\s+(\d+)\s+valid finishes\b", narrative_lower)
            for fm in finish_matches:
                claimed_finishes = int(fm.group(1))
                if claimed_finishes != ins.sample_size:
                    raise AIResponseValidationError(
                        f"Contradiction detected: Narrative states across '{claimed_finishes}' valid finishes, "
                        f"contradicting evidence sample size of {ins.sample_size}."
                    )

    return NarrativeResponse(
        narrative=narrative.strip(),
        limitations=[str(l) for l in limitations],
        evidence_references=[str(r) for r in evidence_references],
        raw_response=data,
    )

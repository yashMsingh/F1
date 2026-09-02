"""F1 Race Intelligence — Deterministic time string parser.

Converts F1 time/duration strings to integer milliseconds using only integer
arithmetic to avoid floating-point precision drift.

Supported formats:
    "H:MM:SS.sss"   →  e.g. "1:31:44.742"  →  5504742 ms
    "MM:SS.sss"     →  e.g. "40:55.302"     →  2455302 ms
    "M:SS.sss"      →  e.g. "1:22.167"      →  82167 ms
    "SS.sss"        →  e.g. "24.123"         →  24123 ms
    "+SS.sss"       →  e.g. "+0.500"         →  500 ms (gap)
    "+M:SS.sss"     →  e.g. "+1:02.345"      →  62345 ms (gap)

Not time durations (categorical status values — returned as-is by caller):
    "+1 Lap", "Lapped", "Finished", etc.
"""

import re
from typing import Optional

from app.f1.parsing.exceptions import F1TimeParsingError

# Regex for time formats: optional sign, then colon-separated numeric parts
# Matches: "1:31:44.742", "1:31:44", "1:22.167", "40:55.302", "24.123", "24", "+0.500", "+1:02.345"
_TIME_PATTERN = re.compile(
    r"^(?P<sign>[+-])?"
    r"(?:(?P<h>\d+):(?P<m>\d{1,2}):(?P<s>\d{1,2})(?:\.(?P<ms1>\d+))?$"  # H:MM:SS[.sss]
    r"|(?P<m2>\d+):(?P<s2>\d{1,2})(?:\.(?P<ms2>\d+))?$"                 # MM:SS[.sss] or M:SS[.sss]
    r"|(?P<s3>\d+)(?:\.(?P<ms3>\d+))?$)"                                # SS[.sss]
)


def _pad_millis(ms_str: Optional[str]) -> int:
    """Pad millisecond string to 3 digits and convert to integer.

    None   → 0
    "7"    → 700
    "74"   → 740
    "742"  → 742
    "7425" → 742
    """
    if ms_str is None:
        return 0
    padded = ms_str.ljust(3, "0")[:3]
    return int(padded)


def parse_time_to_millis(
    value: Optional[str],
    allow_negative: bool = False,
) -> Optional[int]:
    """Parse an F1 time/duration string to integer milliseconds.

    Args:
        value: Time string such as "1:22.167", "40:55.302", "1:31:44.742",
               "24.123", "+0.500". None if the source value is absent.
        allow_negative: If False (default), negative durations raise F1TimeParsingError.
                        If True, signed values (e.g. gaps) are permitted.

    Returns:
        Integer milliseconds, or None if value is None.

    Raises:
        F1TimeParsingError: If value is empty, malformed, negative (when not allowed),
                            or has invalid components.
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise F1TimeParsingError(
            f"Expected string, got {type(value).__name__}", raw_value=str(value)
        )

    stripped = value.strip()
    if not stripped:
        raise F1TimeParsingError("Empty time string", raw_value=value)

    match = _TIME_PATTERN.match(stripped)
    if match is None:
        raise F1TimeParsingError(f"Malformed time string: '{value}'", raw_value=value)

    sign = match.group("sign")
    if sign == "-" and not allow_negative:
        raise F1TimeParsingError(
            f"Negative duration not allowed: '{value}'", raw_value=value
        )

    # H:MM:SS[.sss]
    if match.group("h") is not None:
        hours = int(match.group("h"))
        minutes = int(match.group("m"))
        seconds = int(match.group("s"))
        millis = _pad_millis(match.group("ms1"))

        if minutes > 59:
            raise F1TimeParsingError(
                f"Invalid minutes ({minutes}) in '{value}'", raw_value=value
            )
        if seconds > 59:
            raise F1TimeParsingError(
                f"Invalid seconds ({seconds}) in '{value}'", raw_value=value
            )

        total = (hours * 3600 + minutes * 60 + seconds) * 1000 + millis

    # MM:SS[.sss] or M:SS[.sss]
    elif match.group("m2") is not None:
        minutes = int(match.group("m2"))
        seconds = int(match.group("s2"))
        millis = _pad_millis(match.group("ms2"))

        if seconds > 59:
            raise F1TimeParsingError(
                f"Invalid seconds ({seconds}) in '{value}'", raw_value=value
            )

        total = (minutes * 60 + seconds) * 1000 + millis

    # SS[.sss]
    elif match.group("s3") is not None:
        seconds = int(match.group("s3"))
        millis = _pad_millis(match.group("ms3"))

        total = seconds * 1000 + millis

    else:
        raise F1TimeParsingError(
            f"Unexpected match structure for '{value}'", raw_value=value
        )

    if sign == "-":
        return -total
    return total


def parse_gap_to_millis(value: Optional[str]) -> Optional[int]:
    """Parse a race time gap string to integer milliseconds.

    Handles numeric gaps like "+0.500", "+22.457", "+1:02.345".
    Returns None for non-numeric gap representations like "+1 Lap", "Lapped".
    Returns None if the value is None.

    Raises:
        F1TimeParsingError: Only if the value looks numeric but is malformed.
    """
    if value is None:
        return None

    if not isinstance(value, str):
        return None

    stripped = value.strip()
    if not stripped:
        return None

    # Non-numeric status values — not a time gap
    # e.g. "+1 Lap", "+2 Laps", "Lapped", "DNF", etc.
    if re.search(r"[a-zA-Z]", stripped):
        return None

    # At this point it looks numeric, try to parse
    return parse_time_to_millis(stripped, allow_negative=True)

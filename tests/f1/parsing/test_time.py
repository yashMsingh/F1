"""Tests for deterministic time parsing (app.f1.parsing.time)."""

import pytest

from app.f1.parsing.exceptions import F1TimeParsingError
from app.f1.parsing.time import parse_gap_to_millis, parse_time_to_millis


class TestParseTimeToMillis:
    """Unit tests for parse_time_to_millis."""

    # ── Standard valid formats ──────────────────────────────────────────

    def test_elapsed_time_hours(self):
        """1:31:44.742 -> (1*3600 + 31*60 + 44)*1000 + 742 = 5504742 ms."""
        assert parse_time_to_millis("1:31:44.742") == 5504742

    def test_lap_time_minutes(self):
        """1:22.167 -> (1*60 + 22)*1000 + 167 = 82167 ms."""
        assert parse_time_to_millis("1:22.167") == 82167

    def test_pit_stop_duration_minutes(self):
        """40:55.302 -> (40*60 + 55)*1000 + 302 = 2455302 ms."""
        assert parse_time_to_millis("40:55.302") == 2455302

    def test_short_pit_stop_seconds(self):
        """24.123 -> 24*1000 + 123 = 24123 ms."""
        assert parse_time_to_millis("24.123") == 24123

    def test_whole_seconds(self):
        """24 -> 24000 ms."""
        assert parse_time_to_millis("24") == 24000

    def test_whole_minutes_seconds_no_millis(self):
        """1:31:44 -> 5504000 ms."""
        assert parse_time_to_millis("1:31:44") == 5504000

    def test_none_returns_none(self):
        """None -> None (genuine missing value)."""
        assert parse_time_to_millis(None) is None

    # ── Boundary and parameterized cases ────────────────────────────────

    @pytest.mark.parametrize(
        ("input_str", "expected_ms"),
        [
            ("0:00.000", 0),
            ("0:00", 0),
            ("0.000", 0),
            ("0.0", 0),
            ("0", 0),
            ("0:59.999", 59999),
            ("1:00.000", 60000),
            ("59:59.999", 3599999),
            ("40:55.302", 2455302),
            ("1:00:00.000", 3600000),
            ("2:00:00.000", 7200000),
            ("0:01.005", 1005),
            ("0:01.05", 1050),
            ("0:01.5", 1500),
        ],
    )
    def test_boundary_cases(self, input_str: str, expected_ms: int):
        assert parse_time_to_millis(input_str) == expected_ms

    # ── Negative duration rejection ─────────────────────────────────────

    def test_negative_duration_rejected_by_default(self):
        with pytest.raises(F1TimeParsingError) as exc_info:
            parse_time_to_millis("-24.123")
        assert "Negative duration not allowed" in str(exc_info.value)

    def test_negative_duration_allowed_when_flag_set(self):
        assert parse_time_to_millis("-24.123", allow_negative=True) == -24123
        assert parse_time_to_millis("-1:22.167", allow_negative=True) == -82167

    # ── Malformed and invalid inputs ────────────────────────────────────

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "",
            "   ",
            "abc",
            "invalid",
            "1:22:33:44",
            "1:22.abc",
            "1:60.000",        # seconds cannot be 60
            "1:75.000",        # seconds > 59
            "1:60:00.000",     # minutes > 59 in H:MM:SS
            "1:75:30.000",     # minutes > 59 in H:MM:SS
            "1:22:65.000",     # seconds > 59 in H:MM:SS
            ":22.167",
            "1:22.",
            ".167",
        ],
    )
    def test_invalid_strings_raise_error(self, invalid_input: str):
        with pytest.raises(F1TimeParsingError):
            parse_time_to_millis(invalid_input)

    def test_non_string_type_raises_error(self):
        with pytest.raises(F1TimeParsingError):
            parse_time_to_millis(12345)  # type: ignore


class TestParseGapToMillis:
    """Unit tests for parse_gap_to_millis."""

    def test_short_gap(self):
        """+0.500 -> 500 ms."""
        assert parse_gap_to_millis("+0.500") == 500

    def test_seconds_gap(self):
        """+22.457 -> 22457 ms."""
        assert parse_gap_to_millis("+22.457") == 22457

    def test_minutes_gap(self):
        """+1:02.345 -> 62345 ms."""
        assert parse_gap_to_millis("+1:02.345") == 62345

    def test_none_returns_none(self):
        assert parse_gap_to_millis(None) is None

    def test_empty_returns_none(self):
        assert parse_gap_to_millis("") is None
        assert parse_gap_to_millis("   ") is None

    @pytest.mark.parametrize(
        "status_str",
        [
            "+1 Lap",
            "+2 Laps",
            "Lapped",
            "1 Lap",
            "Finished",
            "Retired",
            "Engine",
            "Disqualified",
        ],
    )
    def test_categorical_status_returns_none(self, status_str: str):
        """Status strings containing letters must return None, not raise."""
        assert parse_gap_to_millis(status_str) is None

    def test_malformed_numeric_gap_raises_error(self):
        """A string that looks numeric but is malformed should raise."""
        with pytest.raises(F1TimeParsingError):
            parse_gap_to_millis("+1:99.000")

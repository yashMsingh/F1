"""Independent regression checks for Grand Prix reliability/attrition analytics."""

import pytest
from sqlalchemy.orm import Session

from app.analytics.reliability_attrition import (
    _metrics,
    classify_attrition_status,
    get_reliability_attrition_report,
)


@pytest.mark.parametrize(
    ("position_text", "status", "expected"),
    [
        ("R", "Retired", "DNF"), ("17", "Retired", "DNF"),
        ("W", "Did not start", "DNS"), ("D", "Disqualified", "DSQ"),
        ("15", "Lapped", "CLASSIFIED"), ("", "", "UNKNOWN_NON_CLASSIFIED"),
    ],
)
def test_source_status_classification(position_text, status, expected):
    assert classify_attrition_status(position_text, status) == expected


def test_zero_start_denominator_is_unavailable_not_zero():
    metrics = _metrics(entries=1, starts=0, classified=0, dnf=0, dns=1, dsq=0, unknown=0)
    assert metrics.dnf_rate is None
    assert metrics.non_classification_rate is None
    assert metrics.dns_results == 1


@pytest.mark.integration
def test_2024_raw_sql_reference_totals_and_phase_boundaries(session: Session):
    """References independently calculated from raw 2024 race_results tables."""
    report = get_reliability_attrition_report(session, 2024, up_to_round=24)
    assert [(name, item.start_round, item.end_round) for name, item in report.phases.items()] == [
        ("Early", 1, 8), ("Middle", 9, 16), ("Late", 17, 24)
    ]
    expected = {
        "Early": (159, 159, 142, 17, 0, 0),
        "Middle": (160, 159, 149, 9, 1, 1),
        "Late": (160, 158, 134, 23, 2, 1),
    }
    for name, values in expected.items():
        metrics = report.phases[name].total
        assert report.phases[name].is_complete is True
        assert (metrics.entries, metrics.starts, metrics.classified_finishes, metrics.dnf_results, metrics.dns_results, metrics.dsq_results) == values

    totals = tuple(sum(getattr(phase.total, field) for phase in report.phases.values()) for field in ("entries", "starts", "classified_finishes", "dnf_results", "dns_results", "dsq_results"))
    assert totals == (479, 476, 425, 49, 3, 2)
    assert len(report.rounds) == 24


@pytest.mark.integration
def test_constructor_driver_zero_and_substitution_references(session: Session):
    report = get_reliability_attrition_report(session, 2024, up_to_round=24)
    full = report.phases["Early"].constructors
    assert len(full) == 10
    assert full["mclaren"].metrics.dnf_results == 0
    assert full["mclaren"].metrics.dnf_rate == 0.0

    all_constructor_totals = {cid: sum(phase.constructors[cid].metrics.dnf_results for phase in report.phases.values()) for cid in report.phases["Early"].constructors}
    assert all_constructor_totals == {"alpine": 5, "aston_martin": 4, "ferrari": 4, "haas": 4, "mclaren": 0, "mercedes": 4, "rb": 7, "red_bull": 6, "sauber": 4, "williams": 11}
    # Bearman's R2 Ferrari result belongs to Ferrari event attribution; he retired zero times there.
    assert report.phases["Early"].drivers["bearman"].metrics.entries == 1
    assert report.phases["Early"].drivers["bearman"].metrics.dnf_results == 0
    assert report.phases["Early"].constructors["ferrari"].metrics.entries == 16


@pytest.mark.integration
def test_incomplete_period_is_unavailable_not_zero(session: Session):
    report = get_reliability_attrition_report(session, 2024, up_to_round=7)
    early = report.phases["Early"]
    assert early.is_complete is False
    assert early.total.entries is None
    assert early.total.dnf_rate is None
    assert early.constructors == {}
    assert early.drivers == {}

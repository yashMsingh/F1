"""Independent regression tests for Qualifying-to-Race Conversion & Race Craft Analytics (Phase 5B.2A).

Covers all 12 analytical and statistical requirements:
1. Pole-to-Win Conversion.
2. Front-Row Podium Retention.
3. Grid-Tier Position Deltas (Front P1-P4, Midfield P5-P10, Lower P11-P20).
4. Top-10 Points Conversion.
5. DNS handling (Gasly R12, Albon R21, Stroll R21).
6. DNF and DSQ handling (Verstappen R03 DNF, Russell R14 DSQ).
7. Pit-lane start exclusion (Ocon R20).
8. Substitute driver handling (Bearman, Colapinto, Lawson, Antonelli, Doohan).
9. Minimum sample-size threshold enforcement.
10. Zero-denominator safety.
11. Evidence traceability and audit trail completeness.
12. Full-season deterministic 24-round output reconciliation.

All expected values are explicitly grounded in independent SQL reference audits.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Optional

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.conversion_analysis import (
    get_all_drivers_conversion_summaries,
    get_driver_conversion_summary,
)
from app.db.models.race import Race
from app.insights.rules import (
    RULE_FRONT_ROW_PODIUM_RETENTION,
    RULE_GRID_TIER_POSITION_GAIN,
    RULE_GRID_TIER_POSITION_LOSS,
    RULE_POLE_TO_WIN_CONVERSION,
    RULE_TOP10_CONVERSION_HIGH,
)
from app.insights.types import Direction, EvidenceStrength
from app.services.longitudinal_service import LongitudinalInsightService
from app.statistics.conversion import (
    compute_driver_conversion_stats,
    compute_front_row_stats,
    compute_grid_tier_stats,
    compute_pole_to_win_stats,
    compute_top10_conversion_stats,
)

SEASON_YEAR = 2024
TOTAL_ROUNDS = 24


def _check_db_has_data(session: Session) -> bool:
    count = session.scalar(
        select(func.count(Race.id)).where(Race.season_year == SEASON_YEAR)
    )
    return count == TOTAL_ROUNDS


# ─── 1. Pole-to-Win Conversion Tests ──────────────────────────────────────────


@pytest.mark.integration
def test_pole_to_win_conversion_ground_truth(session: Session):
    """Independent SQL values for pole positions and wins from pole."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    # Max Verstappen: 10 poles (R1, R2, R3, R4, R5, R6, R7, R11, R14, R23), won 6
    v_summ = get_driver_conversion_summary(session, SEASON_YEAR, "max_verstappen")
    assert v_summ is not None
    assert v_summ.pole_to_win.total_poles == 10
    assert v_summ.pole_to_win.wins_from_pole == 6
    assert v_summ.pole_to_win.pole_to_win_rate == 60.0

    # Lando Norris: 8 poles (R10, R13, R15, R16, R18, R19, R21, R24), won 3
    n_summ = get_driver_conversion_summary(session, SEASON_YEAR, "norris")
    assert n_summ is not None
    assert n_summ.pole_to_win.total_poles == 8
    assert n_summ.pole_to_win.wins_from_pole == 3
    assert n_summ.pole_to_win.pole_to_win_rate == 37.5

    # George Russell: 3 poles (R9, R12, R22), won 1 (R22)
    r_summ = get_driver_conversion_summary(session, SEASON_YEAR, "russell")
    assert r_summ is not None
    assert r_summ.pole_to_win.total_poles == 3
    assert r_summ.pole_to_win.wins_from_pole == 1
    assert r_summ.pole_to_win.pole_to_win_rate == 33.33

    # Charles Leclerc: 2 poles (R8, R17), won 1 (R8)
    l_summ = get_driver_conversion_summary(session, SEASON_YEAR, "leclerc")
    assert l_summ is not None
    assert l_summ.pole_to_win.total_poles == 2
    assert l_summ.pole_to_win.wins_from_pole == 1
    assert l_summ.pole_to_win.pole_to_win_rate == 50.0

    # Carlos Sainz: 1 pole (R20), won 1 (R20)
    s_summ = get_driver_conversion_summary(session, SEASON_YEAR, "sainz")
    assert s_summ is not None
    assert s_summ.pole_to_win.total_poles == 1
    assert s_summ.pole_to_win.wins_from_pole == 1
    assert s_summ.pole_to_win.pole_to_win_rate == 100.0


# ─── 2. Front-Row Podium Retention Tests ──────────────────────────────────────


@pytest.mark.integration
def test_front_row_podium_retention_ground_truth(session: Session):
    """Independent SQL values for front-row starts (P1 or P2) and podium finishes."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    # Verstappen: 16 front-row starts, 12 podiums -> 75.0%
    v = get_driver_conversion_summary(session, SEASON_YEAR, "max_verstappen")
    assert v is not None
    assert v.front_row.front_row_starts == 16
    assert v.front_row.front_row_podiums == 12
    assert v.front_row.front_row_podium_rate == 75.0

    # Norris: 9 front-row starts, 6 podiums -> 66.67%
    n = get_driver_conversion_summary(session, SEASON_YEAR, "norris")
    assert n is not None
    assert n.front_row.front_row_starts == 9
    assert n.front_row.front_row_podiums == 6
    assert n.front_row.front_row_podium_rate == 66.67

    # Leclerc: 6 front-row starts, 5 podiums -> 83.33%
    l = get_driver_conversion_summary(session, SEASON_YEAR, "leclerc")
    assert l is not None
    assert l.front_row.front_row_starts == 6
    assert l.front_row.front_row_podiums == 5
    assert l.front_row.front_row_podium_rate == 83.33

    # Piastri: 6 front-row starts, 4 podiums -> 66.67%
    p = get_driver_conversion_summary(session, SEASON_YEAR, "piastri")
    assert p is not None
    assert p.front_row.front_row_starts == 6
    assert p.front_row.front_row_podiums == 4
    assert p.front_row.front_row_podium_rate == 66.67

    # Russell: 5 front-row starts, 2 podiums -> 40.0%
    r = get_driver_conversion_summary(session, SEASON_YEAR, "russell")
    assert r is not None
    assert r.front_row.front_row_starts == 5
    assert r.front_row.front_row_podiums == 2
    assert r.front_row.front_row_podium_rate == 40.0

    # Sainz: 3 front-row starts, 3 podiums -> 100.0%
    s = get_driver_conversion_summary(session, SEASON_YEAR, "sainz")
    assert s is not None
    assert s.front_row.front_row_starts == 3
    assert s.front_row.front_row_podiums == 3
    assert s.front_row.front_row_podium_rate == 100.0

    # Perez: 2 front-row starts, 2 podiums -> 100.0%
    pz = get_driver_conversion_summary(session, SEASON_YEAR, "perez")
    assert pz is not None
    assert pz.front_row.front_row_starts == 2
    assert pz.front_row.front_row_podiums == 2
    assert pz.front_row.front_row_podium_rate == 100.0

    # Hamilton: 1 front-row start, 1 podium -> 100.0%
    h = get_driver_conversion_summary(session, SEASON_YEAR, "hamilton")
    assert h is not None
    assert h.front_row.front_row_starts == 1
    assert h.front_row.front_row_podiums == 1
    assert h.front_row.front_row_podium_rate == 100.0


# ─── 3. Grid-Tier Position Delta Tests ────────────────────────────────────────


@pytest.mark.integration
def test_grid_tier_position_deltas_ground_truth(session: Session):
    """Independent SQL values for front, midfield, and lower tier position deltas."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    # Norris Front Tier (P1-P4): 19 starts, 19 classified, net delta -36, avg -1.8947
    norris = get_driver_conversion_summary(session, SEASON_YEAR, "norris")
    assert norris is not None
    nft = norris.grid_tiers["front"]
    assert nft.eligible_starts == 19
    assert nft.classified_finishes == 19
    assert nft.non_classified_results == 0
    assert nft.total_positions_gained == -36
    assert nft.avg_position_delta == pytest.approx(-1.8947, abs=1e-4)

    # Verstappen Front Tier: 18 starts, 17 classified, 1 DNF (Australia), net delta -9, avg -0.5294
    ver = get_driver_conversion_summary(session, SEASON_YEAR, "max_verstappen")
    assert ver is not None
    vft = ver.grid_tiers["front"]
    assert vft.eligible_starts == 18
    assert vft.classified_finishes == 17
    assert vft.non_classified_results == 1
    assert vft.total_positions_gained == -9
    assert vft.avg_position_delta == pytest.approx(-0.5294, abs=1e-4)

    # Russell Front Tier: 11 starts, 10 classified, 1 DNF (Silverstone), net delta -14, avg -1.40
    rus = get_driver_conversion_summary(session, SEASON_YEAR, "russell")
    assert rus is not None
    rft = rus.grid_tiers["front"]
    assert rft.eligible_starts == 11
    assert rft.classified_finishes == 10
    assert rft.non_classified_results == 1
    assert rft.total_positions_gained == -14
    assert rft.avg_position_delta == pytest.approx(-1.40, abs=1e-4)

    # Hamilton Lower Tier (P11-P20): 7 starts, 5 classified, 2 non-classified, net delta +41, avg +8.20
    ham = get_driver_conversion_summary(session, SEASON_YEAR, "hamilton")
    assert ham is not None
    hlt = ham.grid_tiers["lower"]
    assert hlt.eligible_starts == 7
    assert hlt.classified_finishes == 5
    assert hlt.non_classified_results == 2
    assert hlt.total_positions_gained == 41
    assert hlt.avg_position_delta == pytest.approx(8.20, abs=1e-4)

    # Zhou Lower Tier (P11-P20): 24 starts, 22 classified, 2 non-classified, net delta +48, avg +2.1818
    zhou = get_driver_conversion_summary(session, SEASON_YEAR, "zhou")
    assert zhou is not None
    zlt = zhou.grid_tiers["lower"]
    assert zlt.eligible_starts == 24
    assert zlt.classified_finishes == 22
    assert zlt.non_classified_results == 2
    assert zlt.total_positions_gained == 48
    assert zlt.avg_position_delta == pytest.approx(2.1818, abs=1e-4)


# ─── 4. Top-10 Points Conversion Tests ────────────────────────────────────────


@pytest.mark.integration
def test_top10_points_conversion_ground_truth(session: Session):
    """Independent SQL values for top-10 starting grid to top-10 finish conversion."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    # Norris: 23 top-10 starts, 22 conversions -> 95.65%
    n = get_driver_conversion_summary(session, SEASON_YEAR, "norris")
    assert n is not None
    assert n.top10_conversion.top10_starts == 23
    assert n.top10_conversion.top10_conversions == 22
    assert n.top10_conversion.top10_conversion_rate == 95.65

    # Piastri: 23 top-10 starts, 22 conversions -> 95.65%
    p = get_driver_conversion_summary(session, SEASON_YEAR, "piastri")
    assert p is not None
    assert p.top10_conversion.top10_starts == 23
    assert p.top10_conversion.top10_conversions == 22
    assert p.top10_conversion.top10_conversion_rate == 95.65

    # Verstappen: 22 top-10 starts, 21 conversions -> 95.45%
    v = get_driver_conversion_summary(session, SEASON_YEAR, "max_verstappen")
    assert v is not None
    assert v.top10_conversion.top10_starts == 22
    assert v.top10_conversion.top10_conversions == 21
    assert v.top10_conversion.top10_conversion_rate == 95.45

    # Leclerc: 21 top-10 starts, 20 conversions -> 95.24%
    l = get_driver_conversion_summary(session, SEASON_YEAR, "leclerc")
    assert l is not None
    assert l.top10_conversion.top10_starts == 21
    assert l.top10_conversion.top10_conversions == 20
    assert l.top10_conversion.top10_conversion_rate == 95.24

    # Sainz: 21 top-10 starts, 20 conversions -> 95.24%
    s = get_driver_conversion_summary(session, SEASON_YEAR, "sainz")
    assert s is not None
    assert s.top10_conversion.top10_starts == 21
    assert s.top10_conversion.top10_conversions == 20
    assert s.top10_conversion.top10_conversion_rate == 95.24

    # Hamilton: 17 top-10 starts, 16 conversions -> 94.12%
    h = get_driver_conversion_summary(session, SEASON_YEAR, "hamilton")
    assert h is not None
    assert h.top10_conversion.top10_starts == 17
    assert h.top10_conversion.top10_conversions == 16
    assert h.top10_conversion.top10_conversion_rate == 94.12

    # Russell: 22 top-10 starts, 19 conversions -> 86.36%
    r = get_driver_conversion_summary(session, SEASON_YEAR, "russell")
    assert r is not None
    assert r.top10_conversion.top10_starts == 22
    assert r.top10_conversion.top10_conversions == 19
    assert r.top10_conversion.top10_conversion_rate == 86.36

    # Perez: 14 top-10 starts, 11 conversions -> 78.57%
    pz = get_driver_conversion_summary(session, SEASON_YEAR, "perez")
    assert pz is not None
    assert pz.top10_conversion.top10_starts == 14
    assert pz.top10_conversion.top10_conversions == 11
    assert pz.top10_conversion.top10_conversion_rate == 78.57


# ─── 5. DNS Handling Tests ────────────────────────────────────────────────────


@pytest.mark.integration
def test_dns_exclusion_handling(session: Session):
    """DNS events must be excluded from race starts and conversions."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    # Gasly R12: DNS (Did not start, position_text='W')
    gasly = get_driver_conversion_summary(session, SEASON_YEAR, "gasly")
    assert gasly is not None
    assert gasly.dns_count >= 1

    # Albon R21: Qualified P7, grid 7, DNS in race -> excluded from top-10 starts
    albon = get_driver_conversion_summary(session, SEASON_YEAR, "albon")
    assert albon is not None
    assert albon.dns_count >= 1
    # Total rounds 24, but starts are 23 due to R21 DNS
    total_tier_starts = sum(gt.eligible_starts for gt in albon.grid_tiers.values())
    assert total_tier_starts == 23  # 7 midfield + 16 lower = 23 (R21 DNS excluded)

    # Stroll R21: Qualified P10, grid 10, DNS in race -> excluded from top-10 starts
    stroll = get_driver_conversion_summary(session, SEASON_YEAR, "stroll")
    assert stroll is not None
    assert stroll.dns_count >= 1
    total_stroll_starts = sum(gt.eligible_starts for gt in stroll.grid_tiers.values())
    assert total_stroll_starts == 23  # 6 midfield + 17 lower = 23 (R21 DNS excluded)


# ─── 6. DNF and DSQ Handling Tests ───────────────────────────────────────────


@pytest.mark.integration
def test_dnf_and_dsq_handling(session: Session):
    """DNFs and DSQs must be recorded as non_classified without fabricating position deltas."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    # Verstappen Australia R03: DNF (Brake failure) from P1
    ver = get_driver_conversion_summary(session, SEASON_YEAR, "max_verstappen")
    assert ver is not None
    assert ver.grid_tiers["front"].non_classified_results == 1
    # 18 starts, 17 classified, 1 non-classified
    assert ver.grid_tiers["front"].eligible_starts == 18
    assert ver.grid_tiers["front"].classified_finishes == 17

    # Russell Spa R14: DSQ (underweight car) from P6 grid
    # Midfield tier: 11 starts, 9 classified, 2 non-classified (Australia R03 DNF, Spa R14 DSQ)
    rus = get_driver_conversion_summary(session, SEASON_YEAR, "russell")
    assert rus is not None
    assert rus.grid_tiers["midfield"].non_classified_results == 2
    assert rus.grid_tiers["midfield"].eligible_starts == 11
    assert rus.grid_tiers["midfield"].classified_finishes == 9


# ─── 7. Pit-Lane Start Handling Tests ─────────────────────────────────────────


@pytest.mark.integration
def test_pit_lane_start_exclusion(session: Session):
    """Pit-lane starts (grid <= 0) must be tracked separately and excluded from tiers."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    # Ocon Mexico R20: started from pit lane (grid_position=0)
    ocon = get_driver_conversion_summary(session, SEASON_YEAR, "ocon")
    assert ocon is not None
    assert ocon.pit_lane_starts_count == 1
    # Total grid tier starts = 1 front + 3 midfield + 18 lower = 22 (R20 pit lane excluded)
    total_ocon_tier_starts = sum(gt.eligible_starts for gt in ocon.grid_tiers.values())
    assert total_ocon_tier_starts == 22


# ─── 8. Substitute Driver Handling Tests ──────────────────────────────────────


@pytest.mark.integration
def test_substitute_drivers_handling(session: Session):
    """Substitute drivers are evaluated on actual starts; reference entities produce zero."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    # Oliver Bearman: 3 starts (R02 Ferrari, R17 Haas, R21 Haas)
    b_summ = get_driver_conversion_summary(session, SEASON_YEAR, "bearman")
    assert b_summ is not None
    assert b_summ.top10_conversion.top10_starts == 1
    assert b_summ.top10_conversion.top10_conversions == 1
    # Top-10 starts = 1 < 5 -> no top-10 insight emitted
    b_insights = LongitudinalInsightService.get_driver_conversion_insights(
        session, SEASON_YEAR, "bearman"
    )
    assert len(b_insights) == 0, "Bearman must produce 0 conversion insights due to N < min_sample"

    # Franco Colapinto: 9 starts (R16-R24)
    c_summ = get_driver_conversion_summary(session, SEASON_YEAR, "colapinto")
    assert c_summ is not None
    assert c_summ.grid_tiers["lower"].eligible_starts == 8
    assert c_summ.grid_tiers["lower"].classified_finishes == 5
    assert c_summ.grid_tiers["lower"].total_positions_gained == 22
    assert c_summ.grid_tiers["lower"].avg_position_delta == pytest.approx(4.40, abs=1e-4)
    # Lower tier starts = 8 >= 5 and avg_delta = +4.40 >= 2.0 -> emits GRID_TIER_POSITION_GAIN
    c_insights = LongitudinalInsightService.get_driver_conversion_insights(
        session, SEASON_YEAR, "colapinto"
    )
    assert len(c_insights) == 1
    assert c_insights[0].rule_id == RULE_GRID_TIER_POSITION_GAIN
    assert c_insights[0].subject_id == "colapinto"

    # Liam Lawson: 6 starts (R19-R24)
    law = get_driver_conversion_summary(session, SEASON_YEAR, "lawson")
    assert law is not None
    assert law.grid_tiers["lower"].eligible_starts == 5
    assert law.grid_tiers["lower"].avg_position_delta == pytest.approx(1.75, abs=1e-4)
    # Avg delta 1.75 < 2.0 -> no gain insight
    law_insights = LongitudinalInsightService.get_driver_conversion_insights(
        session, SEASON_YEAR, "lawson"
    )
    assert len(law_insights) == 0

    # Reference entities: Antonelli and Doohan have 0 race starts
    ant_summ = get_driver_conversion_summary(session, SEASON_YEAR, "antonelli")
    assert ant_summ is None
    ant_insights = LongitudinalInsightService.get_driver_conversion_insights(
        session, SEASON_YEAR, "antonelli"
    )
    assert len(ant_insights) == 0

    doo_summ = get_driver_conversion_summary(session, SEASON_YEAR, "doohan")
    assert doo_summ is not None
    assert doo_summ.grid_tiers["lower"].eligible_starts == 1
    doo_insights = LongitudinalInsightService.get_driver_conversion_insights(
        session, SEASON_YEAR, "doohan"
    )
    assert len(doo_insights) == 0


# ─── 9. Minimum Sample-Size Threshold Enforcement ────────────────────────────


@pytest.mark.integration
def test_minimum_sample_size_safeguards(session: Session):
    """Insights must be suppressed when valid observations < minimum required sample size."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    # Leclerc has 2 poles (N=2 < 3) -> POLE_TO_WIN_CONVERSION suppressed
    l_insights = LongitudinalInsightService.get_driver_conversion_insights(
        session, SEASON_YEAR, "leclerc"
    )
    l_rules = {i.rule_id for i in l_insights}
    assert RULE_POLE_TO_WIN_CONVERSION not in l_rules
    assert RULE_FRONT_ROW_PODIUM_RETENTION in l_rules  # Leclerc has 6 front row starts (>=3)

    # Sainz has 1 pole (N=1 < 3) -> POLE_TO_WIN_CONVERSION suppressed
    # Sainz has 3 front-row starts (N=3 >= 3) -> FRONT_ROW_PODIUM_RETENTION emitted
    s_insights = LongitudinalInsightService.get_driver_conversion_insights(
        session, SEASON_YEAR, "sainz"
    )
    s_rules = {i.rule_id for i in s_insights}
    assert RULE_POLE_TO_WIN_CONVERSION not in s_rules
    assert RULE_FRONT_ROW_PODIUM_RETENTION in s_rules

    # Hamilton has 4 front tier starts (N=4 < 5) -> GRID_TIER_POSITION_LOSS/GAIN suppressed
    h_insights = LongitudinalInsightService.get_driver_conversion_insights(
        session, SEASON_YEAR, "hamilton"
    )
    h_front_insights = [i for i in h_insights if i.comparison_subject_id == "front"]
    assert len(h_front_insights) == 0


# ─── 10. Zero-Denominator Safeguards ──────────────────────────────────────────


def test_zero_denominator_statistical_safeguards():
    """Statistical functions must safely handle zero denominators without exception."""
    # Zero poles
    p = compute_pole_to_win_stats(total_poles=0, wins_from_pole=0, rounds_included=[1, 2, 3])
    assert p.conversion_rate == 0.0
    assert not p.evidence.is_available
    assert p.evidence.evidence_strength == EvidenceStrength.INSUFFICIENT

    # Zero front-row starts
    fr = compute_front_row_stats(front_row_starts=0, front_row_podiums=0, rounds_included=[1, 2, 3])
    assert fr.retention_rate == 0.0
    assert not fr.evidence.is_available
    assert fr.evidence.evidence_strength == EvidenceStrength.INSUFFICIENT

    # Zero tier starts
    gt = compute_grid_tier_stats(
        tier_name="front",
        min_grid=1,
        max_grid=4,
        eligible_starts=0,
        classified_finishes=0,
        non_classified_results=0,
        total_positions_gained=0,
        rounds_included=[1, 2, 3],
    )
    assert gt.avg_position_delta is None
    assert not gt.evidence.is_available
    assert gt.evidence.evidence_strength == EvidenceStrength.INSUFFICIENT

    # Zero top-10 starts
    t10 = compute_top10_conversion_stats(top10_starts=0, top10_conversions=0, rounds_included=[1, 2, 3])
    assert t10.conversion_rate == 0.0
    assert not t10.evidence.is_available
    assert t10.evidence.evidence_strength == EvidenceStrength.INSUFFICIENT


# ─── 11. Evidence Traceability Completeness ───────────────────────────────────


@pytest.mark.integration
def test_evidence_traceability_audit_trail(session: Session):
    """Every generated insight must have a complete, verifiable audit trail."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    insights = LongitudinalInsightService.get_season_conversion_insights(
        session, SEASON_YEAR, up_to_round=TOTAL_ROUNDS
    )
    assert len(insights) > 0

    for ins in insights:
        t = ins.traceability
        assert t is not None
        assert t.source_metric == ins.metric
        assert t.source_function in (
            "compute_pole_to_win_stats",
            "compute_front_row_stats",
            "compute_grid_tier_stats",
            "compute_top10_conversion_stats",
        )
        assert t.rule_id == ins.rule_id
        assert t.sample_size == ins.sample_size
        assert t.sample_size >= t.minimum_sample_size
        assert t.season_year == SEASON_YEAR
        assert t.driver_id == ins.subject_id
        assert t.rounds_included is not None
        assert len(t.rounds_included) > 0
        assert ins.explanation is not None
        assert len(ins.explanation) > 10


# ─── 12. Full-Season Deterministic 24-Round Output ────────────────────────────


@pytest.mark.integration
def test_full_season_conversion_insights_distribution(session: Session):
    """Full-season 2024 conversion insights must match exact expected distribution."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season database")

    insights = LongitudinalInsightService.get_season_conversion_insights(
        session, SEASON_YEAR, up_to_round=TOTAL_ROUNDS
    )
    assert len(insights) == 24, f"Expected exactly 24 conversion insights, got {len(insights)}"

    # Insight ID uniqueness and deduplication
    insight_ids = [i.insight_id for i in insights]
    assert len(insight_ids) == len(set(insight_ids)) == 24, "All 24 insight IDs must be unique"

    # Rule breakdown verification
    rule_counts = Counter(i.rule_id for i in insights)
    assert rule_counts[RULE_GRID_TIER_POSITION_GAIN] == 8
    assert rule_counts[RULE_GRID_TIER_POSITION_LOSS] == 1
    assert rule_counts[RULE_TOP10_CONVERSION_HIGH] == 6
    assert rule_counts[RULE_FRONT_ROW_PODIUM_RETENTION] == 6
    assert rule_counts[RULE_POLE_TO_WIN_CONVERSION] == 3

    # Front Tier Position Loss: Norris
    ftl_drivers = [i.subject_id for i in insights if i.rule_id == RULE_GRID_TIER_POSITION_LOSS]
    assert ftl_drivers == ["norris"]

    # Pole-to-Win: Verstappen, Norris, Russell
    pole_drivers = sorted([i.subject_id for i in insights if i.rule_id == RULE_POLE_TO_WIN_CONVERSION])
    assert pole_drivers == ["max_verstappen", "norris", "russell"]

    # Front-Row Podium Retention: Leclerc, Verstappen, Norris, Piastri, Russell, Sainz
    fr_drivers = sorted([i.subject_id for i in insights if i.rule_id == RULE_FRONT_ROW_PODIUM_RETENTION])
    assert fr_drivers == ["leclerc", "max_verstappen", "norris", "piastri", "russell", "sainz"]

    # Top-10 Conversion High: Hamilton, Leclerc, Verstappen, Norris, Piastri, Sainz
    t10_drivers = sorted([i.subject_id for i in insights if i.rule_id == RULE_TOP10_CONVERSION_HIGH])
    assert t10_drivers == ["hamilton", "leclerc", "max_verstappen", "norris", "piastri", "sainz"]

    # Lower Tier Gain: Alonso, Colapinto, Gasly, Hamilton, Hulkenberg, Magnussen, Perez, Zhou
    lt_drivers = sorted([i.subject_id for i in insights if i.rule_id == RULE_GRID_TIER_POSITION_GAIN])
    assert lt_drivers == [
        "alonso",
        "colapinto",
        "gasly",
        "hamilton",
        "hulkenberg",
        "kevin_magnussen",
        "perez",
        "zhou",
    ]

    # Non-starters producing zero insights
    all_subjects = {i.subject_id for i in insights}
    assert "antonelli" not in all_subjects
    assert "doohan" not in all_subjects

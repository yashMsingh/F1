"""Tests for longitudinal analytics across the expanded 2024 Rounds 1-10 dataset.

Verifies driver trajectories, season aggregates, teammate comparisons,
rolling-window statistics, and deterministic insights against the 10-round historical data.

Ground-truth facts verified in Phase 4C:
  - Rounds 1-10 coverage (Bahrain through Spain)
  - Sprint rounds: Round 5 (China) and Round 6 (Miami)
  - Max Verstappen: 10 starts, 9 classified finishes, 1 DNF (Australia),
    203.00 race points, 16.00 sprint points, 219.00 total points, 7 wins
  - Red Bull: 330.00 total points, 7 wins
  - Teammates: Verstappen and Perez were teammates for 10 rounds,
    with 7 comparable race finishes (due to Verstappen DNF in R3 and Perez DNFs in R8, R9)
  - Ferrari substitutions: Bearman subbed in Round 2 (1 round with Leclerc);
    Sainz and Leclerc were teammates for 9 rounds
  - Rolling-window: Verstappen's last 3 rounds (R8 Monaco P6, R9 Canada P1, R10 Spain P1)
    yield an average finish of 2.67 (8/3)
  - Longitudinal rate metrics: 21.90 points per round, 20.30 points per GP start
  - Insufficient sample: Oliver Bearman (N=1) suppresses all longitudinal insights
"""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.analytics.longitudinal_constructor import (
    get_constructor_season_aggregate,
    get_constructor_trajectory,
)
from app.analytics.longitudinal_driver import (
    get_driver_season_aggregate,
    get_driver_trajectory,
)
from app.analytics.longitudinal_teammate import (
    get_event_teammate_comparisons,
    get_season_teammate_comparisons,
)
from app.services.longitudinal_service import LongitudinalInsightService
from app.statistics.longitudinal import compute_driver_form_summary

SEASON_YEAR = 2024
TOTAL_ROUNDS = 10


def _check_db_has_data(session: Session) -> bool:
    """Helper to check if 10-round data is available in the current session."""
    from sqlalchemy import func, select
    from app.db.models.race import Race
    count = session.scalar(
        select(func.count(Race.id)).where(Race.season_year == SEASON_YEAR, Race.round <= TOTAL_ROUNDS)
    )
    return (count or 0) >= TOTAL_ROUNDS


# ─── 1. Verstappen Driver Aggregate Tests ────────────────────────────────────


def test_verstappen_ten_round_aggregate(session: Session):
    """Verstappen through Round 10: 10 starts, 9 classified, 1 DNF, 203 race pts, 16 sprint pts, 219 total, 7 wins."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-10 database")

    # Verify explicit up_to_round=10 (preserving 10-round historical semantics)
    agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen", up_to_round=TOTAL_ROUNDS)
    assert agg is not None, "Verstappen aggregate should exist"
    assert agg.races_entered == 10, "Should have 10 GP starts"
    assert agg.races_classified == 9, "Should have 9 classified finishes"
    assert agg.dnf_count == 1, "Should have 1 DNF (Australia Round 3)"
    assert agg.total_race_points == Decimal("203.00"), "Should have 203.00 GP race points"
    assert agg.total_sprint_points == Decimal("16.00"), "Should have 16.00 sprint points (China 8 + Miami 8)"
    assert agg.total_points == Decimal("219.00"), "Should have 219.00 total championship points"
    assert agg.wins == 7, "Should have 7 Grand Prix wins (R1, R2, R4, R5, R7, R9, R10)"
    assert agg.championship_standing == 1, "Should be P1 in championship standings"


def test_verstappen_ten_round_trajectory_counts(session: Session):
    """Verstappen trajectory across Rounds 1-10 should contain exactly 10 round items."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-10 database")

    traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen", up_to_round=10)
    assert len(traj) == 10
    rounds = [t.round for t in traj]
    assert rounds == list(range(1, 11))

    # Verify DNF representation in Round 3
    aus = next(t for t in traj if t.round == 3)
    assert aus.finish_position is None
    assert aus.is_classified is False
    assert aus.race_points == Decimal("0.0")

    # Verify Sprint points in Round 5 (China) and Round 6 (Miami)
    china = next(t for t in traj if t.round == 5)
    assert china.sprint_points == Decimal("8.00")
    miami = next(t for t in traj if t.round == 6)
    assert miami.sprint_points == Decimal("8.00")


# ─── 2. Red Bull Constructor Aggregate Tests ─────────────────────────────────


def test_red_bull_ten_round_aggregate(session: Session):
    """Red Bull through Round 10: 330.00 total points, 7 wins, proper points separation."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-10 database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "red_bull", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_points == Decimal("330.00"), "Red Bull should have 330.00 total points through Round 10"
    assert agg.wins == 7, "Red Bull should have 7 wins (all by Verstappen)"
    assert agg.championship_standing == 1, "Red Bull should be P1 in constructor standings"

    # Verify separation of race and sprint contributions
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("330.00")

    # Driver contributions: Verstappen (219.00) + Perez (111.00) = 330.00
    ver_contrib = next(c for c in agg.driver_contributions if c.driver_id == "max_verstappen")
    per_contrib = next(c for c in agg.driver_contributions if c.driver_id == "perez")
    assert ver_contrib.total_points == Decimal("219.00")
    assert per_contrib.total_points == Decimal("111.00")


# ─── 3. Teammate Comparison Tests ─────────────────────────────────────────────


def test_teammate_comparisons_ten_rounds(session: Session):
    """Teammate comparisons through Round 10 across constructors and substitutions."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-10 database")

    comps = get_season_teammate_comparisons(session, SEASON_YEAR, up_to_round=10)

    # 1. Red Bull: Verstappen and Perez
    rb = next((c for c in comps if c.constructor_id == "red_bull"), None)
    assert rb is not None
    assert rb.rounds_together == 10, "Verstappen and Perez were teammates for all 10 rounds"
    assert rb.qualifying_head_to_head_a == 10, "Verstappen outqualified Perez in all 10 rounds"
    assert rb.qualifying_head_to_head_b == 0
    assert rb.qualifying_comparable_rounds == 10

    # Race comparable rounds denominator:
    # Round 3 (Australia): Verstappen DNF
    # Round 8 (Monaco): Perez DNF
    # Round 9 (Canada): Perez DNF
    # Comparable finishes = 10 - 3 = 7 rounds
    assert rb.race_comparable_rounds == 7, (
        f"Expected 7 comparable race rounds (10 rounds minus 3 DNFs), got {rb.race_comparable_rounds}"
    )
    assert rb.race_head_to_head_a == 7
    assert rb.race_head_to_head_b == 0

    # 2. Ferrari: Leclerc and Sainz (9 rounds together)
    lec_sai = next(
        (c for c in comps if c.constructor_id == "ferrari" and "sainz" in (c.driver_a_id, c.driver_b_id)),
        None,
    )
    assert lec_sai is not None
    assert lec_sai.rounds_together == 9, "Leclerc and Sainz were teammates for 9 rounds (Sainz missed R2)"
    assert lec_sai.qualifying_comparable_rounds == 9

    # 3. Ferrari: Bearman and Leclerc (1 round together)
    bea_lec = next(
        (c for c in comps if c.constructor_id == "ferrari" and "bearman" in (c.driver_a_id, c.driver_b_id)),
        None,
    )
    assert bea_lec is not None
    assert bea_lec.rounds_together == 1, "Bearman was Leclerc's teammate in Round 2 only"


def test_bearman_round2_event_teammate_pairing(session: Session):
    """Round 2 (Saudi Arabia) Ferrari pairing includes Bearman and Leclerc, excluding Sainz."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-10 database")

    r2_comps = get_event_teammate_comparisons(session, SEASON_YEAR, 2)
    ferrari_r2 = next(c for c in r2_comps if c.constructor_id == "ferrari")

    assert ferrari_r2.driver_a_id == "bearman"
    assert ferrari_r2.driver_b_id == "leclerc"
    assert ferrari_r2.finish_a == 7
    assert ferrari_r2.finish_b == 3
    assert ferrari_r2.points_a == Decimal("6.00")
    assert ferrari_r2.points_b == Decimal("16.00")


# ─── 4. Rolling-Window Statistics Tests ───────────────────────────────────────


def test_verstappen_last_three_rounds_rolling_form(session: Session):
    """Verstappen rolling 3-race window over R8-R10 (Monaco P6, Canada P1, Spain P1) -> average finish 2.67."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-10 database")

    traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen", up_to_round=10)
    form_summary = compute_driver_form_summary(traj, window_size=3)

    assert form_summary.up_to_round == 10
    assert len(form_summary.rolling_windows) > 0

    # The latest finish_position rolling window corresponds to round 10 covering rounds 8, 9, 10
    finish_windows = [w for w in form_summary.rolling_windows if w.metric_name == "finish_position"]
    latest_win = next((w for w in finish_windows if w.round == 10), None)
    assert latest_win is not None, "Latest finish_position rolling window for round 10 not found"
    assert latest_win.round == 10
    assert latest_win.rounds_included == [8, 9, 10]
    assert latest_win.valid_observations == 3
    assert latest_win.mean is not None
    # Monaco (P6) + Canada (P1) + Spain (P1) = 8 / 3 ≈ 2.6667
    assert round(latest_win.mean, 2) == 2.67


# ─── 5. Longitudinal Insights Tests ──────────────────────────────────────────


def test_verstappen_ten_round_longitudinal_insights(session: Session):
    """Verstappen longitudinal rate insights across 10 rounds: 21.90 pts/round, 20.30 pts/start."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-10 database")

    insights = LongitudinalInsightService.get_driver_insights(
        session, SEASON_YEAR, "max_verstappen", up_to_round=10
    )
    ins_map = {i.rule_id: i for i in insights}

    # 1. LONGITUDINAL_POINTS_PER_ROUND
    pts_round = ins_map.get("LONGITUDINAL_POINTS_PER_ROUND")
    assert pts_round is not None, "Missing LONGITUDINAL_POINTS_PER_ROUND insight"
    assert pts_round.sample_size == 10
    assert pts_round.magnitude == 21.9
    assert pts_round.traceability.observed_value == 21.9
    assert pts_round.traceability.rounds_included == list(range(1, 11))

    # 2. LONGITUDINAL_POINTS_PER_START
    pts_start = ins_map.get("LONGITUDINAL_POINTS_PER_START")
    assert pts_start is not None, "Missing LONGITUDINAL_POINTS_PER_START insight"
    assert pts_start.sample_size == 10
    assert pts_start.magnitude == 20.3
    assert pts_start.traceability.observed_value == 20.3
    assert pts_start.traceability.source_metric == "points_per_gp_start"

    # 3. LONGITUDINAL_RECENT_FORM
    recent_form = ins_map.get("LONGITUDINAL_RECENT_FORM")
    assert recent_form is not None, "Missing LONGITUDINAL_RECENT_FORM insight"
    assert recent_form.sample_size == 3
    assert recent_form.magnitude == 2.67
    assert recent_form.traceability.rounds_included == [8, 9, 10]


# ─── 6. Insufficient Sample Size Suppression Tests ───────────────────────────


def test_bearman_insufficient_sample_suppresses_insights(session: Session):
    """Oliver Bearman with 1 round entry must not trigger insights requiring N >= 3 or N >= 5."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-10 database")

    insights = LongitudinalInsightService.get_driver_insights(
        session, SEASON_YEAR, "bearman", up_to_round=10
    )
    # Bearman entered only 1 race in 2024 (Saudi Arabia)
    # Minimum required observations: 3 for rolling form, 5 for longitudinal stats
    assert len(insights) == 0, (
        f"Expected 0 insights for Bearman (N=1 < min_sample), but got {len(insights)}: {[i.rule_id for i in insights]}"
    )

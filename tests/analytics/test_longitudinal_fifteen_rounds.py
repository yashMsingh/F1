"""Tests for longitudinal analytics across the expanded 2024 Rounds 1-15 dataset.

Verifies driver trajectories, season aggregates, teammate comparisons,
rolling-window statistics, and deterministic insights against the 15-round historical data.

Ground-truth facts independently verified via direct SQL reference in Phase 4D.2:
  - Rounds 1-15 coverage (Bahrain through Netherlands)
  - Sprint rounds: Round 5 (China), Round 6 (Miami), Round 11 (Austria)
  - Max Verstappen: 15 starts, 14 classified finishes, 1 DNF (Australia),
    271.00 race points, 24.00 sprint points, 295.00 total points, 7 wins, P1 standing
  - Sergio Perez: 15 starts, 13 classified finishes, 2 DNFs (Monaco, Canada),
    126.00 race points, 13.00 sprint points, 139.00 total points, 0 wins, P7 standing
  - Lando Norris: 15 starts, 15 classified finishes (classified P20 in Austria), 0 DNFs,
    216.00 race points, 9.00 sprint points, 225.00 total points, 2 wins (Miami, Netherlands), P2 standing
  - Charles Leclerc: 15 starts, 14 classified finishes, 1 DNF (Canada),
    178.00 race points, 14.00 sprint points, 192.00 total points, 1 win (Monaco), P3 standing
  - Carlos Sainz: 14 starts (missed Saudi Arabia), 13 classified finishes, 1 DNF (Canada),
    160.00 race points, 12.00 sprint points, 172.00 total points, 1 win (Australia), P5 standing
  - George Russell: 15 starts, 12 classified finishes, 3 non-classified (Australia DNF,
    Britain DNF, Belgium DSQ), 116.00 race points, 6.00 sprint points, 122.00 total points,
    1 win (Austria), P8 standing
  - Lewis Hamilton: 15 starts, 14 classified finishes, 1 DNF (Australia),
    144.00 race points, 10.00 sprint points, 154.00 total points, 2 wins (Britain, Belgium), P6 standing
  - Oscar Piastri: 15 starts, 15 classified finishes, 0 DNFs,
    167.00 race points, 12.00 sprint points, 179.00 total points, 1 win (Hungary), P4 standing
  - Oliver Bearman: 1 start (Saudi Arabia R2), 1 classified finish (P7), 0 DNFs,
    6.00 race points, 0 sprint points, 6.00 total points, 0 wins, P15 standing
  - Constructors:
    - Red Bull: 434.00 total points (395 race + 39 sprint), 7 wins, P1
    - McLaren: 404.00 total points (380 race + 24 sprint), 3 wins, P2
    - Ferrari: 370.00 total points (353 race + 17 sprint), 2 wins, P3
    - Mercedes: 276.00 total points (258 race + 18 sprint), 3 wins, P4
  - Teammate Comparisons:
    - Verstappen vs Perez: 15 rounds together; Quali 15-0; Race 12-0 (R3, R8, R9 excluded)
    - Leclerc vs Sainz: 14 rounds together; Quali 9-5; Race 8-5 (R9 Canada excluded); Pts 176.00 vs 172.00
    - Bearman vs Leclerc: 1 round together; Quali 0-1; Race 0-1; Pts 6.00 vs 16.00
    - Norris vs Piastri: 15 rounds together; Quali 12-3; Race 10-5; Pts 225.00 vs 179.00
    - Hamilton vs Russell: 15 rounds together; Quali 4-11; Race 4-8 (R3, R12, R14 excluded); Pts 154.00 vs 122.00
  - Rolling 3-Round Form (R13-R15, no sprint sessions):
    - Verstappen: 3 classified, mean finish 3.67, 40.00 combined points
    - Norris: 3 classified, mean finish 2.67, 54.00 combined points
    - Leclerc: 3 classified, mean finish 3.33, 42.00 combined points
    - Russell: 2 classified (Belgium DSQ excluded), mean finish 7.50, 11.00 combined points
  - Edge Cases:
    - R11 Austria: Sprint winner VER (8 pts), GP winner RUS (25 pts), VER finish P5 (10 pts)
    - R12 Britain: Franco Colapinto FP1 reference entity exists, 0 starts, 0 standings rows
    - R13 Hungary: Piastri maiden GP win (25 pts), Norris P2 (18 pts) -> McLaren 1-2 finish
    - R14 Belgium: Hamilton winner (25 pts), Russell DSQ (status='Disqualified', 0 pts)
    - R15 Netherlands: Logan Sargeant Q1 time is NULL, finished P16 (status='Lapped')
"""

from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.analytics.longitudinal_constructor import (
    get_constructor_season_aggregate,
    get_constructor_trajectory,
)
from app.analytics.longitudinal_driver import (
    get_all_drivers_season_aggregates,
    get_driver_season_aggregate,
    get_driver_trajectory,
)
from app.analytics.longitudinal_teammate import (
    get_event_teammate_comparisons,
    get_season_teammate_comparisons,
)
from app.db.models.driver import Driver
from app.db.models.race import Race
from app.db.models.race_result import RaceResult
from app.db.models.qualifying_result import QualifyingResult
from app.services.longitudinal_service import LongitudinalInsightService
from app.statistics.longitudinal import compute_driver_form_summary

SEASON_YEAR = 2024
TOTAL_ROUNDS = 15


def _check_db_has_data(session: Session) -> bool:
    """Helper to check if 15-round data is available in the current session."""
    count = session.scalar(
        select(func.count(Race.id)).where(Race.season_year == SEASON_YEAR, Race.round <= TOTAL_ROUNDS)
    )
    return (count or 0) >= TOTAL_ROUNDS


# ─── 1. Driver Season Aggregate Tests ────────────────────────────────────────


def test_verstappen_fifteen_round_aggregate(session: Session):
    """Verstappen through Round 15: 15 starts, 14 classified, 1 DNF, 271 race pts, 24 sprint pts, 295 total, 7 wins."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    # Verify explicit up_to_round=15 only.
    # NOTE: The unbounded call was valid when only 15 rounds existed in the DB.
    # With 24 rounds now present, unbounded correctly returns 24-round totals.
    # Unbounded 24-round coverage is deferred to Phase 5B tests.
    agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen", up_to_round=TOTAL_ROUNDS)
    assert agg is not None, "Verstappen aggregate should exist"
    assert agg.races_entered == 15, "Should have 15 GP starts"
    assert agg.races_classified == 14, "Should have 14 classified finishes"
    assert agg.dnf_count == 1, "Should have 1 DNF (Australia Round 3)"
    assert agg.total_race_points == Decimal("271.00"), "Should have 271.00 GP race points"
    assert agg.total_sprint_points == Decimal("24.00"), "Should have 24.00 sprint points (China 8, Miami 8, Austria 8)"
    assert agg.total_points == Decimal("295.00"), "Should have 295.00 total points"
    assert agg.wins == 7, "Should have 7 Grand Prix wins"
    assert agg.championship_standing == 1, "Should be P1 in championship"
    assert round(agg.average_finish, 2) == 2.36, "Average finish should be 2.36 (33/14)"
    assert round(agg.average_grid, 2) == 2.53, "Average grid should be 2.53 (38/15)"


def test_perez_fifteen_round_aggregate(session: Session):
    """Perez through Round 15: 15 starts, 13 classified, 2 DNFs, 126 race pts, 13 sprint pts, 139 total, 0 wins, P7."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "perez", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 15
    assert agg.races_classified == 13
    assert agg.dnf_count == 2, "Should have 2 DNFs (Monaco Round 8, Canada Round 9)"
    assert agg.total_race_points == Decimal("126.00")
    assert agg.total_sprint_points == Decimal("13.00")
    assert agg.total_points == Decimal("139.00")
    assert agg.wins == 0
    assert agg.championship_standing == 7
    assert round(agg.average_finish, 2) == 6.00
    assert round(agg.average_grid, 2) == 8.47


def test_norris_fifteen_round_aggregate(session: Session):
    """Norris through Round 15: 15 starts, 15 classified, 0 DNFs, 216 race pts, 9 sprint pts, 225 total, 2 wins, P2."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "norris", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 15
    assert agg.races_classified == 15, "Classified in all 15 rounds (including P20 in Austria)"
    assert agg.dnf_count == 0
    assert agg.total_race_points == Decimal("216.00")
    assert agg.total_sprint_points == Decimal("9.00")
    assert agg.total_points == Decimal("225.00")
    assert agg.wins == 2, "Should have 2 wins (Miami Round 6, Netherlands Round 15)"
    assert agg.championship_standing == 2
    assert round(agg.average_finish, 2) == 4.40
    assert round(agg.average_grid, 2) == 3.27


def test_leclerc_fifteen_round_aggregate(session: Session):
    """Leclerc through Round 15: 15 starts, 14 classified, 1 DNF, 178 race pts, 14 sprint pts, 192 total, 1 win, P3."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "leclerc", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 15
    assert agg.races_classified == 14
    assert agg.dnf_count == 1, "Should have 1 DNF (Canada Round 9)"
    assert agg.total_race_points == Decimal("178.00")
    assert agg.total_sprint_points == Decimal("14.00")
    assert agg.total_points == Decimal("192.00")
    assert agg.wins == 1, "Should have 1 win (Monaco Round 8)"
    assert agg.championship_standing == 3
    assert round(agg.average_finish, 2) == 4.57
    assert round(agg.average_grid, 2) == 4.93


def test_sainz_fifteen_round_aggregate(session: Session):
    """Sainz through Round 15: 14 starts, 13 classified, 1 DNF, 160 race pts, 12 sprint pts, 172 total, 1 win, P5."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "sainz", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 14, "Missed Saudi Arabia Round 2"
    assert agg.races_classified == 13
    assert agg.dnf_count == 1, "Should have 1 DNF (Canada Round 9)"
    assert agg.total_race_points == Decimal("160.00")
    assert agg.total_sprint_points == Decimal("12.00")
    assert agg.total_points == Decimal("172.00")
    assert agg.wins == 1, "Should have 1 win (Australia Round 3)"
    assert agg.championship_standing == 5
    assert round(agg.average_finish, 2) == 4.31
    assert round(agg.average_grid, 2) == 5.50


def test_russell_fifteen_round_aggregate(session: Session):
    """Russell through Round 15: 15 starts, 12 classified, 3 non-classified, 116 race pts, 6 sprint pts, 122 total, 1 win, P8."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "russell", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 15
    assert agg.races_classified == 12
    # 2 DNFs (Australia, Britain) + 1 DSQ (Belgium) = 3 non-classified
    assert agg.dnf_count == 3
    assert agg.total_race_points == Decimal("116.00")
    assert agg.total_sprint_points == Decimal("6.00")
    assert agg.total_points == Decimal("122.00")
    assert agg.wins == 1, "Should have 1 win (Austria Round 11)"
    assert agg.championship_standing == 8
    assert round(agg.average_finish, 2) == 5.58
    assert round(agg.average_grid, 2) == 5.87


def test_hamilton_fifteen_round_aggregate(session: Session):
    """Hamilton through Round 15: 15 starts, 14 classified, 1 DNF, 144 race pts, 10 sprint pts, 154 total, 2 wins, P6."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "hamilton", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 15
    assert agg.races_classified == 14
    assert agg.dnf_count == 1, "Should have 1 DNF (Australia Round 3)"
    assert agg.total_race_points == Decimal("144.00")
    assert agg.total_sprint_points == Decimal("10.00")
    assert agg.total_points == Decimal("154.00")
    assert agg.wins == 2, "Should have 2 wins (Britain Round 12, Belgium Round 14)"
    assert agg.championship_standing == 6
    assert round(agg.average_finish, 2) == 5.50
    assert round(agg.average_grid, 2) == 7.67


def test_piastri_fifteen_round_aggregate(session: Session):
    """Piastri through Round 15: 15 starts, 15 classified, 0 DNFs, 167 race pts, 12 sprint pts, 179 total, 1 win, P4."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "piastri", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 15
    assert agg.races_classified == 15
    assert agg.dnf_count == 0
    assert agg.total_race_points == Decimal("167.00")
    assert agg.total_sprint_points == Decimal("12.00")
    assert agg.total_points == Decimal("179.00")
    assert agg.wins == 1, "Should have 1 win (Hungary Round 13)"
    assert agg.championship_standing == 4
    assert round(agg.average_finish, 2) == 5.07
    assert round(agg.average_grid, 2) == 5.13


def test_bearman_fifteen_round_aggregate(session: Session):
    """Bearman through Round 15: 1 start, 1 classified (P7), 0 DNFs, 6 race pts, 0 sprint pts, 6 total, P15."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "bearman", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 1
    assert agg.races_classified == 1
    assert agg.dnf_count == 0
    assert agg.total_race_points == Decimal("6.00")
    assert agg.total_sprint_points == Decimal("0.00")
    assert agg.total_points == Decimal("6.00")
    assert agg.wins == 0
    assert agg.best_finish == 7
    assert agg.best_grid == 11
    assert agg.championship_standing == 15


def test_all_drivers_fifteen_round_aggregates(session: Session):
    """All driver season aggregates across 15 rounds returns all active drivers with Verstappen at P1."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    aggs = get_all_drivers_season_aggregates(session, SEASON_YEAR, up_to_round=TOTAL_ROUNDS)
    # 21 drivers participated in Rounds 1-15 (20 regular + Bearman)
    assert len(aggs) == 21
    assert aggs[0].driver_id == "max_verstappen"
    assert aggs[0].championship_standing == 1
    assert aggs[1].driver_id == "norris"
    assert aggs[1].championship_standing == 2
    assert aggs[2].driver_id == "leclerc"
    assert aggs[2].championship_standing == 3


# ─── 2. Driver Trajectory Tests ──────────────────────────────────────────────


def test_verstappen_fifteen_round_trajectory(session: Session):
    """Verstappen trajectory across Rounds 1-15 contains 15 rounds with sprint points in R5, R6, R11."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen", up_to_round=TOTAL_ROUNDS)
    assert len(traj) == 15
    assert [t.round for t in traj] == list(range(1, 16))

    # Verify Austria (Round 11) sprint points separation
    austria = next(t for t in traj if t.round == 11)
    assert austria.sprint_points == Decimal("8.00"), "Verstappen won Austria Sprint (8 pts)"
    assert austria.race_points == Decimal("10.00"), "Verstappen finished P5 in Austria GP (10 pts)"
    assert austria.total_round_points == Decimal("18.00")

    # Verify cumulative points monotonic progression
    for i in range(1, len(traj)):
        assert traj[i].cumulative_total_points >= traj[i - 1].cumulative_total_points


def test_russell_trajectory_belgium_dsq(session: Session):
    """Russell trajectory handles Belgium (Round 14) DSQ correctly."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    traj = get_driver_trajectory(session, SEASON_YEAR, "russell", up_to_round=TOTAL_ROUNDS)
    spa = next(t for t in traj if t.round == 14)
    assert spa.finish_position is None, "DSQ should result in None finish_position"
    assert spa.is_classified is False, "DSQ is not classified"
    assert spa.race_points == Decimal("0.0"), "DSQ scores 0 race points"


# ─── 3. Constructor Season Aggregate Tests ───────────────────────────────────


def test_red_bull_fifteen_round_aggregate(session: Session):
    """Red Bull through Round 15: 434.00 total points (395 race + 39 sprint), 7 wins, P1 standing."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    # Verify explicit up_to_round=15 only.
    # NOTE: The unbounded call was valid when only 15 rounds existed in the DB.
    # With 24 rounds now present, unbounded correctly returns 24-round totals.
    # Unbounded 24-round coverage is deferred to Phase 5B tests.
    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "red_bull", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_points == Decimal("434.00")
    assert agg.wins == 7
    assert agg.championship_standing == 1

    # Driver contributions: Verstappen (295.00) + Perez (139.00) = 434.00
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("434.00")
    ver_c = next(c for c in agg.driver_contributions if c.driver_id == "max_verstappen")
    per_c = next(c for c in agg.driver_contributions if c.driver_id == "perez")
    assert ver_c.total_points == Decimal("295.00")
    assert per_c.total_points == Decimal("139.00")


def test_mclaren_fifteen_round_aggregate(session: Session):
    """McLaren through Round 15: 404.00 total points (380 race + 24 sprint), 3 wins, P2 standing."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "mclaren", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_points == Decimal("404.00")
    assert agg.wins == 3, "Miami (Norris), Hungary (Piastri), Netherlands (Norris)"
    assert agg.championship_standing == 2

    # Driver contributions: Norris (225.00) + Piastri (179.00) = 404.00
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("404.00")
    nor_c = next(c for c in agg.driver_contributions if c.driver_id == "norris")
    pia_c = next(c for c in agg.driver_contributions if c.driver_id == "piastri")
    assert nor_c.total_points == Decimal("225.00")
    assert pia_c.total_points == Decimal("179.00")


def test_ferrari_fifteen_round_aggregate(session: Session):
    """Ferrari through Round 15: 370.00 total points (353 race + 17 sprint), 2 wins, 3 drivers, P3 standing."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "ferrari", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_points == Decimal("370.00")
    assert agg.wins == 2, "Australia (Sainz), Monaco (Leclerc)"
    assert agg.championship_standing == 3

    # Driver contributions: Leclerc (192.00) + Sainz (172.00) + Bearman (6.00) = 370.00
    assert len(agg.driver_contributions) == 3
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("370.00")
    lec_c = next(c for c in agg.driver_contributions if c.driver_id == "leclerc")
    sai_c = next(c for c in agg.driver_contributions if c.driver_id == "sainz")
    bea_c = next(c for c in agg.driver_contributions if c.driver_id == "bearman")
    assert lec_c.total_points == Decimal("192.00")
    assert sai_c.total_points == Decimal("172.00")
    assert bea_c.total_points == Decimal("6.00")


def test_mercedes_fifteen_round_aggregate(session: Session):
    """Mercedes through Round 15: 276.00 total points (258 race + 18 sprint), 3 wins, P4 standing."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "mercedes", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_points == Decimal("276.00")
    assert agg.wins == 3, "Austria (Russell), Britain (Hamilton), Belgium (Hamilton)"
    assert agg.championship_standing == 4

    # Driver contributions: Hamilton (154.00) + Russell (122.00) = 276.00
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("276.00")
    ham_c = next(c for c in agg.driver_contributions if c.driver_id == "hamilton")
    rus_c = next(c for c in agg.driver_contributions if c.driver_id == "russell")
    assert ham_c.total_points == Decimal("154.00")
    assert rus_c.total_points == Decimal("122.00")


# ─── 4. Teammate Head-to-Head Comparison Tests ───────────────────────────────


def test_teammate_comparisons_fifteen_rounds(session: Session):
    """Teammate head-to-head comparisons through Round 15 across constructors."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    comps = get_season_teammate_comparisons(session, SEASON_YEAR, up_to_round=TOTAL_ROUNDS)

    # 1. Red Bull: Verstappen vs Perez
    rb = next((c for c in comps if c.constructor_id == "red_bull"), None)
    assert rb is not None
    assert rb.rounds_together == 15
    assert rb.qualifying_head_to_head_a == 15
    assert rb.qualifying_head_to_head_b == 0
    assert rb.qualifying_comparable_rounds == 15
    # Comparable race finishes = 15 - 3 DNFs (VER R3, PER R8, PER R9) = 12
    assert rb.race_comparable_rounds == 12
    assert rb.race_head_to_head_a == 12
    assert rb.race_head_to_head_b == 0
    assert rb.total_points_a == Decimal("295.00")
    assert rb.total_points_b == Decimal("139.00")

    # 2. Ferrari: Leclerc vs Sainz
    lec_sai = next(
        (c for c in comps if c.constructor_id == "ferrari" and "sainz" in (c.driver_a_id, c.driver_b_id)),
        None,
    )
    assert lec_sai is not None
    assert lec_sai.rounds_together == 14, "Sainz missed Round 2"
    assert lec_sai.qualifying_comparable_rounds == 14
    # Driver A is leclerc, Driver B is sainz
    if lec_sai.driver_a_id == "leclerc":
        assert lec_sai.qualifying_head_to_head_a == 9
        assert lec_sai.qualifying_head_to_head_b == 5
        # Comparable race finishes = 14 - 1 (Canada R9 both DNF) = 13
        assert lec_sai.race_comparable_rounds == 13
        assert lec_sai.race_head_to_head_a == 8
        assert lec_sai.race_head_to_head_b == 5
        assert lec_sai.total_points_a == Decimal("176.00")  # Excluding Leclerc's R2 points (16 pts with Bearman)
        assert lec_sai.total_points_b == Decimal("172.00")
    else:
        assert lec_sai.qualifying_head_to_head_a == 5
        assert lec_sai.qualifying_head_to_head_b == 9
        assert lec_sai.race_comparable_rounds == 13
        assert lec_sai.race_head_to_head_a == 5
        assert lec_sai.race_head_to_head_b == 8
        assert lec_sai.total_points_a == Decimal("172.00")
        assert lec_sai.total_points_b == Decimal("176.00")

    # 3. Ferrari: Bearman vs Leclerc
    bea_lec = next(
        (c for c in comps if c.constructor_id == "ferrari" and "bearman" in (c.driver_a_id, c.driver_b_id)),
        None,
    )
    assert bea_lec is not None
    assert bea_lec.rounds_together == 1
    assert bea_lec.qualifying_comparable_rounds == 1
    assert bea_lec.race_comparable_rounds == 1
    if bea_lec.driver_a_id == "bearman":
        assert bea_lec.total_points_a == Decimal("6.00")
        assert bea_lec.total_points_b == Decimal("16.00")
    else:
        assert bea_lec.total_points_a == Decimal("16.00")
        assert bea_lec.total_points_b == Decimal("6.00")

    # 4. McLaren: Norris vs Piastri
    mcl = next((c for c in comps if c.constructor_id == "mclaren"), None)
    assert mcl is not None
    assert mcl.rounds_together == 15
    assert mcl.qualifying_comparable_rounds == 15
    if mcl.driver_a_id == "norris":
        assert mcl.qualifying_head_to_head_a == 12
        assert mcl.qualifying_head_to_head_b == 3
        assert mcl.race_comparable_rounds == 15
        assert mcl.race_head_to_head_a == 10
        assert mcl.race_head_to_head_b == 5
        assert mcl.total_points_a == Decimal("225.00")
        assert mcl.total_points_b == Decimal("179.00")

    # 5. Mercedes: Hamilton vs Russell
    merc = next((c for c in comps if c.constructor_id == "mercedes"), None)
    assert merc is not None
    assert merc.rounds_together == 15
    assert merc.qualifying_comparable_rounds == 15
    # Comparable races = 15 - 3 (R3 HAM DNF, R12 RUS DNF, R14 RUS DSQ) = 12
    assert merc.race_comparable_rounds == 12
    if merc.driver_a_id == "hamilton":
        assert merc.qualifying_head_to_head_a == 4
        assert merc.qualifying_head_to_head_b == 11
        assert merc.race_head_to_head_a == 4
        assert merc.race_head_to_head_b == 8
        assert merc.total_points_a == Decimal("154.00")
        assert merc.total_points_b == Decimal("122.00")


# ─── 5. Rolling-Window Statistics Tests (R13-R15) ─────────────────────────────


def test_rolling_form_rounds_thirteen_to_fifteen(session: Session):
    """Rolling 3-race window across Rounds 13-15 for key drivers."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    # Verstappen: R13 P5, R14 P4, R15 P2 -> mean finish 3.67 (11/3)
    ver_traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen", up_to_round=TOTAL_ROUNDS)
    ver_form = compute_driver_form_summary(ver_traj, window_size=3)
    ver_finish_win = next(
        w for w in ver_form.rolling_windows if w.metric_name == "finish_position" and w.round == 15
    )
    assert ver_finish_win.rounds_included == [13, 14, 15]
    assert ver_finish_win.valid_observations == 3
    assert round(ver_finish_win.mean, 2) == 3.67

    # Norris: R13 P2, R14 P5, R15 P1 -> mean finish 2.67 (8/3)
    nor_traj = get_driver_trajectory(session, SEASON_YEAR, "norris", up_to_round=TOTAL_ROUNDS)
    nor_form = compute_driver_form_summary(nor_traj, window_size=3)
    nor_finish_win = next(
        w for w in nor_form.rolling_windows if w.metric_name == "finish_position" and w.round == 15
    )
    assert nor_finish_win.rounds_included == [13, 14, 15]
    assert nor_finish_win.valid_observations == 3
    assert round(nor_finish_win.mean, 2) == 2.67

    # Leclerc: R13 P4, R14 P3, R15 P3 -> mean finish 3.33 (10/3)
    lec_traj = get_driver_trajectory(session, SEASON_YEAR, "leclerc", up_to_round=TOTAL_ROUNDS)
    lec_form = compute_driver_form_summary(lec_traj, window_size=3)
    lec_finish_win = next(
        w for w in lec_form.rolling_windows if w.metric_name == "finish_position" and w.round == 15
    )
    assert lec_finish_win.rounds_included == [13, 14, 15]
    assert lec_finish_win.valid_observations == 3
    assert round(lec_finish_win.mean, 2) == 3.33

    # Russell: R13 P8, R14 DSQ (excluded), R15 P7 -> 2 observations, mean finish 7.50 (15/2)
    rus_traj = get_driver_trajectory(session, SEASON_YEAR, "russell", up_to_round=TOTAL_ROUNDS)
    rus_form = compute_driver_form_summary(rus_traj, window_size=3)
    rus_finish_win = next(
        w for w in rus_form.rolling_windows if w.metric_name == "finish_position" and w.round == 15
    )
    assert rus_finish_win.rounds_included == [13, 14, 15]
    assert rus_finish_win.valid_observations == 2, "Round 14 DSQ excluded from classified finish denominator"
    assert round(rus_finish_win.mean, 2) == 7.50


# ─── 6. Longitudinal Rate Metrics & Insights ─────────────────────────────────


def test_longitudinal_rate_metrics_fifteen_rounds(session: Session):
    """Longitudinal rate metrics for Verstappen and Norris across 15 rounds."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    # Verstappen insights
    ver_insights = LongitudinalInsightService.get_driver_insights(
        session, SEASON_YEAR, "max_verstappen", up_to_round=TOTAL_ROUNDS
    )
    ver_map = {i.rule_id: i for i in ver_insights}

    pts_round = ver_map.get("LONGITUDINAL_POINTS_PER_ROUND")
    assert pts_round is not None
    assert pts_round.sample_size == 15
    # 295 / 15 = 19.6667 -> 19.67
    assert round(pts_round.magnitude, 2) == 19.67

    pts_start = ver_map.get("LONGITUDINAL_POINTS_PER_START")
    assert pts_start is not None
    assert pts_start.sample_size == 15
    # 271 / 15 = 18.0667 -> 18.07
    assert round(pts_start.magnitude, 2) == 18.07

    # Norris insights
    nor_insights = LongitudinalInsightService.get_driver_insights(
        session, SEASON_YEAR, "norris", up_to_round=TOTAL_ROUNDS
    )
    nor_map = {i.rule_id: i for i in nor_insights}
    nor_pts_round = nor_map.get("LONGITUDINAL_POINTS_PER_ROUND")
    assert nor_pts_round is not None
    assert nor_pts_round.sample_size == 15
    # 225 / 15 = 15.00
    assert round(nor_pts_round.magnitude, 2) == 15.00


def test_bearman_fifteen_rounds_insufficient_sample(session: Session):
    """Oliver Bearman with N=1 must have all longitudinal insights suppressed."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    insights = LongitudinalInsightService.get_driver_insights(
        session, SEASON_YEAR, "bearman", up_to_round=TOTAL_ROUNDS
    )
    assert len(insights) == 0, f"Expected 0 insights for Bearman (N=1), got {len(insights)}"


# ─── 7. Historical Edge Cases Verification ───────────────────────────────────


def test_edge_case_austria_sprint_and_gp(session: Session):
    """Round 11 Austria: Sprint winner Verstappen (8 pts), GP winner Russell (25 pts), Verstappen P5 (10 pts)."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    # Verify event-level teammate comparison
    r11_comps = get_event_teammate_comparisons(session, SEASON_YEAR, 11)
    rb_r11 = next(c for c in r11_comps if c.constructor_id == "red_bull")
    # Verstappen: 8 sprint + 10 race = 18 round points
    assert rb_r11.points_a == Decimal("10.00") and rb_r11.sprint_points_a == Decimal("8.00")

    # Verify race winner Russell
    merc_r11 = next(c for c in r11_comps if c.constructor_id == "mercedes")
    assert (
        (merc_r11.driver_a_id == "russell" and merc_r11.finish_a == 1)
        or (merc_r11.driver_b_id == "russell" and merc_r11.finish_b == 1)
    )


def test_edge_case_colapinto_reference_entity(session: Session):
    """Round 12 Britain: Franco Colapinto reference entity exists with 0 starts and 0 standings."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    colapinto = session.scalar(select(Driver).where(Driver.driver_id == "colapinto"))
    assert colapinto is not None, "Colapinto driver entity must exist in database"

    # Aggregates query for Colapinto should return None or 0 starts
    agg = get_driver_season_aggregate(session, SEASON_YEAR, "colapinto", up_to_round=TOTAL_ROUNDS)
    assert agg is None, "Colapinto had 0 race starts through Round 15"


def test_edge_case_hungary_mclaren_one_two(session: Session):
    """Round 13 Hungary: Piastri maiden win (25 pts), Norris P2 (18 pts) -> McLaren 1-2."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    r13_comps = get_event_teammate_comparisons(session, SEASON_YEAR, 13)
    mcl_r13 = next(c for c in r13_comps if c.constructor_id == "mclaren")
    finishes = {mcl_r13.finish_a, mcl_r13.finish_b}
    assert finishes == {1, 2}, f"McLaren should have finished 1-2 in Hungary, got {finishes}"


def test_edge_case_belgium_dsq_and_hamilton_win(session: Session):
    """Round 14 Belgium: Hamilton won (25 pts), Russell was disqualified (status='Disqualified')."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    # Race results check
    race_id = session.scalar(select(Race.id).where(Race.season_year == 2024, Race.round == 14))
    assert race_id is not None

    ham_res = session.scalar(
        select(RaceResult).join(Driver).where(RaceResult.race_id == race_id, Driver.driver_id == "hamilton")
    )
    assert ham_res is not None
    assert ham_res.source_position == 1
    assert ham_res.points == Decimal("25.00")

    rus_res = session.scalar(
        select(RaceResult).join(Driver).where(RaceResult.race_id == race_id, Driver.driver_id == "russell")
    )
    assert rus_res is not None
    assert rus_res.status.lower() == "disqualified"
    assert rus_res.points == Decimal("0.00")


def test_edge_case_netherlands_sargeant_null_quali(session: Session):
    """Round 15 Netherlands: Logan Sargeant had no qualifying time recorded (null), finished P16."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 Rounds 1-15 database")

    race_id = session.scalar(select(Race.id).where(Race.season_year == 2024, Race.round == 15))
    assert race_id is not None

    sar_quali = session.scalar(
        select(QualifyingResult).join(Driver).where(QualifyingResult.race_id == race_id, Driver.driver_id == "sargeant")
    )
    assert sar_quali is not None
    assert sar_quali.q1_time is None
    assert sar_quali.q1_time_millis is None

    sar_race = session.scalar(
        select(RaceResult).join(Driver).where(RaceResult.race_id == race_id, Driver.driver_id == "sargeant")
    )
    assert sar_race is not None
    assert sar_race.source_position == 16

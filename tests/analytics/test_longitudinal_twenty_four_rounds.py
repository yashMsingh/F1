"""Tests for longitudinal analytics across the complete 2024 season (Rounds 1-24).

Verifies driver trajectories, season aggregates, constructor aggregates,
teammate comparisons, rolling-window statistics, and deterministic insights
against the full 24-round historical dataset.

All reference values independently verified via direct PostgreSQL SQL queries in Phase 5B:
  - Rounds 1-24 coverage (Bahrain through Abu Dhabi)
  - Sprint rounds: Round 5 (China), Round 6 (Miami), Round 11 (Austria),
    Round 19 (United States), Round 21 (São Paulo), Round 23 (Qatar)
  - Driver aggregates:
    - Max Verstappen: 24 starts, 23 classified, 1 DNF (Australia), 399 GP pts, 38 sprint pts, 437 total, 9 wins, P1
    - Lando Norris: 24 starts, 24 classified, 0 DNFs, 344 GP pts, 30 sprint pts, 374 total, 4 wins, P2
    - Charles Leclerc: 24 starts, 23 classified, 1 DNF (Canada), 327 GP pts, 29 sprint pts, 356 total, 3 wins, P3
    - Oscar Piastri: 24 starts, 24 classified, 0 DNFs, 265 GP pts, 27 sprint pts, 292 total, 2 wins, P4
    - Carlos Sainz: 23 starts (missed Saudi Arabia), 20 classified, 3 DNFs, 262 GP pts, 28 sprint pts, 290 total, 2 wins, P5
    - George Russell: 24 starts, 21 classified, 3 non-classified (Australia DNF, Britain DNF, Belgium DSQ), 226 GP pts, 19 sprint pts, 245 total, 2 wins, P6
    - Lewis Hamilton: 24 starts, 22 classified, 2 DNFs (Australia, Austin), 207 GP pts, 16 sprint pts, 223 total, 2 wins, P7
    - Sergio Perez: 24 starts, 19 classified, 5 DNFs, 138 GP pts, 14 sprint pts, 152 total, 0 wins, P8
    - Oliver Bearman: 3 starts, 3 classified, 0 DNFs, 7 GP pts (6 Ferrari + 1 Haas), 0 sprint pts, 7 total, P18
    - Liam Lawson: 6 starts (R19-R24), 5 classified, 1 DNF, 4 GP pts, 0 sprint pts, 4 total, P21
    - Franco Colapinto: 9 starts (R16-R24), 6 classified, 3 DNFs, 5 GP pts, 0 sprint pts, 5 total, P19
    - Andrea Kimi Antonelli: 0 starts, reference-only entity (FP1), aggregate is None
  - Constructor aggregates:
    - McLaren: 609 GP + 57 sprint = 666 total pts, 6 wins, P1
    - Ferrari: 595 GP + 57 sprint = 652 total pts, 5 wins, P2
    - Red Bull: 537 GP + 52 sprint = 589 total pts, 9 wins, P3
    - Mercedes: 433 GP + 35 sprint = 468 total pts, 4 wins, P4
    - Aston Martin: 94 GP + 0 sprint = 94 total pts, 0 wins, P5
    - Alpine: 63 GP + 2 sprint = 65 total pts, 0 wins, P6
    - Haas: 51 GP + 7 sprint = 58 total pts, 0 wins, P7
    - RB: 40 GP + 6 sprint = 46 total pts, 0 wins, P8
    - Williams: 17 GP + 0 sprint = 17 total pts, 0 wins, P9
    - Sauber: 4 GP + 0 sprint = 4 total pts, 0 wins, P10
  - Teammate Comparisons:
    - Verstappen vs Perez: 24 rounds, Quali 23-1, Race 18-0 (6 excluded: R3, R8, R9, R17, R23, R24)
    - Russell vs Hamilton: 24 rounds, Quali 19-5, Race 13-7 (4 excluded: R3, R12, R14, R19)
    - Substitute Pairings: Albon vs Colapinto (9 rds, Q 7-2, R 2-1), Tsunoda vs Lawson (6 rds, Q 6-0, R 3-1), Bearman vs Hulkenberg (2 rds, Q 2-0, R 1-0)
  - Deterministic Insights: Exactly 33 emitted, unique, and strictly grounded in database evidence.
"""

from collections import Counter
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.analytics.longitudinal_constructor import (
    get_all_constructors_season_aggregates,
    get_constructor_season_aggregate,
)
from app.analytics.longitudinal_driver import (
    get_driver_season_aggregate,
    get_driver_trajectory,
)
from app.analytics.longitudinal_teammate import (
    get_season_teammate_comparisons,
)
from app.db.models.driver import Driver
from app.db.models.race import Race
from app.db.models.race_result import RaceResult
from app.services.longitudinal_service import LongitudinalInsightService
from app.statistics.longitudinal import compute_driver_form_summary

pytestmark = pytest.mark.integration

SEASON_YEAR = 2024
TOTAL_ROUNDS = 24


def _check_db_has_data(session: Session) -> bool:
    """Helper to check if 24-round full-season data is available in the current session."""
    count = session.scalar(
        select(func.count(Race.id)).where(Race.season_year == SEASON_YEAR, Race.round <= TOTAL_ROUNDS)
    )
    return (count or 0) >= TOTAL_ROUNDS


# =============================================================================
# 1. Driver Season Aggregate Tests (12 tests)
# =============================================================================


@pytest.mark.integration
def test_verstappen_twenty_four_round_aggregate(session: Session):
    """Verstappen full season: 24 starts, 23 classified, 1 DNF, 399 GP pts, 38 sprint pts, 437 total, 9 wins, P1."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    # Verify both bounded (up_to_round=24) and unbounded calls produce identical full-season aggregates
    agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen", up_to_round=TOTAL_ROUNDS)
    agg_unbound = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen")

    assert agg is not None, "Verstappen aggregate should exist"
    assert agg_unbound is not None, "Unbounded Verstappen aggregate should exist"
    assert agg.total_points == agg_unbound.total_points == Decimal("437.00")
    assert agg.wins == agg_unbound.wins == 9

    assert agg.races_entered == 24, "Should have 24 GP starts"
    assert agg.races_classified == 23, "Should have 23 classified finishes"
    assert agg.dnf_count == 1, "Should have 1 DNF (Australia Round 3 brake fire)"
    assert agg.total_race_points == Decimal("399.00"), "Should have 399.00 Grand Prix race points"
    assert agg.total_sprint_points == Decimal("38.00"), "Should have 38.00 sprint points across 6 sprint events"
    assert agg.total_points == Decimal("437.00"), "Should have 437.00 total championship points"
    assert agg.wins == 9, "Should have 9 Grand Prix wins"
    assert agg.championship_standing == 1, "Should be P1 World Drivers' Champion"
    assert round(agg.average_finish, 2) == 2.96, "Average finish should be 2.96 (68 / 23)"
    assert round(agg.average_grid, 2) == 3.54, "Average grid should be 3.54 (85 / 24)"


@pytest.mark.integration
def test_norris_twenty_four_round_aggregate(session: Session):
    """Norris full season: 24 starts, 24 classified, 0 DNFs, 344 GP pts, 30 sprint pts, 374 total, 4 wins, P2."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "norris", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 24
    assert agg.races_classified == 24, "Classified in all 24 Grand Prix races"
    assert agg.dnf_count == 0
    assert agg.total_race_points == Decimal("344.00")
    assert agg.total_sprint_points == Decimal("30.00")
    assert agg.total_points == Decimal("374.00")
    assert agg.wins == 4, "Should have 4 wins (Miami, Netherlands, Singapore, Abu Dhabi)"
    assert agg.championship_standing == 2
    assert round(agg.average_finish, 2) == 4.29, "Average finish should be 4.29 (103 / 24)"
    assert round(agg.average_grid, 2) == 3.38, "Average grid should be 3.38 (81 / 24)"


@pytest.mark.integration
def test_leclerc_twenty_four_round_aggregate(session: Session):
    """Leclerc full season: 24 starts, 23 classified, 1 DNF, 327 GP pts, 29 sprint pts, 356 total, 3 wins, P3."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "leclerc", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 24
    assert agg.races_classified == 23
    assert agg.dnf_count == 1, "Should have 1 DNF (Canada Round 9 engine failure)"
    assert agg.total_race_points == Decimal("327.00")
    assert agg.total_sprint_points == Decimal("29.00")
    assert agg.total_points == Decimal("356.00")
    assert agg.wins == 3, "Should have 3 wins (Monaco, Italy, United States)"
    assert agg.championship_standing == 3
    assert round(agg.average_finish, 2) == 3.91, "Average finish should be 3.91 (90 / 23)"
    assert round(agg.average_grid, 2) == 5.42, "Average grid should be 5.42 (130 / 24)"


@pytest.mark.integration
def test_piastri_twenty_four_round_aggregate(session: Session):
    """Piastri full season: 24 starts, 24 classified, 0 DNFs, 265 GP pts, 27 sprint pts, 292 total, 2 wins, P4."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "piastri", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 24
    assert agg.races_classified == 24, "Classified in all 24 Grand Prix races"
    assert agg.dnf_count == 0
    assert agg.total_race_points == Decimal("265.00")
    assert agg.total_sprint_points == Decimal("27.00")
    assert agg.total_points == Decimal("292.00")
    assert agg.wins == 2, "Should have 2 wins (Hungary, Azerbaijan)"
    assert agg.championship_standing == 4
    assert round(agg.average_finish, 2) == 5.12, "Average finish should be 5.12 (123 / 24, round-to-even)"
    assert round(agg.average_grid, 2) == 5.42, "Average grid should be 5.42 (130 / 24)"


@pytest.mark.integration
def test_sainz_twenty_four_round_aggregate(session: Session):
    """Sainz full season: 23 starts, 20 classified, 3 DNFs, 262 GP pts, 28 sprint pts, 290 total, 2 wins, P5."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "sainz", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 23, "Missed Saudi Arabia Round 2 with appendicitis"
    assert agg.races_classified == 20
    assert agg.dnf_count == 3, "Should have 3 DNFs (Canada R9, Azerbaijan R17, Brazil R21)"
    assert agg.total_race_points == Decimal("262.00")
    assert agg.total_sprint_points == Decimal("28.00")
    assert agg.total_points == Decimal("290.00")
    assert agg.wins == 2, "Should have 2 wins (Australia, Mexico City)"
    assert agg.championship_standing == 5
    assert round(agg.average_finish, 2) == 4.05, "Average finish should be 4.05 (81 / 20)"
    assert round(agg.average_grid, 2) == 5.70, "Average grid should be 5.70 (131 / 23)"


@pytest.mark.integration
def test_russell_twenty_four_round_aggregate(session: Session):
    """Russell full season: 24 starts, 21 classified, 3 non-classified, 226 GP pts, 19 sprint pts, 245 total, 2 wins, P6."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "russell", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 24
    assert agg.races_classified == 21
    # 2 DNFs (Australia crash, Britain water leak) + 1 DSQ (Belgium underweight) = 3 non-classified
    assert agg.dnf_count == 3
    assert agg.total_race_points == Decimal("226.00")
    assert agg.total_sprint_points == Decimal("19.00")
    assert agg.total_points == Decimal("245.00")
    assert agg.wins == 2, "Should have 2 wins (Austria, Las Vegas)"
    assert agg.championship_standing == 6
    assert round(agg.average_finish, 2) == 5.05, "Average finish should be 5.05 (106 / 21)"
    assert round(agg.average_grid, 2) == 5.62, "Average grid should be 5.62 (135 / 24, round-to-even)"


@pytest.mark.integration
def test_hamilton_twenty_four_round_aggregate(session: Session):
    """Hamilton full season: 24 starts, 22 classified, 2 DNFs, 207 GP pts, 16 sprint pts, 223 total, 2 wins, P7."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "hamilton", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 24
    assert agg.races_classified == 22
    assert agg.dnf_count == 2, "Should have 2 DNFs (Australia Round 3, United States Round 19)"
    assert agg.total_race_points == Decimal("207.00")
    assert agg.total_sprint_points == Decimal("16.00")
    assert agg.total_points == Decimal("223.00")
    assert agg.wins == 2, "Should have 2 wins (Britain, Belgium)"
    assert agg.championship_standing == 7
    assert round(agg.average_finish, 2) == 5.86, "Average finish should be 5.86 (129 / 22)"
    assert round(agg.average_grid, 2) == 8.83, "Average grid should be 8.83 (212 / 24)"


@pytest.mark.integration
def test_perez_twenty_four_round_aggregate(session: Session):
    """Perez full season: 24 starts, 19 classified, 5 DNFs, 138 GP pts, 14 sprint pts, 152 total, 0 wins, P8."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "perez", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 24
    assert agg.races_classified == 19
    assert agg.dnf_count == 5, "Should have 5 DNFs (Monaco R8, Canada R9, Azerbaijan R17, Qatar R23, Abu Dhabi R24)"
    assert agg.total_race_points == Decimal("138.00")
    assert agg.total_sprint_points == Decimal("14.00")
    assert agg.total_points == Decimal("152.00")
    assert agg.wins == 0
    assert agg.championship_standing == 8
    assert round(agg.average_finish, 2) == 7.42, "Average finish should be 7.42 (141 / 19)"
    assert round(agg.average_grid, 2) == 9.38, "Average grid should be 9.38 (225 / 24)"


@pytest.mark.integration
def test_bearman_twenty_four_round_aggregate(session: Session):
    """Bearman full season: 3 starts across 2 teams, 3 classified, 0 DNFs, 7 GP pts, 0 sprint pts, 7 total, P18."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "bearman", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 3, "Started R2 for Ferrari, R17 & R21 for Haas"
    assert agg.races_classified == 3, "Classified in all 3 starts (P7, P10, P12)"
    assert agg.dnf_count == 0
    assert agg.total_race_points == Decimal("7.00"), "6 points at Ferrari (P7) + 1 point at Haas (P10)"
    assert agg.total_sprint_points == Decimal("0.00")
    assert agg.total_points == Decimal("7.00")
    assert agg.wins == 0
    assert agg.best_finish == 7
    assert agg.best_grid == 10
    assert agg.championship_standing == 18
    assert round(agg.average_finish, 2) == 9.67, "Average finish should be 9.67 (29 / 3)"
    assert round(agg.average_grid, 2) == 12.00, "Average grid should be 12.00 (36 / 3)"


@pytest.mark.integration
def test_lawson_twenty_four_round_aggregate(session: Session):
    """Lawson full season: 6 starts (R19-R24), 5 classified, 1 DNF, 4 GP pts, 0 sprint pts, 4 total, P21."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "lawson", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 6, "Replaced Ricciardo at RB for Rounds 19-24"
    assert agg.races_classified == 5
    assert agg.dnf_count == 1, "Should have 1 DNF (Abu Dhabi Round 24 collision)"
    assert agg.total_race_points == Decimal("4.00"), "2 points at Austin (P9) + 2 points at Qatar (P9)"
    assert agg.total_sprint_points == Decimal("0.00")
    assert agg.total_points == Decimal("4.00")
    assert agg.wins == 0
    assert agg.championship_standing == 21
    assert round(agg.average_finish, 2) == 12.80, "Average finish should be 12.80 (64 / 5)"
    assert round(agg.average_grid, 2) == 13.17, "Average grid should be 13.17 (79 / 6)"


@pytest.mark.integration
def test_colapinto_twenty_four_round_aggregate(session: Session):
    """Colapinto full season: 9 starts (R16-R24), 6 classified, 3 DNFs, 5 GP pts, 0 sprint pts, 5 total, P19."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "colapinto", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.races_entered == 9, "Replaced Sargeant at Williams for Rounds 16-24"
    assert agg.races_classified == 6
    assert agg.dnf_count == 3, "Should have 3 DNFs (Brazil R21, Qatar R23, Abu Dhabi R24)"
    assert agg.total_race_points == Decimal("5.00"), "4 points at Baku (P8) + 1 point at Austin (P10)"
    assert agg.total_sprint_points == Decimal("0.00")
    assert agg.total_points == Decimal("5.00")
    assert agg.wins == 0
    assert agg.championship_standing == 19
    assert round(agg.average_finish, 2) == 11.17, "Average finish should be 11.17 (67 / 6)"
    assert round(agg.average_grid, 2) == 16.00, "Average grid should be 16.00 (144 / 9)"


@pytest.mark.integration
def test_antonelli_twenty_four_round_reference_entity(session: Session):
    """Antonelli is a reference-only entity (FP1 sessions) with 0 starts, 0 standings, and None aggregate."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    antonelli = session.scalar(select(Driver).where(Driver.driver_id == "antonelli"))
    assert antonelli is not None, "Antonelli entity must exist in database from FP1 ingestion"

    # Confirms reference-only entity cannot enter championship rankings or aggregates
    agg = get_driver_season_aggregate(session, SEASON_YEAR, "antonelli", up_to_round=TOTAL_ROUNDS)
    assert agg is None, "Antonelli had 0 race starts, aggregate must be None"

    agg_unbound = get_driver_season_aggregate(session, SEASON_YEAR, "antonelli")
    assert agg_unbound is None, "Unbounded Antonelli aggregate must be None"

    race_starts = session.scalar(
        select(func.count(RaceResult.id)).join(Driver).where(Driver.driver_id == "antonelli")
    )
    assert race_starts == 0, "Antonelli must have 0 race result entries"


# =============================================================================
# 2. Constructor Season Aggregate Tests (10 tests)
# =============================================================================


@pytest.mark.integration
def test_mclaren_twenty_four_round_aggregate(session: Session):
    """McLaren full season: 609 GP pts, 57 sprint pts, 666 total pts, 6 wins, P1 Constructors' Champion."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "mclaren", up_to_round=TOTAL_ROUNDS)
    agg_unbound = get_constructor_season_aggregate(session, SEASON_YEAR, "mclaren")

    assert agg is not None
    assert agg_unbound is not None
    assert agg.total_points == agg_unbound.total_points == Decimal("666.00")
    assert agg.total_race_points == Decimal("609.00")
    assert agg.total_sprint_points == Decimal("57.00")
    assert agg.wins == 6, "4 wins (Norris) + 2 wins (Piastri)"
    assert agg.championship_standing == 1, "McLaren won the 2024 Constructors' Championship"

    # Driver contributions: Norris (374.00) + Piastri (292.00) = 666.00
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("666.00")
    nor_c = next(c for c in agg.driver_contributions if c.driver_id == "norris")
    pia_c = next(c for c in agg.driver_contributions if c.driver_id == "piastri")
    assert nor_c.total_points == Decimal("374.00")
    assert pia_c.total_points == Decimal("292.00")


@pytest.mark.integration
def test_ferrari_twenty_four_round_aggregate(session: Session):
    """Ferrari full season: 595 GP pts, 57 sprint pts, 652 total pts, 5 wins, 3 drivers, P2."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "ferrari", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_race_points == Decimal("595.00")
    assert agg.total_sprint_points == Decimal("57.00")
    assert agg.total_points == Decimal("652.00")
    assert agg.wins == 5, "3 wins (Leclerc) + 2 wins (Sainz)"
    assert agg.championship_standing == 2

    # Driver contributions: Leclerc (356.00) + Sainz (290.00) + Bearman (6.00) = 652.00
    assert len(agg.driver_contributions) == 3
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("652.00")
    lec_c = next(c for c in agg.driver_contributions if c.driver_id == "leclerc")
    sai_c = next(c for c in agg.driver_contributions if c.driver_id == "sainz")
    bea_c = next(c for c in agg.driver_contributions if c.driver_id == "bearman")
    assert lec_c.total_points == Decimal("356.00")
    assert sai_c.total_points == Decimal("290.00")
    assert bea_c.total_points == Decimal("6.00")


@pytest.mark.integration
def test_red_bull_twenty_four_round_aggregate(session: Session):
    """Red Bull full season: 537 GP pts, 52 sprint pts, 589 total pts, 9 wins, P3."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "red_bull", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_race_points == Decimal("537.00")
    assert agg.total_sprint_points == Decimal("52.00")
    assert agg.total_points == Decimal("589.00")
    assert agg.wins == 9, "9 wins (Verstappen)"
    assert agg.championship_standing == 3

    # Driver contributions: Verstappen (437.00) + Perez (152.00) = 589.00
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("589.00")
    ver_c = next(c for c in agg.driver_contributions if c.driver_id == "max_verstappen")
    per_c = next(c for c in agg.driver_contributions if c.driver_id == "perez")
    assert ver_c.total_points == Decimal("437.00")
    assert per_c.total_points == Decimal("152.00")


@pytest.mark.integration
def test_mercedes_twenty_four_round_aggregate(session: Session):
    """Mercedes full season: 433 GP pts, 35 sprint pts, 468 total pts, 4 wins, P4."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "mercedes", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_race_points == Decimal("433.00")
    assert agg.total_sprint_points == Decimal("35.00")
    assert agg.total_points == Decimal("468.00")
    assert agg.wins == 4, "2 wins (Russell) + 2 wins (Hamilton)"
    assert agg.championship_standing == 4

    # Driver contributions: Russell (245.00) + Hamilton (223.00) = 468.00
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("468.00")
    rus_c = next(c for c in agg.driver_contributions if c.driver_id == "russell")
    ham_c = next(c for c in agg.driver_contributions if c.driver_id == "hamilton")
    assert rus_c.total_points == Decimal("245.00")
    assert ham_c.total_points == Decimal("223.00")


@pytest.mark.integration
def test_aston_martin_twenty_four_round_aggregate(session: Session):
    """Aston Martin full season: 94 GP pts, 0 sprint pts, 94 total pts, 0 wins, P5."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "aston_martin", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_race_points == Decimal("94.00")
    assert agg.total_sprint_points == Decimal("0.00")
    assert agg.total_points == Decimal("94.00")
    assert agg.wins == 0
    assert agg.championship_standing == 5

    # Driver contributions: Alonso (70.00) + Stroll (24.00) = 94.00
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("94.00")
    alo_c = next(c for c in agg.driver_contributions if c.driver_id == "alonso")
    str_c = next(c for c in agg.driver_contributions if c.driver_id == "stroll")
    assert alo_c.total_points == Decimal("70.00")
    assert str_c.total_points == Decimal("24.00")


@pytest.mark.integration
def test_alpine_twenty_four_round_aggregate(session: Session):
    """Alpine full season: 63 GP pts, 2 sprint pts, 65 total pts, 0 wins, 3 drivers, P6."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "alpine", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_race_points == Decimal("63.00")
    assert agg.total_sprint_points == Decimal("2.00")
    assert agg.total_points == Decimal("65.00")
    assert agg.wins == 0
    assert agg.championship_standing == 6

    # Driver contributions: Gasly (42.00) + Ocon (23.00) + Doohan (0.00) = 65.00
    assert len(agg.driver_contributions) == 3
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("65.00")
    gas_c = next(c for c in agg.driver_contributions if c.driver_id == "gasly")
    oco_c = next(c for c in agg.driver_contributions if c.driver_id == "ocon")
    doo_c = next(c for c in agg.driver_contributions if c.driver_id == "doohan")
    assert gas_c.total_points == Decimal("42.00")
    assert oco_c.total_points == Decimal("23.00")
    assert doo_c.total_points == Decimal("0.00")


@pytest.mark.integration
def test_haas_twenty_four_round_aggregate(session: Session):
    """Haas full season: 51 GP pts, 7 sprint pts, 58 total pts, 0 wins, 3 drivers, P7."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "haas", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_race_points == Decimal("51.00")
    assert agg.total_sprint_points == Decimal("7.00")
    assert agg.total_points == Decimal("58.00")
    assert agg.wins == 0
    assert agg.championship_standing == 7

    # Driver contributions: Hulkenberg (41.00) + Kevin Magnussen (16.00) + Bearman (1.00) = 58.00
    assert len(agg.driver_contributions) == 3
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("58.00")
    hul_c = next(c for c in agg.driver_contributions if c.driver_id == "hulkenberg")
    mag_c = next(c for c in agg.driver_contributions if c.driver_id == "kevin_magnussen")
    bea_c = next(c for c in agg.driver_contributions if c.driver_id == "bearman")
    assert hul_c.total_points == Decimal("41.00")
    assert mag_c.total_points == Decimal("16.00")
    assert bea_c.total_points == Decimal("1.00")


@pytest.mark.integration
def test_rb_twenty_four_round_aggregate(session: Session):
    """RB full season: 40 GP pts, 6 sprint pts, 46 total pts, 0 wins, 3 drivers, P8."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "rb", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_race_points == Decimal("40.00")
    assert agg.total_sprint_points == Decimal("6.00")
    assert agg.total_points == Decimal("46.00")
    assert agg.wins == 0
    assert agg.championship_standing == 8

    # Driver contributions: Tsunoda (30.00) + Ricciardo (12.00) + Lawson (4.00) = 46.00
    assert len(agg.driver_contributions) == 3
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("46.00")
    tsu_c = next(c for c in agg.driver_contributions if c.driver_id == "tsunoda")
    ric_c = next(c for c in agg.driver_contributions if c.driver_id == "ricciardo")
    law_c = next(c for c in agg.driver_contributions if c.driver_id == "lawson")
    assert tsu_c.total_points == Decimal("30.00")
    assert ric_c.total_points == Decimal("12.00")
    assert law_c.total_points == Decimal("4.00")


@pytest.mark.integration
def test_williams_twenty_four_round_aggregate(session: Session):
    """Williams full season: 17 GP pts, 0 sprint pts, 17 total pts, 0 wins, 3 drivers, P9."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "williams", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_race_points == Decimal("17.00")
    assert agg.total_sprint_points == Decimal("0.00")
    assert agg.total_points == Decimal("17.00")
    assert agg.wins == 0
    assert agg.championship_standing == 9

    # Driver contributions: Albon (12.00) + Colapinto (5.00) + Sargeant (0.00) = 17.00
    assert len(agg.driver_contributions) == 3
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("17.00")
    alb_c = next(c for c in agg.driver_contributions if c.driver_id == "albon")
    col_c = next(c for c in agg.driver_contributions if c.driver_id == "colapinto")
    sar_c = next(c for c in agg.driver_contributions if c.driver_id == "sargeant")
    assert alb_c.total_points == Decimal("12.00")
    assert col_c.total_points == Decimal("5.00")
    assert sar_c.total_points == Decimal("0.00")


@pytest.mark.integration
def test_sauber_twenty_four_round_aggregate(session: Session):
    """Sauber full season: 4 GP pts, 0 sprint pts, 4 total pts, 0 wins, P10."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "sauber", up_to_round=TOTAL_ROUNDS)
    assert agg is not None
    assert agg.total_race_points == Decimal("4.00")
    assert agg.total_sprint_points == Decimal("0.00")
    assert agg.total_points == Decimal("4.00")
    assert agg.wins == 0
    assert agg.championship_standing == 10

    # Driver contributions: Zhou (4.00) + Bottas (0.00) = 4.00
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == Decimal("4.00")
    zho_c = next(c for c in agg.driver_contributions if c.driver_id == "zhou")
    bot_c = next(c for c in agg.driver_contributions if c.driver_id == "bottas")
    assert zho_c.total_points == Decimal("4.00")
    assert bot_c.total_points == Decimal("0.00")


# =============================================================================
# 3. Teammate Head-to-Head & Edge Cases (4 tests)
# =============================================================================


@pytest.mark.integration
def test_red_bull_teammate_head_to_head(session: Session):
    """Red Bull H2H: Verstappen vs Perez across 24 rounds: Quali 23-1, Race 18-0 with 6 excluded."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    comps = get_season_teammate_comparisons(session, SEASON_YEAR, up_to_round=TOTAL_ROUNDS)
    rb = next((c for c in comps if c.constructor_id == "red_bull"), None)
    assert rb is not None, "Red Bull comparison must exist"
    assert rb.rounds_together == 24
    assert rb.qualifying_comparable_rounds == 24

    # Quali H2H: 23-1 (Perez only beat Verstappen at Baku R17: P4 vs P6)
    if rb.driver_a_id == "max_verstappen":
        assert rb.qualifying_head_to_head_a == 23
        assert rb.qualifying_head_to_head_b == 1
        # Race H2H: 18-0 (18 comparable finishes, 6 unclassified exclusions: VER R3; PER R8, R9, R17, R23, R24)
        assert rb.race_comparable_rounds == 18
        assert rb.race_head_to_head_a == 18
        assert rb.race_head_to_head_b == 0
        assert rb.total_points_a == Decimal("437.00")
        assert rb.total_points_b == Decimal("152.00")
    else:
        assert rb.qualifying_head_to_head_a == 1
        assert rb.qualifying_head_to_head_b == 23
        assert rb.race_comparable_rounds == 18
        assert rb.race_head_to_head_a == 0
        assert rb.race_head_to_head_b == 18
        assert rb.total_points_a == Decimal("152.00")
        assert rb.total_points_b == Decimal("437.00")


@pytest.mark.integration
def test_mercedes_teammate_head_to_head(session: Session):
    """Mercedes H2H: Russell vs Hamilton across 24 rounds: Quali 19-5, Race 13-7 with 4 excluded."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    comps = get_season_teammate_comparisons(session, SEASON_YEAR, up_to_round=TOTAL_ROUNDS)
    merc = next((c for c in comps if c.constructor_id == "mercedes"), None)
    assert merc is not None, "Mercedes comparison must exist"
    assert merc.rounds_together == 24
    assert merc.qualifying_comparable_rounds == 24
    # Race exclusions: 4 rounds (R3 dual DNF, R12 RUS water leak, R14 RUS underweight DSQ, R19 HAM gravel DNF)
    assert merc.race_comparable_rounds == 20

    if merc.driver_a_id == "russell":
        assert merc.qualifying_head_to_head_a == 19
        assert merc.qualifying_head_to_head_b == 5
        assert merc.race_head_to_head_a == 13
        assert merc.race_head_to_head_b == 7
        assert merc.total_points_a == Decimal("245.00")
        assert merc.total_points_b == Decimal("223.00")
    else:
        assert merc.qualifying_head_to_head_a == 5
        assert merc.qualifying_head_to_head_b == 19
        assert merc.race_head_to_head_a == 7
        assert merc.race_head_to_head_b == 13
        assert merc.total_points_a == Decimal("223.00")
        assert merc.total_points_b == Decimal("245.00")


@pytest.mark.integration
def test_substitute_pairings_isolated(session: Session):
    """Substitute teammate pairings are strictly isolated to their shared events."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    comps = get_season_teammate_comparisons(session, SEASON_YEAR, up_to_round=TOTAL_ROUNDS)

    # 1. Williams: Albon vs Colapinto (9 rounds: R16-R24)
    alb_col = next(
        (c for c in comps if c.constructor_id == "williams" and "colapinto" in (c.driver_a_id, c.driver_b_id)),
        None,
    )
    assert alb_col is not None, "Albon vs Colapinto comparison must exist"
    assert alb_col.rounds_together == 9
    assert alb_col.qualifying_comparable_rounds == 9
    if alb_col.driver_a_id == "albon":
        assert alb_col.qualifying_head_to_head_a == 7
        assert alb_col.qualifying_head_to_head_b == 2
        # Comparable races = 3 (6 excluded: Albon DNS R21, Albon DNF R18, R19, R20, R24; Colapinto DNF R21, R23, R24)
        assert alb_col.race_comparable_rounds == 3
        assert alb_col.race_head_to_head_a == 2
        assert alb_col.race_head_to_head_b == 1
        assert alb_col.total_points_a == Decimal("8.00"), "Albon points scored during shared rounds"
        assert alb_col.total_points_b == Decimal("5.00")
    else:
        assert alb_col.qualifying_head_to_head_a == 2
        assert alb_col.qualifying_head_to_head_b == 7
        assert alb_col.race_comparable_rounds == 3
        assert alb_col.race_head_to_head_a == 1
        assert alb_col.race_head_to_head_b == 2
        assert alb_col.total_points_a == Decimal("5.00")
        assert alb_col.total_points_b == Decimal("8.00")

    # 2. RB: Tsunoda vs Lawson (6 rounds: R19-R24)
    tsu_law = next(
        (c for c in comps if c.constructor_id == "rb" and "lawson" in (c.driver_a_id, c.driver_b_id)),
        None,
    )
    assert tsu_law is not None, "Tsunoda vs Lawson comparison must exist"
    assert tsu_law.rounds_together == 6
    assert tsu_law.qualifying_comparable_rounds == 6
    if tsu_law.driver_a_id == "tsunoda":
        assert tsu_law.qualifying_head_to_head_a == 6
        assert tsu_law.qualifying_head_to_head_b == 0
        # Comparable races = 4 (2 excluded: Tsunoda DNF R20, Lawson DNF R24)
        assert tsu_law.race_comparable_rounds == 4
        assert tsu_law.race_head_to_head_a == 3
        assert tsu_law.race_head_to_head_b == 1
        assert tsu_law.total_points_a == Decimal("8.00"), "Tsunoda points during shared rounds"
        assert tsu_law.total_points_b == Decimal("4.00")
    else:
        assert tsu_law.qualifying_head_to_head_a == 0
        assert tsu_law.qualifying_head_to_head_b == 6
        assert tsu_law.race_comparable_rounds == 4
        assert tsu_law.race_head_to_head_a == 1
        assert tsu_law.race_head_to_head_b == 3
        assert tsu_law.total_points_a == Decimal("4.00")
        assert tsu_law.total_points_b == Decimal("8.00")

    # 3. Haas: Bearman vs Hulkenberg (2 rounds: R17 Azerbaijan, R21 Brazil)
    bea_hul = next(
        (c for c in comps if c.constructor_id == "haas" and "bearman" in (c.driver_a_id, c.driver_b_id)),
        None,
    )
    assert bea_hul is not None, "Bearman vs Hulkenberg comparison must exist"
    assert bea_hul.rounds_together == 2
    assert bea_hul.qualifying_comparable_rounds == 2
    if bea_hul.driver_a_id == "bearman":
        assert bea_hul.qualifying_head_to_head_a == 2
        assert bea_hul.qualifying_head_to_head_b == 0
        # Comparable races = 1 (1 excluded: Hulkenberg pushed-start DSQ at Brazil R21)
        assert bea_hul.race_comparable_rounds == 1
        assert bea_hul.race_head_to_head_a == 1
        assert bea_hul.race_head_to_head_b == 0
        assert bea_hul.total_points_a == Decimal("1.00"), "Bearman P10 at Baku"
        assert bea_hul.total_points_b == Decimal("0.00")
    else:
        assert bea_hul.qualifying_head_to_head_a == 0
        assert bea_hul.qualifying_head_to_head_b == 2
        assert bea_hul.race_comparable_rounds == 1
        assert bea_hul.race_head_to_head_a == 0
        assert bea_hul.race_head_to_head_b == 1
        assert bea_hul.total_points_a == Decimal("0.00")
        assert bea_hul.total_points_b == Decimal("1.00")


@pytest.mark.integration
def test_all_constructors_season_order(session: Session):
    """All 10 constructors ranked in strict championship order from P1 to P10."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    aggs = get_all_constructors_season_aggregates(session, SEASON_YEAR, up_to_round=TOTAL_ROUNDS)
    assert len(aggs) == 10, "Exactly 10 constructors participated in 2024"

    expected_order = [
        "mclaren",
        "ferrari",
        "red_bull",
        "mercedes",
        "aston_martin",
        "alpine",
        "haas",
        "rb",
        "williams",
        "sauber",
    ]
    observed_order = [a.constructor_id for a in aggs]
    assert observed_order == expected_order, f"Expected order {expected_order}, got {observed_order}"

    for standing, agg in enumerate(aggs, 1):
        assert agg.championship_standing == standing

    # Verify unbounded call returns identical championship rankings
    aggs_unbound = get_all_constructors_season_aggregates(session, SEASON_YEAR)
    assert [a.constructor_id for a in aggs_unbound] == expected_order


# =============================================================================
# 4. Rolling Performance, Points Rates & Insights (2 tests)
# =============================================================================


@pytest.mark.integration
def test_rolling_performance_and_points_rates(session: Session):
    """Trailing window performance (3 and 5 rounds) and strictly verified points rates."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    # 1. Verstappen rolling form
    ver_traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen", up_to_round=TOTAL_ROUNDS)
    ver_form3 = compute_driver_form_summary(ver_traj, window_size=3)
    ver_win3 = next(
        w for w in ver_form3.rolling_windows if w.metric_name == "finish_position" and w.round == 24
    )
    assert ver_win3.rounds_included == [22, 23, 24]
    assert round(ver_win3.mean, 2) == 4.00, "Verstappen R22-R24 finish mean = 4.00 (P5, P1, P6)"
    ver_pts3 = next(
        w for w in ver_form3.rolling_windows if w.metric_name == "points" and w.round == 24
    )
    assert round(ver_pts3.mean, 2) == 14.67, "Verstappen R22-R24 points mean = 14.67 (44.00 / 3)"
    ver_pts3_sum = sum(t.total_round_points for t in ver_traj if t.round in [22, 23, 24])
    assert ver_pts3_sum == Decimal("44.00")

    ver_form5 = compute_driver_form_summary(ver_traj, window_size=5)
    ver_win5 = next(
        w for w in ver_form5.rolling_windows if w.metric_name == "finish_position" and w.round == 24
    )
    assert ver_win5.rounds_included == [20, 21, 22, 23, 24]
    assert round(ver_win5.mean, 2) == 3.80, "Verstappen R20-R24 finish mean = 3.80 (P6, P1, P5, P1, P6)"
    ver_pts5 = next(
        w for w in ver_form5.rolling_windows if w.metric_name == "points" and w.round == 24
    )
    assert round(ver_pts5.mean, 2) == 16.60, "Verstappen R20-R24 points mean = 16.60 (83.00 / 5)"
    ver_pts5_sum = sum(t.total_round_points for t in ver_traj if t.round in [20, 21, 22, 23, 24])
    assert ver_pts5_sum == Decimal("83.00")

    # 2. Norris rolling form
    nor_traj = get_driver_trajectory(session, SEASON_YEAR, "norris", up_to_round=TOTAL_ROUNDS)
    nor_form3 = compute_driver_form_summary(nor_traj, window_size=3)
    nor_win3 = next(
        w for w in nor_form3.rolling_windows if w.metric_name == "finish_position" and w.round == 24
    )
    assert round(nor_win3.mean, 2) == 5.67, "Norris R22-R24 finish mean = 5.67 (P6, P10, P1)"
    nor_pts3 = next(
        w for w in nor_form3.rolling_windows if w.metric_name == "points" and w.round == 24
    )
    assert round(nor_pts3.mean, 2) == 14.33, "Norris R22-R24 points mean = 14.33 (43.00 / 3)"
    nor_pts3_sum = sum(t.total_round_points for t in nor_traj if t.round in [22, 23, 24])
    assert nor_pts3_sum == Decimal("43.00")

    nor_form5 = compute_driver_form_summary(nor_traj, window_size=5)
    nor_win5 = next(
        w for w in nor_form5.rolling_windows if w.metric_name == "finish_position" and w.round == 24
    )
    assert round(nor_win5.mean, 2) == 5.00, "Norris R20-R24 finish mean = 5.00 (P2, P6, P6, P10, P1)"
    nor_pts5 = next(
        w for w in nor_form5.rolling_windows if w.metric_name == "points" and w.round == 24
    )
    assert round(nor_pts5.mean, 2) == 15.40, "Norris R20-R24 points mean = 15.40 (77.00 / 5)"
    nor_pts5_sum = sum(t.total_round_points for t in nor_traj if t.round in [20, 21, 22, 23, 24])
    assert nor_pts5_sum == Decimal("77.00")

    # 3. Leclerc rolling form
    lec_traj = get_driver_trajectory(session, SEASON_YEAR, "leclerc", up_to_round=TOTAL_ROUNDS)
    lec_form3 = compute_driver_form_summary(lec_traj, window_size=3)
    lec_win3 = next(
        w for w in lec_form3.rolling_windows if w.metric_name == "finish_position" and w.round == 24
    )
    assert round(lec_win3.mean, 2) == 3.00, "Leclerc R22-R24 finish mean = 3.00 (P4, P2, P3)"
    lec_pts3 = next(
        w for w in lec_form3.rolling_windows if w.metric_name == "points" and w.round == 24
    )
    assert round(lec_pts3.mean, 2) == 16.33, "Leclerc R22-R24 points mean = 16.33 (49.00 / 3)"
    lec_pts3_sum = sum(t.total_round_points for t in lec_traj if t.round in [22, 23, 24])
    assert lec_pts3_sum == Decimal("49.00")

    lec_form5 = compute_driver_form_summary(lec_traj, window_size=5)
    lec_win5 = next(
        w for w in lec_form5.rolling_windows if w.metric_name == "finish_position" and w.round == 24
    )
    assert round(lec_win5.mean, 2) == 3.40, "Leclerc R20-R24 finish mean = 3.40 (P3, P5, P4, P2, P3)"
    lec_pts5 = next(
        w for w in lec_form5.rolling_windows if w.metric_name == "points" and w.round == 24
    )
    assert round(lec_pts5.mean, 2) == 16.20, "Leclerc R20-R24 points mean = 16.20 (81.00 / 5)"
    lec_pts5_sum = sum(t.total_round_points for t in lec_traj if t.round in [20, 21, 22, 23, 24])
    assert lec_pts5_sum == Decimal("81.00")

    # 4. Points-rate denominator mathematical reconciliation
    # Verstappen: 24 GP starts, 24 rounds entered
    ver_agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen", up_to_round=TOTAL_ROUNDS)
    assert round(float(ver_agg.total_race_points) / ver_agg.races_entered, 2) == 16.62
    assert round(float(ver_agg.total_points) / len(ver_traj), 2) == 18.21

    # Norris: 24 GP starts, 24 rounds entered
    nor_agg = get_driver_season_aggregate(session, SEASON_YEAR, "norris", up_to_round=TOTAL_ROUNDS)
    assert round(float(nor_agg.total_race_points) / nor_agg.races_entered, 2) == 14.33
    assert round(float(nor_agg.total_points) / len(nor_traj), 2) == 15.58

    # Sainz: 23 GP starts, 23 rounds entered, 24 championship rounds in season
    sai_traj = get_driver_trajectory(session, SEASON_YEAR, "sainz", up_to_round=TOTAL_ROUNDS)
    sai_agg = get_driver_season_aggregate(session, SEASON_YEAR, "sainz", up_to_round=TOTAL_ROUNDS)
    assert sai_agg.races_entered == 23
    assert len(sai_traj) == 23
    assert round(float(sai_agg.total_race_points) / sai_agg.races_entered, 2) == 11.39
    assert round(float(sai_agg.total_points) / len(sai_traj), 2) == 12.61
    assert round(float(sai_agg.total_points) / TOTAL_ROUNDS, 2) == 12.08


@pytest.mark.integration
def test_full_season_deterministic_insights(session: Session):
    """Exactly 33 deterministic insights emitted, unique, and strictly adhering to rules."""
    if not _check_db_has_data(session):
        pytest.skip("Requires 2024 full season (24 rounds) database")

    insights = LongitudinalInsightService.get_season_insights(
        session, SEASON_YEAR, up_to_round=TOTAL_ROUNDS
    )
    assert len(insights) == 33, f"Expected exactly 33 deterministic insights, got {len(insights)}"

    # Insight ID uniqueness and deduplication
    insight_ids = [i.insight_id for i in insights]
    assert len(insight_ids) == len(set(insight_ids)) == 33, "All 33 insight IDs must be unique"

    # Category distribution verification
    cats = Counter(i.category.value for i in insights)
    assert cats["CONSTRUCTOR"] == 2, "2 constructor podium rate insights (Ferrari, McLaren)"
    assert cats["DRIVER_FORM"] == 4, "4 driver form insights (Leclerc, Verstappen, Russell, Sainz)"
    assert cats["POINTS"] == 3, "3 points rate insights (Verstappen/round, Norris/round, Verstappen/start)"
    assert cats["POSITION_CHANGE"] == 4, "4 position gain insights (Bearman, Colapinto, Hamilton, Zhou)"
    assert cats["TEAMMATE"] == 20, "20 teammate H2H insights (6 points, 9 qualifying, 5 race)"

    # Substitute safety guardrails
    subject_ids = {i.subject_id for i in insights}
    comp_subject_ids = {i.comparison_subject_id for i in insights if i.comparison_subject_id}
    all_insight_drivers = subject_ids.union(comp_subject_ids)

    # Reference entities and zero-round drivers must produce zero insights
    assert "antonelli" not in all_insight_drivers, "Antonelli must produce 0 insights"
    assert "doohan" not in all_insight_drivers, "Doohan must produce 0 insights"

    # Bearman teammate insights must be suppressed due to small sample size
    bearman_tm_insights = [
        i for i in insights if i.category.value == "TEAMMATE" and "bearman" in (i.subject_id, i.comparison_subject_id)
    ]
    assert len(bearman_tm_insights) == 0, "Bearman teammate insights must be suppressed"

    # Bearman individual gain insight must be present with sample_size = 3 and MODERATE evidence strength
    bearman_gain = next((i for i in insights if i.subject_id == "bearman" and i.category.value == "POSITION_CHANGE"), None)
    assert bearman_gain is not None
    assert bearman_gain.sample_size == 3
    assert bearman_gain.evidence_strength.value == "MODERATE"

    # Colapinto individual gain insight must be present with sample_size = 6 and HIGH evidence strength
    colapinto_gain = next((i for i in insights if i.subject_id == "colapinto" and i.category.value == "POSITION_CHANGE"), None)
    assert colapinto_gain is not None
    assert colapinto_gain.sample_size == 6
    assert colapinto_gain.evidence_strength.value == "HIGH"

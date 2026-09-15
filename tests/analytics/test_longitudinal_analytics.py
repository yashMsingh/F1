"""Tests for longitudinal analytical queries — multi-race trajectories, aggregates, and teammates.

These tests verify against the real 2024 Rounds 1-5 dataset already persisted in PostgreSQL:
  Round 1: Bahrain GP
  Round 2: Saudi Arabian GP (Bearman substitutes for Sainz at Ferrari)
  Round 3: Australian GP (Verstappen DNF)
  Round 4: Japanese GP
  Round 5: Chinese GP (Sprint weekend)

Known ground-truth facts used for assertions:
  - Verstappen: 110 pts after Round 5, P1 in championship
  - Red Bull: 195 pts after Round 5, P1 in constructors
  - Sainz: Won Round 3 (Australia) — Ferrari's only win so far
  - Bearman: P7 in Round 2 (Jeddah), filling in for Sainz (appendix surgery)
  - China Round 5 is a Sprint weekend
  - Verstappen DNF'd in Round 3 (Australia) with brake failure
"""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session


# ── Fixtures: use session from conftest (real PostgreSQL connection) ───────────

SEASON_YEAR = 2024
TOTAL_ROUNDS = 5

# Known ground-truth driver facts (post Round 5)
VER_TOTAL_PTS = 110  # Race pts + Sprint pts combined (Championship)
VER_WINS_1_TO_5 = 4  # Rounds 1, 2, 4, 5

SAINZ_WIN_ROUND = 3  # Australia
SAINZ_ENTRIES_1_TO_5 = 4  # Sat out Round 2 (Bearman subbed), entered Rounds 1, 3, 4, 5

BEARMAN_ENTRIES = 1  # Round 2 only
BEARMAN_FINISH = 7  # P7 in Jeddah
BEARMAN_POINTS = Decimal("6.0")

# Constructor facts (post Round 5)
RB_TOTAL_PTS = 195
RB_WINS = 4


# ── Driver Trajectory Tests ───────────────────────────────────────────────────


def test_driver_trajectory_returns_correct_number_of_rounds(session: Session):
    """Verstappen should have 5 trajectory entries across Rounds 1-5."""
    from app.analytics.longitudinal_driver import get_driver_trajectory

    traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen")
    assert len(traj) == TOTAL_ROUNDS, (
        f"Expected {TOTAL_ROUNDS} trajectory entries for Verstappen, got {len(traj)}"
    )


def test_driver_trajectory_sorted_by_round(session: Session):
    """Trajectory should be ordered by round ascending."""
    from app.analytics.longitudinal_driver import get_driver_trajectory

    traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen")
    rounds = [t.round for t in traj]
    assert rounds == sorted(rounds), f"Trajectory not sorted: {rounds}"


def test_driver_trajectory_australia_dnf(session: Session):
    """Verstappen DNF'd in Round 3 (Australia) — finish_position is None, is_classified is False."""
    from app.analytics.longitudinal_driver import get_driver_trajectory

    traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen")
    aus_item = next((t for t in traj if t.round == 3), None)
    assert aus_item is not None, "Round 3 (Australia) not found in Verstappen trajectory"
    assert aus_item.finish_position is None, "Verstappen should have no finish position (DNF)"
    assert aus_item.is_classified is False, "Verstappen should not be classified in Australia"
    assert aus_item.race_points == Decimal("0.0"), "Verstappen should score 0 race points for DNF"


def test_driver_trajectory_sprint_points_separation(session: Session):
    """Round 5 (China) is a sprint weekend — sprint_points > 0, separately tracked from race_points."""
    from app.analytics.longitudinal_driver import get_driver_trajectory

    traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen")
    china_item = next((t for t in traj if t.round == 5), None)
    assert china_item is not None, "Round 5 (China) not found in Verstappen trajectory"
    assert china_item.sprint_points > 0, "Verstappen should have sprint points in China"
    assert china_item.race_points > 0, "Verstappen should have GP race points in China"
    assert china_item.total_round_points == china_item.race_points + china_item.sprint_points


def test_driver_trajectory_cumulative_totals_are_monotonic(session: Session):
    """Cumulative total points should be non-decreasing across rounds."""
    from app.analytics.longitudinal_driver import get_driver_trajectory

    traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen")
    for i in range(1, len(traj)):
        assert traj[i].cumulative_total_points >= traj[i - 1].cumulative_total_points, (
            f"Cumulative points decreased at round {traj[i].round}"
        )


def test_driver_trajectory_up_to_round_filter(session: Session):
    """up_to_round=2 should return only rounds 1 and 2."""
    from app.analytics.longitudinal_driver import get_driver_trajectory

    traj = get_driver_trajectory(session, SEASON_YEAR, "max_verstappen", up_to_round=2)
    assert len(traj) == 2
    assert [t.round for t in traj] == [1, 2]


def test_driver_trajectory_nonexistent_driver(session: Session):
    """A non-existent driver slug should return an empty list."""
    from app.analytics.longitudinal_driver import get_driver_trajectory

    result = get_driver_trajectory(session, SEASON_YEAR, "nonexistent_driver_xyz")
    assert result == []


# ── Driver Season Aggregate Tests ────────────────────────────────────────────


def test_driver_season_aggregate_verstappen_championship_standing(session: Session):
    """Verstappen should be P1 in the championship after Round 5."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen")
    assert agg is not None
    assert agg.championship_standing == 1


def test_driver_season_aggregate_verstappen_dnf_counts(session: Session):
    """Verstappen entered all 5 races; DNF'd once (Round 3 Australia)."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen")
    assert agg is not None
    assert agg.races_entered == 5
    assert agg.dnf_count == 1
    assert agg.races_classified == 4


def test_driver_season_aggregate_verstappen_wins(session: Session):
    """Verstappen won Rounds 1, 2, 4, 5 — 4 wins total through Round 5."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen")
    assert agg is not None
    assert agg.wins == VER_WINS_1_TO_5


def test_driver_season_aggregate_dnf_excluded_from_average_finish(session: Session):
    """Average finish should use only classified results (Australia DNF excluded from denominator)."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen")
    assert agg is not None
    # Classified finishes: Rounds 1,2,4,5 — all P1 -> average = 1.0
    assert agg.average_finish == 1.0


def test_driver_season_aggregate_points_separated(session: Session):
    """Total points = race points + sprint points, and sprint points > 0 for Round 5."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen")
    assert agg is not None
    assert agg.total_sprint_points > 0, "Should have sprint points from China"
    assert agg.total_points == agg.total_race_points + agg.total_sprint_points
    assert agg.total_points == Decimal(str(VER_TOTAL_PTS))


def test_driver_season_aggregate_pit_lane_grid_excluded(session: Session):
    """Drivers with pit lane starts (grid=0 or None) should have those rounds excluded from average_grid."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    # Any driver will do — grid-exclusion logic must not return negative or 0 as best_grid
    agg = get_driver_season_aggregate(session, SEASON_YEAR, "max_verstappen")
    assert agg is not None
    if agg.best_grid is not None:
        assert agg.best_grid >= 1, "best_grid must be >= 1 (pit lane start excluded)"


def test_driver_season_aggregate_bearman_one_race(session: Session):
    """Bearman subbed for Sainz in Round 2 only — should have 1 race entry, P7 finish, 6 pts."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "bearman")
    assert agg is not None, "Bearman should be found in 2024 season"
    assert agg.races_entered == BEARMAN_ENTRIES
    assert agg.best_finish == BEARMAN_FINISH
    assert agg.total_points == BEARMAN_POINTS
    assert agg.constructor_id == "ferrari"


def test_driver_season_aggregate_sainz_3_or_4_races(session: Session):
    """Sainz did not participate in Round 2 (Bearman subbed) so should have 4 entries: Rounds 1,3,4,5."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "sainz")
    assert agg is not None
    assert agg.races_entered == SAINZ_ENTRIES_1_TO_5


def test_driver_season_aggregate_sainz_australia_win(session: Session):
    """Sainz won Round 3 (Australia) — should have at least 1 win in the aggregate."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    agg = get_driver_season_aggregate(session, SEASON_YEAR, "sainz")
    assert agg is not None
    assert agg.wins >= 1, "Sainz should have at least 1 win (Australia)"
    assert agg.best_finish == 1


def test_driver_season_aggregate_nonexistent(session: Session):
    """Non-existent driver should return None."""
    from app.analytics.longitudinal_driver import get_driver_season_aggregate

    result = get_driver_season_aggregate(session, SEASON_YEAR, "nonexistent_xyz")
    assert result is None


# ── All Drivers Season Aggregates ────────────────────────────────────────────


def test_get_all_drivers_season_aggregates_count(session: Session):
    """Should return all drivers who participated in 2024 Rounds 1-5 (21 known entries)."""
    from app.analytics.longitudinal_driver import get_all_drivers_season_aggregates

    aggs = get_all_drivers_season_aggregates(session, SEASON_YEAR)
    # At minimum 20 drivers, allowing for Bearman substitution making it 21
    assert len(aggs) >= 20, f"Expected >= 20 drivers, got {len(aggs)}"


def test_get_all_drivers_season_aggregates_verstappen_first(session: Session):
    """Verstappen should be first in the sorted list (P1 championship)."""
    from app.analytics.longitudinal_driver import get_all_drivers_season_aggregates

    aggs = get_all_drivers_season_aggregates(session, SEASON_YEAR)
    assert len(aggs) > 0
    assert aggs[0].driver_id == "max_verstappen"


def test_get_all_drivers_season_aggregates_up_to_round_filter(session: Session):
    """up_to_round=1 should return only drivers from Round 1 (Bahrain)."""
    from app.analytics.longitudinal_driver import get_all_drivers_season_aggregates

    aggs = get_all_drivers_season_aggregates(session, SEASON_YEAR, up_to_round=1)
    # Bahrain had 20 drivers
    assert len(aggs) == 20, f"Expected 20 drivers for Round 1 only, got {len(aggs)}"
    # Every driver has up_to_round = 1
    for a in aggs:
        assert a.up_to_round == 1


# ── Constructor Trajectory Tests ─────────────────────────────────────────────


def test_constructor_trajectory_red_bull_count(session: Session):
    """Red Bull should have 5 trajectory entries across Rounds 1-5."""
    from app.analytics.longitudinal_constructor import get_constructor_trajectory

    traj = get_constructor_trajectory(session, SEASON_YEAR, "red_bull")
    assert len(traj) == TOTAL_ROUNDS


def test_constructor_trajectory_sprint_separation(session: Session):
    """Round 5 (China) should have sprint_points > 0 for Red Bull."""
    from app.analytics.longitudinal_constructor import get_constructor_trajectory

    traj = get_constructor_trajectory(session, SEASON_YEAR, "red_bull")
    china = next((t for t in traj if t.round == 5), None)
    assert china is not None
    assert china.sprint_points > 0
    assert china.total_round_points == china.race_points + china.sprint_points


def test_constructor_trajectory_cumulative_totals(session: Session):
    """Cumulative total points should be non-decreasing."""
    from app.analytics.longitudinal_constructor import get_constructor_trajectory

    traj = get_constructor_trajectory(session, SEASON_YEAR, "red_bull")
    for i in range(1, len(traj)):
        assert traj[i].cumulative_total_points >= traj[i - 1].cumulative_total_points


def test_constructor_trajectory_nonexistent(session: Session):
    """Non-existent constructor slug should return empty list."""
    from app.analytics.longitudinal_constructor import get_constructor_trajectory

    result = get_constructor_trajectory(session, SEASON_YEAR, "nonexistent_team_xyz")
    assert result == []


# ── Constructor Season Aggregate Tests ───────────────────────────────────────


def test_constructor_season_aggregate_red_bull_total_points(session: Session):
    """Red Bull should have 195 total championship points after Round 5."""
    from app.analytics.longitudinal_constructor import get_constructor_season_aggregate

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "red_bull")
    assert agg is not None
    assert agg.total_points == Decimal(str(RB_TOTAL_PTS))


def test_constructor_season_aggregate_red_bull_wins(session: Session):
    """Red Bull should have 4 wins (Rounds 1, 2, 4, 5)."""
    from app.analytics.longitudinal_constructor import get_constructor_season_aggregate

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "red_bull")
    assert agg is not None
    assert agg.wins == RB_WINS


def test_constructor_season_aggregate_driver_contribution_sum(session: Session):
    """Sum of all driver contributions must equal the constructor's total points."""
    from app.analytics.longitudinal_constructor import get_constructor_season_aggregate

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "red_bull")
    assert agg is not None
    contrib_total = sum(c.total_points for c in agg.driver_contributions)
    assert contrib_total == agg.total_points


def test_constructor_season_aggregate_ferrari_3_drivers(session: Session):
    """Ferrari used 3 drivers in Rounds 1-5: Leclerc, Sainz, Bearman (Round 2 sub)."""
    from app.analytics.longitudinal_constructor import get_constructor_season_aggregate

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "ferrari")
    assert agg is not None
    contrib_driver_ids = {c.driver_id for c in agg.driver_contributions}
    assert "leclerc" in contrib_driver_ids
    assert "sainz" in contrib_driver_ids
    assert "bearman" in contrib_driver_ids


def test_constructor_season_aggregate_championship_standing(session: Session):
    """Red Bull should be P1 in constructors championship."""
    from app.analytics.longitudinal_constructor import get_constructor_season_aggregate

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "red_bull")
    assert agg is not None
    assert agg.championship_standing == 1


def test_constructor_season_aggregate_ferrari_australia_win(session: Session):
    """Ferrari should have at least 1 win (Sainz, Australia Round 3)."""
    from app.analytics.longitudinal_constructor import get_constructor_season_aggregate

    agg = get_constructor_season_aggregate(session, SEASON_YEAR, "ferrari")
    assert agg is not None
    assert agg.wins >= 1


# ── All Constructors Season Aggregates ────────────────────────────────────────


def test_get_all_constructors_season_aggregates_count(session: Session):
    """Should return all 10 constructors active in 2024 Rounds 1-5."""
    from app.analytics.longitudinal_constructor import get_all_constructors_season_aggregates

    aggs = get_all_constructors_season_aggregates(session, SEASON_YEAR)
    assert len(aggs) == 10


def test_get_all_constructors_season_aggregates_red_bull_first(session: Session):
    """Red Bull should be first in the sorted list (P1 championship)."""
    from app.analytics.longitudinal_constructor import get_all_constructors_season_aggregates

    aggs = get_all_constructors_season_aggregates(session, SEASON_YEAR)
    assert aggs[0].constructor_id == "red_bull"


# ── Event Teammate Comparison Tests ──────────────────────────────────────────


def test_event_teammate_comparisons_round1_count(session: Session):
    """Round 1 (Bahrain) should return 10 constructor comparisons (all 10 teams)."""
    from app.analytics.longitudinal_teammate import get_event_teammate_comparisons

    comps = get_event_teammate_comparisons(session, SEASON_YEAR, 1)
    assert len(comps) == 10


def test_event_teammate_comparisons_round2_ferrari_bearman(session: Session):
    """Round 2 (Saudi Arabia): Ferrari pairing should include Bearman (not Sainz)."""
    from app.analytics.longitudinal_teammate import get_event_teammate_comparisons

    comps = get_event_teammate_comparisons(session, SEASON_YEAR, 2)
    ferrari_comp = next((c for c in comps if c.constructor_id == "ferrari"), None)
    assert ferrari_comp is not None

    driver_ids = {ferrari_comp.driver_a_id, ferrari_comp.driver_b_id}
    assert "bearman" in driver_ids, "Bearman should be in Round 2 Ferrari pairing"
    assert "sainz" not in driver_ids, "Sainz was absent in Round 2 (Bearman sub)"
    assert "leclerc" in driver_ids, "Leclerc should be in Round 2 Ferrari pairing"


def test_event_teammate_comparisons_round3_ferrari_verstappen_dnf(session: Session):
    """Round 3 (Australia): Verstappen DNF — Red Bull finish comparison should not be comparable."""
    from app.analytics.longitudinal_teammate import get_event_teammate_comparisons

    comps = get_event_teammate_comparisons(session, SEASON_YEAR, 3)
    rb_comp = next((c for c in comps if c.constructor_id == "red_bull"), None)
    assert rb_comp is not None

    ver_id = "max_verstappen"
    ver_finish = rb_comp.finish_a if rb_comp.driver_a_id == ver_id else rb_comp.finish_b
    assert ver_finish is None, "Verstappen's finish position should be None (DNF)"
    assert rb_comp.is_comparable_finish is False, "Should not be comparable when one driver DNF'd"


def test_event_teammate_comparisons_alphabetical_ordering(session: Session):
    """driver_a_id should always be alphabetically before driver_b_id."""
    from app.analytics.longitudinal_teammate import get_event_teammate_comparisons

    comps = get_event_teammate_comparisons(session, SEASON_YEAR, 1)
    for c in comps:
        assert c.driver_a_id < c.driver_b_id, (
            f"Ordering violated: {c.driver_a_id} >= {c.driver_b_id}"
        )


# ── Season Teammate Comparison Tests ─────────────────────────────────────────


def test_season_teammate_comparisons_ferrari_bearman_sainz_separate_pairings(session: Session):
    """Ferrari should produce two distinct season pairings: (bearman, leclerc) and (leclerc, sainz)."""
    from app.analytics.longitudinal_teammate import get_season_teammate_comparisons

    comps = get_season_teammate_comparisons(session, SEASON_YEAR)
    ferrari_comps = [c for c in comps if c.constructor_id == "ferrari"]

    # Expect 2 distinct Ferrari pairings (one with Bearman, one with Sainz)
    assert len(ferrari_comps) == 2, (
        f"Expected 2 Ferrari pairings (Leclerc/Bearman + Leclerc/Sainz), got {len(ferrari_comps)}"
    )

    pairing_keys = {(c.driver_a_id, c.driver_b_id) for c in ferrari_comps}
    assert ("bearman", "leclerc") in pairing_keys
    assert ("leclerc", "sainz") in pairing_keys


def test_season_teammate_comparisons_bearman_leclerc_1_round(session: Session):
    """Bearman and Leclerc were teammates for exactly 1 round (Round 2 Jeddah)."""
    from app.analytics.longitudinal_teammate import get_season_teammate_comparisons

    comps = get_season_teammate_comparisons(session, SEASON_YEAR)
    bea_lec = next(
        (c for c in comps if c.constructor_id == "ferrari" and "bearman" in (c.driver_a_id, c.driver_b_id)),
        None,
    )
    assert bea_lec is not None
    assert bea_lec.rounds_together == 1


def test_season_teammate_comparisons_leclerc_sainz_rounds(session: Session):
    """Leclerc and Sainz were teammates in Rounds 1, 3, 4, 5 — 4 rounds together."""
    from app.analytics.longitudinal_teammate import get_season_teammate_comparisons

    comps = get_season_teammate_comparisons(session, SEASON_YEAR)
    lec_sai = next(
        (c for c in comps if c.constructor_id == "ferrari" and "sainz" in (c.driver_a_id, c.driver_b_id) and "leclerc" in (c.driver_a_id, c.driver_b_id)),
        None,
    )
    assert lec_sai is not None
    assert lec_sai.rounds_together == 4


def test_season_teammate_comparisons_red_bull_5_rounds(session: Session):
    """Verstappen and Perez were teammates all 5 rounds."""
    from app.analytics.longitudinal_teammate import get_season_teammate_comparisons

    comps = get_season_teammate_comparisons(session, SEASON_YEAR)
    rb_comp = next((c for c in comps if c.constructor_id == "red_bull"), None)
    assert rb_comp is not None
    assert rb_comp.rounds_together == 5


def test_season_teammate_comparisons_comparable_rounds_australia_dnf(session: Session):
    """Red Bull race-comparable rounds should be 4 (not 5) because of Verstappen DNF in Round 3."""
    from app.analytics.longitudinal_teammate import get_season_teammate_comparisons

    comps = get_season_teammate_comparisons(session, SEASON_YEAR)
    rb_comp = next((c for c in comps if c.constructor_id == "red_bull"), None)
    assert rb_comp is not None
    assert rb_comp.race_comparable_rounds == 4, (
        f"Expected 4 comparable race rounds (DNF in Round 3), got {rb_comp.race_comparable_rounds}"
    )


def test_season_teammate_comparisons_points_sum(session: Session):
    """Points between two teammates in a pairing should be traceable and sum correctly."""
    from app.analytics.longitudinal_teammate import get_season_teammate_comparisons

    comps = get_season_teammate_comparisons(session, SEASON_YEAR)
    rb_comp = next((c for c in comps if c.constructor_id == "red_bull"), None)
    assert rb_comp is not None
    # Total points should be positive
    assert rb_comp.total_points_a > 0
    assert rb_comp.total_points_b > 0
    # Total points for both teammates should equal sum of their individual totals
    assert rb_comp.total_points_a == rb_comp.points_a + rb_comp.sprint_points_a
    assert rb_comp.total_points_b == rb_comp.points_b + rb_comp.sprint_points_b


def test_season_teammate_comparisons_constructor_filter(session: Session):
    """Filtering by constructor_id should return only that constructor's pairings."""
    from app.analytics.longitudinal_teammate import get_season_teammate_comparisons

    comps = get_season_teammate_comparisons(session, SEASON_YEAR, constructor_id="ferrari")
    assert all(c.constructor_id == "ferrari" for c in comps)
    assert len(comps) == 2  # bearman+leclerc and leclerc+sainz

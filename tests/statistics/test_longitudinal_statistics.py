"""Unit tests for longitudinal statistical analysis and evidence generation.

All tests verify pure mathematical and statistical properties without database access.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.analytics.types import (
    DriverTrajectoryItem,
    TeammateEventComparison,
)
from app.statistics.longitudinal import (
    compute_driver_form_summary,
    compute_driver_longitudinal_stats,
    compute_driver_points_stats,
    compute_longitudinal_evidence_metadata,
    compute_longitudinal_teammate_h2h_stats,
    compute_rolling_window_stats,
)
from app.statistics.types import EvidenceStrength


# ── Helper to construct test DriverTrajectoryItem objects ──────────────────────

def _make_trajectory_item(
    round_num: int,
    grid: int | None = 1,
    finish: int | None = 1,
    race_pts: str = "25.0",
    sprint_pts: str = "0.0",
    status: str = "Finished",
    pos_text: str = "1",
) -> DriverTrajectoryItem:
    r_pts = Decimal(race_pts)
    s_pts = Decimal(sprint_pts)
    return DriverTrajectoryItem(
        season_year=2024,
        round=round_num,
        race_name=f"Race {round_num}",
        circuit_name=f"Circuit {round_num}",
        race_date=date(2024, 3, min(28, round_num * 5)),
        constructor_id="red_bull",
        constructor_name="Red Bull",
        grid_position=grid,
        finish_position=finish,
        position_text=pos_text,
        status=status,
        is_classified=(finish is not None),
        race_points=r_pts,
        sprint_points=s_pts,
        total_round_points=r_pts + s_pts,
        cumulative_race_points=r_pts,
        cumulative_sprint_points=s_pts,
        cumulative_total_points=r_pts + s_pts,
        championship_standing_position=1,
        pit_stop_count=2,
        fastest_lap_rank=1,
    )


# ── Points Statistics Tests ───────────────────────────────────────────────────

class TestDriverPointsStats:
    def test_empty_trajectory(self):
        pts = compute_driver_points_stats([])
        assert pts.total_championship_points == Decimal("0.0")
        assert pts.total_race_points == Decimal("0.0")
        assert pts.total_sprint_points == Decimal("0.0")
        assert pts.grand_prix_starts == 0
        assert pts.rounds_entered == 0
        assert pts.points_per_gp_start is None
        assert pts.points_per_gp_entry is None
        assert pts.points_per_round_total is None
        assert pts.evidence.is_available is False
        assert pts.evidence.evidence_strength == EvidenceStrength.INSUFFICIENT

    def test_single_round_points(self):
        item = _make_trajectory_item(1, race_pts="25.0", sprint_pts="0.0")
        pts = compute_driver_points_stats([item])
        assert pts.total_championship_points == Decimal("25.0")
        assert pts.total_race_points == Decimal("25.0")
        assert pts.total_sprint_points == Decimal("0.0")
        assert pts.grand_prix_starts == 1
        assert pts.rounds_entered == 1
        assert pts.points_per_gp_start == 25.0
        assert pts.points_per_gp_entry == 25.0
        assert pts.points_per_round_total == 25.0
        assert pts.evidence.valid_observations == 1
        assert pts.evidence.evidence_strength == EvidenceStrength.LOW

    def test_sprint_points_separation(self):
        # Round 1: GP only (25 pts)
        # Round 2: Sprint weekend (8 sprint pts + 25 GP pts = 33 round pts)
        t1 = _make_trajectory_item(1, race_pts="25.0", sprint_pts="0.0")
        t2 = _make_trajectory_item(2, race_pts="25.0", sprint_pts="8.0")

        pts = compute_driver_points_stats([t1, t2])
        assert pts.total_race_points == Decimal("50.0")
        assert pts.total_sprint_points == Decimal("8.0")
        assert pts.total_championship_points == Decimal("58.0")
        assert pts.grand_prix_starts == 2
        assert pts.rounds_entered == 2
        assert pts.points_per_gp_start == 25.0  # 50 race pts / 2 starts
        assert pts.points_per_gp_entry == 25.0
        assert pts.points_per_round_total == 29.0  # 58 total pts / 2 rounds

    def test_dns_exclusion_from_gp_starts(self):
        # Round 1: normal start (18 pts)
        # Round 2: DNS (0 pts)
        t1 = _make_trajectory_item(1, race_pts="18.0", sprint_pts="0.0")
        t2 = _make_trajectory_item(2, grid=None, finish=None, race_pts="0.0", status="Did not start", pos_text="DNS")

        pts = compute_driver_points_stats([t1, t2])
        assert pts.rounds_entered == 2
        assert pts.grand_prix_starts == 1  # DNS excluded from starts
        assert pts.points_per_gp_start == 18.0  # 18.0 / 1 start
        assert pts.points_per_gp_entry == 9.0  # 18.0 / 2 rounds entered
        assert pts.points_per_round_total == 9.0


# ── Driver Longitudinal Profile Tests ─────────────────────────────────────────

class TestDriverLongitudinalStats:
    def test_empty_trajectory(self):
        stats = compute_driver_longitudinal_stats([])
        assert stats.finish_position.sample_size == 0
        assert stats.grid_position.sample_size == 0
        assert stats.position_change.stats.sample_size == 0
        assert stats.points.rounds_entered == 0
        assert stats.evidence.is_available is False

    def test_dnf_handling_in_finish_and_position_change(self):
        # Round 1: Grid 1, Finish 1 (change 0)
        # Round 2: Grid 1, Finish 1 (change 0)
        # Round 3: Grid 1, DNF / Finish None (status="Retired", change None)
        # Round 4: Grid 1, Finish 1 (change 0)
        # Round 5: Grid 1, Finish 1 (change 0)
        traj = [
            _make_trajectory_item(1, grid=1, finish=1, race_pts="25.0"),
            _make_trajectory_item(2, grid=1, finish=1, race_pts="25.0"),
            _make_trajectory_item(3, grid=1, finish=None, race_pts="0.0", status="Retired", pos_text="R"),
            _make_trajectory_item(4, grid=1, finish=1, race_pts="25.0"),
            _make_trajectory_item(5, grid=1, finish=1, race_pts="25.0"),
        ]

        stats = compute_driver_longitudinal_stats(traj)

        # Finish position: 4 valid, 1 excluded (DNF)
        assert stats.finish_position.sample_size == 4
        assert stats.finish_position.mean == 1.0
        assert stats.finish_position.minimum == 1.0
        assert stats.finish_position.maximum == 1.0
        assert stats.finish_position.stddev == 0.0

        # Grid position: all 5 had grid=1
        assert stats.grid_position.sample_size == 5
        assert stats.grid_position.mean == 1.0

        # Position change: 4 valid, 1 excluded due to DNF
        assert stats.position_change.quality.total_observations == 5
        assert stats.position_change.quality.valid_observations == 4
        assert stats.position_change.quality.excluded_observations == 1
        assert stats.position_change.distribution.zero_count == 4
        assert stats.position_change.distribution.zero_rate == 1.0

        # Evidence strength with n=5 rounds
        assert stats.evidence.evidence_strength == EvidenceStrength.HIGH
        assert stats.evidence.valid_observations == 5

    def test_pit_lane_start_exclusion(self):
        # Round 1: Pit lane start (grid=0, finish=10 -> change cannot be calculated)
        # Round 2: Grid 16, finish 10 (change +6)
        traj = [
            _make_trajectory_item(1, grid=0, finish=10),
            _make_trajectory_item(2, grid=16, finish=10),
        ]
        stats = compute_driver_longitudinal_stats(traj)

        # Grid position: grid=0 excluded
        assert stats.grid_position.sample_size == 1
        assert stats.grid_position.mean == 16.0

        # Position change: pit lane start excluded
        assert stats.position_change.quality.valid_observations == 1
        assert stats.position_change.quality.excluded_observations == 1
        assert stats.position_change.stats.mean == 6.0
        assert stats.position_change.distribution.positive_count == 1

    def test_position_change_distributions(self):
        # Round 1: Grid 10, Finish 5 (+5 gained)
        # Round 2: Grid 2, Finish 6 (-4 lost)
        # Round 3: Grid 3, Finish 3 (0 maintained)
        traj = [
            _make_trajectory_item(1, grid=10, finish=5),
            _make_trajectory_item(2, grid=2, finish=6),
            _make_trajectory_item(3, grid=3, finish=3),
        ]
        stats = compute_driver_longitudinal_stats(traj)
        dist = stats.position_change.distribution

        assert dist.sample_size == 3
        assert dist.positive_count == 1
        assert dist.negative_count == 1
        assert dist.zero_count == 1
        assert dist.positive_rate == pytest.approx(1 / 3)
        assert dist.negative_rate == pytest.approx(1 / 3)
        assert dist.zero_rate == pytest.approx(1 / 3)


# ── Rolling Window Statistics Tests ──────────────────────────────────────────

class TestRollingWindowStats:
    def test_empty_observations(self):
        res = compute_rolling_window_stats([], window_size=3)
        assert res == []

    def test_fewer_observations_than_window(self):
        data = [(1, 10.0), (2, 20.0)]
        res = compute_rolling_window_stats(data, window_size=3)
        assert len(res) == 2

        # Round 1 (window size 1 available): mean 10.0
        assert res[0].round == 1
        assert res[0].valid_observations == 1
        assert res[0].mean == 10.0
        assert res[0].stddev is None
        assert res[0].rounds_included == [1]

        # Round 2 (window size 2 available): mean 15.0
        assert res[1].round == 2
        assert res[1].valid_observations == 2
        assert res[1].mean == 15.0
        assert res[1].rounds_included == [1, 2]

    def test_exact_and_overflow_window(self):
        # 5 rounds with window=3
        data = [(1, 1.0), (2, 2.0), (3, 3.0), (4, 4.0), (5, 5.0)]
        res = compute_rolling_window_stats(data, window_size=3)
        assert len(res) == 5

        # Round 3: window [1, 2, 3] -> mean 2.0
        assert res[2].round == 3
        assert res[2].rounds_included == [1, 2, 3]
        assert res[2].mean == 2.0

        # Round 4: window [2, 3, 4] -> mean 3.0
        assert res[3].round == 4
        assert res[3].rounds_included == [2, 3, 4]
        assert res[3].mean == 3.0

        # Round 5: window [3, 4, 5] -> mean 4.0
        assert res[4].round == 5
        assert res[4].rounds_included == [3, 4, 5]
        assert res[4].mean == 4.0

    def test_missing_values_in_window(self):
        # Round 3 has None (e.g. DNF)
        data = [(1, 1.0), (2, 2.0), (3, None), (4, 4.0)]
        res = compute_rolling_window_stats(data, window_size=3)

        # Round 3: window includes [1, 2, 3], valid = [1.0, 2.0] -> mean 1.5
        assert res[2].round == 3
        assert res[2].valid_observations == 2
        assert res[2].mean == 1.5

        # Round 4: window includes [2, 3, 4], valid = [2.0, 4.0] -> mean 3.0
        assert res[3].round == 4
        assert res[3].valid_observations == 2
        assert res[3].mean == 3.0


# ── Driver Form Summary Tests ────────────────────────────────────────────────

class TestDriverFormSummary:
    def test_empty_form_summary(self):
        form = compute_driver_form_summary([])
        assert form.rolling_windows == []
        assert form.race_to_race_deltas == []
        assert form.evidence.is_available is False

    def test_race_to_race_deltas(self):
        # Round 1: finish 1, pts 25
        # Round 2: finish 3, pts 15 (finish delta +2, pts delta -10)
        # Round 3: finish None (DNF), pts 0 (finish delta None, pts delta -15)
        # Round 4: finish 1, pts 25 (finish delta None, pts delta +25)
        traj = [
            _make_trajectory_item(1, finish=1, race_pts="25.0"),
            _make_trajectory_item(2, finish=3, race_pts="15.0"),
            _make_trajectory_item(3, finish=None, race_pts="0.0", status="Retired", pos_text="R"),
            _make_trajectory_item(4, finish=1, race_pts="25.0"),
        ]
        form = compute_driver_form_summary(traj, window_size=3)

        deltas = form.race_to_race_deltas
        # 3 round transitions * 2 metrics = 6 deltas
        f_deltas = [d for d in deltas if d.metric_name == "finish_position"]
        p_deltas = [d for d in deltas if d.metric_name == "points"]

        assert len(f_deltas) == 3
        assert f_deltas[0].delta == 2.0   # Round 1 -> 2: P1 to P3
        assert f_deltas[1].delta is None  # Round 2 -> 3: P3 to DNF
        assert f_deltas[2].delta is None  # Round 3 -> 4: DNF to P1

        assert len(p_deltas) == 3
        assert p_deltas[0].delta == -10.0  # 25 -> 15
        assert p_deltas[1].delta == -15.0  # 15 -> 0
        assert p_deltas[2].delta == 25.0   # 0 -> 25


# ── Teammate Head-to-Head Tests ──────────────────────────────────────────────

class TestTeammateH2HStatistics:
    def test_empty_comparisons(self):
        res = compute_longitudinal_teammate_h2h_stats([])
        assert res == {}

    def test_equal_and_different_qualifying_deltas(self):
        # Round 1: drv_a -300ms faster
        # Round 2: drv_b -200ms faster (drv_a is +200ms)
        # Round 3: equal times (0ms delta)
        c1 = TeammateEventComparison(
            season_year=2024, round=1, race_name="R1", constructor_id="red_bull", constructor_name="Red Bull",
            driver_a_id="max_verstappen", driver_a_name="Max", driver_b_id="perez", driver_b_name="Checo",
            qualifying_a_pos=1, qualifying_b_pos=2, qualifying_delta_millis=-300,
            grid_a=1, grid_b=2, finish_a=1, finish_b=2, status_a="Finished", status_b="Finished",
            points_a=Decimal("25.0"), points_b=Decimal("18.0"), sprint_points_a=Decimal("0.0"), sprint_points_b=Decimal("0.0"),
            is_comparable_qualifying=True, is_comparable_finish=True,
            ahead_in_qualifying="max_verstappen", ahead_in_race="max_verstappen",
        )
        c2 = TeammateEventComparison(
            season_year=2024, round=2, race_name="R2", constructor_id="red_bull", constructor_name="Red Bull",
            driver_a_id="max_verstappen", driver_a_name="Max", driver_b_id="perez", driver_b_name="Checo",
            qualifying_a_pos=3, qualifying_b_pos=1, qualifying_delta_millis=200,
            grid_a=3, grid_b=1, finish_a=2, finish_b=1, status_a="Finished", status_b="Finished",
            points_a=Decimal("18.0"), points_b=Decimal("25.0"), sprint_points_a=Decimal("0.0"), sprint_points_b=Decimal("0.0"),
            is_comparable_qualifying=True, is_comparable_finish=True,
            ahead_in_qualifying="perez", ahead_in_race="perez",
        )
        c3 = TeammateEventComparison(
            season_year=2024, round=3, race_name="R3", constructor_id="red_bull", constructor_name="Red Bull",
            driver_a_id="max_verstappen", driver_a_name="Max", driver_b_id="perez", driver_b_name="Checo",
            qualifying_a_pos=1, qualifying_b_pos=1, qualifying_delta_millis=0,
            grid_a=1, grid_b=2, finish_a=1, finish_b=2, status_a="Finished", status_b="Finished",
            points_a=Decimal("25.0"), points_b=Decimal("18.0"), sprint_points_a=Decimal("0.0"), sprint_points_b=Decimal("0.0"),
            is_comparable_qualifying=True, is_comparable_finish=True,
            ahead_in_qualifying=None, ahead_in_race="max_verstappen",
        )

        res = compute_longitudinal_teammate_h2h_stats([c1, c2, c3])
        key = ("red_bull", "max_verstappen", "perez")
        assert key in res
        h2h = res[key]

        assert h2h.rounds_together == 3
        # Qualifying
        assert h2h.qualifying_wins_a == 1
        assert h2h.qualifying_wins_b == 1
        assert h2h.qualifying_comparable_rounds == 3
        assert h2h.qualifying_win_rate_a == pytest.approx(1 / 3, rel=1e-3)
        assert h2h.qualifying_win_rate_b == pytest.approx(1 / 3, rel=1e-3)
        assert h2h.qualifying_delta_stats.mean == pytest.approx((-300 + 200 + 0) / 3, rel=1e-3)

        # Race
        assert h2h.race_wins_a == 2
        assert h2h.race_wins_b == 1
        assert h2h.race_win_rate_a == pytest.approx(2 / 3, rel=1e-3)

    def test_driver_substitution_isolation(self):
        # Round 1: Ferrari Leclerc vs Sainz
        # Round 2: Ferrari Bearman vs Leclerc (Bearman substituted)
        # Round 3: Ferrari Leclerc vs Sainz
        c1 = TeammateEventComparison(
            season_year=2024, round=1, race_name="R1", constructor_id="ferrari", constructor_name="Ferrari",
            driver_a_id="leclerc", driver_a_name="Leclerc", driver_b_id="sainz", driver_b_name="Sainz",
            qualifying_a_pos=2, qualifying_b_pos=4, qualifying_delta_millis=-100,
            grid_a=2, grid_b=4, finish_a=4, finish_b=3, status_a="Finished", status_b="Finished",
            points_a=Decimal("12.0"), points_b=Decimal("15.0"), sprint_points_a=Decimal("0.0"), sprint_points_b=Decimal("0.0"),
            is_comparable_qualifying=True, is_comparable_finish=True,
            ahead_in_qualifying="leclerc", ahead_in_race="sainz",
        )
        c2 = TeammateEventComparison(
            season_year=2024, round=2, race_name="R2", constructor_id="ferrari", constructor_name="Ferrari",
            driver_a_id="bearman", driver_a_name="Bearman", driver_b_id="leclerc", driver_b_name="Leclerc",
            qualifying_a_pos=11, qualifying_b_pos=2, qualifying_delta_millis=550,
            grid_a=11, grid_b=2, finish_a=7, finish_b=3, status_a="Finished", status_b="Finished",
            points_a=Decimal("6.0"), points_b=Decimal("15.0"), sprint_points_a=Decimal("0.0"), sprint_points_b=Decimal("0.0"),
            is_comparable_qualifying=True, is_comparable_finish=True,
            ahead_in_qualifying="leclerc", ahead_in_race="leclerc",
        )
        c3 = TeammateEventComparison(
            season_year=2024, round=3, race_name="R3", constructor_id="ferrari", constructor_name="Ferrari",
            driver_a_id="leclerc", driver_a_name="Leclerc", driver_b_id="sainz", driver_b_name="Sainz",
            qualifying_a_pos=4, qualifying_b_pos=2, qualifying_delta_millis=150,
            grid_a=4, grid_b=2, finish_a=2, finish_b=1, status_a="Finished", status_b="Finished",
            points_a=Decimal("19.0"), points_b=Decimal("25.0"), sprint_points_a=Decimal("0.0"), sprint_points_b=Decimal("0.0"),
            is_comparable_qualifying=True, is_comparable_finish=True,
            ahead_in_qualifying="sainz", ahead_in_race="sainz",
        )

        res = compute_longitudinal_teammate_h2h_stats([c1, c2, c3])

        # Must partition into 2 distinct pairings
        assert len(res) == 2
        assert ("ferrari", "leclerc", "sainz") in res
        assert ("ferrari", "bearman", "leclerc") in res

        lec_sai = res[("ferrari", "leclerc", "sainz")]
        assert lec_sai.rounds_together == 2
        assert lec_sai.qualifying_wins_a == 1  # Leclerc
        assert lec_sai.qualifying_wins_b == 1  # Sainz
        assert lec_sai.race_wins_a == 0        # Leclerc
        assert lec_sai.race_wins_b == 2        # Sainz

        bea_lec = res[("ferrari", "bearman", "leclerc")]
        assert bea_lec.rounds_together == 1
        assert bea_lec.qualifying_wins_a == 0
        assert bea_lec.qualifying_wins_b == 1  # Leclerc
        assert bea_lec.race_wins_a == 0
        assert bea_lec.race_wins_b == 1        # Leclerc

    def test_dnf_non_comparable_race_finish(self):
        # Round 1: Normal finish
        # Round 2: driver_a DNF -> not comparable finish
        c1 = TeammateEventComparison(
            season_year=2024, round=1, race_name="R1", constructor_id="red_bull", constructor_name="Red Bull",
            driver_a_id="max_verstappen", driver_a_name="Max", driver_b_id="perez", driver_b_name="Checo",
            qualifying_a_pos=1, qualifying_b_pos=5, qualifying_delta_millis=-400,
            grid_a=1, grid_b=5, finish_a=1, finish_b=2, status_a="Finished", status_b="Finished",
            points_a=Decimal("25.0"), points_b=Decimal("18.0"), sprint_points_a=Decimal("0.0"), sprint_points_b=Decimal("0.0"),
            is_comparable_qualifying=True, is_comparable_finish=True,
            ahead_in_qualifying="max_verstappen", ahead_in_race="max_verstappen",
        )
        c2 = TeammateEventComparison(
            season_year=2024, round=2, race_name="R2", constructor_id="red_bull", constructor_name="Red Bull",
            driver_a_id="max_verstappen", driver_a_name="Max", driver_b_id="perez", driver_b_name="Checo",
            qualifying_a_pos=1, qualifying_b_pos=3, qualifying_delta_millis=-300,
            grid_a=1, grid_b=3, finish_a=None, finish_b=5, status_a="Retired", status_b="Finished",
            points_a=Decimal("0.0"), points_b=Decimal("10.0"), sprint_points_a=Decimal("0.0"), sprint_points_b=Decimal("0.0"),
            is_comparable_qualifying=True, is_comparable_finish=False,
            ahead_in_qualifying="max_verstappen", ahead_in_race=None,
        )

        res = compute_longitudinal_teammate_h2h_stats([c1, c2])
        h2h = res[("red_bull", "max_verstappen", "perez")]

        assert h2h.rounds_together == 2
        assert h2h.qualifying_comparable_rounds == 2
        assert h2h.qualifying_wins_a == 2
        assert h2h.race_comparable_rounds == 1  # Round 2 excluded from race finish H2H
        assert h2h.race_wins_a == 1
        assert h2h.race_wins_b == 0
        assert h2h.race_win_rate_a == 1.0
        assert h2h.race_win_rate_b == 0.0

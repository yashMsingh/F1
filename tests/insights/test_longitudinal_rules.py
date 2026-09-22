"""Unit tests for Phase 3D longitudinal deterministic insight rules.

Tests cover:
- Positive rule cases
- Negative rule cases
- Exact threshold boundaries
- Insufficient sample sizes (< min_sample_size)
- Evidence strength classifications (INSUFFICIENT, LOW, MODERATE, HIGH)
- DNF exclusions and None values
- Sprint vs Grand Prix points separation
- Teammate substitutions and pair isolation
- Deterministic insight IDs and deduplication
- Complete traceability audit trails
- Absence of false positives
"""

from decimal import Decimal
from datetime import date
import pytest

from app.analytics.types import ConstructorTrajectoryItem
from app.insights.engine import InsightEngine
from app.insights.evaluators.longitudinal import (
    evaluate_constructor_longitudinal_insights,
    evaluate_driver_longitudinal_insights,
    evaluate_longitudinal_finish_consistency,
    evaluate_longitudinal_points_per_round,
    evaluate_longitudinal_points_per_start,
    evaluate_longitudinal_position_change_pattern,
    evaluate_longitudinal_qualifying_consistency,
    evaluate_longitudinal_recent_form,
    evaluate_longitudinal_teammate_h2h,
)
from app.insights.rules import (
    RULE_LONGITUDINAL_CONSTRUCTOR_TRAJECTORY,
    RULE_LONGITUDINAL_FINISH_CONSISTENCY,
    RULE_LONGITUDINAL_POINTS_PER_ROUND,
    RULE_LONGITUDINAL_POINTS_PER_START,
    RULE_LONGITUDINAL_POSITION_GAIN_PATTERN,
    RULE_LONGITUDINAL_POSITION_LOSS_PATTERN,
    RULE_LONGITUDINAL_QUALIFYING_CONSISTENCY,
    RULE_LONGITUDINAL_RECENT_FORM,
    RULE_LONGITUDINAL_TEAMMATE_POINTS_H2H,
    RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H,
    RULE_LONGITUDINAL_TEAMMATE_RACE_H2H,
)
from app.insights.types import Direction, EvidenceStrength, InsightCategory
from app.statistics.types import (
    ConsistencyStats,
    DescriptiveStats,
    DriverFormSummary,
    DriverLongitudinalStats,
    LongitudinalEvidenceMetadata,
    PointsStats,
    PositionChangeDistribution,
    PositionChangeStats,
    QualityMetadata,
    RollingWindowStats,
    TeammateH2HStatistics,
)


# ─── Helper Factories ─────────────────────────────────────────────────────────

def _make_driver_stats(
    driver_id: str = "verstappen",
    season_year: int = 2024,
    up_to_round: int = 5,
    rounds_included: list[int] = None,
    grid_sample_size: int = 5,
    grid_mean: float = 1.0,
    grid_stddev: float = 0.0,
    finish_sample_size: int = 4,
    finish_mean: float = 1.0,
    finish_stddev: float = 0.0,
    pos_change_valid: int = 4,
    pos_change_mean: float = 0.0,
    gp_starts: int = 5,
    rounds_entered: int = 5,
    total_race_points: str = "102.0",
    total_sprint_points: str = "8.0",
    pp_gp_start: float = 20.4,
    pp_round_total: float = 22.0,
) -> DriverLongitudinalStats:
    rounds_inc = rounds_included or list(range(1, up_to_round + 1))
    empty_desc = DescriptiveStats(sample_size=0, mean=None, stddev=None, median=None, minimum=None, maximum=None, iqr=None)
    empty_cons = ConsistencyStats(stats=empty_desc, range=None, iqr=None, coefficient_of_variation=None)

    grid_desc = DescriptiveStats(sample_size=grid_sample_size, mean=grid_mean, stddev=grid_stddev, median=grid_mean, minimum=grid_mean, maximum=grid_mean, iqr=0.0)
    grid_cons = ConsistencyStats(stats=grid_desc, range=0.0, iqr=0.0, coefficient_of_variation=0.0)

    finish_desc = DescriptiveStats(sample_size=finish_sample_size, mean=finish_mean, stddev=finish_stddev, median=finish_mean, minimum=finish_mean, maximum=finish_mean, iqr=0.0)
    finish_cons = ConsistencyStats(stats=finish_desc, range=0.0, iqr=0.0, coefficient_of_variation=0.0)

    dist = PositionChangeDistribution(
        sample_size=pos_change_valid,
        positive_count=pos_change_valid if pos_change_mean > 0 else 0,
        negative_count=pos_change_valid if pos_change_mean < 0 else 0,
        zero_count=pos_change_valid if pos_change_mean == 0 else 0,
        positive_rate=1.0 if pos_change_mean > 0 else 0.0,
        negative_rate=1.0 if pos_change_mean < 0 else 0.0,
        zero_rate=1.0 if pos_change_mean == 0 else 0.0,
    )
    pos_change_stats = PositionChangeStats(
        stats=DescriptiveStats(sample_size=pos_change_valid, mean=pos_change_mean, stddev=0.0, median=pos_change_mean, minimum=pos_change_mean, maximum=pos_change_mean, iqr=0.0),
        distribution=dist,
        quality=QualityMetadata(total_observations=len(rounds_inc), valid_observations=pos_change_valid, excluded_observations=len(rounds_inc) - pos_change_valid),
    )

    tot_race = Decimal(total_race_points)
    tot_sprint = Decimal(total_sprint_points)
    pts_stats = PointsStats(
        total_championship_points=tot_race + tot_sprint,
        total_race_points=tot_race,
        total_sprint_points=tot_sprint,
        grand_prix_starts=gp_starts,
        rounds_entered=rounds_entered,
        points_per_gp_start=pp_gp_start,
        points_per_gp_entry=pp_gp_start,
        points_per_round_total=pp_round_total,
        race_points_stats=empty_desc,
        total_points_stats=empty_desc,
        evidence=LongitudinalEvidenceMetadata(
            total_races=len(rounds_inc),
            valid_observations=gp_starts,
            excluded_observations=len(rounds_inc) - gp_starts,
            min_required_observations=1,
            is_available=True,
            evidence_strength=EvidenceStrength.HIGH,
            rounds_included=rounds_inc,
        ),
    )

    return DriverLongitudinalStats(
        driver_id=driver_id,
        season_year=season_year,
        up_to_round=up_to_round,
        finish_position=finish_desc,
        finish_position_consistency=finish_cons,
        grid_position=grid_desc,
        grid_position_consistency=grid_cons,
        position_change=pos_change_stats,
        position_change_consistency=empty_cons,
        points=pts_stats,
        points_consistency=empty_cons,
        evidence=LongitudinalEvidenceMetadata(
            total_races=len(rounds_inc),
            valid_observations=len(rounds_inc),
            excluded_observations=0,
            min_required_observations=1,
            is_available=True,
            evidence_strength=EvidenceStrength.HIGH,
            rounds_included=rounds_inc,
        ),
    )


def _make_form_summary(
    driver_id: str = "verstappen",
    season_year: int = 2024,
    window_mean_finish: float = 1.0,
    valid_observations: int = 2,
    window_size: int = 3,
    round_num: int = 5,
    rounds_included: list[int] = None,
) -> DriverFormSummary:
    rounds_inc = rounds_included or [3, 4, 5]
    rw = RollingWindowStats(
        metric_name="finish_position",
        window_size_requested=window_size,
        round=round_num,
        rounds_included=rounds_inc,
        valid_observations=valid_observations,
        mean=window_mean_finish,
        median=window_mean_finish,
        stddev=0.0,
        minimum=window_mean_finish,
        maximum=window_mean_finish,
        evidence=LongitudinalEvidenceMetadata(
            total_races=len(rounds_inc),
            valid_observations=valid_observations,
            excluded_observations=len(rounds_inc) - valid_observations,
            min_required_observations=1,
            is_available=True,
            evidence_strength=EvidenceStrength.MODERATE,
            rounds_included=rounds_inc,
            window_size_requested=window_size,
        ),
    )
    return DriverFormSummary(
        driver_id=driver_id,
        season_year=season_year,
        up_to_round=round_num,
        rolling_windows=[rw],
        race_to_race_deltas=[],
        evidence=LongitudinalEvidenceMetadata(
            total_races=5,
            valid_observations=5,
            excluded_observations=0,
            min_required_observations=1,
            is_available=True,
            evidence_strength=EvidenceStrength.HIGH,
            rounds_included=[1, 2, 3, 4, 5],
        ),
    )


# ─── 1. Qualifying Consistency Tests ──────────────────────────────────────────

class TestQualifyingConsistencyRule:
    def test_qualifying_consistency_positive(self):
        stats = _make_driver_stats(grid_sample_size=5, grid_mean=1.0, grid_stddev=0.0)
        ins = evaluate_longitudinal_qualifying_consistency(stats)
        assert ins is not None
        assert ins.rule_id == RULE_LONGITUDINAL_QUALIFYING_CONSISTENCY
        assert ins.category == InsightCategory.QUALIFYING
        assert ins.subject_id == "verstappen"
        assert ins.direction == Direction.STABLE
        assert ins.magnitude == 0.0
        assert ins.evidence_strength == EvidenceStrength.HIGH
        assert ins.sample_size == 5
        assert "standard deviation of 0.00" in ins.explanation
        assert ins.traceability.source_function == "compute_driver_longitudinal_stats"

    def test_qualifying_consistency_exact_boundary(self):
        # Threshold is stddev <= 1.5
        stats = _make_driver_stats(grid_sample_size=4, grid_mean=3.0, grid_stddev=1.5)
        ins = evaluate_longitudinal_qualifying_consistency(stats)
        assert ins is not None
        assert ins.magnitude == 1.5
        assert ins.evidence_strength == EvidenceStrength.MODERATE

    def test_qualifying_consistency_negative_exceeds_threshold(self):
        stats = _make_driver_stats(grid_sample_size=5, grid_mean=4.0, grid_stddev=1.51)
        ins = evaluate_longitudinal_qualifying_consistency(stats)
        assert ins is None

    def test_qualifying_consistency_insufficient_sample_size(self):
        # min_sample_size is 3; 2 starts should emit None
        stats = _make_driver_stats(grid_sample_size=2, grid_mean=1.0, grid_stddev=0.0)
        ins = evaluate_longitudinal_qualifying_consistency(stats)
        assert ins is None

    def test_qualifying_consistency_missing_stddev(self):
        stats = _make_driver_stats(grid_sample_size=5, grid_mean=1.0, grid_stddev=None)
        ins = evaluate_longitudinal_qualifying_consistency(stats)
        assert ins is None


# ─── 2. Finish Consistency Tests ──────────────────────────────────────────────

class TestFinishConsistencyRule:
    def test_finish_consistency_positive(self):
        # 4 classified finishes (1 DNF excluded) with stddev 0.0
        stats = _make_driver_stats(finish_sample_size=4, finish_mean=1.0, finish_stddev=0.0)
        ins = evaluate_longitudinal_finish_consistency(stats)
        assert ins is not None
        assert ins.rule_id == RULE_LONGITUDINAL_FINISH_CONSISTENCY
        assert ins.category == InsightCategory.RACE_RESULT
        assert ins.direction == Direction.STABLE
        assert ins.evidence_strength == EvidenceStrength.MODERATE  # n=4 is MODERATE
        assert ins.sample_size == 4
        assert "DNFs excluded" in ins.traceability.sign_convention

    def test_finish_consistency_exact_boundary(self):
        stats = _make_driver_stats(finish_sample_size=5, finish_mean=2.0, finish_stddev=1.5)
        ins = evaluate_longitudinal_finish_consistency(stats)
        assert ins is not None
        assert ins.magnitude == 1.5
        assert ins.evidence_strength == EvidenceStrength.HIGH

    def test_finish_consistency_negative_exceeds_threshold(self):
        stats = _make_driver_stats(finish_sample_size=5, finish_mean=2.0, finish_stddev=1.8)
        ins = evaluate_longitudinal_finish_consistency(stats)
        assert ins is None

    def test_finish_consistency_insufficient_sample_size_due_to_dnfs(self):
        # 5 rounds entered, but only 2 classified finishes (3 DNFs)
        stats = _make_driver_stats(finish_sample_size=2, finish_mean=1.0, finish_stddev=0.0)
        ins = evaluate_longitudinal_finish_consistency(stats)
        assert ins is None


# ─── 3. Position Change Pattern Tests ─────────────────────────────────────────

class TestPositionChangePatternRules:
    def test_position_gain_pattern_positive(self):
        stats = _make_driver_stats(pos_change_valid=4, pos_change_mean=3.5)
        insights = evaluate_longitudinal_position_change_pattern(stats)
        assert len(insights) == 1
        ins = insights[0]
        assert ins.rule_id == RULE_LONGITUDINAL_POSITION_GAIN_PATTERN
        assert ins.direction == Direction.GAINED
        assert ins.magnitude == 3.5
        assert "gained an average of 3.5 positions" in ins.explanation

    def test_position_gain_pattern_exact_boundary(self):
        stats = _make_driver_stats(pos_change_valid=3, pos_change_mean=2.0)
        insights = evaluate_longitudinal_position_change_pattern(stats)
        assert len(insights) == 1
        assert insights[0].rule_id == RULE_LONGITUDINAL_POSITION_GAIN_PATTERN

    def test_position_loss_pattern_positive(self):
        stats = _make_driver_stats(pos_change_valid=4, pos_change_mean=-2.5)
        insights = evaluate_longitudinal_position_change_pattern(stats)
        assert len(insights) == 1
        ins = insights[0]
        assert ins.rule_id == RULE_LONGITUDINAL_POSITION_LOSS_PATTERN
        assert ins.direction == Direction.LOST
        assert ins.magnitude == 2.5
        assert "lost an average of 2.5 positions" in ins.explanation

    def test_position_loss_pattern_exact_boundary(self):
        stats = _make_driver_stats(pos_change_valid=3, pos_change_mean=-2.0)
        insights = evaluate_longitudinal_position_change_pattern(stats)
        assert len(insights) == 1
        assert insights[0].rule_id == RULE_LONGITUDINAL_POSITION_LOSS_PATTERN

    def test_position_change_neutral_no_pattern(self):
        stats = _make_driver_stats(pos_change_valid=5, pos_change_mean=0.2)
        insights = evaluate_longitudinal_position_change_pattern(stats)
        assert insights == []

    def test_position_change_insufficient_sample_size(self):
        stats = _make_driver_stats(pos_change_valid=2, pos_change_mean=4.0)
        insights = evaluate_longitudinal_position_change_pattern(stats)
        assert insights == []


# ─── 4. Points Per Start & Per Round Tests ────────────────────────────────────

class TestPointsRules:
    def test_points_per_start_positive(self):
        stats = _make_driver_stats(gp_starts=5, pp_gp_start=20.4, total_race_points="102.0")
        ins = evaluate_longitudinal_points_per_start(stats)
        assert ins is not None
        assert ins.rule_id == RULE_LONGITUDINAL_POINTS_PER_START
        assert ins.category == InsightCategory.POINTS
        assert ins.magnitude == 20.4
        assert "excluding sprint sessions" in ins.explanation

    def test_points_per_start_exact_boundary(self):
        stats = _make_driver_stats(gp_starts=4, pp_gp_start=15.0)
        ins = evaluate_longitudinal_points_per_start(stats)
        assert ins is not None
        assert ins.magnitude == 15.0

    def test_points_per_start_negative_below_threshold(self):
        stats = _make_driver_stats(gp_starts=5, pp_gp_start=12.0)
        ins = evaluate_longitudinal_points_per_start(stats)
        assert ins is None

    def test_points_per_round_total_includes_sprint(self):
        stats = _make_driver_stats(
            rounds_entered=5,
            total_race_points="102.0",
            total_sprint_points="8.0",
            pp_round_total=22.0,
        )
        ins = evaluate_longitudinal_points_per_round(stats)
        assert ins is not None
        assert ins.rule_id == RULE_LONGITUDINAL_POINTS_PER_ROUND
        assert ins.magnitude == 22.0
        assert "102.0 race, 8.0 sprint" in ins.explanation


# ─── 5. Recent Form Tests ─────────────────────────────────────────────────────

class TestRecentFormRule:
    def test_recent_form_positive(self):
        form = _make_form_summary(window_mean_finish=1.0, valid_observations=2, window_size=3)
        ins = evaluate_longitudinal_recent_form(form)
        assert ins is not None
        assert ins.rule_id == RULE_LONGITUDINAL_RECENT_FORM
        assert ins.category == InsightCategory.DRIVER_FORM
        assert ins.magnitude == 1.0
        assert "Over the most recent 3 rounds" in ins.explanation
        assert "average finish of P1.0 across 2 valid finishes" in ins.explanation

    def test_recent_form_exact_boundary(self):
        form = _make_form_summary(window_mean_finish=5.0, valid_observations=3, window_size=3)
        ins = evaluate_longitudinal_recent_form(form)
        assert ins is not None
        assert ins.magnitude == 5.0

    def test_recent_form_negative_exceeds_threshold(self):
        form = _make_form_summary(window_mean_finish=6.5, valid_observations=3, window_size=3)
        ins = evaluate_longitudinal_recent_form(form)
        assert ins is None

    def test_recent_form_insufficient_valid_observations_in_window(self):
        # Window of 3, but only 1 classified finish (e.g. 2 DNFs in last 3 rounds)
        form = _make_form_summary(window_mean_finish=1.0, valid_observations=1, window_size=3)
        ins = evaluate_longitudinal_recent_form(form)
        assert ins is None


# ─── 6. Teammate H2H Tests ────────────────────────────────────────────────────

class TestTeammateH2HRules:
    def _make_h2h(
        self,
        con_id: str = "red_bull",
        drv_a: str = "max_verstappen",
        drv_b: str = "perez",
        rounds: int = 5,
        q_comp: int = 5,
        q_wins_a: int = 5,
        q_rate_a: float = 1.0,
        r_comp: int = 4,
        r_wins_a: int = 4,
        r_rate_a: float = 1.0,
        pts_a: str = "102.0",
        pts_b: str = "77.0",
        sprint_a: str = "8.0",
        sprint_b: str = "8.0",
    ) -> TeammateH2HStatistics:
        rounds_inc = list(range(1, rounds + 1))
        empty_desc = DescriptiveStats(sample_size=0, mean=None, stddev=None, median=None, minimum=None, maximum=None, iqr=None)
        empty_cons = ConsistencyStats(stats=empty_desc, range=None, iqr=None, coefficient_of_variation=None)

        p_a = Decimal(pts_a)
        p_b = Decimal(pts_b)
        sp_a = Decimal(sprint_a)
        sp_b = Decimal(sprint_b)
        tot_a = p_a + sp_a
        tot_b = p_b + sp_b

        return TeammateH2HStatistics(
            constructor_id=con_id,
            driver_a_id=drv_a,
            driver_b_id=drv_b,
            rounds_together=rounds,
            qualifying_wins_a=q_wins_a,
            qualifying_wins_b=q_comp - q_wins_a,
            qualifying_comparable_rounds=q_comp,
            qualifying_win_rate_a=q_rate_a,
            qualifying_win_rate_b=1.0 - q_rate_a,
            qualifying_delta_stats=DescriptiveStats(sample_size=q_comp, mean=-288.0, stddev=50.0, median=-288.0, minimum=-350.0, maximum=-200.0, iqr=50.0),
            qualifying_delta_consistency=empty_cons,
            qualifying_evidence=LongitudinalEvidenceMetadata(total_races=rounds, valid_observations=q_comp, excluded_observations=rounds - q_comp, min_required_observations=1, is_available=True, evidence_strength=EvidenceStrength.HIGH, rounds_included=rounds_inc),
            race_wins_a=r_wins_a,
            race_wins_b=r_comp - r_wins_a,
            race_comparable_rounds=r_comp,
            race_win_rate_a=r_rate_a,
            race_win_rate_b=1.0 - r_rate_a,
            race_delta_stats=empty_desc,
            race_delta_consistency=empty_cons,
            race_evidence=LongitudinalEvidenceMetadata(total_races=rounds, valid_observations=r_comp, excluded_observations=rounds - r_comp, min_required_observations=1, is_available=True, evidence_strength=EvidenceStrength.MODERATE, rounds_included=rounds_inc),
            points_a=p_a,
            points_b=p_b,
            sprint_points_a=sp_a,
            sprint_points_b=sp_b,
            total_points_a=tot_a,
            total_points_b=tot_b,
            points_difference=tot_a - tot_b,
            points_delta_stats=empty_desc,
            points_evidence=LongitudinalEvidenceMetadata(total_races=rounds, valid_observations=rounds, excluded_observations=0, min_required_observations=1, is_available=True, evidence_strength=EvidenceStrength.HIGH, rounds_included=rounds_inc),
        )

    def test_verstappen_vs_perez_all_dimensions(self):
        h2h = self._make_h2h()
        insights = evaluate_longitudinal_teammate_h2h(h2h, season_year=2024)
        assert len(insights) == 3

        rule_ids = {ins.rule_id for ins in insights}
        assert RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H in rule_ids
        assert RULE_LONGITUDINAL_TEAMMATE_RACE_H2H in rule_ids
        assert RULE_LONGITUDINAL_TEAMMATE_POINTS_H2H in rule_ids

        # Qualifying
        q_ins = next(i for i in insights if i.rule_id == RULE_LONGITUDINAL_TEAMMATE_QUALIFYING_H2H)
        assert q_ins.subject_id == "max_verstappen"
        assert q_ins.comparison_subject_id == "perez"
        assert q_ins.magnitude == 1.0
        assert q_ins.direction == Direction.FASTER

        # Points
        p_ins = next(i for i in insights if i.rule_id == RULE_LONGITUDINAL_TEAMMATE_POINTS_H2H)
        assert p_ins.magnitude == 25.0
        assert "sprint: 8.0 vs 8.0" in p_ins.explanation

    def test_bearman_substitution_emits_zero_longitudinal_insights(self):
        # Bearman/Leclerc had only 1 round together -> sample size 1 < 3
        h2h = self._make_h2h(
            con_id="ferrari",
            drv_a="bearman",
            drv_b="leclerc",
            rounds=1,
            q_comp=1,
            q_wins_a=0,
            q_rate_a=0.0,
            r_comp=1,
            r_wins_a=0,
            r_rate_a=0.0,
            pts_a="6.0",
            pts_b="16.0",
            sprint_a="0.0",
            sprint_b="0.0",
        )
        insights = evaluate_longitudinal_teammate_h2h(h2h, season_year=2024)
        assert insights == []

    def test_balanced_pairing_no_false_positive_advantage(self):
        # 4 rounds, Q: 2-2 (win rate 0.50 < 0.70), points diff 9.0 < 15.0
        h2h = self._make_h2h(
            con_id="ferrari",
            drv_a="leclerc",
            drv_b="sainz",
            rounds=4,
            q_comp=4,
            q_wins_a=2,
            q_rate_a=0.5,
            r_comp=4,
            r_wins_a=1,
            r_rate_a=0.25,
            pts_a="60.0",
            pts_b="69.0",
        )
        insights = evaluate_longitudinal_teammate_h2h(h2h, season_year=2024)
        # Sainz won 3/4 races (75% >= 70%) -> should emit Race H2H for Sainz, but no Q or Points H2H
        assert len(insights) == 1
        assert insights[0].rule_id == RULE_LONGITUDINAL_TEAMMATE_RACE_H2H
        assert insights[0].subject_id == "sainz"
        assert insights[0].comparison_subject_id == "leclerc"


# ─── 7. Constructor Trajectory Tests ──────────────────────────────────────────

class TestConstructorTrajectoryRule:
    def _make_trajectory_item(self, rnd: int, podiums: int = 1, cum_pts: str = "25.0") -> ConstructorTrajectoryItem:
        return ConstructorTrajectoryItem(
            season_year=2024,
            round=rnd,
            race_name=f"Race {rnd}",
            circuit_name=f"Circuit {rnd}",
            race_date=date(2024, 3, rnd * 5),
            constructor_id="red_bull",
            constructor_name="Red Bull",
            race_points=Decimal("25.0"),
            sprint_points=Decimal("0.0"),
            total_round_points=Decimal("25.0"),
            cumulative_race_points=Decimal(cum_pts),
            cumulative_sprint_points=Decimal("0.0"),
            cumulative_total_points=Decimal(cum_pts),
            best_finish=1,
            podiums=podiums,
            cars_classified=2,
            cars_entered=2,
            championship_standing_position=1,
        )

    def test_constructor_podium_rate_positive(self):
        traj = [self._make_trajectory_item(r, podiums=1, cum_pts=str(r * 25)) for r in range(1, 6)]
        insights = evaluate_constructor_longitudinal_insights(traj, season_year=2024, constructor_id="red_bull")
        assert len(insights) == 1
        ins = insights[0]
        assert ins.rule_id == RULE_LONGITUDINAL_CONSTRUCTOR_TRAJECTORY
        assert ins.category == InsightCategory.CONSTRUCTOR
        assert ins.magnitude == 1.0  # 5/5 = 100%
        assert ins.evidence_strength == EvidenceStrength.HIGH
        assert "achieved podium finishes in 5 rounds (100%)" in ins.explanation

    def test_constructor_podium_rate_negative_below_threshold(self):
        # 1 podium in 5 races = 20% < 60%
        traj = [self._make_trajectory_item(r, podiums=1 if r == 1 else 0) for r in range(1, 6)]
        insights = evaluate_constructor_longitudinal_insights(traj, season_year=2024, constructor_id="alpine")
        assert insights == []

    def test_constructor_trajectory_insufficient_sample_size(self):
        traj = [self._make_trajectory_item(r, podiums=1) for r in range(1, 3)]
        insights = evaluate_constructor_longitudinal_insights(traj, season_year=2024, constructor_id="red_bull")
        assert insights == []


# ─── 8. Determinism and Deduplication Tests ────────────────────────────────────

class TestDeterminismAndDeduplication:
    def test_engine_deduplication(self):
        stats = _make_driver_stats(grid_sample_size=5, grid_stddev=0.0)
        ins1 = evaluate_longitudinal_qualifying_consistency(stats)
        ins2 = evaluate_longitudinal_qualifying_consistency(stats)

        assert ins1.insight_id == ins2.insight_id
        deduped = InsightEngine.deduplicate([ins1, ins2])
        assert len(deduped) == 1

    def test_driver_profile_aggregation(self):
        stats = _make_driver_stats()
        form = _make_form_summary()
        insights = evaluate_driver_longitudinal_insights(stats, form)

        # Should generate qualifying consistency, finish consistency, points per start, points per round, recent form
        rule_ids = [ins.rule_id for ins in insights]
        assert RULE_LONGITUDINAL_QUALIFYING_CONSISTENCY in rule_ids
        assert RULE_LONGITUDINAL_FINISH_CONSISTENCY in rule_ids
        assert RULE_LONGITUDINAL_POINTS_PER_START in rule_ids
        assert RULE_LONGITUDINAL_POINTS_PER_ROUND in rule_ids
        assert RULE_LONGITUDINAL_RECENT_FORM in rule_ids

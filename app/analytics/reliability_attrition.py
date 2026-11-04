"""Deterministic, Grand Prix-only reliability and attrition analytics.

Source status supports retirement, DNS, DSQ and classified-result categories.
The imported 2024 data does not identify mechanical versus incident causes, so
this module intentionally makes no mechanical-failure attribution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.race import Race
from app.db.models.race_result import RaceResult

PHASE_DEFINITIONS: list[tuple[str, int, int]] = [("Early", 1, 8), ("Middle", 9, 16), ("Late", 17, 24)]


@dataclass(frozen=True)
class AttritionMetrics:
    entries: Optional[int]
    starts: Optional[int]
    classified_finishes: Optional[int]
    dnf_results: Optional[int]
    dns_results: Optional[int]
    dsq_results: Optional[int]
    unknown_non_classified: Optional[int]
    non_classified_results: Optional[int]
    dnf_rate: Optional[float]
    non_classification_rate: Optional[float]


@dataclass(frozen=True)
class EntityAttritionSummary:
    entity_id: str
    entity_name: str
    metrics: AttritionMetrics


@dataclass(frozen=True)
class AttritionPeriodSummary:
    period_name: str
    start_round: int
    end_round: int
    is_complete: bool
    total: AttritionMetrics
    constructors: dict[str, EntityAttritionSummary]
    drivers: dict[str, EntityAttritionSummary]


@dataclass(frozen=True)
class ReliabilityAttritionReport:
    season_year: int
    up_to_round: int
    phases: dict[str, AttritionPeriodSummary]
    rounds: list[AttritionPeriodSummary]


def classify_attrition_status(position_text: Optional[str], status: Optional[str]) -> str:
    """Classify only source-supported result states; no causal inference."""
    position = (position_text or "").strip().upper()
    normalized = (status or "").strip().lower()
    if normalized in {"did not start", "dns", "withdrawn"} or position in {"W", "DNS"}:
        return "DNS"
    if normalized == "disqualified" or position == "D":
        return "DSQ"
    if normalized == "retired" or position == "R":
        return "DNF"
    if position or normalized in {"finished", "lapped"} or normalized.startswith("+"):
        return "CLASSIFIED"
    return "UNKNOWN_NON_CLASSIFIED"


def _unavailable() -> AttritionMetrics:
    return AttritionMetrics(*(None for _ in range(10)))


def _metrics(entries: int, starts: int, classified: int, dnf: int, dns: int, dsq: int, unknown: int) -> AttritionMetrics:
    non_classified = dnf + dsq + unknown
    return AttritionMetrics(
        entries=entries, starts=starts, classified_finishes=classified, dnf_results=dnf,
        dns_results=dns, dsq_results=dsq, unknown_non_classified=unknown,
        non_classified_results=non_classified,
        dnf_rate=round(dnf / starts * 100, 4) if starts else None,
        non_classification_rate=round(non_classified / starts * 100, 4) if starts else None,
    )


def _aggregate(session: Session, season_year: int, start_round: int, end_round: int, group_column, entity_name_column) -> dict[str, EntityAttritionSummary]:
    category = case(
        (func.lower(RaceResult.status).in_(["did not start", "dns", "withdrawn"]), "DNS"),
        (RaceResult.position_text.in_(["W", "DNS"]), "DNS"),
        (func.lower(RaceResult.status) == "disqualified", "DSQ"), (RaceResult.position_text == "D", "DSQ"),
        (func.lower(RaceResult.status) == "retired", "DNF"), (RaceResult.position_text == "R", "DNF"),
        (RaceResult.position_text != "", "CLASSIFIED"),
        (func.lower(RaceResult.status).in_(["finished", "lapped"]), "CLASSIFIED"),
        (RaceResult.status.startswith("+"), "CLASSIFIED"),
        else_="UNKNOWN_NON_CLASSIFIED",
    )
    query = (
        select(
            group_column, entity_name_column, func.count(RaceResult.id),
            func.sum(case((category != "DNS", 1), else_=0)),
            func.sum(case((category == "CLASSIFIED", 1), else_=0)),
            func.sum(case((category == "DNF", 1), else_=0)),
            func.sum(case((category == "DNS", 1), else_=0)),
            func.sum(case((category == "DSQ", 1), else_=0)),
            func.sum(case((category == "UNKNOWN_NON_CLASSIFIED", 1), else_=0)),
        )
        .select_from(RaceResult)
        .join(Race, Race.id == RaceResult.race_id)
        .where(Race.season_year == season_year, Race.round.between(start_round, end_round))
        .group_by(group_column, entity_name_column)
        .order_by(group_column)
    )
    if group_column is Constructor.constructor_id:
        query = query.join(Constructor, Constructor.id == RaceResult.constructor_id)
    else:
        query = query.join(Driver, Driver.id == RaceResult.driver_id)
    results: dict[str, EntityAttritionSummary] = {}
    for entity_id, name, entries, starts, classified, dnf, dns, dsq, unknown in session.execute(query):
        results[entity_id] = EntityAttritionSummary(
            entity_id=entity_id, entity_name=name,
            metrics=_metrics(int(entries), int(starts or 0), int(classified or 0), int(dnf or 0), int(dns or 0), int(dsq or 0), int(unknown or 0)),
        )
    return results


def _period(session: Session, season_year: int, name: str, start: int, end: int, available: set[int]) -> AttritionPeriodSummary:
    complete = set(range(start, end + 1)).issubset(available)
    if not complete:
        return AttritionPeriodSummary(name, start, end, False, _unavailable(), {}, {})
    constructors = _aggregate(session, season_year, start, end, Constructor.constructor_id, Constructor.name)
    drivers = _aggregate(session, season_year, start, end, Driver.driver_id, func.trim(Driver.given_name + " " + Driver.family_name))
    total = _metrics(
        sum(item.metrics.entries or 0 for item in constructors.values()),
        sum(item.metrics.starts or 0 for item in constructors.values()),
        sum(item.metrics.classified_finishes or 0 for item in constructors.values()),
        sum(item.metrics.dnf_results or 0 for item in constructors.values()),
        sum(item.metrics.dns_results or 0 for item in constructors.values()),
        sum(item.metrics.dsq_results or 0 for item in constructors.values()),
        sum(item.metrics.unknown_non_classified or 0 for item in constructors.values()),
    )
    return AttritionPeriodSummary(name, start, end, True, total, constructors, drivers)


def get_reliability_attrition_report(session: Session, season_year: int, up_to_round: Optional[int] = None) -> ReliabilityAttritionReport:
    """Return complete fixed-phase and round-level GP reliability evidence.

    A round is complete only when it has at least one stored GP result.  This is
    an analytics report, not an inference about retirement cause.
    """
    completed = set(session.scalars(
        select(Race.round).join(RaceResult, RaceResult.race_id == Race.id).where(Race.season_year == season_year, Race.round <= up_to_round if up_to_round is not None else True).distinct()
    ).all())
    actual_cutoff = up_to_round if up_to_round is not None else max(completed, default=0)
    phases = {name: _period(session, season_year, name, start, end, completed) for name, start, end in PHASE_DEFINITIONS}
    rounds = [_period(session, season_year, f"R{round_num:02d}", round_num, round_num, completed) for round_num in range(1, actual_cutoff + 1)]
    return ReliabilityAttritionReport(season_year, actual_cutoff, phases, rounds)

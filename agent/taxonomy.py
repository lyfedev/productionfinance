"""D-86: the three-value mismatch taxonomy, built in now rather than
retrofitted (AGT-04). Every comparison between a disclosed government
figure and the engine's computed figure carries EXACTLY one of three
values — `exact_match`, `explained_variance`, `unexplained` — and never a
fourth, and never a `None`.

`explained_variance` is reachable ONLY through a named, sourced, dated rule
declared in `agent/variance_rules.yaml`. Predicates resolve by NAME from a
closed set implemented in this module — never `eval`, never an expression
string executed from the YAML file (T-05-07). An unknown predicate name
raises `UnknownPredicateError` at load time, matching the repo's fail-loud
schema convention (`engine.models.load_ruleset`).

`AccuracySummary` reports the four bucket/failure counts and nothing else
(D-86): no percentage, mean, average, blended or aggregate error field of
any kind — a blended number can silently absorb a real bug, which is worse
than no figure at all.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from agent.numbers import UnparseableFigureError, parse_money
from agent.schema import ExtractedAward

__all__ = [
    "AccuracySummary",
    "AwardResult",
    "MatchClass",
    "UnknownPredicateError",
    "VarianceExplanation",
    "VarianceRule",
    "classify",
    "load_variance_rules",
    "summarize",
]


class MatchClass(str, Enum):
    """Exactly three members. There is no fourth and no `None` verdict —
    every comparison carries one of these (AGT-04)."""

    exact_match = "exact_match"
    explained_variance = "explained_variance"
    unexplained = "unexplained"


@dataclass(frozen=True)
class VarianceExplanation:
    """Why a mismatch was classified `explained_variance` — always traced
    back to one named, sourced, dated rule."""

    rule_id: str
    reason: str
    source_url: str
    date_checked: str


@dataclass(frozen=True)
class VarianceRule:
    """One declared rule from `agent/variance_rules.yaml`. `params` carries
    any predicate-specific extra keys the rule's YAML entry declares beyond
    the five fixed fields (e.g. `programme_id`/`declared_rate` for
    `implied_rate_matches_declared_alternate_programme`)."""

    id: str
    predicate: str
    reason: str
    source_url: str
    date_checked: str
    params: dict[str, Any] = field(default_factory=dict)


class UnknownPredicateError(ValueError):
    """Raised by `load_variance_rules` when a rule names a predicate
    outside the closed set implemented in this module (T-05-07)."""


@dataclass(frozen=True)
class AwardResult:
    """One extracted award's full comparison record."""

    award: ExtractedAward
    disclosed: Decimal
    computed: Decimal | None
    match_class: MatchClass
    explanation: VarianceExplanation | None
    derivation: tuple[str, ...] = field(default_factory=tuple)
    corroborates_committed_fixture: bool = False


@dataclass(frozen=True)
class AccuracySummary:
    """Honest bucket counts only (D-86) — no percentage, mean, average,
    blended, or aggregate-error field of any kind. The four counts below
    sum to `awards_extracted`."""

    awards_extracted: int
    exact_match: int
    explained_variance: int
    unexplained: int
    extraction_failures: int


# ---------------------------------------------------------------------------
# The closed predicate set (T-05-07) — resolved by NAME from
# agent/variance_rules.yaml, never `eval`, never an expression string.
# ---------------------------------------------------------------------------


def _diversity_credit_equals_delta(
    disclosed: Decimal, computed: Decimal, award: ExtractedAward
) -> bool:
    """The ESD "Credits Issued" chart lists the diversity uplift as its own
    column. A row whose disclosed total exceeds the modelled production
    credit by exactly that column's value is explained, not a modelling
    error."""
    if award.diversity_credit_amount is None:
        return False
    try:
        diversity_credit = parse_money(award.diversity_credit_amount)
    except UnparseableFigureError:
        return False
    return (disclosed - computed) == diversity_credit


def _implied_rate_matches_declared_alternate_programme(
    disclosed: Decimal,
    computed: Decimal,
    award: ExtractedAward,
    *,
    programme_id: str,
    declared_rate: str,
) -> bool:
    """A row the disclosure attributes to a programme label OTHER than the
    one this engine modelled (`programme_id`), where the row's own implied
    rate (disclosed / qualified spend) equals that modelled programme's own
    declared rate exactly. This means the disclosure's alternate-programme
    label is a categorisation artifact of the source document, not evidence
    that the engine mis-modelled the rate."""
    if not award.programme_hint or award.programme_hint == programme_id:
        return False
    try:
        qualified_spend = parse_money(award.qualified_spend)
    except UnparseableFigureError:
        return False
    if qualified_spend == 0:
        return False
    implied_rate = disclosed / qualified_spend
    return implied_rate == Decimal(declared_rate)


_PREDICATES: dict[str, Callable[..., bool]] = {
    "diversity_credit_equals_delta": _diversity_credit_equals_delta,
    "implied_rate_matches_declared_alternate_programme": (
        _implied_rate_matches_declared_alternate_programme
    ),
}

_FIXED_RULE_KEYS = {"id", "predicate", "reason", "source_url", "date_checked"}


def load_variance_rules(path: str | Path) -> tuple[VarianceRule, ...]:
    """Load the declared, sourced, versioned rule file. Raises
    `UnknownPredicateError` — naming the offending predicate — if any entry
    names a predicate outside the closed `_PREDICATES` set."""
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    entries = raw.get("rules", []) if isinstance(raw, dict) else []
    rules: list[VarianceRule] = []
    for entry in entries:
        predicate_name = entry.get("predicate")
        if predicate_name not in _PREDICATES:
            raise UnknownPredicateError(
                f"{path}: rule {entry.get('id')!r} declares unknown predicate "
                f"{predicate_name!r} — known predicates: {sorted(_PREDICATES)}"
            )
        params = {k: v for k, v in entry.items() if k not in _FIXED_RULE_KEYS}
        rules.append(
            VarianceRule(
                id=entry["id"],
                predicate=predicate_name,
                reason=entry["reason"],
                source_url=entry["source_url"],
                date_checked=entry["date_checked"],
                params=params,
            )
        )
    return tuple(rules)


def classify(
    disclosed: Decimal,
    computed: Decimal,
    award: ExtractedAward,
    rules: Sequence[VarianceRule],
) -> tuple[MatchClass, VarianceExplanation | None]:
    """Exact equality first; then each declared rule in file order, first
    match wins; else unexplained. Never widen exact equality with a
    tolerance — that mechanism belongs to the fixture layer's
    `assertion.mode: bounded`, not to this classifier."""
    if disclosed == computed:
        return MatchClass.exact_match, None

    for rule in rules:
        predicate = _PREDICATES[rule.predicate]
        if predicate(disclosed, computed, award, **rule.params):
            explanation = VarianceExplanation(
                rule_id=rule.id,
                reason=rule.reason,
                source_url=rule.source_url,
                date_checked=rule.date_checked,
            )
            return MatchClass.explained_variance, explanation

    return MatchClass.unexplained, None


def summarize(results: Sequence[AwardResult], *, extraction_failures: int) -> AccuracySummary:
    """Build an `AccuracySummary` from a batch of `AwardResult`s. Never
    divides by anything — a run with zero results produces every count 0."""
    exact = sum(1 for r in results if r.match_class is MatchClass.exact_match)
    explained = sum(1 for r in results if r.match_class is MatchClass.explained_variance)
    unexplained = sum(1 for r in results if r.match_class is MatchClass.unexplained)
    return AccuracySummary(
        awards_extracted=len(results) + extraction_failures,
        exact_match=exact,
        explained_variance=explained,
        unexplained=unexplained,
        extraction_failures=extraction_failures,
    )

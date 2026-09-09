"""AGT-10's single point of truth for cached-vs-live data classification.

At module load time this file imports nothing from `agent/` or `engine/`
— every consumer, including `agent/job2.py`, can depend on it without a
cycle. Plan 07-04 (Task 1/Task 2) adds three sanctioned entry points —
`resolve_fx`, `resolve_cap_consumption`, `resolve_programme_status` — each
of which imports its own resolver module (`app.services.live_fx`,
`agent.live_checks`) LAZILY, inside the function body, so this module's
own top-level import graph stays exactly as clean as the sentence above
promises; the lazy import is what lets `app.services.live_fx` and
`agent.live_checks` import DataClass/assert_live back FROM this module
(a normal, one-directional dependency at the moment either of THEM is
actually loaded) without a circular import at process start.

Curated rule models are cached because they are committed YAML under
`jurisdictions/` whose git history is the audit trail (03-REVIEW.md
precedent); the other four data classes move between one request and the
next and must be resolved on the request. This is D-89's "the live
research path must not read from cache" made structural rather than
aspirational: `agent/job2.py` calls `assert_live(DataClass.uncurated_city_research)`
before its first Search call, and that call raises if this table is ever
mutated to class that data class as cached. Plan 07-04 extends the same
discipline to the other three live classes: `app/services/spec.py` (and
nothing else) calls `resolve_fx`/`resolve_cap_consumption`/
`resolve_programme_status` — never `httpx`, `engine.fx.load_fx_snapshot`,
or `agent.live_checks` directly — so this module stays the one place the
cached-versus-live decision is made for all five data classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.services.live_fx import FxResolution

__all__ = [
    "POLICY",
    "CacheBoundaryViolation",
    "DataClass",
    "PolicyEntry",
    "ProgrammeStatusCheck",
    "assert_live",
    "may_use_cache",
    "resolve_cap_consumption",
    "resolve_fx",
    "resolve_programme_status",
]


class DataClass(str, Enum):
    """A closed set — AGT-10's five data classes."""

    curated_rule_model = "curated_rule_model"
    cap_consumption = "cap_consumption"
    programme_open_status = "programme_open_status"
    fx_rate = "fx_rate"
    uncurated_city_research = "uncurated_city_research"


@dataclass(frozen=True)
class PolicyEntry:
    """One `DataClass`'s AGT-10 verdict plus the one-line reasoning for it —
    so `POLICY` reads as the phase's stated policy, not an unexplained
    dict."""

    verdict: Literal["cached", "live"]
    rationale: str


POLICY: dict[DataClass, PolicyEntry] = {
    DataClass.curated_rule_model: PolicyEntry(
        verdict="cached",
        rationale=(
            "Committed YAML under jurisdictions/ whose git history is already the audit trail."
        ),
    ),
    DataClass.cap_consumption: PolicyEntry(
        verdict="live",
        rationale="A programme's cap consumption moves between one request and the next.",
    ),
    DataClass.programme_open_status: PolicyEntry(
        verdict="live",
        rationale="A programme's open/closed state can change between requests.",
    ),
    DataClass.fx_rate: PolicyEntry(
        verdict="live",
        rationale="A currency rate moves continuously and must be resolved on the request.",
    ),
    DataClass.uncurated_city_research: PolicyEntry(
        verdict="live",
        rationale="D-89: the live research path must not read from cache.",
    ),
}


class CacheBoundaryViolation(RuntimeError):
    """Raised by `assert_live` (and by `may_use_cache`/`assert_live` for a
    non-member value) — proves the assertion is load-bearing, not
    decorative."""


def _entry_for(data_class: DataClass) -> PolicyEntry:
    if not isinstance(data_class, DataClass):
        raise CacheBoundaryViolation(f"not a DataClass member: {data_class!r}")
    return POLICY[data_class]


def may_use_cache(data_class: DataClass) -> bool:
    """True iff `POLICY[data_class]` allows a cached read. Raises
    `CacheBoundaryViolation` for a value that is not a `DataClass` member —
    a bare string can never smuggle past the boundary."""
    return _entry_for(data_class).verdict == "cached"


def assert_live(data_class: DataClass) -> None:
    """Raise `CacheBoundaryViolation` unless `data_class` is currently
    classed `\"live\"`. Also raises for a non-`DataClass` value."""
    entry = _entry_for(data_class)
    if entry.verdict != "live":
        raise CacheBoundaryViolation(
            f"{data_class.value} is classed {entry.verdict!r}, not live: {entry.rationale}"
        )


# ---------------------------------------------------------------------------
# Plan 07-04: the three sanctioned live-resolver entry points. Each asserts
# this module's own policy before doing anything, then delegates the
# transport/SDK mechanics to a resolver module that itself imports
# DataClass/assert_live from here (the "consumer" half of the AGT-10
# single-point-of-truth AST gate, tests/test_cache_policy_live.py).
# ---------------------------------------------------------------------------


def resolve_fx(base: str, quote: str, on_date: date) -> FxResolution:
    """The single sanctioned FX entry point (AGT-10/D-89): a caller asks
    THIS module for a rate, never `httpx` or `engine.fx.load_fx_snapshot`
    directly — that would put a second cached-versus-live decision outside
    the single point AGT-10 requires. Delegates the live-attempt-then-
    disclosed-fallback mechanics to `app.services.live_fx`, imported here
    lazily so this module's own top-level import graph never depends on
    `httpx` or `engine.fx`."""
    from app.services.live_fx import resolve_fx as _resolve_fx_live_or_fallback

    return _resolve_fx_live_or_fallback(base, quote, on_date)


def resolve_cap_consumption(
    *,
    jurisdiction_name: str,
    programme_name: str,
    cap_consumption_method: str | None,
    source_url_hint: str | None,
) -> Decimal | None:
    """Returns the live-resolved remaining annual cap allocation, or
    `None` when this programme's `cap_consumption_check.method` is absent
    or is not `\"live_research\"` — a programme declaring
    `official_dashboard`, `manual`, or `not_applicable` (or no check at
    all) never reaches a Search call here. `None` also covers an
    undetermined live result: never a fabricated remaining balance
    (AGT-10/D-94). `engine.credit.assess_availability` is the only
    consumer of the value this function returns."""
    if cap_consumption_method != "live_research":
        return None

    assert_live(DataClass.cap_consumption)
    from agent.live_checks import check_cap_consumption

    result = check_cap_consumption(jurisdiction_name, programme_name, source_url_hint)
    if not result.determined or result.remaining is None:
        return None
    return result.remaining


@dataclass(frozen=True)
class ProgrammeStatusCheck:
    """The live open/closed answer for one programme — carried alongside
    the priced result, its own line with its own source and check time.
    NEVER written into `Jurisdiction.status`, never passed to
    `assess_eligibility`, and never changes a `Figure.confidence` value —
    that field drives the `validated`-versus-`researched` stamp, and a
    live check overwriting it would silently relabel researched data as
    validated (the exact dishonesty this project exists to refute)."""

    state: Literal["open", "closed", "unknown"]
    source_url: str | None
    checked_at: str | None
    reason: str


def resolve_programme_status(
    *, jurisdiction_name: str, programme_name: str
) -> ProgrammeStatusCheck:
    """The live open/closed check for one programme."""
    assert_live(DataClass.programme_open_status)
    from agent.live_checks import check_programme_open

    result = check_programme_open(jurisdiction_name, programme_name)
    return ProgrammeStatusCheck(
        state=result.state,
        source_url=result.source_url,
        checked_at=result.checked_at,
        reason=result.reason,
    )

"""AGT-10's single point of truth for cached-vs-live data classification.

Imports nothing from `agent/` or `engine/` so every consumer — including
`agent/job2.py` — can depend on it without a cycle.

Curated rule models are cached because they are committed YAML under
`jurisdictions/` whose git history is the audit trail (03-REVIEW.md
precedent); the other four data classes move between one request and the
next and must be resolved on the request. This is D-89's "the live
research path must not read from cache" made structural rather than
aspirational: `agent/job2.py` calls `assert_live(DataClass.uncurated_city_research)`
before its first Search call, and that call raises if this table is ever
mutated to class that data class as cached.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

__all__ = [
    "POLICY",
    "CacheBoundaryViolation",
    "DataClass",
    "PolicyEntry",
    "assert_live",
    "may_use_cache",
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

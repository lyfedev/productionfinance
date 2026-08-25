"""The Figure value object — an immutable computed number that carries its
own provenance and derivation.

Reproduced from ``.planning/research/ARCHITECTURE.md`` Q3 as the specified
design (verbatim in ``02-RESEARCH.md`` "Code Examples"), not a new proposal.
A ``Figure`` travels with the data as a return-value field — no global
mutable trace object, no side-channel, no signature pollution.

PRV-01/PRV-02/PRV-03 are enforced structurally by this class:
  - PRV-01: ``source_url``/``date_checked`` are required constructor
    arguments; an unknown fact is an explicit ``None``, never an empty
    string or an invented URL.
  - PRV-02: ``confidence`` is a closed two-value enum with no default —
    omitting it, or passing anything other than the two legal strings, is a
    runtime error.
  - PRV-03: ``derivation`` is a non-empty tuple by construction contract
    (every producer of a ``Figure`` is required to seed it with at least one
    line); ``with_step`` only ever appends, never replaces or collapses.

Note on the two confidence vocabularies (RD-02, ``02-01-PLAN.md``):
``Figure.confidence`` measures whether *this computed figure* has been
checked against a real government disclosure (``validated``) or is only
research-backed (``researched``). This is a different axis from
``tests/test_source_truth.py``'s ``LEGAL_CONFIDENCE_TIERS`` four-tier
source-document-reliability vocabulary (``LOW``/``MEDIUM``/``MEDIUM-HIGH``/
``HIGH``), used by ``JurisdictionRuleSet.sources[].confidence`` in
``engine/models.py``. The two are never conflated.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import uuid4

__all__ = ["Confidence", "Figure", "combined_confidence"]

Confidence = Literal["validated", "researched"]

_LEGAL_CONFIDENCE_VALUES = ("validated", "researched")


def _new_figure_id() -> str:
    # uuid4 gives collision-proof uniqueness per constructed instance without
    # any shared mutable counter state — two Figures with the same value and
    # label but different sources (or two evolutions of the same lineage via
    # with_step) never collide (PRV-01 adjacency edge).
    return uuid4().hex


@dataclass(frozen=True, kw_only=True)
class Figure:
    """An immutable computed number with its own derivation DAG.

    All fields are keyword-only (``kw_only=True``) so the required/optional
    split below is enforceable regardless of declaration order — every field
    except ``figure_id`` is required; passing none of them, or omitting
    ``confidence`` specifically, raises ``TypeError`` from the generated
    ``__init__``.
    """

    value: Decimal
    unit: str
    label: str
    derivation: tuple[str, ...]
    inputs: tuple["Figure", ...]
    source_url: str | None
    date_checked: date | None
    confidence: Confidence
    live_fetched_this_run: bool
    figure_id: str = field(default_factory=_new_figure_id)

    def __post_init__(self) -> None:
        if self.confidence not in _LEGAL_CONFIDENCE_VALUES:
            raise ValueError(
                f"Figure.confidence must be one of {_LEGAL_CONFIDENCE_VALUES}, "
                f"got {self.confidence!r}"
            )

    def with_step(self, line: str, *, value: Decimal | None = None) -> "Figure":
        """Return a new frozen Figure with ``line`` appended to derivation.

        Two adjacent no-op steps calling this method in sequence produce two
        distinct derivation lines — the derivation tuple is only ever
        appended to, never collapsed or deduplicated (PRV-03).
        """
        return replace(
            self,
            derivation=(*self.derivation, line),
            value=self.value if value is None else value,
            figure_id=_new_figure_id(),
        )


def combined_confidence(inputs: Sequence[Figure]) -> Confidence:
    """Derive a combined confidence from a sequence of input Figures.

    Returns ``"researched"`` if any input is ``researched`` — the weaker
    tier always wins. Aggregation never upgrades a confidence tier (PRV-02):
    a Figure combining a validated input and a researched input reports
    ``researched``, never ``validated``. An empty sequence defaults to
    ``"validated"`` — there is nothing weaker to inherit from.
    """
    if any(figure.confidence == "researched" for figure in inputs):
        return "researched"
    return "validated"

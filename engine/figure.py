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

__all__ = ["Basis", "Confidence", "Figure", "combined_basis", "combined_confidence"]

Confidence = Literal["validated", "researched"]

_LEGAL_CONFIDENCE_VALUES = ("validated", "researched")

# D-58: a third, orthogonal provenance axis for cost-side figures — *where
# the number came from*, never conflated with `Confidence` (RD-02) or with
# `Jurisdiction.sources[].confidence`'s four-tier vocabulary. `sourced` is
# strongest, `modelling_assumption` is weakest.
Basis = Literal["sourced", "estimated", "modelling_assumption"]

_LEGAL_BASIS_VALUES = ("sourced", "estimated", "modelling_assumption")

# Weakest-wins ordering for `combined_basis` — lower number is weaker.
_BASIS_WEAKNESS_ORDER: dict[str, int] = {
    "modelling_assumption": 0,
    "estimated": 1,
    "sourced": 2,
}


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
    except ``figure_id`` and ``basis`` is required; passing none of them, or
    omitting ``confidence`` specifically, raises ``TypeError`` from the
    generated ``__init__``.

    ``basis`` (D-58) defaults to ``None`` because every pre-Phase-4
    construction site (``engine/credit.py``, ``engine/net_cash.py``,
    ``engine/qualifying_base.py``, ``engine/pipeline.py``) omits it — it is
    the incentive side's axis-that-does-not-apply, not an unset cost claim.
    Every cost-side ``Figure`` constructed from Phase 4 onward must supply a
    real ``Basis`` value; ``combined_basis`` below refuses to paper over a
    missing one.
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
    basis: Basis | None = None

    def __post_init__(self) -> None:
        if self.confidence not in _LEGAL_CONFIDENCE_VALUES:
            raise ValueError(
                f"Figure.confidence must be one of {_LEGAL_CONFIDENCE_VALUES}, "
                f"got {self.confidence!r}"
            )
        if self.basis is not None and self.basis not in _LEGAL_BASIS_VALUES:
            raise ValueError(
                f"Figure.basis must be one of {_LEGAL_BASIS_VALUES} or None, "
                f"got {self.basis!r}"
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


def combined_basis(inputs: Sequence[Figure]) -> Basis:
    """Derive a combined ``basis`` from a sequence of input Figures (D-58).

    Weakest-wins, mirroring ``combined_confidence`` — a total containing one
    ``modelling_assumption`` input reports ``modelling_assumption``, never a
    stronger tier. Ordering, weakest to strongest: ``modelling_assumption``,
    ``estimated``, ``sourced``.

    **Landmine (D-59), stated explicitly:** ``combined_confidence`` above
    returns ``"validated"`` for an empty sequence — correct for its own use,
    and a trap if copied here. ``combined_basis`` does the opposite: an
    input list containing no basis-carrying Figure (either because it is
    empty, or because every Figure in it has ``basis=None`` — the
    incentive-side default) raises ``ValueError`` rather than silently
    defaulting to ``"sourced"`` or any other value. A cost total that could
    report ``sourced`` while its inputs are unlabelled is the same class of
    dishonesty as a modelling assumption wearing a ``validated`` tier.
    """
    bases = [figure.basis for figure in inputs if figure.basis is not None]
    if not bases:
        raise ValueError(
            "combined_basis() received no basis-carrying input (D-59) — an "
            "empty sequence, or a sequence whose members all have "
            "basis=None, must raise rather than default to a fallback "
            "value; unlike combined_confidence's empty-sequence default, "
            "combined_basis never returns 'sourced' (or any value) here"
        )
    return min(bases, key=lambda basis: _BASIS_WEAKNESS_ORDER[basis])

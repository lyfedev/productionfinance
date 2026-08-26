"""D-58/D-59: the `basis` provenance axis on `Figure`, `combined_basis`'s
weakest-wins arithmetic, and the empty-sequence refusal.

`combined_confidence` (Phase 2) returns `"validated"` for an empty
sequence — correct for its own use, and a landmine if copied.
`combined_basis` (Phase 4) must never mirror that default: an empty
sequence, or a sequence whose members all carry `basis=None`, must raise
`ValueError` rather than silently reporting `"sourced"` or any other
value.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from engine.figure import Basis, Figure, combined_basis
from engine.figure_serialize import figure_to_dict


def _figure(
    *,
    value: Decimal = Decimal("100"),
    basis: Basis | None = None,
    confidence: str = "researched",
    inputs: tuple[Figure, ...] = (),
) -> Figure:
    return Figure(
        value=value,
        unit="USD",
        label="test figure",
        derivation=("a test derivation line",),
        inputs=inputs,
        source_url=None,
        date_checked=date(2026, 1, 1),
        confidence=confidence,
        live_fetched_this_run=False,
        basis=basis,
    )


# ---------------------------------------------------------------------------
# Basis exists on Figure and defaults to None
# ---------------------------------------------------------------------------


def test_basis_field_defaults_to_none():
    figure = _figure()
    assert figure.basis is None


def test_figure_rejects_illegal_basis_value():
    with pytest.raises(ValueError):
        _figure(basis="fabricated")  # type: ignore[arg-type]


@pytest.mark.parametrize("basis", ["sourced", "estimated", "modelling_assumption"])
def test_figure_accepts_every_legal_basis_value(basis: Basis):
    figure = _figure(basis=basis)
    assert figure.basis == basis


def test_with_step_preserves_basis():
    figure = _figure(basis="estimated")
    stepped = figure.with_step("a derivation step")
    assert stepped.basis == "estimated"


# ---------------------------------------------------------------------------
# combined_basis — weakest-wins
# ---------------------------------------------------------------------------


def test_combined_basis_weakest_wins_across_every_pair():
    sourced = _figure(basis="sourced")
    estimated = _figure(basis="estimated")
    assumption = _figure(basis="modelling_assumption")

    assert combined_basis([sourced, estimated]) == "estimated"
    assert combined_basis([sourced, assumption]) == "modelling_assumption"
    assert combined_basis([estimated, assumption]) == "modelling_assumption"
    assert combined_basis([sourced, sourced]) == "sourced"
    assert combined_basis([sourced, estimated, assumption]) == "modelling_assumption"


def test_combined_basis_over_mixed_sequence_returns_the_single_weak_member():
    mixed = [_figure(basis="sourced"), _figure(basis="sourced"), _figure(basis="modelling_assumption")]
    assert combined_basis(mixed) == "modelling_assumption"


def test_combined_basis_ignores_none_basis_inputs_when_at_least_one_is_labelled():
    # A None-basis input (the incentive side's default — see D-58's
    # docstring on Figure) is excluded from the weakest-wins comparison
    # rather than treated as an invalid member, as long as at least one
    # input in the sequence actually carries a basis.
    labelled = _figure(basis="estimated")
    unlabelled = _figure(basis=None)
    assert combined_basis([labelled, unlabelled]) == "estimated"


# ---------------------------------------------------------------------------
# D-59 — the empty-sequence / all-None landmine, named explicitly
# ---------------------------------------------------------------------------


def test_combined_basis_on_empty_sequence_raises_value_error():
    with pytest.raises(ValueError):
        combined_basis([])


def test_combined_basis_on_all_none_basis_sequence_raises_value_error():
    with pytest.raises(ValueError):
        combined_basis([_figure(basis=None), _figure(basis=None)])


def test_combined_basis_does_not_mirror_combined_confidence_empty_default():
    """The exact regression D-59 names in advance: `combined_confidence`
    returns `"validated"` for an empty sequence. `combined_basis` must
    NEVER do the analogous thing (return `"sourced"`, or any other value)
    for an empty or all-None sequence — it must raise instead."""
    from engine.figure import combined_confidence

    assert combined_confidence([]) == "validated"
    with pytest.raises(ValueError):
        combined_basis([])


# ---------------------------------------------------------------------------
# figure_to_dict carries `basis` at every level of the recursive tree
# ---------------------------------------------------------------------------


def test_figure_to_dict_carries_basis_key_at_every_level():
    leaf = _figure(basis="sourced", value=Decimal("10"))
    branch = _figure(basis="estimated", value=Decimal("20"), inputs=(leaf,))
    root = _figure(basis="modelling_assumption", value=Decimal("30"), inputs=(branch,))

    as_dict = figure_to_dict(root)
    assert as_dict["basis"] == "modelling_assumption"
    assert as_dict["inputs"][0]["basis"] == "estimated"
    assert as_dict["inputs"][0]["inputs"][0]["basis"] == "sourced"


def test_figure_to_dict_serializes_none_basis_as_null_for_incentive_side_figures():
    """Every pre-Phase-4 incentive-side Figure construction site omits
    `basis` — it must serialize as JSON `null`, never be silently dropped
    from the dict or defaulted to a legal value."""
    figure = _figure(basis=None)
    as_dict = figure_to_dict(figure)
    assert "basis" in as_dict
    assert as_dict["basis"] is None

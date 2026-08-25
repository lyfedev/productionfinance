"""Stage 3 (qualifying-base) tests: the four base-definition types, the
`custom` escape hatch, excluded-line-item order-independence, and the
minimum-spend cliff (INC-01, INC-09).

Fixture loading follows the same sorted-glob, safe-loader,
fail-loud-on-empty-glob discipline established in
`tests/test_validation_pair_fixtures.py`.
"""

from __future__ import annotations

from decimal import Decimal
from glob import glob

import pytest
import yaml

from engine.figure import Figure
from engine.models import (
    Audit,
    BaseDefinition,
    Caps,
    Money,
    PayoutLag,
    PerPersonCeiling,
    Programme,
    RateStructure,
    Timing,
    TransferDiscount,
    Validation,
    load_ruleset,
)
from engine.qualifying_base import CORE_EXPENDITURE_LABEL, SpendBreakdown, compute_qualifying_base

FIXTURE_DIR = "tests/fixtures/jurisdictions"
BASEDEFS_FIXTURE = f"{FIXTURE_DIR}/synthetic-basedefs.yaml"
MINCLIFF_FIXTURE = f"{FIXTURE_DIR}/synthetic-mincliff.yaml"

CURATED_DIR = "jurisdictions"

# Sorted glob: parametrization/iteration order is deterministic across runs,
# on any OS, independent of filesystem directory-listing order.
FIXTURE_PATHS = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))
CURATED_PATHS = sorted(glob(f"{CURATED_DIR}/*.yaml"))

# A test iterating an empty collection reports a vacuous green — fail
# collection itself rather than let that happen silently (T-01-15 discipline,
# carried forward from tests/test_validation_pair_fixtures.py).
if not FIXTURE_PATHS:
    raise RuntimeError(
        f"No fixture files found under {FIXTURE_DIR}/*.yaml — an empty "
        "synthetic-fixture set must fail loudly, not report a vacuous green."
    )
if not CURATED_PATHS:
    raise RuntimeError(
        f"No curated rule files found under {CURATED_DIR}/*.yaml — an empty "
        "curated-jurisdiction set must fail loudly, not report a vacuous green."
    )


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _programme_by_id(path: str, programme_id: str) -> Programme:
    ruleset = load_ruleset(path)
    for programme in ruleset.programmes:
        if programme.id == programme_id:
            return programme
    raise AssertionError(f"{path}: no programme with id {programme_id!r}")


def _make_programme(
    base_definition: BaseDefinition,
    *,
    programme_id: str = "synthetic-test-programme",
    name: str = "Synthetic Test Programme",
    minimum_spend: Money | None = None,
) -> Programme:
    """Build a minimal, valid Programme for tests that need a specific
    base_definition/minimum_spend combination not covered by the committed
    YAML fixtures. Every other required field is filled with an inert,
    illustrative default."""
    return Programme(
        id=programme_id,
        name=name,
        mechanism="refundable",
        taxable=False,
        corporation_tax_rate=None,
        base_definition=base_definition,
        per_person_ceiling=PerPersonCeiling(applies=False),
        rate_structure=RateStructure(type="flat", base_rate=Decimal("0.25")),
        minimum_spend=minimum_spend,
        caps=Caps(),
        audit=Audit(mandatory=False),
        timing=Timing(
            terms_lock_at="application",
            payout_lag=PayoutLag(
                description="synthetic test programme — not a real payout schedule"
            ),
        ),
        transfer_discount=TransferDiscount(applies=False),
        validation=Validation(validated=False),
    )


# The one shared budget the plan's <behavior> section specifies: $10,000,000
# total, $6,000,000 labour, $4,000,000 paid to local hires. core_expenditure
# is set equal to total_spend (no cost-localisation split exists yet, D-02).
SHARED_BUDGET = SpendBreakdown(
    total_spend=Decimal("10000000"),
    labour_spend=Decimal("6000000"),
    local_hires_spend=Decimal("4000000"),
    core_expenditure=Decimal("10000000"),
)


def test_base_definition_types():
    """One identical budget yields four different, individually-correct
    qualifying bases — a dispatch bug routing every type to the same
    handler fails this test."""
    total = compute_qualifying_base(
        _programme_by_id(BASEDEFS_FIXTURE, "basedef-total-qualified-spend"), SHARED_BUDGET
    )
    labour = compute_qualifying_base(
        _programme_by_id(BASEDEFS_FIXTURE, "basedef-labour-only"), SHARED_BUDGET
    )
    local_hires = compute_qualifying_base(
        _programme_by_id(BASEDEFS_FIXTURE, "basedef-local-hires-only"), SHARED_BUDGET
    )
    lesser_of = compute_qualifying_base(
        _programme_by_id(BASEDEFS_FIXTURE, "basedef-lesser-of"), SHARED_BUDGET
    )

    assert total.value == Decimal("10000000")
    assert labour.value == Decimal("6000000")
    assert local_hires.value == Decimal("4000000")
    assert lesser_of.value == Decimal("8000000")

    values = {total.value, labour.value, local_hires.value, lesser_of.value}
    assert len(values) == 4, (
        f"expected four pairwise-distinct qualifying bases, got {values} — a "
        "dispatch bug routing every type to the same handler would collapse this"
    )

    for figure in (total, labour, local_hires, lesser_of):
        assert base_type_name(figure) in figure.derivation[0]
        assert any(inp.label == CORE_EXPENDITURE_LABEL for inp in figure.inputs), (
            f"{figure.label}: missing the '{CORE_EXPENDITURE_LABEL}' inputs edge"
        )


def base_type_name(figure: Figure) -> str:
    """Extract the base_definition.type token this figure's derivation line
    should name — derived from the first derivation line's own convention
    ('base type: <TYPE> — ...') rather than hardcoded per call site."""
    first_line = figure.derivation[0]
    assert first_line.startswith("base type: "), first_line
    return first_line.split("base type: ", 1)[1].split(" —", 1)[0]


def test_custom_handler_prices_through_registry():
    """The `custom` escape hatch, referencing an identifier present in
    HANDLER_REGISTRY, prices correctly rather than raising."""
    figure = compute_qualifying_base(
        _programme_by_id(BASEDEFS_FIXTURE, "basedef-custom"), SHARED_BUDGET
    )
    # labour_plus_quarter_local_hires: 6,000,000 + 0.25 * 4,000,000 = 7,000,000
    assert figure.value == Decimal("7000000")
    assert "custom" in figure.derivation[0]
    assert "labour_plus_quarter_local_hires" in figure.derivation[0]


def test_custom_handler_id_unknown_raises_keyerror():
    """The same programme shape with an identifier absent from the registry
    raises KeyError naming it — never a silent fallback to a default base."""
    base_definition = BaseDefinition(
        type="custom",
        custom_handler_id="does-not-exist-in-registry",
    )
    programme = _make_programme(base_definition)

    with pytest.raises(KeyError) as excinfo:
        compute_qualifying_base(programme, SHARED_BUDGET)

    assert "does-not-exist-in-registry" in str(excinfo.value)


def test_equal_candidates_lesser_of_returns_value_once():
    """When the two lesser-of candidates are exactly equal, the result is
    that value, returned once and never doubled, with a derivation line
    stating the two candidates were equal."""
    base_definition = BaseDefinition(
        type="lesser_of_pct_core_or_actual_local",
        pct_core_cap=Decimal("1.00"),
    )
    programme = _make_programme(base_definition)
    spend = SpendBreakdown(
        total_spend=Decimal("8000000"),
        labour_spend=Decimal("8000000"),
        local_hires_spend=Decimal("8000000"),
        core_expenditure=Decimal("8000000"),
    )

    figure = compute_qualifying_base(programme, spend)

    assert figure.value == Decimal("8000000")
    assert "equal" in figure.derivation[0]


@pytest.mark.parametrize(
    "base_definition_kwargs",
    [
        {"type": "total_qualified_spend"},
        {"type": "labour_only"},
        {"type": "local_hires_only"},
        {"type": "lesser_of_pct_core_or_actual_local", "pct_core_cap": Decimal("0.80")},
        {"type": "custom", "custom_handler_id": "labour_plus_quarter_local_hires"},
    ],
    ids=[
        "total_qualified_spend",
        "labour_only",
        "local_hires_only",
        "lesser_of_pct_core_or_actual_local",
        "custom",
    ],
)
def test_zero_budget_yields_zero_base_with_derivation(base_definition_kwargs):
    """A qualified spend of exactly Decimal('0') yields a qualifying base of
    exactly Decimal('0') under every one of the four types (plus custom),
    each with a non-empty derivation naming its type."""
    base_definition = BaseDefinition(**base_definition_kwargs)
    programme = _make_programme(base_definition)
    zero_spend = SpendBreakdown(
        total_spend=Decimal("0"),
        labour_spend=Decimal("0"),
        local_hires_spend=Decimal("0"),
        core_expenditure=Decimal("0"),
    )

    figure = compute_qualifying_base(programme, zero_spend)

    assert figure.value == Decimal("0")
    assert len(figure.derivation) > 0
    assert base_definition_kwargs["type"] in figure.derivation[0]


def test_excluded_line_items_are_order_independent():
    """Excluded line items are applied in the order the rule file declares
    them, and re-ordering the excluded_line_items list without changing its
    membership does not change the resulting base."""
    spend = SpendBreakdown(
        total_spend=Decimal("1000000"),
        labour_spend=Decimal("1000000"),
        local_hires_spend=Decimal("1000000"),
        core_expenditure=Decimal("1000000"),
        line_items={
            "per_diem_overage": Decimal("50000"),
            "atl_over_cap": Decimal("30000"),
        },
    )

    forward = _make_programme(
        BaseDefinition(
            type="total_qualified_spend",
            excluded_line_items=["per_diem_overage", "atl_over_cap"],
        )
    )
    reversed_order = _make_programme(
        BaseDefinition(
            type="total_qualified_spend",
            excluded_line_items=["atl_over_cap", "per_diem_overage"],
        )
    )

    forward_figure = compute_qualifying_base(forward, spend)
    reversed_figure = compute_qualifying_base(reversed_order, spend)

    assert forward_figure.value == Decimal("920000")
    assert reversed_figure.value == Decimal("920000")
    assert forward_figure.value == reversed_figure.value


def test_excluded_line_item_unknown_name_raises_keyerror():
    """A base_definition.excluded_line_items entry not present in
    SpendBreakdown.line_items raises KeyError rather than silently treating
    the missing component as zero."""
    spend = SpendBreakdown(
        total_spend=Decimal("1000000"),
        labour_spend=Decimal("1000000"),
        local_hires_spend=Decimal("1000000"),
        core_expenditure=Decimal("1000000"),
    )
    programme = _make_programme(
        BaseDefinition(type="total_qualified_spend", excluded_line_items=["not_declared"])
    )

    with pytest.raises(KeyError):
        compute_qualifying_base(programme, spend)


def test_directory_hygiene_fixture_status_vs_curated_status():
    """A reviewer must never be able to mistake a test fixture for curated
    government data: every file under tests/fixtures/jurisdictions/ declares
    jurisdiction.status synthetic_fixture, and no file under jurisdictions/
    does."""
    for path in FIXTURE_PATHS:
        data = _load(path)
        status = data["jurisdiction"]["status"]
        assert status == "synthetic_fixture", (
            f"{path}: expected jurisdiction.status 'synthetic_fixture', got {status!r} "
            "— every file under tests/fixtures/jurisdictions/ must declare this status"
        )

    for path in CURATED_PATHS:
        data = _load(path)
        status = data["jurisdiction"]["status"]
        assert status != "synthetic_fixture", (
            f"{path}: jurisdiction.status is 'synthetic_fixture' but this file is "
            "under jurisdictions/ (curated data) — a synthetic fixture must never "
            "be filed here"
        )


# --- Task 2: minimum-spend thresholds as tested cliffs, never ramps -------


@pytest.mark.parametrize(
    ("raw_spend", "expected_base"),
    [
        (Decimal("99999"), Decimal("0")),
        (Decimal("100000"), Decimal("100000")),
        (Decimal("100001"), Decimal("100001")),
    ],
    ids=["threshold_minus_one", "at_threshold", "threshold_plus_one"],
)
def test_minimum_spend_cliff(raw_spend, expected_base):
    """A minimum-spend threshold is a step function: threshold minus one
    dollar gives exactly Decimal('0'), threshold gives the full base,
    threshold plus one dollar gives the full base — never a value between
    zero and the full base. The equality assertion below would fail for any
    proportionally-reduced non-zero value, not only for a fully-ramped one."""
    programme = _programme_by_id(MINCLIFF_FIXTURE, "with-minimum-spend")
    spend = SpendBreakdown.from_total(raw_spend)

    figure = compute_qualifying_base(programme, spend)

    assert figure.value == expected_base

    if expected_base == Decimal("0"):
        assert "100000" in figure.derivation[-1]


def test_minimum_spend_not_declared_still_emits_derivation():
    """A programme declaring no minimum spend still emits a derivation line
    stating that no minimum-spend threshold is declared, so silence is never
    mistaken for 'not considered'."""
    with_threshold = _programme_by_id(MINCLIFF_FIXTURE, "with-minimum-spend")
    without_threshold = _programme_by_id(MINCLIFF_FIXTURE, "without-minimum-spend")

    met_figure = compute_qualifying_base(
        with_threshold, SpendBreakdown.from_total(Decimal("500000"))
    )
    undeclared_figure = compute_qualifying_base(
        without_threshold, SpendBreakdown.from_total(Decimal("500000"))
    )

    assert len(undeclared_figure.derivation) > 0
    assert "no minimum-spend threshold is declared" in undeclared_figure.derivation[-1]
    assert len(undeclared_figure.derivation) >= len(met_figure.derivation)


def test_minimum_spend_evaluated_against_base_not_total():
    """The cliff is evaluated against the qualifying base produced by the
    base-definition dispatch, not against the raw input total — a labour-only
    programme reducing $110,000 of total spend to $90,000 of labour falls
    below a $100,000 threshold even though the total spend does not."""
    programme = _make_programme(
        BaseDefinition(type="labour_only"),
        minimum_spend=Money(value=Decimal("100000"), currency="USD"),
    )
    spend = SpendBreakdown(
        total_spend=Decimal("110000"),
        labour_spend=Decimal("90000"),
        local_hires_spend=Decimal("110000"),
        core_expenditure=Decimal("110000"),
    )

    figure = compute_qualifying_base(programme, spend)

    assert figure.value == Decimal("0")

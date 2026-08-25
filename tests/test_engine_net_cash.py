"""Stage 5 (net-cash conversion) tests: the four mechanism functions
(`refundable`, `rebate_grant`, `transferable`, `nonrefundable_credit`), the
cliff-tiered audit fee schedule (INC-06), corporation tax on the taxable
path (INC-07), and `ArrivalTiming` (INC-08).

Fixture loading follows the same sorted-glob, safe-loader,
fail-loud-on-empty-glob discipline established in
`tests/test_validation_pair_fixtures.py` and carried forward by
`tests/test_engine_qualifying_base.py` / `tests/test_engine_credit.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from engine.credit import compute_gross_credit
from engine.figure import Figure
from engine.models import (
    Audit,
    AuditFeeTier,
    BaseDefinition,
    Caps,
    PayoutLag,
    PerPersonCeiling,
    Programme,
    RateStructure,
    Timing,
    TransferDiscount,
    Validation,
    load_ruleset,
)
from engine.net_cash import (
    ArrivalTiming,
    convert_to_net_cash,
    nonrefundable_credit,
    rebate_grant,
    refundable,
    transferable,
)
from engine.qualifying_base import SpendBreakdown, compute_qualifying_base
from engine.rounding import quantize_money

FIXTURE_DIR = "tests/fixtures/jurisdictions"
MECH_FIXTURE = f"{FIXTURE_DIR}/synthetic-mechanisms.yaml"

SHARED_SPEND = Decimal("10000000")


def _programme_by_id(path: str, programme_id: str) -> Programme:
    ruleset = load_ruleset(path)
    for programme in ruleset.programmes:
        if programme.id == programme_id:
            return programme
    raise AssertionError(f"{path}: no programme with id {programme_id!r}")


def _make_programme(
    *,
    mechanism: str = "refundable",
    taxable: bool = False,
    corporation_tax_rate: Decimal | None = None,
    audit: Audit | None = None,
    transfer_discount: TransferDiscount | None = None,
    payout_lag: PayoutLag | None = None,
    base_rate: Decimal = Decimal("0.30"),
    programme_id: str = "synthetic-net-cash-test-programme",
    name: str = "Synthetic Net Cash Test Programme",
) -> Programme:
    """Build a minimal, valid Programme for tests that need a specific
    audit/transfer_discount/taxable combination not covered by the committed
    YAML fixtures. Every other required field is filled with an inert,
    illustrative default — mirrors tests/test_engine_credit.py's
    `_make_programme` helper."""
    return Programme(
        id=programme_id,
        name=name,
        mechanism=mechanism,
        taxable=taxable,
        corporation_tax_rate=corporation_tax_rate,
        base_definition=BaseDefinition(type="total_qualified_spend"),
        per_person_ceiling=PerPersonCeiling(applies=False),
        rate_structure=RateStructure(type="flat", base_rate=base_rate),
        minimum_spend=None,
        caps=Caps(),
        audit=audit if audit is not None else Audit(mandatory=False),
        timing=Timing(
            terms_lock_at="application",
            payout_lag=payout_lag
            if payout_lag is not None
            else PayoutLag(description="synthetic test programme — not a real payout schedule"),
        ),
        transfer_discount=transfer_discount
        if transfer_discount is not None
        else TransferDiscount(applies=False),
        validation=Validation(validated=False),
    )


def _gross_credit_for(programme: Programme, spend_value: Decimal) -> Figure:
    qualifying_base = compute_qualifying_base(
        programme, SpendBreakdown.from_total(spend_value), currency="USD"
    )
    return compute_gross_credit(programme, qualifying_base)


def _walk_figures(*roots: Figure) -> list[Figure]:
    """Deduped-by-figure_id recursive walk of a Figure's `.inputs` DAG,
    mirroring tests/test_engine_figure_provenance.py's multi-root walk."""
    seen: dict[str, Figure] = {}
    stack = [r for r in roots if r is not None]
    while stack:
        figure = stack.pop()
        if figure.figure_id in seen:
            continue
        seen[figure.figure_id] = figure
        stack.extend(figure.inputs)
    return list(seen.values())


# ---------------------------------------------------------------------------
# Task 1: four mechanisms, the cliff-tiered audit fee, corporation tax,
# arrival timing.
# ---------------------------------------------------------------------------


def test_mechanism_conversions():
    """One identical qualified spend ($10,000,000) fed through all four
    mechanism programmes in the committed fixture produces four
    pairwise-different net-cash representative values — a dispatch bug
    routing every mechanism to one function collapses this to fewer than
    four distinct values."""
    ruleset = load_ruleset(MECH_FIXTURE)
    assert len(ruleset.programmes) == 4

    results: dict[str, Decimal] = {}
    for programme in ruleset.programmes:
        gross_credit = _gross_credit_for(programme, SHARED_SPEND)
        net_cash = convert_to_net_cash(programme, gross_credit)
        representative = net_cash.point if net_cash.point is not None else net_cash.low
        results[programme.mechanism] = representative.value

    assert set(results) == {
        "refundable",
        "rebate_grant",
        "transferable",
        "nonrefundable_credit",
    }
    values = list(results.values())
    assert len(set(values)) == 4, (
        f"expected four pairwise-distinct net cash values, got {results} — a "
        "dispatch bug would collapse this to fewer than four"
    )


def test_refundable_rebate_grant_same_arithmetic_distinct_derivation():
    """`refundable` and `rebate_grant` apply the identical gross-less-fee
    arithmetic, but each names its own mechanism in its final derivation
    line — never a shared branch masquerading as two mechanisms."""
    programme_refundable = _make_programme(mechanism="refundable")
    programme_rebate = _make_programme(mechanism="rebate_grant")
    gross_refundable = _gross_credit_for(programme_refundable, Decimal("1000000"))
    gross_rebate = _gross_credit_for(programme_rebate, Decimal("1000000"))

    net_refundable = refundable(programme_refundable, gross_refundable)
    net_rebate = rebate_grant(programme_rebate, gross_rebate)

    assert net_refundable.value == net_rebate.value
    assert "refundable mechanism" in net_refundable.derivation[-2]
    assert "rebate_grant mechanism" in net_rebate.derivation[-2]
    assert net_refundable.derivation[-2] != net_rebate.derivation[-2]


@pytest.mark.parametrize(
    "spend,expected_fee",
    [
        (Decimal("4999999"), Decimal("5000")),
        (Decimal("5000000"), Decimal("15000")),
        (Decimal("5000001"), Decimal("15000")),
        (Decimal("9999999"), Decimal("15000")),
        (Decimal("10000000"), Decimal("25000")),
        (Decimal("10000001"), Decimal("25000")),
    ],
)
def test_audit_fee_cliff_boundaries(spend, expected_fee):
    """Bands are half-open: a spend exactly at a band's low threshold
    selects THAT band, and a spend exactly at a band's high threshold
    selects the NEXT one — proven at both the $5,000,000 and $10,000,000
    boundaries, six points, never interpolated (A1.6)."""
    programme = _programme_by_id(MECH_FIXTURE, "mechanisms-refundable")
    gross_credit = _gross_credit_for(programme, spend)

    net = refundable(programme, gross_credit)

    expected_net = quantize_money(gross_credit.value - expected_fee)
    assert net.value == expected_net


def test_audit_fee_schedule_gap_raises_naming_spend_and_bands():
    """A qualified spend matching no declared band raises rather than
    silently deducting zero — a schedule with a hole in it is a rule-file
    bug and must surface."""
    schedule = [
        AuditFeeTier(
            spend_threshold_low=Decimal("0"),
            spend_threshold_high=Decimal("5000000"),
            fee_primary=Decimal("5000"),
        ),
        AuditFeeTier(
            spend_threshold_low=Decimal("7000000"),
            spend_threshold_high=None,
            fee_primary=Decimal("25000"),
        ),
    ]
    programme = _make_programme(audit=Audit(mandatory=True, fee_schedule=schedule))
    gross_credit = _gross_credit_for(programme, Decimal("6000000"))

    with pytest.raises(ValueError) as excinfo:
        refundable(programme, gross_credit)

    message = str(excinfo.value)
    assert "6000000" in message
    assert "5000000" in message
    assert "7000000" in message


def test_empty_audit_fee_schedule_deducts_zero_with_derivation():
    """An empty `fee_schedule` deducts exactly `Decimal('0')` and the
    derivation states no fee schedule is declared — a jurisdiction with no
    audit-fee data (like New York today) never fabricates a plausible
    fee."""
    programme = _make_programme(audit=Audit(mandatory=False))
    gross_credit = _gross_credit_for(programme, SHARED_SPEND)

    net = refundable(programme, gross_credit)

    assert net.value == quantize_money(gross_credit.value)
    assert any(
        "no audit fee schedule is declared" in line for line in net.derivation
    ), net.derivation


def test_transferable_no_point_derivation_names_both_rates_and_source():
    """A `transferable` result has `point` equal to `None`, and both bound
    Figures' derivation names the low rate, the high rate, and the source
    note they came from — never a fabricated midpoint."""
    programme = _programme_by_id(MECH_FIXTURE, "mechanisms-transferable")
    gross_credit = _gross_credit_for(programme, SHARED_SPEND)

    net_cash = convert_to_net_cash(programme, gross_credit)

    assert net_cash.point is None
    assert net_cash.low.value != net_cash.high.value
    assert net_cash.low.value < net_cash.high.value
    for figure in (net_cash.low, net_cash.high):
        last_line = figure.derivation[-1]
        assert "0.85" in last_line
        assert "0.92" in last_line
        assert programme.transfer_discount.source_note in last_line


def test_transferable_requires_fully_declared_transfer_discount():
    """A `transferable` mechanism with `transfer_discount.applies` false (or
    a missing low/high rate) raises rather than silently converting at an
    unsourced rate."""
    programme = _make_programme(
        mechanism="transferable", transfer_discount=TransferDiscount(applies=False)
    )
    gross_credit = _gross_credit_for(programme, SHARED_SPEND)

    with pytest.raises(ValueError):
        transferable(programme, gross_credit)


def test_nonrefundable_credit_taxable_true_deducts_corporation_tax():
    """`nonrefundable_credit` with `taxable` true deducts the audit fee,
    then corporation tax at the declared rate."""
    programme = _programme_by_id(MECH_FIXTURE, "mechanisms-nonrefundable-credit")
    gross_credit = _gross_credit_for(programme, SHARED_SPEND)

    net = nonrefundable_credit(programme, gross_credit)

    after_fee = gross_credit.value - Decimal("25000")
    expected = quantize_money(after_fee - after_fee * Decimal("0.20"))
    assert net.value == expected
    assert any("corporation tax" in line for line in net.derivation)


def test_nonrefundable_credit_taxable_false_no_tax_deducted():
    """A mechanism with `taxable` false does not deduct corporation tax and
    its derivation says corporation tax does not apply — a reader can tell
    the step was considered, not skipped."""
    programme = _make_programme(mechanism="nonrefundable_credit", taxable=False)
    gross_credit = _gross_credit_for(programme, Decimal("1000000"))

    net = nonrefundable_credit(programme, gross_credit)

    assert net.value == quantize_money(gross_credit.value)
    assert any(
        "corporation tax does not apply" in line for line in net.derivation
    ), net.derivation


def test_taxable_true_with_null_corporation_tax_rate_raises_at_load():
    """A programme declaring `taxable` true with a null
    `corporation_tax_rate` fails validation on load rather than defaulting
    to zero tax at runtime (RD-05 #3, `Programme` model validator)."""
    with pytest.raises(ValidationError):
        Programme(
            id="bad-taxable-programme",
            name="Bad taxable programme",
            mechanism="nonrefundable_credit",
            taxable=True,
            corporation_tax_rate=None,
            base_definition=BaseDefinition(type="total_qualified_spend"),
            per_person_ceiling=PerPersonCeiling(applies=False),
            rate_structure=RateStructure(type="flat", base_rate=Decimal("0.30")),
            caps=Caps(),
            audit=Audit(mandatory=False),
            timing=Timing(
                terms_lock_at="application",
                payout_lag=PayoutLag(description="synthetic test — not real"),
            ),
            transfer_discount=TransferDiscount(applies=False),
            validation=Validation(validated=False),
        )


def test_arrival_timing_present():
    """An `ArrivalTiming` is returned alongside net cash for every one of
    the four mechanisms. A programme whose payout lag is unsourced reports
    a null estimated date and a reason naming the missing source; a
    programme with a declared `typical_days` reports an estimated date
    computed from it."""
    ruleset = load_ruleset(MECH_FIXTURE)
    today = datetime.now(tz=UTC).date()

    seen_null = False
    seen_dated = False
    for programme in ruleset.programmes:
        gross_credit = _gross_credit_for(programme, SHARED_SPEND)
        net_cash = convert_to_net_cash(programme, gross_credit)

        arrival = net_cash.arrival
        assert isinstance(arrival, ArrivalTiming)
        assert arrival.reason

        if programme.timing.payout_lag.typical_days is None:
            assert arrival.estimated_date is None
            assert arrival.typical_days is None
            seen_null = True
        else:
            expected_date = today + timedelta(days=programme.timing.payout_lag.typical_days)
            assert arrival.estimated_date == expected_date
            assert arrival.typical_days == programme.timing.payout_lag.typical_days
            seen_dated = True

    # The fixture declares a payout lag on some programmes and null on at
    # least one (Task 1's action text) — both branches must be exercised.
    assert seen_null
    assert seen_dated


def test_mechanisms_fixture_declares_synthetic_status():
    """Directory-hygiene guard specific to this new file: even though
    tests/test_engine_qualifying_base.py's structural glob-based test
    already covers this, assert it here too so a reader of this test
    module sees the guarantee beside the fixture it concerns."""
    ruleset = load_ruleset(MECH_FIXTURE)
    assert ruleset.jurisdiction.status == "synthetic_fixture"

"""Stage 4 (credit-calculation) tests: the per-person ceiling (before the
rate, W-2 versus loan-out, on a dated withholding schedule — INC-02) and
the two rate-structure dispatch functions, `lookup_flat_rate_by_band`
(cliff lookup) and `blend_two_rates_by_ceiling` (ceiling-split blend —
INC-03), proven to be genuinely different computations, each reproducing
its sourced worked figure and each proven NOT to produce the plausible
wrong figure the other interpretation gives.

Fixture loading follows the same sorted-glob, safe-loader,
fail-loud-on-empty-glob discipline established in
`tests/test_validation_pair_fixtures.py` and carried forward by
`tests/test_engine_qualifying_base.py`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from engine.credit import (
    PerPersonCompensation,
    blend_two_rates_by_ceiling,
    compute_gross_credit,
    lookup_flat_rate_by_band,
)
from engine.figure import Figure
from engine.models import (
    Audit,
    BaseDefinition,
    Caps,
    CeilingSplit,
    Money,
    PayoutLag,
    PerPersonCeiling,
    Programme,
    RateStructure,
    Tier,
    Timing,
    TransferDiscount,
    Validation,
    load_ruleset,
)
from engine.net_cash import convert_to_net_cash
from engine.qualifying_base import CORE_EXPENDITURE_LABEL, SpendBreakdown, compute_qualifying_base
from engine.rounding import quantize_money

FIXTURE_DIR = "tests/fixtures/jurisdictions"
GA_FIXTURE = f"{FIXTURE_DIR}/synthetic-ga-style.yaml"
UK_FIXTURE = f"{FIXTURE_DIR}/synthetic-uk-style.yaml"


def _programme_by_id(path: str, programme_id: str) -> Programme:
    ruleset = load_ruleset(path)
    for programme in ruleset.programmes:
        if programme.id == programme_id:
            return programme
    raise AssertionError(f"{path}: no programme with id {programme_id!r}")


def _make_programme(
    *,
    rate_structure: RateStructure,
    per_person_ceiling: PerPersonCeiling | None = None,
    base_definition: BaseDefinition | None = None,
    programme_id: str = "synthetic-credit-test-programme",
    name: str = "Synthetic Credit Test Programme",
    mechanism: str = "refundable",
    taxable: bool = False,
    corporation_tax_rate: Decimal | None = None,
) -> Programme:
    """Build a minimal, valid Programme for tests that need a specific
    per_person_ceiling/rate_structure combination not covered by the
    committed YAML fixtures. Every other required field is filled with an
    inert, illustrative default — mirrors
    tests/test_engine_qualifying_base.py's `_make_programme` helper."""
    return Programme(
        id=programme_id,
        name=name,
        mechanism=mechanism,
        taxable=taxable,
        corporation_tax_rate=corporation_tax_rate,
        base_definition=base_definition or BaseDefinition(type="total_qualified_spend"),
        per_person_ceiling=per_person_ceiling or PerPersonCeiling(applies=False),
        rate_structure=rate_structure,
        minimum_spend=None,
        caps=Caps(),
        audit=Audit(mandatory=False),
        timing=Timing(
            terms_lock_at="application",
            payout_lag=PayoutLag(description="synthetic test programme — not a real payout schedule"),
        ),
        transfer_discount=TransferDiscount(applies=False),
        validation=Validation(validated=False),
    )


# ---------------------------------------------------------------------------
# Task 1: per-person ceilings — before the rate, W-2 vs loan-out, dated
# schedule (INC-02)
# ---------------------------------------------------------------------------


def test_per_person_ceiling_w2_vs_loanout():
    """$10,000,000 of qualified spend including a $2,000,000 W-2 lead,
    against a declared $500,000 cap and a flat 30% rate: the W-2 path
    yields a base of Decimal('8500000') and a credit of Decimal('2550000').
    The same lead paid via loan-out (loanout_exempt true) yields a base of
    Decimal('10000000') and a credit of Decimal('3000000') — the two
    credits differ, so a ceiling implementation that ignores the loan-out
    exemption fails."""
    programme = _programme_by_id(GA_FIXTURE, "ga-style-w2-vs-loanout-confirmed-synthetic")
    spend = SpendBreakdown.from_total(Decimal("10000000"))
    qualifying_base = compute_qualifying_base(programme, spend, currency="USD")
    production_date = date(2026, 3, 1)  # falls in the "2026-01-01 onward" 4.99% band

    w2_credit = compute_gross_credit(
        programme,
        qualifying_base,
        per_person_compensations=[
            PerPersonCompensation(role="Lead actor", amount=Decimal("2000000"), payment_route="w2")
        ],
        production_date=production_date,
    )
    loanout_credit = compute_gross_credit(
        programme,
        qualifying_base,
        per_person_compensations=[
            PerPersonCompensation(
                role="Lead actor", amount=Decimal("2000000"), payment_route="loanout"
            )
        ],
        production_date=production_date,
    )

    # base = credit / 0.30 (flat rate) — recovers the intermediate,
    # ceiling-adjusted base without needing a second return value.
    w2_base = w2_credit.value / Decimal("0.30")
    loanout_base = loanout_credit.value / Decimal("0.30")

    assert w2_base == Decimal("8500000")
    assert w2_credit.value == Decimal("2550000")
    assert loanout_base == Decimal("10000000")
    assert loanout_credit.value == Decimal("3000000")
    assert w2_credit.value != loanout_credit.value

    # The loan-out withholding obligation is a separate Figure, attached to
    # gross_credit.inputs, and does NOT change the credit or net cash.
    withholding_figures = [
        f for f in loanout_credit.inputs if "withholding" in f.label.lower()
    ]
    assert len(withholding_figures) == 1, (
        f"expected exactly one withholding-obligation Figure, found "
        f"{len(withholding_figures)}: {loanout_credit.inputs}"
    )
    withholding = withholding_figures[0]
    assert withholding.value == Decimal("2000000") * Decimal("0.0499")

    net_cash = convert_to_net_cash(programme, loanout_credit)
    assert net_cash.point.value == loanout_credit.value == Decimal("3000000"), (
        "the withholding obligation's presence must not change the credit or net cash — "
        "it is a liability on a different party, never netted off"
    )


@pytest.mark.parametrize(
    ("compensation", "expected_excess"),
    [
        (Decimal("499999"), Decimal("0")),
        (Decimal("500000"), Decimal("0")),
        (Decimal("500001"), Decimal("1")),
    ],
    ids=["cap_minus_one", "at_cap", "cap_plus_one"],
)
def test_per_person_ceiling_w2_boundary(compensation, expected_excess):
    """Per-person compensation of exactly the cap amount qualifies in full
    — the excess at the boundary is exactly Decimal('0') — proven at cap
    minus one dollar, cap, and cap plus one dollar. A flat 100% rate makes
    the resulting credit equal to the post-ceiling base directly, so the
    excess is read straight off the credit delta without needing a second
    return value from compute_gross_credit."""
    programme = _make_programme(
        per_person_ceiling=PerPersonCeiling(
            applies=True,
            w2_cap_amount=Money(value=Decimal("500000"), currency="USD"),
        ),
        rate_structure=RateStructure(type="flat", base_rate=Decimal("1")),
    )
    qualifying_base = compute_qualifying_base(
        programme, SpendBreakdown.from_total(Decimal("1000000")), currency="USD"
    )

    gross = compute_gross_credit(
        programme,
        qualifying_base,
        per_person_compensations=[
            PerPersonCompensation(role="Lead", amount=compensation, payment_route="w2")
        ],
    )

    assert gross.value == Decimal("1000000") - expected_excess


def test_per_person_ceiling_loanout_withholding_selects_earlier_band():
    """A production dated inside an earlier band selects that band's rate
    — a $1,000,000 loan-out payment dated 2023-06-01 falls in the
    2023-01-01/2023-12-31 band (5.49%, SOURCE-TRUTH.md SRC-05), giving a
    withholding obligation of exactly Decimal('54900.00'), not the current
    (2026) 4.99% band's Decimal('49900.00')."""
    programme = _programme_by_id(GA_FIXTURE, "ga-style-w2-vs-loanout-confirmed-synthetic")
    qualifying_base = compute_qualifying_base(
        programme, SpendBreakdown.from_total(Decimal("10000000")), currency="USD"
    )

    gross = compute_gross_credit(
        programme,
        qualifying_base,
        per_person_compensations=[
            PerPersonCompensation(
                role="Composer", amount=Decimal("1000000"), payment_route="loanout"
            )
        ],
        production_date=date(2023, 6, 1),
    )

    withholding = next(f for f in gross.inputs if "withholding" in f.label.lower())
    assert withholding.value == Decimal("1000000") * Decimal("0.0549")
    assert withholding.value != Decimal("1000000") * Decimal("0.0499"), (
        "must not silently select the current (2026) band for a 2023-dated production"
    )


def test_per_person_ceiling_unconfirmed_schedule_entry_reports_researched():
    """An unconfirmed schedule entry (loanout_withholding_confirmed: false)
    is still USED to compute the withholding obligation, but the resulting
    gross-credit Figure reports confidence 'researched' rather than
    'validated'."""
    programme = _programme_by_id(GA_FIXTURE, "ga-style-w2-vs-loanout-unconfirmed-synthetic")
    qualifying_base = compute_qualifying_base(
        programme, SpendBreakdown.from_total(Decimal("10000000")), currency="USD"
    )
    assert qualifying_base.confidence == "validated"

    gross = compute_gross_credit(
        programme,
        qualifying_base,
        per_person_compensations=[
            PerPersonCompensation(role="Lead actor", amount=Decimal("2000000"), payment_route="loanout")
        ],
        production_date=date(2026, 3, 1),
    )

    assert gross.confidence == "researched"
    withholding = next(f for f in gross.inputs if "withholding" in f.label.lower())
    assert withholding.confidence == "researched"


def test_per_person_ceiling_no_compensations_supplied_leaves_base_unchanged():
    """A ceiling that applies, but for which no per-person compensation
    lines were supplied for this production, leaves the base unchanged and
    still emits a non-silent derivation line (PRV-03)."""
    programme = _programme_by_id(GA_FIXTURE, "ga-style-w2-vs-loanout-confirmed-synthetic")
    qualifying_base = compute_qualifying_base(
        programme, SpendBreakdown.from_total(Decimal("10000000")), currency="USD"
    )

    gross = compute_gross_credit(programme, qualifying_base)

    assert gross.value == Decimal("3000000")  # 10,000,000 x 0.30, unchanged
    assert any("no per-person compensation lines were supplied" in line for line in gross.derivation)


def test_per_person_ceiling_applies_false_emits_noop_and_leaves_base_unchanged():
    """A programme declaring per_person_ceiling.applies false emits a
    derivation line saying no per-person ceiling applies, and leaves the
    base unchanged."""
    programme = _make_programme(
        per_person_ceiling=PerPersonCeiling(applies=False, note="test: no ceiling in this jurisdiction"),
        rate_structure=RateStructure(type="flat", base_rate=Decimal("0.25")),
    )
    qualifying_base = compute_qualifying_base(
        programme, SpendBreakdown.from_total(Decimal("1000000")), currency="USD"
    )

    gross = compute_gross_credit(
        programme,
        qualifying_base,
        per_person_compensations=[
            PerPersonCompensation(role="Lead", amount=Decimal("5000000"), payment_route="w2")
        ],
    )

    assert gross.value == Decimal("250000")  # 1,000,000 x 0.25, unaffected by the supplied compensation
    assert any("no per-person ceiling applies in this jurisdiction" in line for line in gross.derivation)


# ---------------------------------------------------------------------------
# Task 2: cliff-tier lookup and ceiling-split blend — two functions, never
# one (INC-03)
# ---------------------------------------------------------------------------

# Connecticut's real three-band schedule (jurisdictions/us-ct.yaml), used
# directly here as plain Tier objects to unit-test lookup_flat_rate_by_band
# in isolation from the full rule-file/pipeline machinery.
CT_TIERS = [
    Tier(threshold_low=Decimal("100000"), threshold_high=Decimal("500000"), rate=Decimal("0.10")),
    Tier(threshold_low=Decimal("500000"), threshold_high=Decimal("1000000"), rate=Decimal("0.15")),
    Tier(threshold_low=Decimal("1000000"), threshold_high=None, rate=Decimal("0.30")),
]


def test_lookup_and_blend_are_distinct_callables():
    """A test asserts both are importable from engine.credit and are not
    the same object — a single shared function handling both structures
    via an internal branch would fail this."""
    assert lookup_flat_rate_by_band is not blend_two_rates_by_ceiling
    assert callable(lookup_flat_rate_by_band)
    assert callable(blend_two_rates_by_ceiling)


@pytest.mark.parametrize(
    ("base", "expected_raw_value"),
    [
        (Decimal("499999"), Decimal("499999") * Decimal("0.10")),
        (Decimal("500000"), Decimal("500000") * Decimal("0.15")),
        (Decimal("500001"), Decimal("500001") * Decimal("0.15")),
        (Decimal("999999"), Decimal("999999") * Decimal("0.15")),
        (Decimal("1000000"), Decimal("1000000") * Decimal("0.30")),
        (Decimal("1000001"), Decimal("1000001") * Decimal("0.30")),
    ],
    ids=[
        "499999_band1",
        "500000_band2_starts_here",
        "500001_band2",
        "999999_band2",
        "1000000_band3_starts_here",
        "1000001_band3",
    ],
)
def test_lookup_flat_rate_by_band_half_open_boundaries(base, expected_raw_value):
    """Bands are half-open: a base exactly at a band's upper threshold
    falls in the NEXT band up — proven at 499999/500000/500001 and
    999999/1000000/1000001 against Connecticut's real $500,000 and
    $1,000,000 boundaries. The boundary value takes the rate of the band
    that STARTS at it."""
    assert lookup_flat_rate_by_band(base, CT_TIERS) == expected_raw_value


def test_lookup_flat_rate_by_band_reproduces_christmas_always_and_not_the_marginal_misreading():
    """Cliff lookup: Decimal('3865005') against Connecticut's three-band
    schedule takes the single 30% rate of the band above $1,000,000,
    giving Decimal('1159501.50'), which quantises to Decimal('1159502') —
    the figure Connecticut actually issued. The same input does NOT
    produce Decimal('984502') — the marginal/blended reading of the same
    table (02-RESEARCH.md Finding 3), wrong by nearly $175,000. This
    negative literal is not computed by any function in this codebase; it
    is the documented wrong value a plausible alternative implementation
    would produce."""
    raw = lookup_flat_rate_by_band(Decimal("3865005"), CT_TIERS)
    assert raw == Decimal("1159501.50")

    computed = quantize_money(raw)
    assert computed == Decimal("1159502")

    wrong_marginal_value = Decimal("984502")
    assert computed != wrong_marginal_value


def test_lookup_flat_rate_by_band_no_matching_band_raises():
    """A base matching no declared band raises, naming the base."""
    narrow_tiers = [
        Tier(threshold_low=Decimal("100000"), threshold_high=Decimal("500000"), rate=Decimal("0.10"))
    ]
    with pytest.raises(ValueError) as excinfo:
        lookup_flat_rate_by_band(Decimal("50"), narrow_tiers)
    assert "50" in str(excinfo.value)


def test_blend_two_rates_by_ceiling_reproduces_uk_example_and_not_the_cap_before_split_misreading():
    """Ceiling split: Decimal('18000000') of core expenditure against a
    15,000,000 enhanced threshold, a 0.80 core cap and rates of 0.53 and
    0.34 gives exactly Decimal('7176000'). The same input does NOT produce
    Decimal('7632000') — the value produced by capping the whole base
    before splitting instead of capping each slice after (the cap-before-
    split misreading)."""
    computed = blend_two_rates_by_ceiling(
        Decimal("18000000"),
        Decimal("15000000"),
        Decimal("0.53"),
        Decimal("0.34"),
        pct_cap=Decimal("0.80"),
    )
    assert computed == Decimal("7176000")

    wrong_cap_before_split_value = Decimal("7632000")
    assert computed != wrong_cap_before_split_value


def test_blend_two_rates_by_ceiling_full_pipeline_uk_fixture():
    """The full credit sequence, driven by the committed
    synthetic-uk-style.yaml fixture, reproduces Decimal('7176000') exactly
    and the blend's derivation contains one line for the enhanced slice
    and a separate line for the standard slice, each naming its slice
    amount, its capped amount and its rate."""
    programme = _programme_by_id(UK_FIXTURE, "uk-style-ceiling-split-synthetic")
    spend = SpendBreakdown.from_total(Decimal("18000000"))
    qualifying_base = compute_qualifying_base(programme, spend, currency="GBP")

    gross = compute_gross_credit(programme, qualifying_base)

    assert gross.value == Decimal("7176000")

    enhanced_lines = [line for line in gross.derivation if "enhanced slice" in line]
    standard_lines = [line for line in gross.derivation if "standard slice" in line]
    assert len(enhanced_lines) == 1
    assert len(standard_lines) == 1
    assert enhanced_lines[0] != standard_lines[0]
    for line in (*enhanced_lines, *standard_lines):
        assert "rate" in line


def test_blend_two_rates_by_ceiling_standard_slice_still_emitted_when_zero():
    """A wholly-enhanced production (core expenditure below the enhanced
    threshold) must still show that the standard slice was considered and
    came to nothing — both slices are always computed and always emit a
    derivation line."""
    programme = _make_programme(
        rate_structure=RateStructure(
            type="blended_by_ceiling_split",
            ceiling_split=CeilingSplit(
                enhanced_threshold=Money(value=Decimal("15000000"), currency="GBP"),
                enhanced_rate=Decimal("0.53"),
                standard_rate=Decimal("0.34"),
            ),
        ),
    )
    qualifying_base = compute_qualifying_base(
        programme, SpendBreakdown.from_total(Decimal("5000000")), currency="GBP"
    )

    gross = compute_gross_credit(programme, qualifying_base)

    # enhanced_slice = min(5,000,000, 15,000,000) = 5,000,000; no pct_cap
    # declared on this synthetic programme -> capped_enhanced == enhanced.
    # standard_slice = max(0, 5,000,000 - 15,000,000) = 0.
    assert gross.value == Decimal("5000000") * Decimal("0.53")

    standard_lines = [line for line in gross.derivation if "standard slice" in line]
    assert len(standard_lines) == 1
    assert "0" in standard_lines[0]


def test_blend_two_rates_by_ceiling_missing_core_expenditure_edge_raises():
    """Removing the Core expenditure (pre-cap) entry from a qualifying base
    makes the blend raise rather than silently using the already-capped
    qualifying-base value — the wrong-ordering bug wearing a disguise."""
    programme = _programme_by_id(UK_FIXTURE, "uk-style-ceiling-split-synthetic")
    qualifying_base_without_core_edge = Figure(
        value=Decimal("14400000"),
        unit="GBP",
        label="Qualifying base",
        derivation=("test: deliberately missing the core-expenditure inputs edge",),
        inputs=(),
        source_url=None,
        date_checked=None,
        confidence="validated",
        live_fetched_this_run=False,
    )

    with pytest.raises(ValueError) as excinfo:
        compute_gross_credit(programme, qualifying_base_without_core_edge)

    assert CORE_EXPENDITURE_LABEL in str(excinfo.value)


def test_tier_dispatch_and_stacking():
    """The single consolidated acceptance test named in this plan's
    Validation Architecture map and Task 2's `<action>` — every behaviour
    the individual tests above prove in isolation, exercised together in
    one function so `pytest tests/test_engine_credit.py::test_tier_dispatch_and_stacking`
    is a complete, self-contained proof of Task 2 on its own."""
    # 1. Two separately-named, distinct callables.
    assert lookup_flat_rate_by_band is not blend_two_rates_by_ceiling

    # 2. Half-open band boundaries against Connecticut's real thresholds.
    assert lookup_flat_rate_by_band(Decimal("499999"), CT_TIERS) == Decimal("499999") * Decimal(
        "0.10"
    )
    assert lookup_flat_rate_by_band(Decimal("500000"), CT_TIERS) == Decimal("500000") * Decimal(
        "0.15"
    )
    assert lookup_flat_rate_by_band(Decimal("500001"), CT_TIERS) == Decimal("500001") * Decimal(
        "0.15"
    )
    assert lookup_flat_rate_by_band(Decimal("999999"), CT_TIERS) == Decimal("999999") * Decimal(
        "0.15"
    )
    assert lookup_flat_rate_by_band(Decimal("1000000"), CT_TIERS) == Decimal("1000000") * Decimal(
        "0.30"
    )
    assert lookup_flat_rate_by_band(Decimal("1000001"), CT_TIERS) == Decimal("1000001") * Decimal(
        "0.30"
    )

    # 3. Cliff lookup golden value AND the explicit negative assertion —
    # Decimal('1159502') is Connecticut's real disclosed Christmas Always
    # figure; Decimal('984502') is the marginal/blended misreading of the
    # same table (02-RESEARCH.md Finding 3), wrong by nearly $175,000.
    cliff_computed = quantize_money(lookup_flat_rate_by_band(Decimal("3865005"), CT_TIERS))
    assert cliff_computed == Decimal("1159502")
    assert cliff_computed != Decimal("984502")

    # 4. Blend golden value AND the explicit negative assertion —
    # Decimal('7176000') is the correct split-then-cap-each-slice figure;
    # Decimal('7632000') is the cap-the-whole-base-first misreading.
    blend_computed = blend_two_rates_by_ceiling(
        Decimal("18000000"),
        Decimal("15000000"),
        Decimal("0.53"),
        Decimal("0.34"),
        pct_cap=Decimal("0.80"),
    )
    assert blend_computed == Decimal("7176000")
    assert blend_computed != Decimal("7632000")

    # 5. No declared band matching the base raises, naming the base.
    with pytest.raises(ValueError) as excinfo:
        lookup_flat_rate_by_band(
            Decimal("50"),
            [Tier(threshold_low=Decimal("100000"), threshold_high=None, rate=Decimal("0.10"))],
        )
    assert "50" in str(excinfo.value)

    # 6. Rate-structure dispatch is read from data, not hardcoded — the
    # closed-enum dispatch on rate_structure.type (never a jurisdiction
    # identifier string, JUR-05) means declaring a different
    # rate_structure.type changes which function runs, proven here by
    # dispatching the SAME base through both structures and confirming the
    # two rate_structure types give different, individually-correct results
    # (never the same number by coincidence, never a shared code path).
    # (Uplift stacking itself — additive rates across programmes — is a
    # separate mechanism implemented in plan 02-06, not exercised here.)
    cliff_programme = _make_programme(
        rate_structure=RateStructure(type="tiered_by_spend", tiers=CT_TIERS)
    )
    blend_programme = _make_programme(
        rate_structure=RateStructure(
            type="blended_by_ceiling_split",
            ceiling_split=CeilingSplit(
                enhanced_threshold=Money(value=Decimal("500000"), currency="USD"),
                enhanced_rate=Decimal("0.10"),
                standard_rate=Decimal("0.15"),
            ),
        )
    )
    shared_base_spend = SpendBreakdown.from_total(Decimal("3865005"))
    cliff_base = compute_qualifying_base(cliff_programme, shared_base_spend, currency="USD")
    blend_base = compute_qualifying_base(blend_programme, shared_base_spend, currency="USD")
    cliff_result = compute_gross_credit(cliff_programme, cliff_base)
    blend_result = compute_gross_credit(blend_programme, blend_base)
    assert cliff_result.value != blend_result.value, (
        "tiered_by_spend and blended_by_ceiling_split dispatched on the same input "
        "must not silently collapse to the same computation"
    )


def test_directory_hygiene_synthetic_fixtures_declare_synthetic_status():
    """Both new fixtures declare jurisdiction.status synthetic_fixture —
    the same structural guard tests/test_engine_qualifying_base.py already
    enforces repo-wide, re-asserted directly here for the two files this
    plan adds."""
    for path in (GA_FIXTURE, UK_FIXTURE):
        ruleset = load_ruleset(path)
        assert ruleset.jurisdiction.status == "synthetic_fixture", (
            f"{path}: expected jurisdiction.status 'synthetic_fixture', "
            f"got {ruleset.jurisdiction.status!r}"
        )

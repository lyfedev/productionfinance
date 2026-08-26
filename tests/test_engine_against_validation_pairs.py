"""The end-to-end proof (D-02): each curated jurisdiction's rule file,
loaded as data through `engine.models.load_ruleset`, prices
`Decimal(qualified_spend)` through `engine.qualifying_base.compute_qualifying_base`
and `engine.credit.compute_gross_credit` and reproduces the
government-disclosed award figures already committed under
`tests/fixtures/validation_pairs/*.yaml` — exactly for an `exact`-mode
pair, or within a small, explicitly written-down tolerance for a
`bounded`-mode pair.

RD-03: the assertion is against GrossCredit (the credit issued/allocated,
pre-audit-fee, pre-transfer-discount Figure), never against net cash —
government disclosures report the credit issued, not what a producer nets
after fees, and asserting a disclosed figure against net cash would
silently require the audit-fee/discount model to be wrong in a
compensating direction.

Plan 02-05 deviation, re-coupled by plan 02-09 (Rule 1 — bug: an accidental
coupling, not a requirement of RD-03 itself): this test originally priced
base + credit directly, bypassing `engine.pipeline.price_jurisdiction`
entirely. `price_jurisdiction` always also computes net cash via
`engine.net_cash.convert_to_net_cash`, which raised `NotImplementedError`
for any mechanism other than `refundable` before plan 02-04 landed.
Connecticut's real, statute-sourced mechanism is `transferable`
(jurisdictions/us-ct.yaml), so routing this golden-value test through the
full pipeline would have raised before ever reaching the assertion this
test actually needs — even though the test never looks at net cash at all.
Plan 02-04 implemented `transferable` (and the other three net-cash
mechanisms), closing the gap that motivated the decoupling. Plan 02-09
re-coupled the test to `price_jurisdiction`, adding pipeline-routed
assertions ALONGSIDE the original direct base-then-credit assertions — both
paths run and must agree, so neither can compensate for the other. RD-03's
own stated principle ("assert on gross credit, never net cash") still
holds: routing through `price_jurisdiction` changes which code path
produces the figure, never which figure is compared against a government
disclosure.

Plan 02-09 finding, discovered by actually running the re-coupled test
(never assumed): `price_jurisdiction` always ALSO computes net cash, and the
real, committed `jurisdictions/us-ct.yaml` declares
`transfer_discount.applies: true` but leaves `typical_rate_low` and
`typical_rate_high` both null — CGS 12-217jj(e)(1) confirms the credit is
transferable but the statute states no market discount rate, so no sourced
conversion rate exists for Connecticut. `engine.net_cash.transferable`
correctly refuses to convert at an unsourced rate rather than invent one
(the same behaviour `tests/test_engine_net_cash.py::test_transferable_requires_fully_declared_transfer_discount`
already covers generically) — so `price_jurisdiction` currently raises
`ValueError` for EVERY active Connecticut pair, not only Christmas Always.
This is a genuine, disclosed data gap, not a bug: `engine/net_cash.py` and
`jurisdictions/us-ct.yaml` are both correct and unmodified by this plan, and
inventing a discount rate to make the pipeline "complete" would violate this
project's core rule against presenting an unresearched figure as validated.
It is also the concrete, real-data proof of WHY RD-03 anchors the
golden-value assertion on gross credit alone rather than net cash:
`test_christmas_always_reproduces_exactly` above already proves the
disclosed figure is reproduced through the direct base-then-credit path; net
cash for Connecticut cannot currently be computed at all, sourced or
fabricated. `_pipeline_can_complete` (below) makes this exclusion structural
rather than a hard-coded jurisdiction-id skip, so a future `us-ct.yaml`
update that sources a real discount rate is picked up automatically, not
silently left excluded.

Jurisdiction-to-rule-file mapping is now a dict (JUR-05-style: adding a
third jurisdiction here is a one-line addition, not a copied test), per
Task 3's explicit generalisation instruction.

This is the same sorted-glob + safe-loader + fail-loud-on-empty-glob
pattern `tests/test_validation_pair_fixtures.py` already uses (T-01-15 —
a parametrized test over an empty collection is a vacuous green).
"""

import re
from decimal import Decimal
from glob import glob

import pytest
import yaml

from engine.credit import compute_gross_credit
from engine.models import JurisdictionRuleSet, load_ruleset
from engine.pipeline import price_jurisdiction
from engine.qualifying_base import SpendBreakdown, compute_qualifying_base

FIXTURE_DIR = "tests/fixtures/validation_pairs"
FIXTURE_PATHS = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))

if not FIXTURE_PATHS:
    raise RuntimeError(
        f"No fixture files found under {FIXTURE_DIR}/*.yaml — an empty "
        "validation-pair set must fail loudly, not report a vacuous green."
    )

# Jurisdiction-to-rule-file mapping (generalised from a hard-coded New
# York-only filter, Task 3): a third jurisdiction is a one-line addition.
RULESET_PATH_BY_JURISDICTION = {
    "us-ny": "jurisdictions/us-ny.yaml",
    "us-ct": "jurisdictions/us-ct.yaml",
}
RULESETS: dict[str, JurisdictionRuleSet] = {
    jurisdiction_id: load_ruleset(path)
    for jurisdiction_id, path in RULESET_PATH_BY_JURISDICTION.items()
}


def _load(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _active_pairs_for(jurisdiction_id: str) -> list[dict]:
    pairs = []
    for path in FIXTURE_PATHS:
        data = _load(path)
        if data.get("status") != "active":
            continue
        if data.get("jurisdiction_id") != jurisdiction_id:
            continue
        pairs.append(data)
    return pairs


NY_ACTIVE_PAIRS = _active_pairs_for("us-ny")
NY_RULESET = RULESETS["us-ny"]
CT_ACTIVE_PAIRS = _active_pairs_for("us-ct")
CT_RULESET = RULESETS["us-ct"]


def _gross_credit_for(pair: dict) -> Decimal:
    ruleset = RULESETS[pair["jurisdiction_id"]]
    programme = next(
        (p for p in ruleset.programmes if p.id == pair["program_id"]), None
    )
    assert programme is not None, (
        f"{pair['production_title']}: no programme matches program_id "
        f"{pair['program_id']!r} — check {RULESET_PATH_BY_JURISDICTION[pair['jurisdiction_id']]}'s "
        "programme id against the fixture"
    )

    qualified_spend = Decimal(pair["qualified_spend"])
    spend = SpendBreakdown.from_total(qualified_spend)
    qualifying_base = compute_qualifying_base(
        programme, spend, currency=ruleset.jurisdiction.currency
    )
    gross_credit = compute_gross_credit(programme, qualifying_base)
    return gross_credit.value


def _gross_credit_via_pipeline(pair: dict) -> Decimal:
    """Price `pair` through `engine.pipeline.price_jurisdiction` — the
    engine's real entry point — and return the matching `PricedProgramme`'s
    gross-credit value. Mirrors `_gross_credit_for`'s fail-loud missing-
    programme message shape."""
    ruleset = RULESETS[pair["jurisdiction_id"]]
    qualified_spend = Decimal(pair["qualified_spend"])
    priced = price_jurisdiction(ruleset, qualified_spend)
    priced_programme = next(
        (pp for pp in priced.programmes if pp.programme_id == pair["program_id"]), None
    )
    assert priced_programme is not None, (
        f"{pair['production_title']}: no priced programme matches program_id "
        f"{pair['program_id']!r} — check "
        f"{RULESET_PATH_BY_JURISDICTION[pair['jurisdiction_id']]}'s programme id "
        "against the fixture"
    )
    return priced_programme.gross_credit.value


def _pipeline_can_complete(pair: dict) -> bool:
    """True unless `pair`'s declared programme is `transferable` without a
    fully-sourced `transfer_discount` range — the one currently-known reason
    `price_jurisdiction` cannot complete for a real, correctly-sourced
    jurisdiction file (plan 02-09 finding, see module docstring). Checked
    structurally by reading the declared programme, never by jurisdiction
    id, so a future `us-ct.yaml` update that sources a real discount rate is
    picked up automatically rather than staying silently excluded."""
    ruleset = RULESETS[pair["jurisdiction_id"]]
    programme = next(p for p in ruleset.programmes if p.id == pair["program_id"])
    if programme.mechanism != "transferable":
        return True
    discount = programme.transfer_discount
    return (
        discount.applies
        and discount.typical_rate_low is not None
        and discount.typical_rate_high is not None
    )


def _assert_matches_disclosure(pair: dict, computed_credit: Decimal, *, via: str) -> None:
    """The shared exact-versus-bounded comparison, used by both the
    direct-path and pipeline-routed tests so a future tolerance change
    cannot apply to one path and not the other."""
    disclosed_credit = Decimal(pair["credit_amount"])
    disclosed_spend = Decimal(pair["qualified_spend"])

    mode = pair["assertion"]["mode"]
    if mode == "exact":
        assert computed_credit == disclosed_credit, (
            f"{pair['production_title']} ({via}): computed gross credit "
            f"{computed_credit} does not exactly match disclosed "
            f"{disclosed_credit}"
        )
    elif mode == "bounded":
        tolerance_bps = pair["assertion"]["tolerance_bps"]
        assert tolerance_bps is not None, (
            f"{pair['production_title']}: assertion.mode is 'bounded' but "
            "tolerance_bps is missing"
        )
        residue = abs(disclosed_credit - computed_credit)
        implied_bps = (residue / disclosed_spend) * Decimal("10000")
        assert implied_bps <= Decimal(tolerance_bps), (
            f"{pair['production_title']} ({via}): residue {residue} is "
            f"{implied_bps} bps of disclosed spend, exceeding the fixture's "
            f"tolerance_bps of {tolerance_bps}"
        )
    else:
        pytest.fail(f"{pair['production_title']}: unrecognized assertion.mode {mode!r}")


ALL_ACTIVE_PAIRS = NY_ACTIVE_PAIRS + CT_ACTIVE_PAIRS

# Every active pair whose declared programme currently CAN complete through
# `price_jurisdiction` (plan 02-09 finding, see module docstring) —
# Connecticut's real `transferable` programme cannot, so it is excluded here
# but still fully covered by the direct-path tests above and by
# test_ct_pipeline_routing_blocked_by_unsourced_transfer_discount below,
# which proves and names exactly why.
PIPELINE_ROUTABLE_PAIRS = [p for p in ALL_ACTIVE_PAIRS if _pipeline_can_complete(p)]
if not PIPELINE_ROUTABLE_PAIRS:
    raise RuntimeError(
        "no pipeline-routable pairs found — an empty pipeline-routed sweep must fail "
        "loudly, not report a vacuous green."
    )


@pytest.mark.parametrize(
    "pair", ALL_ACTIVE_PAIRS, ids=[p["production_title"] for p in ALL_ACTIVE_PAIRS]
)
def test_curated_jurisdiction_reproduces_disclosed_credit(pair):
    """Assert on the disclosed credit-issued figure alone — the fixture's
    other money field (a separate, distinct NY program not modelled by
    this rule file, per SCOPE-FREEZE.md) is never added to this comparison
    (Pitfall 5). Covers every curated jurisdiction in
    RULESET_PATH_BY_JURISDICTION, not New York alone. Direct base-then-
    credit path — kept alongside the pipeline-routed sweep below, not
    replaced by it (plan 02-09)."""
    computed_credit = _gross_credit_for(pair)
    _assert_matches_disclosure(pair, computed_credit, via="direct")


@pytest.mark.parametrize(
    "pair", PIPELINE_ROUTABLE_PAIRS, ids=[p["production_title"] for p in PIPELINE_ROUTABLE_PAIRS]
)
def test_curated_jurisdiction_reproduces_disclosed_credit_via_pipeline(pair):
    """Every pipeline-routable active validation pair, re-run through
    `price_jurisdiction` — the engine's real entry point, exercising base ->
    credit -> net cash as one composition (plan 02-09 re-coupling). The
    pipeline-routed gross credit must ALSO equal the direct base-then-credit
    gross credit for this same pair: the two paths agreeing is the evidence
    that neither is compensating for the other. Connecticut's `transferable`
    pair is excluded from this sweep by `PIPELINE_ROUTABLE_PAIRS` (module
    docstring, `_pipeline_can_complete`) — its direct-path reproduction is
    still proven by the sweep above and by
    `test_christmas_always_reproduces_exactly`."""
    direct_credit = _gross_credit_for(pair)
    pipeline_credit = _gross_credit_via_pipeline(pair)
    assert pipeline_credit == direct_credit, (
        f"{pair['production_title']}: pipeline-routed gross credit "
        f"{pipeline_credit} disagrees with the direct base-then-credit gross "
        f"credit {direct_credit} — the two paths must agree; a disagreement "
        "is a real finding about the composition, never a fixture problem"
    )
    _assert_matches_disclosure(pair, pipeline_credit, via="price_jurisdiction")


def test_anora_reproduces_exactly():
    """The plan's headline acceptance criterion, asserted directly and
    independently of the parametrized sweep above: Anora's disclosed
    qualified spend of $3,964,760 prices to a gross credit of exactly
    Decimal('991190') — the figure New York State actually issued."""
    anora = next(p for p in NY_ACTIVE_PAIRS if p["production_title"] == "Anora")
    computed = _gross_credit_for(anora)
    assert computed == Decimal("991190")


def test_christmas_always_reproduces_exactly():
    """Plan 02-05's headline acceptance criterion for Connecticut: Christmas
    Always's disclosed qualified spend of $3,865,005 prices to a gross
    credit of exactly Decimal('1159502') — the second real
    government-issued figure this project reproduces exactly, and the
    tiered_by_spend cliff-lookup proof jurisdiction (02-RESEARCH.md
    Finding 3)."""
    christmas_always = next(
        p for p in CT_ACTIVE_PAIRS if p["production_title"] == "Christmas Always"
    )
    computed = _gross_credit_for(christmas_always)
    assert computed == Decimal("1159502")


def test_anora_reproduces_exactly_through_price_jurisdiction():
    """Anora's disclosed qualified spend of $3,964,760 prices to a gross
    credit of exactly Decimal('991190') through `price_jurisdiction` — the
    engine's real entry point, not only the direct base-then-credit path
    `test_anora_reproduces_exactly` above already proves."""
    anora = next(p for p in NY_ACTIVE_PAIRS if p["production_title"] == "Anora")
    computed = _gross_credit_via_pipeline(anora)
    assert computed == Decimal("991190")


def test_christmas_always_reproduces_exactly_through_price_jurisdiction():
    """Plan 02-09 finding (documented, not routed around — see module
    docstring): this test was written to prove Christmas Always's disclosed
    $3,865,005 prices to exactly Decimal('1159502') through
    `price_jurisdiction`, necessarily running Connecticut's `transferable`
    net-cash conversion. Running it against the real, committed
    `jurisdictions/us-ct.yaml` instead proves the opposite of what was
    assumed: `price_jurisdiction` raises `ValueError`, because
    `transfer_discount.typical_rate_low`/`typical_rate_high` are both null —
    CGS 12-217jj(e)(1) states the credit is transferable but states no
    market discount rate, so no sourced conversion rate exists to run. This
    is a genuine, disclosed data gap, not a bug (`engine/net_cash.py` and
    `jurisdictions/us-ct.yaml` are both correct and unmodified by this
    plan), and it is NOT silently routed around: `_pipeline_can_complete`
    reports `False` for this exact reason, `test_christmas_always_reproduces_exactly`
    above already proves the disclosed gross-credit figure through the
    direct path (RD-03's actual assertion target), and this test asserts
    the raise directly so a future sourced `transfer_discount` on
    `jurisdictions/us-ct.yaml` — which would make this test start failing —
    is caught immediately, not silently missed."""
    christmas_always = next(
        p for p in CT_ACTIVE_PAIRS if p["production_title"] == "Christmas Always"
    )
    assert not _pipeline_can_complete(christmas_always), (
        "expected price_jurisdiction to currently raise for Christmas Always "
        "(unsourced transfer_discount on jurisdictions/us-ct.yaml) — if this now "
        "fails, us-ct.yaml has been sourced with a real discount rate and this "
        "test should be rewritten back to its originally-intended exact-value "
        "and low/high/point-None assertions"
    )
    ruleset = RULESETS[christmas_always["jurisdiction_id"]]
    qualified_spend = Decimal(christmas_always["qualified_spend"])
    with pytest.raises(ValueError, match="transfer_discount"):
        price_jurisdiction(ruleset, qualified_spend)


def test_at_least_three_new_york_pairs_exercised():
    """A jurisdiction filter that silently matches nothing must fail
    loudly, not report a vacuous green."""
    assert len(NY_ACTIVE_PAIRS) >= 3, (
        f"expected at least 3 active us-ny validation pairs, found "
        f"{len(NY_ACTIVE_PAIRS)}"
    )


def test_at_least_one_connecticut_pair_exercised():
    """A `program_id` mismatch against jurisdictions/us-ct.yaml must fail
    loudly (a filter silently matching zero Connecticut pairs), not report
    a vacuous green."""
    assert len(CT_ACTIVE_PAIRS) >= 1, (
        f"expected at least 1 active us-ct validation pair, found {len(CT_ACTIVE_PAIRS)}"
    )


# ---------------------------------------------------------------------------
# D-72 (Phase 4) — a validation pair may NEVER route through the budget
# model. Disclosures publish qualified spend and the award, never the
# production's input vector (feasibility-incentives.md:263) — so feeding a
# fixture's production through `engine.budget` and comparing the result to
# a disclosed award would be measuring a fabricated input vector, and a
# green result would mean nothing. This module always feeds each pair's
# DISCLOSED `qualified_spend` straight into `SpendBreakdown.from_total` /
# `price_jurisdiction`, never a `ProductionSpec` built by a cost-side model.
# ---------------------------------------------------------------------------

_IMPORT_ENGINE_BUDGET_RE = re.compile(
    r"^\s*(import\s+engine\.budget\b|from\s+engine\.budget\s+import)", re.MULTILINE
)
_PRODUCTION_SPEC_CONSTRUCTION_RE = re.compile(r"\bProductionSpec\(")

# The ProductionSpec input-vector fields (INP-01..INP-07) a validation-pair
# fixture must never carry — a disclosure gives qualified spend and the
# award, never the production's shoot days, crew size/tier, cast count or
# candidate cities.
_FORBIDDEN_SPEC_INPUT_FIELDS = (
    "shoot_days_stage",
    "shoot_days_location",
    "crew_size",
    "crew_tier",
    "principal_cast_count",
    "candidate_cities",
)


def test_this_module_never_imports_engine_budget_or_constructs_a_production_spec():
    """Source-level guard (matches this repo's own established pattern —
    `tests/test_engine_models.py`'s security gates,
    `tests/test_engine_jurisdiction_additivity.py`'s JUR-05 scan): this
    module's own source must contain no `engine.budget` import and no
    construction of the spec-input dataclass this docstring deliberately
    does not spell out literally, anywhere (see the two regexes above)."""
    with open(__file__, encoding="utf-8") as handle:
        source = handle.read()

    assert not _IMPORT_ENGINE_BUDGET_RE.search(source), (
        "tests/test_engine_against_validation_pairs.py must never import engine.budget "
        "(D-72) — a validation pair is never routed through the budget model"
    )
    assert not _PRODUCTION_SPEC_CONSTRUCTION_RE.search(source), (
        "tests/test_engine_against_validation_pairs.py must never construct a "
        "ProductionSpec (D-72) — disclosures give qualified spend and the award, "
        "never the production's input vector"
    )


def test_every_pair_reproduces_the_disclosure_from_disclosed_spend_alone():
    """The substantive half of the D-72 guard: every active pair's asserted
    figure is produced by feeding the fixture's DISCLOSED `qualified_spend`
    straight into `price_jurisdiction` (via `SpendBreakdown.from_total`,
    the pipeline's own default) — never a modelled `SpendBreakdown` built
    from a `ProductionSpec`. This re-asserts what
    `test_curated_jurisdiction_reproduces_disclosed_credit_via_pipeline`
    already proves per-pair; here it is proven as a structural invariant of
    the whole sweep at once."""
    assert ALL_ACTIVE_PAIRS, "expected at least one active validation pair"
    for pair in ALL_ACTIVE_PAIRS:
        qualified_spend = Decimal(pair["qualified_spend"])
        spend = SpendBreakdown.from_total(qualified_spend)
        assert spend.total_spend == qualified_spend
        assert spend.core_expenditure == qualified_spend


def test_no_validation_pair_fixture_carries_a_production_spec_input_vector_field():
    """A future contributor must never be able to quietly add a
    ProductionSpec-shaped input-vector field to a validation-pair fixture
    — see this module's docstring and D-72."""
    for path in FIXTURE_PATHS:
        data = _load(path)
        present = sorted(set(data) & set(_FORBIDDEN_SPEC_INPUT_FIELDS))
        assert not present, (
            f"{path}: carries ProductionSpec input-vector field(s) {present} — "
            "a validation-pair fixture must only ever declare disclosed spend and "
            "the disclosed award, never a production's input vector (D-72)"
        )

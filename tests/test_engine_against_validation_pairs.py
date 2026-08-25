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

Plan 02-05 deviation (Rule 1 — bug: an accidental coupling, not a
requirement of RD-03 itself): this test now prices base + credit directly,
bypassing `engine.pipeline.price_jurisdiction` entirely. `price_jurisdiction`
always also computes net cash via `engine.net_cash.convert_to_net_cash`,
which raises `NotImplementedError` for any mechanism other than
`refundable` until plan 02-04 lands (02-04 is wave 3 and depends on 02-05,
so it has not run yet). Connecticut's real, statute-sourced mechanism is
`transferable` (jurisdictions/us-ct.yaml), so routing this golden-value
test through the full pipeline would raise before ever reaching the
assertion this test actually needs — even though the test never looks at
net cash at all. RD-03's own stated principle ("assert on gross credit,
never net cash") means this test was never supposed to depend on net cash
being computable in the first place; decoupling from `price_jurisdiction`
makes that principle load-bearing rather than accidental.

Jurisdiction-to-rule-file mapping is now a dict (JUR-05-style: adding a
third jurisdiction here is a one-line addition, not a copied test), per
Task 3's explicit generalisation instruction.

This is the same sorted-glob + safe-loader + fail-loud-on-empty-glob
pattern `tests/test_validation_pair_fixtures.py` already uses (T-01-15 —
a parametrized test over an empty collection is a vacuous green).
"""

from decimal import Decimal
from glob import glob

import pytest
import yaml

from engine.credit import compute_gross_credit
from engine.models import JurisdictionRuleSet, load_ruleset
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


ALL_ACTIVE_PAIRS = NY_ACTIVE_PAIRS + CT_ACTIVE_PAIRS


@pytest.mark.parametrize(
    "pair", ALL_ACTIVE_PAIRS, ids=[p["production_title"] for p in ALL_ACTIVE_PAIRS]
)
def test_curated_jurisdiction_reproduces_disclosed_credit(pair):
    """Assert on the disclosed credit-issued figure alone — the fixture's
    other money field (a separate, distinct NY program not modelled by
    this rule file, per SCOPE-FREEZE.md) is never added to this comparison
    (Pitfall 5). Covers every curated jurisdiction in
    RULESET_PATH_BY_JURISDICTION, not New York alone."""
    disclosed_credit = Decimal(pair["credit_amount"])
    disclosed_spend = Decimal(pair["qualified_spend"])
    computed_credit = _gross_credit_for(pair)

    mode = pair["assertion"]["mode"]
    if mode == "exact":
        assert computed_credit == disclosed_credit, (
            f"{pair['production_title']}: computed gross credit "
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
            f"{pair['production_title']}: residue {residue} is "
            f"{implied_bps} bps of disclosed spend, exceeding the fixture's "
            f"tolerance_bps of {tolerance_bps}"
        )
    else:
        pytest.fail(f"{pair['production_title']}: unrecognized assertion.mode {mode!r}")


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

"""The end-to-end proof (D-02): New York's curated rule file, loaded as
data through `engine.models.load_ruleset`, prices `Decimal(qualified_spend)`
through `engine.pipeline.price_jurisdiction` and reproduces the
government-disclosed award figures already committed under
`tests/fixtures/validation_pairs/ny_*.yaml` — exactly for an `exact`-mode
pair, or within a small, explicitly written-down tolerance for a
`bounded`-mode pair.

RD-03: the assertion is against GrossCredit (the credit issued/allocated,
pre-audit-fee, pre-transfer-discount Figure), never against net cash —
government disclosures report the credit issued, not what a producer nets
after fees, and asserting a disclosed figure against net cash would
silently require the audit-fee/discount model to be wrong in a
compensating direction.

This is the same sorted-glob + safe-loader + fail-loud-on-empty-glob
pattern `tests/test_validation_pair_fixtures.py` already uses (T-01-15 —
a parametrized test over an empty collection is a vacuous green).
"""

from decimal import Decimal
from glob import glob

import pytest
import yaml

from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction

FIXTURE_DIR = "tests/fixtures/validation_pairs"
FIXTURE_PATHS = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))

if not FIXTURE_PATHS:
    raise RuntimeError(
        f"No fixture files found under {FIXTURE_DIR}/*.yaml — an empty "
        "validation-pair set must fail loudly, not report a vacuous green."
    )


def _load(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _new_york_active_pairs() -> list[dict]:
    pairs = []
    for path in FIXTURE_PATHS:
        data = _load(path)
        if data.get("status") != "active":
            continue
        if data.get("jurisdiction_id") != "us-ny":
            continue
        pairs.append(data)
    return pairs


NY_ACTIVE_PAIRS = _new_york_active_pairs()
NY_RULESET = load_ruleset("jurisdictions/us-ny.yaml")


def _gross_credit_for(pair: dict) -> Decimal:
    qualified_spend = Decimal(pair["qualified_spend"])
    result = price_jurisdiction(NY_RULESET, qualified_spend)
    matching = [p for p in result.programmes if p.programme_id == pair["program_id"]]
    assert matching, (
        f"{pair['production_title']}: no priced programme matches "
        f"program_id {pair['program_id']!r} — check jurisdictions/us-ny.yaml's "
        "programme id against the fixture"
    )
    return matching[0].gross_credit.value


@pytest.mark.parametrize(
    "pair", NY_ACTIVE_PAIRS, ids=[p["production_title"] for p in NY_ACTIVE_PAIRS]
)
def test_new_york_reproduces_disclosed_credit(pair):
    """Assert on the disclosed credit-issued figure alone — the fixture's
    other money field (a separate, distinct NY program not modelled by
    this rule file, per SCOPE-FREEZE.md) is never added to this comparison
    (Pitfall 5)."""
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


def test_at_least_three_new_york_pairs_exercised():
    """A jurisdiction filter that silently matches nothing must fail
    loudly, not report a vacuous green."""
    assert len(NY_ACTIVE_PAIRS) >= 3, (
        f"expected at least 3 active us-ny validation pairs, found "
        f"{len(NY_ACTIVE_PAIRS)}"
    )

"""JUR-02: California-specific reproduction of the two committed CA
validation pairs, with explicit literal expected-value assertions.

Modelled on tests/test_engine_against_validation_pairs.py's structure (sorted
glob + fail-loud-on-empty-glob + direct-path/pipeline-routed dual proof), but
scoped to us-ca only, per this plan's own files_modified boundary — that
module already covers us-ny and us-ct and is not touched here.

Snapshot testing is forbidden for validation pairs (the permitted-testing
line in .claude/CLAUDE.md); every expected value below is a literal Decimal
written by hand from each pair's disclosed qualified_spend x the sourced
0.35 base rate (jurisdictions/us-ca.yaml rate_structure.source_note), never
"whatever the code currently returns."
"""

from decimal import Decimal
from glob import glob

import pytest
import yaml

from engine.credit import compute_gross_credit
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction
from engine.qualifying_base import SpendBreakdown, compute_qualifying_base

FIXTURE_DIR = "tests/fixtures/validation_pairs"
FIXTURE_PATHS = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))

if not FIXTURE_PATHS:
    raise RuntimeError(
        f"No fixture files found under {FIXTURE_DIR}/*.yaml — an empty "
        "validation-pair set must fail loudly, not report a vacuous green."
    )

CA_RULESET = load_ruleset("jurisdictions/us-ca.yaml")


def _load(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _active_ca_pairs() -> list[dict]:
    pairs = []
    for path in FIXTURE_PATHS:
        data = _load(path)
        if data.get("status") != "active":
            continue
        if data.get("jurisdiction_id") != "us-ca":
            continue
        pairs.append(data)
    return pairs


CA_ACTIVE_PAIRS = _active_ca_pairs()

# A jurisdiction filter that silently matches nothing must fail loudly, not
# report a vacuous green (T-01-15) — the same guard
# test_engine_against_validation_pairs.py's module-level FIXTURE_PATHS check
# already establishes, applied here to the us-ca-specific filter.
if not CA_ACTIVE_PAIRS:
    raise RuntimeError(
        "no active us-ca validation pairs found — the California jurisdiction "
        "filter must fail loudly, not report a vacuous green."
    )


def _programme_for(pair: dict):
    programme = next((p for p in CA_RULESET.programmes if p.id == pair["program_id"]), None)
    assert programme is not None, (
        f"{pair['production_title']}: no programme matches program_id "
        f"{pair['program_id']!r} — check jurisdictions/us-ca.yaml's programme id "
        "against the fixture"
    )
    return programme


def _gross_credit_direct(pair: dict) -> Decimal:
    """Direct base-then-credit path — compute_qualifying_base ->
    compute_gross_credit, bypassing price_jurisdiction entirely."""
    programme = _programme_for(pair)
    qualified_spend = Decimal(pair["qualified_spend"])
    spend = SpendBreakdown.from_total(qualified_spend)
    qualifying_base = compute_qualifying_base(
        programme, spend, currency=CA_RULESET.jurisdiction.currency
    )
    gross_credit = compute_gross_credit(programme, qualifying_base)
    return gross_credit.value


def _gross_credit_via_pipeline(pair: dict) -> Decimal:
    """price_jurisdiction — the engine's real entry point. Runs base ->
    credit -> net cash as one composition; only the gross-credit figure is
    asserted here (RD-03 — government disclosures report the credit
    issued/allocated, never net cash)."""
    qualified_spend = Decimal(pair["qualified_spend"])
    priced = price_jurisdiction(CA_RULESET, qualified_spend)
    priced_programme = next(
        (pp for pp in priced.programmes if pp.programme_id == pair["program_id"]), None
    )
    assert priced_programme is not None, (
        f"{pair['production_title']}: no priced programme matches program_id "
        f"{pair['program_id']!r} through price_jurisdiction"
    )
    return priced_programme.gross_credit.value


def _assert_matches_disclosure(pair: dict, computed_credit: Decimal, *, via: str) -> None:
    disclosed_credit = Decimal(pair["credit_amount"])
    disclosed_spend = Decimal(pair["qualified_spend"])

    mode = pair["assertion"]["mode"]
    assert mode == "bounded", (
        f"{pair['production_title']}: expected assertion.mode 'bounded' (both "
        f"CA fixtures are allocation-stage, not exact), got {mode!r}"
    )
    tolerance_bps = pair["assertion"]["tolerance_bps"]
    assert tolerance_bps is not None
    residue = abs(disclosed_credit - computed_credit)
    implied_bps = (residue / disclosed_spend) * Decimal("10000")
    assert implied_bps <= Decimal(tolerance_bps), (
        f"{pair['production_title']} ({via}): residue {residue} is {implied_bps} bps "
        f"of disclosed spend, exceeding the fixture's tolerance_bps of {tolerance_bps}"
    )


@pytest.mark.parametrize(
    "pair", CA_ACTIVE_PAIRS, ids=[p["production_title"] for p in CA_ACTIVE_PAIRS]
)
def test_ca_pair_reproduces_disclosed_credit_direct(pair):
    computed = _gross_credit_direct(pair)
    _assert_matches_disclosure(pair, computed, via="direct")


@pytest.mark.parametrize(
    "pair", CA_ACTIVE_PAIRS, ids=[p["production_title"] for p in CA_ACTIVE_PAIRS]
)
def test_ca_pair_reproduces_disclosed_credit_via_pipeline(pair):
    computed = _gross_credit_via_pipeline(pair)
    _assert_matches_disclosure(pair, computed, via="price_jurisdiction")


@pytest.mark.parametrize(
    "pair", CA_ACTIVE_PAIRS, ids=[p["production_title"] for p in CA_ACTIVE_PAIRS]
)
def test_ca_direct_and_pipeline_paths_agree(pair):
    """Two paths agreeing is the evidence that neither compensates for the
    other (mirrors test_engine_against_validation_pairs.py's identical
    cross-check for NY/CT)."""
    direct = _gross_credit_direct(pair)
    pipeline = _gross_credit_via_pipeline(pair)
    assert direct == pipeline, (
        f"{pair['production_title']}: direct-path gross credit {direct} disagrees "
        f"with pipeline-routed gross credit {pipeline} — the two paths must agree"
    )


def test_clueless_s1_reproduces_within_tolerance():
    """Headline literal assertion: Clueless S1's disclosed qualified spend of
    $46,522,000 at the sourced 0.35 base rate prices to a gross credit of
    exactly Decimal('16282700.00') (46522000 * 0.35 = 16282700), a residue of
    $52,300 against the disclosed $16,335,000 allocation — 11.24 bps of
    disclosed spend, inside the fixture's declared 50 bps tolerance."""
    pair = next(p for p in CA_ACTIVE_PAIRS if p["production_title"] == "Clueless S1")
    computed = _gross_credit_direct(pair)
    assert computed == Decimal("16282700.00")
    residue = abs(Decimal(pair["credit_amount"]) - computed)
    assert residue == Decimal("52300.00")


def test_disneys_hexed_reproduces_within_tolerance():
    """Headline literal assertion: Disney's Hexed's disclosed qualified
    spend of $47,538,000 at the sourced 0.35 base rate prices to a gross
    credit of exactly Decimal('16638300.00') (47538000 * 0.35 = 16638300), a
    residue of $300 against the disclosed $16,638,000 allocation — 0.06 bps
    of disclosed spend, comfortably inside the fixture's declared 50 bps
    tolerance."""
    pair = next(p for p in CA_ACTIVE_PAIRS if p["production_title"] == "Disney's Hexed")
    computed = _gross_credit_direct(pair)
    assert computed == Decimal("16638300.00")
    residue = abs(Decimal(pair["credit_amount"]) - computed)
    assert residue == Decimal("300.00")


def test_at_least_two_california_pairs_exercised():
    assert len(CA_ACTIVE_PAIRS) >= 2, (
        f"expected at least 2 active us-ca validation pairs, found {len(CA_ACTIVE_PAIRS)}"
    )


def test_every_active_california_pair_is_allocation_stage():
    """The allocation-versus-issued distinction is the entire point of
    California in this phase (D-97, ROADMAP Phase 5 success criterion 1) —
    it must survive into the data, never be flattened to 'issued'."""
    for pair in CA_ACTIVE_PAIRS:
        assert pair["disclosure_stage"] == "allocated", (
            f"{pair['production_title']}: disclosure_stage is "
            f"{pair['disclosure_stage']!r}, expected 'allocated' — California's "
            "disclosure publishes allocations, never issued credits, and this "
            "distinction must never be silently flattened"
        )

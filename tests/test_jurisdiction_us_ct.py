"""Connecticut-specific validation: literal expected-value assertions and
full statutory-band coverage (JUR-04, plan 05-06).

`tests/test_engine_against_validation_pairs.py` already sweeps every active
Connecticut pair through the direct base-then-credit path and asserts each
against its own fixture-declared `credit_amount` (a data-driven comparison).
This module adds the two guarantees that sweep does not: (1) a literal
Decimal written into the test source itself for each pair, so the reader can
verify the expected figure by hand without cross-referencing a YAML file, and
(2) a structural proof that every rate band `jurisdictions/us-ct.yaml`
declares — not just the one the original fixture happened to exercise — is
backed by a real disclosed government award. Modelled on
`tests/test_engine_against_validation_pairs.py`'s sorted-glob + fail-loud-on-
empty-glob + parametrized-fixture pattern (T-01-15: a parametrized test over
an empty collection is a vacuous green).

Snapshot testing (`syrupy`, `pytest-golden`) is forbidden for validation
pairs by the permitted-testing line in `.claude/CLAUDE.md` — every literal
below was read from a real run of this project's own engine and is checked
by hand-computable arithmetic in a comment beside it, never captured
automatically from whatever the code currently returns.
"""

from decimal import Decimal
from glob import glob

import pytest
import yaml

from engine.credit import compute_gross_credit
from engine.models import load_ruleset
from engine.qualifying_base import SpendBreakdown, compute_qualifying_base

FIXTURE_DIR = "tests/fixtures/validation_pairs"
FIXTURE_PATHS = sorted(glob(f"{FIXTURE_DIR}/*.yaml"))

if not FIXTURE_PATHS:
    raise RuntimeError(
        f"No fixture files found under {FIXTURE_DIR}/*.yaml — an empty "
        "validation-pair set must fail loudly, not report a vacuous green."
    )

CT_RULESET_PATH = "jurisdictions/us-ct.yaml"
CT_JURISDICTION_ID = "us-ct"
CT_RULESET = load_ruleset(CT_RULESET_PATH)
CT_PROGRAMME = next(
    p for p in CT_RULESET.programmes if p.id == "ct-film-digital-media-production-tax-credit"
)


def _load(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _active_ct_pairs() -> list[dict]:
    pairs = []
    for path in FIXTURE_PATHS:
        data = _load(path)
        if data.get("status") != "active":
            continue
        if data.get("jurisdiction_id") != CT_JURISDICTION_ID:
            continue
        pairs.append(data)
    return pairs


CT_ACTIVE_PAIRS = _active_ct_pairs()

if not CT_ACTIVE_PAIRS:
    raise RuntimeError(
        "no active us-ct validation pairs found — an empty Connecticut sweep "
        "must fail loudly, not report a vacuous green."
    )


def _gross_credit_for(pair: dict) -> Decimal:
    programme = next(
        (p for p in CT_RULESET.programmes if p.id == pair["program_id"]), None
    )
    assert programme is not None, (
        f"{pair['production_title']}: no programme matches program_id "
        f"{pair['program_id']!r} — check {CT_RULESET_PATH}'s programme id "
        "against the fixture"
    )
    qualified_spend = Decimal(pair["qualified_spend"])
    spend = SpendBreakdown.from_total(qualified_spend)
    qualifying_base = compute_qualifying_base(
        programme, spend, currency=CT_RULESET.jurisdiction.currency
    )
    gross_credit = compute_gross_credit(programme, qualifying_base)
    return gross_credit.value


def test_at_least_three_active_connecticut_pairs():
    """An empty or shrunken active-pair set must fail loudly, not report a
    vacuous green — mirrors
    tests/test_engine_against_validation_pairs.py::test_at_least_one_connecticut_pair_exercised,
    tightened to the count this plan establishes (one pair per statutory
    band plus the pre-existing top-band anchor)."""
    assert len(CT_ACTIVE_PAIRS) >= 3, (
        f"expected at least 3 active us-ct validation pairs, found "
        f"{len(CT_ACTIVE_PAIRS)}"
    )


@pytest.mark.parametrize(
    "pair", CT_ACTIVE_PAIRS, ids=[p["production_title"] for p in CT_ACTIVE_PAIRS]
)
def test_every_active_pair_declares_the_ct_programme_and_source(pair):
    """Every active Connecticut pair declares the programme id
    jurisdictions/us-ct.yaml actually declares, cites the archived CSV as
    its source_document, and declares disclosure_stage: issued."""
    assert pair["program_id"] == CT_PROGRAMME.id, (
        f"{pair['production_title']}: program_id {pair['program_id']!r} does not "
        f"match the declared programme id {CT_PROGRAMME.id!r} in {CT_RULESET_PATH}"
    )
    assert pair["source_document"] == "sources/ct/2026-08-24-ct-film-tax-credits-issued.csv", (
        f"{pair['production_title']}: source_document "
        f"{pair['source_document']!r} does not cite the archived Connecticut CSV"
    )
    assert pair["disclosure_stage"] == "issued", (
        f"{pair['production_title']}: disclosure_stage "
        f"{pair['disclosure_stage']!r} is not 'issued'"
    )


def test_colony_video_2015_productions_reproduces_exactly():
    """$187,220 qualified spend x the declared 10% rate for the
    $100,000-$500,000 band = $18,722.00 exactly, quantized to $18,722 — no
    rounding residue."""
    pair = next(
        p for p in CT_ACTIVE_PAIRS if p["production_title"] == "Colony Video 2015 Productions"
    )
    computed = _gross_credit_for(pair)
    assert computed == Decimal("18722")


def test_mako_games_reproduces_exactly():
    """$593,380 qualified spend x the declared 15% rate for the
    $500,000-$1,000,000 band = $89,007.00 exactly, quantized to $89,007 —
    no rounding residue."""
    pair = next(p for p in CT_ACTIVE_PAIRS if p["production_title"] == "Mako Games")
    computed = _gross_credit_for(pair)
    assert computed == Decimal("89007")


def test_christmas_always_reproduces_exactly():
    """$3,865,005 qualified spend x the declared 30% rate for the
    $1,000,000+ band = $1,159,501.50, quantized to $1,159,502 — the same
    figure tests/test_engine_against_validation_pairs.py's
    test_christmas_always_reproduces_exactly already proves; restated here
    as a literal so this module alone demonstrates every band."""
    pair = next(p for p in CT_ACTIVE_PAIRS if p["production_title"] == "Christmas Always")
    computed = _gross_credit_for(pair)
    assert computed == Decimal("1159502")


def _tier_id(tier) -> str:
    upper = tier.threshold_high if tier.threshold_high is not None else "inf"
    return f"[{tier.threshold_low}, {upper})"


@pytest.mark.parametrize(
    "tier", CT_PROGRAMME.rate_structure.tiers, ids=_tier_id
)
def test_every_declared_tier_has_a_covering_pair(tier):
    """The substantive new guarantee this module adds: every tier
    jurisdictions/us-ct.yaml's rate_structure.tiers declares has at least
    one active Connecticut pair whose disclosed qualified_spend falls
    inside that tier's band. A declared band nobody ever validated is a
    claim the repo has not earned — this test names the specific
    uncovered band in its failure message rather than reporting a single
    aggregate pass/fail. A null threshold_high is treated as unbounded
    above."""
    low = tier.threshold_low
    high = tier.threshold_high

    def _in_band(spend: Decimal) -> bool:
        return low <= spend and (high is None or spend < high)

    covering = [
        pair["production_title"]
        for pair in CT_ACTIVE_PAIRS
        if _in_band(Decimal(pair["qualified_spend"]))
    ]
    assert covering, (
        f"declared tier {_tier_id(tier)} (rate {tier.rate}) in {CT_RULESET_PATH}'s "
        "rate_structure.tiers has NO active Connecticut validation pair whose "
        "disclosed qualified_spend falls inside it — a declared band nobody ever "
        "validated is a claim the repo has not earned"
    )

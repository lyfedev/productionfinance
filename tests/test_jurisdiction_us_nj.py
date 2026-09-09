"""New Jersey-specific validation: literal expected-value assertions and an
exact, sourced explanation of the one residue that isn't zero (JUR-03, plan
05-05).

Both committed New Jersey pairs are pre-certification ESTIMATES disclosed on
the live NJEDA "Film Tax Credit Activity Report" Power BI dashboard, not
issued/allocated figures the way New York's and California's disclosures are
(see each fixture's own `disclosure_stage: estimated`). Neither the dashboard
row nor `jurisdictions/us-nj.yaml` states a rate — the rule file is built from
four independently-fetched New Jersey government documents archived under
`sources/nj/` (see that file's header comment), never from the dashboard
disclosure itself.

`jurisdictions/us-nj.yaml` deliberately does NOT declare the 2 percent
diversity-plan bonus (N.J.A.C. 19:31T-1.6(o)(1)) as a rate_structure uplift —
it is claimed by some New Jersey productions and not others, and the
dashboard discloses it only as a per-row Yes/No flag, not an itemized dollar
amount. This module is where that choice is made concrete and testable: The
Trial of the Chicago 7 (no bonus claimed) reproduces its disclosed credit
EXACTLY through the base 30% rate alone; Joker (bonus claimed) leaves a
residue against the base-rate-only computation that is asserted, as a Decimal
equality (never a widened tolerance), to equal exactly the sourced 2 percent
bonus rate applied to its own disclosed qualified spend — a fully explained
variance in D-86's taxonomy sense: named, sourced, and quantified.

Snapshot testing (`syrupy`, `pytest-golden`) is forbidden for validation
pairs by the permitted-testing line in `.claude/CLAUDE.md` — every literal
below was read from a real run of this project's own engine and is checked
by hand-computable arithmetic in a comment beside it, never captured
automatically from whatever the code currently returns.

`jurisdictions/us-nj.yaml` declares `mechanism: transferable` (N.J.A.C.
19:31T-1.10(a)'s elective sale/assignment right, available broadly to this
exact programme — see that file's header comment for why this differs from
`jurisdictions/us-ca.yaml`'s `nonrefundable_credit`) with a SOURCED floor
(`transfer_discount.typical_rate_low: "0.75"`, confirmed by four independent
New Jersey documents) but no sourced ceiling (no document located this
session states one). `engine.net_cash.transferable` requires BOTH bounds
before it will convert, so `price_jurisdiction` correctly refuses for every
active New Jersey pair — the same deliberate honesty gate
`tests/test_jurisdiction_us_ct.py` already proves for Connecticut. This is
NOT worked around here: `test_price_jurisdiction_refuses_unsourced_transfer_discount`
below makes the refusal an explicit, asserted, per-pair behaviour, in the
same shape
`tests/test_engine_against_validation_pairs.py::test_christmas_always_reproduces_exactly_through_price_jurisdiction`
already uses for Connecticut's identical gap.
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

NJ_RULESET_PATH = "jurisdictions/us-nj.yaml"
NJ_JURISDICTION_ID = "us-nj"
NJ_RULESET = load_ruleset(NJ_RULESET_PATH)
NJ_PROGRAMME = next(
    p for p in NJ_RULESET.programmes if p.id == "nj-garden-state-film-digital-media-jobs-program"
)


def _load(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _active_nj_pairs() -> list[dict]:
    pairs = []
    for path in FIXTURE_PATHS:
        data = _load(path)
        if data.get("status") != "active":
            continue
        if data.get("jurisdiction_id") != NJ_JURISDICTION_ID:
            continue
        pairs.append(data)
    return pairs


NJ_ACTIVE_PAIRS = _active_nj_pairs()

if not NJ_ACTIVE_PAIRS:
    raise RuntimeError(
        "no active us-nj validation pairs found — an empty New Jersey sweep "
        "must fail loudly, not report a vacuous green."
    )


def _gross_credit_for(pair: dict) -> Decimal:
    programme = next(
        (p for p in NJ_RULESET.programmes if p.id == pair["program_id"]), None
    )
    assert programme is not None, (
        f"{pair['production_title']}: no programme matches program_id "
        f"{pair['program_id']!r} — check {NJ_RULESET_PATH}'s programme id "
        "against the fixture"
    )
    qualified_spend = Decimal(pair["qualified_spend"])
    spend = SpendBreakdown.from_total(qualified_spend)
    qualifying_base = compute_qualifying_base(
        programme, spend, currency=NJ_RULESET.jurisdiction.currency
    )
    gross_credit = compute_gross_credit(programme, qualifying_base)
    return gross_credit.value


def test_at_least_two_active_new_jersey_pairs():
    """A filter matching nothing must fail loudly, not report a vacuous
    green — mirrors
    tests/test_jurisdiction_us_ct.py::test_at_least_three_active_connecticut_pairs,
    tightened to the count this plan establishes: both committed New Jersey
    fixtures, and no more."""
    assert len(NJ_ACTIVE_PAIRS) >= 2, (
        f"expected at least 2 active us-nj validation pairs, found "
        f"{len(NJ_ACTIVE_PAIRS)}"
    )


@pytest.mark.parametrize(
    "pair", NJ_ACTIVE_PAIRS, ids=[p["production_title"] for p in NJ_ACTIVE_PAIRS]
)
def test_every_active_pair_declares_the_nj_programme_and_estimated_stage(pair):
    """Every active New Jersey pair declares the programme id
    jurisdictions/us-nj.yaml actually declares, cites an archived New Jersey
    source document, and stays disclosure_stage: estimated — the dashboard's
    own column headers are pre-certification estimates, never the row's
    separate, later, lower Adjusted Certification figure (see each fixture's
    own notes). Collapsing 'estimated' into 'issued'/'allocated' would be
    exactly the blended-cohort failure D-07 and
    tests/test_validation_pair_fixtures.py::test_disclosure_stages_are_separable
    exist to prevent."""
    assert pair["program_id"] == NJ_PROGRAMME.id, (
        f"{pair['production_title']}: program_id {pair['program_id']!r} does not "
        f"match the declared programme id {NJ_PROGRAMME.id!r} in {NJ_RULESET_PATH}"
    )
    assert pair["source_document"].startswith("sources/nj/"), (
        f"{pair['production_title']}: source_document "
        f"{pair['source_document']!r} does not cite an archived New Jersey source"
    )
    assert pair["disclosure_stage"] == "estimated", (
        f"{pair['production_title']}: disclosure_stage "
        f"{pair['disclosure_stage']!r} is not 'estimated'"
    )


def test_trial_of_the_chicago_7_reproduces_exactly():
    """$17,906,613 disclosed qualified spend x the declared 30% base rate =
    $5,371,983.90, quantized ROUND_HALF_UP to $5,371,984 — the disclosed
    Total Award EXACTLY, no diversity bonus claimed on this row ('No'), zero
    residue. This is the pair that proves the base rate alone, with no
    unexplained gap of any size."""
    pair = next(
        p for p in NJ_ACTIVE_PAIRS if p["production_title"] == "The Trial of the Chicago 7"
    )
    computed = _gross_credit_for(pair)
    assert computed == Decimal("5371984")
    disclosed = Decimal(pair["credit_amount"])
    assert disclosed == computed, (
        "The Trial of the Chicago 7 claims no diversity bonus — the disclosed "
        "credit must equal the base-rate-only computation exactly, with no "
        "residue of any kind"
    )


def test_joker_base_rate_computation():
    """$6,133,257 disclosed qualified spend x the declared 30% base rate =
    $1,839,977.10, quantized ROUND_HALF_UP to $1,839,977 — the base-rate-only
    figure jurisdictions/us-nj.yaml's rate_structure alone produces, BEFORE
    the diversity bonus this file deliberately does not declare as an
    uplift. The next test asserts the gap between this figure and the
    disclosed Total Award."""
    joker = next(p for p in NJ_ACTIVE_PAIRS if p["production_title"] == "Joker")
    computed = _gross_credit_for(joker)
    assert computed == Decimal("1839977")


def test_joker_diversity_bonus_residue_is_exactly_the_sourced_bonus_rate():
    """The substantive new guarantee this module adds, per JUR-03's
    must_haves: Joker's disclosure records a claimed Diversity Bonus ('Yes'),
    and the residue between its disclosed Total Award and the base-rate-only
    computation is asserted, as an exact Decimal equality — never a widened
    tolerance — to equal the sourced 2 percent diversity-plan bonus
    (N.J.A.C. 19:31T-1.6(o)(1) and P.L. 2018, c. 56 Section 4a, both
    independently confirming the identical figure — see
    jurisdictions/us-nj.yaml's header comment and rate_structure.source_note)
    applied to Joker's own disclosed qualified spend:

        disclosed credit_amount:        $1,962,642
        base-rate-only gross credit:    $1,839,977   (see test_joker_base_rate_computation)
        residue:                        $   122,665

        sourced bonus: $6,133,257 (disclosed qualified_spend) x 0.02
                      = $122,665.14, quantized ROUND_HALF_UP to $122,665

    residue == sourced bonus, exactly — a fully explained variance in D-86's
    taxonomy sense (named, sourced, quantified), not an unexplained gap
    absorbed by a tolerance band."""
    joker = next(p for p in NJ_ACTIVE_PAIRS if p["production_title"] == "Joker")
    assert joker["notes"], "expected Joker's fixture to disclose a Diversity Bonus flag"

    disclosed_credit = Decimal(joker["credit_amount"])
    base_rate_only_credit = _gross_credit_for(joker)
    residue = disclosed_credit - base_rate_only_credit

    sourced_bonus = Decimal("122665")  # $6,133,257 x 0.02 = $122,665.14, ROUND_HALF_UP -> $122,665
    assert residue == sourced_bonus, (
        f"Joker: residue {residue} between disclosed credit {disclosed_credit} and "
        f"base-rate-only computed credit {base_rate_only_credit} does not exactly "
        f"equal the sourced 2 percent diversity bonus of {sourced_bonus} — either "
        "the bonus figure or the qualified_spend it was computed against has "
        "changed and this literal must be re-derived, not widened into a tolerance"
    )


def _pipeline_can_complete(pair: dict) -> bool:
    """True unless `pair`'s declared programme is `transferable` without a
    fully-sourced `transfer_discount` range — determined structurally by
    reading the loaded programme's mechanism and its two discount bounds,
    never by matching on jurisdiction id, so a future `us-nj.yaml` update
    that sources a real discount ceiling is picked up automatically rather
    than staying silently excluded. Mirrors
    tests/test_jurisdiction_us_ct.py::_pipeline_can_complete."""
    programme = next(p for p in NJ_RULESET.programmes if p.id == pair["program_id"])
    if programme.mechanism != "transferable":
        return True
    discount = programme.transfer_discount
    return (
        discount.applies
        and discount.typical_rate_low is not None
        and discount.typical_rate_high is not None
    )


@pytest.mark.parametrize(
    "pair", NJ_ACTIVE_PAIRS, ids=[p["production_title"] for p in NJ_ACTIVE_PAIRS]
)
def test_price_jurisdiction_refuses_unsourced_transfer_discount(pair):
    """jurisdictions/us-nj.yaml declares the programme as transferable with
    a sourced FLOOR (typical_rate_low: 0.75, confirmed by four independent
    New Jersey government documents) but no sourced CEILING — no document
    located this session states one — so engine.net_cash.transferable
    correctly refuses to convert rather than invent a ceiling (D-87). This
    makes the refusal a permanent, asserted, per-pair behaviour, in the same
    shape
    tests/test_jurisdiction_us_ct.py::test_price_jurisdiction_refuses_unsourced_transfer_discount
    already establishes for Connecticut's identical (but wholly unsourced,
    not partially-sourced) gap. engine/net_cash.py is not modified by this
    test or by this plan — the refusal is the correct, deliberate honesty
    gate documented in jurisdictions/us-nj.yaml's transfer_discount.source_note,
    not a bug. Do not weaken, bypass, or special-case it to make a pair pass."""
    assert not _pipeline_can_complete(pair), (
        f"{pair['production_title']}: expected price_jurisdiction to currently "
        f"raise (unsourced transfer_discount ceiling on {NJ_RULESET_PATH}) — if this "
        f"now fails, {NJ_RULESET_PATH} has been sourced with a real discount "
        "ceiling and this test should be rewritten to assert the low/high "
        "conversion instead"
    )
    qualified_spend = Decimal(pair["qualified_spend"])
    with pytest.raises(ValueError, match="transfer_discount"):
        price_jurisdiction(NJ_RULESET, qualified_spend)

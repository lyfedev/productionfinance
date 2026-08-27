"""`engine.ranker.rank` — the two-band ranked list (OUT-01, D-55).

Proves the ranked band's multi-city sorting behaviour, D-56's never-zero
guarantee, and both distinct unranked-reason shapes against SYNTHETIC
fixtures (never a real committed city or a Phase 5 rule file pulled
forward — 04-06-PLAN.md's own instruction), plus one test against the
real committed profiles asserting the expected Phase 4 state: exactly one
net_ranked city (New York) and two incentive_not_modelled cities (Los
Angeles, London).
"""

from __future__ import annotations

import inspect
from decimal import Decimal

from engine.budget import build_canonical_budget
from engine.cost_localizer import LocalizedBudget, localize, quarter_start_date
from engine.cost_profile import load_cost_profile
from engine.landed_cost import aggregate
from engine.models import JurisdictionRuleSet, TransferDiscount, load_ruleset
from engine.ranker import rank
from engine.spec import CrewHeadcount, ProductionSpec

COST_PROFILE_FIXTURE_DIR = "tests/fixtures/cost_profiles"
JURISDICTION_FIXTURE_DIR = "tests/fixtures/jurisdictions"
MECH_FIXTURE = f"{JURISDICTION_FIXTURE_DIR}/synthetic-mechanisms.yaml"
RANKED_PROFILE = f"{COST_PROFILE_FIXTURE_DIR}/synthetic-ranked.yaml"
UNRANKED_PROFILE = f"{COST_PROFILE_FIXTURE_DIR}/synthetic-unranked.yaml"


def _spec(crew_size: int) -> ProductionSpec:
    return ProductionSpec.model_validate(
        {
            "production_type": "feature",
            "shoot_days_stage": 10,
            "shoot_days_location": 5,
            "crew_size": crew_size,
            "crew_tier": None,
            "principal_cast_count": 3,
            "principal_cast_imported_count": 0,
            "crew_imported_count": 0,
            "crew_hired_locally_count": crew_size,
            "start_quarter": "Q2",
            "start_year": 2026,
            "candidate_cities": ["Synthetic City"],
        }
    )


def _headcount(n: int) -> CrewHeadcount:
    return CrewHeadcount(
        low=n, high=n, basis="supplied by the visitor", provenance_note="test fixture"
    )


def _localized(profile_path: str, crew_size: int) -> LocalizedBudget:
    profile = load_cost_profile(profile_path)
    budget = build_canonical_budget(_spec(crew_size), _headcount(crew_size))
    return localize(budget, profile)


def _mechanisms_ruleset() -> JurisdictionRuleSet:
    return load_ruleset(MECH_FIXTURE)


def _broken_transferable_ruleset() -> JurisdictionRuleSet:
    """A ruleset carrying ONLY the mechanisms fixture's `transferable`
    programme, with `transfer_discount` incompletely declared — the exact
    shape `jurisdictions/us-ct.yaml`'s real transfer_discount takes
    (WINDOWS.md entry 3): `applies=True` but both rate bounds `None`.
    `engine.net_cash.transferable` refuses to convert at an unsourced
    rate, so `price_jurisdiction` raises for this ruleset."""
    base = load_ruleset(MECH_FIXTURE)
    transferable_programme = next(
        p for p in base.programmes if p.id == "mechanisms-transferable"
    )
    broken_programme = transferable_programme.model_copy(
        update={
            "transfer_discount": TransferDiscount(
                applies=True,
                typical_rate_low=None,
                typical_rate_high=None,
                source_note=None,
            )
        }
    )
    return JurisdictionRuleSet(jurisdiction=base.jurisdiction, programmes=[broken_programme])


# ---------------------------------------------------------------------------
# Two-band sort order (D-55) — synthetic fixtures
# ---------------------------------------------------------------------------


def test_ranked_and_unranked_bands_never_interleave_even_when_unranked_total_is_lower():
    """Two net-ranked synthetic cities of different scale sort ascending by
    NET total among themselves; a synthetic unranked city whose cost-only
    total is LOWER than both still sorts after every net-ranked city
    (D-55 — never interleaved as though comparable)."""
    ruleset_by_jurisdiction = {"zz-synthetic-mechanisms": _mechanisms_ruleset()}
    localized_by_city = {
        "ranked-small": _localized(RANKED_PROFILE, 50),
        "ranked-large": _localized(RANKED_PROFILE, 200),
        "unranked-cheap": _localized(UNRANKED_PROFILE, 50),
    }

    result = rank(localized_by_city, ruleset_by_jurisdiction, reporting_currency="USD")

    assert [c.city_id for c in result] == ["ranked-large", "ranked-small", "unranked-cheap"]
    bands = [c.band for c in result]
    assert bands == ["net_ranked", "net_ranked", "incentive_not_modelled"]

    ranked_cities = [c for c in result if c.band == "net_ranked"]
    assert ranked_cities[0].total_landed_cost.value <= ranked_cities[1].total_landed_cost.value

    unranked_city = next(c for c in result if c.city_id == "unranked-cheap")
    ranked_values = [c.total_landed_cost.value for c in ranked_cities]
    assert unranked_city.total_landed_cost.value < min(ranked_values)


def test_unranked_total_landed_cost_equals_cost_only_total_and_is_never_zero():
    localized_by_city = {"unranked-cheap": _localized(UNRANKED_PROFILE, 50)}
    result = rank(localized_by_city, ruleset_by_jurisdiction={}, reporting_currency="USD")

    assert len(result) == 1
    city = result[0]
    assert city.band == "incentive_not_modelled"
    assert city.total_landed_cost.value == city.cost_only_total.value
    assert city.total_landed_cost.value != Decimal("0")
    assert city.incentive_figure is None


def test_no_rule_file_reason_names_the_absence_never_a_zero_incentive():
    localized_by_city = {"unranked-cheap": _localized(UNRANKED_PROFILE, 50)}
    result = rank(localized_by_city, ruleset_by_jurisdiction={}, reporting_currency="USD")

    city = result[0]
    assert city.reason is not None
    assert "no curated or live-researched rule file exists" in city.reason
    assert city.total_landed_cost.value != Decimal("0")


def test_rule_file_exists_but_net_cash_refuses_falls_into_unranked_without_raising():
    """The CT/WINDOWS-entry-3 shape: a rule file exists, but its
    transferable mechanism cannot convert to net cash because the
    discount rate is unsourced. `rank` must not raise — it places the
    city in the unranked band carrying the underlying refusal message
    verbatim."""
    broken = load_cost_profile(RANKED_PROFILE).model_copy(
        update={"city_id": "synthetic-broken", "jurisdiction_id": "zz-synthetic-broken"}
    )
    budget = build_canonical_budget(_spec(50), _headcount(50))
    localized = localize(budget, broken)

    ruleset_by_jurisdiction = {"zz-synthetic-broken": _broken_transferable_ruleset()}
    result = rank({"broken-city": localized}, ruleset_by_jurisdiction, reporting_currency="USD")

    assert len(result) == 1
    city = result[0]
    assert city.band == "incentive_not_modelled"
    assert city.incentive_figure is None
    assert city.total_landed_cost.value == city.cost_only_total.value
    assert city.reason is not None
    assert "a rule file exists for jurisdiction 'zz-synthetic-broken'" in city.reason
    # The underlying refusal message is carried VERBATIM.
    assert (
        "mechanism is 'transferable' but transfer_discount does not fully declare"
        in city.reason
    )


def test_both_unranked_reason_shapes_are_produced_by_the_conditions_that_cause_them():
    """Reason (a) — no rule file at all — and reason (b) — a rule file
    exists but net cash cannot be computed — are genuinely distinct
    strings, each produced by the condition that actually causes it."""
    no_file_localized = _localized(UNRANKED_PROFILE, 50)

    broken = load_cost_profile(RANKED_PROFILE).model_copy(
        update={"city_id": "synthetic-broken", "jurisdiction_id": "zz-synthetic-broken"}
    )
    broken_localized = localize(
        build_canonical_budget(_spec(50), _headcount(50)), broken
    )

    result = rank(
        {"no-file": no_file_localized, "broken": broken_localized},
        {"zz-synthetic-broken": _broken_transferable_ruleset()},
        reporting_currency="USD",
    )

    reasons = {c.city_id: c.reason for c in result}
    assert reasons["no-file"] != reasons["broken"]
    assert "no curated or live-researched rule file exists" in reasons["no-file"]
    assert "cannot be computed" in reasons["broken"]


def test_net_ranked_city_carries_a_populated_incentive_figure():
    ruleset_by_jurisdiction = {"zz-synthetic-mechanisms": _mechanisms_ruleset()}
    result = rank(
        {"ranked-small": _localized(RANKED_PROFILE, 50)},
        ruleset_by_jurisdiction,
        reporting_currency="USD",
    )

    assert len(result) == 1
    city = result[0]
    assert city.band == "net_ranked"
    assert city.reason is None
    assert city.incentive_figure is not None
    assert city.cost_only_total.value == Decimal("37500")


# ---------------------------------------------------------------------------
# The real committed profiles — the expected Phase 4 state (04-CONTEXT.md
# phase boundary): only New York has a committed rule file.
# ---------------------------------------------------------------------------


def _real_localized(profile_path: str) -> LocalizedBudget:
    spec = ProductionSpec.model_validate(
        {
            "production_type": "feature",
            "shoot_days_stage": 10,
            "shoot_days_location": 5,
            "crew_size": 50,
            "crew_tier": None,
            "principal_cast_count": 3,
            "principal_cast_imported_count": 1,
            "crew_imported_count": 10,
            "crew_hired_locally_count": 40,
            "start_quarter": "Q2",
            "start_year": 2026,
            "candidate_cities": ["placeholder"],
        }
    )
    headcount = CrewHeadcount(
        low=50, high=50, basis="supplied by the visitor", provenance_note="test fixture"
    )
    profile = load_cost_profile(profile_path)
    budget = build_canonical_budget(spec, headcount)
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)
    return localize(budget, profile, on_date=on_date, spec=spec)


def test_real_committed_profiles_produce_exactly_one_net_ranked_city():
    localized_by_city = {
        "us-ny-new-york": _real_localized("data/cost_profiles/us-ny-new-york.yaml"),
        "us-ca-los-angeles": _real_localized("data/cost_profiles/us-ca-los-angeles.yaml"),
        "gb-london": _real_localized("data/cost_profiles/gb-london.yaml"),
    }
    ruleset_by_jurisdiction = {"us-ny": load_ruleset("jurisdictions/us-ny.yaml")}

    result = rank(localized_by_city, ruleset_by_jurisdiction, reporting_currency="USD")

    net_ranked = [c for c in result if c.band == "net_ranked"]
    unranked = [c for c in result if c.band == "incentive_not_modelled"]
    # The asserted expected Phase 4 state (04-CONTEXT.md): one net-ranked
    # city until Phase 5 lands more rule files. This is NOT a gap.
    assert len(net_ranked) == 1
    assert net_ranked[0].city_id == "us-ny-new-york"
    assert len(unranked) == 2
    assert {c.city_id for c in unranked} == {"us-ca-los-angeles", "gb-london"}
    for city in unranked:
        assert city.total_landed_cost.value != Decimal("0")
        assert "no curated or live-researched rule file exists" in city.reason
        # Every city's total is expressed in the SAME reporting currency
        # (D-55/D-75) — never a raw GBP number sorted against raw USD.
        assert city.total_landed_cost.unit == "USD"
        assert city.landed_cost.reporting_currency == "USD"


def test_unranked_band_compares_a_gbp_city_and_a_usd_city_in_the_same_currency():
    """London (GBP) and Los Angeles (USD) both land in the unranked band.
    `rank` must convert London into the shared `reporting_currency`
    BEFORE comparing — never sort on London's raw GBP number against Los
    Angeles's raw USD number as though they were the same unit (D-55)."""
    localized_by_city = {
        "us-ca-los-angeles": _real_localized("data/cost_profiles/us-ca-los-angeles.yaml"),
        "gb-london": _real_localized("data/cost_profiles/gb-london.yaml"),
    }

    result = rank(localized_by_city, ruleset_by_jurisdiction={}, reporting_currency="USD")

    assert len(result) == 2
    assert {c.total_landed_cost.unit for c in result} == {"USD"}
    la = next(c for c in result if c.city_id == "us-ca-los-angeles")
    london = next(c for c in result if c.city_id == "gb-london")

    # London's total, CONVERTED to USD, genuinely exceeds Los Angeles's —
    # asserted against the converted Figure, never the raw GBP number.
    assert london.landed_cost.source_currency == "GBP"
    assert london.landed_cost.reporting_currency == "USD"
    assert london.total_landed_cost.value > la.total_landed_cost.value

    # The bug this proves fixed: London's RAW (unconverted) GBP total is
    # numerically LOWER than Los Angeles's raw USD total — comparing the
    # two without conversion would have produced the opposite (wrong)
    # order.
    raw_london = aggregate(localized_by_city["gb-london"])
    assert raw_london.cost_total.value < la.landed_cost.cost_total.value


# ---------------------------------------------------------------------------
# JUR-05/D-53 — no jurisdiction identifier literal in this module's source
# ---------------------------------------------------------------------------


def test_no_jurisdiction_id_literal_in_ranker_module():
    import engine.ranker as ranker_module

    source = inspect.getsource(ranker_module)
    for literal in ('"us-ny"', '"us-ca"', '"gb-london"'):
        assert literal not in source

"""`engine.exemptions` — INC-10's stackable cost-side reductions, and the
D-76 guarantee that an exemption Figure is never reachable from the
incentive Figure DAG `engine.pipeline.price_jurisdiction` returns, and
never increases the reported gross credit.

Covers: schema validation, the matching-by-category discipline (never a
positional index, never a substring), the stacking shape (two exemptions
on one category are both independent Figures), and the four D-76 proof
points named in 04-04-PLAN.md Task 3.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from engine.budget import build_canonical_budget
from engine.cost_localizer import localize, quarter_start_date
from engine.cost_profile import load_cost_profile
from engine.exemptions import (
    EXEMPTIONS_PATH_BY_ID,
    ExemptionEntry,
    ExemptionsTable,
    exemption_reductions,
    load_exemptions,
)
from engine.figure import Figure
from engine.landed_cost import aggregate
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction
from engine.spec import CrewHeadcount, ProductionSpec


def _spec(**overrides) -> ProductionSpec:
    base = {
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
        "candidate_cities": ["New York, NY"],
    }
    base.update(overrides)
    return ProductionSpec.model_validate(base)


def _crew_headcount() -> CrewHeadcount:
    return CrewHeadcount(
        low=50, high=50, basis="supplied by the visitor", provenance_note="test fixture"
    )


def _ny_profile():
    return load_cost_profile("data/cost_profiles/us-ny-new-york.yaml")


def _entry(**overrides) -> dict:
    base = {
        "exemption_id": "synthetic-exemption",
        "label": "Synthetic exemption",
        "applies_to_category": "equipment",
        "kind": "sales_tax",
        "rate": "0.10",
        "basis": "estimated",
        "source_url": None,
        "date_checked": None,
        "method_note": "a synthetic test fixture method note",
        "eligibility_note": "a synthetic test fixture eligibility note",
    }
    base.update(overrides)
    return base


def _figure(value: Decimal, label: str = "Equipment") -> Figure:
    return Figure(
        value=value,
        unit="USD",
        label=label,
        derivation=("synthetic test fixture Figure",),
        inputs=(),
        source_url=None,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis="modelling_assumption",
    )


def _walk(figure: Figure) -> list[Figure]:
    visited = [figure]
    for child in figure.inputs:
        visited.extend(_walk(child))
    return visited


# ---------------------------------------------------------------------------
# Schema — validation and the required-field discipline
# ---------------------------------------------------------------------------


def test_both_committed_exemptions_tables_load():
    for exemptions_id in ("us-ny-new-york", "us-ca-los-angeles"):
        table = load_exemptions(exemptions_id)
        assert table.exemptions
        for entry in table.exemptions:
            assert entry.method_note.strip()
            assert entry.eligibility_note.strip()


def test_exemptions_path_by_id_discovers_both_committed_files():
    assert "us-ny-new-york" in EXEMPTIONS_PATH_BY_ID
    assert "us-ca-los-angeles" in EXEMPTIONS_PATH_BY_ID


def test_load_exemptions_raises_for_unknown_id():
    with pytest.raises(ValueError, match="no committed exemptions table"):
        load_exemptions("does-not-exist")


def test_sourced_requires_source_url():
    with pytest.raises(ValidationError, match="source_url"):
        ExemptionEntry.model_validate(_entry(basis="sourced", source_url=None))


def test_method_note_and_eligibility_note_must_be_non_empty():
    with pytest.raises(ValidationError, match="method_note"):
        ExemptionEntry.model_validate(_entry(method_note=""))
    with pytest.raises(ValidationError, match="eligibility_note"):
        ExemptionEntry.model_validate(_entry(eligibility_note=""))


def test_duplicate_exemption_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        ExemptionsTable.model_validate(
            {
                "exemptions_id": "synthetic",
                "city_label": "Synthetic City",
                "provenance_note": "synthetic fixture",
                "exemptions": [_entry(), _entry()],
            }
        )


def test_empty_exemptions_list_is_legal():
    table = ExemptionsTable.model_validate(
        {
            "exemptions_id": "synthetic-empty",
            "city_label": "Synthetic City",
            "provenance_note": "a city offering no exemption",
            "exemptions": [],
        }
    )
    assert table.exemptions == []


# ---------------------------------------------------------------------------
# exemption_reductions — matching, stacking, and the never-silently-dropped
# guarantee
# ---------------------------------------------------------------------------


def test_reduction_value_is_negative_rate_times_target_pre_reduction_value():
    table = ExemptionsTable.model_validate(
        {
            "exemptions_id": "synthetic",
            "city_label": "Synthetic City",
            "provenance_note": "synthetic fixture",
            "exemptions": [_entry(rate="0.10")],
        }
    )
    target = _figure(Decimal("1000"))
    (reduction,) = exemption_reductions(table, {"equipment": [target]}, "USD")
    assert reduction.value == Decimal("-100")
    assert reduction.inputs == (target,)


def test_exemption_matching_absent_category_raises_naming_exemption_id():
    table = ExemptionsTable.model_validate(
        {
            "exemptions_id": "synthetic",
            "city_label": "Synthetic City",
            "provenance_note": "synthetic fixture",
            "exemptions": [_entry(exemption_id="ny-sales-tax-production-equipment")],
        }
    )
    with pytest.raises(ValueError, match="ny-sales-tax-production-equipment"):
        exemption_reductions(table, {}, "USD")


def test_ambiguous_multiple_matches_raises():
    table = ExemptionsTable.model_validate(
        {
            "exemptions_id": "synthetic",
            "city_label": "Synthetic City",
            "provenance_note": "synthetic fixture",
            "exemptions": [_entry()],
        }
    )
    with pytest.raises(ValueError, match="ambiguous"):
        exemption_reductions(
            table, {"equipment": [_figure(Decimal("100")), _figure(Decimal("200"))]}, "USD"
        )


def test_two_exemptions_same_category_both_appear_as_separate_figures():
    table = ExemptionsTable.model_validate(
        {
            "exemptions_id": "synthetic",
            "city_label": "Synthetic City",
            "provenance_note": "synthetic fixture",
            "exemptions": [
                _entry(exemption_id="first", rate="0.10"),
                _entry(exemption_id="second", rate="0.05"),
            ],
        }
    )
    target = _figure(Decimal("1000"))
    reductions = exemption_reductions(table, {"equipment": [target]}, "USD")
    assert len(reductions) == 2
    assert {r.figure_id for r in reductions} == {reductions[0].figure_id, reductions[1].figure_id}
    assert len({r.figure_id for r in reductions}) == 2
    # Each applies independently to the PRE-reduction target value — never
    # chained against a running total (stacking, not compounding).
    assert reductions[0].value == Decimal("-100")
    assert reductions[1].value == Decimal("-50")


# ---------------------------------------------------------------------------
# D-76 — the four proof points, against the real committed New York data
# ---------------------------------------------------------------------------


def _localized_and_priced(*, with_exemptions: bool):
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)

    profile = _ny_profile()
    if not with_exemptions:
        profile = profile.model_copy(update={"exemptions_id": None})

    localized = localize(budget, profile, on_date=on_date, spec=spec)
    ruleset = load_ruleset("jurisdictions/us-ny.yaml")
    priced = price_jurisdiction(
        ruleset,
        localized.spend_breakdown.total_spend,
        spend_breakdown=localized.spend_breakdown,
        spend_confidence="researched",
    )
    return localized, priced


def test_exemption_figure_ids_are_disjoint_from_the_incentive_dag():
    localized, priced = _localized_and_priced(with_exemptions=True)

    exemption_figures = [line for line in localized.lines if line.label.startswith("Sales tax")]
    assert exemption_figures, "expected New York's committed sales-tax exemption to be present"
    exemption_ids = {f.figure_id for f in exemption_figures}

    incentive_dag_ids = {node.figure_id for node in _walk(priced.total_net_cash)}

    assert exemption_ids.isdisjoint(incentive_dag_ids), (
        "an exemption reduction Figure's id was found inside the incentive DAG "
        f"returned by price_jurisdiction: {exemption_ids & incentive_dag_ids!r} — "
        "D-76 requires these to be fully disjoint"
    )


def test_gross_credit_is_never_greater_with_exemptions_than_without():
    _, priced_with = _localized_and_priced(with_exemptions=True)
    _, priced_without = _localized_and_priced(with_exemptions=False)

    assert priced_with.total_net_cash.value <= priced_without.total_net_cash.value
    assert priced_with.total_net_cash.value < priced_without.total_net_cash.value, (
        "New York's committed sales-tax exemption reduces the Equipment line, which "
        "reduces total_spend fed into price_jurisdiction — the gross credit must "
        "therefore be strictly lower with the exemption present"
    )


def test_cost_total_delta_equals_the_summed_reduction_amount_exactly():
    spec = _spec()
    budget = build_canonical_budget(spec, _crew_headcount())
    on_date = quarter_start_date(spec.start_quarter, spec.start_year)

    profile_with = _ny_profile()
    profile_without = profile_with.model_copy(update={"exemptions_id": None})

    localized_with = localize(budget, profile_with, on_date=on_date, spec=spec)
    localized_without = localize(budget, profile_without, on_date=on_date, spec=spec)

    landed_with = aggregate(localized_with)
    landed_without = aggregate(localized_without)

    reductions = [line for line in localized_with.lines if line.label.startswith("Sales tax")]
    summed_reduction = sum((r.value for r in reductions), start=Decimal("0"))

    assert landed_with.cost_total.value - landed_without.cost_total.value == summed_reduction


def test_no_jurisdiction_id_literal_in_exemptions_module():
    import re

    with open("engine/exemptions.py", encoding="utf-8") as handle:
        source = handle.read()
    assert not re.search(r'"us-ny"|"us-ca"', source)

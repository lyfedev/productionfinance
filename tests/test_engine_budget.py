"""`engine.budget` — the D-38 department decomposition and COST-01's
one-canonical-budget invariant.

Covers: every tier's department `crew_share` values sum to exactly
`Decimal("1")`; an unknown tier raises rather than returning a default
department set; every emitted budget line carries a closed-set `account`
tag; and the department split is a decomposition, never a new number —
`CanonicalBudget.total_quantity` equals exactly what a single undivided
crew-labour-days line would have computed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.budget import build_canonical_budget, resolve_departments
from engine.spec import CREW_TIERS_PATH, CrewHeadcount, ProductionSpec, UnknownCrewTierError

# Mirrors the five CrewTier literal values (engine.spec.CrewTier) and the
# OUT-04/D-77 closed account vocabulary — deliberately re-declared here
# rather than importing engine.budget's private module constants, so this
# test exercises the public contract only.
_ALL_TIERS = ("micro", "small", "mid", "large", "tentpole")
_LEGAL_ACCOUNTS = ("ATL", "BTL", "POST")


def _make_spec(**overrides: object) -> ProductionSpec:
    kwargs = {
        "production_type": "feature",
        "shoot_days_stage": 10,
        "shoot_days_location": 5,
        "crew_size": None,
        "crew_tier": "mid",
        "principal_cast_count": 3,
        "principal_cast_imported_count": 1,
        "crew_imported_count": 0,
        "crew_hired_locally_count": 0,
        "start_quarter": "Q2",
        "start_year": 2026,
        "candidate_cities": ["New York, NY"],
    }
    kwargs.update(overrides)
    return ProductionSpec.model_validate(kwargs)


# ---------------------------------------------------------------------------
# The department table itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tier", _ALL_TIERS)
def test_every_tiers_department_shares_sum_to_exactly_one(tier: str):
    departments = resolve_departments(tier)
    assert departments, f"expected at least one department for tier {tier!r}"
    total = sum((department.crew_share for department in departments), start=Decimal("0"))
    assert total == Decimal("1"), (
        f"tier {tier!r}'s department crew_share values sum to {total}, not exactly "
        "Decimal('1') — a silent residue would be an unpriced department wearing "
        "no label"
    )


def test_unknown_tier_raises_rather_than_returning_a_default_department_set():
    with pytest.raises(UnknownCrewTierError):
        resolve_departments("does-not-exist")  # type: ignore[arg-type]


def test_every_department_carries_a_legal_account_tag():
    for tier in _ALL_TIERS:
        for department in resolve_departments(tier):
            assert department.account in _LEGAL_ACCOUNTS, (
                f"department {department.name!r} (tier {tier!r}) carries account "
                f"{department.account!r}, not one of {_LEGAL_ACCOUNTS}"
            )


def test_crew_tiers_yaml_still_declares_no_confidence_or_status_key():
    """`data/crew_tiers.yaml` must never declare a `confidence` or `status`
    key — that vocabulary is reserved for jurisdictions/*.yaml rule files
    reproducing an actual government disclosure (RD-02)."""
    with open(CREW_TIERS_PATH, encoding="utf-8") as handle:
        kept_lines = [
            line for line in handle.read().splitlines() if not line.strip().startswith("#")
        ]
    non_comment_source = "\n".join(kept_lines)
    assert "confidence:" not in non_comment_source
    assert "status:" not in non_comment_source


# ---------------------------------------------------------------------------
# build_canonical_budget — the decomposition proof
# ---------------------------------------------------------------------------


def test_canonical_budget_total_quantity_equals_the_undivided_single_line_quantity():
    """D-38's department split is a decomposition, never a new number: the
    sum of every department's labour-days quantity must equal exactly what
    a single undivided crew-labour-days line (shoot_days x headcount low
    bound) would have computed."""
    spec = _make_spec()
    crew_headcount = CrewHeadcount(
        low=90, high=120, basis="modelling_assumption", provenance_note="test fixture"
    )
    budget = build_canonical_budget(spec, crew_headcount)

    expected_total = Decimal(spec.shoot_days_stage + spec.shoot_days_location) * Decimal(
        crew_headcount.low
    )
    assert budget.total_quantity == expected_total


def test_canonical_budget_emits_one_line_per_department_each_with_an_account():
    spec = _make_spec()
    crew_headcount = CrewHeadcount(
        low=90, high=120, basis="modelling_assumption", provenance_note="test fixture"
    )
    budget = build_canonical_budget(spec, crew_headcount)

    expected_labels = {department.label for department in resolve_departments("mid")}
    assert set(budget.line_quantities) == expected_labels
    assert set(budget.accounts) == expected_labels
    for label in expected_labels:
        assert budget.accounts[label] in _LEGAL_ACCOUNTS
        assert budget.line_quantities[label] >= Decimal("0")


def test_canonical_budget_infers_tier_from_explicit_crew_size():
    """A visitor may supply an explicit crew_size instead of a tier
    (INP-03) — the department decomposition must still resolve to SOME
    committed tier bracket rather than raising, and the resulting total
    quantity must still decompose exactly."""
    spec = _make_spec(crew_tier=None, crew_size=90, crew_imported_count=20, crew_hired_locally_count=70)
    crew_headcount = CrewHeadcount(
        low=90, high=90, basis="supplied by the visitor", provenance_note="explicit"
    )
    budget = build_canonical_budget(spec, crew_headcount)

    expected_total = Decimal(spec.shoot_days_stage + spec.shoot_days_location) * Decimal(90)
    assert budget.total_quantity == expected_total

"""`engine.facilities` — the committed schema and pricing path for the
five never-sourced cost categories COST-06 names: stages, equipment,
permits, locations and trucking.

Covers the schema-load happy path, the structural `basis: "sourced"`
rejection (COST-06), the `method_note`/`anchor_note` disclosure
requirements, and `facilities_lines`' low-bound pricing treatment with its
per-category driving-quantity dispatch (Task 2's stated mapping).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from engine.facilities import (
    FACILITIES_CATEGORIES,
    FACILITIES_PATH_BY_ID,
    FacilitiesEntry,
    FacilitiesTable,
    facilities_lines,
    load_facilities,
)


def _entry(**overrides) -> dict:
    base = {
        "category": "stages",
        "rate_low": "1000",
        "rate_high": "2000",
        "rate_unit": "shoot_day",
        "basis": "modelling_assumption",
        "source_url": None,
        "date_checked": None,
        "anchor_note": None,
        "method_note": "a synthetic test fixture method note",
    }
    base.update(overrides)
    return base


def _table(entries: dict[str, dict]) -> FacilitiesTable:
    return FacilitiesTable.model_validate(
        {
            "facilities_id": "synthetic-facilities",
            "city_label": "Synthetic City",
            "provenance_note": "synthetic fixture for tests/test_engine_facilities.py",
            "entries": entries,
        }
    )


def _full_table(**per_category_overrides) -> FacilitiesTable:
    entries = {}
    for category in FACILITIES_CATEGORIES:
        overrides = dict(per_category_overrides.get(category, {}))
        overrides.setdefault("category", category)
        entries[category] = _entry(**overrides)
    return _table(entries)


# ---------------------------------------------------------------------------
# Schema — the happy path and COST-06's structural guarantee
# ---------------------------------------------------------------------------


def test_both_committed_facilities_tables_load_with_all_five_categories():
    for facilities_id in ("us-ny-new-york", "us-ca-los-angeles"):
        table = load_facilities(facilities_id)
        assert set(table.entries) == set(FACILITIES_CATEGORIES)
        for category, entry in table.entries.items():
            assert entry.category == category
            assert entry.method_note.strip()
            assert entry.basis in ("estimated", "modelling_assumption")


def test_loading_a_facilities_entry_with_basis_sourced_raises_naming_cost06():
    with pytest.raises(ValidationError, match="COST-06"):
        FacilitiesEntry.model_validate(_entry(basis="sourced"))


def test_method_note_must_be_non_empty():
    with pytest.raises(ValidationError, match="method_note"):
        FacilitiesEntry.model_validate(_entry(method_note=""))


def test_source_url_requires_anchor_note():
    with pytest.raises(ValidationError, match="anchor_note"):
        FacilitiesEntry.model_validate(
            _entry(
                basis="estimated",
                source_url="https://example.invalid/anchor",
                anchor_note=None,
            )
        )


def test_source_url_with_anchor_note_is_legal():
    entry = FacilitiesEntry.model_validate(
        _entry(
            basis="estimated",
            source_url="https://example.invalid/anchor",
            anchor_note="the named anchor listing",
        )
    )
    assert entry.anchor_note == "the named anchor listing"


def test_table_rejects_missing_category():
    entries = {c: _entry(category=c) for c in FACILITIES_CATEGORIES if c != "trucking"}
    with pytest.raises(ValidationError, match="trucking"):
        _table(entries)


def test_table_rejects_unrecognised_category():
    entries = {c: _entry(category=c) for c in FACILITIES_CATEGORIES}
    entries["parking"] = _entry(category="parking")
    with pytest.raises(ValidationError, match="parking"):
        _table(entries)


def test_table_rejects_key_category_mismatch():
    entries = {c: _entry(category=c) for c in FACILITIES_CATEGORIES}
    entries["stages"] = _entry(category="equipment")
    with pytest.raises(ValidationError, match="stages"):
        _table(entries)


def test_facilities_path_by_id_discovers_both_committed_files():
    assert "us-ny-new-york" in FACILITIES_PATH_BY_ID
    assert "us-ca-los-angeles" in FACILITIES_PATH_BY_ID


def test_load_facilities_raises_for_unknown_id():
    with pytest.raises(ValueError, match="no committed facilities table"):
        load_facilities("does-not-exist")


# ---------------------------------------------------------------------------
# facilities_lines — driving quantity dispatch and the low-bound treatment
# ---------------------------------------------------------------------------


def test_stages_is_driven_by_stage_shoot_days_only():
    table = _full_table()
    figures = facilities_lines(
        table,
        shoot_days_stage=Decimal("7"),
        shoot_days_location=Decimal("99"),
        total_shoot_days=Decimal("999"),
        currency="USD",
    )
    stages = next(f for f in figures if f.label == "Stages")
    assert stages.value == Decimal("7") * Decimal("1000")


def test_locations_and_permits_are_driven_by_location_shoot_days_only():
    table = _full_table()
    figures = facilities_lines(
        table,
        shoot_days_stage=Decimal("99"),
        shoot_days_location=Decimal("4"),
        total_shoot_days=Decimal("999"),
        currency="USD",
    )
    by_label = {f.label: f for f in figures}
    assert by_label["Locations"].value == Decimal("4") * Decimal("1000")
    assert by_label["Permits"].value == Decimal("4") * Decimal("1000")


def test_equipment_and_trucking_are_driven_by_total_shoot_days_only():
    table = _full_table()
    figures = facilities_lines(
        table,
        shoot_days_stage=Decimal("3"),
        shoot_days_location=Decimal("2"),
        total_shoot_days=Decimal("5"),
        currency="USD",
    )
    by_label = {f.label: f for f in figures}
    assert by_label["Equipment"].value == Decimal("5") * Decimal("1000")
    assert by_label["Trucking"].value == Decimal("5") * Decimal("1000")


def test_low_bound_treatment_and_derivation_states_both_bounds():
    table = _full_table(stages={"rate_low": "2500", "rate_high": "6000"})
    figures = facilities_lines(
        table,
        shoot_days_stage=Decimal("10"),
        shoot_days_location=Decimal("0"),
        total_shoot_days=Decimal("10"),
        currency="USD",
    )
    stages = next(f for f in figures if f.label == "Stages")
    # LOW bound, never the midpoint (4250) or the high bound (6000).
    assert stages.value == Decimal("10") * Decimal("2500")
    joined_derivation = " ".join(stages.derivation)
    assert "2500" in joined_derivation
    assert "6000" in joined_derivation
    assert "LOW BOUND" in joined_derivation


def test_flat_rate_unit_prices_a_single_unit_regardless_of_days():
    table = _full_table(permits={"rate_unit": "flat", "rate_low": "500", "rate_high": "1500"})
    figures = facilities_lines(
        table,
        shoot_days_stage=Decimal("50"),
        shoot_days_location=Decimal("50"),
        total_shoot_days=Decimal("100"),
        currency="USD",
    )
    permits = next(f for f in figures if f.label == "Permits")
    assert permits.value == Decimal("500")


def test_week_rate_unit_converts_days_via_shoot_days_per_week():
    from engine.seasonality import SHOOT_DAYS_PER_WEEK

    table = _full_table(equipment={"rate_unit": "week", "rate_low": "1000", "rate_high": "2000"})
    figures = facilities_lines(
        table,
        shoot_days_stage=Decimal("0"),
        shoot_days_location=Decimal("0"),
        total_shoot_days=Decimal(SHOOT_DAYS_PER_WEEK) * 2,
        currency="USD",
    )
    equipment = next(f for f in figures if f.label == "Equipment")
    assert equipment.value == Decimal("2") * Decimal("1000")


def test_every_figure_carries_the_committed_basis_and_researched_confidence():
    table = _full_table(stages={"basis": "modelling_assumption"})
    figures = facilities_lines(
        table,
        shoot_days_stage=Decimal("1"),
        shoot_days_location=Decimal("1"),
        total_shoot_days=Decimal("2"),
        currency="USD",
    )
    for figure in figures:
        assert figure.basis == "modelling_assumption"
        assert figure.confidence == "researched"


def test_facilities_lines_returns_all_five_categories_in_declared_order():
    table = _full_table()
    figures = facilities_lines(
        table,
        shoot_days_stage=Decimal("1"),
        shoot_days_location=Decimal("1"),
        total_shoot_days=Decimal("2"),
        currency="USD",
    )
    assert tuple(f.label for f in figures) == (
        "Stages",
        "Equipment",
        "Permits",
        "Locations",
        "Trucking",
    )


# ---------------------------------------------------------------------------
# JUR-05 — no jurisdiction id literal in this module's own source
# ---------------------------------------------------------------------------


def test_no_jurisdiction_id_literal_in_facilities_module():
    import re

    with open("engine/facilities.py", encoding="utf-8") as handle:
        source = handle.read()
    assert not re.search(r'"us-ny"|"us-ca"', source)

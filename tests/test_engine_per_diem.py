"""Tests for engine/per_diem.py — the committed per-diem snapshot schema
and its single read path (COST-04, D-61, D-64, T-04-10)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from engine.per_diem import (
    PER_DIEM_PATH_BY_ID,
    PerDiemTable,
    load_per_diem,
    lodging_for_month,
)


def _table_kwargs(**overrides):
    base = {
        "per_diem_id": "synthetic-table",
        "fiscal_year": "2026",
        "county": "Synthetic County",
        "source_url": "https://example.invalid/gsa-per-diem",
        "retrieved_at": "2026-08-26",
        "mie_daily": "80",
        "basis": "sourced",
        "ceiling_caveat": "Federal reimbursement ceiling, not a market rate.",
        "lodging_flat_rate": "150",
    }
    base.update(overrides)
    return base


def test_committed_per_diem_ids_are_discovered_and_load():
    assert "us-ny-new-york-county" in PER_DIEM_PATH_BY_ID
    assert "us-ca-los-angeles-county" in PER_DIEM_PATH_BY_ID

    ny = load_per_diem("us-ny-new-york-county")
    la = load_per_diem("us-ca-los-angeles-county")

    assert ny.lodging_by_month is not None
    assert ny.lodging_flat_rate is None
    assert la.lodging_by_month is None
    assert la.lodging_flat_rate == "191"


def test_unknown_per_diem_id_raises_naming_it():
    with pytest.raises(ValueError, match="no-such-per-diem-id"):
        load_per_diem("no-such-per-diem-id")


def test_ny_ceiling_caveat_names_reimbursement_ceiling():
    ny = load_per_diem("us-ny-new-york-county")
    assert "reimbursement ceiling" in ny.ceiling_caveat
    assert "not a market rate" in ny.ceiling_caveat


def test_la_carries_a_seasonality_note():
    la = load_per_diem("us-ca-los-angeles-county")
    assert la.seasonality_note is not None
    assert "does not vary by month" in la.seasonality_note


def test_table_declaring_neither_lodging_shape_raises_naming_the_id():
    kwargs = _table_kwargs()
    del kwargs["lodging_flat_rate"]
    with pytest.raises(ValidationError, match="synthetic-table"):
        PerDiemTable.model_validate(kwargs)


def test_table_declaring_both_lodging_shapes_raises_naming_the_id():
    kwargs = _table_kwargs(lodging_by_month={"2026-01": "100"})
    with pytest.raises(ValidationError, match="synthetic-table"):
        PerDiemTable.model_validate(kwargs)


def test_sourced_basis_without_source_url_is_rejected():
    kwargs = _table_kwargs(source_url=None)
    with pytest.raises(ValidationError):
        PerDiemTable.model_validate(kwargs)


def test_non_sourced_basis_without_method_note_is_rejected():
    kwargs = _table_kwargs(basis="estimated", method_note=None)
    with pytest.raises(ValidationError):
        PerDiemTable.model_validate(kwargs)


def test_empty_ceiling_caveat_is_rejected():
    kwargs = _table_kwargs(ceiling_caveat="   ")
    with pytest.raises(ValidationError):
        PerDiemTable.model_validate(kwargs)


def test_lodging_for_month_returns_flat_rate_when_no_band():
    table = PerDiemTable.model_validate(_table_kwargs())
    assert lodging_for_month(table, "2026-01") == Decimal("150")
    assert lodging_for_month(table, "2099-12") == Decimal("150")


def test_lodging_for_month_returns_band_rate_when_present():
    kwargs = _table_kwargs(lodging_by_month={"2026-01": "179", "2026-07": "237"})
    del kwargs["lodging_flat_rate"]
    table = PerDiemTable.model_validate(kwargs)
    assert lodging_for_month(table, "2026-01") == Decimal("179")
    assert lodging_for_month(table, "2026-07") == Decimal("237")


def test_lodging_for_month_absent_from_band_map_raises_never_a_neighbour():
    kwargs = _table_kwargs(lodging_by_month={"2026-01": "179"})
    del kwargs["lodging_flat_rate"]
    table = PerDiemTable.model_validate(kwargs)
    with pytest.raises(ValueError, match="2026-02"):
        lodging_for_month(table, "2026-02")


def test_ny_lodging_by_month_matches_raw_gsa_bulk_file_reconfirmation():
    """Re-confirmed directly against sources/gsa/2026-08-26-gsa-fy2026-
    per-diem-master-rates-file.xlsx (row ID 266) — byte-for-byte match to
    04-RESEARCH.md's CITED figures, zero discrepancy."""
    ny = load_per_diem("us-ny-new-york-county")
    assert ny.lodging_by_month == {
        "2025-10": "342",
        "2025-11": "342",
        "2025-12": "342",
        "2026-01": "179",
        "2026-02": "179",
        "2026-03": "281",
        "2026-04": "281",
        "2026-05": "281",
        "2026-06": "281",
        "2026-07": "237",
        "2026-08": "237",
        "2026-09": "342",
    }
    assert ny.mie_daily == "92"


def test_la_lodging_flat_rate_matches_raw_gsa_bulk_file_reconfirmation():
    """Re-confirmed directly against the same raw bulk file (row ID 22)."""
    la = load_per_diem("us-ca-los-angeles-county")
    assert la.lodging_flat_rate == "191"
    assert la.mie_daily == "86"

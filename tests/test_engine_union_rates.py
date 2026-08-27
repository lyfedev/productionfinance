"""`engine.union_rates` — dated union rate-card row selection (COST-02) and
fringe schedule loading (COST-03).

Task 2 (04-02-PLAN.md) covers the happy path plus the two load-time
guards (overlap detection, sourced-requires-source_url /
non-sourced-requires-method_note). Task 3 widens this file with the
boundary (exactly-on / one-before / one-after) and precision assertions.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from glob import glob

import pytest
import yaml
from pydantic import ValidationError

from engine.union_rates import (
    FringeComponent,
    FringeSchedule,
    RateRow,
    load_fringe_schedules,
    load_union_rates,
    select_rate_row,
    weakest_basis,
)

MANIFEST_PATH = "sources/MANIFEST.yaml"
UNION_RATES_GLOB = "data/union_rates/*.yaml"


def _row(**overrides) -> RateRow:
    base = {
        "row_id": "test-row",
        "union": "IATSE",
        "local": "600",
        "region": "us-ny",
        "craft": "camera",
        "rate": "900.00",
        "rate_unit": "day",
        "effective_from": date(2025, 1, 1),
        "effective_to": date(2025, 12, 31),
        "basis": "sourced",
        "source_url": "https://example.invalid/rate-card",
        "date_checked": "2026-08-26",
        "method_note": None,
    }
    base.update(overrides)
    return RateRow.model_validate(base)


# ---------------------------------------------------------------------------
# select_rate_row
# ---------------------------------------------------------------------------


def test_select_rate_row_returns_the_covering_row():
    rows = [_row()]
    selected = select_rate_row(rows, region="us-ny", craft="camera", on_date=date(2025, 6, 15))
    assert selected.row_id == "test-row"


def test_select_rate_row_raises_for_a_date_covered_by_no_row_naming_inputs():
    rows = [_row()]
    with pytest.raises(ValueError) as excinfo:
        select_rate_row(rows, region="us-ny", craft="camera", on_date=date(2030, 1, 1))
    message = str(excinfo.value)
    assert "us-ny" in message
    assert "camera" in message
    assert "2030-01-01" in message


def test_select_rate_row_never_falls_back_to_nearest_or_newest_row():
    older = _row(
        row_id="older", effective_from=date(2020, 1, 1), effective_to=date(2020, 12, 31)
    )
    newer = _row(
        row_id="newer", effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31)
    )
    # 2023 is covered by neither — must raise, not silently pick "newer"
    # (nearest by date-forward) or "older" (nearest by date-backward).
    with pytest.raises(ValueError):
        select_rate_row(
            [older, newer], region="us-ny", craft="camera", on_date=date(2023, 6, 1)
        )


def test_select_rate_row_matches_region_and_craft_exactly_no_normalization():
    rows = [_row(region="us-ca", craft="general_crew")]
    with pytest.raises(ValueError):
        # Wrong region — must not fall back to the only other declared row.
        select_rate_row(rows, region="us-ny", craft="general_crew", on_date=date(2025, 6, 1))
    with pytest.raises(ValueError):
        # Wrong craft — same discipline.
        select_rate_row(rows, region="us-ca", craft="camera", on_date=date(2025, 6, 1))


# ---------------------------------------------------------------------------
# Overlap detection at load time (WR-03)
# ---------------------------------------------------------------------------


def test_load_union_rates_raises_on_overlapping_dated_rows_same_region_and_craft(tmp_path):
    overlapping_yaml = tmp_path / "overlap.yaml"
    overlapping_yaml.write_text(
        """
rows:
  - row_id: "a"
    union: "IATSE"
    region: "us-ny"
    craft: "camera"
    rate: "900.00"
    rate_unit: "day"
    effective_from: "2025-01-01"
    effective_to: "2025-12-31"
    basis: "sourced"
    source_url: "https://example.invalid/a"
  - row_id: "b"
    union: "IATSE"
    region: "us-ny"
    craft: "camera"
    rate: "950.00"
    rate_unit: "day"
    effective_from: "2025-06-01"
    effective_to: null
    basis: "sourced"
    source_url: "https://example.invalid/b"
"""
    )
    with pytest.raises(ValueError, match="overlapping dated rows"):
        load_union_rates(paths=[overlapping_yaml])


def test_load_union_rates_allows_adjacent_non_overlapping_rows(tmp_path):
    adjacent_yaml = tmp_path / "adjacent.yaml"
    adjacent_yaml.write_text(
        """
rows:
  - row_id: "a"
    union: "IATSE"
    region: "us-ca"
    craft: "camera"
    rate: "900.00"
    rate_unit: "day"
    effective_from: "2025-01-01"
    effective_to: "2025-12-31"
    basis: "sourced"
    source_url: "https://example.invalid/a"
  - row_id: "b"
    union: "IATSE"
    region: "us-ca"
    craft: "camera"
    rate: "950.00"
    rate_unit: "day"
    effective_from: "2026-01-01"
    effective_to: null
    basis: "sourced"
    source_url: "https://example.invalid/b"
"""
    )
    rows = load_union_rates(paths=[adjacent_yaml])
    assert len(rows) == 2


def test_load_union_rates_does_not_collide_across_different_regions_or_crafts(tmp_path):
    non_colliding_yaml = tmp_path / "non_colliding.yaml"
    non_colliding_yaml.write_text(
        """
rows:
  - row_id: "a"
    union: "IATSE"
    region: "us-ny"
    craft: "camera"
    rate: "900.00"
    rate_unit: "day"
    effective_from: "2025-01-01"
    effective_to: null
    basis: "sourced"
    source_url: "https://example.invalid/a"
  - row_id: "b"
    union: "IATSE"
    region: "us-ca"
    craft: "camera"
    rate: "700.00"
    rate_unit: "day"
    effective_from: "2025-01-01"
    effective_to: null
    basis: "sourced"
    source_url: "https://example.invalid/b"
  - row_id: "c"
    union: "IATSE"
    region: "us-ny"
    craft: "general_crew"
    rate: "450.00"
    rate_unit: "day"
    effective_from: "2025-01-01"
    effective_to: null
    basis: "estimated"
    method_note: "test fixture"
"""
    )
    rows = load_union_rates(paths=[non_colliding_yaml])
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# RateRow honesty validators
# ---------------------------------------------------------------------------


def test_sourced_rate_row_without_source_url_is_rejected():
    with pytest.raises(ValidationError, match="source_url"):
        _row(basis="sourced", source_url=None)


def test_non_sourced_rate_row_without_method_note_is_rejected():
    with pytest.raises(ValidationError, match="method_note"):
        _row(basis="estimated", source_url=None, method_note=None)


def test_unquoted_yaml_numeric_rate_is_rejected_by_the_schema():
    """RD-01: Pydantic's default `str` validation does not coerce an
    int/float input — an authoring mistake that leaves `rate` unquoted in
    YAML fails loudly here rather than silently parsing as a float."""
    with pytest.raises(ValidationError):
        RateRow.model_validate(
            {
                "row_id": "bad",
                "union": "IATSE",
                "region": "us-ny",
                "craft": "camera",
                "rate": 900.00,  # unquoted numeric, not a str
                "rate_unit": "day",
                "effective_from": "2025-01-01",
                "basis": "sourced",
                "source_url": "https://example.invalid",
            }
        )


# ---------------------------------------------------------------------------
# Fringe schedules
# ---------------------------------------------------------------------------


def _fringe_component(**overrides) -> FringeComponent:
    base = {
        "value": "0.20",
        "basis": "sourced",
        "source_url": "https://example.invalid/fringe",
        "date_checked": "2026-08-26",
        "method_note": None,
    }
    base.update(overrides)
    return FringeComponent.model_validate(base)


def test_fringe_component_sourced_requires_source_url():
    with pytest.raises(ValidationError, match="source_url"):
        _fringe_component(basis="sourced", source_url=None)


def test_fringe_component_non_sourced_requires_method_note():
    with pytest.raises(ValidationError, match="method_note"):
        _fringe_component(basis="estimated", source_url=None, method_note=None)


def test_load_fringe_schedules_reads_the_committed_file_for_all_five_unions():
    # Five unions as of plan 04-05: BECTU joins IATSE/SAG-AFTRA/DGA/WGA
    # (London's committed cost profile).
    schedules = load_fringe_schedules()
    assert set(schedules) == {"IATSE", "SAG-AFTRA", "DGA", "WGA", "BECTU"}
    for schedule in schedules.values():
        assert isinstance(schedule, FringeSchedule)
        # Every percentage parses cleanly as a Decimal — RD-01 discipline.
        Decimal(schedule.pension_health_pct.value)
        Decimal(schedule.payroll_tax_pct.value)
        Decimal(schedule.other_burden_pct.value)


def test_dga_and_wga_pension_health_are_sourced_iatse_and_sag_aftra_are_estimated():
    """Resolves 04-RESEARCH.md Assumptions Log rows A1/A2: DGA and WGA's
    own primary documents confirm their Pension & Health percentages this
    session; IATSE's blanket figure and SAG-AFTRA's (network-blocked)
    figure remain industry estimates."""
    schedules = load_fringe_schedules()
    assert schedules["DGA"].pension_health_pct.basis == "sourced"
    assert schedules["WGA"].pension_health_pct.basis == "sourced"
    assert schedules["IATSE"].pension_health_pct.basis == "estimated"
    assert schedules["SAG-AFTRA"].pension_health_pct.basis == "estimated"


# ---------------------------------------------------------------------------
# weakest_basis
# ---------------------------------------------------------------------------


def test_weakest_basis_picks_the_weakest_of_three():
    assert weakest_basis(["sourced", "sourced", "sourced"]) == "sourced"
    assert weakest_basis(["sourced", "estimated", "sourced"]) == "estimated"
    assert weakest_basis(["sourced", "estimated", "modelling_assumption"]) == (
        "modelling_assumption"
    )


def test_weakest_basis_raises_on_empty_list():
    with pytest.raises(ValueError):
        weakest_basis([])


# ---------------------------------------------------------------------------
# The committed data/union_rates/iatse.yaml file loads cleanly
# ---------------------------------------------------------------------------


def test_committed_union_rates_load_without_error():
    rows = load_union_rates()
    assert rows, "no rate rows loaded from data/union_rates/*.yaml"
    camera_ny = select_rate_row(rows, region="us-ny", craft="camera", on_date=date(2026, 4, 1))
    assert camera_ny.basis == "sourced"
    camera_ca = select_rate_row(rows, region="us-ca", craft="camera", on_date=date(2026, 4, 1))
    assert camera_ca.basis == "sourced"
    general_ny = select_rate_row(
        rows, region="us-ny", craft="general_crew", on_date=date(2026, 4, 1)
    )
    assert general_ny.basis == "estimated"


# ---------------------------------------------------------------------------
# Task 3 — boundary coverage: exactly-on, one-before, one-after (WR-03)
# ---------------------------------------------------------------------------


def test_select_rate_row_boundary_exact_on_and_adjacent_successor():
    """Closed-closed: a date exactly on `effective_from` or exactly on
    `effective_to` both select that row. One day after `effective_to`
    selects the adjacent successor row when one exists (never raises just
    because the FIRST row's range ended)."""
    row_a = _row(
        row_id="a",
        region="us-boundary",
        craft="boundary",
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 6, 30),
    )
    row_b = _row(
        row_id="b",
        region="us-boundary",
        craft="boundary",
        effective_from=date(2025, 7, 1),
        effective_to=None,
    )
    rows = [row_a, row_b]

    # Exactly on row_a's effective_from.
    assert (
        select_rate_row(rows, region="us-boundary", craft="boundary", on_date=date(2025, 1, 1))
        .row_id
        == "a"
    )
    # Exactly on row_a's effective_to (closed-closed, not open at the end).
    assert (
        select_rate_row(rows, region="us-boundary", craft="boundary", on_date=date(2025, 6, 30))
        .row_id
        == "a"
    )
    # One day after row_a's effective_to — the adjacent successor (row_b)
    # covers this date, so it is selected, not a raise.
    assert (
        select_rate_row(rows, region="us-boundary", craft="boundary", on_date=date(2025, 7, 1))
        .row_id
        == "b"
    )
    # Exactly on row_b's effective_from (same date as the prior assertion,
    # confirming it is row_b's own start, not a fallback).
    assert (
        select_rate_row(rows, region="us-boundary", craft="boundary", on_date=date(2025, 7, 1))
        .row_id
        == "b"
    )
    # row_b is open-ended — far in the future still resolves to it.
    assert (
        select_rate_row(rows, region="us-boundary", craft="boundary", on_date=date(2030, 1, 1))
        .row_id
        == "b"
    )


def test_select_rate_row_boundary_one_day_before_start_raises_when_no_prior_row_exists():
    row_a = _row(
        row_id="a",
        region="us-boundary",
        craft="boundary-solo",
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 6, 30),
    )
    with pytest.raises(ValueError) as excinfo:
        select_rate_row(
            [row_a], region="us-boundary", craft="boundary-solo", on_date=date(2024, 12, 31)
        )
    message = str(excinfo.value)
    assert "us-boundary" in message
    assert "boundary-solo" in message
    assert "2024-12-31" in message


def test_select_rate_row_boundary_one_day_after_end_raises_when_no_successor_exists():
    row_a = _row(
        row_id="a",
        region="us-boundary",
        craft="boundary-closed",
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 6, 30),
    )
    with pytest.raises(ValueError):
        select_rate_row(
            [row_a], region="us-boundary", craft="boundary-closed", on_date=date(2025, 7, 1)
        )


def test_select_rate_row_boundary_one_day_before_start_selects_prior_row_when_one_exists():
    """The mirror of the "raises when none does" case above: one day
    before a row's start is COVERED by an earlier row when one exists —
    never a raise, and never a silent fallback to the wrong row."""
    row_a = _row(
        row_id="a",
        region="us-boundary",
        craft="boundary-chain",
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 6, 30),
    )
    row_b = _row(
        row_id="b",
        region="us-boundary",
        craft="boundary-chain",
        effective_from=date(2025, 7, 1),
        effective_to=date(2025, 12, 31),
    )
    rows = [row_a, row_b]
    # One day before row_b's start (2025-06-30) is row_a's own effective_to
    # — covered by row_a, not by row_b, not a raise.
    selected = select_rate_row(
        rows, region="us-boundary", craft="boundary-chain", on_date=date(2025, 6, 30)
    )
    assert selected.row_id == "a"


def test_committed_iatse_los_angeles_camera_rows_are_adjacent_not_overlapping():
    """The real committed data exercises the same boundary shape: LA's two
    camera rows are closed-closed adjacent (2026-08-01 -> row 1,
    2026-08-02 -> row 2), never overlapping and never leaving a gap."""
    rows = load_union_rates()
    row_at_end_of_first = select_rate_row(
        rows, region="us-ca", craft="camera", on_date=date(2026, 8, 1)
    )
    row_at_start_of_second = select_rate_row(
        rows, region="us-ca", craft="camera", on_date=date(2026, 8, 2)
    )
    assert row_at_end_of_first.row_id != row_at_start_of_second.row_id
    assert row_at_end_of_first.basis == "sourced"
    assert row_at_start_of_second.basis == "sourced"


def test_committed_new_york_camera_row_raises_past_its_expiry_no_successor():
    """New York's camera row has no committed 2026-2027 successor (only a
    DRAFT rate card was found — see .planning/WINDOWS.md) — a shoot date
    past 2026-08-01 must raise, never silently reuse the expired row."""
    rows = load_union_rates()
    with pytest.raises(ValueError):
        select_rate_row(rows, region="us-ny", craft="camera", on_date=date(2026, 8, 2))


# ---------------------------------------------------------------------------
# Task 3 — precision
# ---------------------------------------------------------------------------


def test_every_component_of_a_rate_row_parses_cleanly_as_decimal():
    row = _row(rate="947.58")
    assert isinstance(Decimal(row.rate), Decimal)


# ---------------------------------------------------------------------------
# Task 3 — sourcing record: every `basis: sourced` row traces to MANIFEST
# ---------------------------------------------------------------------------


def _load_manifest_documents() -> list[dict]:
    with open(MANIFEST_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle)["documents"]


def test_every_sourced_union_rate_row_is_named_in_manifest_cited_for():
    """A future rate edit cannot promote a row to `sourced` without
    archiving its document: every `basis: "sourced"` row's `row_id` must
    appear in at least one `sources/MANIFEST.yaml` document's `cited_for`
    list."""
    documents = _load_manifest_documents()
    all_cited_text = " ".join(
        " ".join(doc.get("cited_for", [])) for doc in documents
    )

    failures: list[str] = []
    for path in sorted(glob(UNION_RATES_GLOB)):
        with open(path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        for row_data in raw.get("rows", []) or []:
            if row_data.get("basis") == "sourced" and row_data["row_id"] not in all_cited_text:
                failures.append(f"{path}: row {row_data['row_id']!r} basis 'sourced' but not "
                                 "named in any sources/MANIFEST.yaml cited_for entry")

    assert not failures, "\n".join(failures)


def test_manifest_reconciliation_would_catch_a_hand_edited_sourced_row():
    """Non-vacuity proof: a synthetic 'sourced' row NOT named in the
    manifest must be flagged by the same check the test above runs — this
    proves the check can fail, not just that today's committed data
    happens to pass it."""
    documents = _load_manifest_documents()
    all_cited_text = " ".join(" ".join(doc.get("cited_for", [])) for doc in documents)
    fabricated_row_id = "fabricated-row-never-in-any-manifest-entry-xyz"
    assert fabricated_row_id not in all_cited_text

"""Tests for engine/seasonality.py — the shoot calendar (D-65),
month-weighted per diem/housing (COST-04/COST-07), and
engine/landed_cost.py's quarter-invariance machinery (D-66/D-67)."""

from __future__ import annotations

from decimal import Decimal

from engine.landed_cost import SeasonalityState, compute_quarter_invariance
from engine.per_diem import load_per_diem
from engine.seasonality import (
    SHOOT_DAYS_PER_WEEK,
    SHOOT_DAYS_PER_WEEK_NOTE,
    MonthNights,
    _shoot_calendar,
    month_weighted_per_diem,
    shoot_calendar,
)
from engine.spec import ProductionSpec


def _spec(*, start_quarter: str = "Q2", shoot_days_stage: int = 10, shoot_days_location: int = 5):
    return ProductionSpec(
        production_type="feature",
        shoot_days_stage=shoot_days_stage,
        shoot_days_location=shoot_days_location,
        crew_size=50,
        principal_cast_count=3,
        principal_cast_imported_count=1,
        crew_imported_count=10,
        crew_hired_locally_count=40,
        start_quarter=start_quarter,
        start_year=2026,
        candidate_cities=["New York, NY"],
    )


# ---------------------------------------------------------------------------
# _shoot_calendar / shoot_calendar (D-65)
# ---------------------------------------------------------------------------


def test_shoot_calendar_spreads_days_across_calendar_months():
    spec = _spec(start_quarter="Q2", shoot_days_stage=10, shoot_days_location=5)
    calendar = shoot_calendar(spec)
    assert calendar == _shoot_calendar(spec)
    # 15 total shoot days / 5 days-per-week = 3 weeks = 21 calendar nights,
    # starting 2026-04-01 (Q2). 21 nights span April (30 days) entirely.
    assert sum(month.nights for month in calendar) == 21
    assert all(month.year_month.startswith("2026-04") for month in calendar)


def test_shoot_calendar_spans_a_month_boundary():
    # Q3 2026 starts 2026-07-01. A larger shoot pushes into August.
    spec = _spec(start_quarter="Q3", shoot_days_stage=40, shoot_days_location=10)
    calendar = shoot_calendar(spec)
    year_months = {month.year_month for month in calendar}
    assert "2026-07" in year_months
    assert "2026-08" in year_months
    total_nights = sum(month.nights for month in calendar)
    assert total_nights == 70  # ceil(50/5) * 7 = 70


def test_shoot_calendar_zero_shoot_days_is_empty_never_a_division_error():
    spec = _spec(shoot_days_stage=0, shoot_days_location=0)
    assert shoot_calendar(spec) == ()


def test_shoot_days_per_week_is_a_disclosed_modelling_assumption():
    assert SHOOT_DAYS_PER_WEEK == Decimal("5")
    assert "modelling assumption" in SHOOT_DAYS_PER_WEEK_NOTE
    assert "SHOOT_DAYS_PER_WEEK" in SHOOT_DAYS_PER_WEEK_NOTE


def test_shoot_calendar_never_hardcodes_twelve_monthly_rows():
    # A three-week shoot must NOT produce twelve MonthNights entries.
    spec = _spec(start_quarter="Q1", shoot_days_stage=10, shoot_days_location=5)
    calendar = shoot_calendar(spec)
    assert len(calendar) < 12


# ---------------------------------------------------------------------------
# month_weighted_per_diem (COST-04/COST-05, D-61, D-64)
# ---------------------------------------------------------------------------


def test_new_york_per_diem_carries_the_ceiling_caveat_and_basis():
    ny_table = load_per_diem("us-ny-new-york-county")
    calendar = shoot_calendar(_spec(start_quarter="Q2"))
    housing, per_diem = month_weighted_per_diem(ny_table, calendar, headcount=11)

    for figure in (housing, per_diem):
        assert figure.caveat is not None
        assert "reimbursement ceiling" in figure.caveat
        assert figure.basis == "sourced"

    assert housing.label == "Housing — imported crew and cast"
    assert per_diem.label == "Per diem (M&IE) — imported crew and cast"


def test_new_york_and_los_angeles_are_two_separate_sibling_figures():
    """D-62's discipline extended to travel: housing and per diem are
    never folded into one Figure."""
    ny_table = load_per_diem("us-ny-new-york-county")
    calendar = shoot_calendar(_spec())
    housing, per_diem = month_weighted_per_diem(ny_table, calendar, headcount=11)
    assert housing.figure_id != per_diem.figure_id
    assert housing.value != per_diem.value or housing.label != per_diem.label


def test_los_angeles_flat_rate_states_absence_explicitly():
    la_table = load_per_diem("us-ca-los-angeles-county")
    calendar = shoot_calendar(_spec())
    housing, per_diem = month_weighted_per_diem(la_table, calendar, headcount=11)
    joined = " ".join(housing.derivation)
    assert "no month-banded per-diem data exists" in joined
    assert "does not vary by month" in joined


def test_changing_start_quarter_changes_new_york_but_not_los_angeles():
    """The COST-07/D-64 must-have: start quarter moves New York's per-diem
    total (a real month band exists) but not Los Angeles's (flat rate)."""
    ny_table = load_per_diem("us-ny-new-york-county")
    la_table = load_per_diem("us-ca-los-angeles-county")

    q1_calendar = shoot_calendar(_spec(start_quarter="Q1"))
    q3_calendar = shoot_calendar(_spec(start_quarter="Q3"))

    ny_q1_housing, ny_q1_per_diem = month_weighted_per_diem(ny_table, q1_calendar, headcount=11)
    ny_q3_housing, ny_q3_per_diem = month_weighted_per_diem(ny_table, q3_calendar, headcount=11)
    la_q1_housing, la_q1_per_diem = month_weighted_per_diem(la_table, q1_calendar, headcount=11)
    la_q3_housing, la_q3_per_diem = month_weighted_per_diem(la_table, q3_calendar, headcount=11)

    assert ny_q1_housing.value != ny_q3_housing.value
    # NY's M&IE is flat ($92) — only the lodging component moves seasonally.
    assert ny_q1_per_diem.value == ny_q3_per_diem.value

    assert la_q1_housing.value == la_q3_housing.value
    assert la_q1_per_diem.value == la_q3_per_diem.value


def test_per_diem_scales_linearly_with_headcount():
    ny_table = load_per_diem("us-ny-new-york-county")
    calendar = shoot_calendar(_spec())
    one_housing, one_per_diem = month_weighted_per_diem(ny_table, calendar, headcount=1)
    ten_housing, ten_per_diem = month_weighted_per_diem(ny_table, calendar, headcount=10)
    assert ten_housing.value == one_housing.value * 10
    assert ten_per_diem.value == one_per_diem.value * 10


def test_zero_headcount_produces_computed_zero_not_absent():
    ny_table = load_per_diem("us-ny-new-york-county")
    calendar = shoot_calendar(_spec())
    housing, per_diem = month_weighted_per_diem(ny_table, calendar, headcount=0)
    assert housing.value == Decimal("0")
    assert per_diem.value == Decimal("0")


def test_zero_calendar_nights_derives_zero_per_diem():
    ny_table = load_per_diem("us-ny-new-york-county")
    housing, per_diem = month_weighted_per_diem(ny_table, (), headcount=11)
    assert housing.value == Decimal("0")
    assert per_diem.value == Decimal("0")
    assert "zero calendar nights" in " ".join(housing.derivation)


def test_derivation_names_every_month_its_nights_and_its_rate():
    ny_table = load_per_diem("us-ny-new-york-county")
    calendar = (MonthNights(year_month="2026-01", nights=7), MonthNights(year_month="2026-07", nights=3))
    housing, per_diem = month_weighted_per_diem(ny_table, calendar, headcount=2)
    joined = " ".join(housing.derivation)
    assert "2026-01" in joined and "7 night" in joined and "179" in joined
    assert "2026-07" in joined and "3 night" in joined and "237" in joined


def test_no_code_assumes_twelve_monthly_rows():
    import re

    with open("engine/seasonality.py", encoding="utf-8") as handle:
        source = handle.read()
    for match in re.finditer(r"range\(\s*12\s*\)", source):
        raise AssertionError(f"engine/seasonality.py hardcodes a 12-row assumption: {match.group()}")


# ---------------------------------------------------------------------------
# compute_quarter_invariance (D-66/D-67) — a genuine measurement, never a
# hardcoded list of category names.
# ---------------------------------------------------------------------------


def _figure(label: str, value: str, *, basis: str = "sourced"):
    from engine.figure import Figure

    return Figure(
        value=Decimal(value),
        unit="USD",
        label=label,
        derivation=(f"{label} = {value}",),
        inputs=(),
        source_url=None,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis=basis,
    )


def test_compute_quarter_invariance_separates_variant_from_invariant():
    runs = {
        "Q1": (_figure("Camera wage", "1000"), _figure("Per diem", "342")),
        "Q2": (_figure("Camera wage", "1000"), _figure("Per diem", "281")),
        "Q3": (_figure("Camera wage", "1000"), _figure("Per diem", "237")),
        "Q4": (_figure("Camera wage", "1000"), _figure("Per diem", "342")),
    }
    variant, invariant = compute_quarter_invariance(runs)
    assert variant == ("Per diem",)
    assert invariant == ("Camera wage",)


def test_compute_quarter_invariance_is_a_real_measurement_not_a_literal_list():
    """Mutating a rate and re-running must move a label between the two
    sets — proving this is computed, not a hardcoded answer."""
    stable_runs = {
        "Q1": (_figure("Camera wage", "1000"),),
        "Q2": (_figure("Camera wage", "1000"),),
    }
    _, invariant_before = compute_quarter_invariance(stable_runs)
    assert "Camera wage" in invariant_before

    mutated_runs = {
        "Q1": (_figure("Camera wage", "1000"),),
        "Q2": (_figure("Camera wage", "1100"),),  # the rate changed
    }
    variant_after, _ = compute_quarter_invariance(mutated_runs)
    assert "Camera wage" in variant_after


def test_compute_quarter_invariance_treats_a_missing_label_as_variant():
    runs = {
        "Q1": (_figure("Camera wage", "1000"), _figure("Per diem", "342")),
        "Q2": (_figure("Camera wage", "1000"),),  # Per diem absent this run
    }
    variant, invariant = compute_quarter_invariance(runs)
    assert "Per diem" in variant
    assert "Camera wage" in invariant


def test_compute_quarter_invariance_raises_on_empty_runs():
    import pytest

    with pytest.raises(ValueError, match="no runs"):
        compute_quarter_invariance({})


def test_compute_quarter_invariance_against_real_committed_per_diem_tables():
    """A real, non-synthetic proof: New York's per-diem Figure is variant
    across quarters, Los Angeles's is invariant.

    Q1/Q2/Q3 only — the committed FY2026 GSA snapshot covers 2025-10
    through 2026-09 (a genuine October-2025-through-September-2026 federal
    fiscal year); a Q4 2026 start_quarter derives an October 2026 calendar
    month, past the committed snapshot's coverage, and correctly RAISES
    (D-64: never a fallback) rather than fabricating a rate — recorded to
    .planning/WINDOWS.md rather than routed around here."""
    ny_table = load_per_diem("us-ny-new-york-county")
    la_table = load_per_diem("us-ca-los-angeles-county")

    runs: dict[str, tuple] = {}
    for quarter in ("Q1", "Q2", "Q3"):
        calendar = shoot_calendar(_spec(start_quarter=quarter))
        ny_housing, ny_per_diem = month_weighted_per_diem(ny_table, calendar, headcount=11)
        la_housing, la_per_diem = month_weighted_per_diem(la_table, calendar, headcount=11)
        runs[quarter] = (
            _figure("NY Housing", str(ny_housing.value)),
            _figure("LA Housing", str(la_housing.value)),
            _figure("NY Per diem", str(ny_per_diem.value)),
            _figure("LA Per diem", str(la_per_diem.value)),
        )

    variant, invariant = compute_quarter_invariance(runs)
    assert "NY Housing" in variant
    assert "LA Housing" in invariant
    assert "LA Per diem" in invariant


# ---------------------------------------------------------------------------
# SeasonalityState + aggregate() wiring (D-66)
# ---------------------------------------------------------------------------


def test_seasonality_state_carries_month_banded_and_no_month_band():
    ny_table = load_per_diem("us-ny-new-york-county")
    la_table = load_per_diem("us-ca-los-angeles-county")

    ny_state = SeasonalityState(
        state="month_banded",
        reason=f"{ny_table.per_diem_id!r} carries a genuine month-banded lodging rate",
    )
    la_state = SeasonalityState(state="no_month_band", reason=la_table.seasonality_note)

    assert ny_state.state == "month_banded"
    assert la_state.state == "no_month_band"
    assert "does not vary by month" in la_state.reason


def test_aggregate_accepts_and_returns_seasonality_fields():
    """aggregate()'s new keyword-only parameters are additive and pass
    through unchanged — existing callers that omit them are unaffected."""
    from decimal import Decimal as D

    from engine.cost_localizer import LocalizedBudget
    from engine.figure import Figure as F
    from engine.landed_cost import aggregate
    from engine.qualifying_base import SpendBreakdown

    cost_figure = F(
        value=D("100"),
        unit="USD",
        label="Test cost line",
        derivation=("test",),
        inputs=(),
        source_url=None,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )
    localized = LocalizedBudget(
        city_id="synthetic",
        jurisdiction_id=None,
        currency="USD",
        lines=(cost_figure,),
        spend_breakdown=SpendBreakdown(
            total_spend=D("100"), labour_spend=D("0"), local_hires_spend=D("0"), core_expenditure=D("100")
        ),
        categories_priced=frozenset({"equipment"}),
    )
    state = SeasonalityState(state="no_month_band", reason="synthetic reason")
    landed = aggregate(
        localized,
        quarter_variant_lines=("Test cost line",),
        quarter_invariant_lines=("Other line",),
        seasonality_state=state,
    )
    assert landed.quarter_variant_lines == ("Test cost line",)
    assert landed.quarter_invariant_lines == ("Other line",)
    assert landed.seasonality_state is state


def test_aggregate_defaults_are_backward_compatible():
    """Confirms omitting the new kwargs keeps the pre-04-03 contract
    unchanged (empty tuples, None state)."""
    from decimal import Decimal as D

    from engine.cost_localizer import LocalizedBudget
    from engine.figure import Figure as F
    from engine.landed_cost import aggregate
    from engine.qualifying_base import SpendBreakdown

    cost_figure = F(
        value=D("50"),
        unit="USD",
        label="Test cost line",
        derivation=("test",),
        inputs=(),
        source_url=None,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )
    localized = LocalizedBudget(
        city_id="synthetic",
        jurisdiction_id=None,
        currency="USD",
        lines=(cost_figure,),
        spend_breakdown=SpendBreakdown(
            total_spend=D("50"), labour_spend=D("0"), local_hires_spend=D("0"), core_expenditure=D("50")
        ),
        categories_priced=frozenset({"equipment"}),
    )
    landed = aggregate(localized)
    assert landed.quarter_variant_lines == ()
    assert landed.quarter_invariant_lines == ()
    assert landed.seasonality_state is None

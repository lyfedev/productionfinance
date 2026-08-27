"""D-78: golden cost totals, pinned in CI.

A single fixed `ProductionSpec` (below) priced against the three committed
cost profiles produces exact `Decimal` totals — every one independently
derived BY HAND from the raw committed data files (`data/crew_tiers.yaml`,
`data/union_rates/*.yaml`, `data/per_diem/**/*.yaml`,
`data/facilities/*.yaml`, `data/tax_exemptions/*.yaml`, `data/fx/*.yaml`)
before this test was ever run against the pipeline. The derivation for
each city is written out below, immediately beside its assertion — this
is NOT a snapshot of whatever the code currently produces (the project's
own stack guidance rejects that by name for exactly this reason, and
`.planning/PROJECT.md`'s "What NOT to Use" table names `pytest-golden` and
`syrupy` explicitly). Every independently-derived number agreed EXACTLY
with the pipeline's own output on the first run — no discrepancy was
found or silently reconciled this session.

**Shared derivation facts, used by every city below:**

- `shoot_days_stage=10`, `shoot_days_location=5` -> 15 total shoot days.
- `crew_size=50` (no tier) resolves to the `"small"` bracket (30-60), but
  every `crew_tiers.yaml` department's `crew_share` is IDENTICAL across
  all five tiers, so the bracket choice does not affect the result.
- Department person-days = `50 * crew_share * 15`. `crew_share`s: production
  0.10, camera 0.15, grip_and_electric 0.15, art 0.15, wardrobe 0.08,
  hair_and_makeup 0.07, sound 0.05, transportation 0.10, locations 0.05,
  post 0.10 (sums to exactly 1).
- Every non-camera department prices at the `general_crew` craft rate for
  that city; camera prices at the `camera` craft rate.
- Fringe = `wage_value * (pension_health_pct + payroll_tax_pct +
  other_burden_pct)`, summed in `Decimal` before the one multiplication.
- The shoot calendar (`engine.seasonality.shoot_calendar`) spreads 15
  shoot days at 5 days/week -> `ceil(15/5) = 3` weeks -> 21 calendar
  nights, all falling in April 2026 (`start_quarter="Q2"`, `start_year
  =2026` -> April 1 + 21 nights = April 1-21, within April's 30 days).
  `imported_headcount = crew_imported_count(10) + principal_cast_imported
  _count(1) = 11`.
- Facilities (COST-06) price at the LOW bound: stages x
  `shoot_days_stage`, permits/locations x `shoot_days_location`,
  equipment/trucking x total shoot days (15).
- `quantize_money` is `ROUND_HALF_UP` to the whole dollar (`engine
  /rounding.py`) — every intermediate money value below is rounded
  independently at the SAME points the pipeline rounds, matching
  `engine/cost_localizer.py`'s per-line quantization discipline exactly.
"""

from __future__ import annotations

from decimal import Decimal

import engine.cost_localizer as cost_localizer_module
from engine.budget import build_canonical_budget
from engine.cost_localizer import localize, quarter_start_date
from engine.cost_profile import load_cost_profile
from engine.gap import decompose_gap
from engine.landed_cost import LandedCost, aggregate
from engine.spec import CrewHeadcount, ProductionSpec
from engine.union_rates import load_union_rates as real_load_union_rates

# The one fixed ProductionSpec every assertion in this module prices
# against. Pinned exactly — changing any field here invalidates every
# hand-derived expectation below and requires re-deriving them.
GOLDEN_SPEC = ProductionSpec.model_validate(
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
GOLDEN_HEADCOUNT = CrewHeadcount(
    low=50, high=50, basis="supplied by the visitor", provenance_note="golden test fixture"
)


def _landed(profile_path: str, *, reporting_currency: str = "USD") -> LandedCost:
    budget = build_canonical_budget(GOLDEN_SPEC, GOLDEN_HEADCOUNT)
    on_date = quarter_start_date(GOLDEN_SPEC.start_quarter, GOLDEN_SPEC.start_year)
    profile = load_cost_profile(profile_path)
    localized = localize(budget, profile, on_date=on_date, spec=GOLDEN_SPEC)
    return aggregate(localized, reporting_currency=reporting_currency)


# ---------------------------------------------------------------------------
# New York — hand derivation
#
# Camera: 112.5 person-days (50 x 0.15 x 15) x $947.58 (IATSE Local 600,
# row iatse-l600-camera-us-ny-2025, covers 2025-08-03..2026-08-01, which
# April 1 2026 falls inside) = $106,602.75 -> $106,603.
# Fringe (IATSE: 0.40 + 0.0965 + 0.02 = 0.5165): $106,603 x 0.5165 =
# $55,060.4495 -> $55,060.
# Every other department (general_crew, $450/day, same 0.5165 fringe):
#   production   75.0 days x $450 = $33,750   ; fringe $17,431.875  -> $17,432
#   grip/elec   112.5 days x $450 = $50,625   ; fringe $26,147.8125 -> $26,148
#   art         112.5 days x $450 = $50,625   ; fringe $26,147.8125 -> $26,148
#   wardrobe     60.0 days x $450 = $27,000   ; fringe $13,945.5    -> $13,946
#   hair/makeup  52.5 days x $450 = $23,625   ; fringe $12,202.3125 -> $12,202
#   sound        37.5 days x $450 = $16,875   ; fringe $8,716.4375  -> $8,716
#   transport    75.0 days x $450 = $33,750   ; fringe $17,432 (same as production)
#   locations    37.5 days x $450 = $16,875   ; fringe $8,716 (same as sound)
#   post         75.0 days x $450 = $33,750   ; fringe $17,432 (same as production)
# Labour + fringe subtotal = $596,710.
#
# Housing:  11 imported people x 21 nights x $281 (April GSA lodging,
#           us-ny-new-york-county) = $64,911.
# Per diem: 11 x 21 x $92 (GSA M&IE)                  = $21,252.
# Flights:  11 x $450 round trip                      = $4,950.
# Facilities (low bound): stages $2,500 x 10 = $25,000; equipment $1,800
#   x 15 = $27,000; permits $300 x 5 = $1,500; locations $1,500 x 5 =
#   $7,500; trucking $800 x 15 = $12,000. Subtotal = $73,000.
# Exemption: sales tax 8.875% on Equipment ($27,000) = -$2,396.25 -> -$2,396.
#
# TOTAL = 596,710 + 64,911 + 21,252 + 4,950 + 73,000 - 2,396 = $758,427.
# ---------------------------------------------------------------------------

NY_COST_TOTAL = Decimal("758427")


def test_new_york_golden_cost_total():
    landed = _landed("data/cost_profiles/us-ny-new-york.yaml")
    assert landed.cost_total.value == NY_COST_TOTAL


# ---------------------------------------------------------------------------
# Los Angeles — hand derivation
#
# Camera: 112.5 days x $719.28 (IATSE Local 600, row
# iatse-l600-camera-us-ca-2025, covers 2025-08-03..2026-08-01) =
# $80,919.00 -> $80,919. Fringe: $80,919 x 0.5165 = $41,794.6635 -> $41,795.
# Every other department is IDENTICAL to New York (same $450/day
# general_crew rate, same fringe percentages) — labour+fringe totals for
# production/grip/art/wardrobe/hair/sound/transport/locations/post are
# byte-identical to the New York derivation above.
# Labour + fringe subtotal = $557,761 (= $596,710 NY total, less the
# camera-department delta: ($106,603+$55,060) - ($80,919+$41,795) =
# $161,663 - $122,714 = $38,949; $596,710 - $38,949 = $557,761).
#
# Housing:  11 x 21 x $191 (GSA lodging_flat_rate, us-ca-los-angeles-county,
#           no month band, D-64 absent branch) = $44,121.
# Per diem: 11 x 21 x $86 (GSA M&IE)            = $19,866.
# Flights:  11 x $450                           = $4,950.
# Facilities: IDENTICAL low-bound ranges to New York (data/facilities
#   /us-ca-los-angeles.yaml declares the same rate_low values) = $73,000.
# Exemption: 30-night extended-stay hotel-occupancy tax, 14% on Housing
#   ($44,121) = -$6,176.94 -> -$6,177.
#
# TOTAL = 557,761 + 44,121 + 19,866 + 4,950 + 73,000 - 6,177 = $693,521.
# ---------------------------------------------------------------------------

LA_COST_TOTAL = Decimal("693521")


def test_los_angeles_golden_cost_total():
    landed = _landed("data/cost_profiles/us-ca-los-angeles.yaml")
    assert landed.cost_total.value == LA_COST_TOTAL


# ---------------------------------------------------------------------------
# London — hand derivation (GBP, then per-component converted to USD)
#
# Camera: 112.5 days x GBP138.50 (Bectu Camera Branch,
# bectu-camera-branch-london-2025) = GBP15,581.25 -> GBP15,581. Fringe
# (BECTU: 0.03 + 0.15 + 0.02 = 0.20): GBP15,581 x 0.20 = GBP3,116.20 ->
# GBP3,116.
# Every other department at GBP424/day (Bectu Grips Branch,
# bectu-grips-branch-general-crew-london-2024), same 0.20 fringe:
#   production   75.0 days x 424 = 31,800 ; fringe 6,360
#   grip/elec   112.5 days x 424 = 47,700 ; fringe 9,540
#   art         112.5 days x 424 = 47,700 ; fringe 9,540
#   wardrobe     60.0 days x 424 = 25,440 ; fringe 5,088
#   hair/makeup  52.5 days x 424 = 22,260 ; fringe 4,452
#   sound        37.5 days x 424 = 15,900 ; fringe 3,180
#   transport    75.0 days x 424 = 31,800 ; fringe 6,360
#   locations    37.5 days x 424 = 15,900 ; fringe 3,180
#   post         75.0 days x 424 = 31,800 ; fringe 6,360
# Labour + fringe subtotal = GBP343,057.
#
# Housing:  11 x 21 nights x GBP424 (State Dept lodging_flat_rate,
#           no month band, D-64 absent branch) = GBP97,944.
# Per diem: 11 x 21 x GBP174 (State Dept M&IE)  = GBP40,194.
# Flights:  11 x GBP650 (international round trip) = GBP7,150.
# Facilities (low bound): stages 2,000 x 10 = 20,000; equipment 1,500 x
#   15 = 22,500; permits 250 x 5 = 1,250; locations 1,200 x 5 = 6,000;
#   trucking 700 x 15 = 10,500. Subtotal = GBP60,250.
# Exemptions: zero declared for London (data/tax_exemptions/gb-london.yaml).
#
# TOTAL (GBP) = 343,057 + 97,944 + 40,194 + 7,150 + 60,250 = GBP548,595.
#
# Converted to USD at the committed rate 1.363 (data/fx/gbp-usd.yaml):
# 548,595 x 1.363 = 747,734.985 -> rounds to $747,735 at the whole-total
# level; `engine.landed_cost.aggregate` converts and quantizes each of the
# ~28 individual lines separately then sums the already-quantized
# results (never a second quantize of the sum) — the per-line roundings
# net to the SAME $747,735 here, which this test also asserts directly
# against the pipeline's actual per-component-converted output.
# ---------------------------------------------------------------------------

LONDON_COST_TOTAL_GBP = Decimal("548595")
LONDON_COST_TOTAL_USD = Decimal("747735")


def test_london_golden_cost_total_gbp():
    landed = _landed("data/cost_profiles/gb-london.yaml", reporting_currency="GBP")
    assert landed.cost_total.value == LONDON_COST_TOTAL_GBP


def test_london_golden_cost_total_converted_to_usd():
    landed = _landed("data/cost_profiles/gb-london.yaml", reporting_currency="USD")
    assert landed.cost_total.value == LONDON_COST_TOTAL_USD


# ---------------------------------------------------------------------------
# New York vs Los Angeles — the headline gap and its components (OUT-02)
#
# Headline = NY_COST_TOTAL - LA_COST_TOTAL = 758,427 - 693,521 = $64,906.
#
# Every non-camera, non-Equipment, non-Housing component is byte-identical
# between the two cities (same crew_share, same $450/day general_crew
# rate, same facilities ranges) and therefore deltas to exactly
# Decimal('0') — a zero delta EMITTED, not dropped (a hard acceptance
# criterion for engine.gap).
#
# Camera labour days:  NY $106,603 - LA $80,919  = $25,684.
# Fringe — Camera:      NY $55,060  - LA $41,795  = $13,265.
# Equipment (with NY's exemption folded in, LA has none):
#   NY: $27,000 - $2,396 = $24,604; LA: $27,000 -> delta = -$2,396.
# Housing (with LA's exemption folded in, NY has none):
#   NY: $64,911; LA: $44,121 - $6,177 = $37,944 -> delta = $26,967.
# Per diem (M&IE):      NY $21,252 - LA $19,866  = $1,386.
#
# Sum of the five non-zero components = 25,684 + 13,265 - 2,396 + 26,967
# + 1,386 = $64,906 — exactly the headline gap, with every other
# component (20 more matched labels) contributing exactly $0.
# ---------------------------------------------------------------------------


def test_new_york_vs_los_angeles_golden_gap():
    ny = _landed("data/cost_profiles/us-ny-new-york.yaml")
    la = _landed("data/cost_profiles/us-ca-los-angeles.yaml")

    gap = decompose_gap(
        "us-ny-new-york", ny, "us-ca-los-angeles", la, reporting_currency="USD"
    )

    assert gap.headline_gap.value == Decimal("64906")

    by_label = {c.label: c.value for c in gap.components}
    assert by_label["Camera labour days"] == Decimal("25684")
    assert by_label["Fringe and payroll burden — Camera"] == Decimal("13265")
    assert by_label["Equipment"] == Decimal("-2396")
    assert by_label["Housing — imported crew and cast"] == Decimal("26967")
    assert by_label["Per diem (M&IE) — imported crew and cast"] == Decimal("1386")

    # Every other matched label is byte-identical between the two cities.
    zero_labels = set(by_label) - {
        "Camera labour days",
        "Fringe and payroll burden — Camera",
        "Equipment",
        "Housing — imported crew and cast",
        "Per diem (M&IE) — imported crew and cast",
    }
    for label in zero_labels:
        assert by_label[label] == Decimal("0"), label

    total = sum(by_label.values(), start=Decimal("0"))
    assert total == gap.headline_gap.value


# ---------------------------------------------------------------------------
# Non-vacuity (D-78): a golden test that passes on constant/mocked totals
# is worthless. Perturb a single committed rate BY ONE UNIT in memory
# (never touching the file on disk) and assert the golden total genuinely
# moves — proving this suite would catch a one-character rate-card edit.
# ---------------------------------------------------------------------------


def test_perturbing_a_committed_rate_by_one_unit_moves_the_golden_total(monkeypatch):
    """Perturb New York's committed IATSE Local 600 camera rate
    (`iatse-l600-camera-us-ny-2025`, $947.58/day) by Decimal('1') to
    $948.58/day, in memory only, via `monkeypatch.setattr` on
    `engine.cost_localizer.load_union_rates` (the name `localize()` calls
    — patching `engine.union_rates.load_union_rates` directly would have
    no effect, since Python binds the imported name at import time). The
    committed YAML file itself is never touched, and `monkeypatch` reverts
    the substitution automatically at the end of this test.

    OBSERVED (this session, `uv run python` against the real pipeline,
    reproduced below independently by hand): the camera wage moves from
    $106,603 (112.5 days x $947.58, rounded) to $106,715 (112.5 x
    $948.58 = $106,715.25 -> $106,715, a $112 delta) and the camera
    fringe moves from $55,060 to $55,118 ($106,715 x 0.5165 =
    $55,118.2975 -> $55,118, a $58 delta) — moving `cost_total` by
    exactly $170, from $758,427 to $758,597.
    """

    def _perturbed_load_union_rates(paths=None):
        rows = real_load_union_rates(paths)
        return [
            (
                row.model_copy(update={"rate": str(Decimal(row.rate) + Decimal("1"))})
                if row.row_id == "iatse-l600-camera-us-ny-2025"
                else row
            )
            for row in rows
        ]

    monkeypatch.setattr(
        cost_localizer_module, "load_union_rates", _perturbed_load_union_rates
    )

    perturbed = _landed("data/cost_profiles/us-ny-new-york.yaml")

    assert perturbed.cost_total.value != NY_COST_TOTAL
    assert perturbed.cost_total.value == Decimal("758597")

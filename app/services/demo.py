"""app/services/demo.py — the business logic behind two of the demo
page's four beats (`GET /demo`, `app/routers/export.py`).

DMO-01 (open on validation) and DMO-04 (a city with no curated model,
researched live) are both existing surfaces — `/proof` (08-01) and
`/research` (Phase 7) — the demo route simply links to them rather than
rebuilding either. This module holds the two beats that need NEW
assembly: DMO-02 (the naive-percentage-arithmetic case) and DMO-03 (the
headline-rate-vs-net-cash ranking inversion).

Neither function below introduces new pricing logic — every real number
is produced by calling engine entry points other product surfaces
already use:

- `naive_arithmetic_example` (DMO-02) calls
  `engine.pipeline.price_jurisdiction` — the same single public entry
  point every priced total on this site goes through — against a
  committed, real fixture file that is ALREADY an engine-correctness
  regression for this exact worked example
  (`tests/fixtures/jurisdictions/synthetic-uk-style.yaml`, established by
  plan 02-04/02-05; see that file's own header comment for why it must
  never be presented as a model of the UK's actual programme). Reading a
  fixture from `tests/fixtures/` at request time mirrors
  `app/services/validate.py::VALIDATION_PAIRS_DIR`'s already-established
  pattern — not a new one this plan invents.

- `rate_ranking_inversion` (DMO-03) calls the identical two-step
  gross-credit computation `app/services/proof.py::_compute_gross_credit`
  already established for a disclosure comparison
  (`compute_qualifying_base` then `compute_gross_credit`, never the full
  `price_jurisdiction` — which raises before returning anything for a
  jurisdiction whose net cash cannot be computed), applied here to all
  four curated jurisdictions
  (`app.services._paths.RULESET_PATH_BY_JURISDICTION`) against one
  shared illustrative spend so the comparison is like-for-like. Net cash
  is then attempted separately, in its own try/except — catching the
  same `ValueError` `app/services/validate.py::reproduce_disclosure`
  already catches for New Jersey and Connecticut's undeclared
  transfer-discount ceiling (WINDOWS.md #3) — so a jurisdiction whose
  real cash value is not sourced is reported as unavailable, never
  fabricated (D-87), mirroring `engine.ranker.rank`'s own two-band,
  never-a-fabricated-number discipline (D-55/D-56), applied here to
  jurisdictions rather than cities.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.services._paths import REPO_ROOT, RULESET_PATH_BY_JURISDICTION
from engine.credit import compute_gross_credit
from engine.figure import Figure
from engine.models import load_ruleset
from engine.net_cash import ArrivalTiming, convert_to_net_cash
from engine.pipeline import price_jurisdiction
from engine.qualifying_base import SpendBreakdown, compute_qualifying_base
from engine.rounding import quantize_money

__all__ = [
    "DEMO_RANKING_SPEND",
    "UK_ILLUSTRATIVE_FIXTURE",
    "UK_ILLUSTRATIVE_SPEND",
    "JurisdictionRateRanking",
    "NaiveArithmeticExample",
    "RankingInversion",
    "naive_arithmetic_example",
    "rate_ranking_inversion",
]

# DMO-02: the exact committed engine-correctness fixture the £18M worked
# example (feasibility-incentives.md, PROJECT.md line 88) is built from.
# Its own header comment states this must NEVER be presented as, or
# mistaken for, a model of the United Kingdom's actual Independent Film
# Tax Credit programme — this module honours that by labelling every
# rendering of it as an illustrative arithmetic example, never a
# jurisdiction comparison.
UK_ILLUSTRATIVE_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "jurisdictions" / "synthetic-uk-style.yaml"
)
UK_ILLUSTRATIVE_SPEND = Decimal("18000000")

# DMO-03: one shared illustrative qualifying spend, applied identically
# to all four curated jurisdictions so the headline-rate-vs-net-cash
# comparison is like-for-like — never each jurisdiction's own disclosed
# production (which would compare different spends, not different
# rates).
DEMO_RANKING_SPEND = Decimal("10000000")


@dataclass(frozen=True)
class NaiveArithmeticExample:
    """DMO-02: the naive headline-rate arithmetic set against the real,
    fully-derived net-cash figure the engine computes for the identical
    spend. `naive_figure` carries no derivation of its own — that
    absence is the point: it is the number a naive reading of only the
    enhanced tier's headline rate produces, with no per-tier split, no
    cap, no tax. `correct_net_cash` is a real `engine.figure.Figure`,
    fully sourced and expandable through its own `inputs` tree, computed
    by the same `engine.pipeline.price_jurisdiction` entry point every
    other priced total on this site uses."""

    jurisdiction_label: str
    illustrative_disclaimer: str
    qualifying_spend: Decimal
    currency: str
    naive_rate: Decimal
    naive_figure: Decimal
    naive_derivation: str
    correct_net_cash: Figure
    overstatement_pct: Decimal


def naive_arithmetic_example() -> NaiveArithmeticExample:
    """Price the committed UK-style worked-example fixture through the
    real engine and set its correct, fully-derived net cash figure
    against the naive headline-rate arithmetic a producer reading only
    the enhanced tier's rate would compute by hand."""
    ruleset = load_ruleset(UK_ILLUSTRATIVE_FIXTURE)
    programme = ruleset.programmes[0]
    ceiling_split = programme.rate_structure.ceiling_split
    assert ceiling_split is not None and ceiling_split.enhanced_rate is not None, (
        "the committed UK-style fixture always declares a ceiling_split with an "
        "enhanced_rate — this is a fixture-authoring bug if it does not"
    )
    naive_rate = ceiling_split.enhanced_rate

    priced = price_jurisdiction(ruleset, UK_ILLUSTRATIVE_SPEND)
    programme_result = priced.programmes[0]
    net_cash = programme_result.net_cash.point
    assert net_cash is not None, (
        "the UK-style fixture's mechanism is nonrefundable_credit, taxable — "
        "convert_to_net_cash always resolves this to a single point value"
    )

    naive_figure = quantize_money(UK_ILLUSTRATIVE_SPEND * naive_rate)
    overstatement_pct = (
        (naive_figure - net_cash.value) / naive_figure * Decimal(100)
    ).quantize(Decimal("0.1"))

    return NaiveArithmeticExample(
        jurisdiction_label=ruleset.jurisdiction.name,
        illustrative_disclaimer=(
            "Illustrative arithmetic example only. This is a committed "
            "engine-correctness regression fixture "
            "(tests/fixtures/jurisdictions/synthetic-uk-style.yaml), never a "
            "curated jurisdiction, and never presented as a model of the "
            "United Kingdom's actual film tax credit programme — no "
            "per-production UK disclosure exists for this project to "
            "validate against, and the fixture's own header comment states "
            "this explicitly."
        ),
        qualifying_spend=UK_ILLUSTRATIVE_SPEND,
        currency=ruleset.jurisdiction.currency,
        naive_rate=naive_rate,
        naive_figure=naive_figure,
        naive_derivation=(
            f"{UK_ILLUSTRATIVE_SPEND} {ruleset.jurisdiction.currency} x "
            f"{naive_rate} (the enhanced tier's headline rate, applied to the "
            "whole spend, ignoring the ceiling split, the 80% cap and "
            f"corporation tax) = {naive_figure} {ruleset.jurisdiction.currency}"
        ),
        correct_net_cash=net_cash,
        overstatement_pct=overstatement_pct,
    )


@dataclass(frozen=True)
class JurisdictionRateRanking:
    """One jurisdiction's row in DMO-03's two orderings. `headline_rate`
    and `gross_credit` are always populated — the base-and-credit steps
    never depend on a sourced transfer-discount range. `net_cash` and
    `arrival` are populated only when this jurisdiction's mechanism
    fully resolves to a real cash figure; `net_cash_unavailable_reason`
    is populated (never both) when it does not."""

    jurisdiction_id: str
    jurisdiction_name: str
    qualifying_base: Figure
    gross_credit: Figure
    headline_rate: Decimal
    net_cash: Figure | None
    arrival: ArrivalTiming | None
    net_cash_unavailable_reason: str | None


@dataclass(frozen=True)
class RankingInversion:
    """DMO-03: both orderings of the same four curated jurisdictions,
    priced against the identical illustrative spend — by headline rate
    (`by_headline_rate`, every jurisdiction, always computable) and by
    real net cash (`by_net_cash`, only the jurisdictions whose mechanism
    fully resolves; `net_cash_unavailable` lists the rest, never given a
    fabricated number)."""

    qualifying_spend: Decimal
    currency: str
    by_headline_rate: tuple[JurisdictionRateRanking, ...]
    by_net_cash: tuple[JurisdictionRateRanking, ...]
    net_cash_unavailable: tuple[JurisdictionRateRanking, ...]


def _price_one_jurisdiction(
    jurisdiction_id: str, qualifying_spend: Decimal
) -> JurisdictionRateRanking:
    """The same two-step gross-credit computation
    `app/services/proof.py::_compute_gross_credit` already established
    (`compute_qualifying_base` then `compute_gross_credit`, never the
    full `price_jurisdiction` — which would raise before returning
    anything for a jurisdiction whose net cash cannot be computed),
    applied here to one shared illustrative spend rather than a
    disclosed production's own. Net cash is then attempted separately,
    in its own try/except, so a jurisdiction with no sourced
    transfer-discount range still reports a real, computed headline
    rate."""
    ruleset = load_ruleset(RULESET_PATH_BY_JURISDICTION[jurisdiction_id])
    programme = ruleset.programmes[0]

    spend = SpendBreakdown.from_total(qualifying_spend)
    qualifying_base = compute_qualifying_base(
        programme,
        spend,
        currency=ruleset.jurisdiction.currency,
        source_url=None,
        date_checked=None,
        # An illustrative shared spend, not a disclosed production's own
        # qualified spend — never "validated" (D-63).
        confidence="researched",
    )
    gross_credit = compute_gross_credit(programme, qualifying_base, annual_cap_remaining=None)
    headline_rate = (gross_credit.value / qualifying_base.value).quantize(Decimal("0.0001"))

    net_cash: Figure | None = None
    arrival: ArrivalTiming | None = None
    unavailable_reason: str | None = None
    try:
        net_cash_result = convert_to_net_cash(programme, gross_credit)
        net_cash = net_cash_result.point
        arrival = net_cash_result.arrival
        if net_cash is None:
            # A transferable mechanism with a FULLY declared range still
            # reports low/high with no single point — DMO-03 only ranks a
            # point figure, so this case is named too, never silently
            # ranked on one bound.
            unavailable_reason = (
                "this mechanism converts to a declared low/high cash range, not a "
                "single point figure — no single position to rank"
            )
    except ValueError as exc:
        unavailable_reason = str(exc)

    return JurisdictionRateRanking(
        jurisdiction_id=jurisdiction_id,
        jurisdiction_name=ruleset.jurisdiction.name,
        qualifying_base=qualifying_base,
        gross_credit=gross_credit,
        headline_rate=headline_rate,
        net_cash=net_cash,
        arrival=arrival if net_cash is not None else None,
        net_cash_unavailable_reason=unavailable_reason,
    )


def rate_ranking_inversion() -> RankingInversion:
    """DMO-03: price all four curated jurisdictions
    (`app.services._paths.RULESET_PATH_BY_JURISDICTION`) against the
    identical illustrative spend, then produce both orderings so a
    viewer sees the inversion directly rather than being told it
    happens."""
    rankings = tuple(
        _price_one_jurisdiction(jurisdiction_id, DEMO_RANKING_SPEND)
        for jurisdiction_id in RULESET_PATH_BY_JURISDICTION
    )
    by_headline_rate = tuple(sorted(rankings, key=lambda r: r.headline_rate, reverse=True))
    computable = tuple(r for r in rankings if r.net_cash is not None)
    unavailable = tuple(r for r in rankings if r.net_cash is None)
    by_net_cash = tuple(
        sorted(computable, key=lambda r: r.net_cash.value, reverse=True)
    )
    currency = rankings[0].gross_credit.unit
    return RankingInversion(
        qualifying_spend=DEMO_RANKING_SPEND,
        currency=currency,
        by_headline_rate=by_headline_rate,
        by_net_cash=by_net_cash,
        net_cash_unavailable=unavailable,
    )

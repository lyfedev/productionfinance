"""UI-11 — chosen-currency display with dual disclosure (Phase 6, plan
06-04).

Two distinct honesty mechanisms are proven here:

1. **The chosen-currency conversion** (`app.services.currency_display
   .build_city_displays`/`display_figure`) — a visitor's own pick,
   applied forward via `app.services.cache_policy.resolve_fx` (never
   `httpx`/`engine.fx` directly). Every test in this section monkeypatches
   `httpx.Client.get`, mirroring `tests/test_cache_policy_live.py`'s own
   established pattern — never a real network call.
2. **The original-currency disclosure** (`build_original_currency_figures`
   /`reconstruct_source_currency_total`) — the UNCONDITIONAL case: London
   priced in GBP (£548,595) but expressed as its USD total ($747,735,
   D-78's own pinned golden figure) always discloses the true GBP
   original, independent of any display-currency choice, reconstructed
   from the engine's own disclosed `Figure` tree, never re-derived.

Golden totals (D-78) are asserted unchanged regardless of
`display_currency` — this module is a pure display layer and must never
move a priced total.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.compare import CompareInputs, build_comparison
from app.services.currency_display import (
    DISPLAY_CURRENCIES,
    build_city_displays,
    build_original_currency_figures,
    display_figure,
    reconstruct_source_currency_total,
)
from engine.figure import Figure

client = TestClient(app)

# Sourced from 04-CONTEXT.md § D-70 — duplicated per this repo's
# established per-test-module discipline (never imported).
_PRESCRIPTIVE_VOCABULARY: tuple[str, ...] = (
    "recommend",
    "recommends",
    "recommended",
    "recommendation",
    "should",
    "consider",
    "considers",
    "considered",
    "considering",
    "best",
    "optimal",
    "you could",
    "you should",
)
_VOCABULARY_PATTERNS = {
    word: re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    for word in _PRESCRIPTIVE_VOCABULARY
}


def _money_figure(value: str, unit: str, *, label: str = "Test figure") -> Figure:
    return Figure(
        value=Decimal(value),
        unit=unit,
        label=label,
        derivation=("test fixture",),
        inputs=(),
        source_url="https://example.gov/rate",
        date_checked=date(2026, 1, 1),
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )


def _fake_frankfurter_success(rate: str):
    def _get(self, url, params=None, **kwargs):
        base = params["base"]
        quote = params["symbols"]
        payload = {"amount": 1.0, "base": base, "date": "2026-09-09", "rates": {quote: float(rate)}}
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    return _get


def _fake_frankfurter_failure(self, url, params=None, **kwargs):
    raise httpx.ConnectError("simulated network down")


# ---------------------------------------------------------------------------
# display_figure / build_city_displays — the chosen-currency conversion
# ---------------------------------------------------------------------------


def test_display_figure_same_currency_needs_no_conversion():
    figure = _money_figure("100", "USD")
    result = display_figure(figure, "USD", rate_or_error=None)
    assert result.original_value == Decimal(100)
    assert result.original_unit == "USD"
    assert result.converted_value is None
    assert result.conversion_refusal is None


def test_display_figure_live_rate_converts_and_marks_origin(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_success("1.4"))
    from app.services.cache_policy import resolve_fx

    resolution = resolve_fx("GBP", "USD", date(2026, 9, 9))
    figure = _money_figure("100", "GBP")
    result = display_figure(figure, "USD", resolution)
    assert result.original_value == Decimal(100)
    assert result.original_unit == "GBP"
    assert result.converted_value == Decimal(140)
    assert result.rate_origin == "live"
    assert result.rate is not None
    assert result.disclosure is not None
    assert result.conversion_refusal is None


def test_display_figure_fallback_rate_marks_snapshot_origin(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    from app.services.cache_policy import resolve_fx

    resolution = resolve_fx("GBP", "USD", date(2026, 9, 9))
    figure = _money_figure("1000", "GBP")
    result = display_figure(figure, "USD", resolution)
    assert result.rate_origin == "committed_snapshot_fallback"
    assert result.rate == Decimal("1.363")
    assert result.converted_value == Decimal(1363)
    assert result.rate_date == "2026-08-26"


def test_display_figure_no_live_and_no_fallback_snapshot_refuses_never_fabricates(monkeypatch):
    """USD->GBP has no committed snapshot (only gbp-usd.yaml is committed) —
    a live failure on that pair must surface as an explicit refusal, never
    a guessed number (D-74's own refuse-rather-than-derive discipline)."""
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    figure = _money_figure("500", "USD")
    error = ValueError("fx: no committed snapshot for USD->GBP")
    result = display_figure(figure, "GBP", error)
    assert result.converted_value is None
    assert result.rate is None
    assert result.conversion_refusal is not None
    assert "no committed snapshot" in result.conversion_refusal


def test_build_city_displays_resolves_one_rate_per_distinct_currency_not_per_figure(monkeypatch):
    """Several figures sharing a currency must reuse the SAME resolved
    rate — proven by counting the underlying transport calls, not just
    the returned values."""
    call_count = {"n": 0}

    def _counting_get(self, url, params=None, **kwargs):
        call_count["n"] += 1
        return _fake_frankfurter_success("1.5")(self, url, params=params, **kwargs)

    monkeypatch.setattr(httpx.Client, "get", _counting_get)

    inputs = CompareInputs(candidate_cities=["New York, NY", "Los Angeles, CA"])
    comparison = build_comparison(inputs)
    cities = (*comparison.net_ranked, *comparison.incentive_not_modelled)
    # Both cities are USD-priced (no conversion needed for a USD display
    # currency) — force a genuinely different display currency so every
    # money figure on both cities needs converting, all from the SAME
    # source currency (USD).
    displays = build_city_displays(cities, "GBP", on_date=date(2026, 9, 9))
    assert displays  # non-vacuous
    assert call_count["n"] == 1, f"expected exactly one resolve_fx call, got {call_count['n']}"


def test_build_city_displays_never_mutates_the_original_figure(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_success("1.4"))
    inputs = CompareInputs(candidate_cities=["New York, NY"])
    comparison = build_comparison(inputs)
    cities = comparison.net_ranked
    before = cities[0].total_landed_cost.value
    build_city_displays(cities, "GBP", on_date=date(2026, 9, 9))
    assert cities[0].total_landed_cost.value == before


# ---------------------------------------------------------------------------
# reconstruct_source_currency_total / build_original_currency_figures —
# the UNCONDITIONAL original-currency disclosure
# ---------------------------------------------------------------------------


def test_reconstruct_source_currency_total_none_when_no_conversion_occurred():
    """A figure whose OWN inputs never went through a currency
    conversion (e.g. a same-currency city) has nothing to reconstruct."""
    leaf = _money_figure("100", "USD")
    total = Figure(
        value=Decimal(100),
        unit="USD",
        label="Total cost (pre-incentive)",
        derivation=("summed",),
        inputs=(leaf,),
        source_url=None,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )
    assert reconstruct_source_currency_total(total, "USD") is None


def test_reconstruct_source_currency_total_matches_the_real_committed_london_figure():
    """The flagship proof: London's real committed data reconstructs to
    the EXACT documented golden pairing — £548,595 GBP / $747,735 USD
    (D-78) — using only data the engine already disclosed."""
    inputs = CompareInputs(candidate_cities=["London, UK"])
    comparison = build_comparison(inputs)
    london = next(
        c for c in (*comparison.net_ranked, *comparison.incentive_not_modelled)
        if c.city_id == "gb-london"
    )
    assert london.cost_only_total.value == Decimal(747735)
    assert london.cost_only_total.unit == "USD"
    reconstructed = reconstruct_source_currency_total(london.cost_only_total, "GBP")
    assert reconstructed == Decimal(548595)


def test_reconstruct_source_currency_total_excludes_the_fx_rate_component():
    """The FX rate itself (a leaf with a `USD per GBP`-shaped unit,
    D-75) must never be swept into the reconstructed sum — it carries a
    rate, not a cost."""
    inputs = CompareInputs(candidate_cities=["London, UK"])
    comparison = build_comparison(inputs)
    london = next(
        c for c in (*comparison.net_ranked, *comparison.incentive_not_modelled)
        if c.city_id == "gb-london"
    )
    fx_rate_entries = [entry for entry in london.cost_only_total.inputs if entry.unit == "USD per GBP"]
    assert fx_rate_entries, "expected the FX rate component to be present as its own input"
    reconstructed = reconstruct_source_currency_total(london.cost_only_total, "GBP")
    # A rate value (~1.363) folded in by mistake would move the total by
    # roughly that amount — nowhere near the exact £548,595.
    assert reconstructed == Decimal(548595)


def test_build_original_currency_figures_always_present_regardless_of_display_currency():
    """UI-11's core honesty requirement: the original is shown ALWAYS,
    independent of the visitor's chosen display currency — proven for
    BOTH members of DISPLAY_CURRENCIES."""
    inputs = CompareInputs(candidate_cities=["London, UK"])
    comparison = build_comparison(inputs)
    cities = (*comparison.net_ranked, *comparison.incentive_not_modelled)
    for _display_currency in DISPLAY_CURRENCIES:
        originals = build_original_currency_figures(cities)
        london = next(c for c in cities if c.city_id == "gb-london")
        entry = originals.get(london.cost_only_total.figure_id)
        assert entry is not None
        assert entry.source_currency == "GBP"
        assert entry.source_value == Decimal(548595)


def test_build_original_currency_figures_absent_for_same_currency_cities():
    inputs = CompareInputs(candidate_cities=["New York, NY", "Los Angeles, CA"])
    comparison = build_comparison(inputs)
    cities = (*comparison.net_ranked, *comparison.incentive_not_modelled)
    originals = build_original_currency_figures(cities)
    for city in cities:
        assert city.cost_only_total.figure_id not in originals
        assert city.total_landed_cost.figure_id not in originals


def test_build_original_currency_figures_reuses_reconstruction_for_total_landed_cost_when_no_incentive():
    inputs = CompareInputs(candidate_cities=["London, UK"])
    comparison = build_comparison(inputs)
    london = next(
        c for c in (*comparison.net_ranked, *comparison.incentive_not_modelled)
        if c.city_id == "gb-london"
    )
    assert london.incentive_figure is None
    originals = build_original_currency_figures((london,))
    assert originals[london.total_landed_cost.figure_id] == originals[london.cost_only_total.figure_id]


def test_build_original_currency_figures_skips_a_netted_incentive_total_defensively():
    """A city whose total WAS netted against an incentive (a
    same-currency `total_landed_cost != cost_only_total`) never gets a
    reconstructed original attached to `total_landed_cost` — this module
    refuses to guess at a netted total's pre-conversion value rather
    than risk a silently wrong figure (never arises against the real
    committed data today; proven directly against a synthetic
    RankedCity so the guard itself is exercised, not just its absence)."""

    from engine.landed_cost import LandedCost
    from engine.ranker import RankedCity

    # A "converted line" — the exact shape `engine.landed_cost
    # ._convert_cost_lines` produces: a USD-unit Figure whose single
    # `.inputs[0]` is the untouched GBP original.
    original_leaf = _money_figure("1000", "GBP")
    converted_line = Figure(
        value=Decimal(1000),
        unit="USD",
        label="Test line",
        derivation=("converted",),
        inputs=(original_leaf,),
        source_url=None,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )
    cost_only = Figure(
        value=Decimal(1000),
        unit="USD",
        label="Total cost (pre-incentive)",
        derivation=("summed",),
        inputs=(converted_line,),
        source_url=None,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )
    incentive = _money_figure("200", "USD", label="Net cash incentive")
    total = Figure(
        value=Decimal(800),
        unit="USD",
        label="Total landed cost",
        derivation=("netted",),
        inputs=(cost_only, incentive),
        source_url=None,
        date_checked=None,
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )
    landed = LandedCost(
        cost_total=cost_only,
        total_landed_cost=total,
        not_priced=(),
        permanent_exclusions=(),
        reporting_currency="USD",
        source_currency="GBP",
        fx_as_of_date=date(2026, 1, 1),
    )
    city = RankedCity(
        city_id="synthetic",
        total_landed_cost=total,
        band="net_ranked",
        reason=None,
        incentive_figure=incentive,
        cost_only_total=cost_only,
        landed_cost=landed,
    )
    originals = build_original_currency_figures((city,))
    # cost_only_total is still safely reconstructed (a pure sum)...
    assert city.cost_only_total.figure_id in originals
    # ...but total_landed_cost is NOT, since incentive_figure is not None.
    assert city.total_landed_cost.figure_id not in originals


# ---------------------------------------------------------------------------
# End-to-end over the real HTTP surface
# ---------------------------------------------------------------------------


def test_get_compare_default_usd_shows_londons_original_gbp_figure_unconditionally(monkeypatch):
    # Patched at `_fetch_live_rate` (never `httpx.Client.get` directly) —
    # `TestClient` itself is httpx-backed, so patching the transport
    # layer globally would ALSO break the test client's own request to
    # the ASGI app, not just the app's outbound FX check.
    monkeypatch.setattr(
        "app.services.live_fx._fetch_live_rate",
        lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("simulated network down")),
    )
    response = client.get("/compare")
    assert response.status_code == 200
    html = response.text
    assert "data-currency-original" in html
    assert "548595 GBP" in html
    assert "as originally priced" in html


def test_get_compare_gbp_display_converts_usd_totals_and_marks_them_when_live_succeeds(monkeypatch):
    """USD->GBP has no committed fallback snapshot (only gbp-usd.yaml is
    committed) — the converted case is only reachable when the live
    check succeeds."""
    monkeypatch.setattr("app.services.live_fx._fetch_live_rate", lambda *a, **k: Decimal("0.74"))
    response = client.get("/compare", params={"display_currency": "GBP"})
    assert response.status_code == 200
    html = response.text
    assert "data-currency-converted" in html
    assert "(converted)" in html
    assert 'rate live' in html


def test_get_compare_gbp_display_refuses_never_fabricates_when_live_fails():
    """The honest counterpart: with no committed USD->GBP fallback,
    a live failure surfaces as an explicit refusal — never a guessed
    GBP figure for New York/Los Angeles."""
    monkeypatch_target = "app.services.live_fx._fetch_live_rate"
    from unittest import mock

    with mock.patch(monkeypatch_target, side_effect=httpx.ConnectError("simulated network down")):
        response = client.get("/compare", params={"display_currency": "GBP"})
    assert response.status_code == 200
    html = response.text
    assert "data-currency-refusal" in html
    assert "no committed snapshot" in html
    assert "data-currency-converted" not in html


def test_get_compare_golden_totals_unaffected_by_display_currency(monkeypatch):
    """D-78: the priced totals themselves never move because of a
    display-currency choice — the ORIGINAL figure on screen must be
    byte-identical regardless."""
    monkeypatch.setattr(
        "app.services.live_fx._fetch_live_rate",
        lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("simulated network down")),
    )
    for currency in ("USD", "GBP"):
        response = client.get("/compare", params={"display_currency": currency})
        assert response.status_code == 200
        html = response.text
        assert "758427" in html  # NY
        assert "693521" in html  # LA
        assert "747735" in html  # London (USD, reporting currency)


def test_currency_selector_offers_exactly_display_currencies():
    response = client.get("/compare")
    html = response.text
    for code in DISPLAY_CURRENCIES:
        assert f'value="{code}"' in html


def test_get_compare_currency_section_d70_vocabulary_gate():
    response = client.get("/compare", params={"display_currency": "GBP"})
    html = response.text
    match = re.search(
        r'<section class="pf-currency-section"[^>]*>(.*?)</section>', html, re.DOTALL
    )
    assert match, "currency section not found"
    section_html = match.group(1)
    violations = [
        word for word, pattern in _VOCABULARY_PATTERNS.items() if pattern.search(section_html)
    ]
    assert not violations, f"prescriptive vocabulary found in currency section: {violations}"


def test_static_prodfin_css_d70_vocabulary_gate_over_new_currency_rules():
    css_path = __file__.replace("tests/test_app_currency_display.py", "app/static/prodfin.css")
    with open(css_path, encoding="utf-8") as handle:
        css = handle.read()
    violations = [word for word, pattern in _VOCABULARY_PATTERNS.items() if pattern.search(css)]
    assert not violations, f"prescriptive vocabulary found in prodfin.css: {violations}"

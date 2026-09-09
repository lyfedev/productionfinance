"""AGT-10's caching boundary made real across all five data classes
(plan 07-04) — Task 1 (live FX) lands here first; Task 2 (live cap
consumption / programme status) and Task 3 (the single-point-of-truth AST
gate, plus the uncurated-city -> /research entry path, AGT-05) extend this
same file.

Every SDK-touching test in this file either exercises the "no keys
present" undetermined path (deterministic, no network, matches this
project's `.env`-free execution environment) or injects fakes — never a
real live SDK call. The one live network call this plan genuinely proves
(Frankfurter, no key required) is exercised directly against
`httpx.Client.get`, which this file's own tests monkeypatch to control
success/failure deterministically; the confirmed real transcript lives in
07-04-SUMMARY.md, not in this file's assertions.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.services.cache_policy import POLICY, CacheBoundaryViolation, DataClass, resolve_fx
from app.services.spec import SpecFormSubmission, SpecResult, handle_spec_submission

REPO_ROOT = Path(__file__).resolve().parents[1]


def _base_form_kwargs(**overrides: object) -> dict:
    kwargs = {
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
        "candidate_cities": ["London"],
        "total_budget": None,
    }
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# Task 1 — live FX (`-k "fx"`)
# ---------------------------------------------------------------------------


def _fake_frankfurter_success(rate: str):
    def _get(self, url, params=None, **kwargs):
        base = params["base"]
        quote = params["symbols"]
        payload = {
            "amount": 1.0,
            "base": base,
            "date": "2026-09-09",
            "rates": {quote: float(rate)},
        }
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    return _get


def _fake_frankfurter_failure(self, url, params=None, **kwargs):
    raise httpx.ConnectError("simulated network down")


def test_resolve_fx_attempts_live_first_and_succeeds(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_success("1.4"))
    resolution = resolve_fx("GBP", "USD", date(2026, 9, 9))
    assert resolution.origin == "live"
    assert resolution.rate == Decimal("1.4")
    assert isinstance(resolution.rate, Decimal)
    assert resolution.fetched_at is not None
    assert resolution.failure_reason is None
    assert "1.4" in resolution.disclosure


def test_resolve_fx_falls_back_and_names_the_snapshot_date_on_failure(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    resolution = resolve_fx("GBP", "USD", date(2026, 9, 9))
    assert resolution.origin == "committed_snapshot_fallback"
    assert resolution.rate == Decimal("1.363")
    assert resolution.snapshot_date == "2026-08-26"
    assert resolution.failure_reason is not None
    assert "2026-08-26" in resolution.disclosure
    assert "failed" in resolution.disclosure.lower()


def test_resolve_fx_never_derives_a_cross_rate_or_inverts_on_a_missing_snapshot(monkeypatch):
    """Only `data/fx/gbp-usd.yaml` is committed — the reverse pair
    (USD->GBP) has no snapshot. A live failure here must raise the same
    D-74 refusal `engine.fx` raises, never a derived or inverted rate."""
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    with pytest.raises(ValueError, match="no committed snapshot"):
        resolve_fx("USD", "GBP", date(2026, 9, 9))


def test_resolve_fx_asserts_live_and_never_fetches_when_policy_mutated(monkeypatch):
    mutated = dataclasses.replace(POLICY[DataClass.fx_rate], verdict="cached")
    monkeypatch.setitem(POLICY, DataClass.fx_rate, mutated)

    fetch_attempts: list[str] = []
    monkeypatch.setattr(httpx.Client, "get", lambda self, *a, **k: fetch_attempts.append(a) or None)

    with pytest.raises(CacheBoundaryViolation):
        resolve_fx("GBP", "USD", date(2026, 9, 9))
    assert fetch_attempts == []


def test_golden_totals_pinned_regardless_of_live_fx_outcome(monkeypatch):
    """AGT-10's core promise for FX: the /spec dollar total is computed
    exclusively from the committed snapshot (`engine.fx.convert`) and
    never moves because of what `resolve_fx` discloses — see
    `app/services/live_fx.py`'s module docstring."""

    def _submit() -> SpecResult:
        raw = SpecFormSubmission(**_base_form_kwargs())
        result = handle_spec_submission(raw)
        assert isinstance(result, SpecResult)
        return result

    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_success("1.4"))
    live_result = _submit()
    assert live_result.fx_resolutions
    assert live_result.fx_resolutions[0].origin == "live"
    assert live_result.ranked_cities[0].total_landed_cost.value == Decimal("747735")

    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    fallback_result = _submit()
    assert fallback_result.fx_resolutions[0].origin == "committed_snapshot_fallback"
    assert fallback_result.ranked_cities[0].total_landed_cost.value == Decimal("747735")


def test_ny_vs_la_gap_unaffected_by_fx_wiring(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    raw = SpecFormSubmission(
        **_base_form_kwargs(candidate_cities=["New York, NY", "Los Angeles, CA"])
    )
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.gap is not None
    assert result.gap.headline_gap.value == Decimal("64906")
    # Neither city needs a currency conversion (both USD) — no FX call at all.
    assert result.fx_resolutions == ()

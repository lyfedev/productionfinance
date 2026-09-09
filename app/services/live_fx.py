"""Live FX rate resolution (Task 1, plan 07-04) — Frankfurter's no-key
dated-rate endpoint, attempted on every request that needs a currency
check, with a disclosed fallback to the committed snapshot (D-89/AGT-10).

`app.services.cache_policy.resolve_fx` is the sanctioned entry point a
caller should use — it delegates here. This module ALSO asserts live
itself (`assert_live(DataClass.fx_rate)`, defense in depth, mirroring
`agent/job2.py`'s dual-validation pattern from plan 07-01's own precedent)
so a future caller that imports `resolve_fx` from this module directly,
bypassing `app.services.cache_policy.resolve_fx`, still cannot silently
read a cache.

**Confirmed against the live Frankfurter service during this plan's own
execution session** (not reconstructed from memory — see 07-04-SUMMARY.md
for the transcript):

    GET https://api.frankfurter.dev/v1/2024-06-03?base=GBP&symbols=USD
    -> {"amount":1.0,"base":"GBP","date":"2024-06-03","rates":{"USD":1.2729}}

The rate is built from the JSON response's own numeric field via
`str(...)` before `Decimal(...)` — never a float hop through Python
arithmetic (mirrors `engine.fx.FxSnapshot`'s own RD-01 discipline).

**The dollar totals `/spec` renders (`total_landed_cost`/`cost_only_total`)
are UNAFFECTED by this module's outcome.** They are computed exclusively
by `engine.landed_cost.aggregate` -> `engine.fx.convert`, which reads only
the committed, dated, cited snapshot — an engine seam this plan does not
touch (`engine/fx.py`'s own docstring: "never a live call at runtime").
This resolution is rendered as its own, separately-labelled disclosure
next to the converted total (T-07-24) — a live FX *check*, genuinely
attempted on the request per D-89, kept structurally apart from the
pinned, reproducible arithmetic a "provably matching what a government
actually paid" total requires. This is what keeps the D-78 golden totals
exact regardless of live network availability, while still making AGT-10's
`fx_rate` data class genuinely live rather than decorative.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from app.services.cache_policy import DataClass, assert_live
from engine.fx import load_fx_snapshot

__all__ = [
    "FRANKFURTER_BASE_URL",
    "FX_FETCH_TIMEOUT_SECONDS",
    "FxResolution",
    "resolve_fx",
]

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"

# Short and explicit (T-07-22): a slow or unreachable currency service must
# never hold a visitor's /spec request open.
FX_FETCH_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class FxResolution:
    """One base->quote FX resolution as of one request. `origin` is the
    closed two-value field T-07-24 names as the mechanism that keeps a
    fallback rate from ever being presented as a live one — the page never
    renders `rate` without also rendering `origin` and `disclosure`."""

    base: str
    quote: str
    rate: Decimal
    origin: Literal["live", "committed_snapshot_fallback"]
    fetched_at: str | None
    snapshot_date: str | None
    disclosure: str
    failure_reason: str | None


def _fetch_live_rate(base: str, quote: str, on_date: date) -> Decimal:
    """One bounded HTTP call to Frankfurter's dated endpoint. Raises on
    any failure — connection error, timeout, non-2xx status, a response
    carrying no rate for `quote`, or a non-numeric rate value — so the
    caller's single `except` degrades to the disclosed committed-snapshot
    fallback (never a guess, never a silently-substituted stale figure)."""
    url = f"{FRANKFURTER_BASE_URL}/{on_date.isoformat()}"
    with httpx.Client(timeout=FX_FETCH_TIMEOUT_SECONDS) as client:
        response = client.get(url, params={"base": base, "symbols": quote})
    response.raise_for_status()
    payload = response.json()
    rates = payload.get("rates") or {}
    if quote not in rates:
        raise ValueError(
            f"frankfurter response for {base}->{quote} on {on_date} carries no "
            f"{quote!r} rate: {payload!r}"
        )
    try:
        # str(...) first — the JSON value may already be a native float;
        # Decimal(a_float) directly would corrupt it past the fifteenth
        # significant digit (RD-01's exact failure mode).
        return Decimal(str(rates[quote]))
    except InvalidOperation as exc:
        raise ValueError(
            f"frankfurter rate for {base}->{quote} on {on_date} is not numeric: {rates[quote]!r}"
        ) from exc


def resolve_fx(base: str, quote: str, on_date: date) -> FxResolution:
    """Attempt a live Frankfurter fetch for `base`->`quote`; on ANY
    failure, fall back to the committed dated snapshot via
    `engine.fx.load_fx_snapshot` — never derives a cross-rate, never
    inverts a snapshot for the reverse direction (mirrors `engine.fx`'s own
    D-74 refusal exactly). Raises the same `ValueError` `engine.fx` raises
    when no committed snapshot exists for the pair either — there is
    nothing left to disclose in that case."""
    assert_live(DataClass.fx_rate)

    now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    try:
        rate = _fetch_live_rate(base, quote, on_date)
    except Exception as exc:  # noqa: BLE001 — any failure degrades to the disclosed fallback
        snapshot = load_fx_snapshot(base, quote)
        snapshot_rate = Decimal(snapshot.rate)
        return FxResolution(
            base=base,
            quote=quote,
            rate=snapshot_rate,
            origin="committed_snapshot_fallback",
            fetched_at=None,
            snapshot_date=snapshot.as_of_date,
            failure_reason=str(exc),
            disclosure=(
                f"Live {base}→{quote} FX check failed at request time ({exc}) "
                f"— showing the committed snapshot instead: 1 {base} = "
                f"{snapshot_rate} {quote} as of {snapshot.as_of_date} (source: "
                f"{snapshot.source_url})."
            ),
        )

    return FxResolution(
        base=base,
        quote=quote,
        rate=rate,
        origin="live",
        fetched_at=now,
        snapshot_date=None,
        failure_reason=None,
        disclosure=(
            f"Live {base}→{quote} FX check succeeded: 1 {base} = {rate} "
            f"{quote}, fetched at {now} from Frankfurter (api.frankfurter.dev)."
        ),
    )

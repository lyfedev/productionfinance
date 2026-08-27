"""Dated FX conversion — currency as a first-class, cited component
(COST-08, D-74/D-75, 04-CONTEXT.md).

A committed, dated snapshot under `data/fx/`, never a live call at runtime
(D-57): `data/fx/gbp-usd.yaml` was fetched once from Frankfurter's no-key
dated endpoint and archived under `sources/fx/` with a `sources/MANIFEST
.yaml` entry (D-10). Phase 7's freshness gate takes this live later.

**Refuse rather than derive (D-74)**, mirroring
`engine.net_cash.transferable`'s refusal shape exactly (the same class of
honesty `.planning/WINDOWS.md` entry 3 already established): a pair with
no committed snapshot raises naming both currencies, rather than deriving
a cross-rate through a third currency. The reverse direction is NEVER
served by inverting a committed rate — converting USD to GBP requires its
own committed `usd-gbp.yaml`; a `gbp-usd.yaml` snapshot alone never
licenses `1/rate` for the opposite direction. This is structural: `convert`
and `load_fx_snapshot` both look up the file named EXACTLY
`{base}-{quote}.yaml`, never `{quote}-{base}.yaml` inverted.

`SUPPORTED_CURRENCY_CODES` is a closed, committed tuple validated BEFORE
any string is joined into a filename (T-04-20) — a currency code is never
freely interpolated into a `Path`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from engine.figure import Figure
from engine.rounding import quantize_money

__all__ = [
    "FX_DIR",
    "SUPPORTED_CURRENCY_CODES",
    "FxSnapshot",
    "convert",
    "load_fx_snapshot",
    "rate_figure",
]

# Module-anchored, never CWD-relative — matches every sibling reference-
# data module's own directory constant (`engine.cost_profile
# .COST_PROFILES_DIR`, `engine.union_rates.UNION_RATES_DIR`, etc.).
FX_DIR = Path(__file__).resolve().parents[1] / "data" / "fx"

# T-04-20: the closed, committed set of currency codes this project may
# ever convert between — never derived from a visitor string, never
# widened by interpolating an arbitrary code into a filename. The
# committed city set (D-54) is USD-only except London (GBP); widen this
# tuple only when a new city's cost profile genuinely needs a new
# currency, alongside its own committed snapshot.
SUPPORTED_CURRENCY_CODES: tuple[str, ...] = ("USD", "GBP")


class StrictModel(BaseModel):
    """Local mirror of `engine.cost_profile.StrictModel` (forbids
    unrecognised fields). Deliberately not imported from that module — a
    domain model should not drag its import graph in for a two-line
    convention (matches every other module in this phase's own
    precedent)."""

    model_config = ConfigDict(extra="forbid")


class FxSnapshot(StrictModel):
    """One committed dated FX snapshot — exactly the D-74 field list.
    `rate` is a quoted string (RD-01), parsed with `Decimal()` here at
    load time (never as a bare YAML-native float) so a zero, negative or
    non-numeric rate is rejected before any conversion is attempted."""

    base: str
    quote: str
    rate: str
    as_of_date: str
    source_url: str
    retrieved_at: str

    @model_validator(mode="after")
    def _rate_is_a_positive_decimal(self) -> FxSnapshot:
        try:
            value = Decimal(self.rate)
        except InvalidOperation as exc:
            raise ValueError(
                f"fx snapshot {self.base}-{self.quote}: rate {self.rate!r} is not a "
                "valid decimal string"
            ) from exc
        if value <= 0:
            raise ValueError(
                f"fx snapshot {self.base}-{self.quote}: rate must be strictly "
                f"positive, got {self.rate!r} — a zero or negative rate is rejected "
                "at load time"
            )
        return self


def _snapshot_filename(base: str, quote: str) -> str:
    return f"{base.lower()}-{quote.lower()}.yaml"


def load_fx_snapshot(base: str, quote: str) -> FxSnapshot:
    """The single FX-snapshot read path. `base`/`quote` are validated
    against the closed `SUPPORTED_CURRENCY_CODES` tuple BEFORE being
    joined into a filename — an unsupported code never reaches `Path`
    construction (T-04-20). Parses with `yaml.safe_load` only. A missing
    pair (unsupported code, or a supported pair with no committed file —
    including the reverse of a committed pair) raises `ValueError` naming
    both currencies and stating the conversion is refused rather than
    derived (D-74)."""
    if base not in SUPPORTED_CURRENCY_CODES or quote not in SUPPORTED_CURRENCY_CODES:
        raise ValueError(
            f"fx: unsupported currency pair {base!r}/{quote!r} — only "
            f"{SUPPORTED_CURRENCY_CODES} are committed currency codes; refusing "
            "rather than deriving a cross-rate or inverting a reverse pair (D-74)"
        )

    path = FX_DIR / _snapshot_filename(base, quote)
    if not path.is_file():
        raise ValueError(
            f"fx: no committed snapshot for {base}->{quote} at {path} — refusing "
            "rather than deriving a cross-rate through a third currency, or "
            f"inverting the reverse ({quote}->{base}) snapshot even if one exists "
            "(D-74): a committed snapshot for one direction never licenses the "
            "opposite direction"
        )

    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    snapshot = FxSnapshot.model_validate(raw)
    if snapshot.base != base or snapshot.quote != quote:
        raise ValueError(
            f"fx: snapshot at {path} declares base={snapshot.base!r} "
            f"quote={snapshot.quote!r}, expected base={base!r} quote={quote!r} — "
            "a mislabelled snapshot file must surface, never be silently used"
        )
    return snapshot


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def convert(amount: Decimal, base: str, quote: str) -> Figure:
    """Convert `amount` from `base` to `quote` as its own cited `Figure`.

    `base == quote` is an identity conversion — the amount is returned
    unchanged, in a Figure whose derivation says no conversion was
    applied. Otherwise a committed `{base}-{quote}` snapshot is required;
    `load_fx_snapshot` raises with the D-74 refusal message when none
    exists (including when only the REVERSE pair's snapshot exists — see
    its docstring).

    `value = quantize_money(amount * Decimal(snapshot.rate))` — exactly
    one quantize call, applied to the final product only. `snapshot.rate`
    itself is never quantized and no intermediate rounding occurs.
    """
    if base == quote:
        return Figure(
            value=amount,
            unit=quote,
            label=f"FX conversion {base}->{quote}",
            derivation=(
                f"{amount} {base} == {amount} {quote}: base and quote currency are "
                "identical, no conversion applied",
            ),
            inputs=(),
            source_url=None,
            date_checked=None,
            confidence="researched",
            live_fetched_this_run=False,
            basis="sourced",
        )

    snapshot = load_fx_snapshot(base, quote)
    rate = Decimal(snapshot.rate)
    value = quantize_money(amount * rate)

    return Figure(
        value=value,
        unit=quote,
        label=f"FX conversion {base}->{quote}",
        derivation=(
            f"{amount} {base} x {rate} ({base}->{quote} rate, as_of "
            f"{snapshot.as_of_date}) = {value} {quote} — a single quantize applied "
            "to this product only; the rate itself is never quantized",
            f"committed dated snapshot, not a live quote (D-57) — source: "
            f"{snapshot.source_url}, retrieved {snapshot.retrieved_at}",
        ),
        inputs=(),
        source_url=snapshot.source_url,
        date_checked=_parse_date(snapshot.as_of_date),
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )


def rate_figure(base: str, quote: str) -> Figure:
    """The FX rate ITSELF as its own cited `Figure` (D-75) — not a money
    amount converted at that rate, but the rate as a component in its own
    right. This is the object plan 04-06's currency line in the gap
    decomposition attaches to: its own `value`, its own `as_of_date`, its
    own `source_url`, distinct from any converted cost figure.

    Raises for an identity pair (`base == quote`) — a rate figure for a
    currency converted to itself is meaningless (there is no rate to
    report)."""
    if base == quote:
        raise ValueError(
            f"fx.rate_figure: base and quote are both {base!r} — a rate figure for "
            "an identity conversion is meaningless (there is no rate)"
        )

    snapshot = load_fx_snapshot(base, quote)
    rate = Decimal(snapshot.rate)
    return Figure(
        value=rate,
        unit=f"{quote} per {base}",
        label=f"FX rate {base}->{quote}",
        derivation=(
            f"1 {base} = {rate} {quote}, as of {snapshot.as_of_date} — a committed "
            f"dated snapshot (source: {snapshot.source_url}, retrieved "
            f"{snapshot.retrieved_at}), never a live quote (D-57)",
        ),
        inputs=(),
        source_url=snapshot.source_url,
        date_checked=_parse_date(snapshot.as_of_date),
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )

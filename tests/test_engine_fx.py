"""Tests for engine/fx.py — the committed dated FX snapshot and the
refuse-rather-than-derive conversion reader (COST-08, D-74/D-75)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

import engine.fx as fx
from engine.fx import FxSnapshot, convert, load_fx_snapshot, rate_figure
from engine.rounding import quantize_money


def _snapshot_kwargs(**overrides):
    base = {
        "base": "GBP",
        "quote": "USD",
        "rate": "1.363",
        "as_of_date": "2026-08-26",
        "source_url": "https://api.frankfurter.dev/v1/2026-08-26?base=GBP&symbols=USD",
        "retrieved_at": "2026-08-26",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# The committed gbp-usd.yaml snapshot loads and is well-formed.
# ---------------------------------------------------------------------------


def test_committed_gbp_usd_snapshot_loads():
    snapshot = load_fx_snapshot("GBP", "USD")
    assert snapshot.base == "GBP"
    assert snapshot.quote == "USD"
    assert Decimal(snapshot.rate) > 0
    assert snapshot.as_of_date == "2026-08-26"
    assert snapshot.source_url


def test_convert_real_snapshot_carries_basis_sourced_and_date_checked():
    figure = convert(Decimal("100"), "GBP", "USD")
    assert figure.basis == "sourced"
    assert figure.source_url is not None
    assert figure.date_checked is not None
    assert figure.date_checked.isoformat() == "2026-08-26"
    assert figure.unit == "USD"


# ---------------------------------------------------------------------------
# Refuse rather than derive (D-74).
# ---------------------------------------------------------------------------


def test_missing_pair_raises_naming_both_currencies():
    with pytest.raises(ValueError) as exc_info:
        convert(Decimal("100"), "USD", "EUR")
    message = str(exc_info.value)
    assert "USD" in message
    assert "EUR" in message


def test_no_implicit_inversion_usd_to_gbp_raises():
    # Only gbp-usd.yaml is committed — usd-gbp.yaml does not exist. The
    # reverse direction must refuse, never invert 1/rate.
    with pytest.raises(ValueError) as exc_info:
        convert(Decimal("100"), "USD", "GBP")
    message = str(exc_info.value)
    assert "USD" in message
    assert "GBP" in message


def test_load_fx_snapshot_missing_pair_raises_naming_both_currencies():
    with pytest.raises(ValueError, match="USD"):
        load_fx_snapshot("USD", "GBP")


# ---------------------------------------------------------------------------
# Identity conversion.
# ---------------------------------------------------------------------------


def test_identity_conversion_returns_amount_unchanged():
    figure = convert(Decimal("250"), "GBP", "GBP")
    assert figure.value == Decimal("250")
    assert figure.unit == "GBP"


def test_rate_figure_raises_for_identity_pair():
    with pytest.raises(ValueError, match="GBP"):
        rate_figure("GBP", "GBP")


# ---------------------------------------------------------------------------
# Load-time rejection of a zero, negative, or non-numeric rate.
# ---------------------------------------------------------------------------


def test_zero_rate_rejected_at_load():
    with pytest.raises(ValidationError):
        FxSnapshot.model_validate(_snapshot_kwargs(rate="0"))


def test_negative_rate_rejected_at_load():
    with pytest.raises(ValidationError):
        FxSnapshot.model_validate(_snapshot_kwargs(rate="-1.5"))


def test_non_numeric_rate_rejected_at_load():
    with pytest.raises(ValidationError):
        FxSnapshot.model_validate(_snapshot_kwargs(rate="not-a-number"))


# ---------------------------------------------------------------------------
# A rate of exactly "1" returns the input amount unchanged.
# ---------------------------------------------------------------------------


def test_rate_of_exactly_one_returns_input_unchanged(monkeypatch):
    identity_rate_snapshot = FxSnapshot.model_validate(_snapshot_kwargs(rate="1"))
    monkeypatch.setattr(fx, "load_fx_snapshot", lambda base, quote: identity_rate_snapshot)

    figure = convert(Decimal("437"), "GBP", "USD")

    assert figure.value == Decimal("437")


# ---------------------------------------------------------------------------
# The pinned ROUND_HALF_UP mode, not the ambient ROUND_HALF_EVEN default.
# ---------------------------------------------------------------------------


def test_half_dollar_boundary_rounds_up_under_pinned_round_half_up(monkeypatch):
    # 5 GBP x 0.5 = 2.50 exactly. ROUND_HALF_UP rounds this to 3.
    # ROUND_HALF_EVEN (Python Decimal's ambient default) would round this
    # to 2 (the nearest even integer) — a different answer, which is
    # exactly why the rounding mode must be an explicit, tested constant.
    snapshot = FxSnapshot.model_validate(_snapshot_kwargs(rate="0.5"))
    monkeypatch.setattr(fx, "load_fx_snapshot", lambda base, quote: snapshot)

    figure = convert(Decimal("5"), "GBP", "USD")

    assert figure.value == Decimal("3")


# ---------------------------------------------------------------------------
# Exactly one quantize is applied — the rate itself is never quantized.
# ---------------------------------------------------------------------------


def test_single_quantize_applied_the_rate_itself_is_never_quantized(monkeypatch):
    # amount=10, rate=0.125 -> the correct product is 1.25, which
    # quantize_money (ROUND_HALF_UP) rounds DOWN to 1 (0.25 < 0.5). If the
    # RATE itself had been quantized first (as a whole-dollar figure,
    # which is a category error but a real bug class this test guards
    # against), 0.125 would round to 0, and 10 x 0 = 0 — a result that
    # differs from the correct answer by exactly one unit. Constructing
    # the case this way proves the single-quantize-of-the-final-product
    # discipline is load-bearing, not vacuous.
    amount = Decimal("10")
    rate = "0.125"
    snapshot = FxSnapshot.model_validate(_snapshot_kwargs(rate=rate))
    monkeypatch.setattr(fx, "load_fx_snapshot", lambda base, quote: snapshot)

    figure = convert(amount, "GBP", "USD")

    correct = quantize_money(amount * Decimal(rate))
    wrong_pre_quantized_rate = quantize_money(amount * quantize_money(Decimal(rate)))

    assert correct != wrong_pre_quantized_rate
    assert abs(correct - wrong_pre_quantized_rate) == Decimal("1")
    assert figure.value == correct
    assert figure.value != wrong_pre_quantized_rate


# ---------------------------------------------------------------------------
# rate_figure — the rate itself as its own cited component (D-75).
# ---------------------------------------------------------------------------


def test_rate_figure_carries_the_rate_as_its_value_not_a_converted_amount():
    figure = rate_figure("GBP", "USD")
    assert figure.value == Decimal("1.363")
    assert figure.unit == "USD per GBP"
    assert figure.basis == "sourced"
    assert figure.source_url is not None
    assert figure.date_checked is not None


def test_unsupported_currency_code_never_reaches_a_path_join():
    # An unsupported code is rejected before any filesystem access —
    # asserted indirectly: the error names the unsupported code and the
    # message states the refusal reason, never a raw filesystem error
    # (e.g. FileNotFoundError, PermissionError) that would indicate an
    # arbitrary string was interpolated into a Path first.
    with pytest.raises(ValueError, match="unsupported currency pair"):
        load_fx_snapshot("XYZ", "USD")

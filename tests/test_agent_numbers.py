"""D-88: `agent.numbers.parse_money` must accept every locale convention the
project's currencies actually present with, and must RAISE rather than
guess on anything genuinely ambiguous — refusing beats guessing (T-05-08).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.numbers import UnparseableFigureError, parse_money


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$3,964,760", Decimal("3964760")),
        ("3,964,760.00", Decimal("3964760.00")),
        ("3.964.760,00", Decimal("3964760.00")),
        ("(1,234)", Decimal("-1234")),
        ("991,190*", Decimal("991190")),
        ("1 234 567", Decimal("1234567")),
        # narrow non-breaking space grouping (U+202F)
        ("1 234 567", Decimal("1234567")),
        # non-breaking space grouping (U+00A0)
        ("1 234 567", Decimal("1234567")),
        # leading footnote marker
        ("*991,190", Decimal("991190")),
        # superscript-digit footnote marker
        ("991,190¹", Decimal("991190")),
        # Unicode minus sign
        ("−991,190", Decimal("-991190")),
        # no separators at all
        ("991190", Decimal("991190")),
        # other declared currency symbols
        ("£1,234", Decimal("1234")),
        ("€1.234,56", Decimal("1234.56")),
    ],
)
def test_parse_money_accepts_every_declared_convention(raw: str, expected: Decimal) -> None:
    assert parse_money(raw) == expected


@pytest.mark.parametrize("raw", ["", "n/a", "N/A", "—", "1,2345"])
def test_parse_money_refuses_ambiguous_or_empty_input(raw: str) -> None:
    with pytest.raises(UnparseableFigureError):
        parse_money(raw)


def test_parse_money_never_returns_or_routes_through_a_float() -> None:
    result = parse_money("$3,964,760.00")
    assert isinstance(result, Decimal)
    assert not isinstance(result, float)


def test_parse_money_none_raises() -> None:
    with pytest.raises(UnparseableFigureError):
        parse_money(None)  # type: ignore[arg-type]

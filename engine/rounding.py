"""The single pinned money-quantisation call site.

Python's ``decimal`` module default context rounding is ``ROUND_HALF_EVEN``,
not ``ROUND_HALF_UP``. Nowhere else in this codebase should a ``.quantize()``
call appear — every module that needs to turn a computed money value into a
reportable whole-dollar (or whole-cent) figure imports ``quantize_money``
from here, so a future change to the rounding convention is a one-line diff
in this file, never a grep-and-fix across the tree.

Connecticut's ``Christmas Always`` fixture computes to exactly
``$1,159,501.50`` before rounding (``$3,865,005 x 30%``); the disclosed,
asserted figure is ``$1,159,502``. ``ROUND_HALF_UP`` and ``ROUND_HALF_EVEN``
both happen to agree on this specific value, which is precisely why the mode
must be an explicit, tested constant rather than an implicit default — a
future exact-mode fixture landing on an odd-dollar ``.50`` boundary would
otherwise silently expose whichever mode the ambient context happens to be
in.
"""

from decimal import Decimal, ROUND_HALF_UP

__all__ = ["ROUND_HALF_UP", "CENT", "DOLLAR", "quantize_money"]

CENT = Decimal("0.01")
DOLLAR = Decimal("1")


def quantize_money(value: Decimal, *, to: Decimal = DOLLAR) -> Decimal:
    """The single call site for rounding a computed money value.

    ROUND_HALF_UP is the pinned mode — Python's Decimal default context is
    ROUND_HALF_EVEN, which happens to agree with ROUND_HALF_UP on the one
    currently-committed fixture that lands on a .50 boundary (CT's
    Christmas Always: $1,159,501.50 -> $1,159,502) but is not guaranteed to
    for a future fixture. Pin explicitly; do not rely on the ambient default.
    """
    return value.quantize(to, rounding=ROUND_HALF_UP)

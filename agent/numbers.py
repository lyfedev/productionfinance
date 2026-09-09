"""D-88's locale-aware number guardrail — applied to every money string the
model copies verbatim out of a government disclosure document, before it
ever becomes a `Decimal` fed into the engine.

`parse_money` never constructs a `float` at any point on its path: the
cleaned string goes straight into `Decimal(...)`. When the separator
convention genuinely cannot be resolved, it RAISES `UnparseableFigureError`
rather than guessing — refusing beats guessing (T-05-08): a wrong number
that looks confident is worse than a run that honestly reports it could not
read a figure. This mirrors the repo's existing refusal convention
(`engine.net_cash.transferable` refusing to convert at an unsourced discount
rate rather than inventing one).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

__all__ = ["UnparseableFigureError", "parse_money"]


class UnparseableFigureError(ValueError):
    """Raised by `parse_money` when a figure is empty, non-numeric, or its
    grouping/decimal separator convention cannot be resolved without
    guessing."""


# Closed set of leading currency symbols this project's six currencies
# (USD, GBP, CAD, EUR, CZK, HUF) can present with. Stripped only from the
# FRONT of the cleaned string — a currency symbol never appears mid-number.
_CURRENCY_SYMBOLS: tuple[str, ...] = ("$", "£", "€", "¥", "Kč", "Ft")

# Footnote markers a government disclosure table commonly attaches to a
# figure — an asterisk/dagger/double-dagger note reference, or a superscript
# digit. Stripped from either end, never from the middle of a number.
_FOOTNOTE_CHARS = "*†‡⁰¹²³⁴⁵⁶⁷⁸⁹"

_ALLOWED_CHARS_RE = re.compile(r"[0-9,.]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _valid_grouping(groups: list[str]) -> bool:
    """True iff `groups` (the pieces `s.split(sep)` produced) is a valid
    thousands-grouping split: a non-empty 1-3 digit leading group, and every
    subsequent group exactly 3 digits. Requires at least one separator
    (len(groups) >= 2) — a bare, ungrouped number is handled by its own
    branch in `parse_money`, never routed through this check."""
    if len(groups) < 2:
        return False
    first = groups[0]
    if not first.isdigit() or not (1 <= len(first) <= 3):
        return False
    return all(g.isdigit() and len(g) == 3 for g in groups[1:])


def parse_money(raw: str) -> Decimal:
    """Parse a document-verbatim money string into a `Decimal`.

    Handles a leading currency symbol, accounting-parenthesis negatives, a
    Unicode minus sign, leading/trailing footnote markers, and both grouping
    separator/decimal separator conventions (US: `1,234.56`; European:
    `1.234,56`) — detected from the position of the LAST separator when both
    appear, never from a locale setting. Grouping via narrow/non-breaking or
    plain space (`1 234 567`) is also accepted.

    Raises `UnparseableFigureError` for an empty/placeholder string
    (`""`, `"n/a"`, `"—"`) or a genuinely ambiguous separator pattern (e.g.
    `"1,2345"` — a four-digit group is not a valid three-digit grouping and
    not a plausible decimal fraction either).
    """
    if raw is None:
        raise UnparseableFigureError(f"cannot parse a None figure: {raw!r}")

    original = raw
    s = raw.strip()
    if not s:
        raise UnparseableFigureError(f"cannot parse an empty figure: {original!r}")

    # Normalise narrow/non-breaking space to a plain space (both are treated
    # purely as grouping separators, stripped below), and a Unicode minus
    # sign (U+2212) to ASCII.
    s = s.replace(" ", " ").replace(" ", " ").replace("−", "-")

    # Strip leading/trailing footnote markers.
    s = s.strip()
    while s and s[0] in _FOOTNOTE_CHARS:
        s = s[1:]
    while s and s[-1] in _FOOTNOTE_CHARS:
        s = s[:-1]
    s = s.strip()
    if not s:
        raise UnparseableFigureError(f"cannot parse an empty figure: {original!r}")

    # Accounting-parenthesis negative: "(1,234)" -> negative, "1,234".
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    if not s:
        raise UnparseableFigureError(f"cannot parse an empty figure: {original!r}")

    # An explicit leading minus (already ASCII-normalised above).
    if s.startswith("-"):
        negative = True
        s = s[1:].strip()
    if not s:
        raise UnparseableFigureError(f"cannot parse an empty figure: {original!r}")

    # Strip a leading currency symbol from the closed set.
    for symbol in _CURRENCY_SYMBOLS:
        if s.startswith(symbol):
            s = s[len(symbol) :].strip()
            break
    if not s:
        raise UnparseableFigureError(f"cannot parse an empty figure: {original!r}")

    # Every remaining internal space is a grouping separator (narrow NBSP
    # and NBSP were already normalised to plain space above).
    s = _WHITESPACE_RE.sub("", s)
    if not s:
        raise UnparseableFigureError(f"cannot parse an empty figure: {original!r}")

    # Anything left that is not a digit, comma, or period is unparseable —
    # this is what catches "n/a", "—", and any other non-numeric placeholder
    # that survives every strip above.
    if not _ALLOWED_CHARS_RE.fullmatch(s):
        raise UnparseableFigureError(f"unrecognised figure: {original!r}")

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")
        if last_dot > last_comma:
            decimal_sep, grouping_sep = ".", ","
        else:
            decimal_sep, grouping_sep = ",", "."

        integer_part, _, frac_part = s.rpartition(decimal_sep)
        groups = integer_part.split(grouping_sep)
        if not _valid_grouping(groups) or not frac_part.isdigit():
            raise UnparseableFigureError(
                f"ambiguous grouping/decimal separators in figure: {original!r}"
            )
        cleaned = f"{integer_part.replace(grouping_sep, '')}.{frac_part}"

    elif has_dot or has_comma:
        sep = "." if has_dot else ","
        groups = s.split(sep)
        if _valid_grouping(groups):
            cleaned = "".join(groups)
        elif (
            len(groups) == 2
            and groups[0].isdigit()
            and groups[1].isdigit()
            and len(groups[1]) in (1, 2)
        ):
            cleaned = f"{groups[0]}.{groups[1]}"
        else:
            raise UnparseableFigureError(
                f"ambiguous separator in figure (not a valid grouping or a plausible "
                f"decimal fraction): {original!r}"
            )
    else:
        cleaned = s

    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise UnparseableFigureError(f"could not convert {original!r} to Decimal") from exc

    return -value if negative else value

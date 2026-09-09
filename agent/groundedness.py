"""AGT-08's groundedness guardrail (D-97 restores it) — the check that stops
a quote or a money figure the model may have paraphrased, guessed, or
fabricated from ever reaching a priced result.

`check_grounded` is a pure function over strings already in memory: it takes
the award's verbatim `source_row_text` and the extracted document's own
text, and answers one question — does the passage the model claims a row
came from actually appear in the document, and does the money it reports
appear inside that exact passage? It performs no I/O and calls no SDK; it
is deliberately as dumb and checkable as a substring test, because the
failure mode it exists to catch — a model-authored figure attributed to a
document that never said it — is exactly the kind of subtle drift a
cleverer, model-assisted check could itself get wrong or be talked out of.

Normalization is a DELIBERATE loosening of an exact match, not a shortcut:
an extractor reading a markdown table cell returns the cell's rendered
text — case-folded, whitespace-collapsed, with the pipe/dash punctuation the
table's own row framing wraps around a value — not the document's
byte-exact row. Rejecting on that framing alone would reject genuine,
correctly-read rows for a reason that has nothing to do with whether the
model made anything up. The loosening therefore covers EXACTLY: case
(via casefold), non-breaking and narrow non-breaking space normalized to a
plain space, runs of whitespace collapsed to one space, and pipe/dash
table-framing characters stripped from either end of the whole quote only
— never from its interior, and never in a way that lets a fabricated
number pass: a money figure absent from the passage is still ungrounded no
matter how the passage around it is spelled.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["GroundednessVerdict", "check_grounded"]

# Non-breaking space (U+00A0) and narrow non-breaking space (U+202F) — the
# same two characters `agent.numbers.parse_money` already normalizes,
# treated here purely as grouping/formatting whitespace, never as content.
_NBSP_CHARS = "  "
_WHITESPACE_RE = re.compile(r"\s+")

# Stripped from the ENDS of a quote only (never its interior): a plain
# space, the markdown table cell delimiter, and the two dash characters a
# table commonly uses both for its header-separator row and for an empty
# cell placeholder ("—" em dash, "–" en dash) — plus the ASCII hyphen.
_EDGE_STRIP_CHARS = " |-—–"

_QUOTE_PREFIX_LEN = 80


def _normalize(text: str) -> str:
    """Case-fold, normalize NBSP/narrow-NBSP to a plain space, collapse
    whitespace runs to one space, and strip table-framing punctuation from
    both ends only."""
    folded = text.casefold()
    for ch in _NBSP_CHARS:
        folded = folded.replace(ch, " ")
    collapsed = _WHITESPACE_RE.sub(" ", folded).strip()
    return collapsed.strip(_EDGE_STRIP_CHARS).strip()


@dataclass(frozen=True)
class GroundednessVerdict:
    """The result of checking one extracted quote against its claimed
    source document. `quote_prefix` is always populated — even when
    `grounded` is True — so a caller building an `ExtractionFailure` from
    an ungrounded verdict never needs to re-derive it."""

    grounded: bool
    reason: str
    quote_prefix: str


def check_grounded(
    quote: str,
    document_text: str,
    figures: tuple[str, ...] = (),
) -> GroundednessVerdict:
    """Check that `quote` appears (after normalization) inside
    `document_text`, and that every string in `figures` appears (after the
    SAME normalization) inside `quote` itself — a passage that exists but
    does not contain the number attributed to it is exactly the failure
    mode this guardrail exists to catch.

    Returns a `GroundednessVerdict` naming, in `reason`, what specifically
    was not found. Never raises — an ungrounded quote is an ordinary,
    expected outcome of this function, not an exceptional one.
    """
    prefix = quote.strip()[:_QUOTE_PREFIX_LEN] if quote else ""

    if not quote or not quote.strip():
        return GroundednessVerdict(
            grounded=False,
            reason="quote is empty or whitespace-only",
            quote_prefix=prefix,
        )

    normalized_quote = _normalize(quote)
    normalized_document = _normalize(document_text)

    if not normalized_quote or normalized_quote not in normalized_document:
        return GroundednessVerdict(
            grounded=False,
            reason="quote does not appear in the extracted document text",
            quote_prefix=prefix,
        )

    for figure in figures:
        if not figure:
            continue
        normalized_figure = _normalize(figure)
        if not normalized_figure or normalized_figure not in normalized_quote:
            return GroundednessVerdict(
                grounded=False,
                reason=f"figure {figure!r} does not appear inside the quoted passage",
                quote_prefix=prefix,
            )

    return GroundednessVerdict(
        grounded=True,
        reason="quote and every reported figure are present in the document",
        quote_prefix=prefix,
    )

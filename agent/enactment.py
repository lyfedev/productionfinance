"""AGT-08's enactment guardrail (D-97 restores it) — classifies whether a
Job 1 source document is enacted law, a still-moving proposed bill, or
neither can be determined, so a rate read out of a bill that never passed
is never presented as law (T-05-31).

`classify_enactment` is a pure function over strings already in memory: a
document URL and its extracted text. It performs no I/O and calls no SDK.
Both signal sets below are declared HERE, in this new module, never in
`agent/settings.py` — another workstream owns that file concurrently.

The classifier never picks a side on absence of evidence: no matched
marker of either kind means `unknown`, the same refuse-don't-guess
convention `agent.numbers.parse_money` and `engine.net_cash.transferable`
already follow for a figure or a discount rate that cannot be resolved
without guessing.

Neither signal set keys on the HOST alone. A state legislature's own host
(e.g. nysenate.gov) serves both a still-pending bill page and a chaptered,
signed statute's own codified text — a host-only rule would therefore
mislabel one of those two document types every single time. The signals
instead key on (a) language a chaptered, signed statute characteristically
carries ("Chapter N of the Laws of YYYY", "signed into law", "approved by
the Governor") versus language a bill carries while it is still moving
("referred to the committee", "introduced by", "as amended"), and (b) a
codified-statute-shaped URL path (e.g. `/laws/...`) versus a
bill-numbered-shaped URL path (e.g. `/bills/...`).

PRECEDENCE RULE, stated and defended here because it is the one place a
downstream reader will look for it: when a document carries BOTH an
enactment marker and a pending-legislation marker, the enactment signal
wins, and the verdict records BOTH matched marker sets rather than
discarding the pending one. This is deliberate, not a bug: an enacted
statute's own text routinely recites its own legislative history (a
chaptered law's text commonly says things like "as amended" or references
its own bill number in passing) — that recitation does not demote a
signed, chaptered statute back to "merely proposed". Recording both marker
sets on the verdict means a reader sees the conflict and can judge it,
rather than the classifier laundering it into a single silent answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

__all__ = ["EnactmentStatus", "EnactmentVerdict", "classify_enactment"]

_EXCERPT_MAX_LEN = 80
_EXCERPT_CONTEXT_CHARS = 15


class EnactmentStatus(str, Enum):
    """A closed, three-member set. There is no fourth member and no
    default — absence of evidence is `unknown`, a real, first-class
    outcome, never silently folded into `enacted` or `proposed`."""

    enacted = "enacted"
    proposed = "proposed"
    unknown = "unknown"


@dataclass(frozen=True)
class EnactmentVerdict:
    """`matched_markers` names every marker (from either signal set) that
    fired, in the order checked — enacted markers first when the
    precedence rule applies. `evidence` is the corresponding truncated
    excerpt for each entry in `matched_markers`, same length, same order."""

    status: EnactmentStatus
    matched_markers: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[str, ...] = field(default_factory=tuple)


def _pattern(text: str) -> re.Pattern[str]:
    return re.compile(text, re.IGNORECASE)


# Enactment signals: the language a chaptered, signed statute's own text
# characteristically carries.
_ENACTED_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("chapter_of_the_laws_of", _pattern(r"chapter\s+\d+[a-z]?\s+of\s+the\s+laws\s+of\s+\d{4}")),
    ("signed_into_law", _pattern(r"signed\s+into\s+law")),
    ("approved_by_the_governor", _pattern(r"approved\s+(?:and\s+signed\s+)?by\s+the\s+governor")),
    ("enacted", _pattern(r"\benacted\b")),
)

# A codified-statute-shaped URL path segment (e.g. nysenate.gov/legislation
# /laws/TAX/24, or a state's own official code site).
_ENACTED_URL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("codified_statute_url_path", _pattern(r"/laws?/")),
)

# Pending-legislation signals: the language a bill carries while it is
# still moving through a chamber.
_PENDING_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("referred_to_committee", _pattern(r"referred\s+to\s+(?:the\s+)?committee")),
    ("introduced", _pattern(r"\bintroduced\b")),
    ("amended", _pattern(r"\bamended\b")),
    ("passed_one_chamber", _pattern(r"passed\s+the\s+(?:senate|assembly|house)\b")),
)

# A bill-numbered-shaped URL path segment (e.g. nysenate.gov/legislation
# /bills/2023/S1234).
_PENDING_URL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bill_number_url_path", _pattern(r"/bills?/")),
)


def _search_patterns(
    patterns: tuple[tuple[str, re.Pattern[str]], ...], source: str
) -> list[tuple[str, str]]:
    """Search `source` (either the document text or the URL) against each
    named pattern. Returns `(name, excerpt)` pairs for every pattern that
    matched, in declaration order — never every match of a pattern, just
    whether it fired at least once."""
    matches: list[tuple[str, str]] = []
    for name, pattern in patterns:
        found = pattern.search(source)
        if found is None:
            continue
        start = max(0, found.start() - _EXCERPT_CONTEXT_CHARS)
        end = min(len(source), found.end() + _EXCERPT_CONTEXT_CHARS)
        excerpt = source[start:end].strip()[:_EXCERPT_MAX_LEN]
        matches.append((name, excerpt))
    return matches


def classify_enactment(url: str, text: str) -> EnactmentVerdict:
    """Classify a Job 1 source document as `enacted`, `proposed`, or
    `unknown`. Never raises; absence of both signal kinds is a real
    `unknown` verdict, not an exception."""
    enacted_matches = _search_patterns(_ENACTED_TEXT_PATTERNS, text) + _search_patterns(
        _ENACTED_URL_PATTERNS, url
    )
    pending_matches = _search_patterns(_PENDING_TEXT_PATTERNS, text) + _search_patterns(
        _PENDING_URL_PATTERNS, url
    )

    if enacted_matches:
        # Precedence rule (see module docstring): enacted wins over
        # pending, and BOTH marker sets are recorded — never laundered
        # into a single silent answer.
        status = EnactmentStatus.enacted
        combined = enacted_matches + pending_matches
    elif pending_matches:
        status = EnactmentStatus.proposed
        combined = pending_matches
    else:
        status = EnactmentStatus.unknown
        combined = []

    return EnactmentVerdict(
        status=status,
        matched_markers=tuple(name for name, _ in combined),
        evidence=tuple(excerpt for _, excerpt in combined),
    )

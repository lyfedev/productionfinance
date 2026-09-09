"""Parallel Search + Extract — the first two stages of the D-82 pipeline.

`parallel` is imported INSIDE each function, never at module top level
(lazy import): it keeps the FastAPI process footprint on the 472 MB host
unchanged until a run is actually triggered, and it is what lets the app
degrade legibly when the package or key is absent (importing this module
alone never touches the SDK).

T-05-01 (Spoofing): a Search result is accepted only when its parsed
hostname suffix-matches `agent.settings.PRIMARY_GOVERNMENT_SUFFIXES`. The
comparison is against `urlparse(url).hostname`, never a substring of the
whole URL — a substring test would accept
`https://attacker.example/?q=esd.ny.gov`.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from agent.settings import (
    EXTRACT_TIMEOUT_SECONDS,
    PRIMARY_GOVERNMENT_SUFFIXES,
    SEARCH_TIMEOUT_SECONDS,
    parallel_api_key,
)
from agent.telemetry import sdk_call

__all__ = [
    "DisclosureDocument",
    "extract_document",
    "is_primary_government_url",
    "search_for_disclosure",
    "search_for_disclosure_candidates",
]

# The one document this tracer targets: the NY ESD quarterly Film Tax
# Credit report and its per-production credits-issued chart, already
# curated in Phase 3 (see tests/fixtures/validation_pairs/ny_anora.yaml).
# Not every ESD quarterly report carries per-production data. Some are
# aggregate-only — the Q3 2023 report, for instance, states "18 initial
# applications ... totaling over $76.3 million" with monthly rollups and no
# named productions, and a live run against it correctly extracted zero
# awards. The objective therefore asks specifically for a report containing
# a chart of NAMED productions, which the 2024 and 2025 reports do carry.
_SEARCH_OBJECTIVE = (
    "Locate a New York Empire State Development (ESD) quarterly Film "
    "Production Tax Credit Program report containing a table of INDIVIDUALLY "
    "NAMED productions, each row giving that production's title, its "
    "qualified spend and the tax credit issued to it. Prefer a report whose "
    "credits-issued or productions-certified chart lists specific film and "
    "series titles; reject a report that gives only aggregate totals or "
    "monthly application counts without naming productions."
)
_SEARCH_QUERIES = (
    "ESD film tax credit report pdf",
    "New York film credit productions certified",
)


# Suffixes that indicate a retrievable document rather than a landing page.
_DOCUMENT_SUFFIXES = (".pdf", ".xlsx", ".xls", ".csv")

# Bound on returned characters. An ESD quarterly report measures 7k-24k;
# this leaves headroom for a longer disclosure without being unbounded.
EXTRACT_MAX_CHARS = 200_000


def is_primary_government_url(url: str) -> bool:
    """True iff `url`'s parsed hostname suffix-matches a declared
    primary-government-domain suffix (D-88). Compares the parsed host,
    never a substring of the whole URL (T-05-01).
    """
    hostname = urlparse(url).hostname
    if not hostname:
        return False
    hostname = hostname.lower()
    return any(
        hostname == suffix.lstrip(".") or hostname.endswith(suffix)
        for suffix in PRIMARY_GOVERNMENT_SUFFIXES
    )


def search_for_disclosure_candidates() -> tuple[str, ...]:
    """Search for NY ESD disclosure documents and return every
    primary-government-domain result, documents first, in rank order.

    Returns a tuple rather than one URL because rank order does not predict
    which report carries per-production data: not every ESD quarterly report
    does. The Q3 2023 report gives only aggregate totals and monthly
    application counts, and a live run against it correctly extracted zero
    awards — honest, but not useful. The caller tries candidates in order and
    keeps the first that actually yields awards, which is a real test rather
    than a guess about document shape. Empty tuple if nothing passes the D-88
    filter (D-87: no fallback to a hardcoded URL).
    """
    import parallel  # lazy import (see module docstring)

    key = parallel_api_key()
    client = parallel.Parallel(api_key=key)

    with sdk_call("parallel-web", "search", "ny-esd-quarterly-film-report"):
        result = client.search(
            objective=_SEARCH_OBJECTIVE,
            search_queries=list(_SEARCH_QUERIES),
            timeout=SEARCH_TIMEOUT_SECONDS,
        )

    # Prefer an actual document over a landing page. A live run against the
    # ESD index page returned 1,492 characters of navigation and Gemini
    # correctly extracted zero awards from it — the honest outcome, but not
    # a useful one. Search does surface the report PDFs themselves; they
    # just never won a first-match scan. Government-domain preference (D-88)
    # still gates the candidate set; this only orders what survives it.
    primary = [w.url for w in result.results if is_primary_government_url(w.url)]
    documents = [u for u in primary if u.lower().split("?")[0].endswith(_DOCUMENT_SUFFIXES)]
    return tuple(documents + [u for u in primary if u not in documents])


@dataclass(frozen=True)
class DisclosureDocument:
    url: str
    markdown: str
    sha256: str
    char_count: int


def extract_document(url: str) -> DisclosureDocument | None:
    """Extract clean text/markdown from `url` via Parallel Extract. Returns
    None if Extract returns no usable content for the URL (D-87).
    """
    import parallel  # lazy import (see module docstring)

    key = parallel_api_key()
    client = parallel.Parallel(api_key=key)

    with sdk_call("parallel-web", "extract", url):
        # `full_content` must be enabled explicitly. Without it Extract
        # returns only objective-focused excerpts — measured at ~1.2k
        # characters for an ESD quarterly PDF, which is the report's
        # preamble and none of the per-production award table, so Gemini
        # correctly extracted zero awards from it. With it enabled the
        # same documents return 7k-24k characters including the chart.
        response = client.extract(
            urls=[url],
            objective=_SEARCH_OBJECTIVE,
            advanced_settings={"full_content": {"enabled": True}},
            max_chars_total=EXTRACT_MAX_CHARS,
            timeout=EXTRACT_TIMEOUT_SECONDS,
        )

    if not response.results:
        return None
    result = response.results[0]
    content = result.full_content or "\n".join(result.excerpts)
    if not content:
        return None

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return DisclosureDocument(
        url=result.url or url,
        markdown=content,
        sha256=digest,
        char_count=len(content),
    )


def search_for_disclosure() -> str | None:
    """The single-URL form of `search_for_disclosure_candidates`.

    Retained for callers and tests that want one result; returns the
    highest-ranked candidate, or None if none passed the D-88 filter.
    """
    candidates = search_for_disclosure_candidates()
    return candidates[0] if candidates else None

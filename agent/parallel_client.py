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
]

# The one document this tracer targets: the NY ESD quarterly Film Tax
# Credit report and its per-production credits-issued chart, already
# curated in Phase 3 (see tests/fixtures/validation_pairs/ny_anora.yaml).
_SEARCH_OBJECTIVE = (
    "Locate the most recent New York Empire State Development (ESD) "
    "quarterly Film Production Tax Credit Program report that lists "
    "per-production qualified spend and credits issued (the "
    "'credits-issued' or 'productions certified' chart)."
)
_SEARCH_QUERIES = (
    "ESD film tax credit quarterly report",
    "New York film production tax credit report",
)


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


def search_for_disclosure() -> str | None:
    """Search for the NY ESD disclosure document and return the
    highest-ranked primary-government-domain URL, or None if no result
    passes the D-88 filter (D-87: no fallback to a hardcoded URL).
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

    for web_result in result.results:
        if is_primary_government_url(web_result.url):
            return web_result.url
    return None


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
        response = client.extract(
            urls=[url],
            objective=_SEARCH_OBJECTIVE,
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

"""Agent configuration — read from the process environment only.

D-88's primary-government-domain guardrail lives here as a declared tuple of
host suffixes, and T-05-03 (Information disclosure) is enforced structurally
by this module: every function here returns booleans and variable NAMES
only. No function in this module may return, log, format or repr a key
value — `integration_status()` and `IntegrationStatus.not_configured_message()`
are the only sanctioned way to describe key state, and both are key-value-free
by construction.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = [
    "EXTRACT_TIMEOUT_SECONDS",
    "GEMINI_API_KEY_VAR",
    "GEMINI_MODEL",
    "GEMINI_MODEL_VAR",
    "GEMINI_TIMEOUT_SECONDS",
    "GOOGLE_API_KEY_VAR",
    "JOB2_MAX_CHARS_PER_SEARCH",
    "JOB2_WALL_CLOCK_CEILING_SECONDS",
    "MAX_DOCUMENT_CHARS",
    "PARALLEL_API_KEY_VAR",
    "PRIMARY_GOVERNMENT_SUFFIXES",
    "SEARCH_TIMEOUT_SECONDS",
    "IntegrationStatus",
    "gemini_api_key",
    "integration_status",
    "parallel_api_key",
]

PARALLEL_API_KEY_VAR = "PARALLEL_API_KEY"
GEMINI_API_KEY_VAR = "GEMINI_API_KEY"
GOOGLE_API_KEY_VAR = "GOOGLE_API_KEY"
GEMINI_MODEL_VAR = "PRODFIN_GEMINI_MODEL"

# D-88: accept a Search result only when its parsed hostname suffix-matches
# one of these. Comparison is against `urllib.parse.urlparse(url).hostname`
# in agent.parallel_client, never a substring of the whole URL (T-05-01).
PRIMARY_GOVERNMENT_SUFFIXES: tuple[str, ...] = (".gov", ".ny.gov", ".state.ny.us", ".ny.us")

# Per-stage timeouts (seconds) and the document-size bound (T-05-04).
SEARCH_TIMEOUT_SECONDS = 30.0
EXTRACT_TIMEOUT_SECONDS = 60.0
GEMINI_TIMEOUT_SECONDS = 60.0
MAX_DOCUMENT_CHARS = 400_000

# Job 2 (agent/job2.py): a wall-clock BACKSTOP only, checked between rounds
# (never mid-SDK-call) and never by comparing a round counter to an integer
# (D-90) — `agent/job2.py::run_job2` reads this name live at call time, and
# `tests/test_agent_job2_loop.py` is the AST gate that keeps it a backstop
# rather than a round counter. Never add a maximum round count alongside
# this.
JOB2_WALL_CLOCK_CEILING_SECONDS = 240.0
# Bounds what one round's Search call returns (T-07-01/T-07-02), the same
# reasoning as MAX_DOCUMENT_CHARS above but for the live research path.
JOB2_MAX_CHARS_PER_SEARCH = 60_000


def _default_gemini_model() -> str:
    return os.environ.get(GEMINI_MODEL_VAR) or "gemini-3.6-flash"


GEMINI_MODEL: str = _default_gemini_model()


def parallel_api_key() -> str | None:
    """The Parallel key, or None if unset. Never logged, never repr'd."""
    return os.environ.get(PARALLEL_API_KEY_VAR) or None


def gemini_api_key() -> str | None:
    """The Gemini key: GEMINI_API_KEY, falling back to GOOGLE_API_KEY.

    Never logged, never repr'd.
    """
    return os.environ.get(GEMINI_API_KEY_VAR) or os.environ.get(GOOGLE_API_KEY_VAR) or None


@dataclass(frozen=True)
class IntegrationStatus:
    """Booleans and variable NAMES only (T-05-03) — never a key value."""

    parallel_configured: bool
    gemini_configured: bool
    missing: tuple[str, ...]

    def not_configured_message(self) -> str:
        """Legible prose naming the missing variables and where they go.

        Contains no value from the environment — only variable names.
        """
        if not self.missing:
            return "Both integrations are configured."
        names = ", ".join(self.missing)
        return (
            f"Not configured: {names}. Export these in the executor's shell for "
            "local verification, or add them to /opt/prodfin/.env on the Lightsail "
            "box for production (deploy/prodfin.service already loads that file via "
            "EnvironmentFile=-/opt/prodfin/.env). See deploy/README.md for the full "
            "credential runbook."
        )


def integration_status() -> IntegrationStatus:
    """Build an `IntegrationStatus` from the current process environment."""
    parallel_configured = parallel_api_key() is not None
    gemini_configured = gemini_api_key() is not None

    missing: list[str] = []
    if not parallel_configured:
        missing.append(PARALLEL_API_KEY_VAR)
    if not gemini_configured:
        missing.append(f"{GEMINI_API_KEY_VAR} (or {GOOGLE_API_KEY_VAR})")

    return IntegrationStatus(
        parallel_configured=parallel_configured,
        gemini_configured=gemini_configured,
        missing=tuple(missing),
    )

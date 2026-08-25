"""The custom-handler escape hatch — a closed, explicit allow-list.

``HANDLER_REGISTRY`` is a plain ``dict`` literal mapping known identifier
strings to specific function objects. No attribute-based function lookup and
no dynamic module-import machinery may appear anywhere in this package: a
rule-file string must never be able to name code that is not already
present in this literal.

This constraint is forward-looking (T-02-03, V4 in ``02-RESEARCH.md``
Security Domain): Phase 2's own rule files are human-written and
git-reviewed, but Phase 7's Job 2 feeds LLM-extracted YAML through this
exact same schema, and an unconstrained dynamic-resolution pattern
established now becomes a code-execution vector once that YAML's provenance
is no longer "human-reviewed, git-committed."

Empty at this point — no ``custom_handler_id`` is registered yet. Plans that
add a genuinely irregular jurisdiction (e.g. Canada's federal/provincial
residency-pool mismatch) add a named function here and register it in this
same literal, never by dynamic resolution.
"""

from __future__ import annotations

from typing import Callable

__all__ = ["HANDLER_REGISTRY", "resolve_handler"]

HANDLER_REGISTRY: dict[str, Callable[..., object]] = {}


def resolve_handler(handler_id: str) -> Callable[..., object]:
    """Look up ``handler_id`` in the closed registry.

    Raises ``KeyError`` naming the unknown identifier — never falls through
    to dynamic attribute lookup or module import.
    """
    try:
        return HANDLER_REGISTRY[handler_id]
    except KeyError as exc:
        raise KeyError(f"Unknown custom_handler_id: {handler_id!r}") from exc

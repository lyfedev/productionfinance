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

Plan 02-03 adds the registry's first real entry
(``labour_plus_quarter_local_hires``), exercising the escape hatch rather
than merely declaring it. Plans that add a genuinely irregular jurisdiction
(e.g. Canada's federal/provincial residency-pool mismatch) add a named
function here and register it in this same literal, never by dynamic
resolution.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    # Import only for static type-checking. engine.qualifying_base imports
    # this module (to resolve custom_handler_id strings), so a runtime
    # import of SpendBreakdown here would be a circular import; the
    # `from __future__ import annotations` at the top of both modules keeps
    # every annotation a lazily-evaluated string, so this guard is enough.
    from engine.models import Programme
    from engine.qualifying_base import SpendBreakdown

__all__ = ["HANDLER_REGISTRY", "labour_plus_quarter_local_hires", "resolve_handler"]


def labour_plus_quarter_local_hires(
    programme: "Programme", spend: "SpendBreakdown"
) -> Decimal:
    """The registry's first real entry — a qualifying-base formula none of
    the four declarative ``base_definition.type`` values can express:
    labour spend plus one quarter of local-hires spend. Illustrative only,
    referenced by ``tests/fixtures/jurisdictions/synthetic-basedefs.yaml``'s
    ``custom`` programme, proving the escape hatch is genuinely exercised
    rather than merely declared.
    """
    del programme  # unused by this particular formula; kept for signature parity
    return spend.labour_spend + (spend.local_hires_spend * Decimal("0.25"))


HANDLER_REGISTRY: dict[str, Callable[..., object]] = {
    "labour_plus_quarter_local_hires": labour_plus_quarter_local_hires,
}


def resolve_handler(handler_id: str) -> Callable[..., object]:
    """Look up ``handler_id`` in the closed registry.

    Raises ``KeyError`` naming the unknown identifier — never falls through
    to dynamic attribute lookup or module import.
    """
    try:
        return HANDLER_REGISTRY[handler_id]
    except KeyError as exc:
        raise KeyError(f"Unknown custom_handler_id: {handler_id!r}") from exc

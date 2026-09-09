"""Pydantic v2 models for Job 2's reasoning calls — the single schema
source for the sufficiency judgment, the same way `agent/schema.py` is
Job 1's (D-83 pattern).

`research_response_schema()` calls `SufficiencyVerdict.model_json_schema()`
directly and passes it as `response_json_schema` to `google-genai` — one
schema definition serves both the extraction contract and the API
contract. No second, hand-written JSON schema exists anywhere in this
module or `agent.job2`.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "FieldFinding",
    "SufficiencyField",
    "SufficiencyVerdict",
    "research_response_schema",
]


class SufficiencyField(str, Enum):
    """D-91's five named fields — the closed sufficiency contract a cost
    model is judged against. A sixth member is a Pydantic validation error
    at parse time, not a silently accepted string."""

    rate = "rate"
    qualifying_base_definition = "qualifying_base_definition"
    caps = "caps"
    payout_mechanism = "payout_mechanism"
    current_availability = "current_availability"


class FieldFinding(BaseModel):
    """One D-91 field as this round's evidence settled it.

    Money-shaped values stay a `str` here, never a `float` — the same
    `agent/schema.py` precedent (T-05-05): the engine is `Decimal` end to
    end, and a float hop would silently corrupt an exact-reproduction
    claim.
    """

    model_config = ConfigDict(extra="forbid")

    field: SufficiencyField
    determined: bool
    value_text: str | None = None
    evidence_quote: str | None = None
    source_url: str | None = None


class SufficiencyVerdict(BaseModel):
    """The model's own judgment of whether this round's evidence is enough
    to build a cost model, and — when it is not — what to search next.

    `decision` is the ONLY thing that ends `agent/job2.py`'s loop (D-90):
    `\"sufficient\"`, `\"give_up\"` and `\"no_programme_found\"` are each
    terminal; `\"continue\"` carries the refined objective/queries/mode for
    the next round.
    """

    model_config = ConfigDict(extra="forbid")

    decision: Literal["continue", "sufficient", "give_up", "no_programme_found"]
    findings: list[FieldFinding] = Field(default_factory=list)
    summary: str
    next_objective: str | None = None
    next_queries: list[str] = Field(default_factory=list)
    next_mode: Literal["turbo", "fast", "basic", "advanced"] = "fast"


def research_response_schema() -> dict:
    """The JSON schema handed to `google-genai` as `response_json_schema`.
    Never hand-write a second JSON schema for this extraction (D-83's rule,
    applied to Job 2)."""
    return SufficiencyVerdict.model_json_schema()

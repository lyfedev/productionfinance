"""Pydantic v2 models for the Job 1 extraction — the ONLY schema definition
in the codebase for this extraction (D-83).

`gemini_response_schema()` calls `ExtractedAwardSet.model_json_schema()`
directly and passes it as `response_json_schema` to `google-genai` — one
schema definition serves both the extraction contract and (were this ever
exposed over HTTP) the API contract. No second, hand-written JSON schema
exists anywhere in this module or `agent.gemini_client`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ExtractedAward", "ExtractedAwardSet", "gemini_response_schema"]


class ExtractedAward(BaseModel):
    """One production/award row as Gemini read it, verbatim.

    Money fields are `str`, never `float`: the engine is `Decimal` end to
    end, and a float hop would silently corrupt an exact-reproduction claim
    (T-05-05). `source_row_text` is the verbatim document line the model
    read the row from — this is what makes an extracted figure checkable
    against the document.
    """

    model_config = ConfigDict(extra="forbid")

    production_title: str
    qualified_spend: str
    credit_amount: str
    diversity_credit_amount: str | None = None
    programme_hint: str | None = None
    source_row_text: str


class ExtractedAwardSet(BaseModel):
    """The full structured response for one extracted document."""

    model_config = ConfigDict(extra="forbid")

    report_title: str | None = None
    report_period: str | None = None
    awards: list[ExtractedAward] = Field(default_factory=list)


def gemini_response_schema() -> dict:
    """The JSON schema handed to `google-genai` as `response_json_schema`
    (D-83). Never hand-write a second JSON schema for this extraction.
    """
    return ExtractedAwardSet.model_json_schema()

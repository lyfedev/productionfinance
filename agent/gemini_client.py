"""google-genai structured extraction — the third stage of the D-82
pipeline.

`from google import genai` is imported INSIDE `extract_awards`, never at
module top level (lazy import, same reason as `agent.parallel_client`).

T-05-02 (Tampering): the fetched document is untrusted third-party text
crossing into an LLM prompt. No tools and no function declarations are
configured — the model returns structured data and nothing else, so
prompt-injection in the document cannot reach an action, only a field
value, which the caller re-derives through the existing engine rather than
trusting outright.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.schema import ExtractedAwardSet, gemini_response_schema
from agent.settings import (
    GEMINI_MODEL,
    MAX_DOCUMENT_CHARS,
    gemini_api_key,
)
from agent.telemetry import sdk_call

__all__ = ["ExtractionResult", "extract_awards"]

_PROMPT = """You are reading a New York Empire State Development (ESD) film
tax credit quarterly report. Find the per-production credits-issued table
(qualified production costs and film production tax credit issued, per
production). For each row in that table, copy the figures VERBATIM — do not
compute, round, sum, or infer any number. If diversity/relocation credit
columns exist, include them; otherwise leave that field empty. Copy the
production title and the exact text of the row you read it from into
source_row_text. Do not include rows that are subtotals or totals. Return
only the structured JSON described by the response schema.

DOCUMENT:
{document}
"""


@dataclass(frozen=True)
class ExtractionResult:
    award_set: ExtractedAwardSet
    truncated: bool
    model: str


def extract_awards(document_markdown: str) -> ExtractionResult:
    """Call `google-genai` structured extraction over `document_markdown`
    and parse the response back through `ExtractedAwardSet` (D-83).
    """
    from google import genai
    from google.genai import types

    truncated = len(document_markdown) > MAX_DOCUMENT_CHARS
    sliced = document_markdown[:MAX_DOCUMENT_CHARS]

    client = genai.Client(api_key=gemini_api_key())
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=gemini_response_schema(),
    )

    with sdk_call("google-genai", "generate_content", GEMINI_MODEL, truncated=truncated):
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_PROMPT.format(document=sliced),
            config=config,
        )

    award_set = ExtractedAwardSet.model_validate_json(response.text)
    return ExtractionResult(award_set=award_set, truncated=truncated, model=GEMINI_MODEL)

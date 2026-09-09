"""UI-08/UI-12 — the permalink: the ONLY persistence mechanism (Phase 6,
plan 06-04). There is no login, no session, no server-side saved-
comparison table — every fact the diff (UI-12) or the reproduced
comparison (UI-08) needs travels inside the URL itself, opaque-encoded,
nothing else.

Two honesty disciplines this module enforces STRUCTURALLY, not just by
convention:

  1. (UI-08) `decode_permalink` requires EVERY `CompareInputs` field to be
     present in the decoded payload — it never constructs `CompareInputs`
     from a partial dict and lets that model's OWN field defaults
     silently fill a gap. `CompareInputs` has a default for every field
     (a bare `GET /compare` prices a real default comparison — UI-01's
     own contract), which is exactly what would let a truncated or
     hand-edited permalink token silently reproduce a DIFFERENT
     comparison under the same URL rather than failing loudly. A missing
     field raises `PermalinkDecodeError` naming which field is missing —
     "worse than failing to encode" (the plan's own words) is exactly
     what this refuses to do.
  2. (UI-12) `compute_diff` never reports a rate "unchanged" without a
     genuinely resolved current-vs-recorded match — a rate this module
     cannot locate (renamed or removed) or cannot disambiguate (more
     than one current rate shares its recorded label) reports "cannot
     determine what changed", never "unchanged". Silence is never used
     to mean "nothing changed" either — every recorded rate gets its own
     named verdict.

Encoding is deterministic (`json.dumps(..., sort_keys=True,
separators=(",", ":"))`, then URL-safe base64 with the padding trimmed)
so `encode_permalink(decode_permalink(token)) == token` holds for every
token this module itself produced — the round-trip property
`tests/test_app_permalink.py` asserts across many input combinations,
not one example.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.services.compare import CompareInputs
from engine.figure import Figure

__all__ = [
    "FieldDiff",
    "PermalinkDecodeError",
    "PermalinkDiffView",
    "PermalinkState",
    "RateDiff",
    "RecordedFigure",
    "build_diff_view",
    "compute_diff",
    "decode_permalink",
    "encode_permalink",
    "record_figures",
]


class PermalinkDecodeError(ValueError):
    """Raised by `decode_permalink` for any malformed, truncated, or
    field-dropping token — this class NEVER results in `CompareInputs`'
    own defaults being silently substituted for a missing input (see
    module docstring, honesty discipline 1)."""


@dataclass(frozen=True)
class RecordedFigure:
    """One leaf rate exactly as it stood at permalink-creation time —
    exactly the fields `compute_diff` needs to name what changed (UI-12):
    its value, unit, source, date-checked, basis and confidence. `label`
    is the key `compute_diff` looks a CURRENT figure up by — see that
    function's own docstring for what happens when zero or more than one
    current figure shares it."""

    label: str
    value: str
    unit: str
    source_url: str | None
    date_checked: str | None
    basis: str | None
    confidence: str


@dataclass(frozen=True)
class PermalinkState:
    """Everything one permalink token carries. `inputs` is enough to
    reproduce the exact comparison (UI-08); `created_at` plus
    `recorded_figures` is enough to diff it later (UI-12). No other state
    exists anywhere else — this literally IS the persistence mechanism."""

    inputs: CompareInputs
    created_at: str
    recorded_figures: tuple[RecordedFigure, ...]


def record_figures(figures: Sequence[Figure]) -> tuple[RecordedFigure, ...]:
    """Turn a sequence of LEAF `Figure`s — typically
    `app.services.provenance.collect_rate_figures`'s own output — into
    the `RecordedFigure` snapshot a permalink token carries. A thin field
    projection, never a re-derivation: every value here is copied
    straight off the `Figure` the engine already produced for THIS
    comparison, at THIS moment."""
    return tuple(
        RecordedFigure(
            label=figure.label,
            value=str(figure.value),
            unit=figure.unit,
            source_url=figure.source_url,
            date_checked=figure.date_checked.isoformat() if figure.date_checked else None,
            basis=figure.basis,
            confidence=figure.confidence,
        )
        for figure in figures
    )


# Every `CompareInputs` field name, read directly off the model — never a
# hand-maintained list that could silently drift out of sync with
# `app.services.compare.CompareInputs` and stop catching a genuinely
# dropped field (the exact failure mode this module exists to refuse).
_COMPARE_INPUTS_FIELDS: tuple[str, ...] = tuple(CompareInputs.model_fields.keys())


def encode_permalink(state: PermalinkState) -> str:
    """A deterministic, URL-safe token: the SAME `state` always produces
    the SAME token (`sort_keys=True`, no incidental whitespace), which is
    what makes `encode_permalink(decode_permalink(token)) == token` hold
    for every token this module produces."""
    payload = {
        "inputs": state.inputs.model_dump(mode="json"),
        "created_at": state.created_at,
        "recorded_figures": [
            {
                "label": f.label,
                "value": f.value,
                "unit": f.unit,
                "source_url": f.source_url,
                "date_checked": f.date_checked,
                "basis": f.basis,
                "confidence": f.confidence,
            }
            for f in state.recorded_figures
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_permalink(token: str) -> PermalinkState:
    """The inverse of `encode_permalink`. Raises `PermalinkDecodeError`
    — never silently substitutes a default — for: malformed base64/JSON,
    a payload missing `inputs`/`created_at`/`recorded_figures`, or an
    `inputs` payload missing even ONE of `CompareInputs`' own fields. A
    permalink that silently dropped an input would reproduce a DIFFERENT
    comparison under the same URL — this is the "worse than failing to
    encode" case UI-08's own must-haves name explicitly."""
    padded = token + "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw)
    except Exception as exc:
        raise PermalinkDecodeError(f"permalink token could not be decoded: {exc}") from exc

    if not isinstance(payload, dict):
        raise PermalinkDecodeError("permalink token did not decode to a JSON object")

    for key in ("inputs", "created_at", "recorded_figures"):
        if key not in payload:
            raise PermalinkDecodeError(f"permalink token is missing {key!r}")

    inputs_payload = payload["inputs"]
    if not isinstance(inputs_payload, dict):
        raise PermalinkDecodeError("permalink token's 'inputs' is not a JSON object")

    missing = sorted(name for name in _COMPARE_INPUTS_FIELDS if name not in inputs_payload)
    if missing:
        raise PermalinkDecodeError(
            f"permalink token is missing input field(s) {missing} — refusing to fall "
            "back to CompareInputs' own defaults for a partial token, which would "
            "silently reproduce a different comparison under the same URL"
        )

    try:
        inputs = CompareInputs(**inputs_payload)
    except Exception as exc:  # pydantic ValidationError, TypeError, etc.
        raise PermalinkDecodeError(f"permalink token carries invalid inputs: {exc}") from exc

    recorded_raw = payload["recorded_figures"]
    if not isinstance(recorded_raw, list):
        raise PermalinkDecodeError("permalink token's 'recorded_figures' is not a JSON list")

    recorded_figures: list[RecordedFigure] = []
    for index, entry in enumerate(recorded_raw):
        if not isinstance(entry, dict):
            raise PermalinkDecodeError(f"permalink token's recorded_figures[{index}] is not a JSON object")
        try:
            recorded_figures.append(
                RecordedFigure(
                    label=entry["label"],
                    value=entry["value"],
                    unit=entry["unit"],
                    source_url=entry["source_url"],
                    date_checked=entry["date_checked"],
                    basis=entry["basis"],
                    confidence=entry["confidence"],
                )
            )
        except KeyError as exc:
            raise PermalinkDecodeError(
                f"permalink token's recorded_figures[{index}] is missing field {exc}"
            ) from exc

    created_at = payload["created_at"]
    if not isinstance(created_at, str) or not created_at:
        raise PermalinkDecodeError("permalink token's 'created_at' must be a non-empty string")

    return PermalinkState(
        inputs=inputs, created_at=created_at, recorded_figures=tuple(recorded_figures)
    )


@dataclass(frozen=True)
class FieldDiff:
    """One field that differs between what a permalink recorded and what
    the SAME-labelled rate reads right now."""

    field: Literal["value", "source_url", "date_checked"]
    recorded: str | None
    current: str | None


@dataclass(frozen=True)
class RateDiff:
    """One recorded rate's verdict on reopen (UI-12). `status` is one of
    three values, never collapsed to a boolean:

      - `"unchanged"` — a genuinely resolved current rate matched by
        label, and every recorded field (value/source_url/date_checked)
        is identical to what was recorded. Rendered EXPLICITLY, never as
        silence (UI-12's first honesty requirement).
      - `"changed"` — a genuinely resolved current rate matched by
        label, and at least one field differs; `changes` names each one
        individually.
      - `"cannot_determine"` — no current rate shares this label, or MORE
        THAN ONE does (ambiguous); `reason` states which. NEVER reported
        as `"unchanged"` (UI-12's second honesty requirement) — an
        unresolvable rate is reported as unresolvable, not as a false
        reassurance that nothing changed.
    """

    label: str
    status: Literal["unchanged", "changed", "cannot_determine"]
    changes: tuple[FieldDiff, ...]
    reason: str | None


def compute_diff(
    recorded_figures: Sequence[RecordedFigure], current_figures: Sequence[Figure]
) -> tuple[RateDiff, ...]:
    """Diff `recorded_figures` (a permalink's own creation-time snapshot)
    against `current_figures` (the rate figures the SAME comparison's
    inputs price RIGHT NOW — typically
    `app.services.provenance.collect_rate_figures` run fresh on the
    freshly-rebuilt `Figure` tree).

    Matched by `Figure.label` — the closest thing this codebase has to a
    stable business key for "the same rate" across two points in time (a
    `figure_id` is a fresh UUID on every construction, per `engine/figure
    .py`'s own docstring, so it can never survive a recomputation and is
    therefore useless as a diff key here).

    A label with zero or more than one current match resolves to
    `"cannot_determine"`, never `"unchanged"` — see `RateDiff`'s own
    docstring for why collapsing an unresolved match into "unchanged"
    would be a false reassurance."""
    current_by_label: dict[str, list[Figure]] = {}
    for figure in current_figures:
        current_by_label.setdefault(figure.label, []).append(figure)

    results: list[RateDiff] = []
    for recorded in recorded_figures:
        matches = current_by_label.get(recorded.label, [])

        if len(matches) == 0:
            results.append(
                RateDiff(
                    label=recorded.label,
                    status="cannot_determine",
                    changes=(),
                    reason=(
                        f"no rate named {recorded.label!r} is used in the current "
                        "comparison — cannot determine whether it changed, was "
                        "renamed, or was removed"
                    ),
                )
            )
            continue

        if len(matches) > 1:
            results.append(
                RateDiff(
                    label=recorded.label,
                    status="cannot_determine",
                    changes=(),
                    reason=(
                        f"{len(matches)} distinct current rates share the label "
                        f"{recorded.label!r} — cannot determine which one corresponds "
                        "to the rate this link recorded"
                    ),
                )
            )
            continue

        current = matches[0]
        current_date = current.date_checked.isoformat() if current.date_checked else None
        changes: list[FieldDiff] = []
        if recorded.value != str(current.value):
            changes.append(FieldDiff("value", recorded.value, str(current.value)))
        if recorded.source_url != current.source_url:
            changes.append(FieldDiff("source_url", recorded.source_url, current.source_url))
        if recorded.date_checked != current_date:
            changes.append(FieldDiff("date_checked", recorded.date_checked, current_date))

        results.append(
            RateDiff(
                label=recorded.label,
                status="changed" if changes else "unchanged",
                changes=tuple(changes),
                reason=None,
            )
        )

    return tuple(results)


@dataclass(frozen=True)
class PermalinkDiffView:
    """The render-ready wrapper `compare.html`'s "what's changed" banner
    reads. `all_unchanged` is `True` only when `rates` is non-empty AND
    every entry resolved to `"unchanged"` — a link that recorded zero
    rates, or one that could not resolve every rate, never claims this
    (see `build_diff_view`)."""

    created_at: str
    rates: tuple[RateDiff, ...]
    recorded_count: int
    all_unchanged: bool


def build_diff_view(state: PermalinkState, current_figures: Sequence[Figure]) -> PermalinkDiffView:
    """Build the render-ready diff for a decoded permalink. `all_unchanged`
    is deliberately conservative: it is `True` only when EVERY recorded
    rate resolved to `"unchanged"` — a single `"cannot_determine"` entry
    (or a link that recorded no rates at all) means the page must show
    the per-rate table instead of a blanket "nothing changed" claim."""
    rates = compute_diff(state.recorded_figures, current_figures)
    all_unchanged = bool(rates) and all(rate.status == "unchanged" for rate in rates)
    return PermalinkDiffView(
        created_at=state.created_at,
        rates=rates,
        recorded_count=len(state.recorded_figures),
        all_unchanged=all_unchanged,
    )

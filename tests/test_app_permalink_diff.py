"""UI-12 — the diff must distinguish "unchanged" from "unknown" (Phase 6,
plan 06-04).

Two honesty requirements, proven both at the unit level
(`app.services.permalink.compute_diff`) and end-to-end over the real
`GET /compare?permalink=...` surface:

1. A link whose data is genuinely unchanged says so EXPLICITLY.
2. Where a recorded rate cannot be resolved against the current data
   (renamed, removed, or ambiguous), it is reported as "cannot determine
   what changed" — NEVER as "unchanged". This is checked as a property
   across every non-single-match scenario, not one example.
"""

from __future__ import annotations

import base64
import json
import re
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.services.compare import CompareInputs
from app.services.permalink import PermalinkState as _PermalinkState
from app.services.permalink import (
    RecordedFigure,
    build_diff_view,
    compute_diff,
)
from engine.figure import Figure

client = TestClient(app)


def _leaf(label: str, value: str, *, source_url: str | None = "https://example.gov/rate",
          date_checked: date | None = date(2026, 1, 1)) -> Figure:
    return Figure(
        value=Decimal(value),
        unit="USD",
        label=label,
        derivation=("test fixture",),
        inputs=(),
        source_url=source_url,
        date_checked=date_checked,
        confidence="researched",
        live_fetched_this_run=False,
        basis="sourced",
    )


def _recorded(label: str, value: str, *, source_url: str | None = "https://example.gov/rate",
              date_checked: str | None = "2026-01-01") -> RecordedFigure:
    return RecordedFigure(
        label=label,
        value=value,
        unit="USD",
        source_url=source_url,
        date_checked=date_checked,
        basis="sourced",
        confidence="researched",
    )


# ---------------------------------------------------------------------------
# compute_diff — the core honesty properties
# ---------------------------------------------------------------------------


def test_genuinely_unchanged_rate_reports_unchanged_explicitly():
    recorded = (_recorded("Camera day rate", "500"),)
    current = (_leaf("Camera day rate", "500"),)
    diffs = compute_diff(recorded, current)
    assert len(diffs) == 1
    assert diffs[0].status == "unchanged"
    assert diffs[0].changes == ()


def test_changed_value_names_the_field_recorded_and_current():
    recorded = (_recorded("Camera day rate", "500"),)
    current = (_leaf("Camera day rate", "550"),)
    diffs = compute_diff(recorded, current)
    assert diffs[0].status == "changed"
    fields = {c.field for c in diffs[0].changes}
    assert fields == {"value"}
    assert diffs[0].changes[0].recorded == "500"
    assert diffs[0].changes[0].current == "550"


def test_changed_source_url_is_named_individually():
    recorded = (_recorded("Camera day rate", "500", source_url="https://old.gov/rate"),)
    current = (_leaf("Camera day rate", "500", source_url="https://new.gov/rate"),)
    diffs = compute_diff(recorded, current)
    assert diffs[0].status == "changed"
    fields = {c.field for c in diffs[0].changes}
    assert fields == {"source_url"}


def test_changed_date_checked_is_named_individually():
    recorded = (_recorded("Camera day rate", "500", date_checked="2026-01-01"),)
    current = (_leaf("Camera day rate", "500", date_checked=date(2026, 6, 1)),)
    diffs = compute_diff(recorded, current)
    assert diffs[0].status == "changed"
    fields = {c.field for c in diffs[0].changes}
    assert fields == {"date_checked"}


def test_multiple_fields_changed_are_all_named():
    recorded = (_recorded("Camera day rate", "500", source_url="https://old.gov/rate"),)
    current = (_leaf("Camera day rate", "600", source_url="https://new.gov/rate"),)
    diffs = compute_diff(recorded, current)
    fields = {c.field for c in diffs[0].changes}
    assert fields == {"value", "source_url"}


def test_zero_matching_current_rates_is_cannot_determine_never_unchanged():
    """A renamed or removed rate — no current rate shares its label."""
    recorded = (_recorded("Extinct rate", "500"),)
    current = (_leaf("A totally different rate", "500"),)
    diffs = compute_diff(recorded, current)
    assert diffs[0].status == "cannot_determine"
    assert diffs[0].status != "unchanged"
    assert "no rate named" in diffs[0].reason


def test_ambiguous_multiple_matching_current_rates_is_cannot_determine_never_unchanged():
    """Two distinct current rates sharing the recorded label — cannot
    disambiguate which one corresponds."""
    recorded = (_recorded("Ambiguous rate", "500"),)
    current = (
        _leaf("Ambiguous rate", "500", source_url="https://a.gov/rate"),
        _leaf("Ambiguous rate", "500", source_url="https://b.gov/rate"),
    )
    diffs = compute_diff(recorded, current)
    assert diffs[0].status == "cannot_determine"
    assert diffs[0].status != "unchanged"
    assert "distinct current rates share the label" in diffs[0].reason


def test_property_every_non_single_match_scenario_is_never_reported_unchanged():
    """The honesty property, proven across a MATRIX of match counts (0,
    1, 2, 3) — only the exact 1-match case may ever report "unchanged"."""
    for match_count in (0, 1, 2, 3):
        recorded = (_recorded("Rate under test", "500"),)
        current = tuple(_leaf("Rate under test", "500") for _ in range(match_count))
        diffs = compute_diff(recorded, current)
        status = diffs[0].status
        if match_count == 1:
            assert status == "unchanged"
        else:
            assert status == "cannot_determine", (
                f"match_count={match_count} must never report 'unchanged', got {status!r}"
            )


def test_multiple_recorded_rates_each_get_their_own_independent_verdict():
    recorded = (
        _recorded("Rate A", "100"),
        _recorded("Rate B", "200"),
        _recorded("Rate C — renamed away", "300"),
    )
    current = (
        _leaf("Rate A", "100"),  # unchanged
        _leaf("Rate B", "250"),  # changed
        # Rate C has no current match at all.
    )
    diffs = compute_diff(recorded, current)
    by_label = {d.label: d for d in diffs}
    assert by_label["Rate A"].status == "unchanged"
    assert by_label["Rate B"].status == "changed"
    assert by_label["Rate C — renamed away"].status == "cannot_determine"


# ---------------------------------------------------------------------------
# build_diff_view — the render-ready "all_unchanged" aggregate
# ---------------------------------------------------------------------------


def test_build_diff_view_all_unchanged_true_only_when_every_rate_resolved_unchanged():
    recorded = (_recorded("Rate A", "100"), _recorded("Rate B", "200"))
    current = (_leaf("Rate A", "100"), _leaf("Rate B", "200"))
    state = _PermalinkState(inputs=CompareInputs(), created_at="2026-01-01T00:00:00Z", recorded_figures=recorded)
    view = build_diff_view(state, current)
    assert view.all_unchanged is True
    assert view.recorded_count == 2


def test_build_diff_view_all_unchanged_false_when_any_rate_is_cannot_determine():
    recorded = (_recorded("Rate A", "100"), _recorded("Rate B — gone", "200"))
    current = (_leaf("Rate A", "100"),)
    state = _PermalinkState(inputs=CompareInputs(), created_at="2026-01-01T00:00:00Z", recorded_figures=recorded)
    view = build_diff_view(state, current)
    assert view.all_unchanged is False


def test_build_diff_view_all_unchanged_false_when_no_rates_were_recorded():
    """An empty recorded set must NOT read as "all unchanged" — there
    was nothing to check at all, a distinct state from "checked and
    found nothing different"."""
    state = _PermalinkState(inputs=CompareInputs(), created_at="2026-01-01T00:00:00Z", recorded_figures=())
    view = build_diff_view(state, ())
    assert view.all_unchanged is False
    assert view.recorded_count == 0


# ---------------------------------------------------------------------------
# End-to-end over the real HTTP surface
# ---------------------------------------------------------------------------


def _payload_of(token: str) -> dict:
    padded = token + "=" * (-len(token) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))


def _token_of(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _share_token_from(html: str) -> str:
    match = re.search(r'id="pf-share-url"\s+readonly\s+value="[^"]*permalink=([^"]+)"', html)
    assert match, "no permalink token found in the rendered share link"
    return match.group(1)


def test_reopening_an_unchanged_link_shows_the_explicit_no_changes_banner():
    """Nothing genuinely changes between creating and reopening a link
    within the same test run (the committed data is static) — the page
    must say so EXPLICITLY, not render nothing."""
    first = client.get("/compare", params={"candidate_cities": ["New York, NY"]})
    token = _share_token_from(first.text)

    second = client.get("/compare", params={"permalink": token})
    assert second.status_code == 200
    html = second.text
    assert "pf-diff-section" in html
    assert 'data-diff-all-unchanged' in html
    assert "No changes" in html


def test_reopening_a_link_with_a_fabricated_changed_rate_shows_it_named_individually():
    """Feed a token whose recorded_figures intentionally disagree with
    the real current data — the page must name that SPECIFIC rate as
    changed, with both the recorded and current value visible."""
    first = client.get("/compare", params={"candidate_cities": ["New York, NY"]})
    token = _share_token_from(first.text)
    payload = _payload_of(token)
    assert payload["recorded_figures"], "expected at least one recorded rate on a real comparison"
    tampered_label = payload["recorded_figures"][0]["label"]
    payload["recorded_figures"][0]["value"] = "1"  # a value that cannot match reality
    tampered_token = _token_of(payload)

    response = client.get("/compare", params={"permalink": tampered_token})
    assert response.status_code == 200
    html = response.text
    assert 'data-diff-status="changed"' in html
    assert f'data-diff-label="{tampered_label}"' in html


def test_reopening_a_link_with_an_unresolvable_recorded_rate_says_cannot_determine_never_unchanged():
    """A recorded rate whose label no longer exists in the current data
    at all — the page must say "cannot determine", never claim
    "unchanged" for that row."""
    first = client.get("/compare", params={"candidate_cities": ["New York, NY"]})
    token = _share_token_from(first.text)
    payload = _payload_of(token)
    payload["recorded_figures"].append(
        {
            "label": "a rate that has never existed in this dataset",
            "value": "999",
            "unit": "USD",
            "source_url": "https://example.gov/nonexistent",
            "date_checked": "2026-01-01",
            "basis": "sourced",
            "confidence": "researched",
        }
    )
    mutated_token = _token_of(payload)

    response = client.get("/compare", params={"permalink": mutated_token})
    assert response.status_code == 200
    html = response.text
    assert 'data-diff-status="cannot_determine"' in html
    assert "cannot determine what changed" in html
    # The specific fabricated row must never ALSO appear marked "unchanged".
    row_match = re.search(
        r'<tr data-diff-status="([^"]+)" data-diff-label="a rate that has never existed in this dataset">',
        html,
    )
    assert row_match
    assert row_match.group(1) != "unchanged"


def test_no_permalink_present_carries_no_diff_section_at_all():
    """`permalink_diff` is only ever populated when this page was
    actually reached through a permalink — a fresh comparison carries no
    diff banner (there is nothing yet to diff against)."""
    response = client.get("/compare")
    assert "pf-diff-section" not in response.text

"""UI-08 — the permalink: the ONLY persistence mechanism (Phase 6, plan
06-04). There is no login, no session, no server-side saved-comparison
table.

The property this module exists to prove: `encode_permalink(decode_
permalink(token)) == token` for every token this module itself produces
— across MANY input combinations, not one happy-path example — and a
permalink that would otherwise silently drop an input REFUSES to decode
rather than reproducing a different comparison under the same URL.
"""

from __future__ import annotations

import base64
import itertools
import json
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.compare import CompareInputs
from app.services.permalink import (
    PermalinkDecodeError,
    PermalinkState,
    RecordedFigure,
    decode_permalink,
    encode_permalink,
)

client = TestClient(app)


def _states() -> list[PermalinkState]:
    """A generated MATRIX of `PermalinkState`s, varying production_type,
    shoot days, crew (size XOR tier), cast counts, start window,
    candidate-city lists (varying length/content), display currency, and
    gap-city selection — a property proven across many combinations, not
    one example."""
    production_types = ("feature", "limited_series", "episodic")
    crew_options = [
        {"crew_size": 50, "crew_tier": None},
        {"crew_size": None, "crew_tier": "mid"},
        {"crew_size": 12, "crew_tier": None},
    ]
    city_lists = [
        ["New York, NY"],
        ["New York, NY", "Los Angeles, CA"],
        ["New York, NY", "Los Angeles, CA", "London, UK"],
        ["Atlanta, GA"],
    ]
    start_windows = [("Q1", 2025), ("Q2", 2026), ("Q4", 2036)]
    display_currencies = ("USD", "GBP")
    gap_selections = [(None, None), ("us-ny-new-york", "us-ca-los-angeles")]

    states: list[PermalinkState] = []
    combos = itertools.product(
        production_types, crew_options, city_lists, start_windows, display_currencies, gap_selections
    )
    for index, (
        production_type,
        crew,
        cities,
        (quarter, year),
        display_currency,
        (gap_a, gap_b),
    ) in enumerate(combos):
        inputs = CompareInputs(
            production_type=production_type,
            shoot_days_stage=10 + index % 5,
            shoot_days_location=index % 3,
            crew_size=crew["crew_size"],
            crew_tier=crew["crew_tier"],
            principal_cast_count=index % 4,
            principal_cast_imported_count=index % 2,
            crew_imported_count=index % 6,
            crew_hired_locally_count=index % 8,
            start_quarter=quarter,
            start_year=year,
            candidate_cities=cities,
            display_currency=display_currency,
            gap_city_a=gap_a,
            gap_city_b=gap_b,
        )
        recorded_figures = (
            RecordedFigure(
                label=f"Test rate {index}",
                value="12345",
                unit="USD",
                source_url="https://example.gov/rate",
                date_checked="2026-01-01",
                basis="sourced",
                confidence="researched",
            ),
        )
        states.append(
            PermalinkState(
                inputs=inputs,
                created_at=f"2026-01-0{1 + index % 9}T00:00:00Z",
                recorded_figures=recorded_figures,
            )
        )
    return states


_STATES = _states()


def test_state_matrix_is_non_trivial():
    assert len(_STATES) >= 20, "the round-trip property must be checked across many combinations"


def test_decode_of_encode_reproduces_every_input_field():
    for state in _STATES:
        token = encode_permalink(state)
        decoded = decode_permalink(token)
        assert decoded.inputs == state.inputs
        assert decoded.created_at == state.created_at
        assert decoded.recorded_figures == state.recorded_figures


def test_encode_of_decode_is_byte_identical_to_the_original_token():
    """The exact property UI-08's own must-haves name: `encode_permalink
    (decode_permalink(token)) == token` — deterministic encoding, proven
    across the whole matrix, not one example."""
    for state in _STATES:
        token = encode_permalink(state)
        round_tripped = encode_permalink(decode_permalink(token))
        assert round_tripped == token


def test_every_token_is_url_safe():
    for state in _STATES:
        token = encode_permalink(state)
        assert re.fullmatch(r"[A-Za-z0-9_-]+", token), f"token contains unsafe characters: {token!r}"


def test_no_two_distinct_states_in_the_matrix_collide_on_token():
    tokens = [encode_permalink(state) for state in _STATES]
    assert len(tokens) == len(set(tokens)), "distinct states must never encode to the same token"


# ---------------------------------------------------------------------------
# The dropped-field refusal — "worse than failing to encode" is refused
# ---------------------------------------------------------------------------


def _payload_of(token: str) -> dict:
    padded = token + "=" * (-len(token) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))


def _token_of(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def test_decode_refuses_a_token_missing_one_input_field_rather_than_defaulting():
    """The core honesty property: `CompareInputs` has a default for
    every field, so a naive decode could silently paper over a dropped
    one — this must raise, naming the missing field, never construct a
    DIFFERENT comparison under the same URL."""
    state = _STATES[0]
    token = encode_permalink(state)
    payload = _payload_of(token)
    del payload["inputs"]["candidate_cities"]
    truncated_token = _token_of(payload)

    with pytest.raises(PermalinkDecodeError, match="candidate_cities"):
        decode_permalink(truncated_token)


def test_decode_refuses_when_every_input_field_but_one_is_present():
    """Proven across EVERY field, not just one — dropping any single
    `CompareInputs` field must be caught."""
    state = _STATES[1]
    token = encode_permalink(state)
    payload = _payload_of(token)
    for field_name in list(payload["inputs"].keys()):
        mutated = json.loads(json.dumps(payload))  # deep copy
        del mutated["inputs"][field_name]
        mutated_token = _token_of(mutated)
        with pytest.raises(PermalinkDecodeError, match=re.escape(field_name)):
            decode_permalink(mutated_token)


def test_decode_refuses_malformed_base64():
    with pytest.raises(PermalinkDecodeError):
        decode_permalink("not-valid-base64!!!___***")


def test_decode_refuses_a_token_missing_created_at_or_recorded_figures():
    state = _STATES[0]
    token = encode_permalink(state)
    for key in ("created_at", "recorded_figures"):
        payload = _payload_of(token)
        del payload[key]
        mutated_token = _token_of(payload)
        with pytest.raises(PermalinkDecodeError, match=key):
            decode_permalink(mutated_token)


def test_decode_refuses_a_recorded_figure_missing_a_field():
    state = _STATES[0]
    token = encode_permalink(state)
    payload = _payload_of(token)
    del payload["recorded_figures"][0]["source_url"]
    mutated_token = _token_of(payload)
    with pytest.raises(PermalinkDecodeError, match="source_url"):
        decode_permalink(mutated_token)


# ---------------------------------------------------------------------------
# End-to-end over the real HTTP surface — UI-08's own top-level claim
# ---------------------------------------------------------------------------


def _share_token_from(html: str) -> str:
    match = re.search(r'id="pf-share-url"\s+readonly\s+value="[^"]*permalink=([^"]+)"', html)
    assert match, "no permalink token found in the rendered share link"
    return match.group(1)


def test_get_compare_offers_a_share_permalink_on_every_render():
    response = client.get("/compare")
    assert response.status_code == 200
    assert "pf-share-link" in response.text
    token = _share_token_from(response.text)
    assert token


def test_reopening_the_shared_permalink_reproduces_the_same_totals():
    """The literal UI-08 claim: opening the URL in a fresh session with
    no cookie reproduces the same comparison."""
    first = client.get("/compare", params={"candidate_cities": ["New York, NY", "Los Angeles, CA"]})
    token = _share_token_from(first.text)

    fresh_session = TestClient(app)  # a genuinely separate client — no shared cookie jar
    second = fresh_session.get("/compare", params={"permalink": token})
    assert second.status_code == 200
    assert "758427" in second.text  # NY total, unchanged
    assert "693521" in second.text  # LA total, unchanged


def test_get_compare_carries_no_session_cookie_ever():
    """No login, no session, no cookie store — the permalink is the
    ONLY persistence mechanism."""
    response = client.get("/compare")
    assert "set-cookie" not in {k.lower() for k in response.headers}
    response2 = client.get("/compare", params={"candidate_cities": ["New York, NY"]})
    assert "set-cookie" not in {k.lower() for k in response2.headers}


def test_get_compare_invalid_permalink_returns_422_never_a_silent_default():
    response = client.get("/compare", params={"permalink": "totally-not-a-real-token!!"})
    assert response.status_code == 422
    assert "invalid permalink" in response.json()["detail"].lower()


def test_get_compare_permalink_with_dropped_field_returns_422():
    valid = client.get("/compare")
    token = _share_token_from(valid.text)
    payload = _payload_of(token)
    del payload["inputs"]["start_quarter"]
    truncated_token = _token_of(payload)

    response = client.get("/compare", params={"permalink": truncated_token})
    assert response.status_code == 422


def test_permalink_query_param_is_exclusive_of_other_query_params():
    """When `permalink` is present, it is the SOLE source of truth — a
    conflicting `candidate_cities` in the same query string is ignored
    rather than creating an ambiguous merge of two input sources."""
    original = client.get("/compare", params={"candidate_cities": ["New York, NY"]})
    token = _share_token_from(original.text)

    # A different candidate_cities value alongside the permalink token
    # must NOT influence the reproduced comparison.
    response = client.get(
        "/compare",
        params={"permalink": token, "candidate_cities": ["London, UK"]},
    )
    assert response.status_code == 200
    assert "New York, NY" in response.text

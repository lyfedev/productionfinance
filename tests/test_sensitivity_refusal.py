"""The sensitivity refusal is stated, not routed around by narrowing the slider.

`engine.sensitivity.sensitivity_rows` perturbs the shoot's start date, so from a
late start it reaches past the window the committed union-rate snapshots cover.
The engine raises there rather than carrying a rate forward from an expired row
— the same refusal discipline as an unsourced transfer discount.

Two things are guarded here:

1. The engine's refusal is real and specific to the boundary (not blanket).
2. That refusal reaches a visitor as a stated reason rather than a 500, and the
   slider still offers the late start date. The tempting workaround was to drop
   the late quarter so the raise could not be triggered, which would narrow the
   product's real range and hide a genuine data boundary.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.compare import SLIDER_QUARTERS
from app.services.spec import (
    SENSITIVITY_BEYOND_RATE_DATA_REASON,
    SpecFormSubmission,
    handle_spec_submission,
)
from engine.sensitivity import sensitivity_rows

_BASE = {
    "production_type": "feature",
    "shoot_days_stage": 20,
    "shoot_days_location": 15,
    "crew_tier": "mid",
    "principal_cast_count": 4,
    "principal_cast_imported_count": 2,
    "crew_imported_count": 5,
    "crew_hired_locally_count": 40,
    "candidate_cities": ["us-ny-new-york", "us-ca-los-angeles"],
}


def _spec(quarter: str, year: int):
    return handle_spec_submission(
        SpecFormSubmission(start_quarter=quarter, start_year=year, **_BASE)
    ).spec


def test_the_engine_refuses_to_price_a_perturbed_date_past_its_rate_window() -> None:
    """The refusal itself — the behaviour the app-level handling exists for.

    Asserted on the message, not just the type, so a different ValueError
    cannot satisfy this test.
    """
    with pytest.raises(ValueError, match="no union rate row covers"):
        sensitivity_rows(
            _spec("Q3", 2026),
            "us-ny-new-york",
            "us-ca-los-angeles",
            reporting_currency="USD",
        )


def test_the_refusal_is_specific_to_the_boundary_not_blanket() -> None:
    """An in-window start date still produces real perturbation rows.

    Without this, suppressing sensitivity entirely would pass the test above.
    """
    rows = sensitivity_rows(
        _spec("Q4", 2025),
        "us-ny-new-york",
        "us-ca-los-angeles",
        reporting_currency="USD",
    )
    assert rows, "an in-window start date must still yield sensitivity rows"


def test_the_app_states_the_refusal_instead_of_raising() -> None:
    """handle_spec_submission must not propagate the engine's ValueError.

    A visitor gets a stated reason; the page still prices.
    """
    result = handle_spec_submission(
        SpecFormSubmission(start_quarter="Q3", start_year=2026, **_BASE)
    )
    assert result.city_assessments, "the comparison itself must still price"
    assert result.sensitivity == (), "rows are withheld, never fabricated"
    assert result.sensitivity_reason, "an absence must carry a stated reason"


@pytest.mark.parametrize(("quarter", "year"), list(SLIDER_QUARTERS))
def test_every_offered_slider_position_returns_200(quarter: str, year: int) -> None:
    """Every start date the page offers must render, not 500.

    Parametrized over SLIDER_QUARTERS itself, so adding a position that
    cannot render fails here rather than in front of a visitor.
    """
    client = TestClient(app)
    index = list(SLIDER_QUARTERS).index((quarter, year))
    response = client.get(f"/compare?start_index={index}")
    assert response.status_code == 200, f"{quarter} {year} returned {response.status_code}"


def test_the_slider_still_offers_the_late_quarter() -> None:
    """Regression guard on the workaround this replaces.

    Q3 2026 had been removed from the slider so the raise could not fire.
    Restoring it is the point: the boundary is disclosed, not avoided.
    """
    assert ("Q3", 2026) in SLIDER_QUARTERS

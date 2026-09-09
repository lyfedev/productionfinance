"""Route C — "Job 1" — end-to-end HTTP coverage (05-03).

Every saved-run fixture below is built by driving the REAL
`agent.job1.run_job1` through its offline seams (`search_fn`/`extract_fn`/
`extract_awards_fn`, plan 05-02) and then persisted through the REAL
`agent.runs` serialiser — never a hand-written JSON blob, so the fixture
and the serialiser can never silently drift apart. `run_mode` is flipped
to `"live"` via `dataclasses.replace` for the tests that need to prove the
live-accuracy path, since `run_job1` itself always reports `"replay"` for
any seam-injected call (T-05-10) — this test module is the ONE place
outside `agent/job1.py` allowed to construct that override, precisely
because it is proving the router's gate, not bypassing it.

`monkeypatch.delenv(..., raising=False)` for every key variable on every
test — results must never depend on the developer's shell (05-01/05-02
precedent, `tests/test_agent_eligibility.py`).
"""

from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

import agent.runs as runs_module
import app.routers.job1 as job1_router
from agent.gemini_client import ExtractionResult
from agent.job1 import Job1Run, TerminalReason, run_job1
from agent.parallel_client import DisclosureDocument
from agent.schema import ExtractedAward, ExtractedAwardSet
from agent.settings import IntegrationStatus
from app.main import app

client = TestClient(app)

_FAKE_URL = "https://esd.ny.gov/test-double-report.pdf"


def _fake_search() -> str:
    return _FAKE_URL


def _fake_extract(url: str) -> DisclosureDocument:
    markdown = "test-double-markdown, not a real government document"
    return DisclosureDocument(
        url=url, markdown=markdown, sha256="deadbeef" * 8, char_count=len(markdown)
    )


def _fake_extract_awards_factory(awards: list[ExtractedAward]):
    def _fake(_markdown: str) -> ExtractionResult:
        return ExtractionResult(
            award_set=ExtractedAwardSet(
                report_title="ESD Test Double Report",
                report_period="Q9-2099",
                awards=awards,
            ),
            truncated=False,
            model="test-double",
        )

    return _fake


def _three_bucket_awards() -> list[ExtractedAward]:
    """One of each match class — exact, explained, unexplained — using the
    same NY 25% base-rate figures already proven correct in
    tests/test_agent_job1_offline.py."""
    return [
        ExtractedAward(
            production_title="Test Production Alpha",
            qualified_spend="$10,000,000",
            credit_amount="$2,500,000",
            diversity_credit_amount=None,
            source_row_text="Test Production Alpha | $10,000,000 | $2,500,000 | —",
        ),
        ExtractedAward(
            production_title="Test Production Beta",
            qualified_spend="$20,000,000",
            credit_amount="$5,003,000",
            diversity_credit_amount="$3,000",
            source_row_text="Test Production Beta | $20,000,000 | $5,003,000 | $3,000",
        ),
        ExtractedAward(
            production_title="Test Production Gamma (unexplained)",
            qualified_spend="$8,000,000",
            credit_amount="$2,100,000",
            diversity_credit_amount=None,
            source_row_text="Test Production Gamma | $8,000,000 | $2,100,000 | —",
        ),
    ]


def _build_run(awards: list[ExtractedAward], *, run_mode: str | None = None) -> Job1Run:
    run = run_job1(
        search_fn=_fake_search,
        extract_fn=_fake_extract,
        extract_awards_fn=_fake_extract_awards_factory(awards),
    )
    if run_mode is not None:
        run = dataclasses.replace(run, run_mode=run_mode)
    return run


@pytest.fixture(autouse=True)
def _isolated_job1_state(tmp_path, monkeypatch):
    """No test writes into the repo (`var/job1/` and `runs/job1/` both
    redirected to `tmp_path`), no test depends on the developer's shell
    (every key variable unset), and no test leaks rate-limit/in-flight
    state into the next one (module-level globals in app.routers.job1
    reset before and after)."""
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    monkeypatch.setattr(runs_module, "RUNS_DIR", tmp_path / "var-job1")
    monkeypatch.setattr(runs_module, "COMMITTED_RUNS_DIR", tmp_path / "runs-job1-empty")

    job1_router._RUN_REGISTRY.clear()
    job1_router._LAST_RUN_STARTED_MONO = None
    if job1_router._RUN_LOCK.locked():
        job1_router._RUN_LOCK.release()

    yield

    job1_router._RUN_REGISTRY.clear()
    job1_router._LAST_RUN_STARTED_MONO = None
    if job1_router._RUN_LOCK.locked():
        job1_router._RUN_LOCK.release()


# ---------------------------------------------------------------------------
# GET /job1 — not configured, replay run, live run
# ---------------------------------------------------------------------------


def test_get_job1_with_no_keys_names_both_env_vars():
    response = client.get("/job1")
    assert response.status_code == 200
    assert "PARALLEL_API_KEY" in response.text
    assert "GEMINI_API_KEY" in response.text


def test_get_job1_with_persisted_replay_run_never_shows_accuracy():
    run = _build_run(_three_bucket_awards())  # run_mode stays "replay"
    assert run.run_mode == "replay"
    runs_module.save_run(run, run_id="a" * 32)

    response = client.get("/job1")
    assert response.status_code == 200
    assert "REPLAY" in response.text
    assert "honest bucket counts" not in response.text
    assert "Test Production Gamma" not in response.text


def test_get_job1_with_persisted_live_run_shows_bucket_counts_and_every_award():
    run = _build_run(_three_bucket_awards(), run_mode="live")
    assert run.run_mode == "live"
    assert run.accuracy.exact_match == 1
    assert run.accuracy.explained_variance == 1
    assert run.accuracy.unexplained == 1
    runs_module.save_run(run, run_id="b" * 32)

    response = client.get("/job1")
    assert response.status_code == 200
    assert "honest bucket counts" in response.text
    # The denominator appears beside each bucket (D-86: counts, never a
    # bare percentage).
    assert "/ 3" in response.text
    # Every award row, including the unexplained one — never collapsed.
    assert "Test Production Alpha" in response.text
    assert "Test Production Beta" in response.text
    assert "Test Production Gamma (unexplained)" in response.text
    assert "unexplained" in response.text


# ---------------------------------------------------------------------------
# POST /job1 — not configured, rate limit, in-flight
# ---------------------------------------------------------------------------


def test_post_job1_with_no_keys_renders_not_configured_and_starts_no_thread():
    response = client.post("/job1")
    assert response.status_code == 200
    assert "PARALLEL_API_KEY" in response.text
    assert "GEMINI_API_KEY" in response.text
    # No run was ever registered — the not-configured check happens BEFORE
    # any threading.Thread is started.
    assert job1_router._RUN_REGISTRY == {}


def _configure_fast_run(monkeypatch):
    """Simulate both keys present and a fast (already-terminal) run, so
    the rate-limit/in-flight logic can be exercised without a real key or
    a real SDK call."""
    fake_status = IntegrationStatus(parallel_configured=True, gemini_configured=True, missing=())
    monkeypatch.setattr(job1_router, "integration_status", lambda: fake_status)

    def _fast_run_job1(*, on_stage=None, **_kwargs) -> Job1Run:
        if on_stage is not None:
            on_stage("searching")
            on_stage("pricing")
        return Job1Run(run_mode="live", terminal_reason=TerminalReason.ok)

    monkeypatch.setattr(job1_router, "run_job1", _fast_run_job1)


def test_post_job1_rate_limit_html_then_json_429(monkeypatch):
    _configure_fast_run(monkeypatch)

    first = client.post("/job1", follow_redirects=False)
    assert first.status_code == 303
    assert "/job1/" in first.headers["location"]

    second = client.post("/job1")
    assert second.status_code == 200
    assert "wait" in second.text.lower()

    third = client.post("/api/v1/job1")
    assert third.status_code == 429


# ---------------------------------------------------------------------------
# GET /job1/{run_id} and GET /api/v1/job1/{run_id}
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    [
        "not-a-valid-id",
        "a" * 100,
        "../../../../etc/passwd",
    ],
)
def test_get_job1_run_invalid_id_returns_404(bad_id):
    response = client.get(f"/api/v1/job1/{bad_id}")
    assert response.status_code in (404, 400)


def test_get_job1_run_percent_encoded_traversal_returns_404():
    response = client.get("/api/v1/job1/somefakeid%2F..%2F..%2Fetc%2Fpasswd")
    assert response.status_code == 404


def test_get_job1_run_unknown_valid_shaped_id_returns_404():
    response = client.get(f"/api/v1/job1/{'0' * 32}")
    assert response.status_code == 404


def test_api_v1_job1_run_money_values_are_strings_and_no_secret_leaks():
    run = _build_run(_three_bucket_awards(), run_mode="live")
    run_id = "c" * 32
    runs_module.save_run(run, run_id=run_id)

    response = client.get(f"/api/v1/job1/{run_id}")
    assert response.status_code == 200
    body = response.json()

    for award in body["awards"]:
        assert isinstance(award["disclosed"], str)
        assert award["computed"] is None or isinstance(award["computed"], str)

    raw_text = response.text
    assert "PARALLEL_API_KEY" not in raw_text
    assert "GEMINI_API_KEY" not in raw_text
    assert "api_key" not in raw_text.lower()


# ---------------------------------------------------------------------------
# Jinja2 autoescaping — T-05-13
# ---------------------------------------------------------------------------


def test_extracted_title_with_script_tag_is_escaped_not_rendered_raw():
    malicious_award = ExtractedAward(
        production_title="<script>alert(1)</script> Pictures",
        qualified_spend="$10,000,000",
        credit_amount="$2,500,000",
        diversity_credit_amount=None,
        source_row_text="<script>alert(1)</script> Pictures | $10,000,000 | $2,500,000",
    )
    run = _build_run([malicious_award], run_mode="live")
    run_id = "d" * 32
    runs_module.save_run(run, run_id=run_id)

    response = client.get(f"/job1/{run_id}")
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


# ---------------------------------------------------------------------------
# Every pre-existing route keeps serving
# ---------------------------------------------------------------------------


def test_pre_existing_routes_still_return_200():
    for path in ("/health", "/", "/spec", "/validate"):
        response = client.get(path)
        assert response.status_code == 200, path

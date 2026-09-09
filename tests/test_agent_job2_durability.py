"""AGT-11's standing gate: a live research job whose process dies mid-run
must never hang, and the record it left behind must be reclassified,
honestly, by the next process's own startup.

Two layers are proven here:

  - Unit-level (`-k "sweep or boot or lifespan"`): `BOOT_ID` is a stable
    32-hex string for this process; `save_run`/`append_round` stamp it
    centrally on every write; `reclassify_interrupted_jobs()` rewrites a
    stale `running` record to `interrupted` while leaving this process's
    own running jobs, already-terminal records, and already-interrupted
    records untouched, is idempotent, and survives a corrupt neighbor file;
    the FastAPI `lifespan` hook runs the sweep on startup.
  - The real restart test (`test_sigkill_...`): a genuine two-process
    proof, in the same spirit as
    `tests/test_agent_eligibility.py::test_app_main_import_leaves_sdks_unimported`,
    which already uses subprocess isolation because an in-process assertion
    could not prove the claim. A child process is `SIGKILL`ed mid-round —
    never a clean shutdown, because a clean exit would let the process
    write its own terminal state and would prove nothing about the OOM
    kill or `systemctl restart` this gate exists for on the 472 MB host.
    The parent then reclassifies the orphaned record and confirms
    `GET /research/{job_id}` renders a terminal page with no auto-refresh
    on the very first load.

A third layer proves D-92/UI-10's rendering contract directly:
`app/templates/research_result.html` shows every round's objective,
queries, sources, summary, newly-determined and still-missing fields, and
what it searched next — for both an in-flight run (round, elapsed,
ceiling, refresh tag present) and a terminal run (no refresh tag, terminal
reason named in plain words).

Every test redirects `RESEARCH_RUNS_DIR` to `tmp_path` — no test writes
into the repo's own `var/job2/` (the same discipline
`tests/test_agent_job2_offline.py` already follows).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from agent import research_runs
from agent.research_runs import BOOT_ID, boot_id, reclassify_interrupted_jobs, save_run

REPO_ROOT = Path(__file__).resolve().parents[1]

_KEY_VARS = ("PARALLEL_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PRODFIN_GEMINI_MODEL")

# A genuine SDK response is never needed here: `run_job2` is driven entirely
# by the injected `search_fn`/`judge_fn` seams, exactly as
# `tests/test_agent_job2_offline.py` proves the loop offline. Round 1
# returns immediately so the child gets a durable record on disk; round 2's
# `search_fn` blocks for long enough that the parent's SIGKILL always lands
# mid-call, never after a natural return.
_CHILD_SCRIPT = """
import os
import sys
import time

os.environ["PRODFIN_JOB2_RUNS_DIR"] = sys.argv[1]

from agent.job2 import run_job2
from agent.research_schema import SufficiencyVerdict


def search_fn(**kwargs):
    if kwargs["round_number"] == 1:
        return [
            {
                "url": "https://example.org/incentive-programme",
                "title": "Example jurisdiction production incentive",
                "excerpts": ["A 25% rebate applies to qualifying local spend."],
            }
        ]
    time.sleep(600)
    return []


def judge_fn(**kwargs):
    return SufficiencyVerdict(
        decision="continue",
        findings=[],
        summary="round 1 summary: still researching",
        next_objective="continue researching the programme",
        next_queries=["refined query one", "refined query two"],
    )


run_job2("Nowhereville", None, job_id=sys.argv[2], search_fn=search_fn, judge_fn=judge_fn)
"""


@pytest.fixture(autouse=True)
def _no_agent_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """A result must never depend on the developer's own shell (the same
    guard `tests/test_agent_eligibility.py` uses)."""
    for var in _KEY_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _isolated_job2_runs_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test writes a record into the repo's own `var/job2/`."""
    monkeypatch.setattr(research_runs, "RESEARCH_RUNS_DIR", tmp_path)


def _write_record(
    tmp_path: Path, *, job_id: str, status: str, boot_id_value: str, round_count: int = 0
) -> Path:
    """Write a record DIRECTLY to disk (bypassing `save_run`, which always
    stamps THIS process's own `BOOT_ID`) — the only way to seed a record
    that looks like it was written by a different process."""
    record = {
        "schema_version": research_runs.SCHEMA_VERSION,
        "job_id": job_id,
        "city_input": "Nowhereville",
        "qualified_spend_input": None,
        "session_id": "session-1",
        "status": status,
        "terminal_reason": None if status == "running" else "sufficient",
        "message": None,
        "rounds": [],
        "sdk_calls": [],
        "started_at": "2026-09-09T00:00:00.000Z",
        "updated_at": "2026-09-09T00:00:00.000Z",
        "ceiling_seconds": 240.0,
        "boot_id": boot_id_value,
        "round_count": round_count,
    }
    path = tmp_path / f"{job_id}.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Boot identity
# ---------------------------------------------------------------------------


def test_boot_id_is_32_hex_characters():
    assert len(BOOT_ID) == 32
    assert all(c in "0123456789abcdef" for c in BOOT_ID)


def test_boot_id_function_matches_module_constant():
    assert boot_id() == BOOT_ID


def test_boot_id_stable_across_repeated_calls():
    assert boot_id() == boot_id() == BOOT_ID


def test_save_run_stamps_this_processs_own_boot_id(tmp_path):
    """A caller-supplied `boot_id` is never trusted — `save_run` stamps its
    OWN process's `BOOT_ID`, centrally, so no caller can drift from it."""
    job_id = "1" * 32
    save_run(
        {
            "schema_version": research_runs.SCHEMA_VERSION,
            "job_id": job_id,
            "status": "running",
            "boot_id": "a-caller-supplied-value-that-must-be-overwritten",
            "rounds": [],
            "round_count": 0,
        }
    )
    on_disk = json.loads((tmp_path / f"{job_id}.json").read_text(encoding="utf-8"))
    assert on_disk["boot_id"] == BOOT_ID


def test_append_round_stamps_this_processs_own_boot_id(tmp_path):
    job_id = "2" * 32
    save_run(
        {
            "schema_version": research_runs.SCHEMA_VERSION,
            "job_id": job_id,
            "status": "running",
            "rounds": [],
            "round_count": 0,
        }
    )
    updated = research_runs.append_round(job_id, {"round_number": 1})
    assert updated["boot_id"] == BOOT_ID
    on_disk = json.loads((tmp_path / f"{job_id}.json").read_text(encoding="utf-8"))
    assert on_disk["boot_id"] == BOOT_ID


# ---------------------------------------------------------------------------
# reclassify_interrupted_jobs() — the sweep
# ---------------------------------------------------------------------------


def test_sweep_returns_empty_list_when_runs_dir_missing(tmp_path, monkeypatch):
    missing_dir = tmp_path / "does-not-exist"
    monkeypatch.setattr(research_runs, "RESEARCH_RUNS_DIR", missing_dir)
    assert reclassify_interrupted_jobs() == []


def test_sweep_leaves_this_processs_own_running_job_untouched(tmp_path):
    job_id = "3" * 32
    _write_record(tmp_path, job_id=job_id, status="running", boot_id_value=BOOT_ID, round_count=1)

    assert reclassify_interrupted_jobs() == []

    on_disk = json.loads((tmp_path / f"{job_id}.json").read_text(encoding="utf-8"))
    assert on_disk["status"] == "running"


def test_sweep_rewrites_stale_running_job_to_interrupted(tmp_path):
    job_id = "4" * 32
    stale_boot = "b" * 32
    _write_record(
        tmp_path, job_id=job_id, status="running", boot_id_value=stale_boot, round_count=2
    )

    result = reclassify_interrupted_jobs()

    assert result == [job_id]
    on_disk = json.loads((tmp_path / f"{job_id}.json").read_text(encoding="utf-8"))
    assert on_disk["status"] == "interrupted"
    assert on_disk["terminal_reason"] == "interrupted_by_restart"
    assert on_disk["boot_id"] == BOOT_ID


def test_sweep_names_the_round_reached_in_the_message(tmp_path):
    job_id = "5" * 32
    _write_record(tmp_path, job_id=job_id, status="running", boot_id_value="c" * 32, round_count=3)

    reclassify_interrupted_jobs()

    on_disk = json.loads((tmp_path / f"{job_id}.json").read_text(encoding="utf-8"))
    assert "round 3" in on_disk["message"]


def test_sweep_names_round_zero_before_any_round_completed(tmp_path):
    job_id = "6" * 32
    _write_record(tmp_path, job_id=job_id, status="running", boot_id_value="d" * 32, round_count=0)

    reclassify_interrupted_jobs()

    on_disk = json.loads((tmp_path / f"{job_id}.json").read_text(encoding="utf-8"))
    assert "before completing its first round" in on_disk["message"]


def test_sweep_is_idempotent(tmp_path):
    job_id = "7" * 32
    _write_record(tmp_path, job_id=job_id, status="running", boot_id_value="e" * 32, round_count=1)

    first = reclassify_interrupted_jobs()
    second = reclassify_interrupted_jobs()

    assert first == [job_id]
    assert second == []


def test_sweep_never_touches_a_terminal_record(tmp_path):
    job_id = "8" * 32
    path = _write_record(
        tmp_path, job_id=job_id, status="terminal", boot_id_value="f" * 32, round_count=4
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    record["terminal_reason"] = "sufficient"
    path.write_text(json.dumps(record), encoding="utf-8")

    assert reclassify_interrupted_jobs() == []

    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["status"] == "terminal"
    assert on_disk["terminal_reason"] == "sufficient"


def test_sweep_never_touches_an_already_interrupted_record(tmp_path):
    job_id = "9" * 32
    path = _write_record(
        tmp_path, job_id=job_id, status="interrupted", boot_id_value="1a" * 16, round_count=1
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    record["terminal_reason"] = "interrupted_by_restart"
    record["message"] = "previously interrupted"
    path.write_text(json.dumps(record), encoding="utf-8")

    assert reclassify_interrupted_jobs() == []

    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["message"] == "previously interrupted"


def test_sweep_skips_corrupt_json_without_raising(tmp_path):
    (tmp_path / "not-valid.json").write_text("{this is not json", encoding="utf-8")
    job_id = "1b" * 16
    _write_record(tmp_path, job_id=job_id, status="running", boot_id_value="1c" * 16, round_count=0)

    result = reclassify_interrupted_jobs()  # must not raise

    assert result == [job_id]


# ---------------------------------------------------------------------------
# The FastAPI lifespan hook
# ---------------------------------------------------------------------------


def test_lifespan_reclassifies_stale_job_on_app_startup(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import app

    job_id = "1d" * 16
    _write_record(tmp_path, job_id=job_id, status="running", boot_id_value="1e" * 16, round_count=1)

    with TestClient(app):
        pass  # entering the context manager fires the lifespan startup event

    on_disk = json.loads((tmp_path / f"{job_id}.json").read_text(encoding="utf-8"))
    assert on_disk["status"] == "interrupted"
    assert on_disk["terminal_reason"] == "interrupted_by_restart"


# ---------------------------------------------------------------------------
# The real restart test: SIGKILL a child mid-round, prove no hang
# ---------------------------------------------------------------------------


def test_sigkill_mid_run_is_reclassified_by_a_fresh_process_and_renders_terminal(tmp_path):
    job_id = "1f" * 16
    record_path = tmp_path / f"{job_id}.json"

    child_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin")}

    proc = subprocess.Popen(
        [sys.executable, "-c", _CHILD_SCRIPT, str(tmp_path), job_id],
        cwd=REPO_ROOT,
        env=child_env,
    )
    try:
        deadline = time.monotonic() + 20
        record: dict | None = None
        while time.monotonic() < deadline:
            if record_path.is_file():
                try:
                    candidate = json.loads(record_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    candidate = None
                if (
                    candidate
                    and candidate.get("round_count", 0) >= 1
                    and candidate.get("status") == "running"
                ):
                    record = candidate
                    break
            time.sleep(0.05)
        else:
            proc.kill()
            proc.wait(timeout=10)
            pytest.fail("child process never wrote a running round-1 record")

        assert record is not None
        assert record["status"] == "running"
        assert record["round_count"] == 1
        child_boot_id = record["boot_id"]
        # The child is a genuinely different process from this test's own —
        # its boot_id can never equal this process's BOOT_ID.
        assert child_boot_id != BOOT_ID

        # SIGKILL, not a clean shutdown: a graceful exit would let the
        # child write its own terminal state and would prove nothing about
        # a crash or an OOM kill on the 472 MB host.
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)

    # The killed process never had the chance to write its own terminal
    # state — the record on disk is still exactly what it was mid-run.
    orphaned = json.loads(record_path.read_text(encoding="utf-8"))
    assert orphaned["status"] == "running"
    assert orphaned["boot_id"] == child_boot_id

    reclassified = reclassify_interrupted_jobs()
    assert reclassified == [job_id]

    reclassified_record = json.loads(record_path.read_text(encoding="utf-8"))
    assert reclassified_record["status"] == "interrupted"
    assert reclassified_record["terminal_reason"] == "interrupted_by_restart"
    assert "round 1" in reclassified_record["message"]

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        html_response = client.get(f"/research/{job_id}")
        assert html_response.status_code == 200
        body = html_response.text
        assert "interrupted" in body.lower()
        assert 'http-equiv="refresh"' not in body

        json_response = client.get(f"/api/v1/research/{job_id}")
        assert json_response.status_code == 200
        payload = json_response.json()
        assert payload["status"] == "interrupted"
        assert payload["round_count"] == 1


# ---------------------------------------------------------------------------
# D-92/UI-10: the reasoning trail as a rendered product surface
# ---------------------------------------------------------------------------


def _round_record(**overrides) -> dict:
    base = {
        "round_number": 1,
        "objective": "Determine whether Nowhereville has an active incentive programme.",
        "search_queries": ["Nowhereville film tax incentive"],
        "queries_normalized": False,
        "mode": "fast",
        "mode_normalized": False,
        "results": [
            {"url": "https://example.gov/incentive", "title": "Example incentive programme"}
        ],
        "decision": "continue",
        "findings": [],
        "summary": "Found a candidate programme page; rate not yet confirmed.",
        "newly_determined": [],
        "unmet_fields": ["rate", "qualifying_base_definition", "caps"],
        "discarded_fields": [],
        "at": "2026-09-09T18:00:05.000Z",
    }
    base.update(overrides)
    return base


def test_in_flight_page_names_round_elapsed_ceiling_and_carries_refresh_tag(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import app

    job_id = "20" * 16
    save_run(
        {
            "schema_version": research_runs.SCHEMA_VERSION,
            "job_id": job_id,
            "city_input": "Nowhereville",
            "qualified_spend_input": None,
            "session_id": "sess-1",
            "status": "running",
            "terminal_reason": None,
            "message": None,
            "rounds": [],
            "sdk_calls": [],
            "started_at": "2026-09-09T18:00:00.000Z",
            "updated_at": "2026-09-09T18:00:00.000Z",
            "ceiling_seconds": 240.0,
            "round_count": 0,
        }
    )
    research_runs.append_round(job_id, _round_record())

    with TestClient(app) as client:
        response = client.get(f"/research/{job_id}")

    assert response.status_code == 200
    body = response.text
    assert 'http-equiv="refresh"' in body
    assert "Round 1" in body
    assert "Elapsed:" in body
    assert "240s" in body  # the wall-clock ceiling
    assert "another round is in progress" in body


def test_terminal_page_renders_the_full_round_trail_and_no_refresh_tag(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import app

    job_id = "21" * 16
    save_run(
        {
            "schema_version": research_runs.SCHEMA_VERSION,
            "job_id": job_id,
            "city_input": "Nowhereville",
            "qualified_spend_input": None,
            "session_id": "sess-1",
            "status": "terminal",
            "terminal_reason": "sufficient",
            "message": "All five fields determined.",
            "rounds": [],
            "sdk_calls": [],
            "started_at": "2026-09-09T18:00:00.000Z",
            "updated_at": "2026-09-09T18:00:10.000Z",
            "ceiling_seconds": 240.0,
            "round_count": 0,
        }
    )
    research_runs.append_round(
        job_id,
        _round_record(
            round_number=1,
            newly_determined=["rate"],
            unmet_fields=[
                "qualifying_base_definition",
                "caps",
                "payout_mechanism",
                "current_availability",
            ],
        ),
    )
    research_runs.append_round(
        job_id,
        _round_record(
            round_number=2,
            objective="continue researching the remaining fields",
            decision="sufficient",
            summary="round summary: sufficient",
            newly_determined=[
                "qualifying_base_definition",
                "caps",
                "payout_mechanism",
                "current_availability",
            ],
            unmet_fields=[],
        ),
    )

    with TestClient(app) as client:
        html_response = client.get(f"/research/{job_id}")
        json_response = client.get(f"/api/v1/research/{job_id}")

    assert html_response.status_code == 200
    body = html_response.text
    assert 'http-equiv="refresh"' not in body
    # Every round's objective, sources, summary, and field lists are on the page.
    assert "Round 1" in body and "Round 2" in body
    assert "Determine whether Nowhereville" in body
    assert "continue researching the remaining fields" in body
    assert "https://example.gov/incentive" in body
    assert "Example incentive programme" in body
    assert "Found a candidate programme page" in body
    assert "round summary: sufficient" in body
    assert "rate" in body
    assert "qualifying base definition" in body  # underscores rendered as spaces
    # Round 1's "searched next" is round 2's own objective — the two never diverge.
    assert body.count("continue researching the remaining fields") >= 2
    assert "2 rounds" in body
    assert "sufficient" in body.lower()

    # The JSON mirror carries the identical rounds list (D-92: the two
    # surfaces can never diverge on what happened).
    assert json_response.status_code == 200
    payload = json_response.json()
    assert payload["round_count"] == 2
    assert [r["round_number"] for r in payload["rounds"]] == [1, 2]
    assert (
        payload["rounds"][0]["objective"]
        == "Determine whether Nowhereville has an active incentive programme."
    )

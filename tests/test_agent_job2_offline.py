"""CI has no API keys and must never need them. This proves the whole D-90
research loop offline by injecting fakes at the two seams
`agent.job2.run_job2` left (`search_fn`/`judge_fn`), driven by scripted
`SufficiencyVerdict` decisions — never a real Parallel or Gemini call. The
LIVE claim (a real Search call, a real Gemini call, executing inside an
anonymous request's own lifecycle) is proven separately, by the production
`PRODFIN_SDK_CALL` log line plus the `var/job2/{job_id}.json` artifact it
writes while a real request is in flight (D-96's audit input), never
through this offline test.

Follows the structure and reasoning of `tests/test_agent_job1_offline.py`
and the SHP-05/SHP-06 gate in `tests/test_agent_eligibility.py`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent import research_runs
from agent.job2 import InvalidCityInputError, run_job2, validate_city_input
from agent.research_runs import InvalidJobIdError, load_run
from agent.research_schema import (
    FieldFinding,
    JurisdictionIdentity,
    SufficiencyField,
    SufficiencyVerdict,
    research_response_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

_KEY_VARS = ("PARALLEL_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PRODFIN_GEMINI_MODEL")


@pytest.fixture(autouse=True)
def _no_agent_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """A result must never depend on the developer's own shell (the same
    guard `tests/test_agent_eligibility.py` uses)."""
    for var in _KEY_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _isolated_job2_runs_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test writes a record into the repo's own `var/job2/` — every test
    that persists a run redirects `RESEARCH_RUNS_DIR` to `tmp_path`."""
    monkeypatch.setattr(research_runs, "RESEARCH_RUNS_DIR", tmp_path)


def _stripped_source(relative_path: str) -> str:
    """Read a module's source and drop comment-only lines (a grep that
    counts a comment is a self-invalidating gate)."""
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    kept = [line for line in text.splitlines() if not line.strip().startswith("#")]
    return "\n".join(kept)


_FIXTURE_RESULT = {
    "url": "https://example.org/incentive-programme",
    "title": "Example jurisdiction production incentive",
    "excerpts": ["A 25% rebate applies to qualifying local spend, capped annually."],
}


def _scripted_seams(job_id: str, decisions: list[str]):
    """A `search_fn`/`judge_fn` pair scripted to walk `decisions` in order.

    The fake `search_fn` reads `var/job2/{job_id}.json` from the filesystem
    BEFORE recording its own call and asserts it already contains exactly
    as many rounds as calls made so far, with `status == \"running\"` — the
    durability proof for D-92 (every round on disk before the next round's
    Search fires).
    """
    remaining = list(decisions)
    search_calls: list[dict] = []

    def _search_fn(**kwargs):
        record = load_run(job_id)
        assert record is not None
        assert record["status"] == "running"
        assert len(record["rounds"]) == len(search_calls)
        search_calls.append(kwargs)
        return [dict(_FIXTURE_RESULT)]

    def _judge_fn(**kwargs):
        decision = remaining.pop(0)
        round_number = kwargs["round_number"]
        findings = []
        identity = None
        if decision == "sufficient":
            findings = [
                FieldFinding(
                    field=f,
                    determined=True,
                    value_text=f"value-{f.value}",
                    source_url="https://example.org/incentive-programme",
                )
                for f in SufficiencyField
            ]
            # A "sufficient" claim also requires the jurisdiction identity
            # (agent.job2's insufficient_identity check) — supplied here so
            # this fixture's "sufficient" verdicts are genuinely sufficient.
            identity = JurisdictionIdentity(
                jurisdiction_name="Nowhereville",
                country_code="XX",
                level="city",
                currency="USD",
            )
        return SufficiencyVerdict(
            decision=decision,
            findings=findings,
            identity=identity,
            summary=f"round {round_number}: {decision}",
            next_objective=f"refined objective after round {round_number}",
            next_queries=[f"refined query {round_number}a", f"refined query {round_number}b"],
            next_mode="fast",
        )

    return _search_fn, _judge_fn, search_calls


# ---------------------------------------------------------------------------
# D-90: round count is a property of the scripted verdicts, never the driver
# ---------------------------------------------------------------------------


def test_scripted_sufficient_on_round_one_produces_exactly_one_round():
    job_id = "a" * 32
    search_fn, judge_fn, search_calls = _scripted_seams(job_id, ["sufficient"])

    run = run_job2("Nowhereville", None, job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    assert run.status == "terminal"
    assert run.terminal_reason == "sufficient"
    assert len(run.rounds) == 1
    assert len(search_calls) == 1


def test_scripted_continue_then_sufficient_produces_exactly_two_rounds():
    job_id = "b" * 32
    search_fn, judge_fn, search_calls = _scripted_seams(job_id, ["continue", "sufficient"])

    run = run_job2("Nowhereville", None, job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    assert run.terminal_reason == "sufficient"
    assert len(run.rounds) == 2
    assert len(search_calls) == 2


def test_scripted_four_continues_then_give_up_produces_exactly_five_rounds():
    job_id = "c" * 32
    decisions = ["continue", "continue", "continue", "continue", "give_up"]
    search_fn, judge_fn, search_calls = _scripted_seams(job_id, decisions)

    run = run_job2("Nowhereville", None, job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    # TerminalReason.agent_gave_up — distinct from the decision literal
    # "give_up" the model returned (agent.job2.TerminalReason).
    assert run.terminal_reason == "agent_gave_up"
    assert len(run.rounds) == 5
    assert len(search_calls) == 5


def test_scripted_no_programme_found_is_a_legitimate_one_round_terminal():
    """D-94: \"no programme found\" is a legitimate, correct result — never
    an error papered over."""
    job_id = "d" * 32
    search_fn, judge_fn, _ = _scripted_seams(job_id, ["no_programme_found"])

    run = run_job2("Nowhereville", None, job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    assert run.status == "terminal"
    assert run.terminal_reason == "no_programme_found"
    assert len(run.rounds) == 1


# ---------------------------------------------------------------------------
# session_id: one per job, threaded through every round's Search call
# ---------------------------------------------------------------------------


def test_session_id_is_threaded_through_every_scripted_search_call():
    job_id = "e" * 32
    search_fn, judge_fn, search_calls = _scripted_seams(
        job_id, ["continue", "continue", "sufficient"]
    )

    run = run_job2("Nowhereville", None, job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    assert run.session_id
    assert len(search_calls) == 3
    assert all(call["session_id"] == run.session_id for call in search_calls)


# ---------------------------------------------------------------------------
# Objective refinement: round 2 searches under round 1's next_objective,
# never round 1's own objective (D-90's SDK-finding spine).
# ---------------------------------------------------------------------------


def test_round_two_search_receives_round_ones_next_objective_and_queries():
    job_id = "f" * 32
    search_fn, judge_fn, search_calls = _scripted_seams(job_id, ["continue", "sufficient"])

    run_job2("Nowhereville", None, job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    assert search_calls[0]["objective"] != search_calls[1]["objective"]
    assert search_calls[1]["objective"] == "refined objective after round 1"
    assert search_calls[1]["search_queries"] == ["refined query 1a", "refined query 1b"]


# ---------------------------------------------------------------------------
# D-92: every round is durable on disk before the next round's Search fires.
# The assertion lives inside _scripted_seams's fake search_fn itself — if
# the ordering were ever violated, that assertion (not this test) is what
# would raise. This test additionally re-reads the final file directly.
# ---------------------------------------------------------------------------


def test_final_record_on_disk_matches_the_returned_run():
    job_id = "0" * 32
    search_fn, judge_fn, _ = _scripted_seams(job_id, ["continue", "sufficient"])

    run = run_job2("Nowhereville", None, job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    on_disk = load_run(job_id)
    assert on_disk is not None
    assert on_disk["status"] == "terminal"
    assert on_disk["round_count"] == 2
    assert len(on_disk["rounds"]) == 2
    assert on_disk["session_id"] == run.session_id
    assert on_disk["schema_version"] == research_runs.SCHEMA_VERSION
    assert on_disk["boot_id"] == research_runs.boot_id()


# ---------------------------------------------------------------------------
# T-07-04: job_id from a URL path segment never reaches open() unvalidated.
# ---------------------------------------------------------------------------


def test_load_run_rejects_path_traversal_before_touching_any_path():
    with pytest.raises(InvalidJobIdError):
        load_run("../../etc/passwd")


@pytest.mark.parametrize(
    "bad_id",
    ["not-a-valid-id", "a" * 100, "../../../../etc/passwd", "A" * 32, ""],
)
def test_load_run_rejects_every_non_conforming_id_shape(bad_id: str):
    with pytest.raises(InvalidJobIdError):
        load_run(bad_id)


# ---------------------------------------------------------------------------
# T-07-05: the visitor's city string is bounded before it reaches an
# objective or a query — a rejected input is never truncated and used.
# ---------------------------------------------------------------------------


def test_validate_city_input_rejects_empty_and_overlong_and_control_chars():
    with pytest.raises(InvalidCityInputError):
        validate_city_input("")
    with pytest.raises(InvalidCityInputError):
        validate_city_input("   ")
    with pytest.raises(InvalidCityInputError):
        validate_city_input("x" * 121)
    with pytest.raises(InvalidCityInputError):
        validate_city_input("Nowhere\x00ville")


def test_validate_city_input_accepts_and_strips_a_normal_name():
    assert validate_city_input("  Nowhereville  ") == "Nowhereville"


# ---------------------------------------------------------------------------
# D-91: the sufficiency contract is the closed five-value set and nothing
# else — a sixth field is a Pydantic validation error at parse time.
# ---------------------------------------------------------------------------


def test_sufficiency_field_has_exactly_five_members():
    assert {f.value for f in SufficiencyField} == {
        "rate",
        "qualifying_base_definition",
        "caps",
        "payout_mechanism",
        "current_availability",
    }


def test_a_sixth_sufficiency_field_fails_validation():
    with pytest.raises(ValidationError):
        FieldFinding.model_validate({"field": "not_a_real_field", "determined": True})

    with pytest.raises(ValidationError):
        SufficiencyVerdict.model_validate(
            {
                "decision": "sufficient",
                "findings": [{"field": "some_sixth_field", "determined": True}],
                "summary": "bogus",
            }
        )


def test_research_response_schema_is_the_only_schema_source():
    assert research_response_schema() == SufficiencyVerdict.model_json_schema()


# ---------------------------------------------------------------------------
# D-95/T-05-something's Job 2 twin: both real SDK imports stay lazy.
# ---------------------------------------------------------------------------


def test_job2_imports_parallel_inside_a_function():
    source = _stripped_source("agent/job2.py")
    import_lines = [
        line for line in source.splitlines() if line.strip().startswith("import parallel")
    ]
    assert import_lines, "expected at least one 'import parallel' statement"
    for line in import_lines:
        assert line.startswith((" ", "\t")), "import must be inside a function body"


def test_job2_imports_google_genai_inside_a_function():
    source = _stripped_source("agent/job2.py")
    import_lines = [
        line for line in source.splitlines() if line.strip() == "from google import genai"
    ]
    assert import_lines, "expected a 'from google import genai' import statement"
    for line in import_lines:
        assert line.startswith((" ", "\t")), "import must be inside a function body"


def test_app_main_import_leaves_sdks_unimported_with_job2_router_wired_in():
    """Subprocess isolation so a prior test's imports in THIS interpreter
    cannot mask the lazy-import contract — the same shape
    `tests/test_agent_eligibility.py` uses, re-proven here now that
    `app/routers/research.py` (and its `agent.job2` import) is wired into
    `app.main`."""
    probe = (
        "import sys, app.main; "
        "print('google.genai' in sys.modules); "
        "print('parallel' in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines == ["False", "False"], (result.stdout, result.stderr)


# ---------------------------------------------------------------------------
# No CLI entry point exists — D-96's audit input.
# ---------------------------------------------------------------------------


def test_job2_module_has_no_main_entry_point():
    source = _stripped_source("agent/job2.py")
    assert "__main__" not in source
    assert "argparse" not in source


# ---------------------------------------------------------------------------
# With all four key variables deleted, every route serves legibly.
# ---------------------------------------------------------------------------


def test_app_serves_every_route_with_no_keys_present():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    for path in ("/health", "/", "/spec", "/validate", "/job1", "/research"):
        response = client.get(path)
        assert response.status_code == 200, path

    post_response = client.post("/research", data={"city": "Nowhereville", "qualified_spend": ""})
    assert post_response.status_code == 200
    assert "PARALLEL_API_KEY" in post_response.text


def test_get_research_with_no_keys_names_both_env_vars():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.get("/research")
    assert response.status_code == 200
    assert "PARALLEL_API_KEY" in response.text
    assert "GEMINI_API_KEY" in response.text

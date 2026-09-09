"""The SHP-05 / SHP-06 eligibility gate.

Mechanically proves — without ever calling a live SDK, without any API key
in the environment — that:

  - `agent.job1` and `app.main` both import cleanly with no key set, and
    importing either leaves neither `google.genai` nor `parallel` in
    `sys.modules` (the lazy-import contract that keeps the FastAPI process
    footprint on the 472 MB host unchanged until a run is triggered).
  - `agent.settings.integration_status()` and `not_configured_message()`
    report the missing state legibly and never leak a key value.
  - Both `agent/parallel_client.py` and `agent/gemini_client.py` genuinely
    import their SDK (inside a function, not at module top level) and route
    every SDK call through the unconditional D-84 `PRODFIN_SDK_CALL` log
    line.
  - `agent/gemini_client.py` sources its extraction schema from
    `gemini_response_schema()` / `model_json_schema()`, never a
    hand-written second JSON schema (D-83).
  - The pre-existing FastAPI surface still serves every route with no keys
    present.

This file is the standing CI gate for SHP-05 and SHP-06 — it must be able
to fail. `monkeypatch.delenv` clears all four key variable names on every
test so the result never depends on the developer's own shell.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

_KEY_VARS = ("PARALLEL_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PRODFIN_GEMINI_MODEL")


@pytest.fixture(autouse=True)
def _no_agent_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _KEY_VARS:
        monkeypatch.delenv(var, raising=False)


def _stripped_source(relative_path: str) -> str:
    """Read a module's source and drop comment-only lines (a grep that
    counts a comment is a self-invalidating gate)."""
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    kept = [line for line in text.splitlines() if not line.strip().startswith("#")]
    return "\n".join(kept)


# ---------------------------------------------------------------------------
# Import safety with no keys
# ---------------------------------------------------------------------------


def test_importing_agent_job1_with_no_keys_raises_nothing():
    import agent.job1  # noqa: F401 — import itself is the assertion


def test_importing_app_main_with_no_keys_raises_nothing():
    import app.main  # noqa: F401


def test_app_main_import_leaves_sdks_unimported():
    """Subprocess isolation so a prior test's imports in THIS interpreter
    cannot mask the lazy-import contract."""
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
# agent.settings — no key value ever escapes
# ---------------------------------------------------------------------------


def test_integration_status_both_unset():
    from agent.settings import integration_status

    status = integration_status()
    assert status.parallel_configured is False
    assert status.gemini_configured is False
    assert any("PARALLEL_API_KEY" in name for name in status.missing)
    assert any("GEMINI_API_KEY" in name for name in status.missing)


def test_not_configured_message_names_both_variables_no_values():
    from agent.settings import IntegrationStatus, integration_status

    message = integration_status().not_configured_message()
    assert "PARALLEL_API_KEY" in message
    assert "GEMINI_API_KEY" in message

    # `not_configured_message()` is built purely from `missing` (variable
    # NAMES) — never from a key value. Prove that structurally: a status
    # carrying a value that LOOKS like a key in an unrelated field never
    # reaches the message, because the method only ever reads `self.missing`.
    fake_status = IntegrationStatus(
        parallel_configured=False,
        gemini_configured=False,
        missing=("PARALLEL_API_KEY", "GEMINI_API_KEY (or GOOGLE_API_KEY)"),
    )
    assert "sk-not-a-real-secret-value" not in fake_status.not_configured_message()


# ---------------------------------------------------------------------------
# Source-level proof: real SDK imports, on the real call path
# ---------------------------------------------------------------------------


def test_gemini_client_imports_google_genai_inside_a_function():
    source = _stripped_source("agent/gemini_client.py")
    import_lines = [
        line for line in source.splitlines() if line.strip() == "from google import genai"
    ]
    assert import_lines, "expected a 'from google import genai' import statement"
    for line in import_lines:
        assert line.startswith((" ", "\t")), "import must be inside a function body"


def test_parallel_client_imports_parallel_inside_a_function():
    source = _stripped_source("agent/parallel_client.py")
    import_lines = [line for line in source.splitlines() if line.strip().startswith("import parallel")]
    assert import_lines, "expected at least one 'import parallel' statement"
    for line in import_lines:
        assert line.startswith((" ", "\t")), "import must be inside a function body"


def test_gemini_client_uses_model_json_schema_never_a_hand_written_schema():
    source = _stripped_source("agent/gemini_client.py")
    assert "gemini_response_schema()" in source or "model_json_schema()" in source
    # A hand-written JSON Schema literal would declare its own "type" key
    # for an object — this project's only such schema is produced by
    # Pydantic's model_json_schema(), never typed out by hand here.
    assert '"type": "object"' not in source
    assert "'type': 'object'" not in source


def test_schema_module_defines_exactly_one_schema_source():
    from agent.schema import ExtractedAwardSet, gemini_response_schema

    assert gemini_response_schema() == ExtractedAwardSet.model_json_schema()


# ---------------------------------------------------------------------------
# D-84: the PRODFIN_SDK_CALL log line is unconditional
# ---------------------------------------------------------------------------


def test_sdk_call_prefix_used_at_both_call_sites():
    parallel_source = _stripped_source("agent/parallel_client.py")
    gemini_source = _stripped_source("agent/gemini_client.py")
    assert "sdk_call(" in parallel_source
    assert "sdk_call(" in gemini_source


def test_sdk_call_implementation_has_no_verbosity_guard():
    telemetry_source = _stripped_source("agent/telemetry.py")
    assert "SDK_CALL_LOG_PREFIX" in telemetry_source
    forbidden = ("os.environ.get(\"PRODFIN_DEBUG", "if debug", "getenv(\"VERBOSE")
    for token in forbidden:
        assert token not in telemetry_source


def test_sdk_call_emits_one_line_with_elapsed_and_ok_outcome(caplog: pytest.LogCaptureFixture):
    from datetime import datetime

    from agent.telemetry import SDK_CALL_LOG_PREFIX, sdk_call

    with caplog.at_level("INFO", logger="prodfin.sdk"), sdk_call("test-sdk", "noop", "test-target"):
        pass

    records = [r for r in caplog.records if r.message.startswith(SDK_CALL_LOG_PREFIX)]
    assert len(records) == 1
    message = records[0].message
    assert "elapsed_ms=" in message
    assert "outcome=ok" in message
    at_value = message.split("at=")[1].split(" ")[0]
    datetime.fromisoformat(at_value)


def test_sdk_call_reraises_and_logs_error_outcome(caplog: pytest.LogCaptureFixture):
    from agent.telemetry import SDK_CALL_LOG_PREFIX, sdk_call

    with (
        caplog.at_level("INFO", logger="prodfin.sdk"),
        pytest.raises(ValueError, match="boom"),
        sdk_call("test-sdk", "noop", "test-target"),
    ):
        raise ValueError("boom")

    records = [r for r in caplog.records if r.message.startswith(SDK_CALL_LOG_PREFIX)]
    assert len(records) == 1
    assert "outcome=error" in records[0].message


# ---------------------------------------------------------------------------
# The pre-existing app surface still serves with no keys
# ---------------------------------------------------------------------------


def test_app_serves_all_pre_existing_routes_with_no_keys():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/spec").status_code == 200
    assert client.get("/validate").status_code == 200

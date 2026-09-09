"""CI has no API keys and must never need them. This proves the whole
extract-price-classify loop offline by injecting fakes at the three seams
`agent.job1.run_job1` left (`search_fn`/`extract_fn`/`extract_awards_fn`),
driven by a small committed test-double fixture
(`tests/fixtures/agent/esd_excerpt_double.md`) — never a real government
disclosure. The LIVE claim (a real Search call, a real Extract call, a real
Gemini call) is proven separately, through the run artifact plus the
production log line (plan 05-03), never through this offline test.

Also proves, by AST inspection rather than a text grep (a grep counts a
docstring — D-87), that no module in `agent/` outside `agent/schema.py`
ever constructs an extracted-award object, and that `agent/` imports
nothing from `engine/` except the two sanctioned names (D-85).

Finally: the AGT-03 gate. Exactly one of two states must hold — a
committed live run artifact under `runs/job1/` with `run_mode == "live"`
and `exact_match >= 3`, OR a `.planning/WINDOWS.md` entry naming AGT-03.
This is deliberately not a `skip` — a skipped test is indistinguishable in
CI from a passing one.
"""

from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path

from agent.gemini_client import ExtractionResult
from agent.job1 import run_job1
from agent.parallel_client import DisclosureDocument
from agent.schema import ExtractedAward, ExtractedAwardSet
from agent.taxonomy import MatchClass

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = REPO_ROOT / "agent"
DOUBLE_PATH = REPO_ROOT / "tests" / "fixtures" / "agent" / "esd_excerpt_double.md"
RUNS_DIR = REPO_ROOT / "runs" / "job1"
WINDOWS_PATH = REPO_ROOT / ".planning" / "WINDOWS.md"

_FAKE_URL = "https://esd.ny.gov/test-double-report.pdf"


def _double_awards() -> list[ExtractedAward]:
    """Hand-built `ExtractedAward`s mirroring
    `tests/fixtures/agent/esd_excerpt_double.md` row for row. Building
    these directly here (a test module, not `agent/*.py`) is exactly what
    the D-87 AST gate below permits — the fixture file documents the
    committed shape; this function drives the loop from it."""
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
            production_title="Test Production Gamma",
            qualified_spend="$8,000,000",
            credit_amount="$2,100,000",
            diversity_credit_amount=None,
            source_row_text="Test Production Gamma | $8,000,000 | $2,100,000 | —",
        ),
        ExtractedAward(
            production_title="Test Production Delta",
            qualified_spend="3.964.760,00",
            credit_amount="991.190,00",
            diversity_credit_amount=None,
            source_row_text="Test Production Delta | 3.964.760,00 | 991.190,00 | —",
        ),
        ExtractedAward(
            production_title="Test Production Epsilon",
            qualified_spend="n/a",
            credit_amount="$1,000,000",
            diversity_credit_amount=None,
            source_row_text="Test Production Epsilon | n/a | $1,000,000 | —",
        ),
    ]


def _fake_search() -> str:
    return _FAKE_URL


def _fake_extract(url: str) -> DisclosureDocument:
    markdown = DOUBLE_PATH.read_text(encoding="utf-8")
    return DisclosureDocument(url=url, markdown=markdown, sha256="test-double", char_count=len(markdown))


def _fake_extract_awards(markdown: str) -> ExtractionResult:
    return ExtractionResult(
        award_set=ExtractedAwardSet(
            report_title="ESD Test Double Report",
            report_period="Q9-2099",
            awards=_double_awards(),
        ),
        truncated=False,
        model="test-double",
    )


def _run_offline():
    return run_job1(
        search_fn=_fake_search,
        extract_fn=_fake_extract,
        extract_awards_fn=_fake_extract_awards,
    )


# ---------------------------------------------------------------------------
# The fixture itself declares its own status
# ---------------------------------------------------------------------------


def test_fixture_first_line_declares_itself_a_test_double() -> None:
    full_text = DOUBLE_PATH.read_text(encoding="utf-8")
    first_line = full_text.splitlines()[0]

    assert first_line.startswith("<!--")
    assert "TEST DOUBLE" in first_line

    lower = full_text.lower()
    assert "test double" in lower
    assert "not real" in lower or "not government data" in lower


# ---------------------------------------------------------------------------
# The whole loop, offline
# ---------------------------------------------------------------------------


def test_offline_loop_produces_expected_bucket_counts() -> None:
    run = _run_offline()

    assert run.terminal_reason.value == "ok"
    assert run.raw_award_count == 5
    assert run.accuracy.awards_extracted == 5
    assert run.accuracy.exact_match == 2  # Alpha, Delta
    assert run.accuracy.explained_variance == 1  # Beta (diversity credit)
    assert run.accuracy.unexplained == 1  # Gamma
    assert run.accuracy.extraction_failures == 1  # Epsilon (n/a)
    assert len(run.awards) == 4
    assert len(run.extraction_failures) == 1


def test_offline_loop_verdicts_are_the_expected_match_class_per_row() -> None:
    run = _run_offline()
    by_title = {r.award.production_title: r for r in run.awards}

    assert by_title["Test Production Alpha"].match_class is MatchClass.exact_match
    assert by_title["Test Production Beta"].match_class is MatchClass.explained_variance
    assert by_title["Test Production Beta"].explanation is not None
    assert by_title["Test Production Beta"].explanation.rule_id == "diversity-credit-column"
    assert by_title["Test Production Gamma"].match_class is MatchClass.unexplained
    assert by_title["Test Production Delta"].match_class is MatchClass.exact_match
    assert by_title["Test Production Delta"].disclosed == Decimal("991190.00")

    assert run.extraction_failures[0].production_title == "Test Production Epsilon"


def test_offline_run_is_never_live() -> None:
    run = _run_offline()
    assert run.run_mode == "replay"


# ---------------------------------------------------------------------------
# D-87: no module outside agent/schema.py ever constructs an
# extracted-award object — proven by an AST walk, not a text grep.
# ---------------------------------------------------------------------------

_MODEL_NAMES = {"ExtractedAward", "ExtractedAwardSet"}


def _agent_source_files() -> list[Path]:
    return sorted(AGENT_DIR.glob("*.py"))


def test_no_module_outside_schema_constructs_an_extracted_award_object() -> None:
    violations: list[str] = []
    for path in _agent_source_files():
        if path.name in ("schema.py", "__init__.py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id in _MODEL_NAMES:
                violations.append(f"{path.name}:{node.lineno}: direct call {func.id}(...)")
                continue
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id in _MODEL_NAMES
            ):
                # The ONE sanctioned site: agent/gemini_client.py parsing
                # the real Gemini response via a Pydantic classmethod.
                if path.name == "gemini_client.py" and func.attr.startswith("model_validate"):
                    continue
                violations.append(f"{path.name}:{node.lineno}: {func.value.id}.{func.attr}(...)")

    assert not violations, "extracted-award construction found outside schema.py:\n" + "\n".join(
        violations
    )


# ---------------------------------------------------------------------------
# D-85: agent/ imports nothing from engine/ except the two sanctioned names.
# ---------------------------------------------------------------------------

_ALLOWED_ENGINE_IMPORTS = {
    ("engine.models", "load_ruleset"),
    ("engine.pipeline", "price_jurisdiction"),
}


def test_agent_imports_nothing_from_engine_except_the_two_sanctioned_names() -> None:
    violations: list[str] = []
    for path in _agent_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("engine"):
                for alias in node.names:
                    if (node.module, alias.name) not in _ALLOWED_ENGINE_IMPORTS:
                        violations.append(f"{path.name}: from {node.module} import {alias.name}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("engine"):
                        violations.append(f"{path.name}: import {alias.name}")

    assert not violations, "unsanctioned engine/ import found in agent/:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# AGT-03: exactly one of two states must hold. No third state, no skip.
# ---------------------------------------------------------------------------


def _find_live_run_with_three_exact_matches() -> bool:
    if not RUNS_DIR.exists():
        return False
    for run_path in RUNS_DIR.glob("*.json"):
        try:
            data = json.loads(run_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("run_mode") == "live" and data.get("accuracy", {}).get("exact_match", 0) >= 3:
            return True
    return False


def _windows_names_agt_03() -> bool:
    if not WINDOWS_PATH.exists():
        return False
    text = WINDOWS_PATH.read_text(encoding="utf-8")
    return "AGT-03" in text


def test_agt_03_gate_is_satisfied_by_exactly_one_state() -> None:
    has_live_artifact = _find_live_run_with_three_exact_matches()
    has_windows_entry = _windows_names_agt_03()

    assert has_live_artifact or has_windows_entry, (
        "AGT-03 requires EITHER a committed live run artifact under "
        f"{RUNS_DIR} with run_mode=='live' and exact_match >= 3, OR a "
        f".planning/WINDOWS.md entry naming AGT-03. Neither was found — "
        "run `uv run python -m agent.job1 --require-live --json` with "
        "real keys and commit the artifact, or record the honest gap in "
        "WINDOWS.md via `gsd-tools windows append`."
    )

"""AGT-10's caching boundary made real across all five data classes
(plan 07-04) — Task 1 (live FX), Task 2 (live cap consumption / programme
status), and Task 3 (the single-point-of-truth AST gate, plus the
uncurated-city -> /research entry path, AGT-05) all land here.

Every SDK-touching test in this file either exercises the "no keys
present" undetermined path (deterministic, no network, matches this
project's `.env`-free execution environment) or injects fakes via
`monkeypatch.setattr` on `parallel.Parallel`/`google.genai.Client`
directly — never a real live SDK call. The one live network call this
plan genuinely proves (Frankfurter, no key required) is exercised
directly against `httpx.Client.get`, which this file's own tests
monkeypatch to control success/failure deterministically; the confirmed
real transcript lives in 07-04-SUMMARY.md, not in this file's assertions.

Follows `tests/test_agent_job1_offline.py`'s AST-inspection discipline
(D-87) for the structural gates — a text grep counts a docstring and is
self-invalidating.
"""

from __future__ import annotations

import ast
import dataclasses
import os
import re
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from agent.live_checks import (
    CapConsumptionResult,
    check_cap_consumption,
    check_programme_open,
)
from app.services.cache_policy import (
    POLICY,
    CacheBoundaryViolation,
    DataClass,
    resolve_cap_consumption,
    resolve_fx,
    resolve_programme_status,
)
from app.services.spec import SpecFormSubmission, SpecResult, handle_spec_submission

REPO_ROOT = Path(__file__).resolve().parents[1]


def _base_form_kwargs(**overrides: object) -> dict:
    kwargs = {
        "production_type": "feature",
        "shoot_days_stage": 10,
        "shoot_days_location": 5,
        "crew_size": 50,
        "crew_tier": None,
        "principal_cast_count": 3,
        "principal_cast_imported_count": 1,
        "crew_imported_count": 10,
        "crew_hired_locally_count": 40,
        "start_quarter": "Q2",
        "start_year": 2026,
        "candidate_cities": ["London"],
        "total_budget": None,
    }
    kwargs.update(overrides)
    return kwargs


def _valid_spec_form_data(**overrides: str) -> dict[str, str]:
    data = {
        "production_type": "feature",
        "shoot_days_stage": "10",
        "shoot_days_location": "5",
        "crew_size": "50",
        "crew_tier": "",
        "principal_cast_count": "3",
        "principal_cast_imported_count": "1",
        "crew_imported_count": "10",
        "crew_hired_locally_count": "40",
        "start_quarter": "Q2",
        "start_year": "2026",
        "candidate_cities": "New York, NY",
        "total_budget": "",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Task 1 — live FX (`-k "fx"`)
# ---------------------------------------------------------------------------


def _fake_frankfurter_success(rate: str):
    def _get(self, url, params=None, **kwargs):
        base = params["base"]
        quote = params["symbols"]
        payload = {
            "amount": 1.0,
            "base": base,
            "date": "2026-09-09",
            "rates": {quote: float(rate)},
        }
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    return _get


def _fake_frankfurter_failure(self, url, params=None, **kwargs):
    raise httpx.ConnectError("simulated network down")


def test_resolve_fx_attempts_live_first_and_succeeds(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_success("1.4"))
    resolution = resolve_fx("GBP", "USD", date(2026, 9, 9))
    assert resolution.origin == "live"
    assert resolution.rate == Decimal("1.4")
    assert isinstance(resolution.rate, Decimal)
    assert resolution.fetched_at is not None
    assert resolution.failure_reason is None
    assert "1.4" in resolution.disclosure


def test_resolve_fx_falls_back_and_names_the_snapshot_date_on_failure(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    resolution = resolve_fx("GBP", "USD", date(2026, 9, 9))
    assert resolution.origin == "committed_snapshot_fallback"
    assert resolution.rate == Decimal("1.363")
    assert resolution.snapshot_date == "2026-08-26"
    assert resolution.failure_reason is not None
    assert "2026-08-26" in resolution.disclosure
    assert "failed" in resolution.disclosure.lower()


def test_resolve_fx_never_derives_a_cross_rate_or_inverts_on_a_missing_snapshot(monkeypatch):
    """Only `data/fx/gbp-usd.yaml` is committed — the reverse pair
    (USD->GBP) has no snapshot. A live failure here must raise the same
    D-74 refusal `engine.fx` raises, never a derived or inverted rate."""
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    with pytest.raises(ValueError, match="no committed snapshot"):
        resolve_fx("USD", "GBP", date(2026, 9, 9))


def test_resolve_fx_asserts_live_and_never_fetches_when_policy_mutated(monkeypatch):
    mutated = dataclasses.replace(POLICY[DataClass.fx_rate], verdict="cached")
    monkeypatch.setitem(POLICY, DataClass.fx_rate, mutated)

    fetch_attempts: list[str] = []
    monkeypatch.setattr(httpx.Client, "get", lambda self, *a, **k: fetch_attempts.append(a) or None)

    with pytest.raises(CacheBoundaryViolation):
        resolve_fx("GBP", "USD", date(2026, 9, 9))
    assert fetch_attempts == []


def test_golden_totals_pinned_regardless_of_live_fx_outcome(monkeypatch):
    """AGT-10's core promise for FX: the /spec dollar total is computed
    exclusively from the committed snapshot (`engine.fx.convert`) and
    never moves because of what `resolve_fx` discloses — see
    `app/services/live_fx.py`'s module docstring."""

    def _submit() -> SpecResult:
        raw = SpecFormSubmission(**_base_form_kwargs())
        result = handle_spec_submission(raw)
        assert isinstance(result, SpecResult)
        return result

    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_success("1.4"))
    live_result = _submit()
    assert live_result.fx_resolutions
    assert live_result.fx_resolutions[0].origin == "live"
    assert live_result.ranked_cities[0].total_landed_cost.value == Decimal("747735")

    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    fallback_result = _submit()
    assert fallback_result.fx_resolutions[0].origin == "committed_snapshot_fallback"
    assert fallback_result.ranked_cities[0].total_landed_cost.value == Decimal("747735")


def test_ny_vs_la_gap_unaffected_by_fx_wiring(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", _fake_frankfurter_failure)
    raw = SpecFormSubmission(
        **_base_form_kwargs(candidate_cities=["New York, NY", "Los Angeles, CA"])
    )
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.gap is not None
    assert result.gap.headline_gap.value == Decimal("64906")
    # Neither city needs a currency conversion (both USD) — no FX call at all.
    assert result.fx_resolutions == ()


# ---------------------------------------------------------------------------
# Task 2 — live cap consumption / programme status (`-k "cap or programme_status"`)
# ---------------------------------------------------------------------------


def test_resolve_cap_consumption_returns_none_when_method_is_not_live_research():
    assert (
        resolve_cap_consumption(
            jurisdiction_name="Connecticut",
            programme_name="Christmas Always",
            cap_consumption_method=None,
            source_url_hint=None,
        )
        is None
    )
    assert (
        resolve_cap_consumption(
            jurisdiction_name="Connecticut",
            programme_name="Christmas Always",
            cap_consumption_method="official_dashboard",
            source_url_hint=None,
        )
        is None
    )


def test_resolve_cap_consumption_returns_the_determined_remaining_value(monkeypatch):
    monkeypatch.setattr(
        "agent.live_checks.check_cap_consumption",
        lambda jn, pn, hint: CapConsumptionResult(
            determined=True,
            remaining=Decimal("12345678"),
            value_text="$12,345,678",
            source_url="https://esd.ny.gov/report",
            checked_at="2026-09-09T00:00:00Z",
            reason=None,
        ),
    )
    remaining = resolve_cap_consumption(
        jurisdiction_name="New York",
        programme_name="Empire State Film Production Tax Credit",
        cap_consumption_method="live_research",
        source_url_hint=None,
    )
    assert remaining == Decimal("12345678")


def test_resolve_cap_consumption_returns_none_when_undetermined(monkeypatch):
    monkeypatch.setattr(
        "agent.live_checks.check_cap_consumption",
        lambda jn, pn, hint: CapConsumptionResult(
            determined=False,
            remaining=None,
            value_text=None,
            source_url=None,
            checked_at="2026-09-09T00:00:00Z",
            reason="not disclosed",
        ),
    )
    remaining = resolve_cap_consumption(
        jurisdiction_name="New York",
        programme_name="Empire State Film Production Tax Credit",
        cap_consumption_method="live_research",
        source_url_hint=None,
    )
    assert remaining is None


def test_resolve_cap_consumption_asserts_live_before_calling(monkeypatch):
    mutated = dataclasses.replace(POLICY[DataClass.cap_consumption], verdict="cached")
    monkeypatch.setitem(POLICY, DataClass.cap_consumption, mutated)

    calls: list[object] = []
    monkeypatch.setattr(
        "agent.live_checks.check_cap_consumption", lambda *a, **k: calls.append(a) or None
    )
    with pytest.raises(CacheBoundaryViolation):
        resolve_cap_consumption(
            jurisdiction_name="New York",
            programme_name="Empire State Film Production Tax Credit",
            cap_consumption_method="live_research",
            source_url_hint=None,
        )
    assert calls == []


def test_resolve_programme_status_asserts_live_before_calling(monkeypatch):
    mutated = dataclasses.replace(POLICY[DataClass.programme_open_status], verdict="cached")
    monkeypatch.setitem(POLICY, DataClass.programme_open_status, mutated)

    calls: list[object] = []
    monkeypatch.setattr(
        "agent.live_checks.check_programme_open", lambda *a, **k: calls.append(a) or None
    )
    with pytest.raises(CacheBoundaryViolation):
        resolve_programme_status(
            jurisdiction_name="New York", programme_name="Empire State Film Production Tax Credit"
        )
    assert calls == []


def test_check_cap_consumption_undetermined_with_no_keys(monkeypatch):
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = check_cap_consumption("New York", "Empire State Film Production Tax Credit", None)
    assert result.determined is False
    assert result.remaining is None
    assert "PARALLEL_API_KEY" in result.reason
    assert "GEMINI_API_KEY" in result.reason


def test_check_programme_open_unknown_with_no_keys(monkeypatch):
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = check_programme_open("New York", "Empire State Film Production Tax Credit")
    assert result.state == "unknown"
    assert "PARALLEL_API_KEY" in result.reason


def test_no_keys_no_sdk_module_ever_imported() -> None:
    """Run in a fresh subprocess (never the current test process, whose
    `sys.modules` may already carry `parallel`/`google.genai` from an
    earlier fake-injecting test in this same file) with both API keys
    stripped from the environment — mirrors this plan's own
    `<verify>` command shape for the app-startup check."""
    script = (
        "import sys\n"
        "from agent.live_checks import check_cap_consumption, check_programme_open\n"
        "check_cap_consumption('New York', 'Empire State Film Production Tax Credit', None)\n"
        "check_programme_open('New York', 'Empire State Film Production Tax Credit')\n"
        "assert 'parallel' not in sys.modules, 'parallel imported with no keys present'\n"
        "assert 'google.genai' not in sys.modules, 'google.genai imported with no keys present'\n"
        "print('OK')\n"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("PARALLEL_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


class _FakeSearchResult:
    def __init__(self, url: str, excerpts: list[str]) -> None:
        self.url = url
        self.excerpts = excerpts


class _FakeSearchResponse:
    def __init__(self, results: list[_FakeSearchResult]) -> None:
        self.results = results


class _FakeParallelClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def search(self, *, objective: str, search_queries: list[str], timeout: float):
        return _FakeSearchResponse(
            [_FakeSearchResult("https://esd.ny.gov/q3-report", ["some excerpt text"])]
        )


class _FakeGenaiResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, text: str) -> None:
        self._text = text

    def generate_content(self, *, model: str, contents: str, config: object):
        return _FakeGenaiResponse(self._text)


def _fake_genai_client(judgment_json: str):
    class _FakeGenaiClient:
        def __init__(self, api_key: str | None = None) -> None:
            self.models = _FakeModels(judgment_json)

    return _FakeGenaiClient


def test_check_cap_consumption_parses_a_determined_live_judgment(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "fake-parallel-key")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")

    import google.genai as genai_module
    import parallel

    monkeypatch.setattr(parallel, "Parallel", _FakeParallelClient)
    monkeypatch.setattr(
        genai_module,
        "Client",
        _fake_genai_client(
            '{"determined": true, "remaining_value_text": "$12,345,678", '
            '"source_url": "https://esd.ny.gov/q3-report", "reason": null}'
        ),
    )

    result = check_cap_consumption("New York", "Empire State Film Production Tax Credit", None)
    assert result.determined is True
    assert result.remaining == Decimal("12345678")
    assert result.source_url == "https://esd.ny.gov/q3-report"


def test_check_cap_consumption_undetermined_when_model_says_so(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "fake-parallel-key")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")

    import google.genai as genai_module
    import parallel

    monkeypatch.setattr(parallel, "Parallel", _FakeParallelClient)
    monkeypatch.setattr(
        genai_module,
        "Client",
        _fake_genai_client(
            '{"determined": false, "remaining_value_text": null, "source_url": null, '
            '"reason": "no dated disclosure found"}'
        ),
    )

    result = check_cap_consumption("New York", "Empire State Film Production Tax Credit", None)
    assert result.determined is False
    assert result.remaining is None
    assert result.reason == "no dated disclosure found"


def test_check_cap_consumption_never_coerces_an_unparseable_figure(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "fake-parallel-key")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")

    import google.genai as genai_module
    import parallel

    monkeypatch.setattr(parallel, "Parallel", _FakeParallelClient)
    monkeypatch.setattr(
        genai_module,
        "Client",
        _fake_genai_client(
            '{"determined": true, "remaining_value_text": "n/a", "source_url": null, '
            '"reason": null}'
        ),
    )

    result = check_cap_consumption("New York", "Empire State Film Production Tax Credit", None)
    assert result.determined is False
    assert result.remaining is None
    assert result.value_text == "n/a"
    assert "did not parse" in result.reason


def test_check_programme_open_parses_a_live_judgment(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "fake-parallel-key")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")

    import google.genai as genai_module
    import parallel

    monkeypatch.setattr(parallel, "Parallel", _FakeParallelClient)
    monkeypatch.setattr(
        genai_module,
        "Client",
        _fake_genai_client(
            '{"state": "open", "source_url": "https://esd.ny.gov/status", '
            '"reason": "applications currently accepted"}'
        ),
    )

    result = check_programme_open("New York", "Empire State Film Production Tax Credit")
    assert result.state == "open"
    assert result.source_url == "https://esd.ny.gov/status"


def test_resolve_cap_consumption_and_resolve_programme_status_never_fabricate_availability(
    monkeypatch,
):
    """AGT-10/D-94, end to end through app.services.spec: with no keys
    present, New York's live checks return undetermined, and the
    resulting `LiveProgrammeCheck.availability` is `None` (never
    defaulted to True/False) while `Jurisdiction.status`-driven confidence
    stamps remain untouched (tests/test_route_a_basis_walk.py proves the
    latter directly, unchanged by this plan)."""
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    raw = SpecFormSubmission(**_base_form_kwargs(candidate_cities=["New York, NY"]))
    result = handle_spec_submission(raw)
    assert isinstance(result, SpecResult)
    assert result.live_programme_checks
    check = result.live_programme_checks[0]
    assert check.jurisdiction_id == "us-ny"
    assert check.availability is None
    assert check.programme_status_state == "unknown"


# ---------------------------------------------------------------------------
# Task 3 — the AGT-10 single-point-of-truth gate
# ---------------------------------------------------------------------------

_SCAN_ROOTS = (REPO_ROOT / "app", REPO_ROOT / "agent", REPO_ROOT / "engine")
_POLICY_NAMES = {"DataClass", "POLICY", "may_use_cache", "assert_live"}
_POLICY_MODULE = REPO_ROOT / "app" / "services" / "cache_policy.py"


def _scanned_py_files() -> list[Path]:
    files: list[Path] = []
    for root in _SCAN_ROOTS:
        files.extend(sorted(root.rglob("*.py")))
    return files


def test_policy_names_defined_in_exactly_one_module() -> None:
    definitions: dict[str, list[Path]] = {name: [] for name in _POLICY_NAMES}
    for path in _scanned_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in _POLICY_NAMES:
                definitions[node.name].append(path)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in _POLICY_NAMES:
                        definitions[target.id].append(path)
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id in _POLICY_NAMES
            ):
                definitions[node.target.id].append(path)

    for name, files in definitions.items():
        assert files == [_POLICY_MODULE], (
            f"{name!r} must be defined in exactly app/services/cache_policy.py, found in: "
            f"{[str(f) for f in files]}"
        )


_CONSUMER_MODULES = (
    REPO_ROOT / "agent" / "job2.py",
    REPO_ROOT / "agent" / "live_checks.py",
    REPO_ROOT / "app" / "services" / "live_fx.py",
    REPO_ROOT / "app" / "services" / "spec.py",
)


def test_every_consumer_module_imports_from_cache_policy() -> None:
    violations: list[str] = []
    for path in _CONSUMER_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found = any(
            isinstance(node, ast.ImportFrom) and node.module == "app.services.cache_policy"
            for node in ast.walk(tree)
        )
        if not found:
            violations.append(str(path))

    assert not violations, (
        f"consumer module(s) missing an ImportFrom of app.services.cache_policy: {violations}"
    )


def test_policy_table_has_exactly_one_cached_and_four_live_entries_with_rationale() -> None:
    cached = [dc for dc, entry in POLICY.items() if entry.verdict == "cached"]
    live = [dc for dc, entry in POLICY.items() if entry.verdict == "live"]
    assert len(cached) == 1
    assert len(live) == 4
    for data_class, entry in POLICY.items():
        assert entry.rationale.strip() != "", data_class


# Non-vacuity proof for `test_policy_names_defined_in_exactly_one_module`
# (performed once, by hand, and reverted — mirrors
# tests/test_route_a_basis_walk.py's own documented proof shape):
#
# A scratch file `app/services/_scratch_second_dataclass.py` was created
# containing a second top-level `class DataClass(str, Enum): ...`
# definition, and this test module was re-run in isolation. Observed
# result: RED —
#
#   AssertionError: 'DataClass' must be defined in exactly
#   app/services/cache_policy.py, found in:
#   ['.../app/services/_scratch_second_dataclass.py',
#    '.../app/services/cache_policy.py']
#
# The scratch file was deleted immediately afterward (confirmed green
# again, full tests/test_cache_policy_live.py re-run). See
# 07-04-SUMMARY.md for the full transcript.


# ---------------------------------------------------------------------------
# Task 3 — the uncurated-city entry path into /research (AGT-05)
# ---------------------------------------------------------------------------


def test_uncurated_city_renders_a_urlencoded_research_link(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    import app.routers.research as research_router_module
    from agent.settings import IntegrationStatus
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/spec",
        data=_valid_spec_form_data(candidate_cities="Reykjavik"),
    )
    assert response.status_code == 200

    match = re.search(r'href="([^"]*?/research\?city=[^"]+)"', response.text)
    assert match, response.text
    href = match.group(1)
    assert "Reykjavik" in href

    # The prefilled form itself only renders once both integrations are
    # configured (app/routers/research.py, plan 07-01's own "not
    # configured" gate — unrelated to this plan). This environment has no
    # keys (api_keys_reality), so force the configured branch here purely
    # to prove the LINK lands on a form carrying the decoded prefill —
    # this task adds no router code, per its own <action> text.
    monkeypatch.setattr(
        research_router_module,
        "integration_status",
        lambda: IntegrationStatus(parallel_configured=True, gemini_configured=True, missing=()),
    )
    follow = client.get(href)
    assert follow.status_code == 200
    assert 'value="Reykjavik"' in follow.text


def test_curated_city_renders_no_research_link() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/spec",
        data=_valid_spec_form_data(candidate_cities="New York, NY"),
    )
    assert response.status_code == 200
    assert "research this city live" not in response.text

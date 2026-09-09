"""AGT-07/D-93/D-94 — Job 2's coercion layer.

`agent/rule_coercion.py` turns Job 2's merged, sourced findings into a
rule document in the CURATED schema. This module proves three things,
mirroring `tests/test_agent_job1_offline.py`'s and
`tests/test_agent_job2_loop.py`'s own AST-gate discipline (a text grep
counts a docstring and is therefore self-invalidating):

1. Round-trip: the emitted document loads through the SAME
   `engine.models.load_ruleset` a curated file goes through, and every
   `Figure` in a priced live-researched run is `confidence: "researched"`,
   never `"validated"` (D-93).
2. The three refusals Task 2 introduces (`pricing_refused`,
   `rule_schema_violation` for both a schema violation and an unparseable
   qualified-spend string) each reach a durable terminal record — never a
   crash, never a fabricated number.
3. The no-fabricated-rate gate: an AST scan of `agent/rule_coercion.py`
   proves no numeric literal is ever assigned to a rate-bearing schema
   key, and the `UNDETERMINED_NEUTRAL_DEFAULTS` table carries no
   rate-bearing entry.

## Non-vacuity (recorded in `07-05-SUMMARY.md`)

The AST gate below (`test_rule_coercion_has_no_rate_literal_dict_values`)
was proven non-vacuous by hand: a literal `"base_rate": 25.0` entry was
temporarily added to a dict literal in `agent/rule_coercion.py`, the gate
was re-run and observed to fail, and the mutation was reverted. See
`07-05-SUMMARY.md` for the exact transcript.
"""

from __future__ import annotations

import ast
import uuid
from decimal import Decimal
from pathlib import Path

import markupsafe
import pytest

from agent import research_runs, rule_coercion
from agent.job2 import TerminalReason, run_job2
from agent.research_schema import (
    FieldFinding,
    JurisdictionIdentity,
    SufficiencyField,
    SufficiencyVerdict,
)
from agent.rule_coercion import (
    RuleCoercionError,
    UnslugableIdentityError,
    build_rule_document,
    cited_source_urls,
    write_rule_file,
)
from engine.models import load_ruleset

REPO_ROOT = Path(__file__).resolve().parents[1]
RULE_COERCION_PATH = REPO_ROOT / "agent" / "rule_coercion.py"

_KEY_VARS = ("PARALLEL_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PRODFIN_GEMINI_MODEL")
_SOURCE_URL = "https://film.testlandia.gov/incentive"

_IDENTITY = JurisdictionIdentity(
    jurisdiction_name="Testlandia",
    country_code="TL",
    level="state",
    currency="USD",
)


@pytest.fixture(autouse=True)
def _no_agent_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _KEY_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _isolated_job2_runs_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test writes into the repo's own `var/job2/` — both the JSON run
    record path (`agent.research_runs.RESEARCH_RUNS_DIR`) and the ruleset
    YAML path (`agent.rule_coercion.RESEARCH_RUNS_DIR` — a SEPARATE
    binding, since `rule_coercion.py` did `from agent.research_runs
    import RESEARCH_RUNS_DIR`) are redirected to `tmp_path`."""
    monkeypatch.setattr(research_runs, "RESEARCH_RUNS_DIR", tmp_path)
    monkeypatch.setattr(rule_coercion, "RESEARCH_RUNS_DIR", tmp_path)


def _job_id() -> str:
    return uuid.uuid4().hex


def _finding(
    field: SufficiencyField, value_text: str, source_url: str | None = _SOURCE_URL
) -> FieldFinding:
    return FieldFinding(field=field, determined=True, value_text=value_text, source_url=source_url)


def _refundable_findings() -> dict[SufficiencyField, FieldFinding]:
    return {
        SufficiencyField.rate: _finding(
            SufficiencyField.rate, "A 20% rebate applies to qualifying spend."
        ),
        SufficiencyField.qualifying_base_definition: _finding(
            SufficiencyField.qualifying_base_definition,
            "The credit is based on total qualified production spend within the jurisdiction.",
        ),
        SufficiencyField.caps: _finding(
            SufficiencyField.caps, "The programme has an annual programme cap of $50 million."
        ),
        SufficiencyField.payout_mechanism: _finding(
            SufficiencyField.payout_mechanism,
            "This is a refundable tax credit, paid within 120 days of certification.",
        ),
        SufficiencyField.current_availability: _finding(
            SufficiencyField.current_availability,
            "The programme is currently active and accepting applications for the 2026 tax year.",
        ),
    }


def _transferable_findings() -> dict[SufficiencyField, FieldFinding]:
    findings = _refundable_findings()
    findings[SufficiencyField.payout_mechanism] = _finding(
        SufficiencyField.payout_mechanism,
        "This credit is transferable and may be sold to a third-party taxpayer.",
    )
    return findings


def _scripted_seams_for(
    findings_map: dict[SufficiencyField, FieldFinding], decision: str = "sufficient"
):
    def _search_fn(**kwargs):
        return [
            {"url": _SOURCE_URL, "title": "Example incentive programme", "excerpts": ["evidence"]}
        ]

    def _judge_fn(**kwargs):
        return SufficiencyVerdict(
            decision=decision,
            findings=list(findings_map.values()),
            identity=_IDENTITY,
            summary="round 1: sufficient",
        )

    return _search_fn, _judge_fn


# ---------------------------------------------------------------------------
# Task 1: findings -> a document -> the curated loader (round-trip + defaults)
# ---------------------------------------------------------------------------


def test_build_rule_document_round_trips_through_load_ruleset():
    findings = _refundable_findings()
    sources = cited_source_urls(findings)
    document = build_rule_document(_job_id(), _IDENTITY, findings, sources)

    path = write_rule_file(_job_id(), document)
    ruleset = load_ruleset(path)

    assert ruleset.jurisdiction.status == "live_researched"
    assert ruleset.jurisdiction.id == "testlandia"
    assert ruleset.jurisdiction.name == "Testlandia"
    assert ruleset.jurisdiction.sources[0].confidence == "MEDIUM"  # .gov host
    programme = ruleset.programmes[0]
    assert programme.mechanism == "refundable"
    assert programme.rate_structure.base_rate == Decimal("0.20")
    assert programme.base_definition.type == "total_qualified_spend"
    assert programme.caps.annual_programme_cap.amount.value == Decimal("50000000")
    assert programme.timing.payout_lag.typical_days == 120
    assert programme.validation.validated is False


def test_document_matches_the_curated_shape_key_for_key():
    """Manual read parity with `jurisdictions/us-ny.yaml`'s own top-level
    shape (per this plan's own verification instruction)."""
    findings = _refundable_findings()
    document = build_rule_document(_job_id(), _IDENTITY, findings, cited_source_urls(findings))
    assert set(document.keys()) == {"jurisdiction", "programmes"}
    assert set(document["jurisdiction"].keys()) >= {
        "id",
        "name",
        "country_code",
        "level",
        "currency",
        "status",
        "effective_dates",
        "sources",
    }


def test_apply_neutral_defaults_with_full_overrides_returns_no_disclosures():
    overrides = {
        "programme.taxable": True,
        "programme.audit.mandatory": True,
        "programme.per_person_ceiling.applies": True,
        "programme.timing.terms_lock_at": "application",
    }
    values, disclosures = rule_coercion.apply_neutral_defaults(overrides)
    assert disclosures == []
    assert values == overrides


def test_apply_neutral_defaults_with_no_overrides_discloses_every_entry():
    values, disclosures = rule_coercion.apply_neutral_defaults(None)
    assert len(disclosures) == len(rule_coercion.UNDETERMINED_NEUTRAL_DEFAULTS)
    assert values["programme.taxable"] is False
    assert values["programme.audit.mandatory"] is False


def test_undetermined_neutral_defaults_has_no_rate_bearing_entry():
    for path in rule_coercion.UNDETERMINED_NEUTRAL_DEFAULTS:
        leaf = path.rsplit(".", 1)[-1]
        assert leaf not in rule_coercion.RATE_BEARING_SCHEMA_KEYS, (
            f"{path!r} defaults a rate-bearing field — forbidden by D-94"
        )


def test_source_confidence_is_medium_for_a_gov_host_and_low_otherwise():
    assert rule_coercion._source_confidence_for_url("https://film.testlandia.gov/x") == "MEDIUM"
    assert rule_coercion._source_confidence_for_url("https://example.com/x") == "LOW"
    assert rule_coercion._source_confidence_for_url("https://example.com/x") != "HIGH"


def test_build_rule_document_refuses_an_ambiguous_multi_rate_finding():
    findings = _refundable_findings()
    findings[SufficiencyField.rate] = _finding(
        SufficiencyField.rate, "20% applies up to $1 million, then 25% above that threshold."
    )
    with pytest.raises(RuleCoercionError):
        build_rule_document(_job_id(), _IDENTITY, findings, cited_source_urls(findings))


def test_build_rule_document_refuses_an_unclassifiable_base_definition():
    findings = _refundable_findings()
    findings[SufficiencyField.qualifying_base_definition] = _finding(
        SufficiencyField.qualifying_base_definition, "Something indeterminate about the base."
    )
    with pytest.raises(RuleCoercionError):
        build_rule_document(_job_id(), _IDENTITY, findings, cited_source_urls(findings))


def test_build_rule_document_refuses_caps_text_with_no_extractable_amount_and_not_uncapped():
    findings = _refundable_findings()
    findings[SufficiencyField.caps] = _finding(SufficiencyField.caps, "Capped at some amount, TBD.")
    with pytest.raises(RuleCoercionError):
        build_rule_document(_job_id(), _IDENTITY, findings, cited_source_urls(findings))


def test_build_rule_document_accepts_an_explicitly_uncapped_programme_without_inventing_a_figure():
    findings = _refundable_findings()
    findings[SufficiencyField.caps] = _finding(SufficiencyField.caps, "The programme is uncapped.")
    document = build_rule_document(_job_id(), _IDENTITY, findings, cited_source_urls(findings))
    caps = document["programmes"][0]["caps"]
    assert caps["per_project_cap"] is None
    assert caps["annual_programme_cap"] is None


def test_build_rule_document_refuses_an_unslugable_jurisdiction_name():
    identity = JurisdictionIdentity(
        jurisdiction_name="!!!", country_code="TL", level="state", currency="USD"
    )
    findings = _refundable_findings()
    with pytest.raises(UnslugableIdentityError):
        build_rule_document(_job_id(), identity, findings, cited_source_urls(findings))


def test_build_rule_document_refuses_zero_cited_sources():
    findings = {f: _finding(f, "some value", source_url=None) for f in SufficiencyField}
    with pytest.raises(RuleCoercionError):
        build_rule_document(_job_id(), _IDENTITY, findings, [])


def test_write_rule_file_refuses_an_invalid_job_id():
    document = build_rule_document(
        _job_id(), _IDENTITY, _refundable_findings(), cited_source_urls(_refundable_findings())
    )
    with pytest.raises(RuleCoercionError):
        write_rule_file("not-a-valid-job-id", document)


# ---------------------------------------------------------------------------
# Task 2: refuse rather than derive — the engine's own refusals become
# terminal states, never a crash.
# ---------------------------------------------------------------------------


def test_sufficient_run_with_spend_input_is_priced_through_price_jurisdiction():
    search_fn, judge_fn = _scripted_seams_for(_refundable_findings())
    run = run_job2(
        "Testlandia", "$1,000,000", job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn
    )

    assert run.terminal_reason == TerminalReason.sufficient.value
    assert run.ruleset_path is not None
    assert run.priced is not None
    assert run.priced["total_net_cash"]["confidence"] == "researched"
    assert Decimal(run.priced["total_net_cash"]["value"]) > 0


def test_sufficient_run_with_no_spend_input_writes_the_ruleset_but_skips_pricing():
    search_fn, judge_fn = _scripted_seams_for(_refundable_findings())
    run = run_job2("Testlandia", None, job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn)

    assert run.terminal_reason == TerminalReason.sufficient.value
    assert run.ruleset_path is not None
    assert run.priced is None


def test_transferable_with_no_discount_range_ends_in_pricing_refused():
    search_fn, judge_fn = _scripted_seams_for(_transferable_findings())
    run = run_job2(
        "Testlandia", "$1,000,000", job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn
    )

    assert run.terminal_reason == TerminalReason.pricing_refused.value
    assert run.ruleset_path is not None
    assert run.priced is None
    assert "transfer" in (run.message or "").lower()


def test_unparseable_qualified_spend_ends_in_rule_schema_violation_never_coerced_to_a_number():
    search_fn, judge_fn = _scripted_seams_for(_refundable_findings())
    run = run_job2(
        "Testlandia", "not a number", job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn
    )

    assert run.terminal_reason == TerminalReason.rule_schema_violation.value
    assert "not a number" in (run.message or "")
    assert run.priced is None
    # the ruleset itself is fine — only the spend string was refused
    assert run.ruleset_path is not None


def test_ambiguous_rate_ends_in_rule_schema_violation_with_no_ruleset_written():
    findings = _refundable_findings()
    findings[SufficiencyField.rate] = _finding(
        SufficiencyField.rate, "20% applies up to $1 million, then 25% above."
    )
    search_fn, judge_fn = _scripted_seams_for(findings)
    job_id = _job_id()
    run = run_job2(
        "Testlandia", "$1,000,000", job_id=job_id, search_fn=search_fn, judge_fn=judge_fn
    )

    assert run.terminal_reason == TerminalReason.rule_schema_violation.value
    assert run.ruleset_path is None
    assert run.priced is None
    assert not (research_runs.RESEARCH_RUNS_DIR / f"{job_id}.ruleset.yaml").exists()


def test_a_document_that_fails_schema_validation_reports_the_validation_error_text(monkeypatch):
    """Forces the `load_ruleset` branch specifically: patch
    `build_rule_document` to emit a document with an out-of-vocabulary
    classification value, which `JurisdictionRuleSet` rejects at load."""
    import agent.job2 as job2_module

    def _broken_build_rule_document(job_id, identity, merged, sources):
        document = build_rule_document(job_id, identity, merged, sources)
        document["jurisdiction"]["level"] = "not-a-real-level"
        return document

    # agent/job2.py did `from agent.rule_coercion import build_rule_document`,
    # binding its OWN name in job2's namespace — patching rule_coercion's
    # copy would not affect job2's already-bound reference.
    monkeypatch.setattr(job2_module, "build_rule_document", _broken_build_rule_document)
    search_fn, judge_fn = _scripted_seams_for(_refundable_findings())
    run = job2_module.run_job2(
        "Testlandia", "$1,000,000", job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn
    )
    assert run.terminal_reason == TerminalReason.rule_schema_violation.value
    assert run.priced is None


def test_no_programme_found_still_writes_no_ruleset_file():
    def _search_fn(**kwargs):
        return [{"url": _SOURCE_URL, "title": "Example", "excerpts": []}]

    def _judge_fn(**kwargs):
        return SufficiencyVerdict(decision="no_programme_found", summary="nothing found")

    job_id = _job_id()
    run = run_job2("Testlandia", None, job_id=job_id, search_fn=_search_fn, judge_fn=_judge_fn)

    assert run.terminal_reason == TerminalReason.no_programme_found.value
    assert run.ruleset_path is None
    assert run.priced is None
    assert not (research_runs.RESEARCH_RUNS_DIR / f"{job_id}.ruleset.yaml").exists()


# ---------------------------------------------------------------------------
# Task 3: labelled unvalidated, and the no-fabricated-rate gate.
# ---------------------------------------------------------------------------


def _walk_priced_node(node: dict) -> list[dict]:
    visited = [node]
    for child in node.get("inputs", []):
        visited.extend(_walk_priced_node(child))
    return visited


def test_every_figure_in_a_sufficient_priced_run_is_researched_never_validated():
    search_fn, judge_fn = _scripted_seams_for(_refundable_findings())
    run = run_job2(
        "Testlandia", "$1,000,000", job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn
    )
    assert run.priced is not None

    all_nodes: list[dict] = []
    all_nodes.extend(_walk_priced_node(run.priced["total_net_cash"]))
    for pp in run.priced["programmes"]:
        all_nodes.extend(_walk_priced_node(pp["qualifying_base"]))
        all_nodes.extend(_walk_priced_node(pp["gross_credit"]))
        all_nodes.extend(_walk_priced_node(pp["net_cash"]["low"]))
        all_nodes.extend(_walk_priced_node(pp["net_cash"]["high"]))
        if pp["net_cash"]["point"] is not None:
            all_nodes.extend(_walk_priced_node(pp["net_cash"]["point"]))

    assert len(all_nodes) >= 3, "walk visited too few nodes to be a meaningful non-vacuity proof"
    validated_nodes = [n for n in all_nodes if n["confidence"] == "validated"]
    assert not validated_nodes, (
        f"found a 'validated'-confidence node in a live-researched priced tree: "
        f"{[n['label'] for n in validated_nodes]!r} — D-93 requires every node to be, at "
        "most, 'researched'"
    )


def test_source_confidence_is_never_conflated_with_figure_confidence():
    """RD-02/D-58: `Source.confidence` (four-tier) and `Figure.confidence`
    (two-value) are never the same axis. A MEDIUM-confidence source still
    yields a `researched` (never `validated`, never `MEDIUM`) Figure."""
    search_fn, judge_fn = _scripted_seams_for(_refundable_findings())
    run = run_job2(
        "Testlandia", "$1,000,000", job_id=_job_id(), search_fn=search_fn, judge_fn=judge_fn
    )
    assert run.priced is not None
    assert run.priced["total_net_cash"]["confidence"] in ("validated", "researched")
    assert run.priced["total_net_cash"]["confidence"] == "researched"
    assert run.priced["total_net_cash"]["confidence"] != "MEDIUM"


def test_disclosure_sentences_and_unvalidated_banner_render_on_the_page():
    from fastapi.testclient import TestClient

    from app.main import app

    search_fn, judge_fn = _scripted_seams_for(_refundable_findings())
    job_id = _job_id()
    run_job2("Testlandia", "$1,000,000", job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    with TestClient(app) as client:
        response = client.get(f"/research/{job_id}")

    assert response.status_code == 200
    body = response.text
    assert "researched" in body.lower()
    assert "has not been checked against a" in body.lower() or "not validated" in body.lower()
    for disclosure in rule_coercion.neutral_default_disclosures(_refundable_findings()):
        # Jinja autoescapes an apostrophe to `&#39;` — compare against the
        # same HTML-escaped form the template actually renders.
        assert markupsafe.escape(disclosure) in body


def test_pricing_refused_page_states_the_refusal_plainly():
    from fastapi.testclient import TestClient

    from app.main import app

    search_fn, judge_fn = _scripted_seams_for(_transferable_findings())
    job_id = _job_id()
    run_job2("Testlandia", "$1,000,000", job_id=job_id, search_fn=search_fn, judge_fn=judge_fn)

    with TestClient(app) as client:
        response = client.get(f"/research/{job_id}")

    assert response.status_code == 200
    body = response.text
    assert "cannot be computed" in body.lower()
    assert "transfer" in body.lower()


def _is_numeric_constant(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    )


def _dict_rate_literal_violations(tree: ast.Module, filename: str) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key_node, value_node in zip(node.keys, node.values, strict=False):
            if (
                isinstance(key_node, ast.Constant)
                and isinstance(key_node.value, str)
                and key_node.value in rule_coercion.RATE_BEARING_SCHEMA_KEYS
                and _is_numeric_constant(value_node)
            ):
                violations.append(
                    f"{filename}:{value_node.lineno}: {key_node.value!r} = {value_node.value!r}"
                )
    return violations


def test_rule_coercion_has_no_rate_literal_dict_values():
    """D-94's no-fabricated-rate gate over `agent/rule_coercion.py`
    specifically: no numeric literal is ever assigned to a rate-bearing
    schema key anywhere in this file. Non-vacuity proven by hand — see
    the module docstring."""
    tree = ast.parse(
        RULE_COERCION_PATH.read_text(encoding="utf-8"), filename=str(RULE_COERCION_PATH)
    )
    violations = _dict_rate_literal_violations(tree, RULE_COERCION_PATH.name)
    assert not violations, "rate-bearing literal found in agent/rule_coercion.py:\n" + "\n".join(
        violations
    )

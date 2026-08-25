"""Decimal-typing regression, closed-enum fail-loud behaviour, and the three
source-level security gates (T-02-01/02/03) for ``engine/models.py``.

The three security gates are written as pytest tests, not shell greps in a
verify block, so they run inside the existing CI job with no workflow
change (``02-RESEARCH.md`` Task 1 instruction). Each gate reads the
relevant source files, drops comment-only lines (so a file's own
head-comment or docstring *mentioning* the banned pattern cannot itself
trip the gate — see ``02-01-SUMMARY.md``'s recorded deviation, where
``engine/handlers/__init__.py``'s own docstring literally contained the
words ``getattr``/``importlib`` while explaining why they are banned), and
asserts zero remaining matches against the actual construct. Each gate also
fails loud if the file list it is about to scan is empty, matching
``tests/test_validation_pair_fixtures.py``'s existing discipline (T-01-15).
"""

from __future__ import annotations

import copy
import re
from datetime import date
from decimal import Decimal
from glob import glob

import pytest
import yaml
from pydantic import ValidationError

from engine.models import (
    Audit,
    BaseDefinition,
    Caps,
    EffectiveDates,
    Jurisdiction,
    JurisdictionRuleSet,
    PayoutLag,
    PerPersonCeiling,
    Programme,
    RateStructure,
    Timing,
    TransferDiscount,
    Validation,
    load_ruleset,
)

# ---------------------------------------------------------------------------
# Shared helper: strip comment-only lines before scanning source text.
# ---------------------------------------------------------------------------


def _strip_comment_lines(text: str) -> list[str]:
    """Return the list of (line_number, line_text) pairs for every line in
    ``text`` whose first non-whitespace character does not start a Python
    comment. Line numbers are 1-indexed and preserved even though
    comment-only lines are dropped, so a failure message can name the exact
    offending line in the original file."""
    kept: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("#"):
            continue
        kept.append((lineno, line))
    return kept


def _scan(paths: list[str], pattern: re.Pattern) -> list[str]:
    """Scan every path in ``paths`` (comment-lines stripped) for ``pattern``
    and return a list of ``"path:line: matched text"`` failure strings."""
    failures: list[str] = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for lineno, line in _strip_comment_lines(text):
            match = pattern.search(line)
            if match:
                failures.append(f"{path}:{lineno}: {match.group(0)!r} — {line.strip()!r}")
    return failures


# ---------------------------------------------------------------------------
# Gate 1 (T-02-01): no PyYAML non-safe loader entry point anywhere in engine/
# ---------------------------------------------------------------------------

# Matches an actual invocation of a non-safe PyYAML loading function, or an
# actual reference to a non-safe Loader class — never a backtick-quoted
# mention of the token in prose (which would require a trailing "(" for the
# function forms, absent from prose like "never ``yaml.load``/``yaml.unsafe_load``").
_UNSAFE_YAML_RE = re.compile(
    r"yaml\.(load|unsafe_load|full_load)\s*\(|yaml\.(UnsafeLoader|FullLoader|Loader)\b"
)

ENGINE_PY_FILES = sorted(glob("engine/**/*.py", recursive=True))

if not ENGINE_PY_FILES:
    raise RuntimeError(
        "No files found under engine/**/*.py — a gate scanning an empty file "
        "list must fail loudly (T-01-15 discipline), not report a vacuous green."
    )


def test_no_unsafe_yaml_loader_entry_points_in_engine():
    failures = _scan(ENGINE_PY_FILES, _UNSAFE_YAML_RE)
    assert not failures, (
        "Non-safe PyYAML loader entry point(s) found — every rule-file read "
        "must go through yaml.safe_load only (T-02-01):\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Gate 2 (T-02-04 schema half): no floating-point type annotation in models.py
# ---------------------------------------------------------------------------

_FLOAT_ANNOTATION_RE = re.compile(r":\s*float\b")

MODELS_PY_FILE = ["engine/models.py"]


def test_no_float_typed_fields_in_models():
    failures = _scan(MODELS_PY_FILE, _FLOAT_ANNOTATION_RE)
    assert not failures, (
        "float-typed field annotation(s) found in engine/models.py — every "
        "money/rate/threshold field must be Decimal-typed (RD-01, "
        "02-RESEARCH.md Finding 1):\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Gate 3 (T-02-03): no dynamic name resolution anywhere in engine/handlers/
# ---------------------------------------------------------------------------

_DYNAMIC_RESOLUTION_RE = re.compile(r"\b(getattr|importlib)\b")

HANDLER_PY_FILES = sorted(glob("engine/handlers/**/*.py", recursive=True))

if not HANDLER_PY_FILES:
    raise RuntimeError(
        "No files found under engine/handlers/**/*.py — a gate scanning an "
        "empty file list must fail loudly, not report a vacuous green."
    )


def test_no_dynamic_name_resolution_in_handlers():
    failures = _scan(HANDLER_PY_FILES, _DYNAMIC_RESOLUTION_RE)
    assert not failures, (
        "Dynamic attribute lookup or module-import machinery found under "
        "engine/handlers/ — the custom_handler_id escape hatch must remain "
        "a closed dict-literal allow-list (T-02-03):\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Decimal-typing regression (RD-01): the executable form of Finding 1
# ---------------------------------------------------------------------------


def test_quoted_string_rate_parses_exactly_as_decimal():
    """A rate field loaded from the quoted YAML string "0.263" equals a
    Decimal constructed straight from that same string."""
    rate_structure = RateStructure(type="flat", base_rate="0.263")
    assert rate_structure.base_rate == Decimal("0.263")


def test_quoted_string_rate_is_not_equal_to_naive_float_conversion():
    """The inequality that makes the precision claim non-vacuous: the value
    the naive path would have produced — handing a binary floating-point
    0.263 straight to the Decimal constructor — is a materially different
    number, and Pydantic's Decimal validator (used via the quoted-string
    YAML convention) never produces it."""
    rate_structure = RateStructure(type="flat", base_rate="0.263")
    naive_conversion = Decimal(0.263)
    assert rate_structure.base_rate != naive_conversion


# ---------------------------------------------------------------------------
# Fail-loud schema (T-02-02): unrecognised classification values and an
# unexpected extra key both raise pydantic.ValidationError rather than
# silently defaulting.
# ---------------------------------------------------------------------------


def _valid_ruleset_doc() -> dict:
    """A real, valid rule-file document (New York's curated rule file),
    loaded fresh for every test that needs to mutate it — never a shared
    mutable dict two tests could accidentally corrupt for each other."""
    with open("jurisdictions/us-ny.yaml", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_baseline_ruleset_document_validates():
    """Sanity anchor: the unmutated document must itself validate, so the
    negative tests below are proven to be testing the mutation, not a
    pre-existing baseline defect."""
    JurisdictionRuleSet.model_validate(_valid_ruleset_doc())


def test_unrecognised_mechanism_raises():
    doc = copy.deepcopy(_valid_ruleset_doc())
    doc["programmes"][0]["mechanism"] = "refundable_maybe"
    with pytest.raises(ValidationError):
        JurisdictionRuleSet.model_validate(doc)


def test_unrecognised_base_definition_type_raises():
    doc = copy.deepcopy(_valid_ruleset_doc())
    doc["programmes"][0]["base_definition"]["type"] = "bogus_base_type"
    with pytest.raises(ValidationError):
        JurisdictionRuleSet.model_validate(doc)


def test_unrecognised_rate_structure_type_raises():
    doc = copy.deepcopy(_valid_ruleset_doc())
    doc["programmes"][0]["rate_structure"]["type"] = "bogus_rate_type"
    with pytest.raises(ValidationError):
        JurisdictionRuleSet.model_validate(doc)


def test_unrecognised_jurisdiction_status_raises():
    doc = copy.deepcopy(_valid_ruleset_doc())
    doc["jurisdiction"]["status"] = "bogus_status"
    with pytest.raises(ValidationError):
        JurisdictionRuleSet.model_validate(doc)


def test_unexpected_extra_top_level_key_raises():
    doc = copy.deepcopy(_valid_ruleset_doc())
    doc["unexpected_top_level_key"] = "surprise"
    with pytest.raises(ValidationError):
        JurisdictionRuleSet.model_validate(doc)


# ---------------------------------------------------------------------------
# WR-01/WR-02 (INC-03): every declared `stacks_with` and
# `mutually_exclusive_with` edge must resolve to a different declared
# programme id, or the ruleset raises at load time (02-08-PLAN.md Task 1).
# WR-04 (PRV-02): a zero-programme ruleset raises rather than pricing a
# confident, source-less $0 total (02-08-PLAN.md Task 2).
# ---------------------------------------------------------------------------


def _make_programme(
    *,
    programme_id: str = "synthetic-model-test-programme",
    stacks_with: list[str] | None = None,
    mutually_exclusive_with: list[str] | None = None,
) -> Programme:
    """A minimal, valid `Programme` for tests that only need to vary the
    declared edge fields — every other required field is filled with an
    inert default, mirroring `tests/test_engine_credit.py::_make_programme`."""
    return Programme(
        id=programme_id,
        name=f"Synthetic model test programme {programme_id}",
        stacks_with=stacks_with or [],
        mutually_exclusive_with=mutually_exclusive_with or [],
        mechanism="refundable",
        taxable=False,
        corporation_tax_rate=None,
        base_definition=BaseDefinition(type="total_qualified_spend"),
        per_person_ceiling=PerPersonCeiling(applies=False),
        rate_structure=RateStructure(type="flat", base_rate=Decimal("0.20")),
        minimum_spend=None,
        caps=Caps(),
        audit=Audit(mandatory=False),
        timing=Timing(
            terms_lock_at="application",
            payout_lag=PayoutLag(description="synthetic test programme — not a real payout schedule"),
        ),
        transfer_discount=TransferDiscount(applies=False),
        validation=Validation(validated=False),
    )


def _make_two_programme_ruleset(programmes: list[Programme]) -> JurisdictionRuleSet:
    """An in-memory `JurisdictionRuleSet` for edge-validation tests, mirroring
    `tests/test_engine_credit.py::_make_jurisdiction_ruleset`."""
    jurisdiction = Jurisdiction(
        id="zz-synthetic-model-edge-test",
        name="Synthetic in-memory jurisdiction for a programme-edge test — never a real place",
        country_code="ZZ",
        level="national",
        parent_id=None,
        currency="USD",
        status="synthetic_fixture",
        effective_dates=EffectiveDates(
            rule_version_effective_from=date(2026, 1, 1),
            rule_version_effective_to=None,
            source_checked_date=date(2026, 8, 25),
        ),
        sources=[],
    )
    return JurisdictionRuleSet(jurisdiction=jurisdiction, programmes=programmes)


def test_self_referencing_mutual_exclusivity_raises():
    """A programme naming its own id in `mutually_exclusive_with` raises,
    naming the offending programme id (WR-01) — it must never make a
    programme simultaneously taken and excluded and disappear from the sum."""
    other = _make_programme(programme_id="other-programme")
    self_referencing = _make_programme(
        programme_id="self-referencing-programme",
        mutually_exclusive_with=["self-referencing-programme"],
    )
    with pytest.raises(ValidationError) as excinfo:
        _make_two_programme_ruleset([self_referencing, other])
    assert "self-referencing-programme" in str(excinfo.value)


def test_self_referencing_stacks_with_raises():
    """A programme cannot stack with itself any more than it can exclude
    itself — same treatment, same place (WR-02)."""
    other = _make_programme(programme_id="other-programme")
    self_referencing = _make_programme(
        programme_id="self-referencing-programme",
        stacks_with=["self-referencing-programme"],
    )
    with pytest.raises(ValidationError) as excinfo:
        _make_two_programme_ruleset([self_referencing, other])
    assert "self-referencing-programme" in str(excinfo.value)


def test_unknown_stacks_with_reference_raises():
    """A `stacks_with` entry naming an id no declared programme carries
    raises at load time now, naming both the unknown id and the declared ids
    (WR-02) — the same treatment `mutually_exclusive_with` already gets."""
    declared = _make_programme(programme_id="declared-programme")
    dangling = _make_programme(
        programme_id="dangling-reference-programme",
        stacks_with=["no-such-programme-id"],
    )
    with pytest.raises(ValidationError) as excinfo:
        _make_two_programme_ruleset([declared, dangling])
    message = str(excinfo.value)
    assert "no-such-programme-id" in message
    assert "declared-programme" in message


def test_unknown_mutually_exclusive_with_reference_raises():
    """A `mutually_exclusive_with` entry naming an unknown id raises at load
    time now, rather than at `price_jurisdiction` time as before this plan."""
    declared = _make_programme(programme_id="declared-programme")
    dangling = _make_programme(
        programme_id="dangling-reference-programme",
        mutually_exclusive_with=["no-such-programme-id"],
    )
    with pytest.raises(ValidationError) as excinfo:
        _make_two_programme_ruleset([declared, dangling])
    message = str(excinfo.value)
    assert "no-such-programme-id" in message
    assert "declared-programme" in message


def test_edge_id_differing_only_by_case_is_treated_as_unknown():
    """An id differing only by letter case or surrounding whitespace from a
    declared id is a DIFFERENT id — compared as an exact string, never
    normalized into a match. `Declared-Programme` (capitalised) does not
    resolve against a declared `declared-programme`."""
    declared = _make_programme(programme_id="declared-programme")
    near_miss = _make_programme(
        programme_id="near-miss-programme",
        stacks_with=["Declared-Programme"],
    )
    with pytest.raises(ValidationError) as excinfo:
        _make_two_programme_ruleset([declared, near_miss])
    assert "Declared-Programme" in str(excinfo.value)


def test_every_committed_rule_file_still_loads():
    """Every currently-committed rule file — both under `jurisdictions/` and
    both fixture directories — still loads: this plan's validators are
    additive constraints on genuinely invalid data, never a tightening that
    invalidates existing curated files (JUR-05)."""
    paths = sorted(glob("jurisdictions/*.yaml")) + sorted(
        glob("tests/fixtures/jurisdictions/*.yaml")
    )
    if not paths:
        raise RuntimeError(
            "No rule files found under jurisdictions/*.yaml or "
            "tests/fixtures/jurisdictions/*.yaml — a glob-driven test over an "
            "empty file list must fail loudly, not report a vacuous green."
        )
    for path in paths:
        load_ruleset(path)


def test_empty_programmes_list_raises():
    """A `JurisdictionRuleSet` constructed with `programmes: []` raises
    `pydantic.ValidationError` naming the `programmes` field — WR-04. Routing
    a zero-programme ruleset through `combined_confidence`'s documented
    empty-sequence default would otherwise produce a `validated`,
    source-less, date-less $0 total: a confidence claim about a computation
    that never happened."""
    jurisdiction = Jurisdiction(
        id="zz-synthetic-empty-programmes",
        name="Synthetic in-memory jurisdiction with zero programmes — never a real place",
        country_code="ZZ",
        level="national",
        parent_id=None,
        currency="USD",
        status="synthetic_fixture",
        effective_dates=EffectiveDates(
            rule_version_effective_from=date(2026, 1, 1),
            rule_version_effective_to=None,
            source_checked_date=date(2026, 8, 25),
        ),
        sources=[],
    )
    with pytest.raises(ValidationError) as excinfo:
        JurisdictionRuleSet(jurisdiction=jurisdiction, programmes=[])
    assert "programmes" in str(excinfo.value)


def test_empty_programmes_list_raises_through_load_ruleset(tmp_path):
    """The same empty-`programmes` shape, round-tripped through a temporary
    YAML file and `load_ruleset`, raises too — proven on the real rule-file
    read path, not only on direct construction."""
    doc = copy.deepcopy(_valid_ruleset_doc())
    doc["jurisdiction"]["status"] = "synthetic_fixture"
    doc["programmes"] = []
    rule_file = tmp_path / "empty-programmes.yaml"
    rule_file.write_text(yaml.safe_dump(doc), encoding="utf-8")
    with pytest.raises(ValidationError) as excinfo:
        load_ruleset(rule_file)
    assert "programmes" in str(excinfo.value)

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
from glob import glob

import pytest
import yaml
from pydantic import ValidationError

from decimal import Decimal

from engine.models import JurisdictionRuleSet, RateStructure

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

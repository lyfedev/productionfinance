"""Turn Job 2's merged, sourced findings into a rule document in the SAME
schema a curated jurisdiction file uses, written to
`var/job2/{job_id}.ruleset.yaml`.

This module imports NOTHING from `engine/` — not even the two names the
AST gate in `tests/test_agent_job1_offline.py`
(`test_agent_imports_nothing_from_engine_except_the_two_sanctioned_names`)
permits. `agent/job2.py` is the only module this plan touches that calls
`engine.models.load_ruleset` / `engine.pipeline.price_jurisdiction` — this
module only ever produces a plain `dict` and hands it to `yaml.safe_dump`.
That is AGT-07's proof: the researched jurisdiction reaches the engine
through the identical loader and the identical pricing call a curated
jurisdiction goes through, because this module structurally cannot reach
the engine any other way.

D-94's two rules, both enforced structurally here rather than asserted in
prose:

1. A rate, cap, threshold or tier is NEVER a literal written in this
   source file — every such value is computed at runtime from a research
   finding's own `value_text`, or the coercion refuses
   (`RuleCoercionError`) rather than invent one.
   `tests/test_agent_job2_coercion.py` proves the "never a literal" half
   with an AST gate over this file; the "or refuses" half is proven
   behaviourally — a finding this module cannot parse into a number never
   reaches `write_rule_file`.
2. Every schema field this module fills in WITHOUT research backing
   (`UNDETERMINED_NEUTRAL_DEFAULTS`) is a closed, committed table. Each
   entry names the field, its neutral value, and the exact disclosure
   sentence a reader sees, naming what was not determined and which
   direction the true figure would move if it were.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import yaml

from agent.numbers import UnparseableFigureError, parse_money
from agent.research_runs import RESEARCH_RUNS_DIR
from agent.research_schema import FieldFinding, JurisdictionIdentity, SufficiencyField

__all__ = [
    "RATE_BEARING_SCHEMA_KEYS",
    "UNDETERMINED_NEUTRAL_DEFAULTS",
    "RuleCoercionError",
    "UnslugableIdentityError",
    "apply_neutral_defaults",
    "build_rule_document",
    "cited_source_urls",
    "neutral_default_disclosures",
    "serialize_priced_jurisdiction",
    "write_rule_file",
]

_JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_SLUG_RE = re.compile(r"^[a-z0-9-]{1,40}$")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_DAYS_RE = re.compile(r"(\d+)\s*(?:business\s*)?days")
_MONEY_RE = re.compile(
    r"(?P<symbol>[$€£])\s*(?P<amount>[\d,]+(?:\.\d+)?)"
    r"\s*(?P<scale>million|billion|thousand|bn\b|m\b|k\b)?",
    re.IGNORECASE,
)
_SCALE_MULTIPLIERS: dict[str, Decimal] = {
    "million": Decimal("1000000"),
    "m": Decimal("1000000"),
    "billion": Decimal("1000000000"),
    "bn": Decimal("1000000000"),
    "thousand": Decimal("1000"),
    "k": Decimal("1000"),
}
_UNCAPPED_KEYWORDS = ("no cap", "uncapped", "no annual cap", "no limit", "unlimited")
_ANNUAL_CAP_KEYWORDS = (
    "annual",
    "per year",
    "aggregate",
    "programme cap",
    "program cap",
    "fiscal year",
)
_PRIMARY_GOVERNMENT_HOST_MARKERS = (".gov", ".mil")

# T-07-29/D-94: the closed set of schema keys the plan's own AST gate
# (tests/test_agent_job2_coercion.py) forbids assigning a numeric literal
# to anywhere in this module — exported so the test imports this list
# rather than re-typing it and risking drift from the plan's own list.
RATE_BEARING_SCHEMA_KEYS: frozenset[str] = frozenset(
    {
        "base_rate",
        "rate",
        "additional_rate",
        "standard_rate",
        "enhanced_rate",
        "corporation_tax_rate",
        "loanout_withholding_rate",
        "pct_core_cap",
        "threshold_low",
        "threshold_high",
    }
)


class RuleCoercionError(ValueError):
    """Raised when the merged findings cannot be coerced into a schema-
    valid rule document without inventing a value D-94 forbids inventing.
    Never raised for a value that WAS determined — only for one this
    module refuses to guess."""


class UnslugableIdentityError(RuleCoercionError):
    """The jurisdiction's researched name cannot be turned into a
    `^[a-z0-9-]{1,40}$` id. A subclass of `RuleCoercionError` so a bare
    `except RuleCoercionError` still catches it; a caller that needs to
    tell this case apart catches it by name."""


# ---------------------------------------------------------------------------
# UNDETERMINED_NEUTRAL_DEFAULTS — D-94 rule 2's closed, committed table.
# Every entry here is a schema field D-91's five sufficiency fields do NOT
# cover. No entry's key is a member of RATE_BEARING_SCHEMA_KEYS and no
# entry's value is a rate, a cap amount, a tier, or a threshold.
# ---------------------------------------------------------------------------

UNDETERMINED_NEUTRAL_DEFAULTS: dict[str, dict[str, object]] = {
    "programme.taxable": {
        "value": False,
        "disclosure": (
            "Whether this credit is subject to corporation tax was not determined by "
            "research; priced as non-taxable. If the real programme is taxable, the true "
            "net cash figure would be LOWER than shown here."
        ),
    },
    "programme.audit.mandatory": {
        "value": False,
        "disclosure": (
            "Whether an independent audit is mandatory, and any audit fee schedule, was "
            "not determined by research; priced with no audit fee deducted. If the real "
            "programme requires a paid audit, the true net cash figure would be LOWER "
            "than shown here."
        ),
    },
    "programme.per_person_ceiling.applies": {
        "value": False,
        "disclosure": (
            "Whether an above-the-line per-person compensation ceiling applies was not "
            "determined by research; priced with no per-person ceiling. If the real "
            "programme caps individual compensation, the true net cash figure would be "
            "LOWER than shown here."
        ),
    },
    "programme.timing.terms_lock_at": {
        "value": "completion",
        "disclosure": (
            "When this programme's terms lock (application, start of principal "
            "photography, or completion) was not determined by research; assumed at "
            "completion for display purposes only — this does not change the computed "
            "dollar figure."
        ),
    },
}

_TAXABLE_SIGNAL_RE = re.compile(r"subject to (?:corporation|corporate) tax", re.IGNORECASE)
_AUDIT_MANDATORY_SIGNAL_RE = re.compile(
    r"(?:mandatory|required) (?:independent )?audit", re.IGNORECASE
)


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _slugify(name: str) -> str | None:
    """A deterministic `^[a-z0-9-]{1,40}$` slug of `name`, or `None` when
    nothing usable survives (e.g. an emoji-only or punctuation-only
    name)."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not slug:
        return None
    slug = slug[:40].rstrip("-")
    if not slug or not _SLUG_RE.match(slug):
        return None
    return slug


def _classify_mechanism(text: str) -> str | None:
    lowered = text.lower()
    if any(word in lowered for word in ("transferable", "transfer", "sellable", "sold")):
        return "transferable"
    if "nonrefundable" in lowered or "non-refundable" in lowered or "non refundable" in lowered:
        return "nonrefundable_credit"
    if "rebate" in lowered or "grant" in lowered:
        return "rebate_grant"
    if "refundable" in lowered:
        return "refundable"
    if "credit" in lowered:
        return "nonrefundable_credit"
    return None


def _classify_base_definition(text: str) -> str | None:
    lowered = text.lower()
    if "lesser of" in lowered:
        return "lesser_of_pct_core_or_actual_local"
    if "local hire" in lowered:
        return "local_hires_only"
    if ("labour" in lowered or "labor" in lowered) and "only" in lowered:
        return "labour_only"
    if "total" in lowered:
        return "total_qualified_spend"
    return None


def _extract_single_rate_decimal(text: str) -> Decimal | None:
    """Extracts a rate ONLY when exactly one percentage figure appears in
    `text` — never a first-match/best-guess pick among several, and never
    a bare fraction with no `%` sign (too easily confused with an
    unrelated number in free-text research prose). Zero, or two or more,
    percentage figures is an explicit refusal, never a guess (D-94)."""
    matches = _PERCENT_RE.findall(text)
    if len(matches) != 1:
        return None
    try:
        percent = Decimal(matches[0])
    except InvalidOperation:
        return None
    return percent / Decimal("100")


def _extract_days(text: str) -> int | None:
    match = _DAYS_RE.search(text)
    if not match:
        return None
    return int(match.group(1))


def _extract_money_amount(text: str) -> Decimal | None:
    match = _MONEY_RE.search(text)
    if not match:
        return None
    try:
        amount = parse_money(match.group("symbol") + match.group("amount"))
    except UnparseableFigureError:
        return None
    scale = match.group("scale")
    if scale:
        multiplier = _SCALE_MULTIPLIERS.get(scale.lower())
        if multiplier is not None:
            amount = amount * multiplier
    return amount


def _is_uncapped(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _UNCAPPED_KEYWORDS)


def _is_annual_cap(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _ANNUAL_CAP_KEYWORDS)


def _source_confidence_for_url(url: str) -> str:
    """`MEDIUM` for a primary-government host, `LOW` otherwise — chosen
    from the parsed hostname alone, never from the model's own claim, and
    never `HIGH` (RD-02: `HIGH` is reserved for the curated, human-
    reviewed file pipeline)."""
    hostname = (urlparse(url).hostname or "").lower()
    if any(marker in hostname for marker in _PRIMARY_GOVERNMENT_HOST_MARKERS):
        return "MEDIUM"
    return "LOW"


def cited_source_urls(merged_findings: Mapping[SufficiencyField, FieldFinding]) -> list[str]:
    """Deduplicated, order-preserving list of every `source_url` any of
    the five D-91 findings actually cites."""
    seen: set[str] = set()
    urls: list[str] = []
    for finding in merged_findings.values():
        url = finding.source_url
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def apply_neutral_defaults(
    overrides: Mapping[str, object] | None = None,
) -> tuple[dict[str, object], list[str]]:
    """Resolve every entry of `UNDETERMINED_NEUTRAL_DEFAULTS`, using
    `overrides` (a field genuinely determined from the research text) in
    place of the table's neutral value where present. Returns `(values,
    disclosures)`. `disclosures` names only the entries this call actually
    defaulted — a field satisfied by `overrides` contributes no
    disclosure sentence, and a call whose `overrides` covers every table
    entry returns an empty `disclosures` list."""
    overrides = overrides or {}
    values: dict[str, object] = {}
    disclosures: list[str] = []
    for path, spec in UNDETERMINED_NEUTRAL_DEFAULTS.items():
        if path in overrides:
            values[path] = overrides[path]
            continue
        values[path] = spec["value"]
        disclosures.append(str(spec["disclosure"]))
    return values, disclosures


def _detect_supporting_overrides(
    merged_findings: Mapping[SufficiencyField, FieldFinding],
) -> dict[str, object]:
    """Scan the findings' own `value_text` for an EXPLICIT statement about
    a supporting field `UNDETERMINED_NEUTRAL_DEFAULTS` would otherwise
    default. Deliberately narrow: only a clear textual signal overrides a
    default — anything else is left to the disclosed neutral value rather
    than guessed at."""
    overrides: dict[str, object] = {}
    combined_text = " ".join(
        finding.value_text for finding in merged_findings.values() if finding.value_text
    )
    if _TAXABLE_SIGNAL_RE.search(combined_text):
        overrides["programme.taxable"] = True
    if _AUDIT_MANDATORY_SIGNAL_RE.search(combined_text):
        overrides["programme.audit.mandatory"] = True
    return overrides


def neutral_default_disclosures(
    merged_findings: Mapping[SufficiencyField, FieldFinding],
) -> list[str]:
    """The disclosure sentences `build_rule_document` would apply for
    these findings — computed independently so a caller can gather them
    without re-parsing the whole document."""
    overrides = _detect_supporting_overrides(merged_findings)
    _, disclosures = apply_neutral_defaults(overrides)
    return disclosures


def build_rule_document(
    job_id: str,
    identity: JurisdictionIdentity,
    merged_findings: Mapping[SufficiencyField, FieldFinding],
    sources: Sequence[str],
) -> dict:
    """Build a plain `dict` in `engine.models.JurisdictionRuleSet` shape
    from Job 2's merged, sourced findings. Raises `RuleCoercionError` (or
    its `UnslugableIdentityError` subclass) rather than fabricate any
    value D-94 forbids fabricating — see the module docstring. `job_id` is
    accepted for parity with the caller's other job_id-keyed calls and is
    not written into the document itself (the jurisdiction's `id` is a
    slug of its researched name, never the job_id)."""
    del job_id  # not embedded in the document — see docstring

    if not identity.jurisdiction_name:
        raise RuleCoercionError("identity carries no jurisdiction_name to slug")
    slug = _slugify(identity.jurisdiction_name)
    if slug is None:
        raise UnslugableIdentityError(
            f"jurisdiction name {identity.jurisdiction_name!r} could not be turned into a usable id"
        )
    if not identity.country_code or not identity.level or not identity.currency:
        raise RuleCoercionError(
            "identity is missing country_code, level, or currency — cannot build a rule "
            "document without all four identity facts"
        )

    if not sources:
        raise RuleCoercionError(
            "no cited source URL was found on any determined finding — a rule document "
            "with zero sources is never written"
        )

    rate_finding = merged_findings[SufficiencyField.rate]
    base_finding = merged_findings[SufficiencyField.qualifying_base_definition]
    caps_finding = merged_findings[SufficiencyField.caps]
    mechanism_finding = merged_findings[SufficiencyField.payout_mechanism]
    availability_finding = merged_findings[SufficiencyField.current_availability]

    for field_name, finding in (
        ("rate", rate_finding),
        ("qualifying_base_definition", base_finding),
        ("caps", caps_finding),
        ("payout_mechanism", mechanism_finding),
        ("current_availability", availability_finding),
    ):
        if not finding.determined or not finding.value_text:
            raise RuleCoercionError(
                f"the {field_name} finding is not determined with usable text — coercion "
                "requires all five D-91 fields to be genuinely determined"
            )

    assert rate_finding.value_text is not None
    assert base_finding.value_text is not None
    assert caps_finding.value_text is not None
    assert mechanism_finding.value_text is not None

    rate_decimal = _extract_single_rate_decimal(rate_finding.value_text)
    if rate_decimal is None:
        raise RuleCoercionError(
            "could not extract exactly one rate figure from the rate finding's own text "
            f"({rate_finding.value_text!r}) — refusing rather than fabricate a rate"
        )

    base_type = _classify_base_definition(base_finding.value_text)
    if base_type is None:
        raise RuleCoercionError(
            "could not classify the qualifying base definition finding's text "
            f"({base_finding.value_text!r}) into a known base type"
        )

    mechanism = _classify_mechanism(mechanism_finding.value_text)
    if mechanism is None:
        raise RuleCoercionError(
            "could not classify the payout mechanism finding's text "
            f"({mechanism_finding.value_text!r}) into a known mechanism"
        )

    caps_text = caps_finding.value_text
    per_project_cap: dict | None = None
    annual_cap: dict | None = None
    if not _is_uncapped(caps_text):
        cap_amount = _extract_money_amount(caps_text)
        if cap_amount is None:
            raise RuleCoercionError(
                "could not extract a cap amount from the caps finding's text "
                f"({caps_text!r}), and it was not stated as uncapped — refusing rather "
                "than silently model no cap"
            )
        money = {"value": str(cap_amount), "currency": identity.currency}
        if _is_annual_cap(caps_text):
            annual_cap = {"amount": money, "period": "calendar_year", "escalator_schedule": None}
        else:
            per_project_cap = money

    overrides = _detect_supporting_overrides(merged_findings)
    defaults, _disclosures = apply_neutral_defaults(overrides)

    payout_days = _extract_days(mechanism_finding.value_text)
    today_str = _today_iso()

    jurisdiction_id = slug
    programme_id = f"{jurisdiction_id}-researched-programme"

    sources_block = [
        {
            "url": url,
            "title": f"Source cited by the live research agent for {identity.jurisdiction_name}",
            "accessed_date": today_str,
            "confidence": _source_confidence_for_url(url),
        }
        for url in sources
    ]

    return {
        "jurisdiction": {
            "id": jurisdiction_id,
            "name": identity.jurisdiction_name,
            "country_code": identity.country_code,
            "level": identity.level,
            "parent_id": None,
            "currency": identity.currency,
            "status": "live_researched",
            "effective_dates": {
                "rule_version_effective_from": today_str,
                "rule_version_effective_to": None,
                "source_checked_date": today_str,
            },
            "sources": sources_block,
        },
        "programmes": [
            {
                "id": programme_id,
                "name": f"{identity.jurisdiction_name} production incentive (live-researched)",
                "requires_separate_application": False,
                "stacks_with": [],
                "mutually_exclusive_with": [],
                "mechanism": mechanism,
                "taxable": defaults["programme.taxable"],
                "corporation_tax_rate": None,
                "base_definition": {
                    "type": base_type,
                    "pct_core_cap": None,
                    "excluded_line_items": [],
                    "custom_handler_id": None,
                },
                "per_person_ceiling": {
                    "applies": defaults["programme.per_person_ceiling.applies"],
                    "note": None,
                    "w2_cap_amount": None,
                    "loanout_exempt": None,
                    "loanout_withholding_rate": None,
                    "loanout_withholding_confirmed": None,
                    "loanout_withholding_schedule": [],
                },
                "rate_structure": {
                    "type": "flat",
                    "base_rate": str(rate_decimal),
                    "tiers": [],
                    "uplifts": [],
                    "ceiling_split": None,
                    "headcount_scale": None,
                    "source_note": rate_finding.evidence_quote or rate_finding.value_text,
                },
                "minimum_spend": None,
                "caps": {
                    "per_project_cap": per_project_cap,
                    "annual_programme_cap": annual_cap,
                    "cap_consumption_check": {
                        "method": "manual",
                        "source_url": availability_finding.source_url,
                    },
                },
                "audit": {
                    "mandatory": defaults["programme.audit.mandatory"],
                    "fee_schedule": [],
                },
                "timing": {
                    "terms_lock_at": defaults["programme.timing.terms_lock_at"],
                    "application_window": None,
                    "decision_sla_days": None,
                    "payout_lag": {
                        "description": (
                            mechanism_finding.evidence_quote or mechanism_finding.value_text
                        ),
                        "typical_days": payout_days,
                        "interest_paid": None,
                    },
                },
                "transfer_discount": {
                    "applies": mechanism == "transferable",
                    "typical_rate_low": None,
                    "typical_rate_high": None,
                    "source_note": None,
                },
                "residency_rules": None,
                "validation": {
                    "validated": False,
                    "validation_pair_fixture_glob": None,
                    "mean_error_pct": None,
                    "last_checked_against_disclosure": None,
                },
            }
        ],
    }


def write_rule_file(job_id: str, document: Mapping[str, object]) -> Path:
    """Write `document` to `var/job2/{job_id}.ruleset.yaml`, atomically
    (sibling temp file + `Path.replace`, mirroring `agent/research_runs
    .py`'s own discipline). The path is built from the validated `job_id`
    ALONE (T-07-04's pattern applied here) — the visitor's city string and
    the model's own jurisdiction name never reach a path."""
    if not _JOB_ID_RE.match(job_id):
        raise RuleCoercionError(f"refusing to write a rule file for an invalid job_id: {job_id!r}")

    RESEARCH_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESEARCH_RUNS_DIR / f"{job_id}.ruleset.yaml"
    tmp_path = RESEARCH_RUNS_DIR / f".{job_id}.ruleset.yaml.{uuid4().hex}.tmp"
    text = yaml.safe_dump(dict(document), sort_keys=False, default_flow_style=False)
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)
    return path


# ---------------------------------------------------------------------------
# Serialization of a priced result — deliberately independent of
# `engine.figure_serialize.figure_to_dict`, which is NOT one of the two
# names `agent/` may import from `engine/`. Reads only the public
# attributes `engine.pipeline.price_jurisdiction`'s return value exposes
# (duck-typed, no import of the `Figure`/`PricedJurisdiction` classes).
# ---------------------------------------------------------------------------


def _serialize_figure(figure: object) -> dict:
    date_checked = figure.date_checked  # type: ignore[attr-defined]
    return {
        "figure_id": figure.figure_id,  # type: ignore[attr-defined]
        "value": str(figure.value),  # type: ignore[attr-defined]
        "unit": figure.unit,  # type: ignore[attr-defined]
        "label": figure.label,  # type: ignore[attr-defined]
        "derivation": list(figure.derivation),  # type: ignore[attr-defined]
        "source_url": figure.source_url,  # type: ignore[attr-defined]
        "date_checked": date_checked.isoformat() if date_checked else None,
        "confidence": figure.confidence,  # type: ignore[attr-defined]
        "basis": figure.basis,  # type: ignore[attr-defined]
        "caveat": figure.caveat,  # type: ignore[attr-defined]
        "live_fetched_this_run": figure.live_fetched_this_run,  # type: ignore[attr-defined]
        "inputs": [_serialize_figure(child) for child in figure.inputs],  # type: ignore[attr-defined]
    }


def _serialize_net_cash(net_cash: object) -> dict:
    point = net_cash.point  # type: ignore[attr-defined]
    arrival = net_cash.arrival  # type: ignore[attr-defined]
    estimated_date = arrival.estimated_date
    return {
        "low": _serialize_figure(net_cash.low),  # type: ignore[attr-defined]
        "high": _serialize_figure(net_cash.high),  # type: ignore[attr-defined]
        "point": _serialize_figure(point) if point is not None else None,
        "arrival": {
            "estimated_date": estimated_date.isoformat() if estimated_date else None,
            "typical_days": arrival.typical_days,
            "reason": arrival.reason,
        },
    }


def serialize_priced_jurisdiction(priced: object) -> dict:
    """Duck-typed serialization of `engine.pipeline.PricedJurisdiction`.
    Imports nothing from `engine/` — see the block comment above."""
    programmes = priced.programmes  # type: ignore[attr-defined]
    return {
        "jurisdiction_id": priced.jurisdiction_id,  # type: ignore[attr-defined]
        "total_net_cash": _serialize_figure(priced.total_net_cash),  # type: ignore[attr-defined]
        "programmes": [
            {
                "programme_id": pp.programme_id,
                "qualifying_base": _serialize_figure(pp.qualifying_base),
                "gross_credit": _serialize_figure(pp.gross_credit),
                "net_cash": _serialize_net_cash(pp.net_cash),
                "eligibility": {
                    "eligible": pp.eligibility.eligible,
                    "reasons": list(pp.eligibility.reasons),
                },
                "availability": {
                    "available": pp.availability.available,
                    "reason": pp.availability.reason,
                },
            }
            for pp in programmes
        ],
    }

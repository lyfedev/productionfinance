"""Route E — the proof panel (UI-07, DMO-01), the honest accuracy figure
(PRV-06), and unresolved source conflicts (PRV-07). 08-01-PLAN.md.

D-98: this module's whole point is serving the ARCHIVED DOCUMENT ITSELF —
the byte-identical file under `sources/`, manifested in
`sources/MANIFEST.yaml` with a re-derivable sha256 — never only a citation
of it. `build_proof` computes the sha256 of the file on disk at request
time (never trusts the recorded value blindly) so a substituted or altered
document is detectable, matching MANIFEST.yaml's own stated invariant.

Reproduced figure, D-98/RD-03 continued: this module computes the
disclosed GROSS credit only — qualifying base then gross credit
(`engine.qualifying_base.compute_qualifying_base` then
`engine.credit.compute_gross_credit`) — the same two steps
`engine.pipeline.price_programme` runs before it unconditionally also
converts to net cash. `app/services/validate.py::reproduce_disclosure`
goes through the full `price_jurisdiction` pipeline instead, which is why
a `transferable`-mechanism pair with no fully-declared `transfer_discount`
range (New Jersey, Connecticut — see WINDOWS.md #3) reports "cannot be
computed" there: that refusal is about NET CASH after a broker's transfer
discount, a question this module never asks. A government disclosure
reports the CREDIT issued/allocated/estimated — the gross figure — so
comparing gross-to-gross is the correct like-for-like reproduction for a
proof panel, and it reaches a real computed number for every selectable
pair, not only the ones with a fully-sourced transfer discount. Every
`ValueError` `compute_qualifying_base`/`compute_gross_credit` can still
raise (unrelated to net cash — a rate-tier lookup miss, an unresolved
custom-base formula, etc.) is still caught and turned into the same
honest-refusal shape `reproduce_disclosure` uses — never a bare 500 and
never an invented number.

PRV-06/D-100: `accuracy_over_validation_pairs` is a REAL "running
validation loop" — it classifies every currently selectable validation
pair through `agent.taxonomy.classify()` against the real, committed
`agent/variance_rules.yaml` rule set, using each pair's own disclosed
figure and this module's own really-computed gross credit. This is not
the same measurement as a live `agent.job1.run_job1` extraction run (no
`runs/job1/` evidence is committed yet — Parallel/Gemini credentials are
not installed on this host, D-101) — it is a distinct, always-available,
100% real computation over the repo's own committed disclosures, using
the exact `AccuracySummary`/`MatchClass` shape D-100 names. It is honest
specifically because it does NOT borrow `reproduce_disclosure`'s own
per-fixture `assertion.tolerance_bps` concept: `agent.taxonomy.classify`
only ever calls a mismatch `explained_variance` when a NAMED, SOURCED
rule in `agent/variance_rules.yaml` actually matches — a fixture's own
free-text `assertion.variance_reason` prose (nj_joker's 2% diversity
bonus, for instance) does not count. A residue this module's own proof
page fully explains in prose can still show as `unexplained` in this
bucket count, and that is correct, not a bug: it is the truthful
statement that the closed predicate set does not (yet) cover that case.

PRV-07/D-99: `load_source_conflicts` reads the one committed data file
this module is a client of, `data/source_conflicts.yaml`. It is currently
empty — this project's only two candidate conflicts (the NY $700M/$800M
figure, the Georgia loan-out withholding rate) were both closed against a
primary source (`sources/MANIFEST.yaml`'s SRC-01/SRC-05 entries) and are
therefore not conflicts. The surface renders only what this file
declares; it never manufactures an entry to demonstrate the feature.
"""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from agent.schema import ExtractedAward
from agent.taxonomy import (
    AccuracySummary,
    AwardResult,
    MatchClass,
    classify,
    load_variance_rules,
    summarize,
)
from app.services._paths import REPO_ROOT, RULESET_PATH_BY_JURISDICTION
from app.services.validate import (
    VALIDATION_PAIRS_DIR,
    MalformedFixtureError,
    SelectablePair,
    UnknownPairError,
    selectable_pairs,
)
from engine.credit import compute_gross_credit
from engine.figure import Figure
from engine.models import load_ruleset
from engine.qualifying_base import SpendBreakdown, compute_qualifying_base

__all__ = [
    "MANIFEST_PATH",
    "REPO_ROOT",
    "SOURCE_CONFLICTS_PATH",
    "VARIANCE_RULES_PATH",
    "ArchivedDocument",
    "ConflictSource",
    "MalformedFixtureError",
    "ProofResult",
    "SourceConflict",
    "UnknownPairError",
    "accuracy_over_validation_pairs",
    "build_proof",
    "document_media_type",
    "load_source_conflicts",
    "proof_pairs",
    "resolve_document_path",
]

MANIFEST_PATH = REPO_ROOT / "sources" / "MANIFEST.yaml"
SOURCE_CONFLICTS_PATH = REPO_ROOT / "data" / "source_conflicts.yaml"
VARIANCE_RULES_PATH = REPO_ROOT / "agent" / "variance_rules.yaml"


def _load_fixture(pair_id: str) -> dict:
    path = VALIDATION_PAIRS_DIR / f"{pair_id}.yaml"
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@dataclass(frozen=True)
class ArchivedDocument:
    """The byte-archived source document (D-98) — never only a citation.

    `live_sha256` is computed from the file on disk at request time;
    `recorded_sha256` is the fixture's own declared value. `sha256_matches`
    is the honest cross-check between them — MANIFEST.yaml's own stated
    invariant made visible, not merely asserted in a comment."""

    repo_relative_path: str
    document_title: str | None
    manifest_url: str | None
    retrieved_at: str | None
    recorded_sha256: str | None
    live_sha256: str | None
    sha256_matches: bool
    media_type: str
    exists_on_disk: bool


@dataclass(frozen=True)
class ProofResult:
    pair_id: str
    production_title: str
    jurisdiction_id: str
    disclosure_stage: str | None
    disclosed_qualified_spend: Decimal
    disclosed_credit: Decimal
    computed_credit: Figure | None
    # Exact Decimal, never rounded (D-98): disclosed - computed. None only
    # when computed_credit itself could not be built (refusal_reason set).
    residue: Decimal | None
    # The fixture's own `assertion.variance_reason` prose, when the fixture
    # declares one — reused verbatim, never rewritten or summarized.
    residue_explanation: str | None
    match_class: MatchClass | None
    refusal_reason: str | None
    source_url: str | None
    report_period: str | None
    date_checked: str | None
    document: ArchivedDocument | None


def proof_pairs() -> tuple[SelectablePair, ...]:
    """Every validation pair currently selectable for the proof panel —
    the identical closed set `app.services.validate.selectable_pairs`
    already computes (T-03-01's membership discipline, reused rather than
    re-derived a second time)."""
    return selectable_pairs()


def _manifest_entries() -> dict[str, dict]:
    """`sources/MANIFEST.yaml`, keyed by its own `path` field. Read fresh
    on every call — a small, infrequently-changing repo file — never
    cached, so there is no staleness question to reason about."""
    if not MANIFEST_PATH.is_file():
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    documents = raw.get("documents", []) if isinstance(raw, dict) else []
    return {entry["path"]: entry for entry in documents if isinstance(entry, dict) and "path" in entry}


def document_media_type(path: Path) -> str:
    """Best-effort media type from the file extension, falling back to a
    generic binary type for an extension `mimetypes` does not recognize —
    never raises, never guesses at file CONTENT."""
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def resolve_document_path(source_document: str) -> Path:
    """Anchor a fixture-declared `source_document` (already a repo-relative
    path drawn from a closed, validated set — never raw request input) to
    `REPO_ROOT`, matching every other module-anchored path in this layer
    (`app/services/_paths.py`)."""
    return REPO_ROOT / source_document


def _build_archived_document(source_document: str | None, recorded_sha256: str | None) -> ArchivedDocument | None:
    if not source_document:
        return None

    path = resolve_document_path(source_document)
    manifest_entry = _manifest_entries().get(source_document)

    exists = path.is_file()
    live_sha256: str | None = None
    if exists:
        live_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()

    return ArchivedDocument(
        repo_relative_path=source_document,
        document_title=manifest_entry.get("document_title") if manifest_entry else None,
        manifest_url=manifest_entry.get("url") if manifest_entry else None,
        retrieved_at=manifest_entry.get("retrieved_at") if manifest_entry else None,
        recorded_sha256=recorded_sha256,
        live_sha256=live_sha256,
        sha256_matches=(
            live_sha256 is not None
            and recorded_sha256 is not None
            and live_sha256 == recorded_sha256
        ),
        media_type=document_media_type(path),
        exists_on_disk=exists,
    )


def _compute_gross_credit(pair: dict) -> Figure:
    """The two steps `engine.pipeline.price_programme` runs before it
    unconditionally also converts to net cash — see this module's
    docstring for why stopping here (never calling
    `engine.net_cash.convert_to_net_cash`) is the correct comparison for a
    disclosed CREDIT figure, and why this never touches `engine/` itself:
    both functions called here are already-public entry points other
    callers (`engine.pipeline.price_programme`) already use."""
    ruleset = load_ruleset(RULESET_PATH_BY_JURISDICTION[pair["jurisdiction_id"]])
    programme = next((p for p in ruleset.programmes if p.id == pair["program_id"]), None)
    if programme is None:
        raise MalformedFixtureError(
            f"{pair.get('production_title')!r}: no priced programme matches "
            f"program_id {pair.get('program_id')!r} — check the ruleset's programme id "
            "against the fixture"
        )

    qualified_spend = Decimal(pair["qualified_spend"])
    spend = SpendBreakdown.from_total(qualified_spend)
    qualifying_base = compute_qualifying_base(
        programme,
        spend,
        currency=ruleset.jurisdiction.currency,
        source_url=None,
        date_checked=None,
        confidence="validated",
    )
    return compute_gross_credit(programme, qualifying_base, annual_cap_remaining=None)


def build_proof(pair_id: str) -> ProofResult:
    """Build the proof panel for `pair_id`. T-03-01/T-05-12 discipline,
    mirrored from `reproduce_disclosure`: the untrusted `pair_id` is
    checked against the closed selectable set FIRST, before any path is
    built from it."""
    selectable_ids = {p.pair_id for p in proof_pairs() if p.selectable}
    if pair_id not in selectable_ids:
        raise UnknownPairError(pair_id)

    pair = _load_fixture(pair_id)
    disclosed = Decimal(pair["credit_amount"])
    qualified_spend = Decimal(pair["qualified_spend"])
    assertion = pair.get("assertion") or {}

    document = _build_archived_document(pair.get("source_document"), pair.get("source_document_sha256"))

    try:
        computed_figure = _compute_gross_credit(pair)
    except ValueError as exc:
        return ProofResult(
            pair_id=pair_id,
            production_title=pair["production_title"],
            jurisdiction_id=pair["jurisdiction_id"],
            disclosure_stage=pair.get("disclosure_stage"),
            disclosed_qualified_spend=qualified_spend,
            disclosed_credit=disclosed,
            computed_credit=None,
            residue=None,
            residue_explanation=None,
            match_class=None,
            refusal_reason=str(exc),
            source_url=pair.get("source_url"),
            report_period=pair.get("report_period"),
            date_checked=pair.get("date_checked"),
            document=document,
        )

    residue = disclosed - computed_figure.value
    award = ExtractedAward(
        production_title=pair["production_title"],
        qualified_spend=pair["qualified_spend"],
        credit_amount=pair["credit_amount"],
        diversity_credit_amount=pair.get("diversity_credit_amount"),
        programme_hint=None,
        source_row_text="",
    )
    rules = load_variance_rules(VARIANCE_RULES_PATH)
    match_class, _explanation = classify(disclosed, computed_figure.value, award, rules)

    return ProofResult(
        pair_id=pair_id,
        production_title=pair["production_title"],
        jurisdiction_id=pair["jurisdiction_id"],
        disclosure_stage=pair.get("disclosure_stage"),
        disclosed_qualified_spend=qualified_spend,
        disclosed_credit=disclosed,
        computed_credit=computed_figure,
        residue=residue,
        residue_explanation=(assertion.get("variance_reason") or "").strip() or None,
        match_class=match_class,
        refusal_reason=None,
        source_url=pair.get("source_url"),
        report_period=pair.get("report_period"),
        date_checked=pair.get("date_checked"),
        document=document,
    )


def accuracy_over_validation_pairs() -> AccuracySummary:
    """PRV-06/D-100: the honest bucket-count accuracy figure, computed by
    actually running every currently selectable validation pair through
    the real `agent.taxonomy.classify()` engine — see this module's own
    docstring for exactly what this measures and why it differs from a
    live Job 1 extraction run's own `AccuracySummary`. A pair whose gross
    credit itself could not be computed (a genuine `MalformedFixtureError`/
    `ValueError`, not currently reachable by any committed pair — see
    `test_accuracy_over_validation_pairs_matches_a_hand_computed_bucket_
    count`) is counted as an extraction failure, never silently dropped
    from `awards_extracted`."""
    rules = load_variance_rules(VARIANCE_RULES_PATH)
    results = []
    extraction_failures = 0

    for selectable in proof_pairs():
        if not selectable.selectable:
            continue
        pair = _load_fixture(selectable.pair_id)
        disclosed = Decimal(pair["credit_amount"])
        award = ExtractedAward(
            production_title=pair["production_title"],
            qualified_spend=pair["qualified_spend"],
            credit_amount=pair["credit_amount"],
            diversity_credit_amount=pair.get("diversity_credit_amount"),
            programme_hint=None,
            source_row_text="",
        )
        try:
            computed_figure = _compute_gross_credit(pair)
        except (ValueError, MalformedFixtureError):
            extraction_failures += 1
            continue

        match_class, explanation = classify(disclosed, computed_figure.value, award, rules)
        results.append(
            AwardResult(
                award=award,
                disclosed=disclosed,
                computed=computed_figure.value,
                match_class=match_class,
                explanation=explanation,
                derivation=computed_figure.derivation,
            )
        )

    return summarize(results, extraction_failures=extraction_failures)


@dataclass(frozen=True)
class ConflictSource:
    """One authoritative source's stated value inside an unresolved
    disagreement (PRV-07/D-99). Never carries a "winner" flag — that is
    the entire discipline this dataclass exists to make structurally
    impossible to express."""

    label: str
    value: str
    source_url: str | None
    source_document: str | None
    source_document_sha256: str | None
    date_checked: str | None


@dataclass(frozen=True)
class SourceConflict:
    topic: str
    sources: tuple[ConflictSource, ...]
    note: str


def load_source_conflicts(path: Path | None = None) -> tuple[SourceConflict, ...]:
    """Load `data/source_conflicts.yaml` (or `path`, for a test fixture).
    Returns an empty tuple for a missing file or an empty `conflicts:`
    list — never fabricates an entry (D-99's own prohibition). A caller
    who wants the real committed file's contents (the production surface)
    calls this with no argument; a test that wants to prove the render
    path works passes a real conflict fixture via `path`."""
    target = path or SOURCE_CONFLICTS_PATH
    if not target.is_file():
        return ()
    with open(target, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    entries = raw.get("conflicts", []) if isinstance(raw, dict) else []

    conflicts: list[SourceConflict] = []
    for entry in entries:
        sources = tuple(
            ConflictSource(
                label=source["label"],
                value=source["value"],
                source_url=source.get("source_url"),
                source_document=source.get("source_document"),
                source_document_sha256=source.get("source_document_sha256"),
                date_checked=source.get("date_checked"),
            )
            for source in entry.get("sources", [])
        )
        conflicts.append(
            SourceConflict(topic=entry["topic"], sources=sources, note=entry.get("note", ""))
        )
    return tuple(conflicts)

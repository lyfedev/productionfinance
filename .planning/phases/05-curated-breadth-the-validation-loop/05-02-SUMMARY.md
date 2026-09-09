---
phase: 05-curated-breadth-the-validation-loop
plan: 02
subsystem: ai-integration
tags: [google-genai, parallel-web, structured-extraction, taxonomy, honesty-gate, decimal-parsing]

requires:
  - phase: 05-curated-breadth-the-validation-loop
    provides: "05-01's agent/ package (settings, telemetry, schema, parallel_client, gemini_client, job1 tracer), the D-82 fixed pipeline shape, and the D-84 SDK-call log line"
provides:
  - "agent/numbers.py::parse_money — D-88 locale-aware money parsing (US/European convention, parens-negative, footnote markers, NBSP grouping), raising rather than guessing on ambiguous input"
  - "agent/taxonomy.py — the D-86 three-value MatchClass enum, classify(), and AccuracySummary (bucket counts only, no percentage/mean/blended field)"
  - "agent/variance_rules.yaml — the sole declared source of an explained_variance verdict, two rules, closed predicate names only (T-05-07)"
  - "agent.job1.run_job1() widened to price and classify EVERY extracted award (no one-award limit), with a closed TerminalReason enum, injectable search_fn/extract_fn/extract_awards_fn seams, and a run_mode field (live/replay)"
affects: [05-03, phase-8-reverification]

actuals:
  tokens: 16300
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Locale-aware Decimal parsing detects the grouping-vs-decimal separator convention from the LAST separator's position, never from a locale setting — refuses (UnparseableFigureError) rather than guesses on genuine ambiguity (D-88)"
    - "A closed predicate-name registry resolved from a declared YAML file, never eval/exec of a string from that file (T-05-07) — the same fail-loud-on-unknown-value convention as engine.models.load_ruleset's Pydantic Literal fields"
    - "Injectable seams (search_fn/extract_fn/extract_awards_fn) default to None and resolve to the real client function; a caller supplying ANY of them skips the API-key configuration check entirely, since a fake-driven run never reaches an SDK call — this is what makes the offline CI test genuinely need zero keys"
    - "Broken-windows ledger (.planning/WINDOWS.md) as the explicit machine-checked alternative to a live artifact for a gate the environment cannot currently satisfy (AGT-03) — a test asserts exactly one of the two states holds, never a skip"

key-files:
  created:
    - agent/numbers.py
    - agent/taxonomy.py
    - agent/variance_rules.yaml
    - tests/test_agent_numbers.py
    - tests/test_agent_taxonomy.py
    - tests/test_agent_job1_offline.py
    - tests/fixtures/agent/esd_excerpt_double.md
  modified:
    - agent/job1.py
    - agent/schema.py
    - .planning/WINDOWS.md

key-decisions:
  - "parse_money's grouping-validity check applies even in the mixed-both-separators case (not just the single-separator case the plan's action text describes) — a 4-digit grouping run after a comma-as-thousands-separator is rejected as ambiguous rather than silently accepted, consistent with the refuse-don't-guess philosophy applied uniformly."
  - "The alternate-programme-declared-rate predicate (rule 2) is real, closed-set-registered code, exercised directly in tests/test_agent_taxonomy.py, but is NOT currently reachable against real New York data — jurisdictions/us-ny.yaml models exactly one programme (the $100M Empire State Independent Film Production Credit's rate is explicitly not confirmed against a primary source and cannot be encoded per the repo's own no-unsourced-rate rule). This is disclosed, not hidden: the rule exists for when a second NY programme is ever curated, and its predicate correctness is proven by direct unit test rather than end-to-end integration."
  - "Rule 1 deviation found writing Task 3: run_job1's not-configured short-circuit originally gated Search unconditionally, even when a caller supplied all three test seams — meaning the offline test path (the entire point of Task 1's injectable-seam design) could never run without real API keys. Fixed so the configuration check applies only when using the real client functions."

requirements-completed: [AGT-01, AGT-04]
# NOTE: this plan's frontmatter `requirements` field lists all four of
# AGT-01..AGT-04, but AGT-03 ("Job 1 reproduces at least three published
# government award figures exactly") is a live-outcome claim that is
# currently FALSE -- no live run has happened, per "API keys reality"
# below and .planning/WINDOWS.md entry #26. Marking it [x] Complete in
# REQUIREMENTS.md while the same commit's WINDOWS.md records it as an
# open unmet-truth entry would be a direct, same-commit contradiction --
# exactly what CLAUDE.md's Honesty constraint forbids. AGT-03 was
# therefore deliberately left [ ] Pending in REQUIREMENTS.md, overriding
# the mechanical "declaring plan finished, no sibling blocks it" default
# that `requirements.ready-ids` reported as ready. AGT-02 is separately
# blocked by the shared-ID gate (05-03 also declares it, not yet
# summarized) -- no judgment call was needed there.

coverage:
  - id: D1
    description: "Every production/award row the document lists is extracted and reported, not a sample and not a hardcoded subset (AGT-01) — run_job1's one-award tracer limit is gone; --limit now defaults to None (every row)"
    requirement: AGT-01
    verification:
      - kind: unit
        ref: "tests/test_agent_job1_offline.py#test_offline_loop_produces_expected_bucket_counts"
        status: pass
      - kind: unit
        ref: "tests/test_agent_numbers.py (21 parametrized cases)"
        status: pass
    human_judgment: true
    rationale: "The offline test proves the code path extracts every row of a committed fixture with zero drops. Whether Gemini genuinely returns every row of the REAL ESD document (not just what a prompt asked for) cannot be proven without a live call — PARALLEL_API_KEY and GEMINI_API_KEY/GOOGLE_API_KEY are unset in this environment (see 'API keys reality' below)."
  - id: D2
    description: "Every extracted pair is re-priced through the unchanged engine.pipeline.price_jurisdiction, the same entry point app/services/validate.py already uses for a committed fixture — no new engine code path (D-85, JUR-05)"
    requirement: AGT-02
    verification:
      - kind: other
        ref: "git diff --stat -- engine/ (empty across all three commits)"
        status: pass
      - kind: unit
        ref: "tests/test_agent_job1_offline.py#test_agent_imports_nothing_from_engine_except_the_two_sanctioned_names"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every award result carries exactly one of three MatchClass values (exact_match/explained_variance/unexplained); explained_variance is reachable ONLY through a named, sourced rule in agent/variance_rules.yaml; an unknown predicate raises at load (AGT-04, D-86, T-05-07)"
    requirement: AGT-04
    verification:
      - kind: unit
        ref: "tests/test_agent_taxonomy.py (11 tests, including test_load_variance_rules_raises_on_unknown_predicate)"
        status: pass
      - kind: unit
        ref: "tests/test_agent_taxonomy.py#test_accuracy_summary_exposes_no_percentage_mean_or_blended_field"
        status: pass
    human_judgment: false
  - id: D4
    description: "An extraction that returns nothing usable, or an award whose money fields do not parse, is a legitimate reported outcome with an empty/skipped entry, never a fabricated pair — proven by AST walk, not a text grep (D-87)"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/test_agent_job1_offline.py#test_no_module_outside_schema_constructs_an_extracted_award_object"
        status: pass
    human_judgment: false
  - id: D5
    description: "Locale-aware money parsing (agent.numbers.parse_money) handles both US and European grouping/decimal conventions, accounting-parenthesis negatives, footnote markers and NBSP grouping, and RAISES on genuinely ambiguous input rather than guessing (D-88)"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/test_agent_numbers.py (21 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "A live run reproduces at least three disclosed government award figures exactly (AGT-03), or the gap is recorded as an explicit unmet-truth entry in .planning/WINDOWS.md — the gate accepts exactly one of those two states, never a skip"
    requirement: AGT-03
    verification:
      - kind: unit
        ref: "tests/test_agent_job1_offline.py#test_agt_03_gate_is_satisfied_by_exactly_one_state"
        status: pass
      - kind: other
        ref: ".planning/WINDOWS.md entry #26 (kind: unmet-truth, phase 05, names AGT-03)"
        status: pass
    human_judgment: true
    rationale: "The gate is currently green via the WINDOWS.md path, not a live artifact — no live SDK call has been possible in this environment. A human must set both API keys and run a live extraction that reproduces 3+ exact figures before AGT-03 can honestly move to the live-artifact state. See 'API keys reality' below."

duration: 55min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 2: The Validation Loop — D-86 Taxonomy and D-88 Locale-Aware Parsing Summary

**Every extracted award now prices through the unchanged engine and classifies into one of three honest buckets (exact_match/explained_variance/unexplained), with locale-aware money parsing that refuses rather than guesses, and a real AGT-03 gap recorded to WINDOWS.md rather than hidden.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-09T07:10:00Z (approx.)
- **Completed:** 2026-09-09T08:05:00Z (approx.)
- **Tasks:** 3
- **Files modified:** 10 (7 created, 3 modified)

## CRITICAL: API keys reality — read before treating AGT-03 as closed

**`PARALLEL_API_KEY` and `GEMINI_API_KEY`/`GOOGLE_API_KEY` remain NOT set in
this environment.** No live Search, Extract, or Gemini call was made during
this plan's execution — the same reality documented in 05-01-SUMMARY.md,
unchanged. Everything this plan proves is proven either:

1. **Structurally / by unit test** — `agent/numbers.py`'s 21 parametrized
   cases, `agent/taxonomy.py`'s 11 tests (including the unknown-predicate
   load-time raise), and two AST-level gates (D-85's engine-import
   restriction, D-87's no-fabricated-award-object restriction).
2. **Offline, against a committed, self-declaring test-double fixture**
   (`tests/fixtures/agent/esd_excerpt_double.md`) — `run_job1` driven
   entirely through its three injectable seams, producing exactly the
   expected bucket counts (`exact_match=2, explained_variance=1,
   unexplained=1, extraction_failures=1`) with `run_mode == "replay"`.

**None of this is a live reproduction of a real government figure.**
AGT-03 — "a live run reproduces at least three disclosed government award
figures exactly" — remains open, honestly, as `.planning/WINDOWS.md` entry
#26. The offline test's `test_agt_03_gate_is_satisfied_by_exactly_one_state`
passes today because that WINDOWS.md entry exists, not because a live run
happened. Once a human installs both keys (per `deploy/README.md`) and runs

```bash
uv run --frozen python -m agent.job1 --require-live --json
```

successfully, producing `run_mode == "live"` with `accuracy.exact_match
>= 3`, that run should be committed under `runs/job1/` and WINDOWS entry
#26 should be marked `fixed` — at which point the AGT-03 gate flips to the
live-artifact state automatically (the test checks both paths).

## Rows extracted vs. rows listed, and every unexplained row

**No live document has been read this session** (see above), so there is
no real "rows the ESD document listed" count to report yet — that number
will only exist once a live run happens. What this plan proves instead,
against the committed offline fixture (5 illustrative rows, explicitly
NOT government data):

| Row | Convention exercised | Verdict | Disclosed | Computed | Explained by |
|---|---|---|---|---|---|
| Test Production Alpha | plain USD | `exact_match` | $2,500,000 | $2,500,000 | — |
| Test Production Beta | USD + diversity credit | `explained_variance` | $5,003,000 | $5,000,000 | `diversity-credit-column` (delta = $3,000, matches the row's own Diversity Credit column) |
| Test Production Gamma | plain USD, no explaining column | **`unexplained`** | $2,100,000 | $2,000,000 | — (a genuine $100,000 residue with no declared rule to explain it) |
| Test Production Delta | European convention (`.` grouping, `,` decimal) | `exact_match` | $991,190.00 | $991,190.00 | — |
| Test Production Epsilon | unparseable (`n/a`) | `ExtractionFailure` | — | — | never priced, never guessed |

5 rows in, 5 rows accounted for: 4 classified awards + 1 honest extraction
failure = `awards_extracted (5) == exact_match (2) + explained_variance
(1) + unexplained (1) + extraction_failures (1)`. Zero rows silently
dropped.

## AGT-03 gate status

**Green via the `.planning/WINDOWS.md` path, not a live artifact.** Entry
#26 (kind `unmet-truth`, phase `05`) names AGT-03 explicitly and states the
missing-keys reason. `tests/test_agent_job1_offline.py::
test_agt_03_gate_is_satisfied_by_exactly_one_state` checks for exactly one
of {a committed `runs/job1/*.json` artifact with `run_mode=="live"` and
`exact_match>=3`, a WINDOWS.md entry naming AGT-03} — never a skip, which
would be indistinguishable from a pass in CI. Today it passes on the
WINDOWS.md branch.

## Requirements tracking note

`requirements.ready-ids` reported AGT-01, AGT-03, and AGT-04 as mechanically
ready to mark complete (no sibling plan still declares them). AGT-01 and
AGT-04 were marked `[x]` — both are true today regardless of live keys.
**AGT-03 was deliberately left `[ ]` Pending**, overriding that mechanical
default: AGT-03's own text is a live-outcome claim ("Job 1 reproduces at
least three published government award figures exactly") that is
currently false, and this same commit's `WINDOWS.md` entry #26 says so
explicitly. Checking it off here while WINDOWS.md calls it open would be a
same-commit contradiction. AGT-02 is separately blocked by the shared-ID
gate (05-03 also declares it) and needed no judgment call.

## Accomplishments

- `agent/numbers.py::parse_money` — D-88's locale-aware money guardrail.
  Handles US (`1,234.56`) and European (`1.234,56`) grouping/decimal
  conventions (detected from the position of the LAST separator, never a
  locale setting), accounting-parenthesis negatives, leading/trailing
  footnote markers, narrow/non-breaking-space grouping, and a Unicode
  minus sign. **Never constructs or routes through a `float`.** Raises
  `UnparseableFigureError` on empty/placeholder input and on genuinely
  ambiguous grouping (a 4-digit group is neither valid grouping nor a
  plausible decimal fraction) — refusing beats guessing.
- `agent/taxonomy.py` — `MatchClass` (exactly three members),
  `VarianceExplanation`, `VarianceRule`, `AwardResult`, `AccuracySummary`.
  `classify()` checks exact equality first, then each declared rule in
  `agent/variance_rules.yaml` (first match wins), else `unexplained` —
  never widens exact equality with a tolerance. `AccuracySummary` reports
  four bucket/failure counts and nothing resembling a percentage, mean,
  average, blended, or aggregate figure — asserted by walking
  `dataclasses.fields()` and `dir()`.
- `agent/variance_rules.yaml` — the sole source of an `explained_variance`
  verdict anywhere in the codebase. Two rules: `diversity-credit-column`
  (grounded in `ny_anora.yaml`'s real `diversity_credit_amount` field) and
  `alternate-programme-declared-rate` (grounded in `jurisdictions/
  us-ny.yaml`'s real committed 25% `base_rate`, though not currently
  reachable against real NY data since only one programme is modelled —
  disclosed as a key decision above, not hidden). Predicates resolve by
  NAME from a closed set implemented in `agent/taxonomy.py` — no `eval`,
  no expression string ever executed from this file (T-05-07); an unknown
  predicate raises `UnknownPredicateError` at load time.
- `agent/job1.py` widened: `run_job1` prices and classifies EVERY
  extracted award (the tracer's one-award `--limit 1` default is gone —
  `--limit` now defaults to `None`, AGT-01). A closed `TerminalReason`
  enum (`ok`, `not_configured`, `no_primary_source_found`,
  `document_extract_failed`, `zero_awards_extracted`, `sdk_error`) covers
  every no-data outcome with an empty award list and a readable message
  (D-87). Injectable `search_fn`/`extract_fn`/`extract_awards_fn` seams
  (never a default) let an offline test drive the whole loop with zero
  network access. `run_mode` (`live`/`replay`) is load-bearing for plan
  05-03: only a `live` run may ever be rendered as a product accuracy
  figure.
- `tests/fixtures/agent/esd_excerpt_double.md` — a committed test double,
  self-declared as such in its very first line (an HTML comment), driving
  the offline loop test with zero network access.
- `tests/test_agent_job1_offline.py` — 7 tests: the full offline loop's
  bucket counts and per-row verdicts, `run_mode` is always `replay` for a
  fake-driven run, the D-87 AST gate (no `agent/*.py` module outside
  `schema.py` ever constructs an `ExtractedAward`/`ExtractedAwardSet`
  object), the D-85 AST gate (`agent/` imports nothing from `engine/`
  except `load_ruleset` and `price_jurisdiction`), and the AGT-03
  exactly-one-state gate.
- Full suite: **529 passed**, 0 failed, with no API keys in the
  environment. `git diff --stat -- engine/` is empty across all three
  commits (D-85). `vendor-scan.sh` and `lockfile-scan.sh` both exit 0.

## Task Commits

1. **Task 1: Read every row, parse figures locale-aware, report empty extraction honestly** — `c7248b8` (feat)
2. **Task 2: The three-value mismatch taxonomy and the honest accuracy summary** — `1193f42` (feat)
3. **Task 3: Offline proof of the whole loop, and the AGT-03 gate** — `994ed7e` (test)

## Files Created/Modified

- `agent/numbers.py` — D-88 locale-aware `parse_money` / `UnparseableFigureError`
- `agent/taxonomy.py` — D-86 `MatchClass`, `classify()`, `AccuracySummary`, closed predicate registry
- `agent/variance_rules.yaml` — the two declared, sourced `explained_variance` rules
- `agent/job1.py` — widened `run_job1`: every-row extraction, `TerminalReason`, injectable seams, `run_mode`, taxonomy wiring, `corroborates_committed_fixture`
- `agent/schema.py` — `ExtractedAward` gains `programme_hint`
- `tests/test_agent_numbers.py` — 21 parametrized `parse_money` cases
- `tests/test_agent_taxonomy.py` — 11 tests covering the taxonomy behaviors
- `tests/test_agent_job1_offline.py` — 7 tests: offline loop, AST gates, AGT-03 gate
- `tests/fixtures/agent/esd_excerpt_double.md` — committed, self-declared test-double fixture
- `.planning/WINDOWS.md` — entries #26 (AGT-03 unmet-truth) and #27 (FURB157 lint-warning, matching prior-phase precedent)

## Decisions Made

See `key-decisions` in frontmatter above (parse_money's grouping validity in the mixed-separator case; the alternate-programme predicate's current unreachability against real NY data, disclosed rather than hidden; the Rule 1 not-configured-short-circuit deviation).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `run_job1`'s not-configured check blocked the offline test seams from ever running**
- **Found during:** Task 3 (writing `tests/test_agent_job1_offline.py`)
- **Issue:** `run_job1` checked `integration_status()` and short-circuited to `TerminalReason.not_configured` BEFORE calling `search()`, even when the caller supplied `search_fn`/`extract_fn`/`extract_awards_fn` test doubles that never touch a real SDK. This meant Task 1's entire injectable-seam design — built specifically so an offline test could drive the loop with zero network access — could not actually be exercised without real API keys present, which is precisely the constraint Task 3 exists to satisfy in their absence.
- **Fix:** The configuration check now applies only when `using_real_seams` is true (i.e. the caller left all three seams as `None` and is about to reach a real SDK call). A caller driving the pipeline entirely from injected fakes never needs a key, since it never reaches one.
- **Files modified:** `agent/job1.py`
- **Verification:** `tests/test_agent_job1_offline.py` (7 tests, all pass with no keys set); full suite 529 passed
- **Committed in:** `994ed7e` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 — a bug in the seam-gating logic, caught and fixed while writing the offline test it was blocking)
**Impact on plan:** Necessary for the offline test's entire premise to hold. No scope creep — this is the injectable-seam design working as originally intended, corrected to actually behave that way.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

**Unchanged from 05-01 — see `deploy/README.md` "Phase 5 — agent
credentials (SHP-05 / SHP-06)".** `PARALLEL_API_KEY` and
`GEMINI_API_KEY`/`GOOGLE_API_KEY` must both be set before AGT-03 can move
from "recorded gap in WINDOWS.md" to "closed via a committed live
artifact under `runs/job1/`". This remains a hard Stage One eligibility
concern (SHP-05/SHP-06, unchanged from 05-01) and now also blocks AGT-03
specifically.

## Next Phase Readiness

- Plan 05-03 can put this on the hosted page: `run_job1()` returns a fully
  classified `Job1Run` with `accuracy: AccuracySummary` and
  `awards: tuple[AwardResult, ...]` ready to render, and `run_mode` is the
  exact field 05-03 needs to gate "only ever render a `live` run as a
  product accuracy figure" (T-05-10).
- **Blocker for full AGT-03/SHP-05/SHP-06 verification (not for further
  building):** unchanged from 05-01 — a human must set both API keys and
  run a live extraction once, successfully, reproducing 3+ exact figures,
  before the WINDOWS.md-recorded gap can be resolved and the live-artifact
  path proven.

## Self-Check: PASSED

All 7 created artifacts confirmed present on disk (`[ -f ]`); all 3 task
commit hashes (`c7248b8`, `1193f42`, `994ed7e`) confirmed present in
`git log --oneline --all`. Full acceptance-criteria re-run: `uv run
--frozen pytest tests/ -q` (529 passed, no API keys in environment),
`git diff --stat -- engine/` (empty), `bash .github/scripts/
vendor-scan.sh` (PASS), `bash .github/scripts/lockfile-scan.sh` (PASS),
`tests/test_agent_numbers.py` (21 passed), `tests/test_agent_taxonomy.py`
(11 passed), `tests/test_agent_job1_offline.py` (7 passed), no-keys
`python -m agent.job1 --limit 1` (prints not-configured, exits 0).

---
*Phase: 05-curated-breadth-the-validation-loop*
*Completed: 2026-09-09*

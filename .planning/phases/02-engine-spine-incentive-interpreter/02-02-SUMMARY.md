---
phase: 02-engine-spine-incentive-interpreter
plan: 02
subsystem: engine
tags: [pytest, decimal, rounding, pydantic-validation, provenance, property-testing]

requires:
  - phase: 02-engine-spine-incentive-interpreter
    provides: >
      02-01's complete Figure value object, quantize_money, and the full
      JurisdictionRuleSet schema — this plan makes the numeric and
      provenance contracts they establish executable rather than
      aspirational, without modifying their structure.
provides:
  - "tests/test_engine_rounding.py — proves ROUND_HALF_UP is genuinely in effect at quantize_money's call site (not merely imported) by asserting the pinned result AND the divergent ROUND_HALF_EVEN default-context result on two constructed values, plus a labelled non-proof CT regression anchor"
  - "tests/test_engine_models.py — three source-level security gates (no unsafe PyYAML loader entry points in engine/, no float-typed annotations in models.py, no dynamic name resolution in engine/handlers/), the Decimal-precision inequality proof (RD-01), and five ValidationError fail-loud schema tests"
  - "tests/test_engine_figure_provenance.py — PRV-01/02/03 as property assertions over a real Anora-priced Figure tree walked via .inputs, plus constructor-level negative-case coverage a real tree cannot exercise"
affects: [02-03, 02-04, 02-05, 02-06, 03-new-york-end-to-end]

actuals:
  tokens: 5732
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Comment-line-stripped source-text security gates as pytest tests (not shell greps in a verify block) — each fails loud on an empty scanned-file list, mirroring tests/test_validation_pair_fixtures.py's T-01-15 discipline"
    - "Paired divergence assertions for rounding-mode proofs: assert the pinned result AND the value the unpinned default context would have produced, on an input where the two genuinely differ — a single-sided assertion cannot detect a deleted rounding= argument"
    - "Multi-root tree walk deduped by figure_id (engine.figure.Figure.inputs is a sibling-lineage DAG, not a single-rooted tree — gross_credit and net_cash.point are two independent with_step evolutions of the same starting figure, neither reachable from the other)"

key-files:
  created:
    - tests/test_engine_rounding.py
    - tests/test_engine_models.py
    - tests/test_engine_figure_provenance.py
  modified: []

key-decisions:
  - "Regex for the unsafe-PyYAML gate requires an actual call parenthesis or class-attribute reference (e.g. yaml\\.load\\() rather than a bare token match — engine/models.py's own docstring contains the literal strings 'yaml.load' and 'yaml.unsafe_load' as prose explaining the ban; a naive token-match gate would have self-tripped on its own correct implementation, the same false-positive class 02-01-SUMMARY.md recorded for engine/handlers/__init__.py's getattr/importlib docstring"
  - "No code change to engine/rounding.py, engine/figure.py or engine/credit.py was needed to make every specified behaviour true — both plan-anticipated escape hatches ('make a small change... if needed') went unused because 02-01's implementation already satisfied every property this plan tests"

patterns-established: []

requirements-completed: [PRV-01, PRV-02, PRV-03]

coverage:
  - id: D1
    description: "ROUND_HALF_UP is proven genuinely in effect at quantize_money's single call site, not merely declared — two constructed values where ROUND_HALF_UP and Python's default ROUND_HALF_EVEN diverge are asserted both ways"
    verification:
      - kind: unit
        ref: "tests/test_engine_rounding.py::test_half_cent_diverges_from_bankers_rounding"
        status: pass
      - kind: unit
        ref: "tests/test_engine_rounding.py::test_half_dollar_diverges_from_bankers_rounding"
        status: pass
      - kind: unit
        ref: "manual non-vacuity check: deleting rounding=ROUND_HALF_UP from quantize_money made 2 of 3 rounding tests fail; reverted, engine/rounding.py unchanged in the commit"
        status: pass
    human_judgment: false
  - id: D2
    description: "Rate precision (RD-01) is provably preserved: a quoted-string YAML rate parses to an exact Decimal, and is provably unequal to the naive float-mediated conversion path"
    requirement: "PRV-01"
    verification:
      - kind: unit
        ref: "tests/test_engine_models.py::test_quoted_string_rate_parses_exactly_as_decimal"
        status: pass
      - kind: unit
        ref: "tests/test_engine_models.py::test_quoted_string_rate_is_not_equal_to_naive_float_conversion"
        status: pass
    human_judgment: false
  - id: D3
    description: "A malformed rule file (unrecognised mechanism, base_definition.type, rate_structure.type, jurisdiction.status, or an unexpected extra key) raises pydantic.ValidationError rather than silently defaulting"
    verification:
      - kind: unit
        ref: "tests/test_engine_models.py::test_unrecognised_mechanism_raises, ::test_unrecognised_base_definition_type_raises, ::test_unrecognised_rate_structure_type_raises, ::test_unrecognised_jurisdiction_status_raises, ::test_unexpected_extra_top_level_key_raises"
        status: pass
    human_judgment: false
  - id: D4
    description: "Three source-level security gates (T-02-01/02-04/02-03) run as pytest tests in CI: no unsafe PyYAML loader entry point anywhere in engine/, no float-typed field annotation in engine/models.py, no dynamic name resolution (getattr/importlib) anywhere in engine/handlers/ — each fails loud if its scanned-file list is empty"
    verification:
      - kind: unit
        ref: "tests/test_engine_models.py::test_no_unsafe_yaml_loader_entry_points_in_engine, ::test_no_float_typed_fields_in_models, ::test_no_dynamic_name_resolution_in_handlers"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every Figure in a fully-walked, real computed tree (Anora priced through jurisdictions/us-ny.yaml) carries source_url/date_checked as a non-empty string/date or an explicit None, with a non-zero count of figures carrying a real source_url"
    requirement: "PRV-01"
    verification:
      - kind: unit
        ref: "tests/test_engine_figure_provenance.py::test_every_figure_in_priced_tree_has_source_or_explicit_null, ::test_at_least_one_figure_has_real_source_url, ::test_priced_tree_visits_at_least_four_distinct_figures"
        status: pass
    human_judgment: false
  - id: D6
    description: "Figure.confidence is a closed two-value enum (validated/researched) with no default, aggregation never upgrades confidence, and distinct source_url values never merge into one figure_id — proven separately from tests/test_source_truth.py's four-tier source-reliability vocabulary (no import coupling)"
    requirement: "PRV-02"
    verification:
      - kind: unit
        ref: "tests/test_engine_figure_provenance.py::test_confidence_is_closed_enum, ::test_confidence_omitted_raises, ::test_combined_confidence_reports_researched_when_mixed, ::test_distinct_source_url_yields_distinct_figure_id, ::test_inputs_order_preserved_regardless_of_member_confidence"
        status: pass
    human_judgment: false
  - id: D7
    description: "Every Figure in the real priced tree carries a non-empty derivation; the five gross-credit adjustment steps appear as five distinct, ordered lines even when two of them are no-ops (no per-person ceiling, no per-project cap declared for New York); derivation is byte-identical across two runs of the same input"
    requirement: "PRV-03"
    verification:
      - kind: unit
        ref: "tests/test_engine_figure_provenance.py::test_every_figure_in_priced_tree_has_non_empty_derivation, ::test_five_adjustment_steps_present_and_in_order, ::test_derivation_is_byte_identical_across_two_runs"
        status: pass
      - kind: unit
        ref: "manual non-vacuity check: removing the per-project-cap step's with_step no-op call made test_five_adjustment_steps_present_and_in_order fail (missing marker); reverted, engine/credit.py unchanged in the commit"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-08-25
status: complete
---

# Phase 2 Plan 02: Numeric & Provenance Contracts as Executable Property Tests Summary

**Three new test modules (34 tests) turn PRV-01/02/03 and the pinned-rounding/Decimal-precision/fail-loud-schema contracts from prose into CI-enforced assertions, with zero changes to engine/ production code — 02-01's implementation already satisfied every property tested.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-25T11:24:36Z (approx., from prior plan's completion)
- **Completed:** 2026-08-25T11:33:29Z
- **Tasks:** 2
- **Files modified:** 3 (3 created, 0 modified)

## Accomplishments

- `tests/test_engine_rounding.py` proves `ROUND_HALF_UP` is genuinely the
  active rounding mode at `quantize_money`'s single call site — not merely
  declared — by constructing two values (`Decimal("0.005")` to cents,
  `Decimal("2.5")` to whole dollars) where `ROUND_HALF_UP` and Python's
  default `ROUND_HALF_EVEN` context produce different results, and
  asserting both the pinned result and the divergent default-context
  result in the same test. Connecticut's `Christmas Always` fixture
  (`$1,159,501.50 → $1,159,502`) is kept as a regression anchor but its
  test explicitly documents that both modes agree on that value and
  therefore proves nothing about which mode is in effect on its own.
- `tests/test_engine_models.py` adds three source-level security gates as
  pytest tests — zero unsafe PyYAML loader entry points anywhere in
  `engine/`, zero `float`-typed field annotations in `engine/models.py`,
  zero dynamic name resolution (`getattr`/`importlib`) anywhere in
  `engine/handlers/` — each comment-line-stripped and fail-loud if its
  scanned-file list is empty, plus the Decimal-precision inequality proof
  (a quoted-string YAML rate parses to an exact `Decimal`, provably unequal
  to the naive float-mediated conversion) and five `ValidationError`
  fail-loud tests covering every classification field plus an unexpected
  extra key.
- `tests/test_engine_figure_provenance.py` prices Anora's disclosed
  qualified spend through the real, committed `jurisdictions/us-ny.yaml`
  via `price_jurisdiction`, walks the returned `Figure` tree recursively
  through its `inputs` edges from multiple root figures (deduped by
  `figure_id`), and asserts PRV-01 (source/date honesty over the whole
  tree, non-zero real-source count), PRV-02 (closed `validated`/
  `researched` enum, omission raises `TypeError`, an invalid value raises
  `ValueError`, aggregation never upgrades confidence, distinct
  `source_url` values never collapse into one `figure_id`), and PRV-03 (the
  five gross-credit adjustment steps appear as five distinct, ordered
  derivation lines even though two of them are no-ops for New York, and
  derivation is byte-identical across two runs of the same input).
- Both plan-specified non-vacuity checks were performed and reverted: (1)
  temporarily deleting the `rounding=ROUND_HALF_UP` argument from
  `quantize_money` made 2 of 3 rounding tests fail as expected; (2)
  temporarily removing the per-project-cap step's no-op `with_step` call
  made the five-adjustment-steps ordering test fail as expected. Neither
  `engine/rounding.py` nor `engine/credit.py` carries any diff in this
  plan's commits — both checks confirm the tests are non-vacuous without
  requiring a permanent production-code change.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin the numeric contract — rounding mode, Decimal typing,
   fail-loud schema** - `d0032b9` (test)
2. **Task 2: Provenance as executable property assertions over a real
   computed tree** - `74c27f2` (test)

_No TDD-cycle commit split — both tasks are `type="auto" tdd="true"`
without a preceding RED-phase failing-test commit, since the behaviours
under test were already implemented by plan 02-01; each task is a single
test-authoring commit._

## Files Created/Modified

- `tests/test_engine_rounding.py` - Pinned-rounding divergence proofs (2
  tests) plus the labelled CT regression anchor (1 test)
- `tests/test_engine_models.py` - Three security gates, two Decimal-
  precision proofs, six schema tests (baseline-validates anchor + five
  `ValidationError` negative cases) — 11 tests
- `tests/test_engine_figure_provenance.py` - PRV-01/02/03 property
  assertions over a real Anora-priced tree plus constructor-level negative
  cases — 11 tests

## Decisions Made

- **Unsafe-PyYAML gate regex requires an actual call/class reference, not
  a bare token match:** `engine/models.py`'s own docstring explains the
  `yaml.safe_load`-only convention using the literal prose
  "`` ``yaml.load``/``yaml.unsafe_load`` ``" (no trailing parenthesis). A
  naive `getattr`/`importlib`-style bare-token grep would have self-tripped
  on this correct, already-compliant file — the exact false-positive class
  `02-01-SUMMARY.md` recorded for `engine/handlers/__init__.py`'s own
  docstring. The gate's regex (`yaml\.(load|unsafe_load|full_load)\s*\(` or
  `yaml\.(UnsafeLoader|FullLoader|Loader)\b`) was designed and verified
  against the actual repository content before being written into the test
  file, avoiding the deviation rather than triggering and then fixing it.
- **No production-code change was needed.** The plan anticipated "a small
  change" might be needed to `engine/rounding.py` or `engine/figure.py` to
  make a behaviour true (e.g., exposing a keyword argument, handling an
  empty input sequence). Every behaviour specified in the plan was already
  true of 02-01's implementation; both escape hatches went unused, and this
  plan's two commits touch only `tests/`.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes were
required; the one design decision worth recording (the yaml-gate regex
specificity, above) was made proactively during authoring rather than as a
reactive fix to a failing acceptance criterion.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Rounding, rate precision, schema strictness and figure provenance are
  now all enforced by tests that run on every commit (65 tests total in
  the full suite, up from 40 before this plan — Phase 1's 35 plus 02-01's
  5 are unregressed).
- Plans 02-03 and 02-05 (siblings in this wave) extend `engine/qualifying_base.py`,
  `engine/handlers/__init__.py` and `engine/credit.py` respectively; this
  plan's new security gates (especially the unsafe-YAML and
  getattr/importlib scans, which glob the whole `engine/` tree and
  `engine/handlers/` respectively) will automatically re-scan any files
  those plans add or modify without further wiring.
- No blockers. Neither `engine/rounding.py`, `engine/figure.py` nor
  `engine/credit.py` needed a behavioural change in this plan, so wave-2
  siblings inherit the same schema and Figure contract 02-01 shipped,
  unchanged.

---

*Phase: 02-engine-spine-incentive-interpreter*
*Completed: 2026-08-25*

## Self-Check: PASSED

All 3 created files verified present on disk (`[ -f ]`). Both task commit
hashes (`d0032b9`, `74c27f2`) verified present in `git log --oneline --all`.
Full suite (`uv run pytest tests/ -q`) verified green at 65 passed
immediately before writing this summary.

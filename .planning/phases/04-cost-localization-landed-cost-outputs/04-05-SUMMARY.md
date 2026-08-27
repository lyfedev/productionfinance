---
phase: 04-cost-localization-landed-cost-outputs
plan: 05
subsystem: cost-localization
tags: [fx, currency, london, bectu, state-dept, per-diem, cost-08, d-74, d-75]

requires:
  - phase: 04-cost-localization-landed-cost-outputs
    provides: "04-01's Figure.basis provenance axis, CityCostProfile schema, engine.cost_localizer.localize, engine.landed_cost.aggregate; 04-02's dynamic labour+fringe pricing path; 04-03's per-diem/seasonality machinery (engine.per_diem, engine.seasonality); 04-04's facilities/exemptions pricing (engine.facilities, engine.exemptions) that empties not_priced"
provides:
  - "engine.fx — FxSnapshot, load_fx_snapshot, convert, rate_figure (COST-08, D-74): a committed dated FX snapshot reader that refuses rather than derives a cross-rate or inverts a rate for the reverse direction"
  - "data/fx/gbp-usd.yaml — GBP->USD 1.363, dated 2026-08-26, fetched once from Frankfurter and archived under sources/fx/ (D-10)"
  - "data/union_rates/bectu.yaml — camera and general_crew craft rows for London, both basis: sourced, zero changes to engine/union_rates.py (the union-agnosticism proof)"
  - "data/per_diem/state-dept/gb-london.yaml — State Dept foreign per diem for London, resolving 04-RESEARCH.md Assumption A4 (no genuine month band)"
  - "data/facilities/gb-london.yaml, data/tax_exemptions/gb-london.yaml, data/cost_profiles/gb-london.yaml — London's complete cost profile, currency GBP, jurisdiction_id null, not_priced empty"
  - "engine.city_profile_lookup — London aliases (london, greater london, UK/United Kingdom/England suffixes)"
  - "engine.landed_cost.aggregate(..., reporting_currency=) — per-component FX conversion into a comparable total; LandedCost.reporting_currency/.source_currency/.fx_as_of_date"
affects: [04-06, 04-07, "Phase 6 (interface renders the FX component line, reporting_currency, seasonality_state)", "Phase 8 (proof panel walks the widened Figure DAG, now including FX conversion nodes)", "Phase 7 (freshness gate takes the committed FX snapshot live)"]

actuals:
  tokens: 36647
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "A committed dated FX snapshot is read by EXACT {base}-{quote}.yaml filename, never inverted for the reverse pair — engine.fx.load_fx_snapshot refuses rather than deriving 1/rate, mirroring engine.net_cash.transferable's refuse-rather-than-invent shape exactly."
    - "Per-component currency conversion: each cost line is converted and quantized individually (one call to quantize_money per line, inside engine.fx.convert), and the total is the exact Decimal sum of the already-quantized converted lines — no second quantize of the sum, so the displayed components always add up to the displayed headline byte-for-byte."
    - "A non-money component (the FX rate itself, D-75) is carried in a total Figure's `inputs` for DAG visibility while being explicitly excluded from the money summation and the exclusion stated in a derivation line — the identical shape engine.pipeline.price_jurisdiction already uses for a non-contributing programme Figure."
    - "reporting_currency defaults to the localized budget's own currency, so every pre-existing same-currency call site (New York, Los Angeles) is provably byte-identical whether or not the keyword is passed — an additive parameter, not a behavior change for USD cities."

key-files:
  created:
    - engine/fx.py
    - data/fx/gbp-usd.yaml
    - data/union_rates/bectu.yaml
    - data/per_diem/state-dept/gb-london.yaml
    - data/facilities/gb-london.yaml
    - data/tax_exemptions/gb-london.yaml
    - data/cost_profiles/gb-london.yaml
    - tests/test_engine_fx.py
    - sources/fx/2026-08-26-frankfurter-gbp-usd.json
    - sources/unions/2026-08-26-bectu-camera-branch-ratecard-2025.pdf
    - sources/unions/2026-08-26-bectu-grips-branch-ratecard-2024.pdf
    - sources/state-dept/2026-08-26-allowances-state-gov-uk-per-diem.html
  modified:
    - engine/landed_cost.py
    - engine/city_profile_lookup.py
    - data/union_rates/fringe_schedules.yaml
    - sources/MANIFEST.yaml
    - tests/test_engine_cost_localizer.py
    - tests/test_engine_landed_cost.py
    - tests/test_engine_union_rates.py
    - .planning/WINDOWS.md

key-decisions:
  - "engine/cost_profile.py and engine/cost_localizer.py were declared in the plan's files_modified but ended up with ZERO changes — this is itself the deliverable, not an omission: pricing London required no engine change beyond the declared BECTU/per-diem/facilities/exemptions DATA and London's own committed cost profile, exactly proving the schema's currency- and union-agnosticism. Verified via `git diff --stat engine/union_rates.py engine/per_diem.py engine/facilities.py engine/exemptions.py` showing an empty diff for Task 2."
  - "app/services/spec.py was NOT touched, despite Task 3's prose saying 'wire London into the per-city loop' — it was not in the plan's files_modified list, and the existing generic profile-resolution loop already prices any city city_profile_lookup resolves, with zero code change needed. reporting_currency stays an opt-in aggregate() parameter Route A does not yet call with a non-default value; the actual USD-comparable cross-city gap is plan 04-06's job."
  - "This executor session HAD live network access (curl) — unlike 04-04's session — and used it for every fetch in this plan: Frankfurter's dated FX endpoint, Bectu's Camera Branch and Grips Branch rate-card PDFs (via pdftotext transcription), and allowances.state.gov's own per-diem query form (POST CountryCode=1114). Both BECTU craft rows land genuinely basis: sourced, a real improvement over 04-04's all-estimated precedent."
  - "London's general_crew craft prices from the Bectu Grips Branch rate card's 'Grip' (non-key) role, TV/SVOD Band 1 (GBP424/day) — a genuine, dated, sourced row, but one specific grip-branch grade standing in for nine non-camera departments, not a true cross-department blended rate. Disclosed in the file's own header and recorded in WINDOWS.md, mirroring iatse.yaml's identical 'one representative row stands in for the whole bucket' precedent."
  - "London's tax_exemptions file declares ZERO entries (an empty list, stated) rather than inventing a UK VAT-relief analog to New York's sales-tax exemption or Los Angeles's hotel-occupancy exemption — the UK's VAT structure is materially different from a US point-of-sale sales/occupancy tax, and no primary HMRC document confirming an analogous relief was fetched this session."
  - "BECTU's fringe schedule uses UK-SPECIFIC estimates (3% statutory auto-enrolment pension minimum, 15% employer NI) rather than reusing this file's US FICA/FUTA/SUTA figure (0.0965) — reusing the US figure would have misrepresented a US-specific payroll tax structure as applicable in Britain, a worse dishonesty than a disclosed UK-specific estimate."
  - "The converted total's per-component conversion discipline (one quantize per line, no second quantize of the sum) is enforced structurally: the converted branch of aggregate() sums already-quantized Decimal values directly, never re-wrapping the sum in quantize_money — keeping 'the converted total is the exact sum of the converted components' true by construction."

requirements-completed: [COST-02, COST-08]

coverage:
  - id: D1
    description: "A committed dated FX snapshot (GBP->USD) refuses rather than derives for any missing pair, including the reverse direction of a committed pair — never an implicit inversion"
    requirement: COST-08
    verification:
      - kind: unit
        ref: "tests/test_engine_fx.py#test_missing_pair_raises_naming_both_currencies"
        status: pass
      - kind: unit
        ref: "tests/test_engine_fx.py#test_no_implicit_inversion_usd_to_gbp_raises"
        status: pass
      - kind: unit
        ref: "tests/test_engine_fx.py#test_zero_rate_rejected_at_load"
        status: pass
      - kind: unit
        ref: "tests/test_engine_fx.py#test_negative_rate_rejected_at_load"
        status: pass
    human_judgment: false
  - id: D2
    description: "Conversion applies exactly one quantize (ROUND_HALF_UP, not the ambient ROUND_HALF_EVEN default) to the final product only — the rate itself is never quantized"
    requirement: COST-08
    verification:
      - kind: unit
        ref: "tests/test_engine_fx.py#test_half_dollar_boundary_rounds_up_under_pinned_round_half_up"
        status: pass
      - kind: unit
        ref: "tests/test_engine_fx.py#test_single_quantize_applied_the_rate_itself_is_never_quantized"
        status: pass
      - kind: unit
        ref: "tests/test_engine_fx.py#test_rate_of_exactly_one_returns_input_unchanged"
        status: pass
    human_judgment: false
  - id: D3
    description: "London prices end to end in GBP from committed BECTU/State-Dept data with zero changes to engine/union_rates.py, engine/per_diem.py, engine/facilities.py or engine/exemptions.py — not_priced is empty"
    requirement: COST-02
    verification:
      - kind: integration
        ref: "tests/test_engine_cost_localizer.py#test_london_prices_end_to_end_in_gbp_with_not_priced_empty"
        status: pass
      - kind: other
        ref: "git diff --stat engine/union_rates.py engine/per_diem.py engine/facilities.py engine/exemptions.py -- empty"
        status: pass
    human_judgment: false
  - id: D4
    description: "Research Assumption A4 is resolved by direct query against allowances.state.gov: London carries no genuine month-by-month lodging band (Season 01/01-12/31, flat), falling into D-64's absent branch — recorded in .planning/WINDOWS.md"
    requirement: COST-04
    verification:
      - kind: unit
        ref: "tests/test_engine_cost_localizer.py#test_london_per_diem_carries_no_month_band_resolving_research_assumption_a4"
        status: pass
      - kind: other
        ref: ".planning/WINDOWS.md entry 18 (recorded via gsd-tools windows append)"
        status: pass
    human_judgment: false
  - id: D5
    description: "London's converted total equals the exact Decimal sum of its converted, quantized components; the FX rate itself is a named component in the total's inputs, excluded from the money sum"
    requirement: COST-08
    verification:
      - kind: unit
        ref: "tests/test_engine_landed_cost.py#test_london_converted_total_equals_exact_sum_of_converted_components"
        status: pass
      - kind: unit
        ref: "tests/test_engine_landed_cost.py#test_fx_rate_figure_is_present_in_inputs_and_contributes_zero_to_the_sum"
        status: pass
      - kind: unit
        ref: "tests/test_engine_landed_cost.py#test_usd_city_reporting_in_usd_adds_no_fx_line_and_is_byte_identical"
        status: pass
      - kind: unit
        ref: "tests/test_engine_landed_cost.py#test_missing_fx_snapshot_raises_rather_than_returning_an_unconverted_total"
        status: pass
    human_judgment: false

duration: 80min
completed: 2026-08-27
status: complete
---

# Phase 4 Plan 05: Currency as a First-Class Component, and London — the Third Floor City

**A committed, dated GBP->USD FX snapshot (1.363, 2026-08-26) that refuses rather than derives any missing or reversed pair, plus London's complete cost profile priced in GBP from genuinely sourced BECTU rate cards and a directly-queried State Department per-diem row — London's landed cost is £548,595 (GBP) / $747,735 (USD, per-component-converted) for the fixed test spec, with zero engine changes proving the schema generalizes past US unions and a single currency.**

## Performance

- **Duration:** ~80 min
- **Started:** 2026-08-26T23:20:00Z (approximate)
- **Completed:** 2026-08-27T00:41:39Z
- **Tasks:** 3
- **Files modified:** 20 (12 created, 8 modified)

## Accomplishments

- **`engine/fx.py`** — `FxSnapshot`, `load_fx_snapshot`, `convert`, `rate_figure`. A committed `{base}-{quote}.yaml` snapshot is the only legal source of a rate; a missing pair (including the REVERSE of a committed pair) raises naming both currencies rather than deriving a cross-rate or inverting `1/rate`. Currency codes are validated against a closed `SUPPORTED_CURRENCY_CODES` tuple before any string reaches a `Path` join (T-04-20). `convert` applies `quantize_money` exactly once, to the final product; the rate itself is never quantized.
- **`data/fx/gbp-usd.yaml`** — GBP->USD 1.363, dated 2026-08-26, fetched once from Frankfurter's no-key dated endpoint and archived byte-for-byte under `sources/fx/`, with a `sources/MANIFEST.yaml` entry. No runtime network call — Phase 7's freshness gate takes this live later (D-57).
- **London lands as the third committed cost profile and the first non-USD one.** `data/union_rates/bectu.yaml` carries two genuinely `basis: sourced` craft rows (camera from Bectu's Camera Branch card; general_crew from the Grips Branch card's "Grip" role) — a real improvement over 04-04's all-estimated precedent, since this session had live network access. `data/per_diem/state-dept/gb-london.yaml`, `data/facilities/gb-london.yaml`, `data/tax_exemptions/gb-london.yaml` and `data/cost_profiles/gb-london.yaml` complete the profile; `not_priced` is empty.
- **Resolved 04-RESEARCH.md Assumption A4 by direct query** against `allowances.state.gov` (POST `CountryCode=1114`): London's per-diem row shows `Season Begin 01/01` / `Season End 12/31` — the whole year under one rate, not a genuine month band. London therefore carries `lodging_flat_rate`, falling into D-64's "absent" seasonality branch alongside Los Angeles. Recorded honestly in `.planning/WINDOWS.md` rather than assumed either way.
- **Zero engine changes proved the union- and currency-agnosticism claim.** `git diff --stat engine/union_rates.py engine/per_diem.py engine/facilities.py engine/exemptions.py` is empty for Task 2 — pricing London required only committed data plus London's own cost profile, exactly as `engine.cost_localizer.localize`'s D-53 jurisdiction-agnostic (and now currency-agnostic) design promised.
- **`engine.landed_cost.aggregate` gains `reporting_currency`** (COST-08/D-75). When it differs from the localized budget's own currency, every cost line is converted individually through `engine.fx.convert` (one quantize per line), and the converted total is the exact `Decimal` sum of the already-quantized lines — no second quantize of the sum. The FX rate itself (`engine.fx.rate_figure`) is attached to `cost_total.inputs` as its own named, dated, cited component, explicitly excluded from the money sum with the exclusion stated in a derivation line — mirroring how `engine.pipeline.price_jurisdiction` carries a non-contributing programme Figure. A USD city reporting in USD is a byte-identical no-op (verified against New York).
- **26 new tests** across `tests/test_engine_fx.py` (15) and additions to `tests/test_engine_landed_cost.py` (7) and `tests/test_engine_cost_localizer.py` (2), plus two pre-existing tests updated for BECTU joining the fringe schedule (five unions, not four) and a corrected `MANIFEST.yaml` `cited_for` row-id reference.

## Task Commits

Each task was committed atomically (plus one small follow-up test commit closing out a Task 2 acceptance criterion discovered after that commit landed):

1. **Task 1: The dated FX snapshot and a reader that refuses rather than derives** — `17d9d30` (feat)
2. **Task 2: The London cost profile, in GBP, from BECTU rates and State Department per diem** — `7dd4716` (feat)
3. **Task 2 follow-up: London's not_priced-empty and seasonality-state tests** — `4fc0803` (test)
4. **Task 3: Per-component conversion into a comparable total** — `b7582ad` (feat)

**Plan metadata:** commit hash recorded after this SUMMARY is committed.

## Files Created/Modified

- `engine/fx.py` — new; `FxSnapshot`, `load_fx_snapshot`, `convert`, `rate_figure`, `SUPPORTED_CURRENCY_CODES`
- `data/fx/gbp-usd.yaml` — new, `basis` implied by field shape (`sourced` per Figure output), quoted strings (RD-01)
- `data/union_rates/bectu.yaml` — new; camera and general_crew craft rows, both `basis: sourced`
- `data/union_rates/fringe_schedules.yaml` — BECTU fringe entry added (UK-specific pension/NI estimates)
- `data/per_diem/state-dept/gb-london.yaml` — new; `lodging_flat_rate`, resolving Assumption A4
- `data/facilities/gb-london.yaml`, `data/tax_exemptions/gb-london.yaml` — new; five `modelling_assumption` categories, zero exemptions
- `data/cost_profiles/gb-london.yaml` — new; the full committed profile, `currency: "GBP"`, `jurisdiction_id: null`
- `engine/city_profile_lookup.py` — London aliases and UK country-suffix fallback
- `engine/landed_cost.py` — `aggregate(..., reporting_currency=)`, `LandedCost.reporting_currency/.source_currency/.fx_as_of_date`, `_convert_cost_lines`
- `sources/MANIFEST.yaml` — four new entries (Frankfurter, two Bectu PDFs, the State Dept HTML query result)
- `sources/fx/`, `sources/unions/`, `sources/state-dept/` — new archived documents
- `tests/test_engine_fx.py` — new, 15 tests
- `tests/test_engine_landed_cost.py`, `tests/test_engine_cost_localizer.py` — new tests for the FX conversion mechanism and London's end-to-end pricing
- `tests/test_engine_union_rates.py` — updated for BECTU joining the fringe schedule
- `.planning/WINDOWS.md` — six new entries (London's absent seasonality resolving A4; the general_crew proxy-rate method choice; the missing UK VAT-exemption analog; BECTU's estimated fringe percentages; London's facilities sourcing gap; this plan's ruff-baseline delta)

## Decisions Made

See `key-decisions` in the frontmatter for the full list. The two most consequential:

- **`engine/cost_profile.py` and `engine/cost_localizer.py` ended this plan with zero changes** despite being declared in the plan's `files_modified` — this IS the deliverable the plan asked for (the union-/currency-agnosticism proof), not an unfinished task.
- **`app/services/spec.py` was deliberately left untouched.** It is not in the plan's declared files, the existing generic per-city loop already prices London through `resolve_city_to_profile_stem` with no code change, and `reporting_currency` stays an opt-in `aggregate()` parameter — the actual cross-city USD-comparable gap is plan 04-06's job.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Two pre-existing tests needed updating for BECTU joining the fringe schedule and the corrected MANIFEST row-id text**
- **Found during:** Task 3, running `uv run --frozen pytest tests/ -q` after landing the FX conversion mechanism
- **Issue:** `tests/test_engine_union_rates.py::test_load_fringe_schedules_reads_the_committed_file_for_all_four_unions` asserted the fixed four-union set, which correctly grows to five once BECTU's fringe entry lands (Task 2); `tests/test_engine_union_rates.py::test_every_sourced_union_rate_row_is_named_in_manifest_cited_for` failed because the `sources/MANIFEST.yaml` `cited_for` prose for the two Bectu PDFs described the rows in words rather than naming their exact `row_id` strings, which the repo-wide sourced-row-manifest-completeness gate requires verbatim.
- **Fix:** Renamed the fringe-schedule test to `test_load_fringe_schedules_reads_the_committed_file_for_all_five_unions` and widened its assertion; updated both `cited_for` entries to embed the literal `row_id` values (`bectu-camera-branch-london-2025`, `bectu-grips-branch-general-crew-london-2024`).
- **Files modified:** `tests/test_engine_union_rates.py`, `sources/MANIFEST.yaml`
- **Verification:** `uv run --frozen pytest tests/ -q` — 419 passed, 0 failed.
- **Committed in:** `b7582ad` (Task 3 commit)

**2. [Rule 3 - Blocking] Two Task 2 acceptance criteria (not_priced-empty and seasonality-state reporting for London) were not yet demonstrated by a test after Task 2's own commit**
- **Found during:** Post-Task-2 self-review, before starting Task 3
- **Issue:** Task 2's acceptance criteria required a demonstration that London's localized budget covers all ten `COST_CATEGORIES` with every figure's unit `GBP`, and that London's seasonality state is reported (mirroring the existing `SeasonalityState` pattern `tests/test_engine_seasonality.py` already establishes for New York/Los Angeles) — neither had a dedicated test yet.
- **Fix:** Added `test_london_prices_end_to_end_in_gbp_with_not_priced_empty` and `test_london_per_diem_carries_no_month_band_resolving_research_assumption_a4` to `tests/test_engine_cost_localizer.py`.
- **Files modified:** `tests/test_engine_cost_localizer.py`
- **Verification:** `uv run pytest tests/test_engine_cost_localizer.py -q` — 30 passed.
- **Committed in:** `4fc0803` (separate follow-up commit, before Task 3 began)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking issues necessary to keep the full test suite green and every acceptance criterion demonstrated). No scope creep.

## Issues Encountered

- **BECTU's Camera Branch rate card's main per-grade table (DoP, Camera Operator, 1st/2nd Assistant) is rendered as a graphic in the archived PDF and did not extract as machine-readable text.** The one row that DID extract as text — a base "London Living Wage" camera-crew day rate under the TV Drama/Major Motion Picture agreements — was used instead, disclosed explicitly in the file's own header and `sources/MANIFEST.yaml` note rather than guessed at from the graphic.
- **No single Bectu branch publishes a true cross-department blended day rate** for the nine non-camera departments — the Grips Branch card's "Grip" (non-key) role stands in for the whole `general_crew` bucket, a genuine, dated, sourced row but one specific grade, not an average. Recorded in `.planning/WINDOWS.md`.
- **No UK production VAT-relief analog to New York's or Los Angeles's exemption entries was identified or verified this session** — `data/tax_exemptions/gb-london.yaml` declares zero entries, stated explicitly rather than left as an unexplained absent file.
- **BECTU's fringe schedule (UK statutory pension minimum, employer NI) is `basis: estimated`, not `sourced`** — the primary Pensions Act 2008 / HMRC documents were not fetched and archived this session, unlike DGA's and WGA's own primary schedules landed in earlier plans.
- **Repo-wide ruff baseline grew from 394 to 415** (net +21) from this plan's new files — the same pre-existing FURB157/ISC004 patterns already tracked across the repo (entries 2, 5, 11, 14, 17), not a new category. Out of scope per the executor scope-boundary rule; recorded to `.planning/WINDOWS.md` (entry recorded this plan).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **London's total landed cost for the fixed test spec** (feature, 10 stage + 5 location shoot days, `crew_size=50`, 10 imported crew + 1 imported principal cast, "London, UK", start Q2 2026): `cost_total` (pre-incentive) is `£548,595` GBP; `incentive_state` is `"not_modelled"` (the UK rule file is out of this phase's scope, D-53), so `total_landed_cost` equals `£548,595` GBP as well. Converted per-component to USD at the committed 1.363 rate: `$747,735` USD — the exact `Decimal` sum of the 28 individually converted, quantized cost lines, with the FX rate itself (`1.363 USD per GBP`, dated 2026-08-26) visible as its own named, cited component.
- **The FX mechanism (`engine.fx`) is reusable as-is** for any later plan adding a fourth currency (a new committed `{base}-{quote}.yaml` snapshot is automatically discoverable by `load_fx_snapshot`, no code change required) and for the currency component of plan 04-06's gap decomposition, which can call `engine.fx.rate_figure` directly for its own dedicated currency line.
- **`aggregate(..., reporting_currency=)` is additive and unwired from `app/services/spec.py`** — Route A's live HTTP response still reports each city in its own native currency (New York/Los Angeles in USD, London in GBP). Plan 04-06 (the gap decomposition) is the natural place to call `aggregate(..., reporting_currency="USD")` for a London-vs-New-York comparison, since that is where a single reporting currency first becomes load-bearing for a cross-city number.
- **Ready for 04-06 (ranker/gap decomposition) and 04-07 (sensitivity).** The three floor cities (New York, Los Angeles, London) all now price end to end from committed data with `not_priced` empty, one is genuinely non-USD, and the FX component is a proven, tested, dated, cited Figure ready to be plugged into the gap panel's currency line.
- No blockers for 04-06.

---
*Phase: 04-cost-localization-landed-cost-outputs*
*Completed: 2026-08-27*

## Self-Check: PASSED

- All 12 created files confirmed present on disk: `engine/fx.py`, `data/fx/gbp-usd.yaml`, `data/union_rates/bectu.yaml`, `data/per_diem/state-dept/gb-london.yaml`, `data/facilities/gb-london.yaml`, `data/tax_exemptions/gb-london.yaml`, `data/cost_profiles/gb-london.yaml`, `tests/test_engine_fx.py`, `sources/fx/2026-08-26-frankfurter-gbp-usd.json`, `sources/unions/2026-08-26-bectu-camera-branch-ratecard-2025.pdf`, `sources/unions/2026-08-26-bectu-grips-branch-ratecard-2024.pdf`, `sources/state-dept/2026-08-26-allowances-state-gov-uk-per-diem.html`.
- All four task commits (`17d9d30`, `7dd4716`, `4fc0803`, `b7582ad`) confirmed present in `git log --oneline --all`.
- `uv run --frozen pytest tests/ -q` re-run fresh: 421 passed, 0 failed (baseline 398; +23 net new tests).
- Plan-level `<verification>`: `grep -rn "\.quantize(" engine/ | grep -v "engine/rounding.py"` returns no hits; `git diff --stat pyproject.toml uv.lock` is empty; London's converted total confirmed equal to the exact sum of its converted components; a missing FX pair and the reverse-direction pair both confirmed to raise; the FX rate confirmed present as its own dated, cited component in `cost_total.inputs`.
- Task-level acceptance criteria re-verified individually: `git diff --stat engine/union_rates.py engine/per_diem.py engine/facilities.py engine/exemptions.py` confirmed empty; `grep -rn "\"us-ny\"\|\"us-ca\"\|\"gb-london\"" engine/fx.py engine/cost_localizer.py` returns no hits; the repo-wide JUR-05 gate (`tests/test_engine_jurisdiction_additivity.py`) passes unmodified (4 passed).

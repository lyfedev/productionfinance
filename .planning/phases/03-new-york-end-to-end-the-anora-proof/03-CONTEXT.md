# Phase 3: New York End-to-End — The Anora Proof - Context

**Gathered:** 2026-08-25
**Status:** Ready for planning

<domain>
## Phase Boundary

The thinnest vertical slice: the first real, cited government figure on the hosted URL.

**What lands:**

1. **The input contract (INP-01…07).** A jurisdiction-agnostic `ProductionSpec` — production type and scale; shoot days split stage vs location; crew size *or* a tier; principal cast count and how many imported; crew imported vs hired locally; start window by quarter; candidate cities named by the user. Validated, normalized, round-trippable to JSON. This is the contract Phase 4 depends on.
2. **The budget refusal (INP-08).** Entering a budget figure is refused with a stated reason.
3. **The Anora proof (JUR-01, success criterion 3).** The hosted page returns `$991,190` against `$3,964,760` of qualified spend for New York, linked through to the NY ESD source document with its date, confidence tier and derivation.
4. **The CI validation gate (SHP-14).** Exact `Decimal` equality against disclosed New York figures asserted on every commit, and proven non-vacuous by deliberately corrupting a rule value and confirming the suite goes red.

**Not in this phase:**

- **No cost localization and no budget model.** Turning a `ProductionSpec` into a qualified-spend figure is ARCHITECTURE.md stage `[1] BudgetModelBuilder` → `[2] CityLocalizer`, and it is Phase 4's goal. Phase 3 owes Phase 4 the *contract*, not the model. See **D-36**.
- **No UI treatment.** ROADMAP is explicit: "a minimal form is sufficient here — deliberately no UI hint, because the real interface treatment is Phase 6 and must not be started early at the cost of the Anora proof." No map, no slider, no ranked list, no design system, no styling pass.
- **No other jurisdictions.** CA, NJ and CT rule models are Phase 5. Connecticut's rule file exists but cannot price through `price_jurisdiction` today (see **Windows #3** under Code Context) — Phase 3 must not offer it.
- **No live research.** Uncurated cities researched at request time is Phase 7. Phase 3 names an unknown city as *uncurated*, it does not research it.
- **No agent jobs.** Neither Job 1 (validation loop) nor Job 2 (live research) is touched. No `google-genai` call, no `parallel-web` call, no AI SDK import lands in this phase.
- **No proof panel.** The full four-beat demo proof surface is Phase 8 (PRV-06).

</domain>

<decisions>
## Implementation Decisions

The user delegated all four gray areas — "none. all good." — the same posture as Phase 1. Every decision below is Claude's call, made against ROADMAP.md, REQUIREMENTS.md, PROJECT.md, `.planning/research/ARCHITECTURE.md` and the Phase 1/2 artifacts. Each carries its rationale so it can be overturned on sight rather than re-derived.

Numbering continues from Phase 1's D-01…D-30. Phase 2 recorded its deviations as RD-01…RD-06 in `jurisdictions/SCOPE-FREEZE.md`, not as D-numbers, so there is no collision.

### The Anora Proof Path — reconciling INP-08 with success criterion 3

The phase's central collision: **INP-08 refuses budget input, but success criterion 3 requires the exact disclosed figure `$3,964,760` to reach the engine.** `engine/pipeline.py::price_jurisdiction(ruleset, qualified_spend: Decimal)` takes that number as an argument. Somebody has to supply it.

- **D-31: A disclosed qualified spend is not a budget figure, and the distinction is load-bearing.** A *budget* is a forward-looking dollar amount the producer supplies for a production that has not shot — forbidden, because "a dollar buys a different production in each city, which makes the comparison circular" (`PROJECT.md` line 72). A *disclosed qualified spend* is a government-published historical fact about a completed production, carrying a URL, a report period and a sha256 — it is a citation, not an input. INP-08 governs the first and has nothing to say about the second. — **Reversibility:** one-way — this distinction is what makes the Anora proof honest; collapsing it either kills success criterion 3 or reopens INP-08 through a side door.

- **D-32: Two visibly distinct routes on the hosted page, never one blended form.**
  - **Route A — "Price a production":** the INP-01…07 spec form. The visitor's own, unshot production. Returns no dollar figure in Phase 3 (see **D-36**).
  - **Route B — "Reproduce a disclosure":** select a committed validation pair (Anora is the default) and the page reproduces the government figure from `jurisdictions/us-ny.yaml` plus the fixture's disclosed spend, showing the disclosed figure, the computed figure, and whether they match **exactly**.

  Rationale: this makes D-02's interpreter-only boundary *visible in the product* rather than buried in a fixture comment, and Route B is verbatim the demo's opening beat — "open on validation, reproducing a published government award figure exactly with the government document alongside it" (`PROJECT.md` line 96). — **Reversibility:** costly — Phase 6's interface and Phase 8's proof panel are both built over this two-route split; merging them later means re-deciding where the honesty boundary is drawn on screen.

- **D-33: REJECTED — an "Anora preset" production spec whose derived spend is pinned to `$3,964,760`.** This is the specific fake to refuse. It would present a modelled number wearing the costume of a reproduced one, at the exact place — the demo's opening beat — where the product's whole claim is staked. `PROJECT.md`'s honesty constraint ("never present a researched figure as validated") forbids it, and the repo is public and inspectable, so the pin would be visible in the diff. Recorded as a rejected option so a later agent does not rediscover it as a shortcut. — **Reversibility:** one-way.

- **D-34: REJECTED — an expert-mode "I already know my qualified spend" field on the spec form.** It reopens INP-08 through the door a producer reaches for first, and it makes Route A's output indistinguishable from Route B's without reading the source. If a genuine need for it appears later it belongs behind an explicit, labelled "unvalidated, self-supplied basis" path — not on the primary form.

- **D-35: INP-08 is enforced twice — structurally, and visibly.**
  - **Structurally:** `ProductionSpec` carries **no money field at all**, and the request model sets `extra="forbid"`, so a posted budget field is a 422 from the schema, not a hand-written validator that can be forgotten.
  - **Visibly:** the form carries **one deliberate, labelled "Total budget" input that is always refused**, with the reason stated in the response: *cost is only ever an output; a fixed dollar amount buys a different production in each city, which makes the comparison circular.* Rationale: success criterion 2 reads "**Entering** a budget figure is refused with an explanation" — you cannot satisfy "entering … is refused" if there is nothing to enter, and a silently absent field teaches the visitor nothing. The refusal is the feature.

### Spec-to-Spend Boundary — what a described production returns in Phase 3

- **D-36: The spec form does NOT return a credit or cost figure in Phase 3.** Success criterion 1 says a visitor can "**describe** a production" — not price one. Phase 4's goal is "the same identical production is **priced** against each city's real local costs," and Phase 4's stated dependency on Phase 3 is "(input contract)" — the contract, not the model. Building a spec→spend model here would produce a plausible qualified-spend number with **no source**, which would then flow into `price_jurisdiction` and render a credit figure sitting on the same page as a validated one. That is precisely the "never present a researched figure as validated" violation, in the worst possible location. — **Reversibility:** costly — Phase 4 extends this seam rather than replacing it; pricing from the spec in Phase 3 would mean Phase 4 inherits an unsourced number already rendered on a public page.

- **D-37: What Route A actually returns — an honest, non-empty, fully-cited result.** Everything below is derivable from the spec plus `jurisdictions/us-ny.yaml` with zero cost modelling:
  1. The normalized spec echoed back — what the system understood, including a tier resolved to a crew headcount.
  2. Per named city: whether a **curated validated** model exists (`jurisdiction.status == curated_validated`), or none does. Never a suggestion, never a substitution.
  3. For New York: the **rule terms that will apply** — rate, mechanism (`refundable`), minimum spend, per-project and annual cap status, audit-fee treatment, estimated payout lag — each carrying its own source URL, `date_checked` and confidence tier straight off the rule file.
  4. An explicit, plain statement that **qualified spend is not yet derived** and that cost localization lands in Phase 4. Stated as a boundary, never as a spinner, a placeholder number, or a `sleep()` behind a progress bar.

- **D-38: INP-03's tier resolves to a crew headcount in Phase 3; the tier→department-ratio table is Phase 4's.** Department ratios only matter once departments are being costed. Phase 3's `ProductionSpec` accepts *either* an explicit crew size *or* a tier, and resolves a tier to a headcount range via a committed YAML table. — **Reversibility:** reversible — Phase 4 adds ratio columns to the same table.

- **D-39: The crew-tier table is labelled a modelling assumption, not a sourced figure, and may never carry the `validated` confidence tier.** There is no government or public source for crew composition — `PROJECT.md` line 78 states non-union local labour rates are not public ("that is what Entertainment Partners and Cast & Crew sell"). The table ships with an explicit provenance note saying so. — **Reversibility:** one-way — a modelling assumption that ever renders as `validated` is the exact dishonesty PRV-02 and the Phase 8 proof panel exist to prevent.

- **D-40: INP-07 — cities are free-text, and the system never suggests one.** No dropdown, no autocomplete, no "popular cities," no nearest-match substitution. An unrecognized city is **accepted** and marked *no curated model*, never rejected and never silently replaced. The requirement's clause "the system never suggests them" is a product commitment, not a UI convenience. — **Reversibility:** costly — Phase 7's live research attaches to exactly this "uncurated" state.

- **D-41: INP-06 captures quarter **and** year, not a bare quarter.** `jurisdictions/us-ny.yaml` already carries `effective_dates.rule_version_effective_from`, Phase 4 needs the year for seasonality, and Phase 2's `ArrivalTiming` computes a real estimated date from `payout_lag.typical_days` — all three need an anchored year. Validate the window is sane rather than open-ended.

### Form and Result Shape — API-first, server-rendered

- **D-42: Server-rendered HTML from FastAPI via Jinja2. No React, no Vite, no npm, no node_modules in Phase 3.** `research/STACK.md` commits to React 19 + Vite 8 + MapLibre — for **Phase 6**. Reasons to hold:
  - Phase 6 is a rewrite in a different technology regardless; a SPA started now is either thrown away or, worse, becomes the temptation to start the interface treatment ROADMAP explicitly forbids starting early.
  - A Vite build adds `npm ci && vite build` to the D-19 `git pull` + `deploy.sh` path on a box where **01-07's resize was deferred** — the instance is still `nano_2_0` (472 MB), measured at **284 MB available with `prodfin.service` running** (STATE.md, 2026-08-25). A node toolchain there is real risk for zero Phase 3 gain.
  - `jinja2` is a plain templating library, no new vendor, and cannot trip the SHP-07 lockfile gate.
  — **Reversibility:** reversible — Phase 6 swaps the presentation layer; see D-43 for why nothing is wasted.

- **D-43: API-first — the JSON endpoints are the durable artifact, the HTML is a thin consumer of the same handlers.** Phase 3 builds the endpoints properly and renders server-side from the identical response objects. Phase 6's React app then consumes the same JSON, and Phase 7's live-research job and Phase 9's scheduler call the same handlers. Nothing built here is throwaway except the templates. — **Reversibility:** costly — Phases 4, 6, 7 and 9 all bind to this contract.

- **D-44: `engine/` stays pure and HTTP-free.** Phase 2 established `engine/` as jurisdiction-agnostic pure functions over immutable values, with `pipeline.py` as the single public entry point. Routers, request/response models and templates live under `app/`. `ProductionSpec` itself is domain data, not transport, so it belongs in `engine/` (e.g. `engine/spec.py`) — but nothing in `engine/` may import from `fastapi`. — **Reversibility:** costly — JUR-05's "add a jurisdiction as a rule file alone" proof and Phase 9's CLI entry point both depend on `engine/` being importable without a web stack.

- **D-45: The `Figure` derivation tree serializes in full, recursively — not flattened to a summary.** `engine/figure.py`'s `Figure` carries `inputs` as a recursive tuple, which *is* the derivation DAG and *is* the product's central claim. Phase 6's click-through-to-source panel and Phase 8's proof panel both need the whole tree; flattening now means re-deriving it later. Anora's tree is small — depth is not a performance concern at this scale. — **Reversibility:** costly — the response shape is the contract Phases 6 and 8 render against.

- **D-46: Every figure on screen shows value, source URL (clickable), `date_checked`, confidence tier, and its derivation reason** — PRV-01/02/03, which Phase 2 already property-tests against a real Anora-priced tree. Route B additionally shows the **disclosed** figure, the **computed** figure, and an explicit match/mismatch verdict — never a single bare number that leaves agreement to be inferred.

- **D-47: `GET /health`'s response is frozen at exactly `status`, `version`, `git_sha`, `boot_time`.** Phase 1 pinned this deliberately (T-01-03: no environment dump, no filesystem path, no dependency inventory). Phase 3 adds routes; it does not touch that contract.

- **D-48: Near-unstyled semantic HTML.** No design system, no CSS framework, no colour palette, no layout work. ROADMAP's "deliberately no UI hint" is a scope instruction, and Phase 6 owns the whole visual treatment. Enough CSS to be legible; nothing that reads as a design decision.

### SHP-14 — the CI validation gate and its non-vacuity proof

- **D-49: An automated mutation job in CI, not a one-time documented ritual.** A ritual proves the suite was non-vacuous *once, on the day it was run*. Suites go vacuous later — a fixture flips to `status: blocked`, a test gets skipped, a `parametrize` list silently empties — and nobody notices. `PROJECT.md`'s honesty constraint and D-26's blocking-not-report-only posture both point the same way, and Phase 8 must re-prove this: an automated job makes that re-proof a CI log rather than a re-enactment. — **Reversibility:** costly — Phase 8's SHP-14 re-proof reruns whatever shape lands here.

- **D-50: The mutation job's five steps, in order.** Run against a **scratch copy of the tree, never the working tree**, so a cancelled run cannot leave a corrupted rule file behind:
  1. Assert the validation suite is **green unmutated** — a suite already red proves nothing.
  2. Assert it **collected a non-zero count of exact-mode New York assertions**. This is the step that actually catches vacuity; an empty `parametrize` is the real failure mode and it passes silently without this check.
  3. Apply a declared mutation to `jurisdictions/us-ny.yaml` — perturb the credit rate by **one basis point**. Small on purpose: only exact `Decimal` equality catches it, which is precisely the claim under test.
  4. Assert the suite is now **red, and red for the right reason** — the failure must name the New York exact-mode assertion, not an unrelated collection or import error.
  5. Restore and re-assert green.

- **D-51: Mutations are declared in a small committed table, not hard-coded in the job.** Each of the exact-mode anchors (Anora and Succession S4 for New York; Christmas Always for Connecticut once Windows #3 clears) can be added as a row without editing the workflow.

- **D-52: The existing `tests` CI job stays; `mutation-check` is added alongside it.** `.github/workflows/ci.yml` already runs `uv run --frozen pytest tests/ -q` on every push and PR, blocking. SHP-14's "runs in CI on every commit" half is therefore already satisfied — Phase 3 adds the non-vacuity half and the explicit exact-Decimal New York assertions, and does not restructure the four existing compliance gates.

### Claude's Discretion

The user answered "none. all good." to the gray-area selection, delegating **all four areas** in full. Every decision above is Claude's discretion. Downstream agents should treat them as working decisions with stated rationale — overturn any of them on the user's word without needing to re-argue the case.

Two decisions are load-bearing on the project's honesty claim and should be escalated rather than quietly reversed if they become inconvenient during planning or execution:

- D-33 — no Anora preset spec with a pinned spend.
- D-36 / D-39 — no unsourced qualified-spend figure rendered anywhere, and no modelling assumption wearing a `validated` tier.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` § "Phase 3: New York End-to-End — The Anora Proof" (lines 136-152) — goal, the four success criteria, the **Frontend note** ("a minimal form is sufficient here — deliberately no UI hint") and the **Why New York first** note explaining why SHP-14 is born here rather than at submission
- `.planning/ROADMAP.md` § "Phase 4: Cost Localization & Landed-Cost Outputs" (lines 153-169) — read for the **boundary**: Phase 4 owns cost localization and depends on Phase 3's *input contract*. This is the line D-36 draws.
- `.planning/REQUIREMENTS.md` lines 24-31 — INP-01 through INP-08 verbatim
- `.planning/REQUIREMENTS.md` line 78 — JUR-01
- `.planning/REQUIREMENTS.md` line 130 — SHP-14 verbatim, including the non-vacuity clause
- `.planning/PROJECT.md` line 41-42 — the seven physical inputs and the budget-rejection rule; line 72 (why a budget input makes the comparison circular); line 78 (non-union labour rates are not public — the basis for D-39); line 96 (the four demo beats, of which Route B is the first); line 114 (the honesty constraint)

### Prior-phase decisions that bind this phase
- `.planning/phases/01-foundations-source-truth-deploy-path/01-CONTEXT.md` § D-02 — **the interpreter-only boundary.** Rated one-way. D-31/D-32/D-36 are all built on it; read before designing either route.
- `.planning/phases/01-foundations-source-truth-deploy-path/01-CONTEXT.md` § D-14, D-17, D-18, D-19 — path mount at `/finance`, no Docker, uv venv under `/opt/prodfin`, `git pull` + `deploy/deploy.sh` deploy path
- `.planning/phases/01-foundations-source-truth-deploy-path/01-CONTEXT.md` § D-26, D-27, D-28 — CI blocks on red; the existing gate inventory SHP-14 is added to
- `jurisdictions/SCOPE-FREEZE.md` — RD-01…RD-06, Phase 2's dated list of disclosed schema simplifications. **RD-01 (every numeric YAML value is a quoted string) is a hard convention** — an unquoted decimal parses as a float and corrupts through `Decimal()`.
- `.planning/STATE.md` § Accumulated Context — the full Phase 1 and Phase 2 decision log, including the deferred `01-07` resize and the measured memory headroom that D-42 leans on
- `.planning/WINDOWS.md` — four open entries; **#3 is the one that touches this phase** (see Code Context)

### Engine contract (Phase 2 output — do not modify)
- `engine/pipeline.py` — `price_jurisdiction(ruleset, qualified_spend: Decimal)` and `price_programme`; the single public entry point. Note the signature takes qualified spend **as an argument** — this is the structural fact D-31 through D-36 resolve.
- `engine/figure.py` — the immutable `Figure` value object with its recursive `inputs` derivation DAG, `confidence`, `source_url`, `date_checked`. D-45's serialization target.
- `engine/models.py` — `JurisdictionRuleSet`, `Jurisdiction`, `Programme`; the load-time validators for programme-edge resolution (WR-01/WR-02) and non-empty `programmes` (WR-04)
- `engine/qualifying_base.py` — `SpendBreakdown` and `SpendBreakdown.from_total()`; its docstring states the D-02 boundary explicitly ("Phase 2 never derives a SpendBreakdown itself")
- `engine/rounding.py` — `quantize_money`; the pinned rounding contract
- `jurisdictions/us-ny.yaml` — the curated New York rule file, `status: curated_validated`, three cited HIGH-confidence sources. Its header documents what it deliberately does **not** model (the separate Tax Law 24-d indie credit; the diversity bonus credit).

### Validation pairs and the CI gate
- `tests/fixtures/validation_pairs/ny_anora.yaml` — the anchor: `qualified_spend: "3964760"`, `credit_amount: "991190"`, `assertion.mode: exact`, sha256-pinned ESD PDF. Its `notes` field restates the D-02 boundary.
- `tests/fixtures/validation_pairs/ny_succession_s4.yaml`, `ny_gilded_age_s2.yaml` — the other two NY pairs; Gilded Age is `mode: bounded` and must not be used as an exact-equality anchor
- `tests/test_engine_against_validation_pairs.py` — the existing golden test, re-coupled to `price_jurisdiction` in plan 02-09. The suite SHP-14's mutation job asserts on.
- `tests/test_validation_pair_fixtures.py` — the fixture-integrity guards (jurisdiction coverage, pair count, per-stage denominator) added in plan 01-04
- `.github/workflows/ci.yml` — the four existing blocking gates plus the `tests` job. D-52 adds to this file; it does not restructure it.
- `sources/ny/2026-08-24-esd-q3-film-report-2025.pdf` and `sources/MANIFEST.yaml` — the archived source document Route B links to, and the manifest reconciling sha256 to on-disk bytes

### Architecture and stack
- `.planning/research/ARCHITECTURE.md` § Q1 "The Core Computation Pipeline" (lines 81-135) — **the stage diagram is the map for this phase.** Stage `[1] BudgetModelBuilder` (`ProductionSpec` → `CanonicalBudget`) and `[2] CityLocalizer` are Phase 4; stages `[3]`–`[5]` are built. Read the "seam that matters most" paragraph — it is the architectural statement of D-36.
- `.planning/research/ARCHITECTURE.md` lines 505-545 — the build-order diagram; its "THINNEST VERTICAL SLICE" block describes this phase almost verbatim, including the `$3,964,760 → $991,190` display. **Read with corrections:** it assumes nginx, Postgres and an S3 bucket, all three of which ROADMAP/PROJECT.md and Phase 1's D-08/D-16/D-17 overrule.
- `.planning/research/STACK.md` — versions and rationale. **Its React/Vite/MapLibre frontend recommendation is deliberately deferred to Phase 6 by D-42**, not rejected.
- `.claude/CLAUDE.md` — the AI-vendor boundary and the forbidden-dependency list. Phase 3 adds no AI SDK; if a plan proposes one, that is a scope error.
- `deploy/README.md` — the Apache `ProxyPass /finance` path mount, the `PRODFIN_PUBLIC_PATH` mechanism, and the documented pre-existing `www` redirect that must not be mistaken for a regression

### Governing brief
- `productionfinance-brief.md` — governs wherever the two briefs disagree (PROJECT.md states this explicitly)
- `feasibility-incentives.md` lines 243-266 — the production/award table and, critically, line 263: disclosures give total qualified spend and top-line labour/hours/wages, **not the full input vector**. This sentence is the origin of D-02 and therefore of D-31/D-36.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`engine/pipeline.py::price_jurisdiction`** — complete and proven. Reproduces Anora's `Decimal('991190')` end-to-end from `jurisdictions/us-ny.yaml` today, in `tests/test_engine_against_validation_pairs.py`. Route B is a thin caller of this function plus a fixture read. **The engine work for success criterion 3 is already done** — Phase 3 is exposing it, not building it.
- **`engine/figure.py::Figure`** — carries `value`, `unit`, `label`, `derivation`, recursive `inputs`, `source_url`, `date_checked`, `confidence`, `live_fetched_this_run`. Every field D-46 needs to render is already on the object; no model change is required to cite a figure.
- **`app/main.py`** — the FastAPI app, `__version__`, the `PRODFIN_PUBLIC_PATH` prefix handling (already load-bearing: an absolute-path link broke under the `/finance` mount in plan 01-09 and was fixed via this variable), and `_resolve_git_sha()`. Extend this app; the `/health` contract is frozen per D-47.
- **`tests/fixtures/validation_pairs/*.yaml`** — twelve committed pairs with `assertion.mode`, `status`, `source_document_sha256`. Route B's pair selector reads this directory; the mutation job asserts over the `mode: exact` subset.
- **`.github/workflows/ci.yml`** — five jobs already blocking on every push and PR. `mutation-check` slots in beside them with the same `astral-sh/setup-uv@v5` + `uv run --frozen` pattern the `tests` job already uses.
- **`.gitleaks.toml`** — carries one scoped literal-string allowlist entry from plan 01-08 (a false-positive on an NJEDA Power BI citation URL). Extend if a new citation trips the scanner; do not broaden it to a pattern.

### Established Patterns
- **`engine/` is jurisdiction-agnostic and HTTP-free.** Nothing in `engine/` is named for a jurisdiction or branches on a jurisdiction id string (JUR-05, proven by `zz-fixture-throwaway.yaml` pricing with a zero-line diff to `engine/`). D-44 preserves this.
- **Quoted-string decimals everywhere (RD-01).** Every numeric YAML value is a quoted string; `engine/models.py` types the field `Decimal`. An unquoted `0.25` parses as a float and corrupts. This applies to any new YAML Phase 3 writes, including D-38's crew-tier table.
- **Money is `Decimal`, never float, quantized through `engine/rounding.py::quantize_money`.** Property-tested in plan 02-02.
- **Provenance is structural, not aspirational.** Every `Figure` carries its own source and confidence; `combined_confidence` degrades a parent to the weakest input. A figure with no source is a figure that reports having no source — it does not silently borrow one.
- **Documentation-first commits.** Conventional-commit `docs(...)` / `feat(...)` messages; `git.branching_strategy` is `none`, so work commits directly to `main` with `create_tag: true`.
- **Findings are documented, not routed around.** Plan 02-09 hit a genuine blocker and recorded it to WINDOWS.md rather than working around it silently. Phase 3 follows the same rule.

### Integration Points
- **`app/main.py` has no router, no POST endpoint, no template engine.** Phase 3 writes the first of each. `jinja2` is a new direct dependency in `pyproject.toml` — it must appear in `uv.lock` and pass the `lockfile-scan` gate (it will; it is not on any forbidden list).
- **The `ProductionSpec` model is the phase's most consumed output.** Phase 4 (localization), Phase 6 (the real form), Phase 7 (live research request shape) and Phase 9 (the fixed reference production) all bind to it. Design it as the durable contract it is.
- **`SpendBreakdown.from_total()` is the seam Route B crosses** — disclosed spend in, `PricedJurisdiction` out. Route A never reaches it in Phase 3.
- **Deploy:** `git pull` + `deploy/deploy.sh` on the box, `prodfin.service` under systemd on `127.0.0.1:8000`, Apache `ProxyPass /finance`. New templates and static assets must land inside the deployed tree and resolve under the `/finance` prefix — the 01-09 absolute-path bug is the precedent.

### Known Constraint — WINDOWS.md #3 (open, from Phase 2)
`jurisdictions/us-ct.yaml`'s `transfer_discount.typical_rate_low/high` are both null (CGS 12-217jj(e)(1) states no market discount rate), so `engine.net_cash.transferable` correctly refuses to convert and **`price_jurisdiction` raises `ValueError` for every active Connecticut pair.** Phase 3 is New York only, so this does not block it — but Route B's pair selector must not offer a pair it cannot price, or if it does, it must surface the refusal honestly ("cannot be converted to net cash: no sourced transfer discount rate") rather than returning a 500. An unsourced rate must never be invented to make the page work.

### Known Constraint — the instance was never resized
Plan `01-07` (resize to `small_3_0`) was **deferred, not completed** — see `01-07-DEFERRED.md`. The box is still `nano_2_0`: 472 MB total, measured **284 MB available with `prodfin.service` running** post-reboot. This is the direct basis for D-42's no-npm/no-Vite call, and it is also unmeasured against any AI SDK import footprint (none lands in Phase 3, so the measurement stays valid through this phase).

</code_context>

<specifics>
## Specific Ideas

- **The anchor, exact:** Anora / New York — `$3,964,760` qualified spend → `$991,190` credit issued, a clean 25.0%. Matched to the dollar as `Decimal('991190')`. This is the number on the hosted page and the demo's opening beat.
- **The source document** Route B links to: `https://esd.ny.gov/sites/default/files/media/document/Q3-Film-Report-2025.pdf`, archived at `sources/ny/2026-08-24-esd-q3-film-report-2025.pdf`, sha256 `824e2f32...`, report period `2025-Q3`, checked `2026-08-24`.
- **The mutation's size is the point:** one basis point on New York's credit rate. Large enough that exact `Decimal` equality catches it; small enough that a tolerance-based or eyeball check would not. It tests the specific claim SHP-14 makes.
- **The refusal is a feature, not an omission.** A visible "Total budget" field that always refuses, with the circularity reason stated, demonstrates INP-08 to a judge in one interaction. A missing field demonstrates nothing.
- **Two routes, one engine.** Route A and Route B call into the same `engine/` and render from the same `Figure` shape. The difference between them is entirely *where the qualified spend came from* — and that is exactly the thing the page should make visible.

</specifics>

<deferred>
## Deferred Ideas

- **The spec→spend budget model** (ARCHITECTURE.md stages `[1] BudgetModelBuilder` and `[2] CityLocalizer`) — Phase 4. This is D-36's other half and the single largest thing deliberately left out of Phase 3.
- **Tier→department-ratio table** (the costing half of INP-03) — Phase 4, when departments are actually being priced. Phase 3 lands headcount only (D-38).
- **React 19 + Vite 8 + MapLibre, the map, the slider, the ranked list, and the whole design treatment** — Phase 6, per ROADMAP's explicit "must not be started early at the cost of the Anora proof." D-43 keeps the JSON API so this is additive.
- **The full proof panel** (PRV-06) and the four-beat demo surface — Phase 8. Phase 3 renders citations inline; it does not build the panel.
- **CA, NJ, CT jurisdiction models and the Job 1 validation-loop agent** — Phase 5.
- **Live research for uncurated cities** (Job 2, `parallel-web` + `google-genai`) — Phase 7. Phase 3 marks an unknown city *uncurated* (D-40) and stops there.
- **Extending the mutation table to CT's Christmas Always anchor** — blocked on WINDOWS.md #3 (`us-ct.yaml`'s unsourced transfer discount). D-51's table makes this a one-row addition once that clears.
- **An explicit "unvalidated, self-supplied basis" path** for a producer who genuinely knows their qualified spend — considered and rejected for Phase 3 (D-34). If it ever lands it must be a separate labelled route, never a field on the primary spec form.

</deferred>

---

*Phase: 3-New York End-to-End — The Anora Proof*
*Context gathered: 2026-08-25*

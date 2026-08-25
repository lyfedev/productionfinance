# Phase 3: New York End-to-End — The Anora Proof - Research

**Researched:** 2026-08-25
**Domain:** FastAPI HTTP surface (JSON + server-rendered HTML), a new jurisdiction-agnostic `ProductionSpec` domain model, and a CI mutation-testing job — layered on top of Phase 2's already-complete, already-proven engine
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

The user delegated all four gray areas — "none. all good." — the same posture as Phase 1. Every decision below is Claude's call, made against ROADMAP.md, REQUIREMENTS.md, PROJECT.md, `.planning/research/ARCHITECTURE.md` and the Phase 1/2 artifacts. Each carries its rationale so it can be overturned on sight rather than re-derived.

Numbering continues from Phase 1's D-01…D-30. Phase 2 recorded its deviations as RD-01…RD-06 in `jurisdictions/SCOPE-FREEZE.md`, not as D-numbers, so there is no collision.

**The Anora Proof Path — reconciling INP-08 with success criterion 3**

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

**Spec-to-Spend Boundary — what a described production returns in Phase 3**

- **D-36: The spec form does NOT return a credit or cost figure in Phase 3.** Success criterion 1 says a visitor can "**describe** a production" — not price one. Phase 4's goal is "the same identical production is **priced** against each city's real local costs," and Phase 4's stated dependency on Phase 3 is "(input contract)" — the contract, not the model. Building a spec→spend model here would produce a plausible qualified-spend number with **no source**, which would then flow into `price_jurisdiction` and render a credit figure sitting on the same page as a validated one. That is precisely the "never present a researched figure as validated" violation, in the worst possible location. — **Reversibility:** costly — Phase 4 extends this seam rather than replacing it; pricing from the spec in Phase 3 would mean Phase 4 inherits an unsourced number already rendered on a public page.

- **D-37: What Route A *does* return — an honest, non-empty, fully-cited result.** Everything below is derivable from the spec plus `jurisdictions/us-ny.yaml` with zero cost modelling:
  1. The normalized spec echoed back — what the system understood, including a tier resolved to a crew headcount.
  2. Per named city: whether a **curated validated** model exists (`jurisdiction.status == curated_validated`), or none does. Never a suggestion, never a substitution.
  3. For New York: the **rule terms that will apply** — rate, mechanism (`refundable`), minimum spend, per-project and annual cap status, audit-fee treatment, estimated payout lag — each carrying its own source URL, `date_checked` and confidence tier straight off the rule file.
  4. An explicit, plain statement that **qualified spend is not yet derived** and that cost localization lands in Phase 4. Stated as a boundary, never as a spinner, a placeholder number, or a `sleep()` behind a progress bar.

- **D-38: INP-03's tier resolves to a crew headcount in Phase 3; the tier→department-ratio table is Phase 4's.** Department ratios only matter once departments are being costed. Phase 3's `ProductionSpec` accepts *either* an explicit crew size *or* a tier, and resolves a tier to a headcount range via a committed YAML table. — **Reversibility:** reversible — Phase 4 adds ratio columns to the same table.

- **D-39: The crew-tier table is labelled a modelling assumption, not a sourced figure, and may never carry the `validated` confidence tier.** There is no government or public source for crew composition — `PROJECT.md` line 78 states non-union local labour rates are not public ("that is what Entertainment Partners and Cast & Crew sell"). The table ships with an explicit provenance note saying so. — **Reversibility:** one-way — a modelling assumption that ever renders as `validated` is the exact dishonesty PRV-02 and the Phase 8 proof panel exist to prevent.

- **D-40: INP-07 — cities are free-text, and the system never suggests one.** No dropdown, no autocomplete, no "popular cities," no nearest-match substitution. An unrecognized city is **accepted** and marked *no curated model*, never rejected and never silently replaced. The requirement's clause "the system never suggests them" is a product commitment, not a UI convenience. — **Reversibility:** costly — Phase 7's live research attaches to exactly this "uncurated" state.

- **D-41: INP-06 captures quarter **and** year, not a bare quarter.** `jurisdictions/us-ny.yaml` already carries `effective_dates.rule_version_effective_from`, Phase 4 needs the year for seasonality, and Phase 2's `ArrivalTiming` computes a real estimated date from `payout_lag.typical_days` — all three need an anchored year. Validate the window is sane rather than open-ended.

**Form and Result Shape — API-first, server-rendered**

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

**SHP-14 — the CI validation gate and its non-vacuity proof**

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

- **D-33** — no Anora preset spec with a pinned spend.
- **D-36 / D-39** — no unsourced qualified-spend figure rendered anywhere, and no modelling assumption wearing a `validated` tier.

### Deferred Ideas (OUT OF SCOPE)

- **The spec→spend budget model** (ARCHITECTURE.md stages `[1] BudgetModelBuilder` and `[2] CityLocalizer`) — Phase 4. This is D-36's other half and the single largest thing deliberately left out of Phase 3.
- **Tier→department-ratio table** (the costing half of INP-03) — Phase 4, when departments are actually being priced. Phase 3 lands headcount only (D-38).
- **React 19 + Vite 8 + MapLibre, the map, the slider, the ranked list, and the whole design treatment** — Phase 6, per ROADMAP's explicit "must not be started early at the cost of the Anora proof." D-43 keeps the JSON API so this is additive.
- **The full proof panel** (PRV-06) and the four-beat demo surface — Phase 8. Phase 3 renders citations inline; it does not build the panel.
- **CA, NJ, CT jurisdiction models and the Job 1 validation-loop agent** — Phase 5.
- **Live research for uncurated cities** (Job 2, `parallel-web` + `google-genai`) — Phase 7. Phase 3 marks an unknown city *uncurated* (D-40) and stops there.
- **Extending the mutation table to CT's Christmas Always anchor** — blocked on WINDOWS.md #3 (`us-ct.yaml`'s unsourced transfer discount). D-51's table makes this a one-row addition once that clears.
- **An explicit "unvalidated, self-supplied basis" path** for a producer who genuinely knows their qualified spend — considered and rejected for Phase 3 (D-34). If it ever lands it must be a separate labelled route, never a field on the primary spec form.
</user_constraints>

## Summary

Phase 3 does not touch `engine/`. Every number Route B needs already computes exactly: `engine.pipeline.price_jurisdiction(load_ruleset("jurisdictions/us-ny.yaml"), Decimal("3964760"))` reproduces `Decimal('991190')` today, proven by `tests/test_engine_against_validation_pairs.py::test_anora_reproduces_exactly_through_price_jurisdiction` [VERIFIED: tests/test_engine_against_validation_pairs.py:297-304, read this session]. This phase's real work is three things Phase 1/2 deliberately left undone: (1) a new `ProductionSpec` domain model (INP-01..07) and its explicit, always-refused "Total budget" field (INP-08); (2) two new HTTP surfaces — Route A (describe a production, get zero cost figures, per D-36) and Route B (reproduce Anora, per JUR-01) — built as a small JSON API with a thin Jinja2 HTML layer over the same handlers (D-42/D-43); and (3) a CI mutation job that proves SHP-14's suite is non-vacuous by deliberately corrupting `jurisdictions/us-ny.yaml`'s credit rate and watching the suite go red for the right reason (D-49..D-52).

Two concrete findings from this session change what the naive implementation would get wrong:

1. **`python-multipart` is required for ANY HTML `<form>` POST, not only file uploads.** Starlette's `request.form()` — which underlies every FastAPI `Form(...)` parameter — dispatches to either `MultiPartParser` or `FormParser` depending on `Content-Type`, but **both code paths require `python-multipart` to be installed**; its absence raises `AssertionError: The python-multipart library must be installed to use form parsing` at request time, not at import time — so a plain, no-JS `<form method="post">` submitting a standard `application/x-www-form-urlencoded` body (the default for a form with no `enctype` and no file input) will 500 on first submission if this dependency is missed [CITED: github.com/Kludex/starlette formparsers.py, corroborated by github.com/fastapi/fastapi discussion #6011]. Neither `jinja2` nor `python-multipart` is currently installed in this project's `uv`-managed venv [VERIFIED: `uv run python3 -c "import jinja2"` executed this session → `ModuleNotFoundError`; `import multipart` → `ModuleNotFoundError`].
2. **`Figure` is not JSON-serializable by `dataclasses.asdict()` alone.** `Figure.value: Decimal` and `Figure.date_checked: date` [VERIFIED: engine/figure.py:65-74, read this session — `value: Decimal`, `derivation: tuple[str, ...]`, `inputs: tuple["Figure", ...]`, `date_checked: date | None`, `confidence: Confidence`] both fail FastAPI's default JSON encoder unless explicitly converted (`Decimal`→`str`, never `float`, to avoid re-introducing Phase 2's own precision bug; `date`→ISO string). D-45 requires the full recursive `inputs` tree to serialize, not a flattened summary — this needs one small, explicitly-written recursive serializer, not `dataclasses.asdict()` called directly on a `Figure`.

**Primary recommendation:** Add exactly two new runtime dependencies (`jinja2`, `python-multipart`) via `uv add`; write `engine/spec.py::ProductionSpec` as a `StrictModel`-style Pydantic model (mirroring `engine/models.py`'s existing `extra="forbid"` convention) with **no money field of any kind**; build one small `app/services/` layer of plain Python functions that both the JSON routes and the Jinja2-rendering routes call identically (per D-43); and implement the SHP-14 mutation job as a bash CI script in `.github/scripts/` (matching the existing `lockfile-scan.sh`/`vendor-scan.sh` convention) driving a Python mutation-table script that operates only on a `mktemp -d` scratch copy of the repo, never the working tree (D-50).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INP-01 | User can specify production type and scale (feature / limited series / episodic) | Pattern 1 (`ProductionSpec.production_type`), Assumption A2 flags the "and scale" phrase for confirmation |
| INP-02 | User can specify shoot days, split between stage and location | Pattern 1 (`shoot_days_stage`, `shoot_days_location`) |
| INP-03 | User can specify crew size, or select a tier from which department ratios are inferred | Pattern 1 (`crew_size`/`crew_tier` mutual-exclusion validator), D-38/D-39 (headcount only in Phase 3, never `validated`), Pitfall 3 (cross-field validation hazard), `data/crew_tiers.yaml` in Recommended Project Structure |
| INP-04 | User can specify principal cast count and how many are imported | Pattern 1 (`principal_cast_count`, `principal_cast_imported_count`, imported-≤-total validator) |
| INP-05 | User can specify how much crew is imported versus hired locally | Pattern 1 (`crew_imported_count`, `crew_hired_locally_count`), Pitfall 3 |
| INP-06 | User can specify a start window by quarter | Pattern 1 (`start_quarter` + `start_year` per D-41) |
| INP-07 | User can name the candidate cities to be priced — the system never suggests them | Pattern 1 (`candidate_cities: list[str]`), Pitfall 5 + Open Question 2 (city→jurisdiction resolution table), Anti-Patterns (no fuzzy matching) |
| INP-08 | System rejects any budget figure as input; cost is only ever an output | Pattern 3 (two-layer enforcement: structural `extra="forbid"` + visible always-refused field), Pitfall 2 (why `extra="forbid"` alone is insufficient) |
| JUR-01 | New York — validated model, reproducing NY ESD quarterly report figures | Code Examples (Route B's complete `reproduce_disclosure()`), Architecture Patterns diagram (Route B), confirms `price_jurisdiction` already reproduces `Decimal('991190')` exactly — no new engine work |
| SHP-14 | Validation test suite runs in CI on every commit, exact equality against disclosed figures, proven non-vacuous by a deliberate rule-value corruption | Pattern 4 (the five-step mutation job), Validation Architecture test map, Assumption A5 (mutation mechanism), `.github/scripts/mutation-check.sh` in Recommended Project Structure |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `ProductionSpec` validation (INP-01..07) | Core computation pipeline (`engine/spec.py`, pure Pydantic, no FastAPI import) | API layer (constructs it from a request) | D-44: domain data belongs in `engine/`, even though this phase's engine never *prices* it (D-36); JUR-05/CLI-entry-point future callers need it importable without a web stack |
| Budget-refusal enforcement (INP-08) | API layer (route-level check + `extra="forbid"` schema gate) | — | Two independent enforcement points per D-35 — one structural (schema), one visible (a labelled always-refused field) — both live in `app/`, never in `engine/`, since refusing an HTTP input is a transport-layer concern |
| Route A result assembly (echoed spec + per-city curated-status + NY rule terms, zero cost) | API layer (`app/services/spec.py`, calls `engine/` read-only) | Jurisdiction rule engine (rule terms sourced from `jurisdictions/us-ny.yaml` via `engine.models.load_ruleset`) | D-37 requires *displaying* rule terms without computing a qualifying base — this is a read of `JurisdictionRuleSet`, not a pricing call |
| Route B computation (Anora reproduction) | Jurisdiction rule engine (`engine.pipeline.price_jurisdiction`, unmodified) | API layer (thin caller + disclosed-vs-computed comparison) | The engine work is complete (Phase 2); Route B's only new logic is "read a validation-pair fixture, call `price_jurisdiction`, compare, render" |
| HTML rendering | Presentation layer (Jinja2, `app/templates/`) | API layer (same response objects) | D-42/D-43: HTML is a thin consumer of the same Python objects the JSON routes return; no rendering logic duplicates business logic |
| CI mutation gate (SHP-14) | Delivery/compliance tier (`.github/workflows/ci.yml` + `.github/scripts/`) | — | Same tier as the existing `lockfile-scan`/`vendor-scan`/`commit-window`/`secret-scan` gates (Phase 1); a fifth blocking job, not application code |
| Crew-tier → headcount table (D-38) | Core computation pipeline (a committed, non-jurisdiction data file) | — | Explicitly *not* rule data (no `jurisdictions/` provenance requirement applies) — a modelling assumption, structurally separated per D-39 |

## Package Legitimacy Audit

Two new runtime dependencies this phase. Both checked via the `package-legitimacy check` seam against PyPI this session.

| Package | Registry | Age (per registry) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|---------------------|-----------|--------------|---------|-------------|
| `jinja2` | PyPI | published 2025-03-05 (latest release; project itself dates to 2008) | unknown (seam could not resolve PyPI download counts) | `github.com/pallets/jinja/` | SUS | Flagged only for `unknown-downloads` — the checker's signal, not a substantive finding. `jinja2` is the templating engine maintained by the Pallets organization (also maintains Flask, Click, Werkzeug) and is FastAPI's own documented default for `Jinja2Templates`. Planner should add a `checkpoint:human-verify` before install per protocol, but this is a formality here, not a real risk signal. |
| `python-multipart` | PyPI | published 2026-06-04 (latest release) | unknown (same seam limitation) | `github.com/Kludex/python-multipart` | SUS | Same `unknown-downloads`-only flag. Maintained by Kludex (Marcelo Trylesinski), the current lead maintainer of both Starlette and FastAPI — this is the exact package FastAPI's own official docs name as the required install for `Form()`/`request.form()` support. Same formality-only checkpoint recommendation as above. |

**Packages removed due to [SLOP] verdict:** none. **Packages flagged as suspicious [SUS]:** `jinja2`, `python-multipart` — both flagged solely because the legitimacy seam's PyPI download-count signal returned unresolvable, not because of any adverse repo/postinstall/age signal. Planner should still gate both installs behind a `checkpoint:human-verify` task per protocol; expect it to pass immediately given the maintainer identities above.

**Version verification (pip registry, this session):**
```
$ pip index versions jinja2
jinja2 (3.1.6)          # latest; this session's venv had 3.1.5 present system-wide, not in the uv venv
$ pip index versions python-multipart
python-multipart (0.0.32)   # latest
```
[VERIFIED: pip index versions, executed this session against the live PyPI registry]

## Standard Stack

### Core (additions to the already-locked stack — see `.claude/CLAUDE.md`, unchanged)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `jinja2` | 3.1.6 (latest, PyPI) [VERIFIED: pip index versions, this session] | Server-rendered HTML for Route A/B per D-42; `fastapi.templating.Jinja2Templates` | FastAPI's own documented default templating integration; zero new build tooling (no npm/Vite), satisfying D-42's memory-headroom constraint on the un-resized `nano_2_0` box |
| `python-multipart` | 0.0.32 (latest, PyPI) [VERIFIED: pip index versions, this session] | Required for FastAPI `Form(...)` parameters to parse the HTML form POST bodies Route A/B need | Not optional — confirmed this session that Starlette's form parser raises `AssertionError` at request time (not import time) without it, for **both** `application/x-www-form-urlencoded` and `multipart/form-data` bodies [CITED: github.com/Kludex/starlette formparsers.py; github.com/fastapi/fastapi discussion #6011] |

No other new dependencies. `pydantic`, `pyyaml`, `fastapi`, `uvicorn`, `pytest` are already locked (`pyproject.toml` read this session — `fastapi==0.141.1`, `pydantic>=2`, `pyyaml==6.0.3`, `pytest==9.1.1`).

### Supporting

None. `engine.pipeline.price_jurisdiction`, `engine.models.load_ruleset`, `engine.figure.Figure` are reused unmodified.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain HTML `<form>` POST + `Form(...)` (needs `python-multipart`) | A vanilla-JS `fetch()` call from the HTML page directly to the JSON API (no server-side form parsing, no new dependency) | Rejected as the primary path — D-42's "near-unstyled semantic HTML" and D-43's "HTML is a thin consumer of the same handlers" both point toward ordinary form-POST navigation over client-side JS. `python-multipart` is a two-line, zero-risk dependency addition; avoiding it to dodge one `uv add` is not a good trade. (A no-JS form also degrades better for a judge testing with JS disabled, which a fetch-only approach would not.) |
| A shared `app/services/` Python function called by both JSON and HTML routes | Duplicate logic in each route handler | Rejected — this is exactly the seam D-43 names as durable; duplicating it doubles the surface a future phase (4/6/7/9) has to keep in sync |

**Installation:**
```bash
uv add jinja2 python-multipart
```

## Architecture Patterns

### System Architecture Diagram

```
Visitor's browser
     │
     ├─── GET /  ───────────────────────────────────────────────┐
     │        (landing page: two links, Route A / Route B)      │
     │                                                            ▼
     ├─── GET /spec ──────────────► app/templates/spec_form.html  (D-32 Route A)
     │        (INP-01..07 fields + the always-refused "Total budget" field, D-35)
     │
     ├─── POST /spec (form) ──────┐
     │                             │
     └─── POST /api/v1/spec (JSON)┤
                                   ▼
                    app/services/spec.py::handle_spec_submission()
                    ┌──────────────────────────────────────────────┐
                    │ 1. Reject if "total_budget" present & non-    │
                    │    empty → friendly circularity explanation   │  (D-35, "visible")
                    │    (INP-08, success criterion 2)               │
                    │ 2. engine.spec.ProductionSpec.model_validate() │  (D-35, "structural":
                    │    — extra="forbid", no money field exists    │   extra field ⇒ 422)
                    │ 3. For each candidate_city: resolve to a       │
                    │    jurisdiction id or "no curated model"       │  (D-40 — never suggest)
                    │ 4. For us-ny hits: load_ruleset("jurisdictions │
                    │    /us-ny.yaml"), read rule TERMS (rate,       │
                    │    mechanism, min spend, caps, audit, timing)  │  (D-37 item 3)
                    │ 5. Resolve crew tier → headcount via the       │
                    │    committed crew-tier table (D-38), tagged    │
                    │    "researched" / modelling-assumption (D-39)  │
                    │ 6. NO qualifying-base call, NO price_jurisdic- │
                    │    tion call — explicit "not yet derived,      │
                    │    Phase 4" statement (D-36/D-37 item 4)       │
                    └──────────────────────┬───────────────────────┘
                                            ▼
                    SpecResult (plain Python object; JSON-serializable
                    via the recursive Figure-tree serializer below)
                                            │
              ┌─────────────────────────────┴─────────────────────────┐
              ▼                                                        ▼
    JSON route returns SpecResult              HTML route renders
    as-is (FastAPI's default encoder            spec_result.html from
    handles it once Decimal/date are            the SAME SpecResult object
    pre-converted to str/isoformat)              (D-43 — one handler, two views)


     ├─── GET /validate ──────────► app/templates/validate_form.html (D-32 Route B)
     │        (select a committed validation-pair fixture; Anora is the default)
     │
     ├─── POST /validate (form) ──┐
     │                             │
     └─── GET /api/v1/validate/{pair_id} (JSON)┤
                                   ▼
                    app/services/validate.py::reproduce_disclosure(pair_id)
                    ┌──────────────────────────────────────────────┐
                    │ 1. Load tests/fixtures/validation_pairs/      │
                    │    <pair_id>.yaml (yaml.safe_load — never     │
                    │    yaml.load/unsafe_load, established V5)     │
                    │ 2. ruleset = load_ruleset(RULESET_PATH_BY_    │
                    │    JURISDICTION[pair["jurisdiction_id"]])     │
                    │ 3. priced = price_jurisdiction(ruleset,        │
                    │    Decimal(pair["qualified_spend"]))          │  ← ALREADY PROVEN, Phase 2
                    │ 4. computed = priced total (or the matching   │
                    │    programme's gross_credit — RD-03 anchors   │
                    │    on gross credit, not net cash, matching    │
                    │    what a disclosure actually reports)        │
                    │ 5. disclosed = Decimal(pair["credit_amount"]) │
                    │ 6. verdict = "exact match" if computed ==     │
                    │    disclosed else "MISMATCH" (never silently  │
                    │    hidden — D-46)                              │
                    └──────────────────────┬───────────────────────┘
                                            ▼
                    ValidateResult (disclosed figure, computed Figure
                    tree — full recursive derivation, D-45 — verdict,
                    source_url, date_checked, confidence, link to the
                    archived NY ESD PDF)
```

### Recommended Project Structure
```
engine/
├── spec.py              # NEW: ProductionSpec (Pydantic, extra="forbid",
│                         #   no money field), CrewTier enum, resolve_crew_tier()
│                         #   — pure, no fastapi import (D-44)
└── figure_serialize.py   # NEW: recursive Figure -> JSON-safe dict (D-45);
                          #   pure, belongs in engine/ for the same reason
                          #   (a plain data transform, no HTTP coupling)

app/
├── main.py               # extend: mount routers, Jinja2Templates instance
├── routers/
│   ├── spec.py            # GET /spec (HTML), POST /spec (HTML form),
│   │                      #   POST /api/v1/spec (JSON) — all three call
│   │                      #   app/services/spec.py, never duplicate logic
│   └── validate.py         # GET /validate (HTML), POST /validate (HTML
│                          #   form), GET /api/v1/validate/{pair_id} (JSON)
├── services/
│   ├── spec.py             # handle_spec_submission() — the one place
│   │                      #   Route A's logic lives
│   ├── validate.py          # reproduce_disclosure() — the one place
│   │                      #   Route B's logic lives
│   └── city_lookup.py       # resolve_city_to_jurisdiction() — see Open
│                          #   Questions; a small, explicit lookup, never
│                          #   fuzzy/nearest-match (D-40)
└── templates/
    ├── base.html
    ├── index.html          # landing page: two links, Route A / Route B
    ├── spec_form.html
    ├── spec_result.html
    ├── validate_form.html
    └── validate_result.html

data/
└── crew_tiers.yaml         # NEW: D-38/D-39 — modelling-assumption headcount
                          #   ranges per tier, structurally separate from
                          #   jurisdictions/ (never `validated` confidence)

.github/scripts/
└── mutation-check.sh       # NEW: SHP-14 non-vacuity gate (D-49..D-52)

tests/
├── mutation_targets.yaml    # NEW: D-51 — declared mutation table (file,
│                          #   find/replace pair, expected failing test)
├── test_engine_spec.py      # ProductionSpec validation, extra="forbid",
│                          #   INP-08 no-money-field proof, crew-tier
│                          #   resolution
├── test_app_spec_route.py    # Route A: HTML + JSON, budget refusal
│                          #   (both structural 422 and visible friendly
│                          #   refusal), per-city curated/uncurated status
└── test_app_validate_route.py # Route B: Anora reproduces $991,190 via
                             #   both the JSON route and the HTML route
```

### Pattern 1: `ProductionSpec` — domain data in `engine/`, no money field, `extra="forbid"`

**What:** Mirror `engine/models.py`'s existing `StrictModel` convention exactly — a `BaseModel` subclass with `model_config = ConfigDict(extra="forbid")` — for `ProductionSpec`. No field of any type represents a dollar amount.
**When to use:** For the one, canonical `ProductionSpec` every later phase binds to (D-43's integration point).
**Example:**
```python
# engine/spec.py — mirrors engine/models.py's StrictModel pattern
# [VERIFIED: engine/models.py:94-97, read this session — the exact
#  ConfigDict(extra="forbid") convention this file reuses]
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductionSpec(StrictModel):
    # INP-01
    production_type: Literal["feature", "limited_series", "episodic"]
    # INP-02
    shoot_days_stage: int = Field(ge=0)
    shoot_days_location: int = Field(ge=0)
    # INP-03 — exactly one of the two must be supplied
    crew_size: int | None = Field(default=None, ge=1)
    crew_tier: Literal["micro", "small", "mid", "large", "tentpole"] | None = None
    # INP-04
    principal_cast_count: int = Field(ge=0)
    principal_cast_imported_count: int = Field(ge=0)
    # INP-05
    crew_imported_count: int = Field(ge=0)
    crew_hired_locally_count: int = Field(ge=0)
    # INP-06 — quarter AND year (D-41)
    start_quarter: Literal["Q1", "Q2", "Q3", "Q4"]
    start_year: int = Field(ge=2024, le=2036)  # 2036: NY's own sunset year (SOURCE-TRUTH.md SRC-01)
    # INP-07 — free text, never suggested (D-40)
    candidate_cities: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _exactly_one_crew_input(self) -> "ProductionSpec":
        if (self.crew_size is None) == (self.crew_tier is None):
            raise ValueError(
                "exactly one of crew_size or crew_tier must be supplied, never both, "
                "never neither"
            )
        return self

    @model_validator(mode="after")
    def _imported_cast_within_total(self) -> "ProductionSpec":
        if self.principal_cast_imported_count > self.principal_cast_count:
            raise ValueError("principal_cast_imported_count cannot exceed principal_cast_count")
        return self
    # NOTE: crew_imported_count + crew_hired_locally_count is validated
    # against crew_size ONLY when crew_size is explicit (a scalar to check
    # against) — when only crew_tier is given, the headcount is a resolved
    # RANGE (D-38), so no exact-sum check applies. See Common Pitfalls.
```

### Pattern 2: The recursive `Figure` JSON serializer (D-45)

**What:** A pure function in `engine/` (no FastAPI import) that walks `Figure.inputs` recursively and returns a JSON-safe nested `dict`, converting `Decimal`→`str` (never `float` — reusing Phase 2's own Finding 1 precision lesson) and `date`→ISO-8601 string.
**When to use:** Every place a `Figure` or `Figure` tree crosses the JSON boundary (Route B's response, and any figure Route A does emit, e.g. the NY rule-term Figures).
**Example:**
```python
# engine/figure_serialize.py
from __future__ import annotations
from engine.figure import Figure


def figure_to_dict(figure: Figure) -> dict:
    """Recursive, full-tree serialization — D-45 forbids flattening to a
    summary. Decimal -> str (never float, per 02-RESEARCH.md Finding 1's
    precision lesson); date -> ISO-8601 string; None stays None."""
    return {
        "figure_id": figure.figure_id,
        "value": str(figure.value),
        "unit": figure.unit,
        "label": figure.label,
        "derivation": list(figure.derivation),
        "source_url": figure.source_url,
        "date_checked": figure.date_checked.isoformat() if figure.date_checked else None,
        "confidence": figure.confidence,
        "live_fetched_this_run": figure.live_fetched_this_run,
        "inputs": [figure_to_dict(child) for child in figure.inputs],
    }
```

### Pattern 3: The always-refused "Total budget" field is a distinct check from `extra="forbid"` (D-35's two layers)

**What:** `extra="forbid"` on `ProductionSpec` gives a generic Pydantic `"Extra inputs are not permitted"` 422 for *any* unrecognized field — it does not know to say "cost is only ever an output." The visible, labelled "Total budget" field needs its own explicit check, upstream of `ProductionSpec` construction, so the friendly circularity explanation (success criterion 2's literal wording: "refused with an explanation") is what the visitor actually sees.
**Example:**
```python
# app/services/spec.py
from pydantic import BaseModel

REFUSAL_REASON = (
    "cost is only ever an output; a fixed dollar amount buys a different "
    "production in each city, which makes the comparison circular"
)


class SpecFormSubmission(BaseModel):
    """The raw incoming form shape — deliberately includes total_budget as
    a NAMED field (unlike ProductionSpec, which has none) so it can be
    caught and answered with the real reason, not a generic schema error."""
    # ... the seven INP fields, all as raw strings/ints from Form(...) ...
    total_budget: str | None = None


def handle_spec_submission(raw: SpecFormSubmission) -> "SpecResult | RefusalResult":
    if raw.total_budget not in (None, ""):
        return RefusalResult(reason=REFUSAL_REASON)  # HTTP 422, not 500 — see routers/spec.py
    spec = ProductionSpec.model_validate(raw.model_dump(exclude={"total_budget"}))
    # ... proceed with D-37's non-cost result assembly ...
```

### Pattern 4: SHP-14 mutation job — scratch copy, declared table, five ordered steps (D-49..D-52)

**What:** A bash CI job (matching `.github/scripts/lockfile-scan.sh`'s style: `set -uo pipefail`, `PASS:`/`FAIL:` prefixed output, explicit non-zero exit) that copies the checked-out tree to `$(mktemp -d)`, runs the five D-50 steps there, and never writes to the original working tree.
**Example:**
```bash
# .github/scripts/mutation-check.sh
#!/usr/bin/env bash
set -uo pipefail

SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT
cp -r . "$SCRATCH"   # never mutate the real working tree (D-50)
cd "$SCRATCH"

# Step 1: unmutated green
if ! uv run pytest tests/test_engine_against_validation_pairs.py -q; then
  echo "FAIL: validation-pair suite is already red BEFORE mutation — proves nothing" >&2
  exit 1
fi

# Step 2: non-zero exact-mode NY assertions actually collected — the real
# vacuity check (an empty parametrize passes silently without this)
COLLECTED=$(uv run pytest tests/test_engine_against_validation_pairs.py \
  -q --collect-only -k "ny" | grep -c "::" || true)
if [ "$COLLECTED" -eq 0 ]; then
  echo "FAIL: zero New York test items collected — suite would be vacuously green" >&2
  exit 1
fi
echo "PASS: $COLLECTED New York test item(s) collected"

# Step 3: apply the declared mutation (one basis point on NY's credit rate)
# Table-driven per D-51 — see tests/mutation_targets.yaml for the real
# find/replace pair and expected-red test name; this is illustrative.
sed -i.bak 's/base_rate: "0.25"/base_rate: "0.2501"/' jurisdictions/us-ny.yaml
if ! grep -q '"0.2501"' jurisdictions/us-ny.yaml; then
  echo "FAIL: mutation did not apply — check the sed pattern still matches" >&2
  exit 1
fi

# Step 4: red, and red for the RIGHT reason — the named NY exact-mode test,
# not an unrelated collection/import error
if uv run pytest tests/test_engine_against_validation_pairs.py::test_anora_reproduces_exactly -q; then
  echo "FAIL: mutated suite is still green — SHP-14's non-vacuity claim is FALSE" >&2
  exit 1
fi
echo "PASS: mutated suite correctly failed test_anora_reproduces_exactly"

# Step 5: restore and re-assert green (on the SCRATCH copy only)
mv jurisdictions/us-ny.yaml.bak jurisdictions/us-ny.yaml
uv run pytest tests/test_engine_against_validation_pairs.py -q
echo "PASS: mutation-check — suite is green unmutated, red under mutation, green restored"
```

### Anti-Patterns to Avoid
- **A budget field that is silently dropped by `extra="forbid"` with no friendly message:** technically satisfies "rejects a budget figure" but not success criterion 2's literal "entering a budget figure is refused **with an explanation**." Both layers of D-35 are required, not either one alone.
- **`Decimal` or `date` fields serialized via bare `dataclasses.asdict(figure)`:** raises `TypeError: Object of type Decimal is not JSON serializable` the first time a `Figure` crosses `/api/v1/validate/{pair_id}`. Use Pattern 2's explicit recursive serializer.
- **Constructing a spec→spend model "just this once" to make Route A feel complete:** this is exactly D-36's forbidden move. Route A's result is complete without a dollar figure — an explicit "qualifying base is not yet derived; cost localization is Phase 4" statement is the correct, honest terminal state, not a placeholder to fill in.
- **Fuzzy-matching, autocompleting, or "closest curated jurisdiction" logic for `candidate_cities`:** D-40 forbids this categorically. A city with no exact match in the small resolution table is `no curated model`, full stop — never a suggestion.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form-body parsing | A hand-rolled `Content-Type` sniff + manual `urllib.parse.parse_qs` | FastAPI `Form(...)` + `python-multipart` | Already the framework-native path; hand-rolling reopens exactly the parsing edge cases (multipart boundaries, encoding) `python-multipart` exists to handle correctly |
| JSON schema validation of the request | Manual `if "total_budget" in raw: raise` checks scattered across routes | `ProductionSpec`'s `extra="forbid"` (Pydantic) for the structural layer, a small named `SpecFormSubmission` check for the visible layer (Pattern 3) | Already established as the project convention in `engine/models.py`'s `StrictModel`; consistency matters for a public, judged repo |
| Recursive dict→JSON walk of a `Figure` tree | A generic `to_json()`-via-`__dict__` reflection helper | The explicit, named `figure_to_dict()` (Pattern 2) | A reflection-based generic serializer would silently "work" on `Decimal` by producing a `float`-ish JSON number in some frameworks — reintroducing the exact precision class of bug Phase 2's Finding 1 already fenced off once |

**Key insight:** every "don't hand-roll" item here is really the same Phase 2 lesson recurring at the HTTP boundary instead of the engine boundary — Decimal precision and explicit, named code paths (never a generic reflection-based shortcut) are the project's standing convention, and this phase is where that convention first meets JSON serialization.

## Common Pitfalls

### Pitfall 1: `python-multipart` missing → 500 on first real form submission, not a startup failure
**What goes wrong:** The app boots fine, `/spec` (GET) renders fine, and the bug is invisible until a visitor actually submits the form — at which point Starlette raises `AssertionError` inside `request.form()`.
**Why it happens:** `Form(...)` type annotations don't trigger an import-time check; the assertion only fires when a request actually needs form parsing.
**How to avoid:** Add `python-multipart` to `pyproject.toml` explicitly (not relying on a transitive pull) and cover it with an integration test that actually POSTs form-encoded data to the route (not just a GET-only smoke test).
**Warning signs:** `tests/test_health.py`-style tests that only exercise `client.get(...)` never catch this — the new route tests must include at least one `client.post(url, data={...})` call.

### Pitfall 2: `extra="forbid"`'s generic error message doesn't satisfy success criterion 2's "with an explanation"
**What goes wrong:** A naive implementation adds `total_budget` nowhere, relies on `extra="forbid"` to 422 any stray field, and calls INP-08 done. The 422 body is Pydantic's generic `"Extra inputs are not permitted"` — technically a refusal, but not "refused with an explanation" in any reader-facing sense, and there is nothing on the form for a visitor to actually try (D-35's own stated rationale: "you cannot satisfy 'entering is refused' if there is nothing to enter").
**Why it happens:** `extra="forbid"` is the correct *structural* half of D-35 but is easy to mistake for the whole requirement.
**How to avoid:** Implement Pattern 3 exactly — a named, visible field, caught explicitly, with the circularity reason in the response body, before `ProductionSpec` is ever constructed.
**Warning signs:** A UAT/manual test of "type a number into the budget field and submit" that returns a bare 422 with no readable sentence.

### Pitfall 3: Cross-field validation of `crew_imported_count + crew_hired_locally_count` against `crew_size` breaks when only `crew_tier` is given
**What goes wrong:** A validator that asserts `crew_imported_count + crew_hired_locally_count == crew_size` unconditionally will `AttributeError`/`TypeError` (comparing against `None`) whenever a visitor supplies `crew_tier` instead of `crew_size` — which INP-03 explicitly allows as an alternative input.
**Why it happens:** The sum-equality check is a reasonable-looking validator that silently assumes `crew_size` is always populated.
**How to avoid:** Guard the check with `if self.crew_size is not None:` — when only `crew_tier` is supplied, `resolve_crew_tier()` returns a **range** (D-38), not a scalar to check a sum against; no equality check applies in that branch.
**Warning signs:** A test matrix that only ever exercises the `crew_size`-supplied path never catches this — a plan must include at least one `crew_tier`-only test case.

### Pitfall 4: A `Figure`'s `Decimal`/`date` fields crash FastAPI's default `JSONResponse` encoder
**What goes wrong:** Returning a raw `Figure` (or a dict containing one, via naive `asdict()`) from a route raises `TypeError: Object of type Decimal is not JSON serializable` at response-encoding time — a 500, not a validation error, so it is easy to miss in a quick manual GET-only check that happens to hit a code path with no `Figure` in it.
**Why it happens:** `Decimal` and `date` are not JSON-native types; Pydantic and Starlette's default encoders do not silently coerce them the way some other JSON libraries do.
**How to avoid:** Route every `Figure` (or `Figure` tree) through Pattern 2's `figure_to_dict()` before it reaches a response — never return a raw `Figure` object from a FastAPI route.
**Warning signs:** Any route test that only checks `response.status_code == 200` without ever getting far enough to hit a `Figure`-carrying branch of the response.

### Pitfall 5: Free-text city → jurisdiction resolution silently becomes a "suggestion" mechanism if built carelessly
**What goes wrong:** Any matching logic more permissive than exact/near-exact string comparison against a small, explicit, committed table (e.g. fuzzy string distance, "did you mean," or partial substring matching against every US city name) risks recommending or substituting a city — exactly what D-40 forbids ("the system never suggests them").
**Why it happens:** Free-text city input naturally invites "helpful" normalization (trimming whitespace, case-folding, handling "NYC" vs "New York City" vs "New York, NY") that can slide from *normalization* into *suggestion* without a clear line.
**How to avoid:** Keep the resolution table small, explicit, and committed (`app/services/city_lookup.py`); normalize only case/whitespace and a short list of known aliases for New York specifically (this phase's only curated jurisdiction); anything not an exact hit after that normalization is `no curated model`, reported plainly, never substituted. See Open Questions — this exact table needs to be written as part of this phase's plan, since no city gazetteer exists anywhere in the repo yet [VERIFIED: `grep -rn "gazetteer\|city_id" .planning/research/ARCHITECTURE.md` returned no gazetteer definition, only a `city_id` example string in an illustrative JSON payload].
**Warning signs:** A resolution function whose behavior a reviewer cannot predict by reading the table alone (any Levenshtein-distance/fuzzy-match call is a warning sign by itself).

## Runtime State Inventory

Not applicable — Phase 3 is net-new HTTP surface and a net-new domain model, not a rename/refactor/migration. No prior runtime state references anything this phase renames or moves. (Checked explicitly per the verification protocol, not left blank: no databases, no live service config, no OS-registered state, no secrets, and no build artifacts carry a name this phase changes.)

## Code Examples

### Route B — the complete Anora reproduction, calling only already-proven engine code
```python
# app/services/validate.py
from decimal import Decimal
from engine.models import load_ruleset
from engine.pipeline import price_jurisdiction
from engine.figure_serialize import figure_to_dict
import yaml

RULESET_PATH_BY_JURISDICTION = {"us-ny": "jurisdictions/us-ny.yaml"}  # NY only, Phase 3


def reproduce_disclosure(pair_id: str) -> dict:
    with open(f"tests/fixtures/validation_pairs/{pair_id}.yaml") as f:
        pair = yaml.safe_load(f)  # never yaml.load/unsafe_load

    ruleset = load_ruleset(RULESET_PATH_BY_JURISDICTION[pair["jurisdiction_id"]])
    qualified_spend = Decimal(pair["qualified_spend"])
    priced = price_jurisdiction(ruleset, qualified_spend)
    programme = next(p for p in priced.programmes if p.programme_id == pair["program_id"])
    computed = programme.gross_credit.value          # RD-03: gross credit, never net cash
    disclosed = Decimal(pair["credit_amount"])

    return {
        "production_title": pair["production_title"],
        "disclosed_qualified_spend": str(qualified_spend),
        "disclosed_credit": str(disclosed),
        "computed_credit": str(computed),
        "verdict": "exact match" if computed == disclosed else "MISMATCH",
        "source_url": pair["source_url"],
        "source_document": pair["source_document"],
        "date_checked": pair["date_checked"],
        "figure_tree": figure_to_dict(programme.gross_credit),
    }
```
This is the entire success-criterion-3 path: no new engine code, no new math — the reproduction is already `Decimal('991190')` exact [VERIFIED: tests/test_engine_against_validation_pairs.py:273-280,297-304, read this session — `test_anora_reproduces_exactly` and `test_anora_reproduces_exactly_through_price_jurisdiction` both assert `== Decimal("991190")`].

## State of the Art

Not applicable in the conventional sense — this is internal application-layer construction over an already-decided stack, not a fast-moving external API. The one relevant note: `jinja2`'s and `python-multipart`'s exact pinned versions (3.1.6 / 0.0.32) are current as of this session and should be re-verified only if `uv add` resolves something different at plan-execution time.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ProductionSpec`'s field names, types, and validators as drafted in Pattern 1 are a reasonable engineering interpretation of INP-01..07's prose, not verified against any authoritative external schema (no `ProductionSpec` code exists yet anywhere in the repo) | Pattern 1, Recommended Project Structure | If the planner or a later phase needs different field names/types, every consumer named in D-43 (Phases 4, 6, 7, 9) would need to follow — cheap to fix now (nothing built on it yet), expensive after Phase 4 starts consuming it |
| A2 | "production type **and scale**" (REQUIREMENTS.md INP-01, PROJECT.md line 41) is satisfied by `production_type` alone (three enum values), with no separate numeric "scale" field (e.g. episode count) — this phrase is not further disambiguated anywhere in CONTEXT.md's decisions or ARCHITECTURE.md | Pattern 1 (`production_type` field) | If "scale" was meant to be a distinct field (e.g., episode/season count for `episodic`/`limited_series`), Route A's echoed spec would be missing a dimension a producer expects to enter — low-risk to add later since it's purely additive to `ProductionSpec`, but worth a discuss-phase confirmation before Phase 6 builds the real form around it |
| A3 | The crew-tier → headcount table (D-38) uses five illustrative tier labels (`micro`/`small`/`mid`/`large`/`tentpole`) with no sourced headcount ranges — D-39 already establishes these can never carry `validated` confidence, but the exact bands themselves are not derived from any cited source in this session | Pattern 1, Recommended Project Structure (`data/crew_tiers.yaml`) | Low risk structurally (D-39 already forces `researched`/modelling-assumption labeling), but the actual numbers need the planner or executor to pick defensible round numbers (e.g., informed by typical IATSE local crew sizes) and state that provenance note explicitly in the committed YAML |
| A4 | The city→jurisdiction resolution table (Pitfall 5, `app/services/city_lookup.py`) is scoped to New York only in Phase 3 — a small, hand-committed list of NY city name aliases, not a general US gazetteer | Common Pitfalls Pitfall 5, Recommended Project Structure | If this table is built more broadly (all curated jurisdictions) now, it's extra unused surface for Phase 5's CA/NJ/CT to extend; if built too narrowly (exact string match on "New York" only), a visitor typing "NYC" or "Brooklyn" gets an honest but unhelpfully narrow "no curated model" — low risk either way, since D-40 forbids suggesting a fix regardless |
| A5 | The mutation size (one basis point, `"0.25"` → `"0.2501"`) and the `sed`-based exact-string-replace mutation mechanism (rather than a YAML-parse-and-rewrite round trip) are both recommended to preserve `jurisdictions/us-ny.yaml`'s existing comments (the RD-01 explanation header) that a `yaml.safe_load` + `yaml.safe_dump` round trip would silently strip | Pattern 4, Recommended Project Structure (`tests/mutation_targets.yaml`) | If a future rule-file edit reformats the `base_rate: "0.25"` line (e.g., different quoting/whitespace), the `sed` pattern in the mutation table would silently stop matching — Step 3 of Pattern 4 already includes a `grep` verification after the `sed` specifically to catch this loudly rather than silently mutating nothing |

## Open Questions

1. **Does "production type and scale" (INP-01) need a distinct numeric field beyond the three-value `production_type` enum?**
   - What we know: REQUIREMENTS.md and PROJECT.md both use the identical phrase "type and scale (feature / limited series / episodic)," listing exactly three values that read as the *type* axis.
   - What's unclear: whether "scale" names a second, unlisted dimension (episode count, season count) or is descriptive phrasing for the type enum itself.
   - Recommendation: ship `production_type` alone for Phase 3 (Pattern 1); flag for discuss-phase or a planner decision before Phase 6 builds the real form, since adding a field later is cheap but a producer noticing a missing "how many episodes" field during the demo is not.

2. **What is the concrete New York city-name alias set for Pitfall 5's resolution table?**
   - What we know: New York is the only curated jurisdiction in Phase 3; the jurisdiction is state-level (`jurisdictions/us-ny.yaml`'s `level: state`), so any NY city name should resolve to `us-ny`.
   - What's unclear: the exact committed list (e.g., does it need "Buffalo," "Rochester," "Albany," "Syracuse," "Yonkers," plus "NYC"/"New York City"/"Manhattan"/"Brooklyn" as NYC aliases, or is a simpler heuristic — matching a trailing ", NY" / ", New York" suffix — sufficient and less presumptuous?).
   - Recommendation: the trailing-suffix heuristic (", NY" / ", New York", case-insensitive) plus a short hand-picked list of the state's best-known production cities is the smallest defensible table; write it as an explicit, committed, reviewable list (never a live gazetteer API call — that would be Job 2/Phase 7 territory) so D-40's "never suggest" guarantee is auditable by reading one file.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All new code | ✓ [VERIFIED: `uv run python3 --version` via existing `.venv`] | 3.12.14 | — |
| `jinja2` | Route A/B HTML rendering | ✗ (not yet installed in the `uv` venv) [VERIFIED: `import jinja2` failed this session] | latest on PyPI: 3.1.6 | `uv add jinja2` — no blocker, trivial add |
| `python-multipart` | `Form(...)` parsing for Route A/B HTML POST | ✗ (not yet installed) [VERIFIED: `import multipart` failed this session] | latest on PyPI: 0.0.32 | `uv add python-multipart` — no blocker, trivial add |
| `pydantic`, `pyyaml`, `fastapi`, `pytest` | Everything else this phase touches | ✓ already locked | 2.13.4 / 6.0.3 / 0.141.1 / 9.1.1 | — |

**Missing dependencies with no fallback:** none — both new dependencies are a one-line `uv add` with zero installation risk on the current `nano_2_0` box (D-42 already reasoned through the memory headroom for a pure-Python-plus-templating addition; `jinja2`/`python-multipart` are both small, pure-Python, no compiled-extension packages).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 |
| Config file | `pyproject.toml` — `testpaths = ["tests"]` [VERIFIED: pyproject.toml, read this session] |
| Quick run command | `uv run pytest tests/test_engine_spec.py tests/test_app_spec_route.py tests/test_app_validate_route.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INP-01..07 | `ProductionSpec` accepts every valid combination, rejects invalid ones (missing required field, both/neither of crew_size+crew_tier, imported > total, extra field) | unit + schema | `uv run pytest tests/test_engine_spec.py -x` | ❌ Wave 0 |
| INP-08 | Structural: extra field 422s. Visible: `total_budget` non-empty returns the friendly circularity reason, not a generic error | unit + integration | `uv run pytest tests/test_app_spec_route.py::test_budget_field_always_refused -x` | ❌ Wave 0 |
| JUR-01 (success criterion 3) | POSTing/selecting Anora reproduces `$991,190` against `$3,964,760`, exact `Decimal` equality, via both the JSON route and the HTML route | golden-value, integration | `uv run pytest tests/test_app_validate_route.py::test_anora_reproduces_exactly_via_route -x` | ❌ Wave 0 |
| SHP-14 | Suite green unmutated; non-zero NY exact-mode assertions collected; red under a declared one-basis-point mutation, red for the right reason; restored and re-green | CI job (bash + pytest), not a pytest test itself | `.github/scripts/mutation-check.sh` run in CI | ❌ Wave 0 |
| (success criterion 1) | Full spec round-trips: submitted → echoed back, including a tier resolved to a headcount range | unit + integration | `uv run pytest tests/test_app_spec_route.py::test_spec_echoes_normalized_input -x` | ❌ Wave 0 |
| (D-40, success criterion 1 adjacent) | An uncurated city name is accepted and marked `no curated model`, never rejected, never substituted | unit | `uv run pytest tests/test_app_spec_route.py::test_uncurated_city_never_suggested -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command above
- **Per wave merge:** `uv run pytest tests/ -q` (full suite — must not regress Phase 1/2's existing ~50+ tests)
- **Phase gate:** full suite green, plus a manual/CI run of `.github/scripts/mutation-check.sh` before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `engine/spec.py`, `engine/figure_serialize.py` — do not exist yet
- [ ] `app/routers/spec.py`, `app/routers/validate.py`, `app/services/spec.py`, `app/services/validate.py`, `app/services/city_lookup.py`, `app/templates/*.html` — none exist yet (only `app/main.py` exists, single-file skeleton)
- [ ] `data/crew_tiers.yaml` — new top-level directory and file
- [ ] `.github/scripts/mutation-check.sh`, `tests/mutation_targets.yaml` — new
- [ ] `tests/test_engine_spec.py`, `tests/test_app_spec_route.py`, `tests/test_app_validate_route.py` — none exist yet
- [ ] `jinja2`, `python-multipart` — not yet added to `pyproject.toml`/`uv.lock`

*(No gap in shared test infrastructure: `testpaths = ["tests"]` already picks up any new file; `.github/workflows/ci.yml`'s existing `tests` job already runs `pytest tests/` — only the new `mutation-check` job needs adding, per D-52.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Per UI-01/PROJECT.md, the hosted URL is deliberately auth-free for an anonymous visitor; no auth surface in this or any Milestone-1 phase |
| V3 Session Management | No | No session state introduced this phase |
| V4 Access Control | No | No privileged operation exists |
| V5 Input Validation | Yes | (1) Pydantic `extra="forbid"` + typed fields on `ProductionSpec` reject any malformed/unexpected POST body structurally, matching `engine/models.py`'s established `StrictModel` convention. (2) `yaml.safe_load()` only, continuing the established convention, when Route B reads `tests/fixtures/validation_pairs/*.yaml` at request time — never `yaml.load`/`yaml.unsafe_load`. (3) `pair_id` (from the URL path / form) must be validated against a closed, known set (the committed fixture directory) before being interpolated into any filesystem path — an unvalidated `pair_id` used directly in `open(f"tests/fixtures/validation_pairs/{pair_id}.yaml")` is a path-traversal vector (`pair_id="../../../../etc/passwd"`-shaped input) if not constrained to a safe character set / checked against a known-file allowlist first. |
| V6 Cryptography | No | No cryptographic operations this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via an unvalidated `pair_id` route/form parameter reaching `open()` | Tampering / Information Disclosure | Validate `pair_id` against `RULESET_PATH_BY_JURISDICTION`-style closed enumeration of actually-committed fixture filenames (e.g. `pathlib.Path("tests/fixtures/validation_pairs") / f"{pair_id}.yaml"` then assert the resolved path's parent is exactly that directory, or simpler: check `pair_id` against a pre-enumerated `set` of legal ids) before ever calling `open()` |
| A malformed `ProductionSpec` POST body silently coerced into a plausible-but-wrong spec | Tampering | Continue the established `extra="forbid"` + typed-`Literal` convention; fail loud (422), never default |
| An HTML form submission missing `python-multipart` causing a 500 that leaks a stack trace in a non-debug-safe way | Information Disclosure (minor) | Standard FastAPI production config already avoids leaking tracebacks by default; still worth an explicit integration test (Pitfall 1) so this is caught in CI, not discovered live |

## Sources

### Primary (HIGH confidence)
- `engine/pipeline.py`, `engine/figure.py`, `engine/models.py`, `engine/qualifying_base.py`, `engine/credit.py` (read in full or substantial part this session) — the complete, unmodified engine contract this phase consumes
- `tests/test_engine_against_validation_pairs.py`, `tests/fixtures/validation_pairs/ny_anora.yaml` (read in full this session) — the exact, already-proven Anora reproduction path
- `jurisdictions/us-ny.yaml` (read in full this session) — the curated rule file Route B reads, including the exact `base_rate: "0.25"` string Pattern 4's mutation targets
- `app/main.py`, `app/__init__.py`, `tests/test_health.py` (read in full this session) — the existing skeleton this phase extends, and its established test-client pattern
- `.github/workflows/ci.yml`, `.github/scripts/lockfile-scan.sh`, `.github/scripts/vendor-scan.sh`, `.github/scripts/commit-window.sh` (read this session) — the existing CI-gate convention `mutation-check.sh` matches
- `pyproject.toml`, `uv.lock` (read this session) — locked dependency versions; confirmed `jinja2`/`python-multipart` are absent
- Direct execution this session (`uv run python3 -c "..."`) confirming `jinja2`/`python-multipart` are not importable in the current venv, and confirming `fastapi.templating.Jinja2Templates` raises a clear, named error without `jinja2` installed
- `.planning/phases/03-new-york-end-to-end-the-anora-proof/03-CONTEXT.md` — every D-31 through D-52 decision, read in full and treated as binding per this agent's role instructions
- `.planning/phases/02-engine-spine-incentive-interpreter/02-RESEARCH.md`, `02-PATTERNS.md` — Phase 2's Decimal-precision and provenance conventions this phase extends to the HTTP boundary
- `.planning/SOURCE-TRUTH.md`, `.planning/WINDOWS.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/PROJECT.md`, `.planning/research/ARCHITECTURE.md` (relevant sections read this session)
- `pip index versions jinja2` / `pip index versions python-multipart` (executed this session against the live PyPI registry) — current versions 3.1.6 / 0.0.32
- `gsd-tools query package-legitimacy check --ecosystem pypi jinja2 python-multipart` (executed this session) — both `SUS` on `unknown-downloads` only, repo URLs confirmed against the Pallets and Kludex (Starlette/FastAPI maintainer) GitHub organizations

### Secondary (MEDIUM confidence)
- WebSearch, cross-checked against the official FastAPI docs page name (`fastapi.tiangolo.com/advanced/templates/`) and a Starlette maintainer-repo source file citation (`github.com/Kludex/starlette formparsers.py`) and a FastAPI maintainer discussion thread (`github.com/fastapi/fastapi` discussion #6011) — the `python-multipart`-required-for-all-form-parsing finding, and the `jinja2`-required-for-`Jinja2Templates` finding

### Tertiary (LOW confidence)
- None — every substantive claim in this document is either read directly from a repo file this session, verified by direct execution, or a WebSearch result cross-checked against a named official/maintainer source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both new dependencies verified against the live PyPI registry this session; the requirement for `python-multipart` verified against Starlette's own source file plus a maintainer-authored GitHub discussion
- Architecture: HIGH — every pattern either reuses an existing, read-this-session repo convention (`StrictModel`, `yaml.safe_load`, the CI-script style) or is a small, explicitly-flagged new design decision (`ProductionSpec`'s exact fields, the crew-tier table, the city-lookup table) tagged in the Assumptions Log rather than asserted as settled fact
- Pitfalls: HIGH — Pitfalls 1, 2, 4 are each independently reproducible (missing dependency → `AssertionError`/`ModuleNotFoundError`/`TypeError`, confirmed by direct execution or an authoritative source citation this session); Pitfalls 3 and 5 are design-hazard warnings derived directly from the CONTEXT.md decisions (D-38, D-40) they protect

**Research date:** 2026-08-25
**Valid until:** No meaningful expiry for the architectural guidance (internal design over an already-locked stack). Re-verify `jinja2`/`python-multipart` versions only if `uv add` at plan-execution time resolves something newer than 3.1.6/0.0.32 — unlikely to change any guidance here, both are mature, stable APIs.

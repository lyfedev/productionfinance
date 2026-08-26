---
phase: 03-new-york-end-to-end-the-anora-proof
plan: 01
subsystem: api
tags: [fastapi, jinja2, python-multipart, decimal, provenance, validation]

# Dependency graph
requires:
  - phase: 02-engine-spine-incentive-interpreter
    provides: "price_jurisdiction(load_ruleset(...), Decimal(qualified_spend)) reproducing Anora's Decimal('991190') exactly; the Figure value object with its recursive derivation tree"
provides:
  - "GET /api/v1/validate/{pair_id} — JSON API reproducing a committed validation-pair fixture through the engine, with the full recursive Figure tree serialized"
  - "GET /validate/{pair_id} and GET+POST /validate — HTML views of the same result, plus a pair selector listing every fixture (selectable and unselectable, with reasons)"
  - "engine/figure_serialize.py::figure_to_dict — the one sanctioned Figure -> JSON-safe dict path"
  - "app/services/validate.py — the reusable reproduce_disclosure/selectable_pairs service both routes share (D-43)"
affects: [03-02-input-contract, 04-route-a-cost-pricing, 06-frontend, 07-live-research, 08-proof-panel]

actuals:
  tokens: 13335
  tasks: 3
  commits: 6

tech-stack:
  added: [jinja2==3.1.6, python-multipart==0.0.32]
  patterns:
    - "app/routers/ + app/services/ split — router holds no business logic, service holds no HTTP framework imports"
    - "One reproduce_disclosure() call shared by three route handlers (JSON, GET-HTML, POST-HTML) — D-43"
    - "Closed-set membership check as the first statement of reproduce_disclosure, before any path is built (T-03-01)"
    - "Every Decimal crosses the JSON boundary via str(), never a bare number"

key-files:
  created:
    - engine/figure_serialize.py
    - app/services/__init__.py
    - app/services/validate.py
    - app/routers/__init__.py
    - app/routers/validate.py
    - app/templates/base.html
    - app/templates/index.html
    - app/templates/validate_form.html
    - app/templates/validate_result.html
    - tests/test_app_validate_route.py
  modified:
    - pyproject.toml
    - uv.lock
    - app/main.py

key-decisions:
  - "Jinja2 autoescape left at its default (on) rather than disabled anywhere — one test assertion was adjusted to match the escaped apostrophe (&#39;) instead of weakening the security posture (T-03-04)"
  - "reproduce_disclosure catches price_jurisdiction's ValueError (the known Connecticut null-transfer-discount case, WINDOWS.md #3) and returns an honest refusal — never a 500, never an invented rate — even though no active NY pair exercises this path in Phase 3"

patterns-established:
  - "Pattern: router -> service -> engine, service owns REPO_ROOT-anchored paths, router owns HTTP status/response shaping only"

requirements-completed: [JUR-01]

coverage:
  - id: D1
    description: "GET /api/v1/validate/ny_anora reproduces the disclosed Anora credit exactly (computed_credit == disclosed_credit == '991190', verdict 'exact match'), with every money value a JSON string and the full recursive Figure tree serialized"
    requirement: "JUR-01"
    verification:
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_anora_reproduces_exactly_via_route"
        status: pass
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_money_crosses_json_boundary_as_string_never_number"
        status: pass
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_figure_tree_serializes_recursively"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /validate/ny_anora and POST /validate render the same result as HTML with both provenance chains and a clickable NY ESD source link"
    requirement: "JUR-01"
    verification:
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_html_route_shows_both_figures_and_the_source_link"
        status: pass
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_post_validate_reproduces_anora_via_form"
        status: pass
    human_judgment: false
  - id: D3
    description: "A non-member pair_id (including path-traversal-shaped input) is a 404 and never reaches an open() call; a bounded-mode pair never claims exact match; /health and the whole prior test suite are unchanged"
    requirement: "JUR-01"
    verification:
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_unknown_pair_id_returns_404"
        status: pass
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_traversal_shaped_pair_id_returns_404_and_reads_nothing"
        status: pass
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_bounded_pair_never_claims_exact_match"
        status: pass
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_health_contract_unchanged"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/ -q (174 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The hosted anonymous public URL (https://vockell.com/finance/) serves the Anora result over TLS after a real deploy"
    human_judgment: true
    rationale: "This is a property of the live Lightsail deployment, not the in-process TestClient — cannot be asserted by pytest. Deferred to end-of-phase harvesting per workflow.human_verify_mode=end-of-phase; consolidated into the phase's UAT.md by the phase-level verifier, not executed by this plan-level executor."
  - id: D5
    description: "Every pair the system cannot price (an out-of-scope jurisdiction, or a status:blocked disclosure) is listed on GET /validate with a plain-words reason, never silently omitted"
    verification:
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_validate_form_lists_anora_and_names_unselectable_pairs_with_reasons"
        status: pass
      - kind: integration
        ref: "tests/test_app_validate_route.py#test_post_validate_with_unselectable_pair_names_it_and_states_reason_not_500"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-25
status: complete
---

# Phase 3 Plan 1: New York End-to-End — The Anora Proof Summary

**Route B ("Reproduce a disclosure") reproduces New York's disclosed Anora tax credit exactly — $991,190 computed against $991,190 disclosed from $3,964,760 qualified spend — through a real HTTP request, with the full recursive `Figure` provenance tree and a pair selector that visibly names every fixture the system cannot yet price.**

## Performance

- **Duration:** ~20 min (checkpoint wait for T-03-SC package-legitimacy sign-off excluded)
- **Started:** 2026-08-25T18:33:59-07:00 (Task 1 commit)
- **Completed:** 2026-08-25T18:42:24-07:00 (Task 3 commit)
- **Tasks:** 3 (1 checkpoint, 2 code tasks each run RED→GREEN)
- **Files modified:** 13 (3 modified, 10 created)

## Accomplishments

- `GET /api/v1/validate/ny_anora` returns `computed_credit == "991190"`, `disclosed_credit == "991190"`, `disclosed_qualified_spend == "3964760"`, `verdict == "exact match"` — the phase's tracer, end-to-end through every layer this phase touches.
- Every `Decimal` crosses the JSON boundary as a string (`figure_tree` walked recursively and confirmed via a float-preserving parser); the recursive `Figure` derivation tree serializes to full depth with no cap.
- `GET /validate/ny_anora` and `POST /validate` render the identical result as HTML, both provenance chains (disclosure's and the rule file's) shown as two visibly separate blocks, plus a clickable link to the archived NY ESD Q3 2025 PDF.
- A non-member `pair_id` — including path-traversal-shaped input, both literal `../` and percent-encoded `%2F` — is always a 404, never a 200 or 500; the closed-set membership check runs before any filesystem path is built (T-03-01).
- `GET /validate` lists every committed validation-pair fixture, including out-of-scope jurisdictions and `status: blocked` pairs, each with its own plain-words reason for being unselectable — never silently omitted.
- The `/health` contract and the entire prior 162-test suite are unchanged; full suite now at 174 tests, all green.

## Task Commits

1. **Task 1: Package legitimacy gate + `uv add jinja2 python-multipart`** — `3a55954` (chore) — checkpoint `gate="blocking-human"` cleared by human sign-off after live PyPI verification of both packages' source repos and versions.
2. **Task 2: End-to-end "Anora reproduces $991,190"** — `69f3dba` (test, RED) → `0bd3330` (feat, GREEN)
3. **Task 3: Pair selector, landing page, honest unselectable list** — `1537461` (test, RED) → `177d34d` (feat, GREEN)

_TDD tasks each produced RED→GREEN commit pairs; no REFACTOR commit was needed — the RED-phase implementation went straight to a clean GREEN with only two trivial ruff fixes (`__all__` sort order, verbose `Decimal("10000")`) folded into the GREEN commit._

## Files Created/Modified

- `engine/figure_serialize.py` — pure `figure_to_dict(figure) -> dict`, no web-framework import (D-44), full recursion (D-45)
- `app/services/validate.py` — `reproduce_disclosure`, `selectable_pairs`, `UnknownPairError`, `ValidateResult`, `SelectablePair`, all filesystem paths anchored to `REPO_ROOT`
- `app/routers/validate.py` — `GET/POST /validate`, `GET /validate/{pair_id}`, `GET /api/v1/validate/{pair_id}`, all four routes calling the identical service function
- `app/templates/base.html`, `index.html`, `validate_form.html`, `validate_result.html` — near-unstyled semantic HTML (D-48), Jinja2's default autoescape left on throughout
- `app/main.py` — mounts `Jinja2Templates` and the validate router; `/health` handler left byte-for-byte unchanged (D-47); `index()` now template-rendered instead of inline HTML
- `tests/test_app_validate_route.py` — 12 tests: golden-value, JSON-boundary-type, recursive-tree, 404/traversal, HTML rendering, bounded-verdict, health-contract, form listing, POST reproduction, POST rejection, landing page
- `pyproject.toml`, `uv.lock` — `jinja2>=3.1.6`, `python-multipart>=0.0.32` added together via `uv add`

## Decisions Made

- Jinja2 autoescape stayed on by default everywhere; when a test assertion collided with the escaped apostrophe in "Don't Look Up", the test was corrected to expect `Don&#39;t Look Up` rather than disabling autoescape to make the raw string match (T-03-04 — free-text fixture values reach these templates).
- `reproduce_disclosure` wraps `price_jurisdiction`'s `ValueError` (the known Connecticut null-transfer-discount case from WINDOWS.md #3) into an honest refusal on `ValidateResult`, even though Phase 3 is NY-only and no active pair currently exercises this path — a guard rail against a future selectable pair hitting an unsourced-rate crash.

## Deviations from Plan

None — plan executed exactly as written. Two trivial ruff auto-fixes (sorting `__all__`, replacing `Decimal("10000")` with `Decimal(10000)` per FURB157) were applied to my own new code before the GREEN commit; these are lint-cleanliness fixes to code this plan itself introduced, not deviations from the plan's design.

## Issues Encountered

None. All acceptance criteria for both Task 2 and Task 3 verified directly:
- `uv run pytest tests/test_app_validate_route.py -q` — 12 passed
- `uv run pytest tests/ -q` — 174 passed, no Phase 1/2 regression
- `uv run python -c "...assert 'fastapi' not in sys.modules..."` — PASS, `engine/figure_serialize.py` confirmed HTTP-free
- `bash .github/scripts/lockfile-scan.sh` — PASS, clean
- `bash .github/scripts/vendor-scan.sh` — PASS, clean
- `uv run ruff check .` — 300 pre-existing errors unchanged from baseline (confirmed by isolated lint of every plan-owned file: only 3 pre-existing findings remain, all in Phase 1's untouched `_resolve_git_sha`, tracked as WINDOWS.md #2)
- Both literal-dots and percent-encoded-slash traversal probes confirmed 404, never 200/500

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Route B is fully live and provable in-process; the hosted deployment check (`https://vockell.com/finance/validate`) is deferred to end-of-phase per `workflow.human_verify_mode=end-of-phase` and will be harvested into the phase's UAT.md by the phase-level verifier, not executed by this plan.
- `app/routers/` and `app/services/` are now established as the first router/service split in the repo — plan 03-02's `app/routers/spec.py` and `app/services/spec.py` follow the identical shape.
- `PUBLIC_PATH`-prefixed links are used consistently in every new template; no absolute-path regression of the kind plan 01-09 found and fixed.
- No blockers for 03-02.

---
*Phase: 03-new-york-end-to-end-the-anora-proof*
*Completed: 2026-08-25*

## Self-Check: PASSED

All 10 created files and the SUMMARY.md itself verified present on disk (`[ -f ]`); all 5 task commits (`3a55954`, `69f3dba`, `0bd3330`, `1537461`, `177d34d`) verified in `git log --oneline --all`.

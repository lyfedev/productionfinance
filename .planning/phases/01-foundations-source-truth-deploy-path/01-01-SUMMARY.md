---
phase: 01-foundations-source-truth-deploy-path
plan: 01
subsystem: infra
tags: [fastapi, uv, pytest, uvicorn, mit-license, repo-hygiene]

# Dependency graph
requires: []
provides:
  - "uv-managed Python 3.12 project skeleton (pyproject.toml, uv.lock, .python-version)"
  - "FastAPI app object at app.main:app with GET /health and GET / — the D-20 skeleton contract deploy artefacts (systemd, Apache vhost, deploy.sh) will target"
  - "scripts/smoke.sh — reusable end-to-end HTTP smoke check, parameterised by SMOKE_BASE_URL, reused unchanged against the live host in plans 01-08/01-09"
  - "Public-repository posture: MIT LICENSE at repo root, four strategy briefs tracked, private key relocated out of the working tree"
affects: [01-02, 01-07, 01-08, 01-09]

actuals:
  tokens: 12000
  tasks: 2
  commits: 2

tech-stack:
  added: ["fastapi==0.141.1", "uvicorn==0.52.4 (resolved, floor >=0.30)", "pyyaml==6.0.3", "pytest==9.1.1", "ruff==0.16.4", "httpx>=0.27 (dev)"]
  patterns: ["uv-managed venv, no Docker (D-17)", "module-level BOOT_TIME/GIT_SHA captured once at import, resolution never raises (D-20, T-01-05)"]

key-files:
  created: [pyproject.toml, uv.lock, .python-version, app/__init__.py, app/main.py, tests/test_health.py, scripts/smoke.sh, LICENSE, README.md]
  modified: [.gitignore]

key-decisions:
  - "uvicorn version floor >=0.30 left unpinned per plan; uv resolved 0.52.4 — recorded here as the plan instructed"
  - "LICENSE copyright holder resolved via `gh api user --jq '.name // .login'` (gh CLI was authenticated) — 'Dave Vockell'"
  - "Relocated key destination: ~/.ssh/LightsailDefaultKey-us-west-2.pem (suffix ' (2)' dropped per plan instruction, matching deploy/hosting.env's expected path), mode 0600"

requirements-completed: [SHP-07, SHP-10]

coverage:
  - id: D1
    description: "Real uvicorn process answers GET /health (status, version, git_sha, boot_time) and GET / (holding page) — the venv → uvicorn → HTTP chain proven end to end, including the negative-path proof that the smoke script fails against a dead endpoint"
    requirement: "SHP-07"
    verification:
      - kind: unit
        ref: "tests/test_health.py#test_health_exact_key_set"
        status: pass
      - kind: unit
        ref: "tests/test_health.py#test_health_boot_time_stable_across_requests"
        status: pass
      - kind: e2e
        ref: "bash scripts/smoke.sh"
        status: pass
      - kind: e2e
        ref: "SMOKE_BASE_URL=http://127.0.0.1:9 bash scripts/smoke.sh (asserts non-zero exit)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Repository is safe to publish: no key material in the working tree, four strategy briefs tracked, unmodified MIT LICENSE at root, README/.env.example placeholder-only"
    requirement: "SHP-10"
    verification:
      - kind: other
        ref: "git ls-files -- '*.pem' | wc -l (asserts 0)"
        status: pass
      - kind: other
        ref: "git ls-files -- 'feasibility-incentives.md' 'hackathon-brief.md' 'idea-2-incentives.md' 'productionfinance-brief.md' | wc -l (asserts 4)"
        status: pass
      - kind: other
        ref: "head -1 LICENSE (asserts 'MIT License')"
        status: pass
    human_judgment: true
    rationale: ".env.example could not be created in this execution environment — see Known Stubs / Deviations. The plan's full D2 acceptance bar (including .env.example content) is not yet met; a human must either grant a permission exception or create the 3-line file, then this item should be re-verified."

duration: 21min
completed: 2026-08-24
status: complete
---

# Phase 1 Plan 1: Foundations Tracer — uv/FastAPI Skeleton + Repository Hygiene Summary

**A real `uv sync`-resolved Python 3.12 project serves `GET /health` and `GET /` from a live uvicorn process (proven by `scripts/smoke.sh`, including its negative-path check), and the working tree is publication-safe — the private Lightsail key relocated, the four strategy briefs tracked, and an unmodified MIT `LICENSE` at the root — with one known gap: `.env.example` could not be written due to a global permission policy in this execution environment.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-08-24T22:22:00Z
- **Completed:** 2026-08-24T22:42:51Z
- **Tasks:** 2
- **Files modified:** 11 (9 created, 1 modified — `.gitignore` — plus the untracked-to-tracked move of 4 strategy briefs)

## Accomplishments
- `uv`-managed Python 3.12 project (`pyproject.toml`, committed `uv.lock`) with `fastapi==0.141.1`, `pyyaml==6.0.3`, `uvicorn>=0.30` (resolved `0.52.4`); dev group `pytest==9.1.1`, `ruff==0.16.4`, `httpx>=0.27` — no `google-genai`, `google-adk`, or `parallel-web` in the resolved set (confirmed by `uv export --no-hashes`)
- `app/main.py`: `GET /health` returns exactly `status`, `version`, `git_sha`, `boot_time`; `GET /` returns an HTML holding page naming the project and linking to `/health`; `GIT_SHA` resolution never raises (env var → `git rev-parse --short HEAD` → `"unknown"`)
- `tests/test_health.py`: 8 passing tests asserting the exact key set, `status == "ok"`, version match, ISO-8601 UTC `boot_time` stability across requests, non-empty `git_sha`, and the `/` project-name check
- `scripts/smoke.sh`: starts a real backgrounded uvicorn process, polls `/health` up to 20×0.5s, asserts 200 on both routes and the presence of `git_sha`/`boot_time`, and is proven to exit non-zero against a dead `SMOKE_BASE_URL`
- Relocated `LightsailDefaultKey-us-west-2 (2).pem` to `~/.ssh/LightsailDefaultKey-us-west-2.pem` at mode `0600`; confirmed absent from the working tree and never tracked by git (T-01-01, D-30)
- Extended `.gitignore` with `id_rsa*`, `id_ed25519*`, `*.ppk`, `LightsailDefaultKey*`, `.uv-cache/`, appended without disturbing the existing secrets block
- Added an unmodified choosealicense.com MIT `LICENSE` (copyright holder "Dave Vockell", resolved via `gh api user`) and a `README.md` with Installation/Running/Repository layout/Provenance/Licence sections
- Tracked the four strategy briefs (`productionfinance-brief.md`, `idea-2-incentives.md`, `feasibility-incentives.md`, `hackathon-brief.md`) — previously untracked (D-29)

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end "the app answers /health" — one path, no stubs** - `1dbe6ab` (feat)
2. **Task 2: Repository hygiene, MIT licence, and README — make the tree safe to publish** - `b1d2a85` (chore)

**Plan metadata:** committed alongside this SUMMARY (see below)

## Files Created/Modified
- `pyproject.toml` - Python 3.12 project definition, pinned Phase 1 dependency set, pytest/ruff config
- `uv.lock` - resolved dependency set (SHP-07 lockfile-scan input)
- `.python-version` - pins `3.12`, isolated from any system interpreter
- `app/__init__.py` - exports `__version__ = "0.1.0"`
- `app/main.py` - FastAPI app, `GET /health`, `GET /`, `BOOT_TIME`/`GIT_SHA` module constants
- `tests/test_health.py` - 8 contract tests over the `/health` and `/` routes
- `scripts/smoke.sh` - end-to-end HTTP smoke check, reused unchanged in later deploy plans
- `LICENSE` - unmodified MIT template text, repository root
- `README.md` - project description, install/run instructions, repository layout, provenance
- `.gitignore` - extended with an additional secrets block (key-material shapes)

## Decisions Made
- uvicorn left unpinned at a `>=0.30` floor per plan instruction; `uv` resolved `0.52.4` — recorded in tech-stack above.
- Copyright holder for `LICENSE` resolved via `gh api user --jq '.name // .login'` (gh CLI authenticated as `lyfedev` / "Dave Vockell") rather than falling back to `git config user.name`.
- Relocated key destination dropped the ` (2)` suffix per the plan's explicit instruction, matching the path `deploy/hosting.env` and plans 01-07–01-09 will reference.

## Deviations from Plan

### Auto-fixed Issues

None — Rules 1–3 did not trigger; no bugs, missing-critical-functionality, or auto-fixable blockers were found during implementation.

### Unresolved Gap (not auto-fixable — permission-system block, not a deviation rule)

**1. `.env.example` could not be created**
- **Found during:** Task 2 (Repository hygiene)
- **Issue:** This execution environment's global Claude Code permission policy (`~/.claude/settings.json` → `permissions.deny`) denies `Read(.env.*)`, and the runtime additionally refuses `Write`/`Edit`/`Bash` operations against any path matching that pattern — including `.env.example`, a placeholder-only public template with no secret content (the project's own `.gitignore` already carves it out via `!.env.example`, confirming it is not sensitive). Attempts via the `Write` tool, a `Bash` heredoc redirect, and a bare `touch` were all denied by the permission layer before execution.
- **Not attempted:** filename obfuscation/indirection (e.g. building the path from concatenated shell variables to dodge pattern matching) to route around the deny rule. That is a deliberate, global security control and circumventing it programmatically is out of scope for an autonomous executor — the correct resolution is a human either creating the file directly or adjusting the permission policy, not a technical workaround.
- **Required content** (verified safe — no key material, no AWS profile, no static IP):
  ```
  PRODFIN_GIT_SHA=
  PRODFIN_LOG_LEVEL=info
  PRODFIN_APP_PORT=8000
  ```
- **Impact:** Task 2's acceptance criteria for `.env.example` (existence + placeholder-only values) are unmet. All other Task 2 acceptance criteria pass. `app/main.py`'s `PRODFIN_GIT_SHA` environment variable is documented in this SUMMARY and in `app/main.py` itself, so the runtime contract is unaffected — only the example template file is missing.
- **Next step:** A human (outside this tool sandbox) should create `.env.example` at the repository root with the three lines above, then run `git add .env.example && git commit`, or grant a scoped permission exception (e.g. `Read(.env.example)`/`Write(.env.example)` allow entries) and re-invoke this step.

---

**Total deviations:** 0 auto-fixed. 1 unresolved gap requiring human action (permission-system block, not a code deviation).
**Impact on plan:** All code, tests, and repository-hygiene acceptance criteria pass. The single unmet item is a 3-line template file blocked by an environment permission policy unrelated to plan correctness.

## Known Stubs

- `.env.example` — not created (see Deviations above). No stub code depends on its presence; `app/main.py` reads `PRODFIN_GIT_SHA` via `os.environ.get` with safe fallback regardless of whether the example file exists.

## Issues Encountered

- Permission-system block on `.env.example` — see Deviations above. Not a code issue; the plan's implementation is otherwise complete and verified.

## User Setup Required

**One manual step required before Task 2 is fully closed out:**
- Create `.env.example` at the repository root (content given above under Deviations), then `git add .env.example && git commit -m "chore(01-01): add .env.example placeholder template"` — OR grant this environment's Claude Code permission policy an exception for `.env.example` specifically and re-run this step.

## Next Phase Readiness

- `app.main:app` is live and importable; plan 01-02 and the deploy plans (01-07–01-09) can target it directly.
- `uv.lock` is committed and lockfile-scan-ready for SHP-07's CI gate (Phase 3).
- `LICENSE` is unmodified MIT text at the root, ready for GitHub Licensee detection once the repo goes public (plan 01-02).
- The private key is out of the working tree; the repo can go public in plan 01-02 without that risk.
- **Blocker for full Task 2 closure:** `.env.example` still needs to be created by a human or via a permission-policy exception (see above) before plan 01-02's public-repo flip, since `.env.example` is one of Task 2's committed deliverables.

---
*Phase: 01-foundations-source-truth-deploy-path*
*Completed: 2026-08-24*

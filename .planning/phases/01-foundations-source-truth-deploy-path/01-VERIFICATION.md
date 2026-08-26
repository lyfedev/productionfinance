---
phase: 01-foundations-source-truth-deploy-path
verified: 2026-08-25T08:15:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 1: Foundations — Source Truth & Deploy Path Verification Report

**Phase Goal:** Every fact the engine will encode is confirmed against a primary source, and a public HTTPS URL serves the app on the resized host while vockell.com stays live.
**Verified:** 2026-08-25T08:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | NY cap, CT CSV headers, GA loan-out rate, and partner track each have a written answer with a primary-source URL and date checked | ✓ VERIFIED | `.planning/SOURCE-TRUTH.md` carries SRC-01/02/04/05 answers, each with a primary `.gov`/dashboard URL, `date_checked: 2026-08-24`, and (for SRC-01/02/05) a `sources/` archive with a matching sha256. Independently re-hashed `sources/ny/2026-08-24-esd-q3-film-report-2025.pdf` — matches the recorded hash exactly. |
| 2 | All 11 production/award pairs exist as committed test fixtures, each recording its source document URL and disclosure stage | ✓ VERIFIED | 12 fixtures exist under `tests/fixtures/validation_pairs/*.yaml` (11 named pairs from `feasibility-incentives.md` + 1 additive CT pair). `test_committed_pair_count` matches ≥11 named pairs by title. Two fixtures spot-checked directly against archived source bytes (see below) — figures traceable exactly. |
| 3 | An anonymous visitor loads the project's public URL over valid TLS and gets a response from the app, while vockell.com continues serving normally | ✓ VERIFIED (see note) | Live external check from this machine: `curl https://vockell.com/finance/health` → `200 {"status":"ok","version":"0.1.0","git_sha":"3b7fb04",...}`. TLS chain: `subject: CN=vockell.com`, `issuer: Let's Encrypt`, `SSL certificate verify ok`. `curl -sI https://vockell.com` unchanged (301 → www, matching documented pre-existing baseline). Port 8000 confirmed unreachable off-box (`nc` exit 1). **Note:** the app is reached via a path mount (`https://vockell.com/finance`), not a new subdomain — see "Wording mismatch" finding below. |
| 4 | The app runs under systemd on Python 3.10+, isolated from system Python, survives a host reboot, reached through Apache's reverse proxy | ✓ VERIFIED | `01-08-SUMMARY.md` documents `/opt/prodfin/.venv/bin/python --version` → 3.12.14 vs system `python3` → 3.9.2 unchanged; `prodfin.service` active/enabled under a dedicated non-login user; a real `sudo reboot` was executed with `boot_time` evidence (06:59:44Z) later than the host's own `uptime -s` (06:59:38Z), the specific evidence distinguishing "survived a reboot" from "was restarted after one." `deploy/prodfin-finance-location.conf` + `01-09-SUMMARY.md` document the live `ProxyPass /finance` addition to the existing vockell.com vhost, confirmed live above. |
| 5 | CI fails the build on a forbidden lockfile package, a committed secret, or an out-of-window commit; GitHub About section shows an OSI-approved licence | ✓ VERIFIED | All three gate scripts independently re-run against adversarial input this session: `lockfile-scan.sh` against a poisoned lockfile containing `google-generativeai` → exits 1, correctly flagged; `vendor-scan.sh` against a file containing `boto3.client("textract")` → exits 1; `commit-window.sh` against a repo with a 2020-dated commit → exits 1. Latest CI run (`32822804908`) green on all 5 jobs (`gh run view --json jobs`). `gh repo view` confirms `licenseInfo.key: mit`, public repo. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Two Critical Code-Review Fixes (execution_reality item 4) — confirmed present

| Finding | Fix claimed | Verified |
|---------|-------------|----------|
| CR-01: `lockfile-scan.sh` omitted `google-generativeai` from `FORBIDDEN_EXACT` | Added to the array | ✓ Confirmed in `.github/scripts/lockfile-scan.sh:41` and by re-running the script against a poisoned lockfile (fails as expected) |
| CR-02: no CI job ran pytest | Added `tests` job to `.github/workflows/ci.yml` | ✓ Confirmed job present (`tests (source-truth integrity)`), and the latest CI run shows it succeeded; locally `uv run --frozen pytest tests/ -q` → 35 passed |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/SOURCE-TRUTH.md` | SRC-01/02/04/05 answers with sources | ✓ VERIFIED | Substantive, cites 5+ archived primary documents with sha256 hashes, corroboration method notes, explicit confidence tiers |
| `sources/MANIFEST.yaml` + `sources/**/*` | Archived documents reconciled to a manifest | ✓ VERIFIED | Present; `tests/test_source_truth.py` runs (part of the 35 passing tests) and asserts manifest↔disk sha256 reconciliation |
| `tests/fixtures/validation_pairs/*.yaml` (12 files) | 11 named pairs + CT, source URL + disclosure stage per pair | ✓ VERIFIED | All present; `tests/test_validation_pair_fixtures.py` (12 parametrized + 5 suite-level tests) enforces required fields, legal disclosure stages, blocked-pair honesty, denominator exclusion |
| `deploy/hosting.env`, `deploy/README.md` | Host facts + runbook | ✓ VERIFIED | Present, sourced by later plans, git-ignored appropriately (no secrets) |
| `deploy/prodfin.service`, `deploy/deploy.sh` | systemd unit + idempotent deploy | ✓ VERIFIED | Live on host, `prodfin.service` active/enabled, `deploy.sh` proven idempotent (run twice, both exit 0) |
| `deploy/prodfin-finance-location.conf` | Reviewable copy of live Apache directives | ✓ VERIFIED | Present in repo; matches the live host edit per `01-09-SUMMARY.md`'s diff evidence |
| `.github/workflows/ci.yml` + `.github/scripts/*.sh` | 5 CI jobs, 4 compliance gates + tests | ✓ VERIFIED | All 5 jobs present and green on latest run; each gate script independently re-run against adversarial/violation input and confirmed to fail correctly |
| `app/main.py` | Honest skeleton, no premature claims | ✓ VERIFIED | `/health` and `/` present, holding page explicitly states "No pricing engine is live yet" — no dishonest figures |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| Anonymous visitor (off-box) | `app/main.py` (`/health`) | Apache `ProxyPass /finance` → `127.0.0.1:8000` | ✓ WIRED | Live `curl` from this machine returns 200 with correct body over valid TLS |
| CI push/PR trigger | `lockfile-scan.sh`, `vendor-scan.sh`, `commit-window.sh`, `gitleaks-action`, `pytest` | GitHub Actions workflow | ✓ WIRED | Confirmed via `gh run view --json jobs` — all 5 jobs ran and passed on the most recent push |
| `sources/MANIFEST.yaml` | Archived files on disk | sha256 reconciliation | ✓ WIRED | Re-hashed 2 archived documents by hand — both match recorded values exactly; `test_source_truth.py` enforces this on every CI run |
| `prodfin.service` | Host reboot | systemd `enabled` + `Restart=on-failure` | ✓ WIRED | Real `sudo reboot` executed; service came back active with a `boot_time` later than host `uptime -s`, with no manual intervention |

### Behavioral / Live Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Anonymous visitor reaches the hosted app over valid TLS | `curl -s -o /dev/null -w '%{http_code}' https://vockell.com/finance/health` | `200` | ✓ PASS |
| TLS chain is genuinely valid (no `-k`) | `curl -v ... \| grep -i 'issuer\|verify ok'` | `issuer: Let's Encrypt`, `SSL certificate verify ok` | ✓ PASS |
| vockell.com apex unaffected | `curl -sI https://vockell.com` | `301 → https://www.vockell.com/` (unchanged baseline) | ✓ PASS |
| App port not exposed off-box | `nc -z -w 5 35.165.60.123 8000` | exit 1 (refused/timeout) | ✓ PASS |
| Anora fixture's figures are in the archived source PDF | `pdftotext -layout sources/.../Q3-Film-Report-2025.pdf - \| grep -i anora` | Row shows `$3,964,760`, `$991,190`, `$4,956` — exact match to fixture | ✓ PASS |
| NJ Trial of the Chicago 7 fixture's figure (incl. its self-reported $1 discrepancy) is in the archived capture | `grep '5,371,984' sources/nj/...txt` | Found, verbatim, matching fixture's `credit_amount: "5371984"` | ✓ PASS |
| `lockfile-scan.sh` fails on a forbidden package | Poisoned lockfile with `google-generativeai` | exit 1, correctly flagged | ✓ PASS |
| `vendor-scan.sh` fails on a forbidden AWS AI call | File containing `boto3.client("textract")` | exit 1, correctly flagged | ✓ PASS |
| `commit-window.sh` fails on a pre-window commit | Repo with a 2020-dated commit | exit 1, correctly flagged | ✓ PASS |
| Local test suite is non-vacuous and green | `uv run --frozen pytest tests/ -q` | `35 passed` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SRC-01 | 01-05 | NY annual cap reconciled | ✓ SATISFIED | SOURCE-TRUTH.md, enacted budget bill archived + hashed |
| SRC-02 | 01-05 | CT CSV column headers confirmed | ✓ SATISFIED | SOURCE-TRUTH.md, archived CSV + 6 documented data-quality gotchas |
| SRC-03 | 01-03, 01-04 | 11 validation pairs locked into fixtures | ✓ SATISFIED | 12 fixtures, structural tests, 2 spot-checked against archives |
| SRC-04 | 01-05 | Partner track confirmed (Parallel) | ✓ SATISFIED | SOURCE-TRUTH.md records owner confirmation and precedence over the sibling brief's "Our track: IBM" line |
| SRC-05 | 01-05 | GA loan-out withholding rate confirmed | ✓ SATISFIED | SOURCE-TRUTH.md, DOR page archived + hashed, 5-year schedule (not a single step) |
| SHP-01 | 01-07 | Instance resized to 2GB | ✗ OPEN (deferred, by design) | `01-07-DEFERRED.md`: user explicitly declined the resize (cost + downtime), choosing to measure real memory footprint first. `REQUIREMENTS.md` correctly tracks this `[ ]` Pending, not falsely marked complete. Not silently dropped — reversal criteria documented ("if 01-08 or any later phase hits memory pressure"). Measured 353MB available post-Python-install on the un-resized box; comfortable for Phase 1's bare skeleton. |
| SHP-02 | 01-08 | Python 3.10+ installed, isolated | ✓ SATISFIED | Live: 3.12.14 in `/opt/prodfin/.venv`, system `python3` unchanged at 3.9.2 |
| SHP-03 | 01-06, 01-09 | Subdomain DNS record exists and resolves | ✓ SATISFIED (wording mismatch — see finding) | No new subdomain/DNS record was created; the D-14 path-mount decision (user-directed) makes the app reachable at `https://vockell.com/finance` instead. The underlying goal (public, valid-TLS, non-disruptive reachability) is met and independently verified live in this session. |
| SHP-04 | 01-08, 01-09 | systemd + reverse proxy + valid TLS, vockell.com undisturbed | ✓ SATISFIED | Live verification above; reboot test; vockell.com baseline unchanged |
| SHP-07 | 01-01, 01-02 | Lockfile forbidden-package gate | ✓ SATISFIED | Gate present, includes `google-generativeai` (post-fix), fails on adversarial input |
| SHP-08 | 01-02 | Public repo, OSI licence in About section | ✓ SATISFIED | `gh repo view` confirms `licenseInfo.key: mit`, `isPrivate: false` |
| SHP-09 | 01-02 | Commit-window CI gate | ✓ SATISFIED | Gate present, fails on a pre-window-dated commit |
| SHP-10 | 01-01, 01-02 | No committed secrets | ✓ SATISFIED | `gitleaks-action` job green; one documented, narrowly-scoped false-positive allowlist entry (`.gitleaks.toml`) for a public NJEDA citation URL, not a real secret |

No orphaned requirements — every ID in `REQUIREMENTS.md`'s Phase 1 row (SRC-01..05, SHP-01..04, SHP-07..10) is declared by exactly one plan's frontmatter.

### Anti-Patterns Found

None. `grep` for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` across `app/`, `deploy/`, `.github/`, `tests/` returned no debt markers (two incidental "subdomain" substring matches in `deploy/README.md` prose, not TODO markers). No stub return values, no hardcoded-empty data flowing to output in the FastAPI skeleton — the holding page explicitly and honestly states "No pricing engine is live yet."

### Findings (informational — not blockers)

1. **Wording mismatch, self-flagged by the team (execution_reality item 2).** `REQUIREMENTS.md`'s SHP-03 text still literally reads "A subdomain DNS record exists and resolves," but the actual, user-directed implementation is a path mount (`https://vockell.com/finance`) with no new subdomain or DNS record. `01-06-SUMMARY.md` and `01-09-SUMMARY.md` both document this explicitly and correctly, and the underlying reachability goal is independently verified live in this session. Recommend a small wording edit to `REQUIREMENTS.md`'s SHP-03 line to describe the path-mount reality, so a future reader doesn't need to cross-reference two SUMMARYs to reconcile the checkbox with what's actually running.
2. **SHP-01 (resize) remains open by explicit, documented user decision**, not a defect. `01-07-DEFERRED.md` records the cost/downtime tradeoff and reversal criteria. `REQUIREMENTS.md` correctly shows this `[ ]` Pending — not falsely marked complete. Flagging here per the task's explicit instruction to report it as OPEN.
3. **5 code-review warnings remain open** (`01-REVIEW.md`, WR-01 through WR-05): spoofable commit-author-date on the commit-window gate, no automated self-test exercising the `.github/fixtures/violation/*` fixtures in CI, bare `uvicorn` under systemd with no memory/CPU limits on a shared 472MB box, and grep-based gates evadable by deliberate obfuscation. None are Stage-One disqualifiers and none contradict any Phase 1 success criterion; they are legitimate hardening items worth carrying into a future phase (WR-04 in particular, given the box's tight memory margin — 284MB available post-reboot per `01-08-SUMMARY.md`).
4. **STATE.md's Blockers/Concerns section is slightly stale**: the "01-06: plan 01-09 needs a revision pass" line is still listed as an open blocker, but `01-09-SUMMARY.md` shows this was in fact resolved (the revision was executed, live, and verified). Cosmetic — does not affect phase-goal achievement.

### Human Verification Required

None. Every success criterion was verifiable directly against the codebase, the live host, and GitHub's API/CI within this session — no visual, real-time, or subjective-quality checks were required for Phase 1's scope (deploy path + source verification, no UI).

### Gaps Summary

No gaps block Phase 1's goal achievement. All 5 ROADMAP success criteria are verified with direct, independently-reproduced evidence (live TLS-validated HTTP requests from off-box, hand-verified sha256 hashes against archived government documents, adversarial re-runs of every CI compliance gate, and a live `gh run view` confirming all 5 CI jobs green). The one requirement left incomplete (SHP-01, the instance resize) is an explicit, reversible, cost-driven user decision — honestly tracked as `Pending` in `REQUIREMENTS.md`, not silently or falsely marked done, and does not block any of the 5 success criteria as literally worded. The wording mismatch on SHP-03 and the 5 open code-review warnings are informational and do not represent unfulfilled phase-goal work.

---

_Verified: 2026-08-25T08:15:00Z_
_Verifier: Claude (gsd-verifier)_

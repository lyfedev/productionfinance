---
phase: 1
slug: foundations-source-truth-deploy-path
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-24
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `01-RESEARCH.md` § Validation Architecture. Seeded at plan time; the
> Per-Task Verification Map is populated once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 — introduced in this phase; no test framework exists in the repo today |
| **Config file** | none yet — Wave 0 creates `[tool.pytest.ini_options]` in `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds (fixture-shape assertions only; no network, no host access) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds
- **Per commit (CI, blocking):** `lockfile-scan`, `secret-scan`, `commit-window` — required status checks (D-26/D-27)
- **Once, at end of Track B:** the four live-host probes (SHP-01..04). These cannot join the repeating
  CI suite — CI runners have no SSH access to the Lightsail box, and D-19 rules out CI-driven deploy.
  They are an explicit one-time checklist in the plan's verification section.

---

## Per-Task Verification Map

*Populated after planning — task IDs do not exist until PLAN.md files are written.
Every task the planner emits must map to a row here before `nyquist_compliant: true` can be set.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *TBD* | — | — | — | — | — | — | — | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement → Evidence Map

| Req ID | Evidence type | How it is checked | Automatable in CI? |
|--------|---------------|-------------------|--------------------|
| SRC-01 | Document review | `.planning/SOURCE-TRUTH.md` entry carries URL + date_checked + the unresolved-conflict note if the $700M/$800M AUP inconsistency is not closed | No |
| SRC-02 | Document review | `.planning/SOURCE-TRUTH.md` records the exact CT CSV header row verbatim | No |
| SRC-03 | pytest (parametrized) | `tests/test_validation_pair_fixtures.py` over every file in `tests/fixtures/validation_pairs/`, asserting `source_url`, `disclosure_stage`, `status` present and non-empty; a second test asserts the expected count and jurisdiction spread so the zero-Connecticut gap cannot recur silently | **Yes** |
| SRC-04 | Document review | Already complete — resolved before planning (Parallel), no further test this phase | N/A |
| SRC-05 | Document review | `.planning/SOURCE-TRUTH.md` entry with the full GA loan-out withholding schedule | No |
| SHP-01 | Live host probe | `curl -I https://vockell.com` returns 200 post-resize; `dig +short A vockell.com` still returns the same static IP | No |
| SHP-02 | Live host probe | `/opt/prodfin/.venv/bin/python3 --version` ≥ 3.10 **and** system `python3 --version` still 3.9.2 (unchanged) | No |
| SHP-03 | External probe | `curl -v https://<subdomain>/health` from off-box: valid cert chain without `-k`, 200 response | No |
| SHP-04 | Live host probe (destructive) | `systemctl is-enabled prodfin` = `enabled`; then real reboot (D-23) → `systemctl is-active prodfin` = `active` with no manual restart | No |
| SHP-07 | CI job | `lockfile-scan` — forbidden packages absent; google-adk bare-only. Must pass on **absent**, not only on present-and-bare | **Yes** |
| SHP-08 | API check | `GET /repos/{owner}/{repo}/license` → `spdx_id == "MIT"` | Post-push only (Licensee runs server-side) |
| SHP-09 | CI job | `commit-window` — every commit author date ≥ 2026-07-27 | **Yes** |
| SHP-10 | CI job + platform | `secret-scan` (gitleaks) + GitHub push protection enabled | **Yes** (job); push protection acts at push time, outside the Actions run |

---

## Wave 0 Requirements

- [ ] `pyproject.toml` with `[tool.pytest.ini_options]` (or `pytest.ini`) — none exists yet
- [ ] `tests/fixtures/validation_pairs/` directory — none exists yet
- [ ] `tests/test_validation_pair_fixtures.py` — parametrized fixture-shape test, built from day one per D-01/D-03 (Phase 3's SHP-14 CI suite builds on this; do not retrofit)
- [ ] `.github/workflows/ci.yml` — the three D-27 jobs, none exist yet
- [ ] `sources/MANIFEST.yaml` — needed before the first archived source document (D-10)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Instance resized to 2 GB, static IP preserved, vockell.com still serving | SHP-01 | Requires the live Lightsail box; destructive (brief downtime for the live site) | Post-resize: `curl -I https://vockell.com` → 200; `dig +short A vockell.com` → 35.165.60.123 |
| Python ≥3.10 installed and isolated from system Python | SHP-02 | Requires SSH to the box | `/opt/prodfin/.venv/bin/python3 --version` ≥3.10; `python3 --version` still 3.9.2 |
| Subdomain resolves and serves over valid TLS | SHP-03 | Requires external network vantage point + real cert issuance | From off-box: `curl -v https://<subdomain>/health` — valid chain without `-k`, 200 |
| Service survives a real reboot under systemd | SHP-04 | Destructive and host-local; cannot run in CI | `systemctl is-enabled prodfin`; `sudo reboot`; wait; `systemctl is-active prodfin` = `active`, no manual restart |
| NY cap / CT headers / GA rate answers carry a primary source and date | SRC-01, SRC-02, SRC-05 | Document review — judging whether a source is primary and whether a conflict is genuinely closed is not a runtime assertion | Review `.planning/SOURCE-TRUTH.md`: each entry has question, answer, URL, date_checked, confidence, what-was-refuted |
| Licence visible in the GitHub About section | SHP-08 | GitHub's Licensee runs server-side after push | `gh api repos/{owner}/{repo}/license --jq .license.spdx_id` → `MIT` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] Per-Task Verification Map populated from the written PLAN.md task IDs
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

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

*Populated 2026-08-24 from the nine written PLAN.md files. Checkpoint tasks are listed for
completeness but carry no automated command by design.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 (tracer) | 01-01 | 1 | SHP-07 | T-01-03, T-01-05, T-01-SC | `/health` exposes only four contract keys; git-SHA resolution never raises | pytest + real HTTP smoke | `uv sync && uv run pytest tests/test_health.py -x && bash scripts/smoke.sh` | ❌ W0 | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | SHP-10 | T-01-01, T-01-02, T-01-04 | Private key relocated; placeholder-only `.env.example`; ignore rules extended not replaced | shell assertions | `test ! -e "LightsailDefaultKey-us-west-2 (2).pem" && test "$(git ls-files -- '*.pem' \| wc -l \| tr -d ' ')" = "0"` | ❌ W0 | ⬜ pending |
| 01-02-T1 | 01-02 | 2 | SHP-08, SHP-10 | T-01-06 | One-way publish decision gated for a human | checkpoint:decision | *(none — blocking-human gate)* | n/a | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | SHP-07, SHP-09, SHP-10 | T-01-07, T-01-08, T-01-11 | Every gate proven fail-first against a committed known-bad fixture | shell fail-first proofs | `bash .github/scripts/lockfile-scan.sh && ! bash .github/scripts/lockfile-scan.sh .github/fixtures/violation/forbidden-uv.lock && ! bash .github/scripts/vendor-scan.sh .github/fixtures/violation && ! bash .github/scripts/commit-window.sh 2099-01-01` | ❌ W0 | ⬜ pending |
| 01-02-T3 | 01-02 | 2 | SHP-08, SHP-10 | T-01-06, T-01-10 | Secret scan green over full history before visibility flips; Licensee result read from the API | `gh` API assertions | `gh api repos/{owner}/{repo}/license --jq '.license.spdx_id' \| grep -qx MIT` | ❌ W0 | ⬜ pending |
| 01-03-T1 | 01-03 | 2 | SRC-03 | — | One-way validation-boundary decision gated for a human | checkpoint:decision | *(none — blocking-human gate)* | n/a | ⬜ pending |
| 01-03-T2 (tracer) | 01-03 | 2 | SRC-03 | T-01-12, T-01-14, T-01-15 | Figures transcribed from archived bytes; manifest hash matches file on disk; empty fixture set fails hard | pytest + hash check | `uv run pytest tests/test_validation_pair_fixtures.py -x -q` | ❌ W0 | ⬜ pending |
| 01-03-T3 | 01-03 | 2 | SRC-03 | T-01-12, T-01-15 | Disclosure stages separable; assertion tier argued in writing | pytest (parametrized) | `uv run pytest tests/test_validation_pair_fixtures.py -q` | ❌ W0 | ⬜ pending |
| 01-04-T1 | 01-04 | 3 | SRC-03 | T-01-17, T-01-19 | CA/NJ figures re-verified from archived primary documents, not the secondary compilation | pytest + hash check | `uv run pytest tests/test_validation_pair_fixtures.py -q` | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 3 | SRC-03 | T-01-18, T-01-19 | CT pair drawn from the 12-217jj production credit only; money parsed past the CSV artifacts | pytest + YAML assertions | `uv run pytest tests/test_validation_pair_fixtures.py -q` | ❌ W0 | ⬜ pending |
| 01-04-T3 | 01-04 | 3 | SRC-03 | T-01-20, T-01-21 | Blocked pairs explain themselves; jurisdiction gap and blended denominator both fail the suite | pytest (guard tests) | `uv run pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 01-05-T1 | 01-05 | 4 | SRC-01 | T-01-23, T-01-24, T-01-25 | Cap answer sourced to the statute or recorded as an explicit unresolved conflict | document-shape assertion | `uv run python -c "…SRC-01 entry shape…"` | ❌ W0 | ⬜ pending |
| 01-05-T2 | 01-05 | 4 | SRC-02, SRC-05 | T-01-26, T-01-28 | CT headers verbatim; GA schedule exact decimal strings; honest tier on loan-out specificity | document-shape assertion | `uv run python -c "…SRC-02/05 entries…"` | ❌ W0 | ⬜ pending |
| 01-05-T3 | 01-05 | 4 | SRC-04 | T-01-23 | Archive, manifest and fixtures proven to agree; check observed failing on a mutated file | pytest | `uv run pytest tests/test_source_truth.py -q && uv run pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 01-06-T1 | 01-06 | 1 | SHP-03 | — | Subdomain label confirmed by the developer, never assumed (D-14) | checkpoint:decision | *(none — blocking-human gate)* | n/a | ⬜ pending |
| 01-06-T2 | 01-06 | 1 | SHP-03 | T-01-32 | `hosting.env` carries no credential and is trackable | shell assertions | `. ./deploy/hosting.env && test "$PRODFIN_STATIC_IP" = "35.165.60.123"` | n/a | ⬜ pending |
| 01-06-T3 | 01-06 | 1 | SHP-03 | T-01-29, T-01-30, T-01-31 | One sibling A record added; apex unchanged; empty `dig` treated as not-yet-propagated | live probe (one-time) | `dig +short A $PRODFIN_HOST \| grep -qx 35.165.60.123` | n/a | ⬜ pending |
| 01-07-T1 | 01-07 | 2 | SHP-01 | T-01-39 | Real resource names and bundle prices read from the API; nothing changed | live AWS read (one-time) | `aws lightsail get-instances … --query "instances[?publicIpAddress=='$PRODFIN_STATIC_IP'].name"` | n/a | ⬜ pending |
| 01-07-T2 | 01-07 | 2 | SHP-01 | T-01-40 | Billable resource authorised with real prices visible | checkpoint:decision | *(none — blocking-human gate)* | n/a | ⬜ pending |
| 01-07-T3 | 01-07 | 2 | SHP-01 | T-01-34, T-01-35, T-01-36, T-01-37 | Snapshot first, health-check before the IP moves, old instance stopped not deleted | live probe (one-time) + human-check | `curl -fsS -o /dev/null -w '%{http_code}' https://vockell.com \| grep -q 200 && dig +short A vockell.com \| grep -qx 35.165.60.123` | n/a | ⬜ pending |
| 01-08-T1 | 01-08 | 3 | SHP-02 | T-01-43 | uv-managed 3.12 present; system 3.9.2 unchanged; LAMP stack still serving | live probe (one-time) | `ssh … "$PRODFIN_APP_ROOT/.venv/bin/python -c 'import sys; assert sys.version_info[:2] >= (3,12)'"` | n/a | ⬜ pending |
| 01-08-T2 | 01-08 | 3 | SHP-04 | T-01-41, T-01-42, T-01-44, T-01-45 | Non-root service user; bound to 127.0.0.1; port 8000 unreachable off-box | live probe (one-time) | `ssh … "systemctl is-active $PRODFIN_SERVICE && curl -fsS http://127.0.0.1:$PRODFIN_APP_PORT/health"` | n/a | ⬜ pending |
| 01-08-T3 | 01-08 | 3 | SHP-04 | T-01-46, T-01-47, T-01-48 | Reboot executed and recovery observed against a boot timestamp (D-23) | live probe (one-time, destructive) + human-check | `ssh … "systemctl is-active $PRODFIN_SERVICE; uptime -s"` | n/a | ⬜ pending |
| 01-09-T1 | 01-09 | 4 | SHP-03, SHP-04 | T-01-49, T-01-50, T-01-54 | New vhost only; no existing vhost edited; pre-TLS snapshot available | live probe (one-time) | `curl -fsS -o /dev/null -w '%{http_code}' "http://$PRODFIN_HOST/health" \| grep -q 200` | n/a | ⬜ pending |
| 01-09-T2 | 01-09 | 4 | SHP-03 | T-01-49 | TLS approach on the live box gated for a human | checkpoint:decision | *(none — blocking-human gate)* | n/a | ⬜ pending |
| 01-09-T3 | 01-09 | 4 | SHP-03, SHP-04 | T-01-51, T-01-52, T-01-53, T-01-56 | Valid chain with validation enabled; vockell.com coverage intact; renewal job exists | external probe (one-time) + human-check | `curl -fsS "https://$PRODFIN_HOST/health" && SMOKE_BASE_URL="https://$PRODFIN_HOST" bash scripts/smoke.sh` | ❌ W0 | ⬜ pending |

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

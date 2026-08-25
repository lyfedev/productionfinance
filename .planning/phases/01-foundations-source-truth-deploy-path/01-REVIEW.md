---
phase: 01-foundations-source-truth-deploy-path
reviewed: 2026-08-25T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - .github/scripts/commit-window.sh
  - .github/scripts/lockfile-scan.sh
  - .github/scripts/vendor-scan.sh
  - .github/workflows/ci.yml
  - .github/fixtures/violation/bad_client.py
  - .github/fixtures/violation/forbidden-uv.lock
  - .gitignore
  - .gitleaks.toml
  - app/__init__.py
  - app/main.py
  - deploy/deploy.sh
  - deploy/prodfin.service
  - deploy/prodfin-finance-location.conf
  - deploy/hosting.env
  - scripts/smoke.sh
  - pyproject.toml
  - tests/test_health.py
  - tests/test_source_truth.py
  - tests/test_validation_pair_fixtures.py
  - tests/fixtures/validation_pairs/ny_anora.yaml
  - tests/fixtures/validation_pairs/ma_dont_look_up.yaml
  - sources/MANIFEST.yaml
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-25T00:00:00Z
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

This phase's job is to be the eligibility/security boundary for the rest of the hackathon build:
four CI gates (SHP-07 lockfile-scan, D-28 vendor-scan, SHP-09 commit-window, SHP-10 secret-scan),
a FastAPI skeleton, a deploy path onto a shared production box, and the audit-trail test suite
(source-truth + validation-pair fixtures) that is the project's central honesty claim.

I read every listed file, then actually **ran** each gate script (against the real repo and
against the `.github/fixtures/violation/*` known-bad fixtures), ran the full pytest suite (35
passed), and probed the scan scripts with adversarial inputs (space-in-filename paths, a
`boto3.client("sagemaker-runtime")` variant, a `.ipynb`-shaped file, an isolated google-adk-extras
lockfile). The scripts behave exactly as their comments claim for every case I could construct —
this is unusually well-engineered defensive shell. The problems I found are not "the script is
wrong" so much as "the script covers less than the project's own stated requirements claim it
does," plus one structural gap: the well-designed test suite that proves the audit trail is
honest is never actually run by CI.

## Critical Issues

### CR-01: lockfile-scan.sh does not check for `google-generativeai`, a package CLAUDE.md explicitly forbids

**File:** `.github/scripts/lockfile-scan.sh:41`
**Issue:** `.claude/CLAUDE.md`'s "What NOT to Use" table and "Forbidden dependencies" section
explicitly name `google-generativeai` as dead/forbidden ("all support ended 2025-11-30... do not
use it, do not let a stale tutorial talk you into it"), and the reviewing task's own brief lists
it as a package this gate "must catch": *"lockfile-scan.sh must catch forbidden packages: openai,
anthropic, langchain-\*, llama-index, crewai, **google-generativeai**."* The script's
`FORBIDDEN_EXACT` array is:

```bash
FORBIDDEN_EXACT=("openai" "anthropic" "langgraph" "crewai" "llama-index" "litellm")
```

`google-generativeai` is absent. I confirmed this concretely — a lockfile containing only
`google-generativeai` and `fastapi` scans clean:

```
$ bash .github/scripts/lockfile-scan.sh /tmp/test-lockfile.lock
PASS: google-adk is ABSENT from '/tmp/test-lockfile.lock' — absence is a pass...
PASS: lockfile-scan clean — 2 resolved package(s) checked against '/tmp/test-lockfile.lock', no forbidden packages found
EXIT: 0
```

`google-generativeai` isn't a Stage-One AI-vendor violation by itself (it's still a Google
package), but it's a project-mandated exclusion the gate is documented and expected to enforce,
and it is silently not enforced.

**Fix:**
```bash
FORBIDDEN_EXACT=("openai" "anthropic" "langgraph" "crewai" "llama-index" "litellm" "google-generativeai")
```

### CR-02: The CI workflow never runs the test suite — the audit-trail/honesty tests are not gated

**File:** `.github/workflows/ci.yml:14-58`
**Issue:** `ci.yml` defines exactly four jobs — `lockfile-scan`, `vendor-scan`, `commit-window`,
`secret-scan` — and no job anywhere runs `pytest`. I confirmed with a repo-wide grep that no
workflow file references `pytest` or `uv run` at all. This means the 35 tests in `tests/`,
including `tests/test_source_truth.py` (SHA256 manifest/disk reconciliation, "every archived file
has a manifest row", fixture-source cross-reference) and
`tests/test_validation_pair_fixtures.py` (blocked-pair exclusion from the accuracy denominator,
disclosure-stage cohort separation, the 11-pair count) — the tests that make this project's core
claim ("every figure sourced, dated, and provably matching what a government actually paid")
structurally checkable rather than aspirational — provide **zero** protection against a
regression landing on `main`. A future commit that corrupts a `sha256` field, deletes an archived
source file, adds an empty/malformed fixture, or reintroduces a blended accuracy denominator would
merge cleanly; nothing in CI would go red. This is exactly the "test quality" risk the review
brief calls out (§5: tests "cannot pass vacuously... blocked pairs cannot silently count") — the
tests themselves are well-built and non-vacuous (verified by reading and running them), but an
unenforced test suite is functionally equivalent to no test suite from CI's point of view.

**Fix:** add a job to `.github/workflows/ci.yml`:
```yaml
  test:
    name: pytest
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run pytest -q
```

## Warnings

### WR-01: commit-window.sh's shallow-checkout detection fails open if the detection command itself errors

**File:** `.github/scripts/commit-window.sh:36-40`
**Issue:**
```bash
IS_SHALLOW=$(git rev-parse --is-shallow-repository 2>/dev/null || echo "unknown")
if [ "$IS_SHALLOW" = "true" ]; then
  echo "FAIL: this is a shallow checkout..." >&2
  exit 1
fi
```
The script's own header comment states the shallow check exists specifically so "a shallow
checkout... must never read as a pass." But if `git rev-parse --is-shallow-repository` errors for
any reason other than "the repo genuinely isn't shallow" (unusual git version, detached
`.git`-dir edge case, etc.), `IS_SHALLOW` becomes the literal string `"unknown"` — which is
neither `"true"` nor `"false"` — and the check silently falls through as if the repo were **not**
shallow, rather than failing closed. In the current CI job this is low-risk in practice because
`fetch-depth: 0` is hardcoded in `ci.yml`, but the script is explicitly designed to be a
belt-and-suspenders check independent of that workflow setting, and as written it doesn't fully
deliver on that design goal.

**Fix:**
```bash
IS_SHALLOW=$(git rev-parse --is-shallow-repository 2>/dev/null) || {
  echo "FAIL: could not determine shallow-repository status ('git rev-parse --is-shallow-repository' errored) — cannot prove full history is present" >&2
  exit 1
}
if [ "$IS_SHALLOW" != "false" ]; then
  echo "FAIL: this is a shallow checkout or its status could not be confirmed as 'false'" >&2
  exit 1
fi
```

### WR-02: commit-window.sh's enforcement mechanism (author date) is trivially spoofable

**File:** `.github/scripts/commit-window.sh:42,50-56`
**Issue:** The gate reads `%ad` (author date) via `git log --pretty=format:'%ad %H'`. Git author
dates are fully attacker-controlled (`git commit --date=...`, `GIT_AUTHOR_DATE`, or a rebase with
`--committer-date-is-author-date`/interactive `--date` edits). Someone who wanted to bring in code
authored before 2026-07-27 — the exact "New code only... no extending prior work" violation this
gate exists to catch (Stage One disqualification) — can pass this check trivially by setting the
author date to any in-window value when committing. This isn't a bug in the shell logic (the
script does correctly implement "cutoff comparison over reachable commits"), but the review brief
explicitly asks whether each gate "can be trivially evaded," and for this gate the answer for its
one adversarial scenario is yes. Given the actual eligibility risk this gate is protecting against
is provenance fraud (not accidental old commits), it's worth flagging even though a fully spoof-proof
version is likely out of scope for a hackathon.

**Fix:** At minimum, add a comment to the script documenting this as a known limitation (so a
future maintainer doesn't over-trust a green run), and consider a supplementary check comparing
author date against committer date (still spoofable together, but catches the common case of an
`--amend`/direct backdating that leaves committer date honest) or cross-checking against GitHub's
own recorded push timestamp for the triggering event where available.

### WR-03: `.github/fixtures/violation/*` are never actually exercised by CI — no automated proof the gates still catch known-bad input

**File:** `.github/fixtures/violation/bad_client.py`, `.github/fixtures/violation/forbidden-uv.lock`, `.github/workflows/ci.yml`
**Issue:** Both fixture files' own header comments describe them as existing "to drive
lockfile-scan.sh/vendor-scan.sh red" — but I grepped the entire repository for any reference to
`fixtures/violation`, `forbidden-uv.lock`, or `bad_client` outside the two scan scripts'
explanatory comments, and found none. No CI job and no test runs the scan scripts against these
fixtures and asserts a non-zero exit. They are real, well-constructed "should fail" fixtures
(confirmed manually — running `lockfile-scan.sh` against `forbidden-uv.lock` correctly reports
`openai` and `langchain-google-genai`; running `vendor-scan.sh` against the fixture dir correctly
reports the `boto3.client("textract")` call) but exist purely as documentation/manual-proving
artifacts. A future edit to either script (e.g. a typo in the exclude-path pattern, an accidentally
narrowed regex, a refactor that drops the `google-adk` extras branch) that silently weakens
detection would not be caught by anything automated — the fixtures would just sit there, giving a
false sense that "there's a red-path test for this."

**Fix:** add a small self-test job/step, e.g.:
```yaml
  gate-self-test:
    name: gate-self-test (prove the gates still catch known-bad input)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: lockfile-scan must fail on known-bad lockfile
        run: |
          if bash .github/scripts/lockfile-scan.sh .github/fixtures/violation/forbidden-uv.lock; then
            echo "FAIL: lockfile-scan.sh passed a known-bad lockfile" >&2; exit 1
          fi
      - name: vendor-scan must fail on known-bad source
        run: |
          if bash .github/scripts/vendor-scan.sh .github/fixtures/violation; then
            echo "FAIL: vendor-scan.sh passed a known-bad source file" >&2; exit 1
          fi
```

### WR-04: prodfin.service deviates from the project's own "never run bare uvicorn in production" decision, with no resource limits on a shared, memory-constrained box

**File:** `deploy/prodfin.service:19-28`
**Issue:** `ExecStart=/opt/prodfin/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`
runs a single bare `uvicorn` process directly under systemd. `.claude/CLAUDE.md`'s Technology
Stack table is explicit and unhedged on this point: *"Never run `uvicorn` alone in production — no
worker recycling, no graceful multi-process handling under load. Gunicorn supervises N uvicorn
workers."* This unit is the actual production deploy artifact for a box that also serves an
unrelated live site (vockell.com) on constrained resources (the CLAUDE.md constraints section
describes the pre-resize host as 472MB RAM with swap already in use; even post-resize at 2GB/2vCPU
it's a small shared box). The unit also sets no `MemoryMax=`/`MemoryHigh=`/`CPUQuota=` and no
sandboxing directives (`NoNewPrivileges=`, `ProtectSystem=`, `PrivateTmp=`) — so a memory leak, a
runaway request, or a crash-loop in this app has no systemd-level guard rail preventing it from
starving Apache/MySQL on the same box, which the review brief specifically flags as a concern
("Check for anything that could destabilise or take down that site").

**Fix:** either adopt Gunicorn+`UvicornWorker` per the documented decision, or explicitly record
in the unit file / deploy docs that bare uvicorn is a deliberate, time-boxed Phase-1 deferral. Add
resource bounds regardless:
```ini
[Service]
...
MemoryMax=512M
CPUQuota=50%
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/prodfin
PrivateTmp=true
```

### WR-05: lockfile-scan.sh and vendor-scan.sh are literal/regex scans and can be evaded by deliberate obfuscation

**File:** `.github/scripts/lockfile-scan.sh:41-59`, `.github/scripts/vendor-scan.sh:21,35`
**Issue:** Both gates match literal tokens (`grep -E`, exact-string comparisons). They robustly
catch the accidental-misuse case the project is explicitly worried about (CLAUDE.md: "AWS
Textract is the specific trap... it is the most likely *accidental* violation"), and I could not
find a false-negative in any non-adversarial scenario I tried. But a deliberate evasion —
`boto3.client(getattr(__import__("builtins"), "chr")(...))`-style dynamic construction, string
concatenation (`"text" + "ract"`), an aliased import, or a forbidden PyPI package installed under
a git/path source rather than the PyPI registry (which would still emit a `name = "..."` line in
`uv.lock`, so that specific evasion is actually caught — but a locally-vendored copy of a forbidden
package's source dropped directly into the tree without a `uv.lock` entry would not be) — would
not be detected. This is a standard limitation of any static grep-based gate and is not fixable
without much more investment (AST parsing, import-graph analysis); flagging per the review brief's
explicit "can this gate be trivially evaded?" question, not as something to necessarily fix in this
phase.

**Fix:** No code change required; recommend adding a one-line comment to each script's header
acknowledging this is a best-effort/accidental-misuse gate, not a defense against deliberate
evasion, so future maintainers calibrate their trust in a green run correctly.

## Info

### IN-01: `_resolve_git_sha()` swallows all exceptions silently, with no log trace

**File:** `app/main.py:44-46`
**Issue:**
```python
    except Exception:
        pass
```
Deliberate per the docstring ("Never raises... must not stop the service from booting") and I
agree with the design goal, but a bare `except Exception: pass` with zero logging means if
`subprocess.run` fails on the host for an unexpected reason (e.g. permissions, PATH issue,
`git` binary missing after a botched provisioning step), there is no trace anywhere that this
happened — `/health` will just quietly report `git_sha: "unknown"` forever, and a future
on-call debugging that will have no breadcrumb pointing at the cause.

**Fix:**
```python
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("git sha resolution failed: %s", exc)
```

### IN-02: `BOOT_TIME` is per-process, not per-deployment — will silently diverge once/if multi-worker Gunicorn is adopted

**File:** `app/main.py:18-20`
**Issue:** `BOOT_TIME` is computed once at module import time, and the comment claims "every
request in this process reports the same boot time" — true today because `prodfin.service` runs
exactly one bare uvicorn process (see WR-04). If/when the project moves to the documented
Gunicorn+`UvicornWorker` multi-worker pattern, each worker process re-imports `app.main` and gets
its own `BOOT_TIME`, so `/health` would return a different `boot_time` depending on which worker
served the request — silently breaking the invariant `test_health_boot_time_stable_across_requests`
currently verifies (that test only exercises a single `TestClient`/single process, so it would
keep passing even after this regression).

**Fix:** when Gunicorn is introduced, thread a deploy-time-computed boot timestamp through the same
mechanism already used for `PRODFIN_GIT_SHA` (write it into `.env` at deploy time, read via
`os.environ`), rather than relying on Python import time.

### IN-03: scripts/smoke.sh uses fixed `/tmp` paths instead of a unique temp file

**File:** `scripts/smoke.sh:22,45,52,58`
**Issue:** `/tmp/prodfin-smoke.log` and `/tmp/prodfin-smoke-health.json` are hardcoded, shared
paths. Harmless for the current single sequential invocation pattern (local dev, or one deploy at
a time), but two concurrent runs of this script (e.g. a developer running it locally while CI or
another operator runs it against the live host) would clobber each other's output files.

**Fix:**
```bash
HEALTH_JSON="$(mktemp)"
trap 'cleanup; rm -f "$HEALTH_JSON"' EXIT
...
HEALTH_CODE=$(curl -s -o "$HEALTH_JSON" -w '%{http_code}' "${BASE_URL}/health")
```

---

_Reviewed: 2026-08-25T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

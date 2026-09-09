#!/usr/bin/env bash
# pre_submission_check.sh
#
# SHP-13 / D-103: the pre-submission re-verification sweep. Every gate below
# is RE-RUN on this invocation of this script — never cited from an earlier
# pass, never assumed still true because it was true last week. "A gate that
# passed a week ago is not evidence about today's tree" (08-CONTEXT.md D-103).
#
# Gates re-run, in order:
#   1. .github/scripts/lockfile-scan.sh   (SHP-07 — resolved lockfile clean)
#   2. .github/scripts/vendor-scan.sh     (D-28 — no forbidden AWS AI token)
#   3. scripts/audit_sdk_call_sites.py --check   (D-96 — call sites reachable)
#   4. the full pytest suite
#   5. the CLAUDE.md pre-submission grep checklist over source files
#      (openai/anthropic/langchain*/llama_index/crewai — package names that
#      would slip past the lockfile scan if only referenced in source, and
#      past vendor-scan.sh, which only checks AWS AI service tokens)
#   6. SHP-14 non-vacuity, re-proven THIS run: .github/scripts/mutation-check.sh
#      breaks a rule value on a scratch copy, confirms the suite catches it,
#      restores, and re-asserts green
#   7. SHP-08 — the GitHub About-section license, re-queried live via `gh`
#   8. SHP-05/SHP-06 — a production-log grep for one real google-genai call
#      and one real parallel-web call, fired by a live logged-out session
#      (best-effort: requires SSH access to the production box; reports
#      BLOCKED, not a silent pass, when that access is unavailable)
#
# Gate 8 is expected to currently FAIL — no live SDK call has ever fired in
# production because PARALLEL_API_KEY/GEMINI_API_KEY are not installed
# (WINDOWS.md #26/#28/#32). That is not a bug in this script; it is this
# script honestly reporting the ship-readiness gap .planning/SHIP-CHECKLIST.md
# exists to close. This script's exit code reflects whether the tree is
# ACTUALLY ready to ship, not whether the code is well-formed.
#
# Exit 0 — every gate passed, including the production-log check.
# Exit 1 — one or more gates failed or are blocked.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f "pyproject.toml" ]; then
  echo "FAIL: must be run from (or under) the repository root — pyproject.toml not found" >&2
  exit 1
fi

RESULTS=()   # "GATE_NAME|STATUS|detail"
OVERALL_OK=true

record() {
  local name="$1" status="$2" detail="${3:-}"
  RESULTS+=("${name}|${status}|${detail}")
  if [ "$status" != "PASS" ]; then
    OVERALL_OK=false
  fi
}

hr() { printf '%s\n' "----------------------------------------------------------------------"; }

echo "ProductionFinance pre-submission check — $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Repo HEAD: $(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
hr

# --- Gate 1: lockfile-scan.sh (SHP-07) --------------------------------------
echo "==> Gate 1/8: lockfile-scan.sh (SHP-07)"
if bash .github/scripts/lockfile-scan.sh; then
  record "lockfile-scan (SHP-07)" "PASS"
else
  record "lockfile-scan (SHP-07)" "FAIL"
fi
hr

# --- Gate 2: vendor-scan.sh (D-28) ------------------------------------------
echo "==> Gate 2/8: vendor-scan.sh (D-28)"
if bash .github/scripts/vendor-scan.sh; then
  record "vendor-scan (D-28)" "PASS"
else
  record "vendor-scan (D-28)" "FAIL"
fi
hr

# --- Gate 3: audit_sdk_call_sites.py --check (D-96) -------------------------
echo "==> Gate 3/8: audit_sdk_call_sites.py --check (D-96)"
if command -v uv >/dev/null 2>&1; then
  if uv run --frozen python scripts/audit_sdk_call_sites.py --check; then
    record "sdk-call-sites (D-96)" "PASS"
  else
    record "sdk-call-sites (D-96)" "FAIL"
  fi
else
  echo "FAIL: uv not found on PATH — cannot re-run the SDK call-site audit" >&2
  record "sdk-call-sites (D-96)" "BLOCKED" "uv not on PATH"
fi
hr

# --- Gate 4: full pytest suite ----------------------------------------------
echo "==> Gate 4/8: full pytest suite"
if command -v uv >/dev/null 2>&1; then
  PYTEST_OUTPUT=$(uv run --frozen pytest tests/ -q 2>&1)
  PYTEST_EXIT=$?
  echo "$PYTEST_OUTPUT" | tail -20
  PYTEST_SUMMARY=$(echo "$PYTEST_OUTPUT" | grep -E '^[0-9]+ (passed|failed)' | tail -1)
  if [ "$PYTEST_EXIT" -eq 0 ]; then
    record "pytest suite" "PASS" "$PYTEST_SUMMARY"
  else
    record "pytest suite" "FAIL" "$PYTEST_SUMMARY"
  fi
else
  echo "FAIL: uv not found on PATH — cannot re-run the test suite" >&2
  record "pytest suite" "BLOCKED" "uv not on PATH"
fi
hr

# --- Gate 5: CLAUDE.md pre-submission grep checklist ------------------------
# .github/scripts/vendor-scan.sh already re-runs (gate 2 above) and covers
# the AWS AI service tokens (textract/bedrock/comprehend/rekognition/
# transcribe/polly/kendra/sagemaker) with the correct English-word-collision
# handling for translate/transcribe. This gate covers the REMAINING tokens
# CLAUDE.md's own pre-submission paragraph names in the same breath —
# openai/anthropic/langchain*/llama_index/crewai — which lockfile-scan.sh
# checks only in the RESOLVED lockfile, not in source files directly (a
# stray `import openai` that failed to resolve, or a copy-pasted snippet,
# would not show up in uv.lock at all). Same file-extension scope as
# vendor-scan.sh (*.py/*.toml/*.yaml/*.yml) and the same fixtures exclusion,
# for the identical reason: this .sh file and CLAUDE.md's own prose
# necessarily name these tokens too, and are outside the scanned extensions.
echo "==> Gate 5/8: CLAUDE.md grep checklist (openai/anthropic/langchain/llama_index/crewai)"
GREP_TOKENS='openai|anthropic|langchain|llama.?index|crewai'
GREP_MATCHES=$(find . -type f \( -name '*.py' -o -name '*.toml' -o -name '*.yaml' -o -name '*.yml' \) \
  -not -path '*/.github/fixtures/*' -not -path '*/.git/*' -not -path '*/.venv/*' -print0 \
  | xargs -0 grep -nEi "$GREP_TOKENS" 2>/dev/null || true)
if [ -n "$GREP_MATCHES" ]; then
  echo "FAIL: forbidden vendor/framework token(s) found in source files:" >&2
  echo "$GREP_MATCHES" >&2
  record "CLAUDE.md grep checklist" "FAIL" "$(echo "$GREP_MATCHES" | wc -l | tr -d ' ') match(es)"
else
  echo "PASS: no openai/anthropic/langchain/llama_index/crewai token in any .py/.toml/.yaml/.yml file"
  record "CLAUDE.md grep checklist" "PASS"
fi
hr

# --- Gate 6: SHP-14 non-vacuity, re-proven this run -------------------------
echo "==> Gate 6/8: SHP-14 non-vacuity — break a rule value, confirm the suite catches it, revert (THIS run, not cited from CI)"
if bash .github/scripts/mutation-check.sh; then
  record "SHP-14 non-vacuity" "PASS"
else
  record "SHP-14 non-vacuity" "FAIL"
fi
hr

# --- Gate 7: SHP-08 — About-section license, re-queried live ----------------
echo "==> Gate 7/8: SHP-08 — GitHub About-section license (re-queried live, not the LICENSE file)"
if command -v gh >/dev/null 2>&1; then
  LICENSE_JSON=$(gh repo view --json licenseInfo 2>&1)
  GH_EXIT=$?
  echo "$LICENSE_JSON"
  if [ "$GH_EXIT" -eq 0 ] && echo "$LICENSE_JSON" | grep -q '"key"'; then
    LICENSE_KEY=$(echo "$LICENSE_JSON" | grep -o '"key":"[^"]*"' | head -1 | cut -d'"' -f4)
    if [ -n "$LICENSE_KEY" ] && [ "$LICENSE_KEY" != "null" ]; then
      record "SHP-08 About-section license" "PASS" "detected: $LICENSE_KEY"
    else
      record "SHP-08 About-section license" "FAIL" "no license key detected in About section"
    fi
  else
    record "SHP-08 About-section license" "BLOCKED" "gh repo view failed — not authenticated or not a GitHub remote"
  fi
else
  echo "BLOCKED: gh CLI not found on PATH — cannot re-query the About-section license live" >&2
  record "SHP-08 About-section license" "BLOCKED" "gh not on PATH"
fi
hr

# --- Gate 8: production log grep for a real Gemini call and a real Parallel call
echo "==> Gate 8/8: production log grep for one real google-genai call and one real parallel-web call"
echo "    (SHP-05/SHP-06 — expected to currently FAIL; see WINDOWS.md #26/#28/#32)"

if [ -f "deploy/hosting.env" ]; then
  # shellcheck disable=SC1091
  set -a && . ./deploy/hosting.env && set +a
fi

SSH_USER="${PRODFIN_SSH_USER:-bitnami}"
# The static IP (deploy/hosting.env's PRODFIN_STATIC_IP), not PRODFIN_HOST
# (vockell.com — the public HTTP hostname). SSH's host-key identity is bound
# to whichever address a client first connects with; this box's key was
# established against the static IP, and BatchMode=yes deliberately refuses
# to silently trust an unrecognized host-key match for a different name
# (e.g. connecting via "vockell.com" fails with "Host key verification
# failed" even though it is the same server) rather than proceeding without
# verifying it is genuinely the same host.
SSH_HOST="${PRODFIN_SSH_HOST:-${PRODFIN_STATIC_IP:-35.165.60.123}}"
# The project's own hosting.env records the intended key path
# (~/.ssh/LightsailDefaultKey-us-west-2.pem); CLAUDE.md's Constraints
# section records the actual key location on this development machine
# (~/Downloads/LightsailDefaultKey-us-west-2.pem). Try both rather than
# guessing wrong and reporting a false BLOCKED.
SSH_KEY_CANDIDATES=(
  "${PRODFIN_SSH_KEY:-}"
  "$HOME/.ssh/LightsailDefaultKey-us-west-2.pem"
  "$HOME/Downloads/LightsailDefaultKey-us-west-2.pem"
)
SSH_KEY=""
for candidate in "${SSH_KEY_CANDIDATES[@]}"; do
  candidate="${candidate/#\~/$HOME}"
  if [ -n "$candidate" ] && [ -f "$candidate" ]; then
    SSH_KEY="$candidate"
    break
  fi
done

if [ -z "$SSH_KEY" ]; then
  echo "BLOCKED: no SSH key found for the production box among: ${SSH_KEY_CANDIDATES[*]}" >&2
  record "production log grep (SHP-05/SHP-06)" "BLOCKED" "no SSH key available in this environment"
else
  # Key permissions must be 600 or sshd silently rejects it.
  chmod 600 "$SSH_KEY" 2>/dev/null || true
  SSH_CMD="sudo journalctl -u prodfin --since '7 days ago' 2>/dev/null | grep PRODFIN_SDK_CALL || true"
  LOG_LINES=$(ssh -o ConnectTimeout=8 -o BatchMode=yes -i "$SSH_KEY" "${SSH_USER}@${SSH_HOST}" "$SSH_CMD" 2>/dev/null)
  SSH_EXIT=$?
  if [ "$SSH_EXIT" -ne 0 ]; then
    echo "BLOCKED: SSH to ${SSH_USER}@${SSH_HOST} failed (exit ${SSH_EXIT}) — cannot re-grep production logs from this environment" >&2
    record "production log grep (SHP-05/SHP-06)" "BLOCKED" "SSH to ${SSH_HOST} failed"
  else
    GEMINI_LINE=$(echo "$LOG_LINES" | grep -c 'sdk=google-genai' || true)
    PARALLEL_LINE=$(echo "$LOG_LINES" | grep -c 'sdk=parallel-web' || true)
    echo "PRODFIN_SDK_CALL lines in the last 7 days: sdk=google-genai=${GEMINI_LINE}, sdk=parallel-web=${PARALLEL_LINE}"
    if [ "${GEMINI_LINE:-0}" -ge 1 ] && [ "${PARALLEL_LINE:-0}" -ge 1 ]; then
      record "production log grep (SHP-05/SHP-06)" "PASS" "gemini=${GEMINI_LINE} parallel=${PARALLEL_LINE}"
    else
      echo "FAIL: production logs do not (yet) show both a real google-genai and a real parallel-web call." >&2
      echo "This is the honest, currently-true state — see .planning/SHIP-CHECKLIST.md items 1, 3, 4." >&2
      record "production log grep (SHP-05/SHP-06)" "FAIL" "gemini=${GEMINI_LINE:-0} parallel=${PARALLEL_LINE:-0}"
    fi
  fi
fi
hr

# --- Summary -----------------------------------------------------------------
echo ""
echo "=== Pre-submission check summary ==="
printf '%-40s %-10s %s\n' "GATE" "STATUS" "DETAIL"
for row in "${RESULTS[@]}"; do
  IFS='|' read -r name status detail <<< "$row"
  printf '%-40s %-10s %s\n' "$name" "$status" "$detail"
done
echo ""

if [ "$OVERALL_OK" = true ]; then
  echo "READY TO SHIP — every gate passed on this run."
  exit 0
else
  echo "NOT READY TO SHIP — one or more gates failed or are blocked on this run."
  echo "See .planning/SHIP-CHECKLIST.md for the human actions that close the remaining gaps."
  exit 1
fi

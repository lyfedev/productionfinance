#!/usr/bin/env bash
# vendor-scan.sh [ROOT]
#
# D-28: grep the source tree (not only the lockfile) for AWS AI service
# call-site tokens named in .claude/CLAUDE.md — this is the pre-submission
# gate armed early so it cannot be forgotten on day 16, and AWS Textract is
# named there as the single most likely accidental disqualification.
#
# Exit 0 — clean.
# Exit 1 — a forbidden token (or a boto3-qualified `translate` client
#          construction) was found; every match is printed with file:line.
set -uo pipefail

ROOT="${1:-.}"

# Bare, case-insensitive tokens. "translate" and "transcribe" are both
# deliberately excluded from this bare list — they are too common as English
# words to match bare without a flood of false positives (D-28). "translate"
# collides with UI strings and doc headings; "transcribe" collides with this
# project's core provenance verb ("transcribed verbatim from the union's own
# published scale"), which appears throughout data/union_rates/*.yaml and
# sources/MANIFEST.yaml and is exactly the language the audit trail is
# supposed to use. Both are handled separately below, matched only as a
# boto3-qualified client construction — the actual call site, which is what
# D-28 restricts. The service is still caught; the English word is not.
BARE_TOKENS='textract|bedrock|comprehend|rekognition|polly|kendra|sagemaker'

MATCH_FILE=$(mktemp)
trap 'rm -f "$MATCH_FILE"' EXIT

scan_file() {
  local file="$1"
  # This script itself necessarily names every one of these tokens above,
  # but it is a .sh file — outside the *.py/*.toml/*.yaml/*.yml scan set —
  # so it is excluded from the scan by construction (file-extension filter),
  # never by a special-cased path exemption that could mask a real match.
  grep -nEi "$BARE_TOKENS" "$file" 2>/dev/null | sed "s|^|${file}:|" >>"$MATCH_FILE"

  # translate / transcribe: only a boto3-qualified client construction counts.
  grep -nE 'boto3[^()]*\.client\([[:space:]]*["'"'"'](translate|transcribe)["'"'"']' "$file" 2>/dev/null | sed "s|^|${file}:|" >>"$MATCH_FILE"
}

# Two explicit find invocations (rather than a conditionally-built exclude
# array) — bash 3.2 (macOS, used to prove this script fail-first locally)
# treats expanding an empty array under `set -u` as an unbound-variable
# error, so this avoids that pitfall entirely rather than working around it.
if [ "$ROOT" = "." ]; then
  # Default-root scan excludes the fixtures directory (deliberately
  # AI-service-shaped, must never fail a clean-tree scan), .git internals,
  # and the virtualenv (third-party vendored code, not this project's).
  while IFS= read -r -d '' file; do
    scan_file "$file"
  done < <(find "$ROOT" -type f \( -name '*.py' -o -name '*.toml' -o -name '*.yaml' -o -name '*.yml' \) \
    -not -path '*/.github/fixtures/*' -not -path '*/.git/*' -not -path '*/.venv/*' -print0)
else
  while IFS= read -r -d '' file; do
    scan_file "$file"
  done < <(find "$ROOT" -type f \( -name '*.py' -o -name '*.toml' -o -name '*.yaml' -o -name '*.yml' \) -print0)
fi

if [ -s "$MATCH_FILE" ]; then
  echo "FAIL: forbidden AWS AI service reference(s) found (file:line:match):" >&2
  cat "$MATCH_FILE" >&2
  exit 1
fi

echo "PASS: vendor-scan clean over '$ROOT' — no forbidden AWS AI service call-site tokens found"
exit 0

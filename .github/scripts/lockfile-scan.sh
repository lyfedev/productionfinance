#!/usr/bin/env bash
# lockfile-scan.sh [LOCKFILE]
#
# SHP-07: assert the *resolved* uv lockfile contains none of the packages
# forbidden by .claude/CLAUDE.md's "Forbidden Python packages" list, and
# assert google-adk (when present) carries no extras marker.
#
# Exit 0  — lockfile clean.
# Exit 1  — lockfile missing, empty of resolved packages, contains a
#           forbidden package, or google-adk is present with extras.
set -uo pipefail

LOCKFILE="${1:-uv.lock}"

if [ ! -f "$LOCKFILE" ]; then
  echo "FAIL: lockfile not found at '$LOCKFILE'" >&2
  exit 1
fi

# uv.lock records each resolved package's name as an unindented, top-level
# `name = "..."` field directly under its `[[package]]` header. Dependency
# *references* inside a `dependencies = [...]` array are inline tables
# (`{ name = "..." }`), which are indented and brace-wrapped — this anchored,
# unindented pattern does not match them, so only real resolved packages are
# extracted, never a package's own dependency edges.
#
# Built with a plain while-read loop (not `mapfile`) for portability to
# bash 3.2 (macOS default, used to prove this script fail-first locally) as
# well as the modern bash on GitHub Actions' ubuntu-latest runners.
PACKAGES=()
while IFS= read -r line; do
  PACKAGES+=("$line")
done < <(grep -E '^name = "' "$LOCKFILE" | sed -E 's/^name = "(.*)"$/\1/')

if [ "${#PACKAGES[@]}" -eq 0 ]; then
  echo "FAIL: extracted zero resolved package names from '$LOCKFILE' — a scan over an empty set is a green light that proves nothing" >&2
  exit 1
fi

# Exact forbidden package names (.claude/CLAUDE.md "Forbidden Python packages").
FORBIDDEN_EXACT=("openai" "anthropic" "langgraph" "crewai" "llama-index" "litellm")

OFFENDERS=()
for pkg in "${PACKAGES[@]}"; do
  for forbidden in "${FORBIDDEN_EXACT[@]}"; do
    if [ "$pkg" = "$forbidden" ]; then
      OFFENDERS+=("$pkg (exact match: $forbidden)")
    fi
  done
  # Any package whose first path segment is "langchain" — catches
  # "langchain-google-genai", "langchain-core", bare "langchain", etc. —
  # matched on the whole extracted name, anchored, never a bare substring
  # search, so e.g. a hypothetical "mylangchain-utils" package would NOT
  # match (its first segment is "mylangchain", not "langchain").
  case "$pkg" in
    langchain|langchain-*)
      OFFENDERS+=("$pkg (langchain-family match)")
      ;;
  esac
done

if [ "${#OFFENDERS[@]}" -gt 0 ]; then
  echo "FAIL: forbidden package(s) found in resolved lockfile '$LOCKFILE':" >&2
  for o in "${OFFENDERS[@]}"; do
    echo "  - $o" >&2
  done
  exit 1
fi

# google-adk extras assertion (SHP-07): absent from the lockfile is a pass —
# it is a Phase 5/7 dependency and is legitimately absent today. Present is
# only a pass if the resolved entry carries no extras marker; extras such as
# [all]/[extensions]/[test] pull disallowed vendors transitively.
GOOGLE_ADK_PRESENT=false
for pkg in "${PACKAGES[@]}"; do
  if [ "$pkg" = "google-adk" ]; then
    GOOGLE_ADK_PRESENT=true
    break
  fi
done

if [ "$GOOGLE_ADK_PRESENT" = true ]; then
  # Any line that mentions google-adk AND carries an extras marker on the
  # same line is how uv.lock records a requested extra — inline tables like
  # `{ name = "google-adk", extras = ["all"], specifier = ">=2.7.1" }` under
  # [package.metadata] requires-dist, or a dependent's own dependencies list,
  # are always single-line TOML inline tables.
  if grep -Ei 'google-adk' "$LOCKFILE" | grep -Eiq 'extras? *[=:]'; then
    echo "FAIL: google-adk is present in '$LOCKFILE' and carries an extras marker ([all]/[extensions]/[test]) — extras pull disallowed vendors transitively" >&2
    exit 1
  fi
  echo "PASS: google-adk is present in '$LOCKFILE' with no extras marker"
else
  echo "PASS: google-adk is ABSENT from '$LOCKFILE' — absence is a pass (SHP-07; google-adk is a Phase 5/7 dependency, legitimately absent today)"
fi

echo "PASS: lockfile-scan clean — ${#PACKAGES[@]} resolved package(s) checked against '$LOCKFILE', no forbidden packages found"
exit 0

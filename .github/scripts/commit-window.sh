#!/usr/bin/env bash
# commit-window.sh [CUTOFF]
#
# SHP-09: assert every commit reachable from every ref has an author date on
# or after the contest window's opening date. Requires a full-history
# checkout (fetch-depth: 0) — a shallow checkout cannot see all commits and
# must never read as a pass.
#
# Exit 0 — every reachable commit is authored on or after CUTOFF.
# Exit 1 — the checkout is shallow (`git rev-parse --is-shallow-repository`),
#          `git log --all` yields zero commits (empty checkout — a shallow
#          clone with depth 1 still has one commit, so this is a distinct,
#          explicit check rather than relying on commit count alone), the
#          cutoff cannot be parsed, or one or more commits are authored
#          strictly before CUTOFF (all offenders are printed).
set -uo pipefail

CUTOFF="${1:-2026-07-27}"

# Portable epoch parser: GNU date (Linux/GitHub Actions runners) then BSD
# date (macOS, for local proving).
_epoch() {
  local d="$1"
  date -u -d "$d" +%s 2>/dev/null || date -u -j -f "%Y-%m-%d" "$d" +%s 2>/dev/null
}

CUTOFF_EPOCH=$(_epoch "$CUTOFF")
if [ -z "$CUTOFF_EPOCH" ]; then
  echo "FAIL: could not parse cutoff date '$CUTOFF' (expected YYYY-MM-DD)" >&2
  exit 1
fi

# Explicit shallow-repository check — a `--depth 1` clone still has one
# reachable commit (the tip), so a commit-count check alone would not catch
# it; `git rev-parse --is-shallow-repository` is the direct signal.
IS_SHALLOW=$(git rev-parse --is-shallow-repository 2>/dev/null || echo "unknown")
if [ "$IS_SHALLOW" = "true" ]; then
  echo "FAIL: this is a shallow checkout ('git rev-parse --is-shallow-repository' reports true) — it cannot see full history and must never read as a pass; the workflow checkout must use fetch-depth: 0" >&2
  exit 1
fi

COMMITS=$(git log --all --no-color --date=short --pretty=format:'%ad %H' 2>/dev/null || true)

if [ -z "$COMMITS" ]; then
  echo "FAIL: 'git log --all' returned zero commits — this is what an empty repository looks like, and must never read as a pass" >&2
  exit 1
fi

OFFENDERS=()
while IFS=' ' read -r author_date sha; do
  [ -z "$author_date" ] && continue
  d_epoch=$(_epoch "$author_date")
  if [ -n "$d_epoch" ] && [ "$d_epoch" -lt "$CUTOFF_EPOCH" ]; then
    OFFENDERS+=("$author_date $sha")
  fi
done <<<"$COMMITS"

TOTAL=$(printf '%s\n' "$COMMITS" | grep -c .)

if [ "${#OFFENDERS[@]}" -gt 0 ]; then
  echo "FAIL: commit(s) authored before the contest window (cutoff $CUTOFF; a commit authored exactly on the cutoff passes):" >&2
  for o in "${OFFENDERS[@]}"; do
    echo "  - $o" >&2
  done
  exit 1
fi

echo "PASS: all $TOTAL commit(s) reachable from all refs are authored on or after $CUTOFF"
exit 0

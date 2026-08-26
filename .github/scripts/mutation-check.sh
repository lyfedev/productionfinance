#!/usr/bin/env bash
# mutation-check.sh
#
# SHP-14 (second half): the validation suite in test_engine_against_
# validation_pairs.py is proven not merely present but non-vacuous — this
# script deliberately mutates a New York rule value by one basis point, on
# a scratch copy of the repository, and confirms five things in order:
#   1. the suite is green BEFORE any mutation (a suite that starts red
#      proves nothing)
#   2. the suite actually collects a non-zero count of New York exact-mode
#      assertions (the real vacuity check — an empty parametrize list
#      passes every other step silently)
#   3. the declared mutation lands exactly once in the target file
#   4. the mutated suite goes red, and goes red naming the declared test —
#      not a collection, import, or environment error
#   5. the target file is restored byte-identical and the suite is green
#      again
#
# Mutations are declared as rows in tests/mutation_targets.yaml (D-51),
# never hard-coded here — adding a second jurisdiction's anchor (e.g.
# Connecticut's Christmas Always, once WINDOWS.md #3 clears) is a one-row
# table addition, not a script change.
#
# D-50: every step below runs inside a directory created by `mktemp -d`
# and removed by an EXIT trap. `.venv` and `.git` are deleted from the
# scratch copy before any step runs, so this script structurally cannot
# reach, commit to, or push the real repository. `git status --porcelain`
# on the invoking working tree must be byte-identical before and after a
# run of this script, including a run that is interrupted or fails
# partway.
#
# Invoke from the repository root: bash .github/scripts/mutation-check.sh
#
# Exit 0 — every active mutation row passed all five steps.
# Exit 1 — a table row failed a step, the table is missing/empty/malformed,
#          or the pre-mutation suite was already red.
set -uo pipefail

TABLE="tests/mutation_targets.yaml"
VALIDATION_SUITE="tests/test_engine_against_validation_pairs.py"

if [ ! -f "pyproject.toml" ] || [ ! -f "$TABLE" ]; then
  echo "FAIL: must be invoked from the repository root (pyproject.toml and '$TABLE' not found in \$PWD)" >&2
  exit 1
fi

SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

echo "==> Copying repository into scratch directory: $SCRATCH"
cp -R . "$SCRATCH"
rm -rf "$SCRATCH/.venv"
rm -rf "$SCRATCH/.git"
cd "$SCRATCH"

# Read active rows out of the declared table as tab-separated records:
# id, file, find, replace, expected_red_test — one record per line, using
# yaml.safe_load only. A row missing any of the eight required keys is
# reported as MALFORMED rather than silently dropped.
ROWS=()
while IFS= read -r line; do
  ROWS+=("$line")
done < <(uv run python - <<'PY'
import sys

import yaml

REQUIRED_KEYS = {
    "id",
    "file",
    "find",
    "replace",
    "expected_red_test",
    "requirement",
    "status",
    "why",
}
FIELDS_FOR_SCRIPT = ["id", "file", "find", "replace", "expected_red_test"]

with open("tests/mutation_targets.yaml") as f:
    table = yaml.safe_load(f)

rows = (table or {}).get("mutation_targets") or []
for row in rows:
    if not isinstance(row, dict) or row.get("status") != "active":
        continue
    if not REQUIRED_KEYS <= set(row):
        print("MALFORMED\t" + str(row.get("id", "<no id>")))
        continue
    print("\t".join(str(row[k]) for k in FIELDS_FOR_SCRIPT))
PY
)

if [ "${#ROWS[@]}" -eq 0 ]; then
  echo "FAIL: zero active rows in '$TABLE' — a mutation gate over an empty table is a green light that proves nothing" >&2
  exit 1
fi

ROW_COUNT=${#ROWS[@]}
ROW_INDEX=0

for ROW in "${ROWS[@]}"; do
  ROW_INDEX=$((ROW_INDEX + 1))

  if [[ "$ROW" == MALFORMED* ]]; then
    BAD_ID="${ROW#MALFORMED$'\t'}"
    echo "FAIL: row '$BAD_ID' in '$TABLE' is missing one of the required keys (id, file, find, replace, expected_red_test, requirement, status, why)" >&2
    exit 1
  fi

  IFS=$'\t' read -r ID FILE FIND REPLACE EXPECTED_RED_TEST <<< "$ROW"

  echo "=== Row ${ROW_INDEX}/${ROW_COUNT}: ${ID} ==="

  if [ ! -f "$FILE" ]; then
    echo "FAIL: [$ID] declared target file '$FILE' not found in the scratch copy" >&2
    exit 1
  fi

  # --- Step 1: green unmutated ------------------------------------------
  echo "--> Step 1: asserting the suite is green before any mutation"
  if ! uv run --frozen pytest "$VALIDATION_SUITE" -q; then
    echo "FAIL: [$ID] step 1 — the validation suite is already red before any mutation was applied; a suite that starts red proves nothing" >&2
    exit 1
  fi
  echo "PASS: [$ID] step 1 — suite green, unmutated"

  # --- Step 2: the real vacuity check ------------------------------------
  echo "--> Step 2: asserting a non-zero New York exact-mode assertion is actually collected"

  NY_EXACT_COUNT=$(uv run python - <<'PY'
import glob

import yaml

count = 0
for path in sorted(glob.glob("tests/fixtures/validation_pairs/*.yaml")):
    with open(path) as f:
        data = yaml.safe_load(f)
    if data.get("jurisdiction_id") != "us-ny":
        continue
    if data.get("status") != "active":
        continue
    if (data.get("assertion") or {}).get("mode") != "exact":
        continue
    count += 1
print(count)
PY
  )

  if ! [[ "$NY_EXACT_COUNT" =~ ^[0-9]+$ ]] || [ "$NY_EXACT_COUNT" -eq 0 ]; then
    echo "FAIL: [$ID] step 2 — zero active New York exact-mode fixtures found under tests/fixtures/validation_pairs/*.yaml; the suite would be vacuously green" >&2
    exit 1
  fi

  COLLECT_OUTPUT=$(uv run --frozen pytest "$EXPECTED_RED_TEST" -q --collect-only 2>&1)
  COLLECT_EXIT=$?
  COLLECTED_COUNT=$(printf '%s\n' "$COLLECT_OUTPUT" | grep -c '::' || true)

  if [ "$COLLECT_EXIT" -ne 0 ] || [ "$COLLECTED_COUNT" -eq 0 ]; then
    echo "FAIL: [$ID] step 2 — '$EXPECTED_RED_TEST' collected zero items; the test may have been renamed, skipped, or its parametrize list emptied" >&2
    echo "$COLLECT_OUTPUT" >&2
    exit 1
  fi
  echo "PASS: [$ID] step 2 — ${NY_EXACT_COUNT} active New York exact-mode fixture(s) on disk, ${COLLECTED_COUNT} item(s) collected for '$EXPECTED_RED_TEST'"

  # --- Step 3: apply the declared mutation --------------------------------
  echo "--> Step 3: applying the declared mutation to '$FILE'"
  cp "$FILE" "$FILE.orig"

  sed "s/${FIND}/${REPLACE}/" "$FILE" > "$FILE.mut"
  mv "$FILE.mut" "$FILE"

  # Count occurrences of the replacement fragment outside comment lines —
  # a bare unfiltered count would also match rule-file prose (header
  # comments, source_note) that mentions the same figure.
  ACTUAL_COUNT=$(grep -v '^[[:space:]]*#' "$FILE" | grep -Fc -- "$REPLACE" || true)
  if [ "$ACTUAL_COUNT" -ne 1 ]; then
    echo "FAIL: [$ID] step 3 — the declared find pattern no longer matches its target exactly once in '$FILE' (found ${ACTUAL_COUNT} occurrence(s) outside comment lines); a no-op mutation followed by a green suite is a false proof" >&2
    exit 1
  fi

  # --- Step 4: red, and red for the right reason --------------------------
  echo "--> Step 4: asserting the mutated suite goes red, and goes red naming '$EXPECTED_RED_TEST'"
  RED_OUTPUT=$(uv run --frozen pytest "$EXPECTED_RED_TEST" -q 2>&1)
  RED_EXIT=$?

  if [ "$RED_EXIT" -eq 0 ]; then
    echo "FAIL: [$ID] step 4 — mutated suite is still green for '$EXPECTED_RED_TEST'; SHP-14's non-vacuity claim is false" >&2
    echo "$RED_OUTPUT" >&2
    exit 1
  fi

  if printf '%s\n' "$RED_OUTPUT" | grep -Eiq 'errors? during collection|ERROR collecting|ModuleNotFoundError|ImportError'; then
    echo "FAIL: [$ID] step 4 — '$EXPECTED_RED_TEST' failed with a collection/import/environment error, not the expected assertion failure" >&2
    echo "$RED_OUTPUT" >&2
    exit 1
  fi

  TEST_FUNC_NAME="${EXPECTED_RED_TEST##*::}"
  if ! printf '%s\n' "$RED_OUTPUT" | grep -Fq -- "$TEST_FUNC_NAME"; then
    echo "FAIL: [$ID] step 4 — '$EXPECTED_RED_TEST' failed, but its output does not name the declared test function '$TEST_FUNC_NAME'" >&2
    echo "$RED_OUTPUT" >&2
    exit 1
  fi
  echo "PASS: [$ID] step 4 — '$EXPECTED_RED_TEST' correctly failed under the mutation"

  # --- Step 5: restore and re-assert green --------------------------------
  echo "--> Step 5: restoring '$FILE' and re-asserting green"
  cp "$FILE.orig" "$FILE"

  if ! cmp -s "$FILE" "$FILE.orig"; then
    echo "FAIL: [$ID] step 5 — restored '$FILE' is not byte-identical to its pre-mutation original" >&2
    exit 1
  fi

  if ! uv run --frozen pytest "$VALIDATION_SUITE" -q; then
    echo "FAIL: [$ID] step 5 — the restore did not return the tree to a state where the suite passes" >&2
    exit 1
  fi

  rm -f "$FILE.orig"
  echo "PASS: [$ID] step 5 — file restored byte-identical, suite green again"
done

echo "PASS: mutation-check complete — ${ROW_COUNT} active row(s) exercised, all five steps passed for each"
exit 0

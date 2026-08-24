#!/usr/bin/env bash
# End-to-end HTTP smoke check for the ProductionFinance FastAPI app.
#
# If SMOKE_BASE_URL is set, probes that URL and does not start a server
# (used against the live host in plans 01-08 and 01-09). Otherwise starts
# a local uvicorn process, probes it, and tears it down on exit.
set -eu

PORT="${PRODFIN_SMOKE_PORT:-8010}"
BASE_URL="${SMOKE_BASE_URL:-http://127.0.0.1:${PORT}}"
SERVER_PID=""

cleanup() {
  if [ -n "${SERVER_PID}" ]; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [ -z "${SMOKE_BASE_URL:-}" ]; then
  uv run uvicorn app.main:app --host 127.0.0.1 --port "${PORT}" >/tmp/prodfin-smoke.log 2>&1 &
  SERVER_PID=$!
fi

echo "Smoke testing ${BASE_URL} ..."

ATTEMPTS=20
SLEEP_SECONDS=0.5
UP=0

for i in $(seq 1 "${ATTEMPTS}"); do
  if curl -s -o /dev/null -w '%{http_code}' "${BASE_URL}/health" 2>/dev/null | grep -q '^200$'; then
    UP=1
    break
  fi
  sleep "${SLEEP_SECONDS}"
done

if [ "${UP}" -ne 1 ]; then
  echo "FAIL: /health did not return 200 after ${ATTEMPTS} attempts"
  exit 1
fi

HEALTH_CODE=$(curl -s -o /tmp/prodfin-smoke-health.json -w '%{http_code}' "${BASE_URL}/health")
if [ "${HEALTH_CODE}" != "200" ]; then
  echo "FAIL: GET /health returned ${HEALTH_CODE}"
  exit 1
fi
echo "PASS: GET /health returned 200"

if ! grep -q 'git_sha' /tmp/prodfin-smoke-health.json; then
  echo "FAIL: /health body missing git_sha"
  exit 1
fi
echo "PASS: /health body carries git_sha"

if ! grep -q 'boot_time' /tmp/prodfin-smoke-health.json; then
  echo "FAIL: /health body missing boot_time"
  exit 1
fi
echo "PASS: /health body carries boot_time"

ROOT_CODE=$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL}/")
if [ "${ROOT_CODE}" != "200" ]; then
  echo "FAIL: GET / returned ${ROOT_CODE}"
  exit 1
fi
echo "PASS: GET / returned 200"

echo "Smoke test passed."
exit 0

#!/usr/bin/env bash
# deploy/deploy.sh — the entire deploy path for ProductionFinance (D-19).
#
# Code reaches the host by `git pull` plus this one script — no CI push, no
# rsync from a developer machine. Idempotent and safe to re-run.
#
# Intended to be run on the host as a user with passwordless sudo (e.g.
# `bitnami`), NOT as the `prodfin` service account itself — it needs sudo to
# restart the systemd unit. Git and uv operations run as `prodfin` via
# `sudo -u prodfin` so the application tree and venv stay owned by the
# service account throughout.
#
# Usage: bash deploy/deploy.sh
# (run from anywhere; it cd's to PRODFIN_APP_ROOT itself)

set -eu

PRODFIN_APP_ROOT="${PRODFIN_APP_ROOT:-/opt/prodfin}"
PRODFIN_SERVICE="${PRODFIN_SERVICE:-prodfin.service}"
PRODFIN_SERVICE_USER="${PRODFIN_SERVICE_USER:-prodfin}"
PRODFIN_APP_PORT="${PRODFIN_APP_PORT:-8000}"
UV_CACHE_DIR="${PRODFIN_APP_ROOT}/.cache"

echo "==> Deploying ProductionFinance to ${PRODFIN_APP_ROOT}"

echo "==> git pull --ff-only (as ${PRODFIN_SERVICE_USER})"
sudo -u "${PRODFIN_SERVICE_USER}" git -C "${PRODFIN_APP_ROOT}" pull --ff-only origin main

GIT_SHA="$(sudo -u "${PRODFIN_SERVICE_USER}" git -C "${PRODFIN_APP_ROOT}" rev-parse --short HEAD)"
echo "==> Checked out ${GIT_SHA}"

echo "==> uv sync --frozen (as ${PRODFIN_SERVICE_USER})"
sudo -u "${PRODFIN_SERVICE_USER}" env UV_CACHE_DIR="${UV_CACHE_DIR}" bash -c \
  "cd '${PRODFIN_APP_ROOT}' && uv sync --frozen"

echo "==> Recording PRODFIN_GIT_SHA=${GIT_SHA} into ${PRODFIN_APP_ROOT}/.env"
sudo -u "${PRODFIN_SERVICE_USER}" bash -c "
  touch '${PRODFIN_APP_ROOT}/.env'
  if grep -q '^PRODFIN_GIT_SHA=' '${PRODFIN_APP_ROOT}/.env' 2>/dev/null; then
    sed -i 's/^PRODFIN_GIT_SHA=.*/PRODFIN_GIT_SHA=${GIT_SHA}/' '${PRODFIN_APP_ROOT}/.env'
  else
    printf 'PRODFIN_GIT_SHA=%s\n' '${GIT_SHA}' >> '${PRODFIN_APP_ROOT}/.env'
  fi
"
sudo chmod 0600 "${PRODFIN_APP_ROOT}/.env"
sudo chown "${PRODFIN_SERVICE_USER}:${PRODFIN_SERVICE_USER}" "${PRODFIN_APP_ROOT}/.env"

echo "==> systemctl restart ${PRODFIN_SERVICE}"
sudo systemctl restart "${PRODFIN_SERVICE}"

echo "==> Waiting for ${PRODFIN_SERVICE} to become active"
ATTEMPTS=20
for i in $(seq 1 "${ATTEMPTS}"); do
  if sudo systemctl is-active --quiet "${PRODFIN_SERVICE}"; then
    break
  fi
  sleep 0.5
  if [ "${i}" -eq "${ATTEMPTS}" ]; then
    echo "FAIL: ${PRODFIN_SERVICE} did not become active after ${ATTEMPTS} attempts" >&2
    sudo systemctl status "${PRODFIN_SERVICE}" --no-pager || true
    exit 1
  fi
done
echo "==> ${PRODFIN_SERVICE} is active"

echo "==> Health-checking http://127.0.0.1:${PRODFIN_APP_PORT}/health"
HEALTH_ATTEMPTS=10
UP=0
for i in $(seq 1 "${HEALTH_ATTEMPTS}"); do
  if curl -fsS -o /dev/null "http://127.0.0.1:${PRODFIN_APP_PORT}/health"; then
    UP=1
    break
  fi
  sleep 0.5
done
if [ "${UP}" -ne 1 ]; then
  echo "FAIL: /health did not return 200 after restart" >&2
  exit 1
fi

echo "==> Deploy complete. git_sha=${GIT_SHA}"
curl -fsS "http://127.0.0.1:${PRODFIN_APP_PORT}/health"
echo

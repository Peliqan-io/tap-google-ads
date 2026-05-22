#!/usr/bin/env bash
set -euo pipefail
TAP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PIP_CACHE="${HOME}/.cache/pip-tap-google-ads"
mkdir -p "$PIP_CACHE"

echo "==> Running baseline capture in python:3.9-slim"
docker run --rm \
  -v "$TAP_DIR":/tap \
  -v "$PIP_CACHE":/root/.cache/pip \
  -w /tap \
  -e TAP_GOOGLE_ADS_OAUTH_CLIENT_ID="${TAP_GOOGLE_ADS_OAUTH_CLIENT_ID:?}" \
  -e TAP_GOOGLE_ADS_OAUTH_CLIENT_SECRET="${TAP_GOOGLE_ADS_OAUTH_CLIENT_SECRET:?}" \
  -e TAP_GOOGLE_ADS_REFRESH_TOKEN="${TAP_GOOGLE_ADS_REFRESH_TOKEN:?}" \
  -e TAP_GOOGLE_ADS_DEVELOPER_TOKEN="${TAP_GOOGLE_ADS_DEVELOPER_TOKEN:?}" \
  -e TAP_GOOGLE_ADS_MANAGER_ACCOUNT_ID="${TAP_GOOGLE_ADS_MANAGER_ACCOUNT_ID:-}" \
  -e TAP_GOOGLE_ADS_ACCOUNT_IDS="${TAP_GOOGLE_ADS_ACCOUNT_IDS:?}" \
  -e TAP_GOOGLE_ADS_INCLUDE_STREAMS="${TAP_GOOGLE_ADS_INCLUDE_STREAMS:-campaign,customer}" \
  -e TAP_GOOGLE_ADS_START_DATE="${TAP_GOOGLE_ADS_START_DATE:-2026-01-01T00:00:00Z}" \
  -e AES_SECRET_KEY="peliqan-test-key" \
  python:3.9-slim \
  bash -c "
    apt-get update -qq && apt-get install -y -qq git > /dev/null
    python -m venv /venv
    /venv/bin/pip install -e . -q
    /venv/bin/python tests/regression/capture.py
  "
echo ""
echo "==> Baseline written to tests/regression/baseline/"

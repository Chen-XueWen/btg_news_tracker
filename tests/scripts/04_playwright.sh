#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

TS="${1:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="test_evidence/reports/${TS}/04_playwright"
mkdir -p "$OUT_DIR"

STATUS_FILE="$OUT_DIR/status.txt"
LOG_FILE="$OUT_DIR/playwright.log"
JSON_REPORT="$OUT_DIR/playwright_report.json"

if [ ! -f "tests/playwright/package.json" ]; then
  echo "status=missing_playwright_package" > "$STATUS_FILE"
  echo "Missing playwright package config under tests/playwright" > "$LOG_FILE"
  exit 0
fi

E2E_BASE_URL="${E2E_BASE_URL:-http://localhost:5173}"
if ! curl -fsS "$E2E_BASE_URL" >/dev/null 2>&1; then
  echo "status=base_url_unreachable" > "$STATUS_FILE"
  echo "E2E base URL not reachable: $E2E_BASE_URL" > "$LOG_FILE"
  echo "Start frontend server, then rerun with E2E_BASE_URL if needed."
  exit 0
fi

set +e
(
  cd tests/playwright
  npm install > "$ROOT_DIR/$OUT_DIR/npm_install.log" 2>&1 && \
  npx playwright install chromium > "$ROOT_DIR/$OUT_DIR/playwright_install.log" 2>&1 && \
  PLAYWRIGHT_JSON_OUTPUT_NAME="$ROOT_DIR/$JSON_REPORT" E2E_BASE_URL="$E2E_BASE_URL" \
    npx playwright test > "$ROOT_DIR/$LOG_FILE" 2>&1
)
TEST_EXIT=$?
set -e

if [ "$TEST_EXIT" -eq 0 ]; then
  echo "status=executed_success" > "$STATUS_FILE"
else
  echo "status=executed_failure_exit_${TEST_EXIT}" > "$STATUS_FILE"
fi

echo "Playwright run finished with exit code: $TEST_EXIT"

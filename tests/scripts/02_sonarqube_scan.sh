#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

TS="${1:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="test_evidence/reports/${TS}/02_sonarqube"
mkdir -p "$OUT_DIR"

LOG_FILE="$OUT_DIR/sonarqube_scan.log"
STATUS_FILE="$OUT_DIR/status.txt"

SCANNER_CMD=()
if command -v sonar-scanner >/dev/null 2>&1; then
  SCANNER_CMD=("sonar-scanner")
elif command -v npx >/dev/null 2>&1; then
  SCANNER_CMD=("npx" "--yes" "sonar-scanner")
else
  echo "status=missing_sonar_scanner" > "$STATUS_FILE"
  echo "Neither sonar-scanner nor npx is available." > "$LOG_FILE"
  echo "SonarQube scan could not run: scanner tooling missing."
  exit 0
fi

if [ -z "${SONAR_HOST_URL:-}" ] || [ -z "${SONAR_TOKEN:-}" ] || [ -z "${SONAR_PROJECT_KEY:-}" ]; then
  echo "status=missing_required_env" > "$STATUS_FILE"
  {
    echo "Missing required environment variables."
    echo "Required: SONAR_HOST_URL, SONAR_TOKEN, SONAR_PROJECT_KEY"
  } > "$LOG_FILE"
  echo "SonarQube scan could not run: missing required environment variables."
  exit 0
fi

set +e
"${SCANNER_CMD[@]}" \
  -Dsonar.projectKey="$SONAR_PROJECT_KEY" \
  -Dsonar.projectName="btg-news-tracker" \
  -Dsonar.sources="backend/app,frontend/src" \
  -Dsonar.tests="tests/integration,tests/playwright/tests" \
  -Dsonar.host.url="$SONAR_HOST_URL" \
  -Dsonar.token="$SONAR_TOKEN" \
  -Dsonar.qualitygate.wait=true \
  > "$LOG_FILE" 2>&1
SCAN_EXIT=$?
set -e

if [ "$SCAN_EXIT" -eq 0 ]; then
  echo "status=executed_success" > "$STATUS_FILE"
else
  echo "status=executed_failure_exit_${SCAN_EXIT}" > "$STATUS_FILE"
fi

echo "SonarQube scan finished with exit code: $SCAN_EXIT"

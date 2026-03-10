#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

TS="${1:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="test_evidence/reports/${TS}/03_pytest"
mkdir -p "$OUT_DIR"

LOG_FILE="$OUT_DIR/pytest.log"
JUNIT_FILE="$OUT_DIR/pytest_junit.xml"
STATUS_FILE="$OUT_DIR/status.txt"

PYTEST_BIN="backend/.venv/bin/python"
if [ ! -x "$PYTEST_BIN" ]; then
  echo "status=missing_backend_python" > "$STATUS_FILE"
  echo "Missing backend virtualenv python: $PYTEST_BIN" > "$LOG_FILE"
  exit 0
fi

set +e
$PYTEST_BIN -m pytest tests/integration/test_api_integration.py \
  -q --maxfail=1 --junitxml="$JUNIT_FILE" > "$LOG_FILE" 2>&1
TEST_EXIT=$?
set -e

if [ "$TEST_EXIT" -eq 0 ]; then
  echo "status=executed_success" > "$STATUS_FILE"
else
  echo "status=executed_failure_exit_${TEST_EXIT}" > "$STATUS_FILE"
fi

echo "Pytest run finished with exit code: $TEST_EXIT"

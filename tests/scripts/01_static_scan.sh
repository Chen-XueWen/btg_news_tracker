#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

TS="${1:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="test_evidence/reports/${TS}/01_static_scan"
mkdir -p "$OUT_DIR"

STATUS_FILE="$OUT_DIR/status.txt"
SUMMARY_FILE="$OUT_DIR/summary.md"

: > "$STATUS_FILE"

# Python static analysis: Bandit
if backend/.venv/bin/python -m bandit --version >/dev/null 2>&1; then
  backend/.venv/bin/python -m bandit -r backend/app -f json -o "$OUT_DIR/bandit_report.json" \
    > "$OUT_DIR/bandit.stdout.log" 2> "$OUT_DIR/bandit.stderr.log" || true
  echo "bandit=executed" >> "$STATUS_FILE"
else
  echo "bandit=missing" >> "$STATUS_FILE"
fi

# Python dependency vulnerability scan: pip-audit
if backend/.venv/bin/python -m pip_audit --version >/dev/null 2>&1; then
  backend/.venv/bin/python -m pip_audit -r backend/requirements.txt -f json \
    > "$OUT_DIR/pip_audit_report.json" 2> "$OUT_DIR/pip_audit.stderr.log" || true
  echo "pip_audit=executed" >> "$STATUS_FILE"
else
  echo "pip_audit=missing" >> "$STATUS_FILE"
fi

# Node dependency vulnerability scan
(
  cd frontend
  npm audit --json --audit-level=high > "$ROOT_DIR/$OUT_DIR/npm_audit_report.json" \
    2> "$ROOT_DIR/$OUT_DIR/npm_audit.stderr.log"
) || true
if [ -s "$OUT_DIR/npm_audit_report.json" ]; then
  echo "npm_audit=executed" >> "$STATUS_FILE"
else
  echo "npm_audit=failed_or_unavailable" >> "$STATUS_FILE"
fi

{
  echo "# Static Scan Summary"
  echo
  echo "- Output directory: \`$OUT_DIR\`"
  echo "- Timestamp: \`$TS\`"
  echo
  echo "## Tool Status"
  sed 's/^/- /' "$STATUS_FILE"
  echo
  echo "## Generated Files"
  find "$OUT_DIR" -maxdepth 1 -type f | sort | sed 's#^#- #'
} > "$SUMMARY_FILE"

echo "Static scan artifacts generated at: $OUT_DIR"

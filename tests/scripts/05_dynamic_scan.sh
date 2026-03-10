#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if git -C "$SCRIPT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
else
  ROOT_DIR="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
fi
cd "$ROOT_DIR"

TS="${1:-$(date +%Y%m%d_%H%M%S)}"
TARGET_BASE_URL="${TARGET_BASE_URL:-http://127.0.0.1:8000}"
OUT_DIR="test_evidence/reports/${TS}/05_dynamic_scan"
mkdir -p "$OUT_DIR"

STATUS_FILE="$OUT_DIR/status.txt"
JSON_FILE="$OUT_DIR/dynamic_scan_report.json"
MD_FILE="$OUT_DIR/dynamic_scan_report.md"
RAW_DIR="$OUT_DIR/raw"
mkdir -p "$RAW_DIR"

if ! curl -fsS "$TARGET_BASE_URL/api/health" > "$RAW_DIR/health_probe.json" 2> "$RAW_DIR/health_probe.err"; then
  echo "status=target_unreachable" > "$STATUS_FILE"
  cat > "$JSON_FILE" <<JSON
{
  "status": "target_unreachable",
  "target_base_url": "$TARGET_BASE_URL",
  "timestamp": "$TS",
  "message": "Failed to reach $TARGET_BASE_URL/api/health"
}
JSON
  cat > "$MD_FILE" <<MD
# Dynamic Scan Report

- Status: target_unreachable
- Target: $TARGET_BASE_URL
- Timestamp: $TS
- Message: Failed to reach $TARGET_BASE_URL/api/health
MD
  echo "Dynamic scan could not execute: target unreachable"
  exit 0
fi

health_code=$(curl -s -o "$RAW_DIR/health_body.json" -w "%{http_code}" "$TARGET_BASE_URL/api/health")
health_headers=$(curl -sSI "$TARGET_BASE_URL/api/health" > "$RAW_DIR/health_headers.txt"; cat "$RAW_DIR/health_headers.txt")

# Security headers check
get_header() {
  local name="$1"
  local header_name_lc
  header_name_lc="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')"
  awk -v n="$header_name_lc" '
    {
      raw = $0
      line = tolower($0)
      if (index(line, n ":") == 1) {
        sub(/^[^:]+:[[:space:]]*/, "", raw)
        sub(/\r$/, "", raw)
        print raw
        exit
      }
    }
  ' "$RAW_DIR/health_headers.txt" || true
}

hsts="$(get_header 'Strict-Transport-Security')"
xcto="$(get_header 'X-Content-Type-Options')"
xfo="$(get_header 'X-Frame-Options')"
csp="$(get_header 'Content-Security-Policy')"
refp="$(get_header 'Referrer-Policy')"
perm="$(get_header 'Permissions-Policy')"

# OPTIONS behavior
options_code=$(curl -s -o "$RAW_DIR/options_body.txt" -w "%{http_code}" -X OPTIONS "$TARGET_BASE_URL/api/news")

# Invalid JSON handling
invalid_json_code=$(curl -s -o "$RAW_DIR/invalid_json_body.json" -w "%{http_code}" -X POST "$TARGET_BASE_URL/api/news" -H "Content-Type: application/json" -d '{bad-json')

# Oversized topic check
oversized_topic=$(python3 - <<'PY'
print('A'*300)
PY
)
oversized_payload=$(jq -n --arg t "$oversized_topic" '{topic:$t, scoring_metrics:[]}')
oversized_code=$(curl -s -o "$RAW_DIR/oversized_body.json" -w "%{http_code}" -X POST "$TARGET_BASE_URL/api/news" -H "Content-Type: application/json" -d "$oversized_payload")

# Simple reflected XSS probe in topic
xss_payload=$(jq -n --arg t "<script>alert(1)</script>" '{topic:$t, scoring_metrics:[]}')
xss_code=$(curl -s -o "$RAW_DIR/xss_body.json" -w "%{http_code}" -X POST "$TARGET_BASE_URL/api/news" -H "Content-Type: application/json" -d "$xss_payload")

# Read response bodies for reflection test
xss_reflected="false"
if rg -q "<script>alert\(1\)</script>" "$RAW_DIR/xss_body.json"; then
  xss_reflected="true"
fi

# CORS check
cors_header="$(get_header 'Access-Control-Allow-Origin')"

# Simple risk scoring
critical=0
high=0
medium=0
low=0
notes=()

if [[ "$health_code" != "200" ]]; then
  high=$((high+1))
  notes+=("Health endpoint did not return 200.")
fi

if [[ -z "$xcto" ]]; then
  medium=$((medium+1))
  notes+=("Missing X-Content-Type-Options header.")
fi
if [[ -z "$xfo" ]]; then
  low=$((low+1))
  notes+=("Missing X-Frame-Options header.")
fi
if [[ -z "$csp" ]]; then
  low=$((low+1))
  notes+=("Missing Content-Security-Policy header on API response.")
fi
if [[ -z "$hsts" ]]; then
  low=$((low+1))
  notes+=("Missing Strict-Transport-Security header (expected behind TLS in production).")
fi
if [[ "$xss_reflected" == "true" ]]; then
  high=$((high+1))
  notes+=("Potential reflected payload observed in API response.")
fi
if [[ "$cors_header" == "*" ]]; then
  medium=$((medium+1))
  notes+=("Wildcard CORS origin detected.")
fi

notes_json='[]'
if ((${#notes[@]} > 0)); then
  notes_json="$(printf '%s\n' "${notes[@]}" | jq -R . | jq -s .)"
fi

overall_status="pass"
if (( critical > 0 || high > 0 )); then
  overall_status="fail"
elif (( medium > 0 )); then
  overall_status="pass_with_findings"
fi

echo "status=executed_$overall_status" > "$STATUS_FILE"

# Write JSON report
jq -n \
  --arg status "$overall_status" \
  --arg target "$TARGET_BASE_URL" \
  --arg ts "$TS" \
  --arg health_code "$health_code" \
  --arg options_code "$options_code" \
  --arg invalid_json_code "$invalid_json_code" \
  --arg oversized_code "$oversized_code" \
  --arg xss_code "$xss_code" \
  --arg xss_reflected "$xss_reflected" \
  --arg hsts "$hsts" \
  --arg xcto "$xcto" \
  --arg xfo "$xfo" \
  --arg csp "$csp" \
  --arg refp "$refp" \
  --arg perm "$perm" \
  --arg cors "$cors_header" \
  --argjson critical "$critical" \
  --argjson high "$high" \
  --argjson medium "$medium" \
  --argjson low "$low" \
  --argjson notes "$notes_json" \
  '{
    status: $status,
    target_base_url: $target,
    timestamp: $ts,
    checks: {
      health_http_code: $health_code,
      options_http_code: $options_code,
      invalid_json_http_code: $invalid_json_code,
      oversized_topic_http_code: $oversized_code,
      xss_probe_http_code: $xss_code,
      xss_reflected: ($xss_reflected == "true"),
      headers: {
        strict_transport_security: $hsts,
        x_content_type_options: $xcto,
        x_frame_options: $xfo,
        content_security_policy: $csp,
        referrer_policy: $refp,
        permissions_policy: $perm,
        access_control_allow_origin: $cors
      }
    },
    findings: {
      critical: $critical,
      high: $high,
      medium: $medium,
      low: $low,
      notes: $notes
    }
  }' > "$JSON_FILE"

{
  echo "# Dynamic Scan Report"
  echo
  echo "- Run ID: \`$TS\`"
  echo "- Target: \`$TARGET_BASE_URL\`"
  echo "- Overall status: \`$overall_status\`"
  echo
  echo "## HTTP Behavior Checks"
  echo "- /api/health: \`$health_code\`"
  echo "- OPTIONS /api/news: \`$options_code\`"
  echo "- POST invalid JSON /api/news: \`$invalid_json_code\`"
  echo "- POST oversized topic /api/news: \`$oversized_code\`"
  echo "- POST XSS probe /api/news: \`$xss_code\`"
  echo "- XSS reflected in response: \`$xss_reflected\`"
  echo
  echo "## Security Headers Snapshot (/api/health)"
  echo "- Strict-Transport-Security: \`${hsts:-<missing>}\`"
  echo "- X-Content-Type-Options: \`${xcto:-<missing>}\`"
  echo "- X-Frame-Options: \`${xfo:-<missing>}\`"
  echo "- Content-Security-Policy: \`${csp:-<missing>}\`"
  echo "- Referrer-Policy: \`${refp:-<missing>}\`"
  echo "- Permissions-Policy: \`${perm:-<missing>}\`"
  echo "- Access-Control-Allow-Origin: \`${cors_header:-<missing>}\`"
  echo
  echo "## Findings"
  echo "- Critical: $critical"
  echo "- High: $high"
  echo "- Medium: $medium"
  echo "- Low: $low"
  if ((${#notes[@]} > 0)); then
    echo "- Notes:"
    for n in "${notes[@]}"; do
      echo "  - $n"
    done
  else
    echo "- Notes: none"
  fi
  echo
  echo "## Evidence Files"
  echo "- JSON: \`$JSON_FILE\`"
  echo "- Raw responses: \`$RAW_DIR\`"
} > "$MD_FILE"

echo "Dynamic scan completed. Report: $MD_FILE"

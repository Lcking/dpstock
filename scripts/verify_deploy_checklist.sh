#!/usr/bin/env bash
# Post-deploy smoke checks for Agu AI production.
# Usage: BASE_URL=https://aguai.net ./scripts/verify_deploy_checklist.sh

set -euo pipefail

BASE_URL="${BASE_URL:-https://aguai.net}"
BASE_URL="${BASE_URL%/}"

echo "== Agu AI deploy verification =="
echo "Target: ${BASE_URL}"
echo

failures=0

check_status() {
  local path="$1"
  local expected="${2:-200}"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${BASE_URL}${path}")"
  if [[ "${code}" != "${expected}" ]]; then
    echo "FAIL ${path} -> HTTP ${code} (expected ${expected})"
    failures=$((failures + 1))
    return 1
  fi
  echo "OK   ${path} -> HTTP ${code}"
}

check_redirect() {
  local path="$1"
  local expected_location="$2"
  local headers
  headers="$(curl -sSI "${BASE_URL}${path}" | tr -d '\r')"
  local code location
  code="$(echo "${headers}" | awk 'toupper($1) ~ /^HTTP/ {print $2; exit}')"
  location="$(echo "${headers}" | awk -F': ' 'tolower($1)=="location" {print $2; exit}')"
  if [[ "${code}" != "302" ]]; then
    echo "FAIL ${path} -> HTTP ${code} (expected 302)"
    failures=$((failures + 1))
    return 1
  fi
  if [[ "${location}" != "${expected_location}" ]]; then
    echo "FAIL ${path} -> Location ${location:-<empty>} (expected ${expected_location})"
    failures=$((failures + 1))
    return 1
  fi
  echo "OK   ${path} -> 302 -> ${expected_location}"
}

check_grep() {
  local path="$1"
  local pattern="$2"
  local body
  body="$(curl -sS "${BASE_URL}${path}")"
  if ! echo "${body}" | grep -Eq "${pattern}"; then
    echo "FAIL ${path} missing pattern: ${pattern}"
    failures=$((failures + 1))
    return 1
  fi
  echo "OK   ${path} contains /${pattern}/"
}

check_json_field() {
  local path="$1"
  local python_expr="$2"
  local body
  body="$(curl -sS "${BASE_URL}${path}")"
  if ! echo "${body}" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if (${python_expr}) else 1)"; then
    echo "FAIL ${path} json check: ${python_expr}"
    failures=$((failures + 1))
    return 1
  fi
  echo "OK   ${path} json: ${python_expr}"
}

check_absent_grep() {
  local path="$1"
  local pattern="$2"
  local body
  body="$(curl -sS "${BASE_URL}${path}")"
  if echo "${body}" | grep -Eq "${pattern}"; then
    echo "FAIL ${path} should not contain: ${pattern}"
    failures=$((failures + 1))
    return 1
  fi
  echo "OK   ${path} excludes /${pattern}/"
}

# Core availability
check_status "/api/health" || true
check_status "/sitemap.xml" || true
check_status "/stock/600519" || true
check_status "/risk-stocks" || true
check_status "/me/weekly-recap" || true
check_status "/api/risk-stocks/export/csv" || true
check_status "/api/ops/analyze-slo" || true

# SEO / GEO surfaces
check_grep "/stock/600519" "FAQPage|常见问题|600519" || true
check_grep "/analysis/1680" "常见问题|FAQPage" || true

# Private weekly recap (legacy URL redirects into SPA)
check_redirect "/review/weekly" "/me/weekly-recap" || true
check_json_field "/api/user-center/weekly-recap" "d.get('scope')=='user' and 'stats' in d" || true

# ETF article chart data path
check_json_field "/api/kline/159941?market_type=ETF&days=5" "not d.get('error') and len(d.get('dates',[]))>0" || true

# Public sitemap must not expose private weekly recap SSR
check_absent_grep "/sitemap-core.xml" "review/weekly" || true

echo
if [[ "${failures}" -gt 0 ]]; then
  echo "Verification finished with ${failures} failure(s)."
  exit 1
fi

echo "All deploy checks passed."

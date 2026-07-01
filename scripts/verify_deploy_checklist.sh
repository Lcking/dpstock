#!/usr/bin/env bash
# Post-deploy smoke checks for Agu AI production.
# Usage: BASE_URL=https://aguai.net ./scripts/verify_deploy_checklist.sh

set -euo pipefail

BASE_URL="${BASE_URL:-https://aguai.net}"
BASE_URL="${BASE_URL%/}"

echo "== Agu AI deploy verification =="
echo "Target: ${BASE_URL}"
echo

check_status() {
  local path="$1"
  local expected="${2:-200}"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${BASE_URL}${path}")"
  if [[ "${code}" != "${expected}" ]]; then
    echo "FAIL ${path} -> HTTP ${code} (expected ${expected})"
    return 1
  fi
  echo "OK   ${path} -> HTTP ${code}"
}

check_grep() {
  local path="$1"
  local pattern="$2"
  local body
  body="$(curl -sS "${BASE_URL}${path}")"
  if ! echo "${body}" | grep -Eq "${pattern}"; then
    echo "FAIL ${path} missing pattern: ${pattern}"
    return 1
  fi
  echo "OK   ${path} contains /${pattern}/"
}

failures=0

check_status "/api/health" || failures=$((failures + 1))
check_status "/sitemap.xml" || failures=$((failures + 1))
check_status "/stock/600519" || failures=$((failures + 1))
check_status "/review/weekly" || failures=$((failures + 1))
check_status "/risk-stocks" || failures=$((failures + 1))

check_grep "/stock/600519" "FAQPage|常见问题|600519" || failures=$((failures + 1))
check_grep "/review/weekly" "历史验证|仅供参考" || failures=$((failures + 1))

echo
if [[ "${failures}" -gt 0 ]]; then
  echo "Verification finished with ${failures} failure(s)."
  exit 1
fi

echo "All deploy checks passed."

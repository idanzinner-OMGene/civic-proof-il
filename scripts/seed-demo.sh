#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

API_URL="${API_URL:-http://localhost:8000}"

echo "Phase 0 seed-demo: verifying readiness at ${API_URL}/readyz"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

RESP=$(curl -fsS "${API_URL}/readyz")
echo "$RESP"

echo ""
echo "Phase 0 seed-demo complete. Real seeding lands in Phase 2."

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILE="infra/docker/docker-compose.yml"
TIMEOUT="${TIMEOUT:-180}"
DEADLINE=$(( $(date +%s) + TIMEOUT ))

echo "Waiting up to ${TIMEOUT}s for services to be healthy..."

while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  STATUS=$(docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null || echo "[]")
  # Count services whose Health is not "healthy" (excluding "migrator" which exits)
  UNHEALTHY=$(echo "$STATUS" | python3 -c '
import sys, json
try:
    data = json.loads(sys.stdin.read() or "[]")
except json.JSONDecodeError:
    data = []
if isinstance(data, dict):
    data = [data]
bad = []
for svc in data:
    name = svc.get("Service") or svc.get("Name", "?")
    health = svc.get("Health", "")
    state = svc.get("State", "")
    if name == "migrator":
        if state not in ("exited",):
            bad.append(f"{name}:{state}")
        continue
    if health and health != "healthy":
        bad.append(f"{name}:{health}")
print(",".join(bad))
')
  if [ -z "$UNHEALTHY" ]; then
    echo "All services healthy."
    exit 0
  fi
  echo "  still waiting: $UNHEALTHY"
  sleep 3
done

echo "Timeout waiting for services." >&2
docker compose -f "$COMPOSE_FILE" ps >&2 || true
exit 1

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  if [ ! -f .env.example ]; then
    echo "error: neither .env nor .env.example exists at $(pwd)" >&2
    exit 1
  fi
  cp .env.example .env
  echo "Copied .env.example -> .env"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install it from https://docs.astral.sh/uv/ and re-run." >&2
  echo "  macOS / Linux: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

echo "Syncing uv workspace..."
uv sync

echo "Bootstrap complete."

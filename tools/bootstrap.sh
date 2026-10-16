#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../core"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found; install it from https://docs.astral.sh/uv/" >&2
  exit 1
fi

uv sync

echo
echo "Engine environment ready. Try:"
echo "  uv run harness load ../projects/gearbox-demo"
echo "  uv run harness solve ../projects/gearbox-demo"
echo "  uv run harness verify ../projects/gearbox-demo"

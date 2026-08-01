#!/usr/bin/env bash
#
# One command that answers "does this repo still work?".
#
# Runs the same four checks CI runs (.github/workflows/ci.yml). Keep the two
# in step — if you add a gate here, add it there.
#
# The Windows UIA adapter needs a real desktop session and is not covered:
# it is exercised by hand during phase spikes. Everything here runs on any
# platform.
#
# Usage: ./scripts/verify.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> uv sync --extra dev"
uv sync --extra dev

echo "==> ruff"
uv run ruff check .

echo "==> black"
uv run black --check .

echo "==> pytest"
uv run pytest -q

echo
echo "OK — lint, format and tests all pass."

#!/bin/sh
set -eu

MODE="${DOCPULSE_MODE:-check}"
CONFIG="${DOCPULSE_CONFIG:-docpulse.yml}"
WORK="${GITHUB_WORKSPACE:-$(pwd)}"
BASE="${DOCPULSE_BASE_REF:-}"
if [ -z "$BASE" ]; then
  BASE="origin/${GITHUB_BASE_REF:-main}"
fi

# Actions checks out into a dir owned by a different uid; mark it safe for git.
git config --global --add safe.directory "$WORK" || true
# Ensure the base ref is present for the diff (checkout often uses fetch-depth: 1).
git -C "$WORK" fetch --no-tags --depth=50 origin "${GITHUB_BASE_REF:-main}" || true

docpulse index --root "$WORK" --config "$WORK/$CONFIG"
exec docpulse "$MODE" --base "$BASE" --root "$WORK" --config "$WORK/$CONFIG" --push

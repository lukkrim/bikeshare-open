#!/usr/bin/env bash
# Stop hook: Claude may not finish a turn while the test suite is red.
#
# Exit 2 blocks the stop and sends stderr back to Claude as the reason.
# If stop_hook_active is true, Claude is already continuing because of this
# hook; let it stop so a suite it cannot fix does not loop forever.
set -uo pipefail

payload=$(cat)
active=$(printf '%s' "$payload" | python3 -c \
  'import json,sys; print(str(json.load(sys.stdin).get("stop_hook_active", False)).lower())')
[ "$active" = "true" ] && exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
PY=".venv/bin/python"; [ -x "$PY" ] || PY=python3
if ! out=$("$PY" -m pytest tests/ -q --tb=line -p no:cacheprovider 2>&1); then
  echo "Test suite is red; fix it or report the failure before stopping:" >&2
  echo "$out" | tail -20 >&2
  exit 2
fi
exit 0

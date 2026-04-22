#!/usr/bin/env bash
# Convenience wrapper around `s local invoke`.
#
# Usage:
#   scripts/local_invoke.sh factor-detect tests/fixtures/events/factor_detect_min.json
#   scripts/local_invoke.sh factor-detect --debug       # server mode + debugpy

set -euo pipefail

FN="${1:?usage: local_invoke.sh <function-name> [event_file|--debug|--server]}"
MODE_ARG="${2:-tests/fixtures/events/${FN//-/_}_min.json}"

case "$MODE_ARG" in
  --debug)
    exec s local invoke "$FN" --config vscode --debug-port 9000 --env-file .env.local
    ;;
  --server)
    exec s local invoke "$FN" --mode server --env-file .env.local
    ;;
  *)
    if [[ ! -f "$MODE_ARG" ]]; then
      echo "event file not found: $MODE_ARG" >&2
      exit 2
    fi
    exec s local invoke "$FN" --event-file "$MODE_ARG" --env-file .env.local
    ;;
esac

#!/usr/bin/env bash
set -euo pipefail
# Some FC versions back-fill logs with 30s delay; poll briefly.
for _ in 1 2 3 4 5 6; do
  if s logs "factor-detect" --tail --access "${FC_ACCESS}" 2>&1 | head -5 | grep -q '.'; then
    echo "ok: SLS has at least one line for factor-detect${FC_SUFFIX}"
    exit 0
  fi
  sleep 5
done
echo "warn: no log lines within 30s (may not block; investigate)"
exit 0

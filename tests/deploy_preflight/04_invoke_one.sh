#!/usr/bin/env bash
set -euo pipefail
EVENT_FILE="tests/fixtures/events/factor_detect_min.json"
RESP="$(s cli fc3 invoke \
  --region "${FC_REGION:-cn-hangzhou}" \
  --function-name "factor-detect${FC_SUFFIX}" \
  -e "$(cat "$EVENT_FILE")" \
  --access "${FC_ACCESS}")"
echo "$RESP"
# must have a "tenant" or "status" field
echo "$RESP" | grep -q '"status"' || { echo "fail: missing status"; exit 1; }
echo "ok: invoke returned JSON"

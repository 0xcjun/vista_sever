#!/usr/bin/env bash
set -euo pipefail
# Start execution with a minimal payload; we only verify StartExecution + DescribeExecution succeed
INPUT='{"tenant":{"user_hash":"pf","workspace_id":"EXP_PF","workspace_kind":"research","run_id":"pf","requested_at":"1970-01-01T00:00:00Z"},"user_input":"preflight","route_codes":["R001"],"problem_codes":["P001"]}'
EXEC_NAME="pf-$(date +%s)"
s cli fnf StartExecution \
  --name "research-pipeline${FC_SUFFIX}" \
  --execution-name "$EXEC_NAME" \
  --input "$INPUT" \
  --access "${FC_ACCESS}"

for _ in 1 2 3 4 5; do
  STATUS="$(s cli fnf DescribeExecution --name "research-pipeline${FC_SUFFIX}" --execution-name "$EXEC_NAME" --access "${FC_ACCESS}" -o json | python -c 'import sys,json;print(json.load(sys.stdin).get("Status",""))')"
  echo "status=$STATUS"
  case "$STATUS" in
    Running|Starting) sleep 3 ;;
    Succeeded|Failed|TimedOut|Stopped) break ;;
  esac
done
# Accept non-Succeeded; we only validate StartExecution + status polling plumbing
echo "ok: execution reached terminal or running state"

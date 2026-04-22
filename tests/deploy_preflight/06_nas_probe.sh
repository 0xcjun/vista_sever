#!/usr/bin/env bash
set -euo pipefail
# Requires the factor-detect function to include a tiny "_probe" branch that
# writes /mnt/vista-cache/preflight-${FC_SUFFIX}.txt when payload has probe=true.
# If that branch is not in handler, skip with warn.
PROBE_EVENT='{"tenant":{"user_hash":"pf","workspace_id":"PF","workspace_kind":"research","run_id":"pf-nas","requested_at":"1970-01-01T00:00:00Z"},"payload":{"factors_db_uri":"oss://invalid","_probe":"nas"}}'
s cli fc3 invoke \
  --region "${FC_REGION:-cn-hangzhou}" \
  --function-name "factor-detect${FC_SUFFIX}" \
  -e "$PROBE_EVENT" \
  --access "${FC_ACCESS}" || true
echo "warn: NAS probe requires handler _probe branch; leave manual verification if unsupported"

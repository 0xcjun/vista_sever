#!/usr/bin/env bash
set -euo pipefail
# remove preflight-scoped resources
REGION="${FC_REGION:-cn-hangzhou}"
s cli fnf remove \
  --region "$REGION" \
  --name "research-pipeline${FC_SUFFIX}" \
  --access "${FC_ACCESS}" || true
s remove --access "${FC_ACCESS}" --assume-yes || true
echo "ok: preflight cleanup done"

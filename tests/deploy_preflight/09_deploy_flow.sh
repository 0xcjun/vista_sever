#!/usr/bin/env bash
set -euo pipefail
REGION="${FC_REGION:-cn-hangzhou}"
FLOW_NAME="research-pipeline${FC_SUFFIX}"
s cli fnf deploy \
  --region "$REGION" \
  --name "$FLOW_NAME" \
  --definition flows/research_pipeline.fdl \
  --type FDL \
  --access "${FC_ACCESS}"
s cli fnf info --region "$REGION" --name "$FLOW_NAME" --access "${FC_ACCESS}" >/dev/null
echo "ok: research-pipeline${FC_SUFFIX} flow created"

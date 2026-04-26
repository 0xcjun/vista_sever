#!/usr/bin/env bash
set -euo pipefail
s deploy research-pipeline-flow -t s.flows.yaml --access "${FC_ACCESS}" --assume-yes
s cli fnf GetFlow --name "research-pipeline${FC_SUFFIX}" --access "${FC_ACCESS}" >/dev/null
echo "ok: research-pipeline${FC_SUFFIX} flow created"

#!/usr/bin/env bash
set -euo pipefail
s cli fc3 list --region "${FC_REGION:-cn-hangzhou}" --access "${FC_ACCESS}" >/dev/null
echo "ok: access=${FC_ACCESS} can list FC functions"

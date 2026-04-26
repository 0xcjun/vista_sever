#!/usr/bin/env bash
set -euo pipefail
# Deploy only one function to shorten preflight time.
s deploy -t s.factor-detect.yaml --access "${FC_ACCESS}" --assume-yes
echo "ok: factor-detect${FC_SUFFIX} deployed"

#!/usr/bin/env bash
set -euo pipefail
# Deploy only one function to shorten preflight time.
s deploy factor-detect --access "${FC_ACCESS}" --assume-yes --skip-push
echo "ok: factor-detect${FC_SUFFIX} deployed"

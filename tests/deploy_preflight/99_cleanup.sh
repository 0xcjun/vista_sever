#!/usr/bin/env bash
set -euo pipefail
# remove preflight-scoped resources
s remove --access "${FC_ACCESS}" --assume-yes || true
echo "ok: preflight cleanup done"

#!/usr/bin/env bash
# Thin wrapper that ensures docker is logged into ACR, then delegates to
# build_image.sh --push.
#
# Expected env:
#   ACR_USER, ACR_PASS  — ACR credentials (CI-only; locally use docker login)
#   IMAGE_REGISTRY       — optional override (same as build_image.sh)

set -euo pipefail

REGISTRY_HOST="registry.cn-hangzhou.aliyuncs.com"
if [[ -n "${ACR_USER:-}" && -n "${ACR_PASS:-}" ]]; then
  echo "$ACR_PASS" | docker login "$REGISTRY_HOST" -u "$ACR_USER" --password-stdin
fi

exec scripts/build_image.sh --push "$@"

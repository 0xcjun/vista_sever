#!/usr/bin/env bash
set -euo pipefail
export IMAGE_REGISTRY="${IMAGE_REGISTRY:-registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base}"
export GIT_SHA="${GIT_SHA:-$(git rev-parse --short HEAD)}"
scripts/push_image.sh
docker manifest inspect "${IMAGE_REGISTRY}:${GIT_SHA}" >/dev/null
echo "ok: image ${IMAGE_REGISTRY}:${GIT_SHA} reachable"

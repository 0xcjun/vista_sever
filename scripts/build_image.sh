#!/usr/bin/env bash
# Build the vista-fc-base image locally or for CI.
#
# Usage:
#   scripts/build_image.sh            # build with git_sha tag for push
#   scripts/build_image.sh --dev      # build with :dev tag for s local
#
# Required env / files:
#   .env.build      — contains UV_INDEX_ZBCZSC_DEV_USERNAME/PASSWORD
#   IMAGE_REGISTRY  — default: registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base
#   IMAGE_PLATFORMS — default: linux/amd64,linux/arm64 (only on --push)

set -euo pipefail

DEV_MODE=false
PUSH=false
for arg in "$@"; do
  case "$arg" in
    --dev) DEV_MODE=true ;;
    --push) PUSH=true ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

IMAGE_REGISTRY="${IMAGE_REGISTRY:-registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base}"
GIT_SHA="$(git rev-parse --short=7 HEAD 2>/dev/null || echo unknown)"

if $DEV_MODE; then
  TAG="dev"
  PLATFORMS="linux/$(uname -m | sed 's/x86_64/amd64/;s/arm64/arm64/;s/aarch64/arm64/')"
else
  TAG="$GIT_SHA"
  PLATFORMS="${IMAGE_PLATFORMS:-linux/amd64,linux/arm64}"
fi

IMAGE="${IMAGE_REGISTRY}:${TAG}"

# Secret file expected at .env.build (gitignored). Fallback: env vars already set.
SECRET_ARG=""
if [[ -f .env.build ]]; then
  SECRET_ARG="--secret id=uv_index,src=.env.build"
fi

echo "[build_image] image=${IMAGE} platforms=${PLATFORMS} dev=${DEV_MODE} push=${PUSH}"

# Enable BuildKit and use buildx for multi-arch
export DOCKER_BUILDKIT=1

if $PUSH; then
  docker buildx build \
    --platform "${PLATFORMS}" \
    ${SECRET_ARG} \
    --tag "${IMAGE}" \
    --tag "${IMAGE_REGISTRY}:main" \
    --cache-to type=registry,ref="${IMAGE_REGISTRY}:buildcache",mode=max \
    --cache-from type=registry,ref="${IMAGE_REGISTRY}:buildcache" \
    --push \
    .
else
  docker buildx build \
    --platform "${PLATFORMS}" \
    ${SECRET_ARG} \
    --tag "${IMAGE}" \
    --load \
    .
fi

echo "[build_image] done: ${IMAGE}"

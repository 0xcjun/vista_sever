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
#   IMAGE_PLATFORMS — default: linux/amd64 (only on --push)
#                     注意：chan-factor-rs / chanfactor 只发布 linux_x86_64 wheel，
#                     arm64 linux 无法解析；如需 arm64 部署，先让 vista 团队补 wheel。

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
GIT_SHA="${GIT_SHA:-$(git rev-parse --short=7 HEAD 2>/dev/null || echo unknown)}"

if $DEV_MODE; then
  TAG="dev"
  # 固定 linux/amd64：FC 目标平台为 amd64，且私有 wheel 只发布 x86_64
  PLATFORMS="linux/amd64"
else
  TAG="$GIT_SHA"
  PLATFORMS="${IMAGE_PLATFORMS:-linux/amd64}"
fi

IMAGE="${IMAGE_REGISTRY}:${TAG}"
PYTHON_IMAGE="${PYTHON_IMAGE:-python:3.12-slim-bookworm}"
UV_IMAGE="${UV_IMAGE:-ghcr.io/astral-sh/uv:latest}"
BUILD_ARGS="--build-arg PYTHON_IMAGE=${PYTHON_IMAGE} --build-arg UV_IMAGE=${UV_IMAGE}"

# Secret file expected at .env.build (gitignored). Fallback: env vars already set.
SECRET_ARG=""
if [[ -f .env.build ]]; then
  SECRET_ARG="--secret id=uv_index,src=.env.build"
fi

CACHE_ARGS=""
if $PUSH && [[ "${IMAGE_CACHE:-off}" == "registry" ]]; then
  BUILDX_DRIVER="$(docker buildx inspect 2>/dev/null | awk -F': ' '/^Driver:/ {print $2; exit}')"
  if [[ "$BUILDX_DRIVER" == "docker" ]]; then
    echo "[build_image] registry cache disabled: buildx driver '${BUILDX_DRIVER}' does not support cache export"
  else
    CACHE_ARGS="--cache-to type=registry,ref=${IMAGE_REGISTRY}:buildcache,mode=max --cache-from type=registry,ref=${IMAGE_REGISTRY}:buildcache"
  fi
fi

echo "[build_image] image=${IMAGE} platforms=${PLATFORMS} dev=${DEV_MODE} push=${PUSH}"
echo "[build_image] python_image=${PYTHON_IMAGE} uv_image=${UV_IMAGE}"

# Enable BuildKit and use buildx for multi-arch
export DOCKER_BUILDKIT=1

if $PUSH; then
  docker buildx build \
    --platform "${PLATFORMS}" \
    ${BUILD_ARGS} \
    ${SECRET_ARG} \
    --tag "${IMAGE}" \
    --tag "${IMAGE_REGISTRY}:main" \
    --provenance=false \
    --sbom=false \
    ${CACHE_ARGS} \
    --push \
    .
else
  docker buildx build \
    --platform "${PLATFORMS}" \
    ${BUILD_ARGS} \
    ${SECRET_ARG} \
    --tag "${IMAGE}" \
    --load \
    .
fi

echo "[build_image] done: ${IMAGE}"

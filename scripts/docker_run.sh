#!/usr/bin/env bash
# Fallback: run a handler directly via docker (no serverless-devs required).
# Useful when debugging container boot issues and `s local invoke` obscures them.
#
# Usage:
#   scripts/docker_run.sh factor_detect tests/fixtures/events/factor_detect_min.json
#
# Needs .env.local. Assumes image tag :dev exists (run build_image.sh --dev first).

set -euo pipefail

HANDLER="${1:?usage: docker_run.sh <handler_name> <event_file>}"
EVENT_FILE="${2:?usage: docker_run.sh <handler_name> <event_file>}"

IMAGE_REGISTRY="${IMAGE_REGISTRY:-registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base}"
IMAGE="${IMAGE_REGISTRY}:dev"
CONTAINER_NAME="vista-fc-${HANDLER}-$$"
# 默认 9878（9000 在本地 compose 里被 MinIO 占用）
PORT="${PORT:-9878}"

EVENT_JSON="$(cat "$EVENT_FILE")"

cleanup() { docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true; }

echo "[docker_run] starting $IMAGE ($HANDLER) on :$PORT"
# Rewrite localhost-targeted endpoints in .env.local to host.docker.internal so
# the container can reach MinIO / ClickHouse running on the dev host.
HOST_ENV="$(mktemp -t vista-fc-env.XXXXXX)"
trap 'rm -f "$HOST_ENV"; cleanup' EXIT
sed -E 's#(=https?://)(localhost|127\.0\.0\.1)([:/]|$)#\1host.docker.internal\3#g' .env.local > "$HOST_ENV"

docker run -d --rm \
  --name "$CONTAINER_NAME" \
  --env-file "$HOST_ENV" \
  --add-host=host.docker.internal:host-gateway \
  -p "${PORT}:9000" \
  "$IMAGE" \
  "handlers.${HANDLER}:handler" >/dev/null

# wait for /health
for _ in $(seq 1 50); do
  if curl -sf "http://localhost:${PORT}/health" >/dev/null; then
    break
  fi
  sleep 0.1
done

echo "[docker_run] POST /invoke"
curl -s -X POST \
  -H "Content-Type: application/json" \
  --data-binary "$EVENT_JSON" \
  "http://localhost:${PORT}/invoke" \
  | tee /tmp/vista_fc_invoke_resp.json
echo
echo "[docker_run] response saved to /tmp/vista_fc_invoke_resp.json"

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
PORT="${PORT:-9000}"

EVENT_JSON="$(cat "$EVENT_FILE")"

cleanup() { docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "[docker_run] starting $IMAGE ($HANDLER) on :$PORT"
docker run -d --rm \
  --name "$CONTAINER_NAME" \
  --env-file .env.local \
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

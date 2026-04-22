#!/usr/bin/env bash
# Idempotent bucket bootstrap for local minio.
set -euo pipefail

MC_ALIAS="${MC_ALIAS:-local}"
ENDPOINT="${ENDPOINT:-http://localhost:9000}"
USER="${USER:-dev}"
PASS="${PASS:-devdevdev}"
BUCKET="${BUCKET:-vista-fc-dev}"

docker run --rm --network host minio/mc:latest /bin/sh -c "
  mc alias set $MC_ALIAS $ENDPOINT $USER $PASS &&
  (mc ls $MC_ALIAS/$BUCKET || mc mb $MC_ALIAS/$BUCKET)
"

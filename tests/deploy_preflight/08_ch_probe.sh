#!/usr/bin/env bash
set -euo pipefail
# SELECT 1 via clickhouse HTTP; requires CLICKHOUSE_URL reachable from this runner
# (preflight usually runs from a jump host with VPC access).
curl -sf "${CLICKHOUSE_URL}/?user=${CLICKHOUSE_USER}&password=${CLICKHOUSE_PASS}" \
  --data-binary 'SELECT 1'
echo
echo "ok: ClickHouse SELECT 1"

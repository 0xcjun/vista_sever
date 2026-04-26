#!/usr/bin/env bash
# Deploy the full research stack (8 functions + 3 fnf flows).
#
# Per-function yamls are the canonical config — this script just iterates over
# all of them. To deploy / redeploy a single function, run `s deploy -t s.<fn>.yaml`
# directly. Realtime variants (s.realtime-cron.yaml, s.realtime-event.yaml) are
# deployed separately on demand.
#
# Usage:
#   scripts/deploy_all.sh                 # deploy all research yamls
#   scripts/deploy_all.sh --dry-run       # print what would be deployed
#   FC_ACCESS=prod scripts/deploy_all.sh  # pick environment

set -euo pipefail

cd "$(dirname "$0")/.."

YAMLS=(
  s.factor-plan.yaml
  s.factor-builder.yaml
  s.factor-detect.yaml
  s.factor-duplicate.yaml
  s.factor-evaluate.yaml
  s.factor-filter.yaml
  s.strategy-backtest.yaml
  s.deadletter.yaml
  s.flows.yaml
)

if [[ "${1:-}" == "--dry-run" ]]; then
  printf '[deploy_all] would run:\n'
  for f in "${YAMLS[@]}"; do
    printf '  s deploy -t %s --access %s --assume-yes\n' "$f" "${FC_ACCESS:-default}"
  done
  exit 0
fi

for f in "${YAMLS[@]}"; do
  echo "============================================================"
  echo "[deploy_all] $f"
  echo "============================================================"
  s deploy -t "$f" --access "${FC_ACCESS:-default}" --assume-yes
done

echo
echo "[deploy_all] all done."

#!/usr/bin/env bash
# Preflight: deploy to an isolated FC namespace with git_sha suffix, invoke,
# probe OSS/NAS/CH/flow, then tear down.
#
# Required env:
#   FC_ACCESS=dev-preflight        (access alias with scoped RAM)
#   GIT_SHA=$(git rev-parse --short HEAD)
#   FC_SUFFIX="-preflight-${GIT_SHA}"
#   Plus everything any s.*.yaml vars block consumes (OSS_BUCKET=vista-fc-preflight, etc.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACTS_DIR="${SCRIPT_DIR}/artifacts/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ARTIFACTS_DIR"

export GIT_SHA="${GIT_SHA:-$(git rev-parse --short HEAD)}"
export FC_SUFFIX="${FC_SUFFIX:--preflight-${GIT_SHA}}"
export FC_ACCESS="${FC_ACCESS:-dev-preflight}"
export OSS_BUCKET="${OSS_BUCKET:-vista-fc-preflight}"

echo "[preflight] suffix=${FC_SUFFIX} access=${FC_ACCESS} bucket=${OSS_BUCKET}"
echo "[preflight] artifacts -> $ARTIFACTS_DIR"

fail=0
for step in \
    00_verify.sh \
    01_credentials.sh \
    02_image_push.sh \
    03_deploy_one.sh \
    04_invoke_one.sh \
    05_logs.sh \
    06_nas_probe.sh \
    07_oss_probe.sh \
    08_ch_probe.sh \
    09_deploy_flow.sh \
    10_execute_flow.sh
do
  name="${step%.sh}"
  printf "\n[preflight] == %s ==\n" "$name"
  if ! bash "${SCRIPT_DIR}/${step}" 2>&1 | tee "${ARTIFACTS_DIR}/${name}.log"; then
    echo "[preflight] FAIL at ${name}"
    fail=1
    break
  fi
done

echo
echo "[preflight] cleaning up ..."
bash "${SCRIPT_DIR}/99_cleanup.sh" 2>&1 | tee "${ARTIFACTS_DIR}/99_cleanup.log" || true

if [[ $fail -ne 0 ]]; then
  echo "[preflight] overall: FAIL"
  exit 1
fi
echo "[preflight] overall: OK"

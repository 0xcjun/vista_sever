#!/usr/bin/env bash
set -euo pipefail
# Use aliyun oss CLI to put+get an empty object into the preflight bucket path.
python - <<'PY'
import os, oss2
auth = oss2.Auth(os.environ["OSS_ACCESS_KEY_ID"], os.environ["OSS_ACCESS_KEY_SECRET"])
ep = f"https://oss-{os.environ.get('FC_REGION','cn-hangzhou')}.aliyuncs.com"
bucket = oss2.Bucket(auth, ep, os.environ["OSS_BUCKET"])
bucket.put_object("_probe/preflight.txt", b"hello")
assert bucket.object_exists("_probe/preflight.txt")
print("ok: OSS put+head OK")
PY

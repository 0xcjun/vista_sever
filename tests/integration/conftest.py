"""Integration test fixtures.

- s_local_runner:  subprocess wrapper for `s local invoke <fn>`.
  Tests using it MUST be decorated with pytest.mark.s_local so they can be
  skipped en masse when `s` or the image are unavailable.
- seeded_oss:      connects to local minio via oss2 with dev creds; supports put_fixture.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class InvokeResult:
    status_code: int
    stdout: str
    stderr: str
    body: dict | None

    def json(self) -> dict:
        assert self.body is not None
        return self.body


def _find_json_block(text: str) -> dict | None:
    # `s local invoke` interleaves logs and the response. Grab the last JSON
    # object that looks plausible.
    last: dict | None = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
    return last


@pytest.fixture
def s_local_runner() -> Callable[..., InvokeResult]:
    if shutil.which("s") is None:
        pytest.skip("serverless-devs (`s`) CLI not installed")
    if shutil.which("docker") is None:
        pytest.skip("docker not installed")

    def _invoke(
        fn_name: str,
        event: dict,
        *,
        env_file: str = ".env.local",
        timeout: int = 120,
    ) -> InvokeResult:
        event_path = ROOT / f".integration-event-{fn_name}.json"
        event_path.write_text(json.dumps(event), encoding="utf-8")
        try:
            proc = subprocess.run(
                [
                    "s",
                    "local",
                    "invoke",
                    fn_name,
                    "--event-file",
                    str(event_path),
                    "--env-file",
                    env_file,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            body = _find_json_block(proc.stdout)
            return InvokeResult(
                status_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                body=body,
            )
        finally:
            event_path.unlink(missing_ok=True)

    return _invoke


@pytest.fixture(scope="session")
def seeded_oss():
    """Local minio OSS client; skips if minio is not reachable."""
    import oss2

    endpoint = os.environ.get("OSS_ENDPOINT", "http://localhost:9000")
    bucket_name = os.environ.get("OSS_BUCKET", "vista-fc-dev")
    ak = os.environ.get("OSS_ACCESS_KEY_ID", "dev")
    sk = os.environ.get("OSS_ACCESS_KEY_SECRET", "devdevdev")
    auth = oss2.Auth(ak, sk)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    # probe reachability
    try:
        bucket.list_objects(max_keys=1)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"local minio unreachable ({endpoint}): {e}")

    class _Helper:
        def put_fixture(self, fixture_name: str, *, target: str) -> str:
            src = ROOT / "tests" / "fixtures" / "duckdb" / fixture_name
            assert src.exists(), f"fixture {src} missing"
            bucket.put_object_from_file(target, str(src))
            return f"oss://{bucket_name}/{target}"

        def exists(self, oss_uri: str) -> bool:
            assert oss_uri.startswith(f"oss://{bucket_name}/")
            key = oss_uri.split("/", 3)[3]
            return bucket.object_exists(key)

    return _Helper()

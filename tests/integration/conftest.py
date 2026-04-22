"""Integration test fixtures.

- s_local_runner:  subprocess wrapper for `s local invoke <fn>`.
  Requires serverless-devs CLI + docker image built with vista installed.
- seeded_oss:      boto3 S3 client against local MinIO. Uses AWS S3
  signature (MinIO compatible); tests set OSS_S3_COMPAT=true and use
  `OssClient.from_env()` to exercise the same backend.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
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
    last: dict | None = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                last = json.loads(s)
            except json.JSONDecodeError:
                continue
    return last


def _minio_reachable(host: str = "127.0.0.1", port: int = 9000, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


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
            return InvokeResult(
                status_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                body=_find_json_block(proc.stdout),
            )
        finally:
            event_path.unlink(missing_ok=True)

    return _invoke


@pytest.fixture(scope="session")
def seeded_oss():
    """Boto3 S3 client against local MinIO. Skips if MinIO is down."""
    if not _minio_reachable():
        pytest.skip("MinIO not reachable on localhost:9000")

    import boto3

    endpoint = os.environ.get("OSS_ENDPOINT", "http://localhost:9000")
    bucket_name = os.environ.get("OSS_BUCKET", "vista-fc-dev")
    ak = os.environ.get("OSS_ACCESS_KEY_ID", "dev")
    sk = os.environ.get("OSS_ACCESS_KEY_SECRET", "devdevdev")
    region = os.environ.get("OSS_REGION", "us-east-1")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
    )
    try:
        client.head_bucket(Bucket=bucket_name)
    except Exception:  # noqa: BLE001
        client.create_bucket(Bucket=bucket_name)

    class _Helper:
        def put_fixture(self, fixture_name: str, *, target: str) -> str:
            src = ROOT / "tests" / "fixtures" / "duckdb" / fixture_name
            assert src.exists(), f"fixture {src} missing"
            client.upload_file(str(src), bucket_name, target)
            return f"oss://{bucket_name}/{target}"

        def exists(self, oss_uri: str) -> bool:
            assert oss_uri.startswith(f"oss://{bucket_name}/")
            key = oss_uri.split("/", 3)[3]
            try:
                client.head_object(Bucket=bucket_name, Key=key)
                return True
            except Exception:  # noqa: BLE001
                return False

    return _Helper()

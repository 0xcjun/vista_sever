"""End-to-end against real MinIO via OSS_S3_COMPAT mode.

Requires `docker compose -f dev/compose.yaml up -d` (minio on :9000).
Skipped gracefully if MinIO is not reachable.

What this test proves end-to-end:
  1. OssClient dispatches to boto3 when OSS_S3_COMPAT=true
  2. Real HTTP round-trip against MinIO works (put/get/head/exists)
  3. factor_detect_service pipeline runs against a live S3-compatible store
  4. Artifact lands in the bucket and is retrievable
"""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "duckdb" / "mini_factors.duckdb"


def _minio_reachable(host: str = "127.0.0.1", port: int = 9000, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


try:
    import vista.utils.factor_detect  # noqa: F401

    vista_available = True
except ImportError:
    vista_available = False


pytestmark = [
    pytest.mark.skipif(not _minio_reachable(), reason="MinIO not reachable on localhost:9000"),
    pytest.mark.skipif(not vista_available, reason="vista not installed"),
    pytest.mark.skipif(not FIXTURE.exists(), reason="mini_factors.duckdb missing"),
]


@pytest.fixture
def minio_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSS_S3_COMPAT", "true")
    monkeypatch.setenv("OSS_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("OSS_REGION", "us-east-1")  # MinIO default
    monkeypatch.setenv("OSS_BUCKET", "vista-fc-dev")
    monkeypatch.setenv("OSS_ACCESS_KEY_ID", "dev")
    monkeypatch.setenv("OSS_ACCESS_KEY_SECRET", "devdevdev")


@pytest.fixture
def s3_bucket(minio_env: None):
    """Direct boto3 client against MinIO, used to seed & probe."""
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url="http://localhost:9000",
        region_name="us-east-1",
        aws_access_key_id="dev",  # pragma: allowlist secret
        aws_secret_access_key="devdevdev",  # pragma: allowlist secret
    )
    # ensure bucket exists (minio-setup service creates it, but be defensive)
    try:
        client.head_bucket(Bucket="vista-fc-dev")
    except Exception:  # noqa: BLE001
        client.create_bucket(Bucket="vista-fc-dev")
    return client


def test_ossclient_roundtrip_via_s3_compat(minio_env: None, s3_bucket, tmp_path: Path) -> None:
    """Low-level: OssClient.from_env() → boto3 backend → put/get/head/exists cycle."""
    from vista_fc.storage.oss_client import OssClient

    client = OssClient.from_env()
    assert client.bucket_name == "vista-fc-dev"

    src = tmp_path / "hello.txt"
    src.write_bytes(b"hello s3")

    key = "_itest/oss_client_roundtrip.txt"
    put = client.put_from_file(key=key, local_path=src)
    assert put.etag  # MinIO returns a quoted MD5 etag

    assert client.exists(key=key) is True
    head = client.head(key=key)
    assert head.size_bytes == src.stat().st_size

    dst = tmp_path / "back.txt"
    client.get_to_file(key=key, local_path=dst)
    assert dst.read_bytes() == b"hello s3"

    # cleanup
    s3_bucket.delete_object(Bucket="vista-fc-dev", Key=key)


def test_factor_detect_full_pipeline_against_minio(
    minio_env: None,
    s3_bucket,
    tmp_path: Path,
) -> None:
    """End-to-end: fixture → MinIO → WorkspaceStorage → vista → artifact back in MinIO."""
    from vista_fc.contracts.common import TenantContext
    from vista_fc.contracts.factor_detect import FactorDetectInput
    from vista_fc.services.factor_detect import factor_detect_service
    from vista_fc.storage.oss_client import OssClient
    from vista_fc.storage.workspace import WorkspaceStorage

    # 1. seed fixture in MinIO
    db_key = "user_data/u_itest/research/EXP_IT_MINIO/factors.duckdb"
    s3_bucket.upload_file(str(FIXTURE), "vista-fc-dev", db_key)

    # 2. build real workspace
    tenant = TenantContext(
        user_hash="u_itest",
        workspace_id="EXP_IT_MINIO",
        workspace_kind="research",
        run_id="run-it-minio-001",
        requested_at=datetime.now(UTC),
    )
    ws = WorkspaceStorage(
        oss=OssClient.from_env(),
        tenant=tenant,
        tmp_root=tmp_path,
    )

    # 3. invoke the real service
    out = factor_detect_service(
        tenant=tenant,
        payload=FactorDetectInput(
            factors_db_uri=f"oss://vista-fc-dev/{db_key}",
            max_workers=1,
            timeout=30,
        ),
        workspace=ws,
    )

    # 4. assertions
    assert out.report_artifact.kind == "report_json"
    assert out.report_artifact.oss_uri.startswith("oss://vista-fc-dev/user_data/u_itest/research/EXP_IT_MINIO/reports/")
    assert out.report_artifact.size_bytes > 0

    # Report artifact actually lives in MinIO
    report_key = out.report_artifact.oss_uri.split("/", 3)[3]
    assert OssClient.from_env().exists(key=report_key)

    # cleanup
    s3_bucket.delete_object(Bucket="vista-fc-dev", Key=db_key)
    s3_bucket.delete_object(Bucket="vista-fc-dev", Key=report_key)

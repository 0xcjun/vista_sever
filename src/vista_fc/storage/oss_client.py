"""OssClient — thin typed wrapper around oss2, with optional S3-compat mode.

Responsible for:
- reading OSS config from env (region / endpoint / bucket / ak / sk)
- get_to_file / put_from_file with optional If-Match (ETag lock)
- head / exists

By default uses `oss2` (Aliyun OSS wire protocol). When `OSS_S3_COMPAT=true`
(or auto-detected from a localhost endpoint), switches to a boto3 S3 backend
for AWS-S3-compatible local stores (MinIO, LocalStack). Production code paths
are unchanged: the public API remains identical.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import oss2

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class ObjectMeta:
    etag: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class PutResult:
    etag: str


class _BucketBackend(Protocol):
    """The subset of oss2.Bucket methods that OssClient uses.

    Positional-only to match both oss2 (`filename`) and our S3 backend (`filepath`).
    """

    def get_object_to_file(self, key: str, filename: str, /) -> Any: ...
    def put_object_from_file(
        self,
        key: str,
        filename: str,
        /,
        headers: dict[str, str] | None = ...,
    ) -> Any: ...
    def head_object(self, key: str, /) -> Any: ...
    def object_exists(self, key: str, /) -> bool: ...


def _use_s3_compat() -> bool:
    """Pick backend based on OSS_S3_COMPAT env var (explicit opt-in only).

    Set OSS_S3_COMPAT=true for local MinIO / LocalStack development. Left unset,
    production keeps the Aliyun OSS wire protocol via oss2.
    """
    return os.environ.get("OSS_S3_COMPAT", "").lower() in ("1", "true", "yes")


class OssClient:
    """Thin typed wrapper around an OSS-or-S3 backend."""

    def __init__(self, bucket: _BucketBackend, *, bucket_name: str) -> None:
        self._bucket = bucket
        self.bucket_name = bucket_name

    @classmethod
    def from_env(cls) -> OssClient:
        if _use_s3_compat():
            return cls._from_env_s3_compat()
        return cls._from_env_oss2()

    @classmethod
    def _from_env_oss2(cls) -> OssClient:
        region = os.environ.get("OSS_REGION", "cn-hangzhou")
        bucket_name = os.environ["OSS_BUCKET"]
        ak = os.environ["OSS_ACCESS_KEY_ID"]
        sk = os.environ["OSS_ACCESS_KEY_SECRET"]
        endpoint = os.environ.get(
            "OSS_ENDPOINT",
            f"https://oss-{region}-internal.aliyuncs.com",
        )
        auth = oss2.Auth(ak, sk)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        return cls(bucket, bucket_name=bucket_name)

    @classmethod
    def _from_env_s3_compat(cls) -> OssClient:
        region = os.environ.get("OSS_REGION", "cn-hangzhou")
        bucket_name = os.environ["OSS_BUCKET"]
        ak = os.environ["OSS_ACCESS_KEY_ID"]
        sk = os.environ["OSS_ACCESS_KEY_SECRET"]
        endpoint = os.environ.get("OSS_ENDPOINT", "http://localhost:9000")
        backend = _S3Backend(
            endpoint=endpoint,
            region=region,
            bucket=bucket_name,
            access_key=ak,
            secret_key=sk,
        )
        return cls(backend, bucket_name=bucket_name)

    def get_to_file(self, *, key: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._bucket.get_object_to_file(key, str(local_path))

    def put_from_file(
        self,
        *,
        key: str,
        local_path: Path,
        if_match_etag: str | None = None,
    ) -> PutResult:
        headers: dict[str, str] | None = None
        if if_match_etag is not None:
            headers = {"If-Match": if_match_etag}
        resp = self._bucket.put_object_from_file(
            key,
            str(local_path),
            headers=headers,
        )
        return PutResult(etag=str(resp.etag))

    def head(self, *, key: str) -> ObjectMeta:
        h = self._bucket.head_object(key)
        return ObjectMeta(etag=str(h.etag), size_bytes=int(h.content_length))

    def exists(self, *, key: str) -> bool:
        return bool(self._bucket.object_exists(key))


# ── S3-compatible backend (boto3) — used only when OSS_S3_COMPAT=true ────────


@dataclass(frozen=True, slots=True)
class _S3Resp:
    etag: str


@dataclass(frozen=True, slots=True)
class _S3Head:
    etag: str
    content_length: int


class _S3Backend:
    """Mimics the oss2.Bucket surface on top of a boto3 S3 client."""

    def __init__(
        self,
        *,
        endpoint: str,
        region: str,
        bucket: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        import boto3

        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self._bucket_name = bucket

    def get_object_to_file(self, key: str, filepath: str) -> None:
        self._client.download_file(self._bucket_name, key, filepath)

    def put_object_from_file(
        self,
        key: str,
        filepath: str,
        headers: dict[str, str] | None = None,
    ) -> _S3Resp:
        extra: dict[str, Any] = {}
        if headers and "If-Match" in headers:
            # boto3 lacks direct If-Match on upload; we do a HEAD precondition first.
            current = self.head_object(key)
            if current.etag != headers["If-Match"]:
                # Mirror oss2's PreconditionFailed shape so classify() maps correctly.
                from botocore.exceptions import ClientError

                raise ClientError(
                    {
                        "Error": {
                            "Code": "PreconditionFailed",
                            "Message": f"If-Match ETag mismatch: got {current.etag}",
                        },
                        "ResponseMetadata": {"HTTPStatusCode": 412},
                    },
                    "PutObject",
                )
        self._client.upload_file(filepath, self._bucket_name, key, ExtraArgs=extra or None)
        head = self._client.head_object(Bucket=self._bucket_name, Key=key)
        return _S3Resp(etag=str(head["ETag"]))

    def head_object(self, key: str) -> _S3Head:
        h = self._client.head_object(Bucket=self._bucket_name, Key=key)
        return _S3Head(etag=str(h["ETag"]), content_length=int(h["ContentLength"]))

    def object_exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self._bucket_name, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise
        return True


def _iter_prefix_keys(client: Any, bucket: str, prefix: str) -> Iterable[str]:  # pragma: no cover
    """Reserved for future use (list_objects support)."""
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents") or []:
            yield obj["Key"]

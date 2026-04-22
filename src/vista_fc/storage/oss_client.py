"""OssClient — thin typed wrapper around oss2.

Responsible for:
- reading OSS config from env (region / endpoint / bucket / ak / sk)
- get_to_file / put_from_file with optional If-Match (ETag lock)
- head / exists
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import oss2


@dataclass(frozen=True, slots=True)
class ObjectMeta:
    etag: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class PutResult:
    etag: str


class OssClient:
    """Thin typed wrapper around oss2.Bucket."""

    def __init__(self, bucket: oss2.Bucket, *, bucket_name: str) -> None:
        self._bucket = bucket
        self.bucket_name = bucket_name

    @classmethod
    def from_env(cls) -> OssClient:
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

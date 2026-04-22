"""OSS URI parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class OssUri:
    bucket: str
    key: str


def parse_oss_uri(uri: str) -> OssUri:
    parsed = urlparse(uri)
    if parsed.scheme != "oss":
        raise ValueError(f"expected oss:// scheme, got {parsed.scheme!r} in {uri!r}")
    if not parsed.netloc:
        raise ValueError(f"missing bucket in {uri!r}")
    key = parsed.path.lstrip("/")
    if not key:
        raise ValueError(f"missing key in {uri!r}")
    return OssUri(bucket=parsed.netloc, key=key)


def format_oss_uri(uri: OssUri) -> str:
    return f"oss://{uri.bucket}/{uri.key}"

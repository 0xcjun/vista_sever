from __future__ import annotations

import pytest

from vista_fc.storage.uri import OssUri, format_oss_uri, parse_oss_uri


def test_parse_valid_uri() -> None:
    u = parse_oss_uri("oss://bucket-x/user_data/u/research/EXP_001/factors.duckdb")
    assert u.bucket == "bucket-x"
    assert u.key == "user_data/u/research/EXP_001/factors.duckdb"


def test_parse_rejects_missing_scheme() -> None:
    with pytest.raises(ValueError):
        parse_oss_uri("s3://bucket/k")


def test_parse_rejects_empty_key() -> None:
    with pytest.raises(ValueError):
        parse_oss_uri("oss://bucket/")


def test_format_roundtrip() -> None:
    u = OssUri(bucket="b", key="a/b/c.txt")
    s = format_oss_uri(u)
    assert s == "oss://b/a/b/c.txt"
    assert parse_oss_uri(s) == u

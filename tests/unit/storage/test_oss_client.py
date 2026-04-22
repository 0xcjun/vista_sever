from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _mk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OSS_REGION", "cn-hangzhou")
    monkeypatch.setenv("OSS_BUCKET", "bucket-x")
    monkeypatch.setenv("OSS_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("OSS_ACCESS_KEY_SECRET", "sk")
    monkeypatch.setenv("OSS_ENDPOINT", "http://localhost:9000")


@patch("vista_fc.storage.oss_client.oss2")
def test_ossclient_reads_config_from_env(mock_oss2: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    _mk_env(monkeypatch)
    mock_bucket = MagicMock()
    mock_oss2.Auth.return_value = "auth"
    mock_oss2.Bucket.return_value = mock_bucket

    from vista_fc.storage.oss_client import OssClient

    c = OssClient.from_env()
    assert c.bucket_name == "bucket-x"

    mock_oss2.Bucket.assert_called_once()
    args = mock_oss2.Bucket.call_args
    assert args.args[0] == "auth"
    assert args.args[1] == "http://localhost:9000"
    assert args.args[2] == "bucket-x"


@patch("vista_fc.storage.oss_client.oss2")
def test_get_to_file_calls_get_object_to_file(
    mock_oss2: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mk_env(monkeypatch)
    mock_bucket = MagicMock()
    mock_oss2.Bucket.return_value = mock_bucket

    from vista_fc.storage.oss_client import OssClient

    c = OssClient.from_env()
    target = tmp_path / "sub" / "out.duckdb"
    c.get_to_file(key="a/b/c.duckdb", local_path=target)

    assert target.parent.exists()  # mkdir -p
    mock_bucket.get_object_to_file.assert_called_once_with("a/b/c.duckdb", str(target))


@patch("vista_fc.storage.oss_client.oss2")
def test_put_from_file_with_etag_precondition(
    mock_oss2: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mk_env(monkeypatch)
    mock_bucket = MagicMock()
    put_resp = MagicMock()
    put_resp.etag = '"abc123"'
    mock_bucket.put_object_from_file.return_value = put_resp
    mock_oss2.Bucket.return_value = mock_bucket

    from vista_fc.storage.oss_client import OssClient

    c = OssClient.from_env()
    src = tmp_path / "data.duckdb"
    src.write_bytes(b"x" * 10)

    res = c.put_from_file(key="a/b/c.duckdb", local_path=src, if_match_etag='"old-etag"')

    mock_bucket.put_object_from_file.assert_called_once()
    call_kwargs = mock_bucket.put_object_from_file.call_args.kwargs
    assert call_kwargs["headers"]["If-Match"] == '"old-etag"'
    assert res.etag == '"abc123"'


@patch("vista_fc.storage.oss_client.oss2")
def test_put_from_file_without_etag(mock_oss2: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _mk_env(monkeypatch)
    mock_bucket = MagicMock()
    put_resp = MagicMock()
    put_resp.etag = '"fresh"'
    mock_bucket.put_object_from_file.return_value = put_resp
    mock_oss2.Bucket.return_value = mock_bucket

    from vista_fc.storage.oss_client import OssClient

    c = OssClient.from_env()
    src = tmp_path / "data.duckdb"
    src.write_bytes(b"y")

    c.put_from_file(key="a/b/c.duckdb", local_path=src)

    call_kwargs = mock_bucket.put_object_from_file.call_args.kwargs
    # headers may be None or missing If-Match
    headers = call_kwargs.get("headers")
    assert headers is None or "If-Match" not in headers


@patch("vista_fc.storage.oss_client.oss2")
def test_head_returns_metadata(mock_oss2: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    _mk_env(monkeypatch)
    mock_bucket = MagicMock()
    head = MagicMock(etag='"e"', content_length=1234)
    mock_bucket.head_object.return_value = head
    mock_oss2.Bucket.return_value = mock_bucket

    from vista_fc.storage.oss_client import OssClient

    c = OssClient.from_env()
    meta = c.head(key="a.txt")
    assert meta.etag == '"e"'
    assert meta.size_bytes == 1234


@patch("vista_fc.storage.oss_client.oss2")
def test_exists_returns_bool(mock_oss2: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    _mk_env(monkeypatch)
    mock_bucket = MagicMock()
    mock_bucket.object_exists.return_value = True
    mock_oss2.Bucket.return_value = mock_bucket

    from vista_fc.storage.oss_client import OssClient

    c = OssClient.from_env()
    assert c.exists(key="x") is True

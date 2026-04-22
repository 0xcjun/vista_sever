from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from vista_fc.contracts.common import ArtifactRef
from vista_fc.services._support import pull_object, push_object


def test_pull_object_calls_workspace(workspace_mock: MagicMock, tmp_path: Path) -> None:
    workspace_mock.pull_to_tmp.return_value = (tmp_path / "factors.duckdb", '"etag1"')
    path, etag = pull_object(
        workspace_mock,
        oss_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
    )
    assert path == tmp_path / "factors.duckdb"
    assert etag == '"etag1"'
    workspace_mock.pull_to_tmp.assert_called_once_with(
        oss_key="user_data/u_abc/research/EXP_001/factors.duckdb",
    )


def test_push_object_returns_artifact_ref(workspace_mock: MagicMock, tmp_path: Path) -> None:
    local = tmp_path / "out.duckdb"
    local.write_bytes(b"x")
    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="duckdb",
        oss_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
        size_bytes=1,
        sha256="aa",
    )
    ref = push_object(
        workspace_mock,
        local_path=local,
        oss_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
        kind="duckdb",
        if_match_etag='"etag1"',
    )
    assert ref.kind == "duckdb"
    call = workspace_mock.push_from_tmp.call_args
    assert call.kwargs["oss_key"] == "user_data/u_abc/research/EXP_001/factors.duckdb"
    assert call.kwargs["if_match_etag"] == '"etag1"'
    assert call.kwargs["kind"] == "duckdb"
    assert call.kwargs["local_path"] == local

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from vista_fc.contracts.common import TenantContext
from vista_fc.storage.oss_client import ObjectMeta, PutResult
from vista_fc.storage.workspace import WorkspaceStorage


def _tenant(kind: str = "research", wid: str = "EXP_001") -> TenantContext:
    return TenantContext(
        user_hash="u_abc",
        workspace_id=wid,
        workspace_kind=kind,  # type: ignore[arg-type]
        run_id="r",
        requested_at=datetime.now(UTC),
    )


def test_factors_db_key_research() -> None:
    t = _tenant()
    ws = WorkspaceStorage(oss=MagicMock(), tenant=t, tmp_root=Path("/tmp/fake"))
    assert ws.factors_db_key() == "user_data/u_abc/research/EXP_001/factors.duckdb"


def test_factor_routes_toml_key_research() -> None:
    t = _tenant()
    ws = WorkspaceStorage(oss=MagicMock(), tenant=t, tmp_root=Path("/tmp/fake"))
    assert ws.factor_routes_toml_key() == "user_data/u_abc/research/EXP_001/factor_routes.toml"


def test_strategies_db_key_realtime() -> None:
    t = _tenant(kind="realtime", wid="FTS_001")
    ws = WorkspaceStorage(oss=MagicMock(), tenant=t, tmp_root=Path("/tmp/fake"))
    assert ws.strategies_db_key() == "user_data/u_abc/realtime/strategies.duckdb"


def test_pull_to_tmp_downloads_and_returns_path(tmp_path: Path) -> None:
    oss = MagicMock()

    def _fake_get(*, key: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(b"duck")

    oss.get_to_file.side_effect = _fake_get
    oss.head.return_value = ObjectMeta(etag='"e1"', size_bytes=4)

    ws = WorkspaceStorage(oss=oss, tenant=_tenant(), tmp_root=tmp_path)
    local, etag = ws.pull_to_tmp(oss_key="user_data/u_abc/research/EXP_001/factors.duckdb")

    assert local.exists()
    assert local.read_bytes() == b"duck"
    assert etag == '"e1"'


def test_push_from_tmp_builds_artifact(tmp_path: Path) -> None:
    src = tmp_path / "factors.duckdb"
    src.write_bytes(b"abc")

    oss = MagicMock()
    oss.bucket_name = "vista-fc-test"
    oss.put_from_file.return_value = PutResult(etag='"new-etag"')

    ws = WorkspaceStorage(oss=oss, tenant=_tenant(), tmp_root=tmp_path)
    artifact = ws.push_from_tmp(
        local_path=src,
        oss_key="user_data/u_abc/research/EXP_001/factors.duckdb",
        kind="duckdb",
        if_match_etag='"old-etag"',
    )
    assert artifact.oss_uri == ("oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb")
    assert artifact.kind == "duckdb"
    assert artifact.size_bytes == 3
    assert artifact.sha256 == hashlib.sha256(b"abc").hexdigest()

    oss.put_from_file.assert_called_once()
    kwargs = oss.put_from_file.call_args.kwargs
    assert kwargs["if_match_etag"] == '"old-etag"'

"""WorkspaceStorage — primary storage abstraction used by services.

Given a TenantContext, knows how to:
- compute canonical OSS keys for factors.duckdb / factor_routes.toml /
  strategies.duckdb / FTS_*/*.toml
- pull_to_tmp: download any object to a tmp_root subdir, return local Path + ETag
- push_from_tmp: upload a local Path, build an ArtifactRef (kind/size/sha256),
  optionally with If-Match ETag for optimistic concurrency
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from vista_fc.contracts.common import ArtifactRef, TenantContext
from vista_fc.storage.oss_client import OssClient

ArtifactKind = Literal[
    "duckdb",
    "toml",
    "parquet",
    "feather",
    "report_json",
    "model",
    "log",
]


def _sha256_file(path: Path, *, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


@dataclass(slots=True)
class WorkspaceStorage:
    oss: OssClient
    tenant: TenantContext
    tmp_root: Path

    def _user_root(self) -> str:
        return f"user_data/{self.tenant.user_hash}"

    def factors_db_key(self) -> str:
        assert self.tenant.workspace_kind == "research"
        return f"{self._user_root()}/research/{self.tenant.workspace_id}/factors.duckdb"

    def factor_routes_toml_key(self) -> str:
        assert self.tenant.workspace_kind == "research"
        return f"{self._user_root()}/research/{self.tenant.workspace_id}/factor_routes.toml"

    def strategies_db_key(self) -> str:
        assert self.tenant.workspace_kind == "realtime"
        return f"{self._user_root()}/realtime/strategies.duckdb"

    def fts_toml_key(self, strategy_basename: str) -> str:
        assert self.tenant.workspace_kind == "realtime"
        return f"{self._user_root()}/realtime/{self.tenant.workspace_id}/{strategy_basename}"

    def pull_to_tmp(self, *, oss_key: str) -> tuple[Path, str]:
        local = self.tmp_root / self.tenant.workspace_id / Path(oss_key).name
        local.parent.mkdir(parents=True, exist_ok=True)
        self.oss.get_to_file(key=oss_key, local_path=local)
        meta = self.oss.head(key=oss_key)
        return local, meta.etag

    def push_from_tmp(
        self,
        *,
        local_path: Path,
        oss_key: str,
        kind: ArtifactKind,
        if_match_etag: str | None = None,
    ) -> ArtifactRef:
        size = local_path.stat().st_size
        sha = _sha256_file(local_path)
        self.oss.put_from_file(
            key=oss_key,
            local_path=local_path,
            if_match_etag=if_match_etag,
        )
        return ArtifactRef(
            kind=kind,
            oss_uri=f"oss://{self.oss.bucket_name}/{oss_key}",
            size_bytes=size,
            sha256=sha,
        )

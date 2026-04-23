"""Shared helpers used by every service.

Bridge oss_uri ↔ oss_key, preserving ETag hand-off for optimistic locking.
"""

from __future__ import annotations

import os
from pathlib import Path

from vista_fc.contracts.common import ArtifactRef
from vista_fc.storage.uri import parse_oss_uri
from vista_fc.storage.workspace import ArtifactKind, WorkspaceStorage


def pull_object(workspace: WorkspaceStorage, *, oss_uri: str) -> tuple[Path, str]:
    key = parse_oss_uri(oss_uri).key
    return workspace.pull_to_tmp(oss_key=key)


def push_object(
    workspace: WorkspaceStorage,
    *,
    local_path: Path,
    oss_uri: str,
    kind: ArtifactKind,
    if_match_etag: str | None = None,
) -> ArtifactRef:
    key = parse_oss_uri(oss_uri).key
    return workspace.push_from_tmp(
        local_path=local_path,
        oss_key=key,
        kind=kind,
        if_match_etag=if_match_etag,
    )


def ensure_research_data(workspace: WorkspaceStorage, *, oss_uri: str | None) -> None:
    """把研究数据 duckdb 从 OSS 按需拉到 VISTA_RESEARCH_PATH，并把路径写回 env。

    生产由 NAS 预置；本地/按需调用时传 uri。已存在的文件不重复下载。
    空 uri 直接跳过（不改 env），让 vista 走默认 /root/.vista/research 或现有 env。
    """
    if not oss_uri:
        return
    research_dir = Path(os.environ.get("VISTA_RESEARCH_PATH") or "/mnt/vista-cache/research")
    research_dir.mkdir(parents=True, exist_ok=True)
    basename = Path(parse_oss_uri(oss_uri).key).name
    target = research_dir / basename
    if not target.exists():
        local_pull, _ = pull_object(workspace, oss_uri=oss_uri)
        local_pull.replace(target)
    os.environ["VISTA_RESEARCH_PATH"] = str(research_dir)

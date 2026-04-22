"""Shared helpers used by every service.

Bridge oss_uri ↔ oss_key, preserving ETag hand-off for optimistic locking.
"""

from __future__ import annotations

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

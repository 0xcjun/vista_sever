"""Shared fixtures for service-level unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vista_fc.contracts.common import TenantContext


@pytest.fixture
def tenant_research() -> TenantContext:
    return TenantContext(
        user_hash="u_abc",
        workspace_id="EXP_001",
        workspace_kind="research",
        run_id="run-test",
        requested_at=datetime(2026, 4, 22, 10, 0, tzinfo=UTC),
    )


@pytest.fixture
def tenant_realtime() -> TenantContext:
    return TenantContext(
        user_hash="u_abc",
        workspace_id="FTS_001",
        workspace_kind="realtime",
        run_id="run-rt",
        requested_at=datetime(2026, 4, 22, 10, 0, tzinfo=UTC),
    )


@pytest.fixture
def workspace_mock(tmp_path: Path, tenant_research: TenantContext) -> MagicMock:
    """A MagicMock standing in for WorkspaceStorage. `.oss.bucket_name` is set
    so push_from_tmp can build valid oss:// URIs in assertions."""
    ws = MagicMock()
    ws.tenant = tenant_research
    ws.tmp_root = tmp_path
    ws.oss.bucket_name = "vista-fc-test"
    return ws

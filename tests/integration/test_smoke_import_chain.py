"""Pure-python service chain smoke (no docker, no s CLI).

Verifies contracts+storage+services wire up together against mocked vista,
without requiring the full container stack. Runs in plain unit pytest.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from vista_fc.contracts.common import ArtifactRef, TenantContext
from vista_fc.contracts.factor_detect import FactorDetectInput
from vista_fc.services.factor_detect import factor_detect_service


def _tenant() -> TenantContext:
    return TenantContext(
        user_hash="u_smoke",
        workspace_id="EXP_SMOKE",
        workspace_kind="research",
        run_id="smoke-run",
        requested_at=datetime.now(UTC),
    )


def test_detect_chain_with_fully_mocked_stack(tmp_path: Path) -> None:
    """No minio, no docker. Everything below the service boundary is mocked."""

    ws = MagicMock()
    ws.tmp_root = tmp_path
    ws.oss.bucket_name = "vista-fc-smoke"

    db_local = tmp_path / "factors.duckdb"
    db_local.write_bytes(b"x")
    ws.pull_to_tmp.return_value = (db_local, '"e"')

    ws.push_from_tmp.return_value = ArtifactRef(
        kind="report_json",
        oss_uri="oss://vista-fc-smoke/x/report.json",
        size_bytes=10,
        sha256=None,
    )

    mock_report = MagicMock()
    mock_report.model_dump.return_value = {
        "total_factors": 10,
        "passed": 9,
        "failed": 1,
    }

    with patch("vista_fc.services.factor_detect._vista_factor_detect") as m:
        m.return_value = mock_report
        out = factor_detect_service(
            tenant=_tenant(),
            payload=FactorDetectInput(factors_db_uri="oss://vista-fc-smoke/x/factors.duckdb"),
            workspace=ws,
        )

    assert out.total_factors == 10
    assert out.passed == 9
    assert out.failed == 1
    assert out.report_artifact.kind == "report_json"

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_detect import FactorDetectInput
from vista_fc.services.factor_detect import factor_detect_service


@pytest.fixture
def patched_vista_detect():
    with patch("vista_fc.services.factor_detect._vista_factor_detect") as m:
        yield m


def test_detect_happy_path(
    workspace_mock: MagicMock,
    tenant_research,
    patched_vista_detect: MagicMock,
    tmp_path: Path,
) -> None:
    db_local = tmp_path / "factors.duckdb"
    db_local.write_bytes(b"duck")
    workspace_mock.pull_to_tmp.return_value = (db_local, '"etag-1"')

    # Match vista's FactorDetectBatchReport field names exactly — this is the
    # real contract the service parses. `failed + errored` sum maps to our `failed`.
    mock_report = MagicMock()
    mock_report.model_dump.return_value = {
        "total": 100,
        "pending": 100,
        "skipped_unsupported": 0,
        "passed": 95,
        "failed": 4,
        "errored": 1,
        "failure_breakdown": {},
        "elapsed_seconds": 1.23,
    }
    patched_vista_detect.return_value = mock_report

    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="report_json",
        oss_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/reports/detect_run-test.json",
        size_bytes=123,
        sha256="ab",
    )

    payload = FactorDetectInput(
        factors_db_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
        max_workers=2,
        timeout=30,
    )
    out = factor_detect_service(
        tenant=tenant_research,
        payload=payload,
        workspace=workspace_mock,
    )

    assert out.total_factors == 100
    assert out.passed == 95
    assert out.failed == 5
    assert out.report_artifact.kind == "report_json"

    patched_vista_detect.assert_called_once()
    kwargs = patched_vista_detect.call_args.kwargs
    assert kwargs["db_path"] == str(db_local)
    assert kwargs["max_workers"] == 2
    assert kwargs["timeout"] == 30

    # push_from_tmp called twice: once for report.json, once to write back updated duckdb
    push_kinds = [c.kwargs["kind"] for c in workspace_mock.push_from_tmp.call_args_list]
    push_keys = [c.kwargs["oss_key"] for c in workspace_mock.push_from_tmp.call_args_list]
    assert "report_json" in push_kinds
    assert "duckdb" in push_kinds
    assert any("reports/detect_" in k for k in push_keys)
    assert any(k.endswith("factors.duckdb") for k in push_keys)


def test_detect_propagates_etag_for_duckdb_writeback(
    workspace_mock: MagicMock,
    tenant_research,
    patched_vista_detect: MagicMock,
    tmp_path: Path,
) -> None:
    """Lost-Update prevention: the ETag returned from pull_to_tmp must be passed
    as if_match_etag on the duckdb writeback so OSS rejects conflicting writers."""
    db_local = tmp_path / "factors.duckdb"
    db_local.write_bytes(b"x")
    workspace_mock.pull_to_tmp.return_value = (db_local, '"etag-pull"')

    mock_report = MagicMock()
    mock_report.model_dump.return_value = {
        "total": 1,
        "passed": 1,
        "failed": 0,
        "errored": 0,
    }
    patched_vista_detect.return_value = mock_report

    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="report_json",
        oss_uri="oss://vista-fc-test/x.json",
        size_bytes=1,
        sha256=None,
    )

    factor_detect_service(
        tenant=tenant_research,
        payload=FactorDetectInput(
            factors_db_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
        ),
        workspace=workspace_mock,
    )

    duckdb_calls = [c for c in workspace_mock.push_from_tmp.call_args_list if c.kwargs.get("kind") == "duckdb"]
    assert len(duckdb_calls) == 1, "expected exactly one duckdb writeback"
    assert (
        duckdb_calls[0].kwargs.get("if_match_etag") == '"etag-pull"'
    ), "duckdb writeback must carry pull ETag as If-Match to prevent Lost-Update"


def test_detect_raises_on_vista_failure(
    workspace_mock: MagicMock,
    tenant_research,
    patched_vista_detect: MagicMock,
    tmp_path: Path,
) -> None:
    db_local = tmp_path / "factors.duckdb"
    db_local.write_bytes(b"x")
    workspace_mock.pull_to_tmp.return_value = (db_local, '"e"')
    patched_vista_detect.side_effect = RuntimeError("boom")

    payload = FactorDetectInput(
        factors_db_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
    )
    with pytest.raises(RuntimeError):
        factor_detect_service(
            tenant=tenant_research,
            payload=payload,
            workspace=workspace_mock,
        )

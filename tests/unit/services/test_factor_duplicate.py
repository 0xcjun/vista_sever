from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_duplicate import FactorDuplicateInput
from vista_fc.services.factor_duplicate import factor_duplicate_service


@pytest.fixture
def patched_dup():
    with (
        patch("vista_fc.services.factor_duplicate._vista_factor_duplicate") as dup,
        patch("vista_fc.services.factor_duplicate._get_problem") as gp,
    ):
        gp.side_effect = lambda code: {"code": code}
        yield dup


def test_happy_path(
    workspace_mock: MagicMock,
    tenant_research,
    patched_dup: MagicMock,
    tmp_path: Path,
) -> None:
    db_local = tmp_path / "factors.duckdb"
    db_local.write_bytes(b"x")
    workspace_mock.pull_to_tmp.return_value = (db_local, '"e"')

    # vista FactorDuplicateReport 的真实字段
    mock_report = MagicMock()
    mock_report.model_dump.return_value = {
        "problem_stats": [
            {"problem_code": "P1", "input": 50, "survived": 40, "rejected": 10},
        ],
        "total_rejected": 10,
        "elapsed_seconds": 1.23,
    }
    patched_dup.return_value = mock_report

    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="report_json",
        oss_uri="oss://vista-fc-test/duplicate_run-test.json",
        size_bytes=1,
        sha256=None,
    )

    out = factor_duplicate_service(
        tenant=tenant_research,
        payload=FactorDuplicateInput(
            factors_db_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
            route_codes=["R1", "R2"],
            problem_codes=["P1"],
        ),
        workspace=workspace_mock,
    )
    assert out.total_input == 50
    assert out.total_rejected == 10
    assert out.total_survived == 40
    assert out.elapsed_seconds == 1.23


def test_duplicate_propagates_etag_for_duckdb_writeback(
    workspace_mock: MagicMock,
    tenant_research,
    patched_dup: MagicMock,
    tmp_path: Path,
) -> None:
    """Lost-Update prevention on duckdb writeback."""
    db_local = tmp_path / "factors.duckdb"
    db_local.write_bytes(b"x")
    workspace_mock.pull_to_tmp.return_value = (db_local, '"etag-dup"')

    mock_report = MagicMock()
    mock_report.model_dump.return_value = {
        "problem_stats": [],
        "total_rejected": 0,
        "elapsed_seconds": 0.0,
    }
    patched_dup.return_value = mock_report

    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="report_json",
        oss_uri="oss://vista-fc-test/x.json",
        size_bytes=1,
        sha256=None,
    )

    factor_duplicate_service(
        tenant=tenant_research,
        payload=FactorDuplicateInput(
            factors_db_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
            route_codes=["R1"],
            problem_codes=["P1"],
        ),
        workspace=workspace_mock,
    )
    duckdb_calls = [c for c in workspace_mock.push_from_tmp.call_args_list if c.kwargs.get("kind") == "duckdb"]
    assert len(duckdb_calls) == 1
    assert duckdb_calls[0].kwargs.get("if_match_etag") == '"etag-dup"'

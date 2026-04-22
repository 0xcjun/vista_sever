from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_evaluate import FactorEvaluateInput
from vista_fc.services.factor_evaluate import factor_evaluate_service


@pytest.fixture
def patched_eval():
    with (
        patch("vista_fc.services.factor_evaluate._vista_factor_evaluate") as e,
        patch("vista_fc.services.factor_evaluate._get_problem") as gp,
    ):
        gp.side_effect = lambda code: {"code": code}
        yield e


def test_happy_path(
    workspace_mock: MagicMock,
    tenant_research,
    patched_eval: MagicMock,
    tmp_path: Path,
) -> None:
    db_local = tmp_path / "factors.duckdb"
    db_local.write_bytes(b"x")
    workspace_mock.pull_to_tmp.return_value = (db_local, '"e"')

    mock_report = MagicMock()
    mock_report.model_dump.return_value = {
        "total_evaluations": 200,
        "succeeded": 180,
        "failed": 20,
    }
    patched_eval.return_value = mock_report

    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="report_json",
        oss_uri="oss://vista-fc-test/evaluate_run-test.json",
        size_bytes=1,
        sha256=None,
    )

    out = factor_evaluate_service(
        tenant=tenant_research,
        payload=FactorEvaluateInput(
            factors_db_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
            route_codes=["R1"],
            problem_codes=["P1"],
            models=["MA001"],
        ),
        workspace=workspace_mock,
    )
    assert out.total_evaluations == 200
    assert out.succeeded == 180
    assert out.failed == 20

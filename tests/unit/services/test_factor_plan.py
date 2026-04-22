from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_plan import FactorPlanInput
from vista_fc.services.factor_plan import factor_plan_service


@pytest.fixture
def patched_plan():
    with patch("vista_fc.services.factor_plan._plan_factor_routes") as m:
        yield m


def test_plan_happy_path(
    workspace_mock: MagicMock,
    tenant_research,
    patched_plan: MagicMock,
    tmp_path: Path,
) -> None:
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {
        "routes": [
            {"code": "R001", "name": "动量", "compute_engine": "czsc"},
        ],
        "toml_text": '[[routes]]\ncode = "R001"\n',
    }
    patched_plan.return_value = mock_result

    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="toml",
        oss_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factor_routes.toml",
        size_bytes=30,
        sha256="ab",
    )

    out = factor_plan_service(
        tenant=tenant_research,
        payload=FactorPlanInput(user_input="动量反转"),
        workspace=workspace_mock,
    )
    assert len(out.routes) == 1
    assert out.routes[0].code == "R001"
    assert out.routes_toml_artifact.kind == "toml"

    patched_plan.assert_called_once()
    kwargs = patched_plan.call_args.kwargs
    assert kwargs["user_input"] == "动量反转"

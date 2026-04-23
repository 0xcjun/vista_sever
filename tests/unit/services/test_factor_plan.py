from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_plan import FactorPlanInput
from vista_fc.services.factor_plan import factor_plan_service


@pytest.fixture
def patched_agent():
    with patch("vista_fc.services.factor_plan.FactorPlanAgent") as cls:
        instance = MagicMock()
        cls.return_value = instance
        yield instance


def test_plan_happy_path(
    workspace_mock: MagicMock,
    tenant_research,
    patched_agent: MagicMock,
    tmp_path: Path,
) -> None:
    route = MagicMock()
    route.code = "R001"
    route.name = "动量"
    route.compute_engine.value = "TimeSeriesEngine"
    route.description = "desc"

    mock_result = MagicMock()
    mock_result.routes = [route]

    # agent.plan 是 async；asyncio.run 会 await 它，用真正的 coroutine
    async def _fake_plan(_user_input):
        return mock_result

    patched_agent.plan.side_effect = _fake_plan

    # save_toml 要真的把文件创出来，这样 push_object 能 stat 到
    def _save_toml(_res, path):
        Path(path).write_text('[[routes]]\ncode = "R001"\n', encoding="utf-8")

    patched_agent.save_toml.side_effect = _save_toml

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
    assert out.routes[0].compute_engine == "TimeSeriesEngine"
    assert out.routes_toml_artifact.kind == "toml"

    patched_agent.save_toml.assert_called_once()

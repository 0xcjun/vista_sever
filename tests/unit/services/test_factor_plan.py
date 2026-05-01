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


def test_plan_passes_explicit_llm_params(
    workspace_mock: MagicMock,
    tenant_research,
    tmp_path: Path,
) -> None:
    """payload 里的显式 anthropic_* 应原样透传给 FactorPlanAgent 构造函数,
    其中 SecretStr 必须 .get_secret_value() 后再传(明文给 vista)。"""
    route = MagicMock()
    route.code = "R001"
    route.name = "x"
    route.compute_engine.value = "T"
    route.description = ""
    mock_result = MagicMock()
    mock_result.routes = [route]

    async def _fake_plan(_):
        return mock_result

    def _save_toml(_res, path):
        Path(path).write_text('[[routes]]\ncode = "R001"\n', encoding="utf-8")

    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="toml",
        oss_uri="oss://b/x.toml",
        size_bytes=1,
        sha256="a",
    )

    with patch("vista_fc.services.factor_plan.FactorPlanAgent") as MockAgent:
        instance = MockAgent.return_value
        instance.plan.side_effect = _fake_plan
        instance.save_toml.side_effect = _save_toml

        factor_plan_service(
            tenant=tenant_research,
            payload=FactorPlanInput(
                user_input="X",
                anthropic_api_key="sk-explicit",  # pragma: allowlist secret
                anthropic_base_url="https://gateway.example/v1",
                anthropic_model="explicit-model",
            ),
            workspace=workspace_mock,
        )

        kw = MockAgent.call_args.kwargs
        assert kw["anthropic_api_key"] == "sk-explicit"  # pragma: allowlist secret
        assert kw["anthropic_base_url"] == "https://gateway.example/v1"
        assert kw["anthropic_model"] == "explicit-model"


def test_plan_defaults_to_none_when_unset(
    workspace_mock: MagicMock,
    tenant_research,
    tmp_path: Path,
) -> None:
    """payload 不传显式参数时,service 应该把 None 透传,让 vista 自己回退 env。"""
    route = MagicMock()
    route.code = "R"
    route.name = "x"
    route.compute_engine.value = "T"
    route.description = ""
    mock_result = MagicMock()
    mock_result.routes = [route]

    async def _fake_plan(_):
        return mock_result

    def _save_toml(_res, path):
        Path(path).write_text('[[routes]]\ncode = "R"\n', encoding="utf-8")

    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="toml", oss_uri="oss://b/x.toml", size_bytes=1, sha256="a"
    )

    with patch("vista_fc.services.factor_plan.FactorPlanAgent") as MockAgent:
        instance = MockAgent.return_value
        instance.plan.side_effect = _fake_plan
        instance.save_toml.side_effect = _save_toml

        factor_plan_service(
            tenant=tenant_research,
            payload=FactorPlanInput(user_input="X"),
            workspace=workspace_mock,
        )
        kw = MockAgent.call_args.kwargs
        assert kw["anthropic_api_key"] is None
        assert kw["anthropic_base_url"] is None
        assert kw["anthropic_model"] is None

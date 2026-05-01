from __future__ import annotations

import pytest
from pydantic import ValidationError

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_plan import (
    FactorPlanInput,
    FactorPlanOutput,
    FactorRouteSummary,
)


def test_input_requires_user_input() -> None:
    m = FactorPlanInput(user_input="动量反转")
    assert m.user_input == "动量反转"
    assert m.interactive is False
    assert m.anthropic_api_key is None
    assert m.anthropic_base_url is None
    assert m.anthropic_model is None


def test_input_rejects_empty_user_input() -> None:
    with pytest.raises(ValidationError):
        FactorPlanInput(user_input="")


def test_input_anthropic_api_key_is_secret() -> None:
    """SecretStr 字段在序列化与 repr 中不应泄漏明文。"""
    m = FactorPlanInput(
        user_input="X",
        anthropic_api_key="sk-explicit-secret",  # pragma: allowlist secret
        anthropic_base_url="https://gateway.example/v1",
        anthropic_model="explicit-model",
    )
    assert m.anthropic_api_key is not None
    assert m.anthropic_api_key.get_secret_value() == "sk-explicit-secret"
    # repr / str / json dump 都应屏蔽明文
    assert "sk-explicit-secret" not in repr(m)
    assert "sk-explicit-secret" not in m.model_dump_json()


def test_input_rejects_extra_fields() -> None:
    """旧字段名 model 已废弃,extra=forbid 应明确拒绝。"""
    with pytest.raises(ValidationError):
        FactorPlanInput(user_input="X", model="some-model")  # type: ignore[call-arg]


def test_output_carries_routes_and_toml_artifact() -> None:
    out = FactorPlanOutput(
        routes=[
            FactorRouteSummary(code="R001", name="动量组", compute_engine="czsc"),
        ],
        routes_toml_artifact=ArtifactRef(
            kind="toml",
            oss_uri="oss://b/user_data/u/research/EXP_001/factor_routes.toml",
            size_bytes=1024,
        ),
    )
    assert len(out.routes) == 1
    assert out.routes_toml_artifact.kind == "toml"

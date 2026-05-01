from __future__ import annotations

import pytest
from pydantic import ValidationError

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_builder import (
    FactorBuilderInput,
    FactorBuilderOutput,
    RouteBuildStat,
)


def test_input_accepts_routes_toml_uri() -> None:
    m = FactorBuilderInput(
        routes_toml_uri="oss://b/user_data/u/research/EXP_001/factor_routes.toml",
        factor_numbers=30,
    )
    assert m.batch_size == 5
    assert m.max_workers == 1
    assert m.anthropic_api_key is None
    assert m.anthropic_base_url is None
    assert m.anthropic_model is None


def test_input_requires_either_uri_or_code() -> None:
    with pytest.raises(ValidationError):
        FactorBuilderInput()


def test_input_anthropic_api_key_is_secret() -> None:
    m = FactorBuilderInput(
        routes_toml_uri="oss://b/r.toml",
        anthropic_api_key="sk-explicit-secret",  # pragma: allowlist secret
        anthropic_base_url="https://gateway.example/v1",
        anthropic_model="explicit-model",
    )
    assert m.anthropic_api_key is not None
    assert m.anthropic_api_key.get_secret_value() == "sk-explicit-secret"
    assert "sk-explicit-secret" not in repr(m)
    assert "sk-explicit-secret" not in m.model_dump_json()


def test_input_rejects_extra_fields() -> None:
    """旧字段名 model 已废弃,extra=forbid 应明确拒绝。"""
    with pytest.raises(ValidationError):
        FactorBuilderInput(routes_toml_uri="oss://b/r.toml", model="some-model")  # type: ignore[call-arg]


def test_output_captures_totals_and_duckdb_artifact() -> None:
    out = FactorBuilderOutput(
        total_factors=42,
        per_route=[RouteBuildStat(route_code="R001", factor_count=42)],
        factors_db_artifact=ArtifactRef(
            kind="duckdb",
            oss_uri="oss://b/user_data/u/research/EXP_001/factors.duckdb",
            size_bytes=1_234_567,
        ),
    )
    assert out.total_factors == 42

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


def test_input_requires_either_uri_or_code() -> None:
    with pytest.raises(ValidationError):
        FactorBuilderInput()


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

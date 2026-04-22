from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_builder import FactorBuilderInput
from vista_fc.services.factor_builder import factor_builder_service


@pytest.fixture
def patched_builder():
    with patch("vista_fc.services.factor_builder._FactorBuilder") as m:
        yield m


@pytest.fixture
def patched_load_toml():
    with patch("vista_fc.services.factor_builder._load_routes_from_toml") as m:
        yield m


def test_build_from_toml_uri(
    workspace_mock: MagicMock,
    tenant_research,
    patched_builder: MagicMock,
    patched_load_toml: MagicMock,
    tmp_path: Path,
) -> None:
    toml_local = tmp_path / "factor_routes.toml"
    toml_local.write_text('[[routes]]\ncode = "R001"\n')
    workspace_mock.pull_to_tmp.return_value = (toml_local, '"toml-etag"')
    patched_load_toml.return_value = [{"code": "R001", "name": "动量", "compute_engine": "czsc"}]

    fake_factor = MagicMock()
    fake_factor.model_dump.return_value = {"name": "f1"}
    builder_instance = MagicMock()
    builder_instance.run.return_value = [fake_factor]
    patched_builder.return_value = builder_instance

    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="duckdb",
        oss_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
        size_bytes=10,
        sha256="a",
    )

    out = factor_builder_service(
        tenant=tenant_research,
        payload=FactorBuilderInput(
            routes_toml_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factor_routes.toml",
            factor_numbers=5,
            batch_size=2,
        ),
        workspace=workspace_mock,
    )

    assert out.total_factors == 1
    assert out.per_route[0].route_code == "R001"
    assert out.factors_db_artifact.kind == "duckdb"

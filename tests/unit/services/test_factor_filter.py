from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.factor_filter import FactorFilterInput
from vista_fc.services.factor_filter import factor_filter_service


@pytest.fixture
def patched_filter():
    with (
        patch("vista_fc.services.factor_filter._vista_factor_filter") as f,
        patch("vista_fc.services.factor_filter._get_manager") as m,
    ):
        yield f, m


def test_filter_writes_multiple_tomls(
    workspace_mock: MagicMock,
    tenant_research,
    patched_filter,
    tmp_path: Path,
) -> None:
    f, m = patched_filter
    db_local = tmp_path / "factors.duckdb"
    db_local.write_bytes(b"x")
    workspace_mock.pull_to_tmp.return_value = (db_local, '"e"')

    def _simulate_filter(*, output_dir: str, **_kwargs):
        out = Path(output_dir) / "filter_results"
        out.mkdir(parents=True, exist_ok=True)
        p1 = out / "strat_a.toml"
        p2 = out / "strat_b.toml"
        p1.write_text('name = "a"')
        p2.write_text('name = "b"')
        return [p1, p2]

    f.side_effect = _simulate_filter
    m.return_value.__enter__.return_value = MagicMock()

    workspace_mock.push_from_tmp.side_effect = [
        ArtifactRef(
            kind="toml",
            oss_uri="oss://vista-fc-test/user_data/u_abc/realtime/FTS_strat_a/strat_a.toml",
            size_bytes=10,
            sha256=None,
        ),
        ArtifactRef(
            kind="toml",
            oss_uri="oss://vista-fc-test/user_data/u_abc/realtime/FTS_strat_b/strat_b.toml",
            size_bytes=10,
            sha256=None,
        ),
    ]

    out = factor_filter_service(
        tenant=tenant_research,
        payload=FactorFilterInput(
            factors_db_uri="oss://vista-fc-test/user_data/u_abc/research/EXP_001/factors.duckdb",
        ),
        workspace=workspace_mock,
    )
    assert out.toml_count == 2
    assert len(out.toml_artifacts) == 2

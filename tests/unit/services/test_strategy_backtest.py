from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.strategy_backtest import StrategyBacktestInput
from vista_fc.services.strategy_backtest import strategy_backtest_service


@pytest.fixture
def patched_backtest():
    with patch("vista_fc.services.strategy_backtest._run_strategy_backtest") as m:
        yield m


def test_happy_path(
    workspace_mock: MagicMock,
    tenant_research,
    patched_backtest: MagicMock,
    tmp_path: Path,
) -> None:
    strat_toml = tmp_path / "strat.toml"
    strat_toml.write_text('name = "s1"')
    workspace_mock.pull_to_tmp.return_value = (strat_toml, '"e"')

    mode_dir = tmp_path / "bt"
    mode_dir.mkdir()
    (mode_dir / "equity.parquet").write_bytes(b"eq")
    (mode_dir / "weights.parquet").write_bytes(b"w")

    patched_backtest.return_value = SimpleNamespace(
        strategy="s1",
        mode="research",
        output_dir=tmp_path,
        mode_dir=mode_dir,
        toml_sha256="sha",
        elapsed_s=3.14,
        artifacts={
            "equity": str(mode_dir / "equity.parquet"),
            "weights": str(mode_dir / "weights.parquet"),
        },
    )

    def _push(**kwargs):
        local_path = kwargs["local_path"]
        return ArtifactRef(
            kind="parquet",
            oss_uri=f"oss://vista-fc-test/backtest/{local_path.name}",
            size_bytes=local_path.stat().st_size,
            sha256=None,
        )

    workspace_mock.push_from_tmp.side_effect = _push

    out = strategy_backtest_service(
        tenant=tenant_research,
        payload=StrategyBacktestInput(
            strategy_toml_uri="oss://vista-fc-test/s.toml",
            mode="research",
        ),
        workspace=workspace_mock,
    )
    assert out.strategy == "s1"
    assert "equity" in out.artifacts
    assert "weights" in out.artifacts

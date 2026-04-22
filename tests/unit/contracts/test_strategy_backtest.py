from __future__ import annotations

import pytest
from pydantic import ValidationError

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.strategy_backtest import (
    StrategyBacktestInput,
    StrategyBacktestOutput,
)


def test_input_mode_research_or_realtime() -> None:
    m = StrategyBacktestInput(
        strategy_toml_uri="oss://b/strat.toml",
        mode="research",
    )
    assert m.data_mode == "total"

    with pytest.raises(ValidationError):
        StrategyBacktestInput(
            strategy_toml_uri="oss://b/strat.toml",
            mode="paper",  # type: ignore[arg-type]
        )


def test_output_has_artifacts_dict() -> None:
    out = StrategyBacktestOutput(
        strategy="my-strat",
        elapsed_s=12.3,
        artifacts={
            "equity": ArtifactRef(kind="parquet", oss_uri="oss://b/eq.parquet", size_bytes=1000),
            "weights": ArtifactRef(kind="parquet", oss_uri="oss://b/w.parquet", size_bytes=2000),
        },
    )
    assert "equity" in out.artifacts

from __future__ import annotations

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.vista_realtime import (
    SummaryData,
    TimingEntry,
    VistaRealtimeInput,
    VistaRealtimeOutput,
)


def test_input_defaults() -> None:
    m = VistaRealtimeInput(strategy_toml_uri="oss://b/fts/strat.toml")
    assert m.strategy_toml_uri == "oss://b/fts/strat.toml"


def test_output_carries_summary_and_timing() -> None:
    out = VistaRealtimeOutput(
        summary=SummaryData(
            strategy="s1",
            latest_dt="2026-04-22T10:00:00",
            symbols=["SFIF9001.CFE", "SFIC9001.CFE"],
            factor_count=10,
            success_factor_count=10,
            failed_factor_count=0,
        ),
        latest_dt="2026-04-22T10:00:00",
        weights_artifact=ArtifactRef(
            kind="parquet",
            oss_uri="oss://b/w.parquet",
            size_bytes=2_000,
        ),
        timing=[TimingEntry(stage="pull_klines", elapsed_seconds=1.5)],
    )
    assert out.summary.success_factor_count == 10

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from vista_fc.contracts.common import ArtifactRef
from vista_fc.contracts.vista_realtime import VistaRealtimeInput
from vista_fc.services.vista_realtime import vista_realtime_service


@pytest.fixture
def patched_rt():
    with (
        patch("vista_fc.services.vista_realtime._RealtimeWorkflow") as wf,
        patch("vista_fc.services.vista_realtime._load_realtime_config") as lc,
    ):
        yield wf, lc


def test_happy_path(
    workspace_mock: MagicMock,
    tenant_realtime,
    patched_rt,
    tmp_path: Path,
) -> None:
    wf, lc = patched_rt
    toml_local = tmp_path / "strat.toml"
    toml_local.write_text('name = "s1"')
    workspace_mock.pull_to_tmp.return_value = (toml_local, '"e"')

    cfg = MagicMock()
    cfg.strategy = "s1"
    lc.return_value = cfg

    instance = MagicMock()
    instance.update.return_value = {
        "df_klines": pd.DataFrame({"dt": ["2026-04-22"], "symbol": ["X"]}),
        "df_weights": pd.DataFrame(
            {
                "dt": ["2026-04-22"],
                "symbol": ["X"],
                "weight": [0.5],
                "price": [100.0],
            }
        ),
        "summary": {
            "strategy": "s1",
            "latest_dt": "2026-04-22T10:00:00",
            "symbols": ["X"],
            "factor_count": 3,
            "success_factor_count": 3,
            "failed_factor_count": 0,
        },
        "consistency_messages": [],
    }
    wf.return_value = instance

    workspace_mock.tenant = tenant_realtime
    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="parquet",
        oss_uri="oss://vista-fc-test/w.parquet",
        size_bytes=10,
        sha256=None,
    )

    out = vista_realtime_service(
        tenant=tenant_realtime,
        payload=VistaRealtimeInput(strategy_toml_uri="oss://vista-fc-test/fts/s.toml"),
        workspace=workspace_mock,
    )
    assert out.summary.strategy == "s1"
    assert out.weights_artifact is not None
    assert out.weights_artifact.kind == "parquet"

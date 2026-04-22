"""vista-realtime service: wraps vista.realtime.workflow.RealtimeWorkflow.

Runs a single update tick: pulls the strategy TOML, computes latest weights,
writes to a parquet snapshot in tmp, pushes the snapshot to OSS.
"""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import pandas as pd
from vista.realtime.configs import RealtimeConfig
from vista.realtime.workflow import RealtimeWorkflow as _RealtimeWorkflow

from vista_fc.contracts.common import TenantContext
from vista_fc.contracts.vista_realtime import (
    SummaryData,
    TimingEntry,
    VistaRealtimeInput,
    VistaRealtimeOutput,
)
from vista_fc.services._support import pull_object, push_object
from vista_fc.storage.workspace import WorkspaceStorage


def _load_realtime_config(path: str | Path) -> RealtimeConfig:
    return RealtimeConfig.from_toml(path)


def vista_realtime_service(
    *,
    tenant: TenantContext,
    payload: VistaRealtimeInput,
    workspace: WorkspaceStorage,
) -> VistaRealtimeOutput:
    toml_local, _ = pull_object(workspace, oss_uri=payload.strategy_toml_uri)

    t0 = perf_counter()
    cfg = _load_realtime_config(toml_local)
    t1 = perf_counter()

    wf = _RealtimeWorkflow(config=cfg)
    update = wf.update(
        update_mode=payload.update_mode,  # pyright: ignore[reportCallIssue]
        push_targets=payload.push_targets,  # pyright: ignore[reportCallIssue]
    )
    t2 = perf_counter()

    summary_raw = update["summary"]
    summary = SummaryData(
        strategy=summary_raw["strategy"],
        latest_dt=summary_raw.get("latest_dt"),
        symbols=list(summary_raw.get("symbols", [])),
        factor_count=int(summary_raw.get("factor_count", 0)),
        success_factor_count=int(summary_raw.get("success_factor_count", 0)),
        failed_factor_count=int(summary_raw.get("failed_factor_count", 0)),
    )

    weights_ref = None
    df_weights = update.get("df_weights")
    if isinstance(df_weights, pd.DataFrame) and not df_weights.empty:
        weights_local = workspace.tmp_root / f"weights_{tenant.run_id}.parquet"
        weights_local.parent.mkdir(parents=True, exist_ok=True)
        df_weights.to_parquet(weights_local)
        key = (
            f"user_data/{tenant.user_hash}/realtime/{tenant.workspace_id}" f"/snapshots/weights_{tenant.run_id}.parquet"
        )
        uri = f"oss://{workspace.oss.bucket_name}/{key}"
        weights_ref = push_object(
            workspace,
            local_path=weights_local,
            oss_uri=uri,
            kind="parquet",
        )

    t3 = perf_counter()

    return VistaRealtimeOutput(
        summary=summary,
        latest_dt=summary.latest_dt,
        weights_artifact=weights_ref,
        timing=[
            TimingEntry(stage="load_config", elapsed_seconds=t1 - t0),
            TimingEntry(stage="update", elapsed_seconds=t2 - t1),
            TimingEntry(stage="persist", elapsed_seconds=t3 - t2),
        ],
    )

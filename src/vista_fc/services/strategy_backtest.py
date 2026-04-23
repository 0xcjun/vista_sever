"""strategy-backtest service: wraps vista.utils.strategy_backtest.run_strategy_backtest."""

from __future__ import annotations

from pathlib import Path

from vista.utils.strategy_backtest import (
    run_strategy_backtest as _run_strategy_backtest,
)

from vista_fc.contracts.common import ArtifactRef, TenantContext
from vista_fc.contracts.strategy_backtest import (
    StrategyBacktestInput,
    StrategyBacktestOutput,
)
from vista_fc.services._support import ensure_research_data, pull_object, push_object
from vista_fc.storage.workspace import ArtifactKind, WorkspaceStorage


def _artifact_kind_for(name: str) -> ArtifactKind:
    if name.endswith(".parquet"):
        return "parquet"
    if name.endswith(".feather"):
        return "feather"
    if name.endswith(".json"):
        return "report_json"
    return "log"


def strategy_backtest_service(
    *,
    tenant: TenantContext,
    payload: StrategyBacktestInput,
    workspace: WorkspaceStorage,
) -> StrategyBacktestOutput:
    toml_local, _ = pull_object(workspace, oss_uri=payload.strategy_toml_uri)
    ensure_research_data(workspace, oss_uri=payload.research_data_uri)

    out_root = workspace.tmp_root / f"backtest_{tenant.run_id}"
    out_root.mkdir(parents=True, exist_ok=True)

    result = _run_strategy_backtest(
        config=toml_local,
        mode=payload.mode,
        output_dir=str(out_root),
        data_mode=payload.data_mode,
        wbt_kwargs={
            "digits": payload.digits,
            "fee_rate": payload.fee_rate,
            "n_jobs": payload.n_jobs,
            "yearly_days": payload.yearly_days,
        },
        max_workers=payload.max_workers,
        verbose=False,
    )

    artifact_refs: dict[str, ArtifactRef] = {}
    for key, path in result.artifacts.items():
        p = Path(path)
        if not p.exists():
            continue
        oss_key = f"user_data/{tenant.user_hash}/research/{tenant.workspace_id}" f"/backtests/{tenant.run_id}/{p.name}"
        uri = f"oss://{workspace.oss.bucket_name}/{oss_key}"
        artifact_refs[key] = push_object(
            workspace,
            local_path=p,
            oss_uri=uri,
            kind=_artifact_kind_for(p.name),
        )

    return StrategyBacktestOutput(
        strategy=str(result.strategy),
        elapsed_s=float(result.elapsed_s),
        artifacts=artifact_refs,
    )

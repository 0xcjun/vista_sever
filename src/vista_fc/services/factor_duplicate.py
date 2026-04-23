"""factor-duplicate service: wraps vista.utils.factor_duplicate.factor_duplicate."""

from __future__ import annotations

import json

from vista.problems import get_problem as _get_problem
from vista.utils.factor_duplicate import (
    factor_duplicate as _vista_factor_duplicate,
)
from vista.utils.factor_duplicate import (
    load_model_config_from_file as _load_model_cfg,
)

from vista_fc.contracts.common import TenantContext
from vista_fc.contracts.factor_duplicate import (
    FactorDuplicateInput,
    FactorDuplicateOutput,
)
from vista_fc.services._support import ensure_research_data, pull_object, push_object
from vista_fc.storage.workspace import WorkspaceStorage


def factor_duplicate_service(
    *,
    tenant: TenantContext,
    payload: FactorDuplicateInput,
    workspace: WorkspaceStorage,
) -> FactorDuplicateOutput:
    db_local, _ = pull_object(workspace, oss_uri=payload.factors_db_uri)
    ensure_research_data(workspace, oss_uri=payload.research_data_uri)

    model_cfg = None
    if payload.model_config_uri:
        cfg_local, _ = pull_object(workspace, oss_uri=payload.model_config_uri)
        model_cfg = _load_model_cfg(str(cfg_local))

    problems = [_get_problem(c) for c in payload.problem_codes]
    report = _vista_factor_duplicate(
        db_path=str(db_local),
        route_codes=payload.route_codes,
        problems=problems,
        model_config=model_cfg,
        threshold=payload.threshold,
        max_workers=payload.max_workers,
        timeout=payload.timeout,
        verbose=False,
    )
    dumped = report.model_dump() if hasattr(report, "model_dump") else dict(report)

    report_local = workspace.tmp_root / f"duplicate_{tenant.run_id}.json"
    report_local.parent.mkdir(parents=True, exist_ok=True)
    report_local.write_text(json.dumps(dumped, ensure_ascii=False), encoding="utf-8")
    key = f"user_data/{tenant.user_hash}/research/{tenant.workspace_id}/reports/duplicate_{tenant.run_id}.json"
    uri = f"oss://{workspace.oss.bucket_name}/{key}"
    artifact = push_object(workspace, local_path=report_local, oss_uri=uri, kind="report_json")
    # 回写 duckdb (duplicate 内部对重复因子打 soft-delete 标签)
    push_object(workspace, local_path=db_local, oss_uri=payload.factors_db_uri, kind="duckdb")

    problem_stats = dumped.get("problem_stats", []) or []
    total_input = sum(int(p.get("input", 0)) for p in problem_stats)
    total_rejected = int(dumped.get("total_rejected", 0))
    return FactorDuplicateOutput(
        total_input=total_input,
        total_rejected=total_rejected,
        total_survived=max(total_input - total_rejected, 0),
        elapsed_seconds=float(dumped.get("elapsed_seconds", 0.0)),
        report_artifact=artifact,
    )

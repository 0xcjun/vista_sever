"""factor-evaluate service: wraps vista.utils.factor_evaluate.factor_evaluate."""

from __future__ import annotations

import json

from vista.models.config import load_model_configs_from_file as _load_model_configs_file
from vista.problems import get_problem as _get_problem
from vista.utils.factor_evaluate import factor_evaluate as _vista_factor_evaluate

from vista_fc.contracts.common import TenantContext
from vista_fc.contracts.factor_evaluate import (
    FactorEvaluateInput,
    FactorEvaluateOutput,
)
from vista_fc.services._support import pull_object, push_object
from vista_fc.storage.workspace import WorkspaceStorage


def factor_evaluate_service(
    *,
    tenant: TenantContext,
    payload: FactorEvaluateInput,
    workspace: WorkspaceStorage,
) -> FactorEvaluateOutput:
    db_local, _ = pull_object(workspace, oss_uri=payload.factors_db_uri)

    if payload.models_config_uri:
        cfg_local, _ = pull_object(workspace, oss_uri=payload.models_config_uri)
        model_configs = list(_load_model_configs_file(str(cfg_local)))
    else:
        model_configs = payload.models

    problems = [_get_problem(c) for c in payload.problem_codes]
    report = _vista_factor_evaluate(
        db_path=str(db_local),
        route_codes=payload.route_codes,
        problems=problems,
        model_configs=model_configs,  # pyright: ignore[reportArgumentType]
        max_workers=payload.max_workers,
        timeout=payload.timeout,
        fee_rate=payload.fee_rate,
        verbose=False,
    )
    dumped = report.model_dump() if hasattr(report, "model_dump") else dict(report)

    report_local = workspace.tmp_root / f"evaluate_{tenant.run_id}.json"
    report_local.parent.mkdir(parents=True, exist_ok=True)
    report_local.write_text(json.dumps(dumped, ensure_ascii=False), encoding="utf-8")
    key = f"user_data/{tenant.user_hash}/research/{tenant.workspace_id}/reports/evaluate_{tenant.run_id}.json"
    uri = f"oss://{workspace.oss.bucket_name}/{key}"
    artifact = push_object(workspace, local_path=report_local, oss_uri=uri, kind="report_json")

    return FactorEvaluateOutput(
        total_evaluations=int(dumped.get("total_evaluations", 0)),
        succeeded=int(dumped.get("succeeded", 0)),
        failed=int(dumped.get("failed", 0)),
        report_artifact=artifact,
    )

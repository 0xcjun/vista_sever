"""factor-plan service: wraps vista.agents.factor_plan.plan_factor_routes."""

from __future__ import annotations

from vista.agents.factor_plan import plan_factor_routes as _plan_factor_routes

from vista_fc.contracts.common import TenantContext
from vista_fc.contracts.factor_plan import (
    FactorPlanInput,
    FactorPlanOutput,
    FactorRouteSummary,
)
from vista_fc.services._support import push_object
from vista_fc.storage.workspace import WorkspaceStorage


def factor_plan_service(
    *,
    tenant: TenantContext,
    payload: FactorPlanInput,
    workspace: WorkspaceStorage,
) -> FactorPlanOutput:
    result = _plan_factor_routes(
        user_input=payload.user_input,
        interactive=payload.interactive,
        output_dir=None,
        model=payload.model,
        skill_path=payload.skill_path or ".claude/skills/vista-factor-planning",
        verbose=False,
    )
    dumped = result.model_dump() if hasattr(result, "model_dump") else dict(result)

    toml_local = workspace.tmp_root / f"factor_routes_{tenant.run_id}.toml"
    toml_local.parent.mkdir(parents=True, exist_ok=True)
    toml_local.write_text(str(dumped.get("toml_text", "")), encoding="utf-8")

    key = f"user_data/{tenant.user_hash}/research/{tenant.workspace_id}/factor_routes.toml"
    uri = f"oss://{workspace.oss.bucket_name}/{key}"
    artifact = push_object(workspace, local_path=toml_local, oss_uri=uri, kind="toml")

    routes = [
        FactorRouteSummary(
            code=r.get("code", ""),
            name=r.get("name", ""),
            compute_engine=r.get("compute_engine", ""),
            description=r.get("description"),
        )
        for r in dumped.get("routes", [])
    ]

    return FactorPlanOutput(routes=routes, routes_toml_artifact=artifact)

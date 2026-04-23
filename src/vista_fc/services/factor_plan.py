"""factor-plan service: wraps vista.agents.factor_plan.FactorPlanAgent."""

from __future__ import annotations

import asyncio

from vista.agents.factor_plan import FactorPlanAgent

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
    agent = FactorPlanAgent(
        model=payload.model,
        skill_path=payload.skill_path or ".claude/skills/vista-factor-planning",
        interactive=payload.interactive,
        verbose=False,
    )
    result = asyncio.run(agent.plan(payload.user_input))

    toml_local = workspace.tmp_root / f"factor_routes_{tenant.run_id}.toml"
    toml_local.parent.mkdir(parents=True, exist_ok=True)
    agent.save_toml(result, toml_local)

    key = f"user_data/{tenant.user_hash}/research/{tenant.workspace_id}/factor_routes.toml"
    uri = f"oss://{workspace.oss.bucket_name}/{key}"
    artifact = push_object(workspace, local_path=toml_local, oss_uri=uri, kind="toml")

    routes = [
        FactorRouteSummary(
            code=r.code,
            name=r.name,
            compute_engine=r.compute_engine.value if hasattr(r.compute_engine, "value") else str(r.compute_engine),
            description=r.description,
        )
        for r in result.routes
    ]

    return FactorPlanOutput(routes=routes, routes_toml_artifact=artifact)

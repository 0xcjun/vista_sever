"""factor-builder service: wraps vista.agents.factor_builder.FactorBuilder."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from vista.agents import factor_build as _factor_build
from vista.factor_db.models import FactorRoute

from vista_fc.contracts.common import TenantContext
from vista_fc.contracts.factor_builder import (
    FactorBuilderInput,
    FactorBuilderOutput,
    RouteBuildStat,
)
from vista_fc.services._support import pull_object, push_object
from vista_fc.storage.workspace import WorkspaceStorage


def _load_routes_from_toml(path: Path) -> list[dict[str, Any]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    routes = data.get("routes", [])
    if not isinstance(routes, list):
        raise ValueError(f"TOML {path} has no list 'routes'")
    return routes


def factor_builder_service(
    *,
    tenant: TenantContext,
    payload: FactorBuilderInput,
    workspace: WorkspaceStorage,
) -> FactorBuilderOutput:
    if payload.routes_toml_uri:
        toml_local, _ = pull_object(workspace, oss_uri=payload.routes_toml_uri)
        route_dicts = _load_routes_from_toml(toml_local)
    else:
        # route_code 单独路由：FactorRoute 有多个必填字段（name/engine/economic_logic/...），
        # 光 code 不够。要么跑上游 factor-plan 拿 TOML，要么后续扩展成从 factor_db 查历史路线。
        raise NotImplementedError("route_code 单路径分支未实现；请先通过 factor-plan 生成 routes_toml_uri")

    # TOML 里的每一项是 dict，vista.FactorBuilder 要求 FactorRoute pydantic 对象
    routes: list[FactorRoute] = [FactorRoute.model_validate(r) for r in route_dicts]

    db_local = workspace.tmp_root / "factors.duckdb"
    db_local.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    per_route: list[RouteBuildStat] = []
    api_key = payload.anthropic_api_key.get_secret_value() if payload.anthropic_api_key else None
    for route in routes:
        factors = _factor_build(
            route=route,
            db_path=str(db_local),
            builder_type=payload.builder_type,
            factor_numbers=payload.factor_numbers,
            batch_size=payload.batch_size,
            max_workers=payload.max_workers,
            multi_turn=payload.multi_turn,
            max_retries=payload.max_retries,
            verbose=False,
            anthropic_api_key=api_key,
            anthropic_base_url=payload.anthropic_base_url,
            anthropic_model=payload.anthropic_model,
        )
        per_route.append(
            RouteBuildStat(
                route_code=route.code,
                factor_count=len(factors),
            )
        )
        total += len(factors)

    key = f"user_data/{tenant.user_hash}/research/{tenant.workspace_id}/factors.duckdb"
    uri = f"oss://{workspace.oss.bucket_name}/{key}"
    artifact = push_object(workspace, local_path=db_local, oss_uri=uri, kind="duckdb")

    return FactorBuilderOutput(
        total_factors=total,
        per_route=per_route,
        route_codes=[s.route_code for s in per_route],
        factors_db_artifact=artifact,
    )

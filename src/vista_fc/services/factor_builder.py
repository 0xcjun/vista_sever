"""factor-builder service: wraps vista.agents.factor_builder.FactorBuilder."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from vista.agents.factor_builder import FactorBuilder as _FactorBuilder

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
        routes = _load_routes_from_toml(toml_local)
    else:
        assert payload.route_code is not None
        routes = [{"code": payload.route_code}]

    db_local = workspace.tmp_root / "factors.duckdb"
    db_local.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    per_route: list[RouteBuildStat] = []
    for route in routes:
        builder = _FactorBuilder(
            route=route,  # pyright: ignore[reportArgumentType]
            db_path=str(db_local),
            factor_numbers=payload.factor_numbers,
            batch_size=payload.batch_size,
            max_workers=payload.max_workers,
            multi_turn=payload.multi_turn,
            model=payload.model,
            max_retries=payload.max_retries,
            verbose=False,
        )
        factors = builder.run()
        per_route.append(
            RouteBuildStat(
                route_code=str(route.get("code", "")),
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
        factors_db_artifact=artifact,
    )

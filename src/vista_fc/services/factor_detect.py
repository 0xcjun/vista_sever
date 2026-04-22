"""factor-detect service: wraps vista.utils.factor_detect.factor_detect.

Steps:
  1. Pull factors.duckdb from OSS to /tmp
  2. (optional) pull problems_map
  3. Call vista detect on local file
  4. Serialize the report to a /tmp JSON
  5. Push the JSON to OSS under the workspace reports dir
  6. Return FactorDetectOutput with summary + artifact ref
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from vista.utils.factor_detect import factor_detect as _vista_factor_detect

from vista_fc.contracts.common import TenantContext
from vista_fc.contracts.factor_detect import FactorDetectInput, FactorDetectOutput
from vista_fc.services._support import pull_object, push_object
from vista_fc.storage.workspace import WorkspaceStorage

if TYPE_CHECKING:
    from vista.factor_db.enums import ComputeEngine
    from vista.problems import BaseResearchProblem

    ProblemsMap = dict[ComputeEngine, list[BaseResearchProblem] | None]


def factor_detect_service(
    *,
    tenant: TenantContext,
    payload: FactorDetectInput,
    workspace: WorkspaceStorage,
) -> FactorDetectOutput:
    # 1. pull factors.duckdb
    db_local, _etag = pull_object(workspace, oss_uri=payload.factors_db_uri)

    # 2. optional problems_map
    problems_map: ProblemsMap | None = None
    if payload.problems_map_uri:
        pm_local, _ = pull_object(workspace, oss_uri=payload.problems_map_uri)
        problems_map = _load_problems_map(pm_local)

    # 3. call vista
    report = _vista_factor_detect(
        db_path=str(db_local),
        problems_map=problems_map,
        max_workers=payload.max_workers,
        timeout=payload.timeout,
        verbose=False,
    )

    # 4. serialize report
    report_dict = report.model_dump() if hasattr(report, "model_dump") else dict(report)
    report_local = workspace.tmp_root / f"detect_report_{tenant.run_id}.json"
    report_local.parent.mkdir(parents=True, exist_ok=True)
    report_local.write_text(json.dumps(report_dict, ensure_ascii=False), encoding="utf-8")

    # 5. push
    report_key = f"user_data/{tenant.user_hash}/research/{tenant.workspace_id}" f"/reports/detect_{tenant.run_id}.json"
    report_uri = f"oss://{workspace.oss.bucket_name}/{report_key}"
    artifact = push_object(
        workspace,
        local_path=report_local,
        oss_uri=report_uri,
        kind="report_json",
    )

    # vista's FactorDetectBatchReport uses `total` not `total_factors`;
    # we fall back to `total_factors` in case the report shape ever changes.
    return FactorDetectOutput(
        total_factors=int(report_dict.get("total", report_dict.get("total_factors", 0))),
        passed=int(report_dict.get("passed", 0)),
        failed=int(report_dict.get("failed", 0)) + int(report_dict.get("errored", 0)),
        report_artifact=artifact,
    )


def _load_problems_map(path: Path) -> ProblemsMap:
    from vista.utils.factor_detect import load_problems_map_from_file

    return load_problems_map_from_file(str(path))

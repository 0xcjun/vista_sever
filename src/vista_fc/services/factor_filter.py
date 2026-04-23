"""factor-filter service: wraps vista.utils.factor_filter.factor_filter.

Emits a list of strategy TOMLs; each TOML is pushed to OSS under
realtime/FTS_<stem>/<basename>.
"""

from __future__ import annotations

from pathlib import Path

from vista.cli.factor_db_helpers import get_manager as _get_manager
from vista.utils.factor_filter import factor_filter as _vista_factor_filter

from vista_fc.contracts.common import TenantContext
from vista_fc.contracts.factor_filter import FactorFilterInput, FactorFilterOutput
from vista_fc.services._support import ensure_research_data, pull_object, push_object
from vista_fc.storage.workspace import WorkspaceStorage


def factor_filter_service(
    *,
    tenant: TenantContext,
    payload: FactorFilterInput,
    workspace: WorkspaceStorage,
) -> FactorFilterOutput:
    db_local, _ = pull_object(workspace, oss_uri=payload.factors_db_uri)
    ensure_research_data(workspace, oss_uri=payload.research_data_uri)

    out_dir = workspace.tmp_root / f"filter_{tenant.run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    with _get_manager(db_path=str(db_local)) as mgr:
        toml_paths = _vista_factor_filter(
            manager=mgr,
            output_dir=str(out_dir),
            problems=payload.problem_codes or None,
            routes=payload.route_codes or None,
            evaluate_methods=payload.evaluate_methods or None,
            filter_methods=payload.filter_methods or None,
            positive_extractor=payload.positive_extractor,
            positive_metric=payload.positive_metric,
            positive_threshold=payload.positive_threshold,
            n=payload.n,
            metric_keys=payload.metric_keys,
            creator=payload.creator,
            author=payload.author,
            outsample_sdt=payload.outsample_sdt,
            verbose=False,
        )

    refs = []
    for p in toml_paths:
        p_path = Path(p)
        fts_id = p_path.stem
        key = f"user_data/{tenant.user_hash}/realtime/FTS_{fts_id}/{p_path.name}"
        uri = f"oss://{workspace.oss.bucket_name}/{key}"
        refs.append(push_object(workspace, local_path=p_path, oss_uri=uri, kind="toml"))

    return FactorFilterOutput(toml_artifacts=refs, toml_count=len(refs))

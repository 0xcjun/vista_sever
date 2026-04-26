"""deadletter service: persist an unrecoverable FnF step failure to OSS.

Called by a catch-branch FnF task after the upstream step has exhausted its
retry policy (or raised a non-retriable error). We serialize the original
payload + classified error to a JSON file and push it under
`user_data/{user_hash}/deadletter/{run_id}/{failed_function}.json`.

The object is intentionally small (a few KB); it complements — does not replace —
the envelope stream in SLS. An operator can page a run from OSS by `run_id`.
"""

from __future__ import annotations

import json

from vista_fc.contracts.common import TenantContext
from vista_fc.contracts.deadletter import DeadLetterInput, DeadLetterOutput
from vista_fc.services._support import push_object
from vista_fc.storage.workspace import WorkspaceStorage


def deadletter_service(
    *,
    tenant: TenantContext,
    payload: DeadLetterInput,
    workspace: WorkspaceStorage,
) -> DeadLetterOutput:
    local = workspace.tmp_root / f"deadletter_{tenant.run_id}_{payload.failed_function}.json"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(
        json.dumps(
            {
                "failed_function": payload.failed_function,
                "original_payload": payload.original_payload,
                "error": payload.error.model_dump(),
                "tenant": tenant.model_dump(mode="json"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    key = f"user_data/{tenant.user_hash}/deadletter/{tenant.run_id}/{payload.failed_function}.json"
    uri = f"oss://{workspace.oss.bucket_name}/{key}"
    artifact = push_object(workspace, local_path=local, oss_uri=uri, kind="report_json")
    return DeadLetterOutput(deadletter_artifact=artifact)

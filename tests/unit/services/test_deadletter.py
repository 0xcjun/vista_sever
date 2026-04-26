from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from vista_fc.contracts.common import ArtifactRef, ErrorInfo
from vista_fc.contracts.deadletter import DeadLetterInput
from vista_fc.services.deadletter import deadletter_service


def test_deadletter_writes_structured_artifact(workspace_mock: MagicMock, tenant_research, tmp_path: Path) -> None:
    workspace_mock.tmp_root = tmp_path
    workspace_mock.push_from_tmp.return_value = ArtifactRef(
        kind="report_json",
        oss_uri="oss://vista-fc-test/user_data/u_abc/deadletter/run-test/factor-detect.json",
        size_bytes=100,
        sha256="ab",
    )

    out = deadletter_service(
        tenant=tenant_research,
        payload=DeadLetterInput(
            failed_function="factor-detect",
            original_payload={"factors_db_uri": "oss://x/y/z.duckdb"},
            error=ErrorInfo(
                code="VISTA_COMPUTE_TIMEOUT",
                message="timeout after 60s",
                retriable=True,
                trace_id="tr-abc",
            ),
        ),
        workspace=workspace_mock,
    )

    assert out.deadletter_artifact.kind == "report_json"
    # Verify the local file written before push carries all relevant fields.
    call = workspace_mock.push_from_tmp.call_args
    written_path: Path = call.kwargs["local_path"]
    data = json.loads(written_path.read_text(encoding="utf-8"))
    assert data["failed_function"] == "factor-detect"
    assert data["error"]["code"] == "VISTA_COMPUTE_TIMEOUT"
    assert data["tenant"]["user_hash"] == "u_abc"
    assert data["original_payload"]["factors_db_uri"] == "oss://x/y/z.duckdb"
    # Target key follows the per-tenant DLQ layout.
    assert call.kwargs["oss_key"] == "user_data/u_abc/deadletter/run-test/factor-detect.json"

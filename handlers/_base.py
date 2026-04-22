"""Shared handler skeleton.

Every handlers/<name>.py is a ~10-line file calling into run_handler with:
  - its Input / Output DTO classes
  - the matching service function
  - its function name (for logging)

run_handler is responsible for:
  1. configure_logging (once per process)
  2. parse event -> EnvelopeIn[Input]
  3. build WorkspaceStorage from env + tenant
  4. bind log_context
  5. call service()
  6. serialize EnvelopeOut[Output] OR EnvelopeOut with error
"""

from __future__ import annotations

import datetime as _dt
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from vista_fc.contracts.common import ArtifactRef, EnvelopeOut, TenantContext
from vista_fc.runtime.context import parse_envelope_in
from vista_fc.runtime.errors import classify
from vista_fc.runtime.logging import configure_logging, log_context
from vista_fc.storage.oss_client import OssClient
from vista_fc.storage.workspace import WorkspaceStorage

_LOG_CONFIGURED = False


def _ensure_logging() -> None:
    global _LOG_CONFIGURED
    if not _LOG_CONFIGURED:
        configure_logging()
        _LOG_CONFIGURED = True


def _build_workspace(tenant: TenantContext) -> WorkspaceStorage:
    oss = OssClient.from_env()
    tmp_root = Path(os.environ.get("VISTA_FC_TMP_ROOT", tempfile.gettempdir()))
    return WorkspaceStorage(oss=oss, tenant=tenant, tmp_root=tmp_root)


def _placeholder_tenant() -> TenantContext:
    return TenantContext(
        user_hash="unknown",
        workspace_id="unknown",
        workspace_kind="research",
        run_id="unknown",
        requested_at=_dt.datetime.now(_dt.UTC),
    )


def _extract_metrics(payload: BaseModel) -> dict[str, float | int | str]:
    m: dict[str, float | int | str] = {}
    data = payload.model_dump()
    for k, v in data.items():
        if isinstance(v, int | float | str) and not k.endswith("_artifact"):
            m[k] = v
    return m


def _extract_artifacts(payload: BaseModel) -> list[ArtifactRef]:
    refs: list[ArtifactRef] = []
    for attr in type(payload).model_fields:
        val = getattr(payload, attr, None)
        if isinstance(val, ArtifactRef):
            refs.append(val)
        elif isinstance(val, list) and val and isinstance(val[0], ArtifactRef):
            refs.extend(val)
        elif isinstance(val, dict) and val and any(isinstance(v, ArtifactRef) for v in val.values()):
            refs.extend(v for v in val.values() if isinstance(v, ArtifactRef))
    return refs


def run_handler[P: BaseModel, R: BaseModel](
    *,
    event: dict[str, Any],
    context: Any,  # noqa: ARG001
    input_cls: type[P],
    output_cls: type[R],
    service: Callable[..., R],
    function_name: str,
) -> dict[str, Any]:
    _ensure_logging()

    from loguru import logger

    # 1. parse envelope; on ValidationError short-circuit with failed envelope
    try:
        envelope = parse_envelope_in(event, input_cls)
    except Exception as e:  # noqa: BLE001
        err = classify(e)
        out = EnvelopeOut[output_cls](  # type: ignore[valid-type]
            tenant=_placeholder_tenant(),
            status="failed",
            error={  # type: ignore[arg-type]
                "code": err.code,
                "message": err.message,
                "retriable": err.retriable,
                "trace_id": err.trace_id,
            },
        )
        return out.model_dump(mode="json")

    tenant = envelope.tenant
    workspace = _build_workspace(tenant)

    with log_context(
        run_id=tenant.run_id,
        user_hash=tenant.user_hash,
        workspace_id=tenant.workspace_id,
        function_name=function_name,
    ):
        try:
            logger.info("invoke start")
            payload_out: R = service(
                tenant=tenant,
                payload=envelope.payload,
                workspace=workspace,
            )
            metrics = _extract_metrics(payload_out)
            artifacts = _extract_artifacts(payload_out)
            out = EnvelopeOut[output_cls](  # type: ignore[valid-type]
                tenant=tenant,
                status="succeeded",
                artifacts=artifacts,
                metrics=metrics,
                payload=payload_out,
            )
            logger.info("invoke ok")
            return out.model_dump(mode="json")
        except Exception as e:  # noqa: BLE001
            err = classify(e)
            logger.error(f"invoke failed: {err.code} {err.message}")
            out_err = EnvelopeOut[output_cls](  # type: ignore[valid-type]
                tenant=tenant,
                status="failed",
                error={  # type: ignore[arg-type]
                    "code": err.code,
                    "message": err.message,
                    "retriable": err.retriable,
                    "trace_id": err.trace_id,
                },
            )
            return out_err.model_dump(mode="json")

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
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from vista_fc.contracts.common import ArtifactRef, EnvelopeOut, TenantContext
from vista_fc.runtime.context import parse_envelope_in
from vista_fc.runtime.errors import classify
from vista_fc.runtime.idempotency import IdempotencyStore, tombstone_key
from vista_fc.runtime.idempotency import is_enabled as idempotency_enabled
from vista_fc.runtime.logging import configure_logging, log_context
from vista_fc.runtime.metrics import (
    HANDLER_DURATION_MS,
    HANDLER_ERROR_TOTAL,
    HANDLER_STATUS_TOTAL,
    emit_metric,
)
from vista_fc.storage.oss_client import OssClient
from vista_fc.storage.workspace import WorkspaceStorage

_LOG_CONFIGURED = False


def _ensure_logging() -> None:
    global _LOG_CONFIGURED
    if not _LOG_CONFIGURED:
        configure_logging()
        _LOG_CONFIGURED = True


def _build_workspace(tenant: TenantContext, context: Any) -> WorkspaceStorage:
    oss = OssClient.from_env(
        access_key_id=getattr(context, "access_key_id", None),
        access_key_secret=getattr(context, "access_key_secret", None),
        security_token=getattr(context, "security_token", None),
    )
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


_SENSITIVE_METRIC_KEYS = frozenset(
    {
        "anthropic_api_key",
        "anthropic_base_url",
        "anthropic_model",
    }
)


def _extract_metrics(payload: BaseModel) -> dict[str, float | int | str]:
    m: dict[str, float | int | str] = {}
    # mode="json" 让 SecretStr 序列化为 "**********",同时 _SENSITIVE_METRIC_KEYS 兜底
    # 排除掉 LLM 凭据/网关/模型这些不该出现在指标流的字段。
    data = payload.model_dump(mode="json")
    for k, v in data.items():
        if k in _SENSITIVE_METRIC_KEYS:
            continue
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
    workspace = _build_workspace(tenant, context)

    # Idempotency: on replay with the same (function_name, user_hash, run_id),
    # return the previously stored envelope instead of re-running the service.
    idem_store: IdempotencyStore | None = None
    idem_key: str | None = None
    if idempotency_enabled():
        idem_store = IdempotencyStore(workspace.oss)
        idem_key = tombstone_key(
            user_hash=tenant.user_hash,
            function_name=function_name,
            run_id=tenant.run_id,
        )
        cached = idem_store.lookup(idem_key)
        if cached is not None:
            return cached

    with log_context(
        run_id=tenant.run_id,
        user_hash=tenant.user_hash,
        workspace_id=tenant.workspace_id,
        function_name=function_name,
    ):
        started = time.perf_counter()
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
            duration_ms = (time.perf_counter() - started) * 1000.0
            emit_metric(name=HANDLER_DURATION_MS, value=duration_ms, unit="ms", status="succeeded")
            emit_metric(name=HANDLER_STATUS_TOTAL, value=1, status="succeeded")
            result = out.model_dump(mode="json")
            if idem_store is not None and idem_key is not None and not idem_store.claim(idem_key, result):
                # Race: if another worker wrote the tombstone first, prefer its
                # envelope so both callers return identical bytes.
                winner = idem_store.lookup(idem_key)
                if winner is not None:
                    return winner
            return result
        except Exception as e:  # noqa: BLE001
            err = classify(e)
            logger.error(f"invoke failed: {err.code} {err.message}")
            duration_ms = (time.perf_counter() - started) * 1000.0
            emit_metric(name=HANDLER_DURATION_MS, value=duration_ms, unit="ms", status="failed")
            emit_metric(name=HANDLER_STATUS_TOTAL, value=1, status="failed")
            emit_metric(
                name=HANDLER_ERROR_TOTAL,
                value=1,
                status="failed",
                error_code=err.code,
            )
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
            # Failures skip the tombstone so retries can succeed.
            return out_err.model_dump(mode="json")

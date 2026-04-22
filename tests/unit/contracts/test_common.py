"""Unit tests for contracts.common."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from vista_fc.contracts.common import (
    ArtifactRef,
    EnvelopeIn,
    EnvelopeOut,
    ErrorInfo,
    TenantContext,
)


class _DummyPayload(BaseModel):
    hello: str


def _mk_tenant() -> TenantContext:
    return TenantContext(
        user_hash="u_abc",
        workspace_id="EXP_001",
        workspace_kind="research",
        run_id="run-0001",
        requested_at=datetime(2026, 4, 22, 10, 0, tzinfo=UTC),
    )


def test_tenant_context_accepts_research() -> None:
    t = _mk_tenant()
    assert t.workspace_kind == "research"


def test_tenant_context_rejects_invalid_kind() -> None:
    with pytest.raises(ValidationError):
        TenantContext(
            user_hash="u_abc",
            workspace_id="EXP_001",
            workspace_kind="batch",  # type: ignore[arg-type]
            run_id="r",
            requested_at=datetime.now(UTC),
        )


def test_envelope_in_is_generic_over_payload() -> None:
    env: EnvelopeIn[_DummyPayload] = EnvelopeIn(
        tenant=_mk_tenant(),
        payload=_DummyPayload(hello="world"),
    )
    assert env.payload.hello == "world"


def test_envelope_out_defaults_payload_and_error_to_none() -> None:
    env: EnvelopeOut[_DummyPayload] = EnvelopeOut(
        tenant=_mk_tenant(),
        status="succeeded",
        artifacts=[],
        metrics={},
    )
    assert env.payload is None
    assert env.error is None


def test_envelope_out_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        EnvelopeOut(
            tenant=_mk_tenant(),
            status="done",  # type: ignore[arg-type]
            artifacts=[],
            metrics={},
        )


def test_artifact_ref_requires_oss_scheme() -> None:
    ref = ArtifactRef(
        kind="duckdb",
        oss_uri="oss://bucket/key.duckdb",
        size_bytes=123,
    )
    assert ref.oss_uri.startswith("oss://")

    with pytest.raises(ValidationError):
        ArtifactRef(
            kind="duckdb",
            oss_uri="s3://bucket/key.duckdb",
            size_bytes=123,
        )


def test_error_info_retriable_is_required_bool() -> None:
    ei = ErrorInfo(
        code="OSS_READ_FAIL",
        message="timeout",
        retriable=True,
        trace_id="tr-1",
    )
    assert ei.retriable is True

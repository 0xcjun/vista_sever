"""Shared DTOs used by every FC handler.

Spec §5.1: TenantContext / EnvelopeIn / EnvelopeOut / ArtifactRef / ErrorInfo.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T", bound=BaseModel)


class TenantContext(BaseModel):
    """Tenant + workspace identifier carried in every handler payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_hash: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    workspace_kind: Literal["research", "realtime"]
    run_id: str = Field(min_length=1)
    requested_at: datetime


class ArtifactRef(BaseModel):
    """Pointer to a persisted artifact (OSS)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "duckdb",
        "toml",
        "parquet",
        "feather",
        "report_json",
        "model",
        "log",
    ]
    oss_uri: str
    size_bytes: int = Field(ge=0)
    sha256: str | None = None

    @field_validator("oss_uri")
    @classmethod
    def _oss_scheme(cls, v: str) -> str:
        if not v.startswith("oss://"):
            raise ValueError("oss_uri must start with 'oss://'")
        return v


class ErrorInfo(BaseModel):
    """Structured error surface for FnF retry policy."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retriable: bool
    trace_id: str


class EnvelopeIn(BaseModel, Generic[T]):
    """Input envelope: tenant context + function-specific payload."""

    model_config = ConfigDict(extra="forbid")

    tenant: TenantContext
    payload: T


class EnvelopeOut(BaseModel, Generic[T]):
    """Output envelope: status, artifacts, metrics, optional payload / error."""

    model_config = ConfigDict(extra="forbid")

    tenant: TenantContext
    status: Literal["succeeded", "failed", "partial"]
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    payload: T | None = None
    error: ErrorInfo | None = None

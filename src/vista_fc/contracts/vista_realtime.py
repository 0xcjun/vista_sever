"""DTO for vista-realtime function.

Wraps `vista.realtime.workflow.RealtimeWorkflow` as a periodic tick:
each invocation pulls latest klines, recomputes factor weights, persists,
and publishes to configured targets.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from vista_fc.contracts.common import ArtifactRef


class VistaRealtimeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_toml_uri: str


class SummaryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str
    latest_dt: str | None
    symbols: list[str]
    factor_count: int = Field(ge=0)
    success_factor_count: int = Field(ge=0)
    failed_factor_count: int = Field(ge=0)


class TimingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    elapsed_seconds: float = Field(ge=0.0)


class VistaRealtimeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: SummaryData
    latest_dt: str | None
    weights_artifact: ArtifactRef | None = None
    timing: list[TimingEntry] = Field(default_factory=list)

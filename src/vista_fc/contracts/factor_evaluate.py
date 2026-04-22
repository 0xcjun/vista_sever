"""DTO for factor-evaluate function.

Wraps `vista.utils.factor_evaluate.factor_evaluate` — evaluates factors by
running strategy models on training segment.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vista_fc.contracts.common import ArtifactRef


class FactorEvaluateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    factors_db_uri: str
    route_codes: list[str] = Field(min_length=1)
    problem_codes: list[str] = Field(min_length=1)
    models: list[str] | None = None
    models_config_uri: str | None = None
    max_workers: int = Field(default=4, ge=1, le=32)
    timeout: int = Field(default=60, ge=1, le=3600)
    fee_rate: float = Field(default=0.0, ge=0.0, le=0.1)
    retry_failed: bool = False

    @model_validator(mode="after")
    def _models_xor_uri(self) -> FactorEvaluateInput:
        if self.models and self.models_config_uri:
            raise ValueError("models and models_config_uri are mutually exclusive")
        return self


class FactorEvaluateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_evaluations: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    report_artifact: ArtifactRef

"""DTO for factor-duplicate function.

Wraps `vista.utils.factor_duplicate.factor_duplicate` — drop redundant factors
within the route × problem grid based on wbt.WeightBacktest daily-return correlation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from vista_fc.contracts.common import ArtifactRef


class FactorDuplicateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    factors_db_uri: str
    route_codes: list[str] = Field(min_length=1)
    problem_codes: list[str] = Field(min_length=1)
    model_config_uri: str | None = None
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_workers: int = Field(default=4, ge=1, le=32)
    timeout: int = Field(default=60, ge=1, le=3600)


class FactorDuplicateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_checked: int = Field(ge=0)
    dropped: int = Field(ge=0)
    kept: int = Field(ge=0)
    report_artifact: ArtifactRef

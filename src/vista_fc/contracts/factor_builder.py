"""DTO for factor-builder function.

Wraps `vista.agents.factor_builder.FactorBuilder`.
Accepts either a routes_toml_uri (pointing to the output of factor-plan) or a
single route_code. Outputs cumulative counts and the persisted factors.duckdb.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vista_fc.contracts.common import ArtifactRef


class FactorBuilderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    routes_toml_uri: str | None = None
    route_code: str | None = None

    factor_numbers: int = Field(default=20, ge=1, le=10_000)
    batch_size: int = Field(default=5, ge=1, le=100)
    max_workers: int = Field(default=1, ge=1, le=32)
    multi_turn: bool = False
    model: str | None = None
    max_retries: int = Field(default=3, ge=0, le=20)

    @model_validator(mode="after")
    def _require_source(self) -> FactorBuilderInput:
        if not self.routes_toml_uri and not self.route_code:
            raise ValueError("Provide either routes_toml_uri or route_code")
        return self


class RouteBuildStat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_code: str
    factor_count: int = Field(ge=0)


class FactorBuilderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_factors: int = Field(ge=0)
    per_route: list[RouteBuildStat]
    factors_db_artifact: ArtifactRef

"""DTO for factor-plan function.

Wraps `vista.agents.factor_plan.plan_factor_routes`.
Input maps to the CLI `vista factor plan`.
Output carries a list of FactorRouteSummary + the persisted TOML artifact.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from vista_fc.contracts.common import ArtifactRef


class FactorPlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str = Field(min_length=1, description="交易想法 / 市场现象自由文本")
    interactive: bool = False
    model: str | None = None
    skill_path: str | None = None


class FactorRouteSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    name: str
    compute_engine: str
    description: str | None = None


class FactorPlanOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    routes: list[FactorRouteSummary]
    routes_toml_artifact: ArtifactRef

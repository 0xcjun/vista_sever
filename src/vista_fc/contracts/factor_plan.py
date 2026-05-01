"""DTO for factor-plan function.

Wraps `vista.agents.factor_plan.plan_factor_routes`.
Input maps to the CLI `vista factor plan`.
Output carries a list of FactorRouteSummary + the persisted TOML artifact.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from vista_fc.contracts.common import ArtifactRef


class FactorPlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str = Field(min_length=1, description="交易想法 / 市场现象自由文本")
    interactive: bool = False
    skill_path: str | None = None

    # LLM 显式参数（每个调用可独立传入,优先级高于函数环境变量）。
    # SecretStr 防止 repr / model_dump_json / 日志打印时泄漏。
    anthropic_api_key: SecretStr | None = Field(default=None, description="显式 Anthropic API Key")
    anthropic_base_url: str | None = Field(default=None, description="显式 Anthropic Base URL")
    anthropic_model: str | None = Field(default=None, description="显式 Anthropic 模型名")


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

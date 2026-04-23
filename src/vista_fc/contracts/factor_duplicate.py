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
    research_data_uri: str | None = None  # 可选;生产由 NAS 预置
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_workers: int = Field(default=4, ge=1, le=32)
    timeout: int = Field(default=60, ge=1, le=3600)


class FactorDuplicateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 字段与 vista.utils.factor_duplicate.FactorDuplicateReport 对齐
    total_input: int = Field(default=0, ge=0, description="所有 problem 输入因子数合计")
    total_rejected: int = Field(default=0, ge=0, description="被软删除的因子数（vista: total_rejected）")
    total_survived: int = Field(default=0, ge=0, description="保留下来的因子数")
    elapsed_seconds: float = Field(default=0.0, ge=0)
    report_artifact: ArtifactRef

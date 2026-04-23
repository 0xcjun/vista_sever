"""DTO for factor-detect function.

Wraps `vista.utils.factor_detect.factor_detect` which checks 未来数据 /
逐品种方差 / 增量一致性 on the given factors.duckdb.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from vista_fc.contracts.common import ArtifactRef


class FactorDetectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factors_db_uri: str
    problems_map_uri: str | None = None
    # 可选:OSS 上的 future_kline.duckdb,按需拉到容器 VISTA_RESEARCH_PATH。
    # 生产由 NAS 预置;本地/一次性请求传 URI。
    research_data_uri: str | None = None
    max_workers: int = Field(default=4, ge=1, le=32)
    timeout: int = Field(default=60, ge=1, le=3600)


class FactorDetectOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_factors: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    report_artifact: ArtifactRef

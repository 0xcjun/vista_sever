"""DTO for factor-filter function.

Wraps `vista.utils.factor_filter.factor_filter` — positive-expectation screen +
top-n fine filter, emits realtime strategy TOML files.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from vista_fc.contracts.common import ArtifactRef


class FactorFilterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factors_db_uri: str
    problem_codes: list[str] = Field(default_factory=list)
    route_codes: list[str] = Field(default_factory=list)
    evaluate_methods: list[str] = Field(default_factory=list)
    filter_methods: list[str] = Field(default_factory=list)
    positive_extractor: str = "ratio_across_problems"
    positive_metric: str = "绝对收益"
    positive_threshold: float = Field(default=0.618, ge=0.0, le=1.0)
    n: int = Field(default=20, ge=1, le=1000)
    metric_keys: list[str] | None = None
    creator: str = "factor_evaluate"
    author: str = ""
    outsample_sdt: str = "20250101"


class FactorFilterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    toml_artifacts: list[ArtifactRef]
    toml_count: int = Field(ge=0)

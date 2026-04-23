"""DTO for strategy-backtest function.

Wraps `vista.utils.strategy_backtest.run_strategy_backtest` — runs the full
backtest pipeline on a RealtimeConfig TOML.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from vista_fc.contracts.common import ArtifactRef


class StrategyBacktestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_toml_uri: str
    mode: Literal["research", "realtime"]
    data_mode: Literal["train", "valid", "total"] = "total"
    digits: int = Field(default=2, ge=0, le=10)
    fee_rate: float = Field(default=0.0, ge=0.0, le=0.1)
    n_jobs: int = Field(default=1, ge=1, le=32)
    yearly_days: int = Field(default=252, ge=1, le=366)
    max_workers: int = Field(default=1, ge=1, le=32)
    # 可选:用 OSS 上的研究数据覆盖容器默认 VISTA_RESEARCH_PATH
    # (生产由 NAS 挂载提供,本地/一次性按需从 OSS 拉)。
    # URI 指向单个 duckdb 文件,落盘文件名保留原 basename。
    research_data_uri: str | None = None


class StrategyBacktestOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str
    elapsed_s: float = Field(ge=0.0)
    artifacts: dict[str, ArtifactRef]
